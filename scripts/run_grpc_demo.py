#!/usr/bin/env python3
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PYTHON_BIN = PROJECT_ROOT / "venv" / "bin" / "python"
if not PYTHON_BIN.exists():
    PYTHON_BIN = sys.executable


def wait_for_port(host, port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (ConnectionRefemptedError := ConnectionRefusedError, socket.timeout, OSError):
            pass
        time.sleep(0.3)
    return False


def main():
    print("=" * 70)
    print("  LAUNCHING gRPC SERVICES DEMONSTRATION")
    print("=" * 70)

    # 1. Start gRPC Inventory Service
    inv_cmd = [str(PYTHON_BIN), str(PROJECT_ROOT / "grpc_service" / "inventory_service.py"), "--port", "50051"]
    print(f"[Demo] Starting gRPC Inventory Service on port 50051...")
    inv_proc = subprocess.Popen(inv_cmd, cwd=str(PROJECT_ROOT))

    # 2. Start gRPC Order Service
    order_cmd = [
        str(PYTHON_BIN),
        str(PROJECT_ROOT / "grpc_service" / "order_service.py"),
        "--port", "50052",
        "--inventory-target", "localhost:50051",
        "--deadline", "2.0",
        "--http-port", "5002"
    ]
    print(f"[Demo] Starting gRPC Order Service on port 50052 (deadline = 2.0s)...")
    order_proc = subprocess.Popen(order_cmd, cwd=str(PROJECT_ROOT))

    try:
        print("[Demo] Waiting for gRPC services to listen...")
        if not wait_for_port("127.0.0.1", 50051, 8):
            raise RuntimeError("gRPC Inventory service failed to listen on port 50051")
        if not wait_for_port("127.0.0.1", 50052, 8):
            raise RuntimeError("gRPC Order service failed to listen on port 50052")
        print("[Demo] Both gRPC services are UP and LISTENING!\n")

        # 3. Run gRPC Client Test Suite
        client_cmd = [str(PYTHON_BIN), str(PROJECT_ROOT / "grpc_service" / "client.py"), "--suite"]
        subprocess.run(client_cmd, cwd=str(PROJECT_ROOT), check=True)

    finally:
        print("\n[Demo] Cleaning up gRPC service processes...")
        order_proc.terminate()
        inv_proc.terminate()
        order_proc.wait(timeout=3)
        inv_proc.wait(timeout=3)
        print("[Demo] gRPC Services stopped cleanly.")


if __name__ == "__main__":
    main()
