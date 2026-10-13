import argparse
from concurrent import futures
import logging
import os
import sys
import threading
import uuid
from pathlib import Path

# Ensure local imports work regardless of execution directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import grpc
from grpc_reflection.v1alpha import reflection
from flask import Flask, jsonify, request as flask_request

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Order-gRPC] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("OrderServiceGRPC")

# In-memory orders store
ORDERS = {}


class OrderServiceServicer(inventory_pb2_grpc.OrderServiceServicer):
    """Implementation of the gRPC Order Service."""

    def __init__(self, inventory_target="localhost:50051", deadline=2.0):
        self.inventory_target = inventory_target
        self.deadline = deadline
        self.channel = grpc.insecure_channel(self.inventory_target)
        self.inventory_stub = inventory_pb2_grpc.InventoryServiceStub(self.channel)
        logger.info(
            f"Initialized Order Service connected to Inventory at '{self.inventory_target}' "
            f"with configured gRPC deadline = {self.deadline}s"
        )

    def CreateOrder(self, request, context):
        item_id = request.item_id
        quantity = request.quantity
        delay = request.delay_seconds

        logger.info(
            f"Received CreateOrder: item_id='{item_id}', quantity={quantity}, simulate_delay={delay}s"
        )

        if not item_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Field 'item_id' cannot be empty")

        if quantity <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Field 'quantity' must be > 0")

        # REQUIREMENT: Set a gRPC deadline for the Order -> Inventory call
        logger.info(
            f"Calling InventoryService.CheckStock for '{item_id}' with gRPC deadline={self.deadline}s..."
        )

        try:
            stock_request = inventory_pb2.CheckStockRequest(
                item_id=item_id,
                quantity=quantity,
                delay_seconds=delay
            )
            # Invoking gRPC stub with timeout specifies the call deadline
            stock_resp = self.inventory_stub.CheckStock(
                stock_request,
                timeout=self.deadline
            )

        except grpc.RpcError as rpc_error:
            # REQUIREMENT: The gRPC call handles the exceeded deadline cleanly.
            # REQUIREMENT: The Order Service remains running after failure.
            status_code = rpc_error.code()
            details = rpc_error.details()

            if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.error(
                    f"DEADLINE EXCEEDED: Inventory Service failed to respond within {self.deadline}s "
                    f"for item '{item_id}'. Handling error cleanly."
                )
                context.abort(
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                    f"Inventory Service deadline exceeded ({self.deadline}s timeout limit)"
                )

            elif status_code == grpc.StatusCode.NOT_FOUND:
                logger.warning(f"Inventory check returned NOT_FOUND for '{item_id}': {details}")
                context.abort(grpc.StatusCode.NOT_FOUND, details)

            elif status_code == grpc.StatusCode.FAILED_PRECONDITION:
                logger.warning(
                    f"Inventory check returned FAILED_PRECONDITION (insufficient stock) for '{item_id}': {details}"
                )
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, details)

            elif status_code == grpc.StatusCode.UNAVAILABLE:
                logger.error(f"Inventory Service unavailable at '{self.inventory_target}': {details}")
                context.abort(
                    grpc.StatusCode.UNAVAILABLE,
                    f"Could not connect to Inventory Service at {self.inventory_target}"
                )

            else:
                logger.error(f"Unexpected gRPC error from Inventory Service: {status_code} - {details}")
                context.abort(status_code, details)

        # Stock is available; finalize the order
        order_id = f"ord-grpc-{uuid.uuid4().hex[:8]}"
        total_price = round(stock_resp.price * quantity, 2)

        order_record = {
            "order_id": order_id,
            "item_id": item_id,
            "item_name": stock_resp.name,
            "quantity": quantity,
            "total_price": total_price,
            "status": "CONFIRMED"
        }
        ORDERS[order_id] = order_record

        logger.info(f"Order created successfully: order_id={order_id}, total=${total_price}")
        return inventory_pb2.CreateOrderResponse(
            order_id=order_id,
            item_id=item_id,
            quantity=quantity,
            status="CONFIRMED",
            total_price=total_price,
            message="Order placed successfully via gRPC"
        )


# Optional HTTP REST Bridge for testing gRPC Order Service via curl
http_app = Flask(__name__)
servicer_instance = None


@http_app.route("/orders", methods=["POST"])
def http_create_order():
    data = flask_request.get_json(silent=True) or {}
    item_id = data.get("item_id", "")
    quantity = int(data.get("quantity", 1))
    delay = float(data.get("delay", 0.0))

    if not servicer_instance:
        return jsonify({"error": "Order service not initialized"}), 500

    try:
        req = inventory_pb2.CreateOrderRequest(
            item_id=item_id,
            quantity=quantity,
            delay_seconds=delay
        )
        # Call stub on self or make direct call
        channel = grpc.insecure_channel(servicer_instance.inventory_target)
        stub = inventory_pb2_grpc.InventoryServiceStub(channel)
        stock_resp = stub.CheckStock(
            inventory_pb2.CheckStockRequest(item_id=item_id, quantity=quantity, delay_seconds=delay),
            timeout=servicer_instance.deadline
        )
        order_id = f"ord-grpc-{uuid.uuid4().hex[:8]}"
        total_price = round(stock_resp.price * quantity, 2)
        return jsonify({
            "order_id": order_id,
            "item_id": item_id,
            "quantity": quantity,
            "status": "CONFIRMED",
            "total_price": total_price,
            "message": "Order placed successfully (via gRPC backend)"
        }), 201
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            return jsonify({
                "status": "FAILED",
                "error": "DEADLINE_EXCEEDED",
                "message": f"Inventory Service deadline exceeded ({servicer_instance.deadline}s)"
            }), 504
        elif e.code() == grpc.StatusCode.NOT_FOUND:
            return jsonify({"status": "REJECTED", "error": "NOT_FOUND", "message": e.details()}), 404
        elif e.code() == grpc.StatusCode.FAILED_PRECONDITION:
            return jsonify({"status": "REJECTED", "error": "FAILED_PRECONDITION", "message": e.details()}), 400
        else:
            return jsonify({"status": "ERROR", "error": str(e.code()), "message": e.details()}), 500


@http_app.route("/health", methods=["GET"])
def http_health():
    return jsonify({
        "status": "healthy",
        "service": "order-grpc",
        "grpc_port": 50052,
        "inventory_target": servicer_instance.inventory_target if servicer_instance else "unknown",
        "deadline_seconds": servicer_instance.deadline if servicer_instance else 2.0,
        "orders_count": len(ORDERS)
    }), 200


def run_http_bridge(port):
    http_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def serve(port=50052, inventory_target="localhost:50051", deadline=2.0, http_port=5002):
    global servicer_instance
    servicer_instance = OrderServiceServicer(inventory_target=inventory_target, deadline=deadline)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_OrderServiceServicer_to_server(servicer_instance, server)

    # Enable gRPC server reflection
    service_names = (
        inventory_pb2.DESCRIPTOR.services_by_name["OrderService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server_address = f"0.0.0.0:{port}"
    server.add_insecure_port(server_address)
    server.start()
    logger.info(f"gRPC Order Service started and listening on {server_address}")

    if http_port:
        http_thread = threading.Thread(target=run_http_bridge, args=(http_port,), daemon=True)
        http_thread.start()
        logger.info(f"Optional HTTP bridge for gRPC Order Service running on http://0.0.0.0:{http_port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Stopping gRPC Order Service...")
        server.stop(grace=1)


def main():
    parser = argparse.ArgumentParser(description="gRPC Order Service")
    parser.add_argument("--port", type=int, default=50052, help="Port to listen on (default: 50052)")
    parser.add_argument(
        "--inventory-target",
        type=str,
        default=os.getenv("INVENTORY_TARGET", "localhost:50051"),
        help="Target address of Inventory Service (default: localhost:50051)"
    )
    parser.add_argument(
        "--deadline",
        type=float,
        default=float(os.getenv("GRPC_DEADLINE", "2.0")),
        help="gRPC deadline in seconds for Inventory calls (default: 2.0)"
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=5002,
        help="Port for optional HTTP bridge (default: 5002, 0 to disable)"
    )
    args = parser.parse_args()
    serve(
        port=args.port,
        inventory_target=args.inventory_target,
        deadline=args.deadline,
        http_port=args.http_port
    )


if __name__ == "__main__":
    main()
