#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT"

python -m grpc_tools.protoc \
  -I ./src \
  --python_out=./src \
  --grpc_python_out=./src \
  ./src/grpc/card_generation.proto

python << 'EOF'
import os

grpc_file = './src/grpc/card_generation_pb2_grpc.py'

if os.path.exists(grpc_file):
    with open(grpc_file, 'r') as f:
        content = f.read()

    # ВАЖНО: правильная замена (рукожопие неимоверное)
    content = content.replace(
        'from grpc import card_generation_pb2',
        'from . import card_generation_pb2'
    )

    with open(grpc_file, 'w') as f:
        f.write(content)

    print("Fixed grpc imports")
EOF

echo "Generated gRPC code correctly"