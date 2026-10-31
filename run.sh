#!/bin/bash

# LoyalPay Run Script
# Usage: ./run.sh [backend|frontend|both|test]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[LoyalPay]${NC} $1"
}

print_error() {
    echo -e "${RED}[Error]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

# Activate virtual environment
activate_venv() {
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_status "Activated virtual environment"
    else
        print_warning "Virtual environment not found. Creating..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        print_status "Created and activated virtual environment"
    fi
}

# Run backend
run_backend() {
    activate_venv
    print_status "Starting backend server on http://127.0.0.1:8000"
    print_status "API docs: http://127.0.0.1:8000/docs"
    python -m uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
}

# Run frontend
run_frontend() {
    cd frontend
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    print_status "Starting frontend on http://localhost:5173"
    npm run dev
}

# Run tests
run_tests() {
    activate_venv
    print_status "Running tests..."
    pytest tests/ -v
}

# Main
case "${1:-both}" in
    backend)
        run_backend
        ;;
    frontend)
        run_frontend
        ;;
    both)
        print_status "Starting LoyalPay..."
        print_status "Backend: http://127.0.0.1:8000"
        print_status "Frontend: http://localhost:5173"
        echo ""
        print_warning "Run in separate terminals:"
        echo "  Terminal 1: ./run.sh backend"
        echo "  Terminal 2: ./run.sh frontend"
        echo ""
        print_status "Or run backend now..."
        run_backend
        ;;
    test)
        run_tests
        ;;
    *)
        echo "Usage: ./run.sh [backend|frontend|both|test]"
        exit 1
        ;;
esac
