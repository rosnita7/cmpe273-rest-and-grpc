import argparse
import sys
import time
from pathlib import Path

# Ensure local imports work regardless of execution directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import grpc

import inventory_pb2
import inventory_pb2_grpc

ORDER_TARGET = "localhost:50052"
INVENTORY_TARGET = "localhost:50051"


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def send_order(item_id, quantity, delay=0.0, target=ORDER_TARGET):
    print(f"\n[Client] Sending gRPC CreateOrder to {target}")
    print(f"[Client] Request: item_id='{item_id}', quantity={quantity}, delay={delay}s")

    channel = grpc.insecure_channel(target)
    stub = inventory_pb2_grpc.OrderServiceStub(channel)

    start_time = time.time()
    try:
        request = inventory_pb2.CreateOrderRequest(
            item_id=item_id,
            quantity=quantity,
            delay_seconds=delay
        )
        response = stub.CreateOrder(request, timeout=10.0)
        elapsed = time.time() - start_time
        print(f"[Client] Call succeeded in {elapsed:.2f}s!")
        print(f"[Client] Response: status={response.status}, order_id={response.order_id}, "
              f"total_price=${response.total_price:.2f}, message='{response.message}'")
        return True, response

    except grpc.RpcError as e:
        elapsed = time.time() - start_time
        print(f"[Client] gRPC call failed in {elapsed:.2f}s with status: {e.code()}")
        print(f"[Client] Error details: '{e.details()}'")
        return False, e


def check_stock_direct(item_id, quantity, delay=0.0, target=INVENTORY_TARGET):
    print(f"\n[Client] Sending direct gRPC CheckStock to {target}")
    print(f"[Client] Request: item_id='{item_id}', quantity={quantity}, delay={delay}s")

    channel = grpc.insecure_channel(target)
    stub = inventory_pb2_grpc.InventoryServiceStub(channel)

    start_time = time.time()
    try:
        request = inventory_pb2.CheckStockRequest(
            item_id=item_id,
            quantity=quantity,
            delay_seconds=delay
        )
        response = stub.CheckStock(request, timeout=10.0)
        elapsed = time.time() - start_time
        print(f"[Client] CheckStock succeeded in {elapsed:.2f}s!")
        print(f"[Client] Response: available={response.available}, stock={response.current_stock}, "
              f"price=${response.price:.2f}, message='{response.message}'")
        return True, response

    except grpc.RpcError as e:
        elapsed = time.time() - start_time
        print(f"[Client] CheckStock failed in {elapsed:.2f}s with status: {e.code()}")
        print(f"[Client] Error details: '{e.details()}'")
        return False, e


def run_full_suite():
    print_section("gRPC TEST SUITE: DEMONSTRATING FUNCTIONALITY & FAILURE HANDLING")

    print_section("Test Case 1: Successful Order (item_1, quantity: 2)")
    send_order("item_1", 2)

    print_section("Test Case 2: Out of Stock / Insufficient Quantity (item_2, quantity: 10)")
    print("Expected: Inventory aborts with FAILED_PRECONDITION; Order Service handles & propagates status")
    send_order("item_2", 10)

    print_section("Test Case 3: Item Not Found (item_999, quantity: 1)")
    print("Expected: Inventory aborts with NOT_FOUND; Order Service handles & propagates status")
    send_order("item_999", 1)

    print_section("Test Case 4: Failure Handling - Inventory Exceeds Deadline (delay: 4.0s > deadline: 2.0s)")
    print("Expected: Order Service catches DEADLINE_EXCEEDED, logs cleanly, returns DEADLINE_EXCEEDED")
    send_order("item_1", 1, delay=4.0)

    print_section("Test Case 5: Evidence Order Service Remains Running After Deadline Failure")
    print("Sending another valid order immediately to confirm Order Service is still alive and responsive:")
    send_order("item_4", 3)

    print_section("gRPC TEST SUITE COMPLETED")


def main():
    parser = argparse.ArgumentParser(description="gRPC Order and Inventory Client")
    parser.add_argument("--item", type=str, help="Item ID to order/check")
    parser.add_argument("--quantity", type=int, default=1, help="Quantity to order/check")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay in seconds to simulate slow inventory")
    parser.add_argument("--target", type=str, default=ORDER_TARGET, help=f"Target address (default: {ORDER_TARGET})")
    parser.add_argument("--direct-inventory", action="store_true", help="Call Inventory Service CheckStock directly")
    parser.add_argument("--suite", action="store_true", help="Run full automated demonstration test suite")
    args = parser.parse_args()

    if args.suite:
        run_full_suite()
    elif args.item:
        if args.direct_inventory:
            check_stock_direct(args.item, args.quantity, args.delay, target=args.target or INVENTORY_TARGET)
        else:
            send_order(args.item, args.quantity, args.delay, target=args.target)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
