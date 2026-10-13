import argparse
import logging
import os
import uuid
from flask import Flask, jsonify, request
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Order-REST] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("OrderServiceREST")

app = Flask(__name__)

# Configuration
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://127.0.0.1:8001")
REST_TIMEOUT = float(os.getenv("REST_TIMEOUT", "2.0"))  # configured timeout in seconds

# In-memory orders store
ORDERS = {}


@app.route("/orders", methods=["POST"])
def create_order():
    """
    Accepts an order containing item_id and quantity.
    Calls Inventory Service with a strict HTTP timeout.
    """
    data = request.get_json(silent=True)
    if not data:
        logger.warning("Rejected order: Request body must be valid JSON")
        return jsonify({"error": "Request body must be valid JSON"}), 400

    item_id = data.get("item_id")
    quantity = data.get("quantity")
    # Optional delay to pass to Inventory Service for demonstrating timeout
    delay = data.get("delay", 0.0)

    if not item_id or not isinstance(item_id, str):
        logger.warning(f"Rejected order: Missing or invalid 'item_id': {item_id}")
        return jsonify({"error": "Field 'item_id' is required and must be a string"}), 400

    if quantity is None or not isinstance(quantity, int) or quantity <= 0:
        logger.warning(f"Rejected order: Invalid quantity: {quantity}")
        return jsonify({"error": "Field 'quantity' is required and must be an integer > 0"}), 400

    logger.info(
        f"Processing order request: item_id='{item_id}', quantity={quantity}, simulate_delay={delay}s"
    )

    # Prepare call to Inventory Service
    check_url = f"{INVENTORY_URL}/inventory/{item_id}"
    params = {"quantity": quantity}
    if delay:
        params["delay"] = delay

    logger.info(
        f"Calling Inventory Service at {check_url} (configured timeout: {REST_TIMEOUT}s)..."
    )

    try:
        response = requests.get(check_url, params=params, timeout=REST_TIMEOUT)
    except requests.exceptions.Timeout:
        # REQUIREMENT: The REST call handles the timeout cleanly.
        # REQUIREMENT: The Order Service remains running after failure.
        logger.error(
            f"TIMEOUT EXCEEDED: Inventory Service failed to respond within {REST_TIMEOUT}s "
            f"for item '{item_id}'. Order aborted."
        )
        return jsonify({
            "status": "FAILED",
            "error": "Gateway Timeout",
            "message": f"Inventory service timed out after {REST_TIMEOUT}s limit.",
            "item_id": item_id,
            "quantity": quantity
        }), 504

    except requests.exceptions.ConnectionError:
        logger.error(
            f"CONNECTION FAILED: Could not reach Inventory Service at {INVENTORY_URL}."
        )
        return jsonify({
            "status": "FAILED",
            "error": "Service Unavailable",
            "message": f"Could not connect to Inventory Service at {INVENTORY_URL}.",
            "item_id": item_id,
            "quantity": quantity
        }), 503

    except requests.exceptions.RequestException as e:
        logger.error(f"Unexpected error calling Inventory Service: {e}")
        return jsonify({
            "status": "ERROR",
            "error": "Internal Communication Error",
            "message": str(e)
        }), 500

    # Parse response from Inventory Service
    try:
        inventory_data = response.json()
    except Exception:
        inventory_data = {"raw": response.text}

    logger.info(
        f"Inventory Service responded with HTTP {response.status_code}: {inventory_data}"
    )

    if response.status_code == 200 and inventory_data.get("available") is True:
        # Order is confirmed
        order_id = f"ord-{uuid.uuid4().hex[:8]}"
        price = inventory_data.get("price", 0.0)
        total_price = round(price * quantity, 2)

        order_record = {
            "order_id": order_id,
            "item_id": item_id,
            "item_name": inventory_data.get("name", "Unknown"),
            "quantity": quantity,
            "total_price": total_price,
            "status": "CONFIRMED",
            "message": "Order placed successfully"
        }
        ORDERS[order_id] = order_record

        logger.info(f"Order created successfully: order_id={order_id}, total=${total_price}")
        return jsonify(order_record), 201

    elif response.status_code == 404:
        logger.warning(f"Order rejected: item '{item_id}' not found in inventory")
        return jsonify({
            "status": "REJECTED",
            "error": "Item Not Found",
            "message": inventory_data.get("error", f"Item '{item_id}' does not exist"),
            "item_id": item_id
        }), 404

    elif response.status_code == 400:
        logger.warning(
            f"Order rejected: item '{item_id}' unavailable or insufficient stock"
        )
        return jsonify({
            "status": "REJECTED",
            "error": "Unavailable",
            "message": inventory_data.get("error", "Requested quantity is not available"),
            "available_stock": inventory_data.get("stock", 0),
            "requested_quantity": quantity,
            "item_id": item_id
        }), 400

    else:
        logger.error(f"Inventory Service returned unhandled status: {response.status_code}")
        return jsonify({
            "status": "FAILED",
            "error": "Inventory Check Failed",
            "details": inventory_data
        }), response.status_code


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id: str):
    """Retrieve an existing order."""
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({"error": "Order not found", "order_id": order_id}), 404
    return jsonify(order), 200


@app.route("/orders", methods=["GET"])
def list_orders():
    """List all placed orders."""
    return jsonify({"orders": list(ORDERS.values())}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint demonstrating that the service is running."""
    return jsonify({
        "status": "healthy",
        "service": "order-rest",
        "inventory_url": INVENTORY_URL,
        "timeout_seconds": REST_TIMEOUT,
        "orders_count": len(ORDERS)
    }), 200


def main():
    global INVENTORY_URL, REST_TIMEOUT
    parser = argparse.ArgumentParser(description="REST Order Service")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--inventory-url",
        type=str,
        default=INVENTORY_URL,
        help="URL of the Inventory Service (default: http://127.0.0.1:8001)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=REST_TIMEOUT,
        help="HTTP timeout in seconds for Inventory Service calls (default: 2.0)"
    )
    args = parser.parse_args()

    INVENTORY_URL = args.inventory_url
    REST_TIMEOUT = args.timeout

    logger.info(f"Starting REST Order Service on port {args.port}...")
    logger.info(f"Connected to Inventory Service at: {INVENTORY_URL}")
    logger.info(f"Configured Inventory request timeout: {REST_TIMEOUT} seconds")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
