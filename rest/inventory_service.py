import argparse
import logging
import os
import time
from flask import Flask, jsonify, request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Inventory-REST] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("InventoryServiceREST")

app = Flask(__name__)

# In-memory inventory catalog
# item_id -> details
INVENTORY = {
    "item_1": {"name": "Laptop", "stock": 10, "price": 999.99},
    "item_2": {"name": "Wireless Mouse", "stock": 3, "price": 29.99},
    "item_3": {"name": "Mechanical Keyboard", "stock": 0, "price": 89.99},
    "item_4": {"name": "USB-C Hub", "stock": 50, "price": 45.00},
}

# Global simulated server delay in seconds (if started with --delay or SIMULATE_DELAY env var)
SERVER_DELAY = float(os.getenv("SIMULATE_DELAY", "0.0"))


def perform_stock_check(item_id: str, quantity: int, delay: float):
    # Apply simulated delay if requested
    effective_delay = max(delay, SERVER_DELAY)
    if effective_delay > 0:
        logger.warning(
            f"Simulating slow response: sleeping for {effective_delay:.2f}s before responding to check for '{item_id}'"
        )
        time.sleep(effective_delay)

    if quantity <= 0:
        logger.warning(f"Invalid quantity requested: {quantity} for item '{item_id}'")
        return {"error": "Quantity must be greater than 0", "item_id": item_id}, 400

    if item_id not in INVENTORY:
        logger.warning(f"Item '{item_id}' not found in inventory")
        return {
            "error": "Item not found in inventory",
            "item_id": item_id,
            "available": False
        }, 404

    item = INVENTORY[item_id]
    if item["stock"] < quantity:
        logger.info(
            f"Insufficient stock for '{item_id}': requested {quantity}, available {item['stock']}"
        )
        return {
            "item_id": item_id,
            "name": item["name"],
            "available": False,
            "stock": item["stock"],
            "requested_quantity": quantity,
            "error": f"Insufficient stock: requested {quantity}, but only {item['stock']} available"
        }, 400

    logger.info(
        f"Stock check SUCCESS for '{item_id}': requested {quantity}, available {item['stock']}"
    )
    return {
        "item_id": item_id,
        "name": item["name"],
        "available": True,
        "stock": item["stock"],
        "requested_quantity": quantity,
        "price": item["price"],
        "message": "Item is available in requested quantity"
    }, 200


@app.route("/inventory/<item_id>", methods=["GET"])
def check_inventory_get(item_id: str):
    """
    Check stock availability via GET /inventory/<item_id>?quantity=...&delay=...
    """
    try:
        quantity = int(request.args.get("quantity", 1))
    except ValueError:
        return jsonify({"error": "Invalid quantity parameter (must be an integer)"}), 400

    try:
        delay = float(request.args.get("delay", 0.0))
    except ValueError:
        delay = 0.0

    result, status_code = perform_stock_check(item_id, quantity, delay)
    return jsonify(result), status_code


@app.route("/inventory/check", methods=["POST"])
def check_inventory_post():
    """
    Check stock availability via POST /inventory/check with JSON body
    """
    data = request.get_json(silent=True) or {}
    item_id = data.get("item_id")
    if not item_id:
        return jsonify({"error": "Missing required field 'item_id'"}), 400

    try:
        quantity = int(data.get("quantity", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid quantity parameter"}), 400

    try:
        delay = float(data.get("delay", 0.0))
    except (ValueError, TypeError):
        delay = 0.0

    result, status_code = perform_stock_check(item_id, quantity, delay)
    return jsonify(result), status_code


@app.route("/inventory", methods=["GET"])
def list_inventory():
    """List all inventory items and current stock."""
    return jsonify({"inventory": INVENTORY}), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "inventory-rest"}), 200


def main():
    global SERVER_DELAY
    parser = argparse.ArgumentParser(description="REST Inventory Service")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on (default: 8001)")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Simulate delay in seconds for every response (default: 0.0)"
    )
    args = parser.parse_args()

    if args.delay > 0:
        SERVER_DELAY = args.delay
        logger.info(f"Configured with permanent simulated delay of {SERVER_DELAY}s")

    logger.info(f"Starting REST Inventory Service on port {args.port}...")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
