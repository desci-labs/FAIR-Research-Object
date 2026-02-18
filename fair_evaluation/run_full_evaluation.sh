#!/bin/bash
#
# Full FAIR Evaluation Script
# ============================
#
# This script runs the complete before/after FAIR evaluation for dev and prod.
# 
# Prerequisites:
#   - F-UJI server installed and configured
#   - Node.js/npm for nodes repo
#   - pnpm for dpid-resolver
#
# Usage:
#   ./run_full_evaluation.sh dev    # Run only dev
#   ./run_full_evaluation.sh prod   # Run only prod
#   ./run_full_evaluation.sh all    # Run both (default)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESCI_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

NODES_DIR="$DESCI_ROOT/nodes"
RESOLVER_DIR="$DESCI_ROOT/dpid-resolver"
FUJI_DIR="$DESCI_ROOT/fuji"
RESULTS_DIR="$SCRIPT_DIR/results"

# Git commits for before state
NODES_BEFORE_COMMIT="6a9b66370a046f257b987e24f9916d973cb536ed"
RESOLVER_BEFORE_COMMIT="1710783ea6e8b20699c01cc84c0e9eed58692790"
FUJI_BEFORE_COMMIT="18b213b"   # Before dPID/IPFS recognition
FUJI_AFTER_COMMIT="ee97605"    # With dPID/IPFS recognition

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_status() {
    echo -e "${GREEN}[STATUS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create results directory
mkdir -p "$RESULTS_DIR"

# Check what to run
RUN_ENV="${1:-all}"

start_fuji() {
    echo_status "Starting F-UJI server..."
    cd "$FUJI_DIR"
    
    # Kill any existing
    pkill -f fuji_server 2>/dev/null || true
    sleep 2
    
    # Start in background
    source venv/bin/activate
    python -m fuji_server -c fuji_server/config/server.ini &
    FUJI_PID=$!
    
    # Wait for startup
    echo_status "Waiting for F-UJI to start..."
    sleep 10
    
    # Check if running
    if curl -s http://localhost:1071/fuji/api/v1/ > /dev/null 2>&1; then
        echo_status "F-UJI server started (PID: $FUJI_PID)"
    else
        echo_error "F-UJI failed to start"
        exit 1
    fi
}

stop_fuji() {
    echo_status "Stopping F-UJI server..."
    pkill -f fuji_server 2>/dev/null || true
}

checkout_before() {
    echo_status "Checking out 'before' state..."
    
    # Save current branches
    cd "$NODES_DIR"
    NODES_CURRENT=$(git branch --show-current || git rev-parse HEAD)
    
    cd "$RESOLVER_DIR"
    RESOLVER_CURRENT=$(git branch --show-current || git rev-parse HEAD)
    
    cd "$FUJI_DIR"
    FUJI_CURRENT=$(git branch --show-current || git rev-parse HEAD)
    
    # Checkout before commits
    cd "$NODES_DIR"
    git stash 2>/dev/null || true
    git checkout "$NODES_BEFORE_COMMIT"
    
    cd "$RESOLVER_DIR"
    git stash 2>/dev/null || true
    git checkout "$RESOLVER_BEFORE_COMMIT"
    
    cd "$FUJI_DIR"
    git stash 2>/dev/null || true
    git checkout "$FUJI_BEFORE_COMMIT"
    
    echo_status "Checked out before commits (nodes, resolver, fuji)"
}

checkout_after() {
    echo_status "Checking out 'after' state..."
    
    cd "$NODES_DIR"
    git checkout "$NODES_CURRENT" 2>/dev/null || git checkout main || git checkout master
    git stash pop 2>/dev/null || true
    
    cd "$RESOLVER_DIR"
    git checkout "$RESOLVER_CURRENT" 2>/dev/null || git checkout main || git checkout master
    git stash pop 2>/dev/null || true
    
    cd "$FUJI_DIR"
    git checkout "$FUJI_AFTER_COMMIT" 2>/dev/null || git checkout "$FUJI_CURRENT" || git checkout master
    git stash pop 2>/dev/null || true
    
    echo_status "Checked out after state (nodes, resolver, fuji)"
}

restart_fuji() {
    echo_status "Restarting F-UJI server with current code..."
    
    # Kill any existing F-UJI
    pkill -f fuji_server 2>/dev/null || true
    sleep 2
    
    # Start F-UJI
    cd "$FUJI_DIR"
    source venv/bin/activate
    python -m fuji_server -c fuji_server/config/server.ini &
    FUJI_PID=$!
    
    # Wait for startup
    sleep 10
    
    # Verify
    if curl -s http://localhost:1071/fuji/api/v1/ > /dev/null 2>&1; then
        echo_status "F-UJI server restarted (PID: $FUJI_PID)"
    else
        echo_warning "F-UJI may not have started properly"
    fi
}

build_and_test() {
    local state=$1
    local env=$2
    
    echo_status "Building desci-models..."
    cd "$NODES_DIR/desci-models"
    npm run build 2>&1 | tail -3
    
    # Restart F-UJI with current code version
    restart_fuji
    
    echo_status "Testing single dPID ($env, $state state)..."
    cd "$SCRIPT_DIR"
    python evaluate_fair_scores.py --env "$env" --state "$state" --start-dpid 46 --end-dpid 46 --timeout 120
    
    if [ $? -eq 0 ]; then
        echo_status "Single dPID test passed!"
        return 0
    else
        echo_error "Single dPID test failed!"
        return 1
    fi
}

run_full_evaluation() {
    local state=$1
    local env=$2
    
    echo_status "Running full evaluation ($env, $state)..."
    cd "$SCRIPT_DIR"
    python evaluate_fair_scores.py \
        --env "$env" \
        --state "$state" \
        --workers 5 \
        --timeout 90 \
        --output "results/${env}_${state}.json"
}

generate_histograms() {
    local env=$1
    
    echo_status "Generating histograms for $env..."
    cd "$SCRIPT_DIR"
    python generate_histogram.py --env "$env"
}

# Main execution
echo "============================================================"
echo "FAIR Score Distribution Evaluation"
echo "============================================================"
echo "DeSci Root: $DESCI_ROOT"
echo "Running for: $RUN_ENV"
echo "============================================================"

# Start F-UJI
start_fuji

# Trap to cleanup on exit
trap "stop_fuji" EXIT

if [ "$RUN_ENV" = "dev" ] || [ "$RUN_ENV" = "all" ]; then
    echo ""
    echo "============================================================"
    echo "EVALUATING DEV ENVIRONMENT"
    echo "============================================================"
    
    # Before state
    echo ""
    echo "--- BEFORE STATE ---"
    checkout_before
    if build_and_test "before" "dev"; then
        run_full_evaluation "before" "dev"
    fi
    
    # After state
    echo ""
    echo "--- AFTER STATE ---"
    checkout_after
    if build_and_test "after" "dev"; then
        run_full_evaluation "after" "dev"
    fi
    
    # Generate comparison
    generate_histograms "dev"
fi

if [ "$RUN_ENV" = "prod" ] || [ "$RUN_ENV" = "all" ]; then
    echo ""
    echo "============================================================"
    echo "EVALUATING PROD ENVIRONMENT"
    echo "============================================================"
    
    # Before state
    echo ""
    echo "--- BEFORE STATE ---"
    checkout_before
    if build_and_test "before" "prod"; then
        run_full_evaluation "before" "prod"
    fi
    
    # After state
    echo ""
    echo "--- AFTER STATE ---"
    checkout_after
    if build_and_test "after" "prod"; then
        run_full_evaluation "after" "prod"
    fi
    
    # Generate comparison
    generate_histograms "prod"
fi

echo ""
echo "============================================================"
echo "EVALUATION COMPLETE"
echo "============================================================"
echo "Results saved in: $RESULTS_DIR"
ls -la "$RESULTS_DIR"

