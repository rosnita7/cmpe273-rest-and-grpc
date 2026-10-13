#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "Compiling protocol buffer definitions from grpc_service/inventory.proto..."
./venv/bin/python -m grpc_tools.protoc \
    -I grpc_service \
    --python_out=grpc_service \
    --grpc_python_out=grpc_service \
    --pyi_out=grpc_service \
    grpc_service/inventory.proto

echo "Protobuf files compiled successfully into grpc_service/"
