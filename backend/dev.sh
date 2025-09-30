#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists, if not, copy from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Install/update dependencies
pip install -r requirements.txt --quiet

# Pick a dev port (fallback if 8000 is busy)
PORT=${PORT:-8000}
PORT=$(python - <<'PY'
import socket, os
start=int(os.environ.get('PORT','8000'))
def free(p):
    s=socket.socket();
    try:
        s.bind(('127.0.0.1',p))
        s.close()
        return True
    except OSError:
        return False
p=start
for _ in range(0,50):
    if free(p):
        break
    p+=1
print(p)
PY
)
echo "Starting backend on port $PORT"
uvicorn main:app --host 0.0.0.0 --port $PORT --reload
