# CMPE 273 - REST and gRPC Service Implementation

This repository contains the implementation of a distributed ordering system comprising two services:
- **Order Service**: Accepts customer orders containing an `item_id` and `quantity`.
- **Inventory Service**: Checks whether the requested item and quantity are available in stock.

The communication from **Order Service → Inventory Service** is implemented in two ways:
1. **REST / HTTP** (JSON over HTTP, HTTP status codes, configurable request timeout)
2. **gRPC** (Protocol Buffers over HTTP/2, rich RPC status codes, configurable call deadline)

Both versions implement the same core business contract and demonstrate graceful failure handling when the Inventory Service responds too slowly.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |               Client                  |
                      +---------------------------------------+
                                   |              |
                      (HTTP POST)  |              |  (gRPC / Client CLI)
                                   v              v
                  +--------------------+     +--------------------+
                  | REST Order Service |     | gRPC Order Service |
                  |    (Port 8000)     |     |   (Port 50052)     |
                  +--------------------+     +--------------------+
                            |                          |
               HTTP GET     |                          |  gRPC CheckStock()
             (Timeout=2.0s) |                          |  (Deadline=2.0s)
                            v                          v
                +------------------------+  +------------------------+
                | REST Inventory Service |  | gRPC Inventory Service |
                |      (Port 8001)       |  |      (Port 50051)      |
                +------------------------+  +------------------------+
```

### Mock Inventory Catalog
Both services share the following mock catalog:
- `item_1`: **Laptop** (Stock: 10, Price: $999.99)
- `item_2`: **Wireless Mouse** (Stock: 3, Price: $29.99)
- `item_3`: **Mechanical Keyboard** (Stock: 0, Price: $89.99 - Out of stock)
- `item_4`: **USB-C Hub** (Stock: 50, Price: $45.00)

---

## Repository Structure

```
cmpe273-rest-and-grpc/
├── README.md                      # Comprehensive lab report and documentation
├── requirements.txt               # Python package dependencies
├── .gitignore                     # Git ignore rules for venv, caches, logs
├── rest/                          # REST/HTTP Implementation
│   ├── inventory_service.py       # REST Inventory Service (Port 8001)
│   ├── order_service.py           # REST Order Service (Port 8000, Timeout: 2.0s)
│   └── client.py                  # CLI test client for REST endpoints
├── grpc_service/                  # gRPC Implementation
│   ├── inventory.proto            # Protobuf service contract definition
│   ├── inventory_service.py       # gRPC Inventory Server (Port 50051)
│   ├── order_service.py           # gRPC Order Service (Port 50052, Deadline: 2.0s)
│   ├── client.py                  # CLI test client for gRPC endpoints
│   ├── inventory_pb2.py           # Generated Python protobuf classes
│   ├── inventory_pb2_grpc.py      # Generated Python gRPC stubs
│   └── inventory_pb2.pyi          # Type annotations for protobuf classes
└── scripts/
    ├── generate_protos.sh         # Helper to compile protobufs
    ├── run_rest_demo.py           # Automated end-to-end test runner for REST
    └── run_grpc_demo.py           # Automated end-to-end test runner for gRPC
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.9+ (Python 3.12 recommended)
- `pip` and `virtualenv`

### 2. Create Virtual Environment and Install Dependencies
```bash
# Clone the repository
git clone <repo-url>
cd cmpe273-rest-and-grpc

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Recompile Protobuf Files
If you make modifications to `grpc_service/inventory.proto`, regenerate the stubs by running:
```bash
./scripts/generate_protos.sh
```

---

## Instructions for Running the REST Version

### Automated One-Command Demo
You can run the entire REST test suite with a single command:
```bash
./venv/bin/python scripts/run_rest_demo.py
```
This automatically starts both services, runs tests (successful order, insufficient stock, not found, slow inventory timeout, and post-failure recovery), prints live logs, and terminates cleanly.

### Running Manually

#### Step 1: Start the REST Inventory Service
In Terminal 1:
```bash
./venv/bin/python rest/inventory_service.py --port 8001
```

#### Step 2: Start the REST Order Service
In Terminal 2 (configured with a 2.0-second timeout):
```bash
./venv/bin/python rest/order_service.py --port 8000 --inventory-url http://127.0.0.1:8001 --timeout 2.0
```

#### Step 3: Run Requests
You can send orders using `curl` or using the provided test client:

```bash
# Using curl:
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item_1", "quantity": 2}'

# Or using the REST client CLI:
./venv/bin/python rest/client.py --item item_1 --quantity 2

# Run full automated suite on running services:
./venv/bin/python rest/client.py --suite
```

---

## Instructions for Running the gRPC Version

### Automated One-Command Demo
You can run the entire gRPC test suite with a single command:
```bash
./venv/bin/python scripts/run_grpc_demo.py
```
This automatically launches both gRPC servers, runs the test suite, prints live server logs and client outputs, and terminates cleanly.

### Running Manually

#### Step 1: Start the gRPC Inventory Service
In Terminal 1:
```bash
./venv/bin/python grpc_service/inventory_service.py --port 50051
```

#### Step 2: Start the gRPC Order Service
In Terminal 2 (configured with a 2.0-second gRPC deadline):
```bash
./venv/bin/python grpc_service/order_service.py --port 50052 --inventory-target localhost:50051 --deadline 2.0
```

#### Step 3: Run Requests
You can interact with the gRPC Order Service using the provided client:

```bash
# Place an order for 2 units of item_1:
./venv/bin/python grpc_service/client.py --item item_1 --quantity 2

# Check inventory directly via gRPC:
./venv/bin/python grpc_service/client.py --item item_1 --quantity 2 --direct-inventory

# Run full automated test suite:
./venv/bin/python grpc_service/client.py --suite
```

*(Note: The gRPC Order Service also runs an HTTP bridge on port `5002` allowing `curl -X POST http://127.0.0.1:5002/orders -H "Content-Type: application/json" -d '{"item_id": "item_1", "quantity": 2}'`)*

---

## Evidence of Successful Requests and Responses

### 1. Example of a Successful REST Request and Response

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item_1", "quantity": 2}'
```

**Response (HTTP 201 Created):**
```json
{
  "item_id": "item_1",
  "item_name": "Laptop",
  "message": "Order placed successfully",
  "order_id": "ord-e34e9efa",
  "quantity": 2,
  "status": "CONFIRMED",
  "total_price": 1999.98
}
```

**Terminal Server Logs:**
```
[Order-REST] Processing order request: item_id='item_1', quantity=2, simulate_delay=0.0s
[Order-REST] Calling Inventory Service at http://127.0.0.1:8001/inventory/item_1 (configured timeout: 2.0s)...
[Inventory-REST] Stock check SUCCESS for 'item_1': requested 2, available 10
[Inventory-REST] 127.0.0.1 - - "GET /inventory/item_1?quantity=2 HTTP/1.1" 200 -
[Order-REST] Inventory Service responded with HTTP 200: {'available': True, 'item_id': 'item_1', 'message': 'Item is available in requested quantity', 'name': 'Laptop', 'price': 999.99, 'requested_quantity': 2, 'stock': 10}
[Order-REST] Order created successfully: order_id=ord-e34e9efa, total=$1999.98
[Order-REST] 127.0.0.1 - - "POST /orders HTTP/1.1" 201 -
```

---

### 2. Example of a Successful gRPC Request and Response

**Request:**
```bash
./venv/bin/python grpc_service/client.py --item item_1 --quantity 2
```

**Client Output:**
```
[Client] Sending gRPC CreateOrder to localhost:50052
[Client] Request: item_id='item_1', quantity=2, delay=0.0s
[Client] Call succeeded in 0.01s!
[Client] Response: status=CONFIRMED, order_id=ord-grpc-ca128ee9, total_price=$1999.98, message='Order placed successfully via gRPC'
```

**Terminal Server Logs:**
```
[Order-gRPC] Received CreateOrder: item_id='item_1', quantity=2, simulate_delay=0.0s
[Order-gRPC] Calling InventoryService.CheckStock for 'item_1' with gRPC deadline=2.0s...
[Inventory-gRPC] Received CheckStock request: item_id='item_1', quantity=2
[Inventory-gRPC] Stock check SUCCESS for 'item_1': requested 2, available 10
[Order-gRPC] Order created successfully: order_id=ord-grpc-ca128ee9, total=$1999.98
```

---

## Failure Handling: Slow Inventory Response

To demonstrate timeout and deadline handling, a simulated delay is introduced to the Inventory Service that is greater than the configured timeout/deadline (`4.0s delay > 2.0s timeout/deadline`).

### 1. Evidence of REST Timeout Handling

**Request (with 4.0s delay):**
```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item_1", "quantity": 1, "delay": 4.0}'
```

**Response (HTTP 504 Gateway Timeout after exactly 2.01s):**
```json
{
  "error": "Gateway Timeout",
  "item_id": "item_1",
  "message": "Inventory service timed out after 2.0s limit.",
  "quantity": 1,
  "status": "FAILED"
}
```

**Terminal Server Logs:**
```
[Order-REST] Processing order request: item_id='item_1', quantity=1, simulate_delay=4.0s
[Order-REST] Calling Inventory Service at http://127.0.0.1:8001/inventory/item_1 (configured timeout: 2.0s)...
[Inventory-REST] Simulating slow response: sleeping for 4.00s before responding to check for 'item_1'
[Order-REST] ERROR: TIMEOUT EXCEEDED: Inventory Service failed to respond within 2.0s for item 'item_1'. Order aborted.
[Order-REST] 127.0.0.1 - - "POST /orders HTTP/1.1" 504 -
```

**Analysis:**
The REST Order Service cleanly caught `requests.exceptions.Timeout`, prevented the thread from blocking indefinitely, logged the error, and returned a standard `HTTP 504 Gateway Timeout` status code.

---

### 2. Evidence of gRPC Deadline Handling

**Request (with 4.0s delay):**
```bash
./venv/bin/python grpc_service/client.py --item item_1 --quantity 1 --delay 4.0
```

**Client Output:**
```
[Client] Sending gRPC CreateOrder to localhost:50052
[Client] Request: item_id='item_1', quantity=1, delay=4.0s
[Order-gRPC] Calling InventoryService.CheckStock for 'item_1' with gRPC deadline=2.0s...
[Inventory-gRPC] Simulating slow response: sleeping for 4.00s before responding to CheckStock for item 'item_1'
[Order-gRPC] ERROR: DEADLINE EXCEEDED: Inventory Service failed to respond within 2.0s for item 'item_1'. Handling error cleanly.
[Client] gRPC call failed in 2.01s with status: StatusCode.DEADLINE_EXCEEDED
[Client] Error details: 'Inventory Service deadline exceeded (2.0s timeout limit)'
```

**Analysis:**
When the Inventory Service exceeded the 2.0-second deadline, gRPC's deadline enforcement triggered immediately. The Order Service caught `grpc.RpcError`, checked `e.code() == grpc.StatusCode.DEADLINE_EXCEEDED`, logged the failure cleanly, and aborted the client RPC with `StatusCode.DEADLINE_EXCEEDED`.

---

## Evidence That Order Service Remains Running After Failures

A critical requirement of distributed systems is resilience: a single slow or failing downstream dependency must not crash or halt upstream services.

### REST Order Service Resilience
Immediately after receiving the HTTP 504 timeout error, a new valid order (`item_4`, quantity: 3) is submitted to the Order Service:

**Post-Failure Order Request:**
```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item_4", "quantity": 3}'
```

**Response (HTTP 201 Created):**
```json
{
  "item_id": "item_4",
  "item_name": "USB-C Hub",
  "message": "Order placed successfully",
  "order_id": "ord-f0430ee5",
  "quantity": 3,
  "status": "CONFIRMED",
  "total_price": 135.0
}
```

**Health Check Evidence (`GET http://127.0.0.1:8000/health`):**
```json
{
  "inventory_url": "http://127.0.0.1:8001",
  "orders_count": 2,
  "service": "order-rest",
  "status": "healthy",
  "timeout_seconds": 2.0
}
```
*Conclusion*: The REST Order Service remained running without restart, processed subsequent requests successfully, and maintained healthy state.

---

### gRPC Order Service Resilience
Immediately after the `DEADLINE_EXCEEDED` failure, a new valid order (`item_4`, quantity: 3) is sent to the gRPC Order Service:

**Post-Failure Order Request:**
```bash
./venv/bin/python grpc_service/client.py --item item_4 --quantity 3
```

**Client Output:**
```
[Client] Sending gRPC CreateOrder to localhost:50052
[Client] Request: item_id='item_4', quantity=3, delay=0.0s
[Order-gRPC] Received CreateOrder: item_id='item_4', quantity=3, simulate_delay=0.0s
[Inventory-gRPC] Stock check SUCCESS for 'item_4': requested 3, available 50
[Order-gRPC] Order created successfully: order_id=ord-grpc-4176099e, total=$135.0
[Client] Call succeeded in 0.01s!
[Client] Response: status=CONFIRMED, order_id=ord-grpc-4176099e, total_price=$135.00, message='Order placed successfully via gRPC'
```
*Conclusion*: The gRPC Order Service thread pool handled the exception cleanly without terminating the server process, and subsequent RPCs executed with low latency (0.01s).

---

## Comparison: REST vs. gRPC

**What differences did you observe between implementing the same service contract using REST and gRPC?**

Implementing the same service contract revealed distinct architectural and operational differences between the two paradigms. First, gRPC enforces a strict, strongly-typed interface via Protocol Buffers that automatically generates client stubs and server servicers, eliminating runtime schema mismatches that often occur with REST's text-based JSON payloads. Second, gRPC provides built-in, first-class deadline propagation across distributed hops using HTTP/2 frames, whereas in REST, timeouts are purely client-side configurations that downstream servers cannot naturally track or inherit. Third, error reporting in gRPC relies on canonical status codes (such as `NOT_FOUND`, `FAILED_PRECONDITION`, and `DEADLINE_EXCEEDED`) accompanied by rich binary metadata, whereas REST requires mapping business exceptions to standard HTTP status codes (400, 404, 504) and custom JSON error bodies. Finally, while REST simplifies ad-hoc debugging and manual testing via browser or `curl`, gRPC offers superior binary serialization efficiency and multiplexing over HTTP/2, making it vastly more suitable for high-throughput inter-service communication.

---

## Summary of Test Results

| Test Scenario | REST Status Code | REST Behavior | gRPC Status Code | gRPC Behavior |
| :--- | :---: | :--- | :---: | :--- |
| **Normal Available Stock** | `201 Created` | Order confirmed, JSON returned | `OK` | Order confirmed, Protobuf returned |
| **Insufficient Stock** | `400 Bad Request` | Clean error JSON with remaining stock | `FAILED_PRECONDITION` | RPC aborted with details |
| **Non-Existent Item** | `404 Not Found` | Clean error JSON: item not found | `NOT_FOUND` | RPC aborted with details |
| **Slow Inventory (Timeout)** | `504 Gateway Timeout` | Caught `requests.exceptions.Timeout` | `DEADLINE_EXCEEDED` | Caught `grpc.RpcError` with `DEADLINE_EXCEEDED` |
| **Service Survival Post-Failure** | `201 Created` | Continues serving requests seamlessly | `OK` | Continues serving requests seamlessly |
