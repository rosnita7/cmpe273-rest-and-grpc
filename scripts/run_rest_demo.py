#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path
import requests

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PYTHON_BIN = PROJECT_ROOT / "venv" / "bin" / "python"
if not PYTHON_BIN.exists():
    PYTHON_BIN = sys.executable


def wait_for_service(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def main():
    print("=" * 70)
    print("  LAUNCHING REST SERVICES DEMONSTRATION")
    print("=" * 70)

    # 1. Start Inventory Service
    inv_cmd = [str(PYTHON_BIN), str(PROJECT_ROOT / "rest" / "inventory_service.py"), "--port", "8001"]
    print(f"[Demo] Starting REST Inventory Service on port 8001...")
    inv_proc = subprocess.Popen(inv_cmd, cwd=str(PROJECT_ROOT))

    # 2. Start Order Service
    order_cmd = [
        str(PYTHON_BIN),
        str(PROJECT_ROOT / "rest" / "order_service.py"),
        "--port", "8000",
        "--inventory-url", "http://127.0.0.1:8001",
        "--timeout", "2.0"
    ]
    print(f"[Demo] Starting REST Order Service on port 8000 (timeout = 2.0s)...")
    order_proc = subprocess.Popen(order_cmd, cwd=str(PROJECT_ROOT))

    try:
        print("[Demo] Waiting for services to become healthy...")
        if not wait_for_service("http://127.0.0.1:8001/health", 8):
            raise RuntimeError("Inventory service failed to start on port 8001")
        if not wait_for_service("http://127.0.0.1:8000/health", 8):
            raise RuntimeError("Order service failed to start on port 8000")
        print("[Demo] Both REST services are UP and HEALTHY!\n")

        # 3. Run Client Test Suite
        client_cmd = [str(PYTHON_BIN), str(PROJECT_ROOT / "rest" / "client.py"), "--suite"]
        subprocess.run(client_cmd, cwd=str(PROJECT_ROOT), check=True)

    finally:
        print("\n[Demo] Cleaning up service processes...")
        order_proc.terminate()
        inv_proc.terminate()
        order_proc.wait(timeout=3)
        inv_proc.wait(timeout=3)
        print("[Demo] REST Services stopped cleanly.")


if __name__ == "__main__":
    main()
