#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping backend..."
    # Kill the backend process group
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
}

trap cleanup EXIT INT TERM

# Start backend
echo "Starting backend (search-ads web)..."
search-ads web &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 2

# Start frontend
echo "Starting frontend (npm run dev)..."
cd frontend
npm run dev
