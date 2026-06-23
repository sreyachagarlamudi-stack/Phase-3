#!/bin/bash

# Monitoring script for TES steam turbine sensitivity analysis
# Shows real-time progress of both optimization runs

echo "================================================================================"
echo "TES STEAM TURBINE SENSITIVITY - OPTIMIZATION MONITOR"
echo "================================================================================"
echo ""

ANALYSIS_DIR="/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis"

cd "$ANALYSIS_DIR"

while true; do
    clear
    echo "================================================================================"
    echo "TES STEAM TURBINE SENSITIVITY - OPTIMIZATION MONITOR"
    echo "================================================================================"
    echo ""
    date
    echo ""

    echo "BASELINE OPTIMIZATION (tes_st_min = 40%):"
    echo "--------------------------------------------------------------------------------"
    if [ -f baseline_optimization.log ]; then
        # Extract progress from last line
        BASELINE_PROGRESS=$(tail -1 baseline_optimization.log | grep -oE '[0-9]+%' | tail -1)
        BASELINE_ITER=$(tail -1 baseline_optimization.log | grep -oE '[0-9]+/365' | tail -1)
        BASELINE_OBJ=$(tail -1 baseline_optimization.log | grep -oE 'obj=[0-9,]+' | tail -1)

        if [ -n "$BASELINE_PROGRESS" ]; then
            echo "  Progress: $BASELINE_PROGRESS complete ($BASELINE_ITER)"
            echo "  $BASELINE_OBJ"
        else
            echo "  Status: Running (initializing...)"
        fi

        # Check if completed
        if grep -q "BASELINE OPTIMIZATION COMPLETE" baseline_optimization.log; then
            echo "  ✓ COMPLETE!"
            echo ""
            echo "  Results saved to:"
            echo "    - baseline_40pct_results.json"
            echo "    - baseline_40pct_dispatch.csv"
        fi
    else
        echo "  Status: Not started"
    fi
    echo ""

    echo "TEST OPTIMIZATION (tes_st_min = 25%):"
    echo "--------------------------------------------------------------------------------"
    if [ -f test_optimization.log ]; then
        # Extract progress from last line
        TEST_PROGRESS=$(tail -1 test_optimization.log | grep -oE '[0-9]+%' | tail -1)
        TEST_ITER=$(tail -1 test_optimization.log | grep -oE '[0-9]+/365' | tail -1)
        TEST_OBJ=$(tail -1 test_optimization.log | grep -oE 'obj=[0-9,]+' | tail -1)

        if [ -n "$TEST_PROGRESS" ]; then
            echo "  Progress: $TEST_PROGRESS complete ($TEST_ITER)"
            echo "  $TEST_OBJ"
        else
            echo "  Status: Running (initializing...)"
        fi

        # Check if completed
        if grep -q "TEST OPTIMIZATION COMPLETE" test_optimization.log; then
            echo "  ✓ COMPLETE!"
            echo ""
            echo "  Results saved to:"
            echo "    - test_25pct_results.json"
            echo "    - test_25pct_dispatch.csv"
        fi
    else
        echo "  Status: Not started"
    fi
    echo ""

    echo "================================================================================"

    # Check if both complete
    BASELINE_DONE=false
    TEST_DONE=false

    if [ -f baseline_optimization.log ]; then
        if grep -q "BASELINE OPTIMIZATION COMPLETE" baseline_optimization.log; then
            BASELINE_DONE=true
        fi
    fi

    if [ -f test_optimization.log ]; then
        if grep -q "TEST OPTIMIZATION COMPLETE" test_optimization.log; then
            TEST_DONE=true
        fi
    fi

    if [ "$BASELINE_DONE" = true ] && [ "$TEST_DONE" = true ]; then
        echo ""
        echo "✓✓✓ BOTH OPTIMIZATIONS COMPLETE! ✓✓✓"
        echo ""
        echo "Next step: Run comparison script"
        echo "  python3 compare_tes_st_min_results.py"
        echo ""
        break
    fi

    echo ""
    echo "Refreshing every 5 seconds... (Ctrl+C to exit)"
    echo ""

    sleep 5
done
