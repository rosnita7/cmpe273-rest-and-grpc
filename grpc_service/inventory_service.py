import argparse
from concurrent import futures
import logging
import os
import sys
import time
from pathlib import Path

# Ensure local imports work regardless of execution directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import grpc
from grpc_reflection.v1alpha import reflection

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Inventory-gRPC] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("InventoryServiceGRPC")

# In-memory inventory catalog
INVENTORY = {
    "item_1": {"name": "Laptop", "stock": 10, "price": 999.99},
    "item_2": {"name": "Wireless Mouse", "stock": 3, "price": 29.99},
    "item_3": {"name": "Mechanical Keyboard", "stock": 0, "price": 89.99},
    "item_4": {"name": "USB-C Hub", "stock": 50, "price": 45.00},
}

# Global simulated server delay (configurable via CLI or env var)
SERVER_DELAY = float(os.getenv("SIMULATE_DELAY", "0.0"))


class InventoryServiceServicer(inventory_pb2_grpc.InventoryServiceServicer):
    """Implementation of the gRPC Inventory Service."""

    def CheckStock(self, request, context):
        item_id = request.item_id
        quantity = request.quantity
        delay = request.delay_seconds

        effective_delay = max(delay, SERVER_DELAY)
        if effective_delay > 0:
            logger.warning(
                f"Simulating slow response: sleeping for {effective_delay:.2f}s "
                f"before responding to CheckStock for item '{item_id}'"
            )
            time.sleep(effective_delay)

        logger.info(f"Received CheckStock request: item_id='{item_id}', quantity={quantity}")

        # Validation: quantity must be positive
        if quantity <= 0:
            logger.warning(f"Invalid quantity: {quantity}")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Quantity must be greater than 0, got {quantity}"
            )

        # Validation: item existence
        if item_id not in INVENTORY:
            logger.warning(f"Item not found: '{item_id}'")
            # REQUIREMENT: Return an appropriate gRPC error/status when requested item is unavailable
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Item '{item_id}' does not exist in inventory"
            )

        item = INVENTORY[item_id]

        # Validation: stock availability
        if item["stock"] < quantity:
            logger.warning(
                f"Insufficient stock for '{item_id}': requested {quantity}, available {item['stock']}"
            )
            # REQUIREMENT: Return an appropriate gRPC error/status when requested item is unavailable
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Insufficient stock for item '{item_id}': requested {quantity}, available {item['stock']}"
            )

        logger.info(
            f"Stock check SUCCESS for '{item_id}': requested {quantity}, available {item['stock']}"
        )
        return inventory_pb2.CheckStockResponse(
            item_id=item_id,
            name=item["name"],
            available=True,
            current_stock=item["stock"],
            price=item["price"],
            message="Item is available in requested quantity"
        )


def serve(port=50051, delay=0.0):
    global SERVER_DELAY
    if delay > 0:
        SERVER_DELAY = delay
        logger.info(f"Configured with permanent simulated delay of {SERVER_DELAY}s")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryServiceServicer(), server
    )

    # Enable gRPC server reflection for development/debugging tooling
    service_names = (
        inventory_pb2.DESCRIPTOR.services_by_name["InventoryService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server_address = f"0.0.0.0:{port}"
    server.add_insecure_port(server_address)
    server.start()
    logger.info(f"gRPC Inventory Service started and listening on {server_address}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Stopping gRPC Inventory Service...")
        server.stop(grace=1)


def main():
    parser = argparse.ArgumentParser(description="gRPC Inventory Service")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on (default: 50051)")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Simulate delay in seconds for every response (default: 0.0)"
    )
    args = parser.parse_args()
    serve(port=args.port, delay=args.delay)


if __name__ == "__main__":
    main()
