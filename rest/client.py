import argparse
import json
import sys
import time
import requests

ORDER_URL = "http://127.0.0.1:8000"


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def send_order(item_id, quantity, delay=0.0):
    url = f"{ORDER_URL}/orders"
    payload = {"item_id": item_id, "quantity": quantity}
    if delay > 0:
        payload["delay"] = delay

    print(f"\n[Client] Sending POST {url}")
    print(f"[Client] Payload: {json.dumps(payload)}")
    start_time = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=10.0)
        elapsed = time.time() - start_time
        print(f"[Client] Response Status: HTTP {resp.status_code} ({elapsed:.2f}s)")
        try:
            body = resp.json()
            print(f"[Client] Response Body:\n{json.dumps(body, indent=2)}")
        except Exception:
            print(f"[Client] Response Body: {resp.text}")
        return resp.status_code, resp.json() if resp.headers.get("content-type") == "application/json" else resp.text
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[Client] Request failed after {elapsed:.2f}s: {e}")
        return None, str(e)


def check_health():
    url = f"{ORDER_URL}/health"
    print(f"\n[Client] Checking Order Service health: GET {url}")
    try:
        resp = requests.get(url, timeout=3.0)
        print(f"[Client] Status: HTTP {resp.status_code}")
        print(f"[Client] Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"[Client] Health check failed: {e}")
        return False


def run_full_suite():
    print_section("REST TEST SUITE: DEMONSTRATING FUNCTIONALITY & FAILURE HANDLING")

    print("\nStep 1: Check Order Service Health")
    if not check_health():
        print("[Client] ERROR: Order Service is not running at", ORDER_URL)
        sys.exit(1)

    print_section("Test Case 1: Successful Order (item_1, quantity: 2)")
    send_order("item_1", 2)

    print_section("Test Case 2: Out of Stock / Insufficient Quantity (item_2, quantity: 10)")
    send_order("item_2", 10)

    print_section("Test Case 3: Item Not Found (item_999, quantity: 1)")
    send_order("item_999", 1)

    print_section("Test Case 4: Failure Handling - Inventory Responds Too Slowly (delay: 4.0s > timeout 2.0s)")
    print("Expected: Order Service catches requests.exceptions.Timeout and returns HTTP 504")
    send_order("item_1", 1, delay=4.0)

    print_section("Test Case 5: Evidence Order Service Remains Running After Timeout Failure")
    print("Sending another valid order immediately to confirm Order Service is still alive and responsive:")
    send_order("item_4", 3)

    print("\nVerifying final health status:")
    check_health()
    print_section("REST TEST SUITE COMPLETED")


def main():
    parser = argparse.ArgumentParser(description="REST Order Service Client")
    parser.add_argument("--item", type=str, help="Item ID to order")
    parser.add_argument("--quantity", type=int, default=1, help="Quantity to order")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay in seconds to simulate slow inventory")
    parser.add_argument("--suite", action="store_true", help="Run full automated demonstration test suite")
    parser.add_argument("--health", action="store_true", help="Check Order Service health")
    args = parser.parse_args()

    if args.suite:
        run_full_suite()
    elif args.health:
        check_health()
    elif args.item:
        send_order(args.item, args.quantity, args.delay)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
