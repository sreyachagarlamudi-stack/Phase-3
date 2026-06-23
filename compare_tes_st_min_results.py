"""
Compare results after both optimization runs complete
Run this after you have both baseline and test results
"""

import json

output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis"
baseline_file = f"{output_dir}/baseline_40pct_results.json"
test_file = f"{output_dir}/test_25pct_results.json"
comparison_file = f"{output_dir}/tes_st_min_sensitivity_comparison.json"

# Load results (update these paths to match your actual output files)
try:
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)
    with open(test_file, 'r') as f:
        test = json.load(f)

    # Extract key metrics (adjust field names to match actual output)
    baseline_lcoe = baseline.get('lcoe_MWh', 0)
    test_lcoe = test.get('lcoe_MWh', 0)

    delta_MWh = test_lcoe - baseline_lcoe
    delta_pct = (delta_MWh / baseline_lcoe * 100) if baseline_lcoe > 0 else 0

    print("="*80)
    print("TES STEAM TURBINE MINIMUM LOAD - RESULTS COMPARISON")
    print("="*80)
    print()

    print("BASELINE (tes_st_min = 40%):")
    print(f"  LCOE: ${baseline_lcoe:.2f}/MWh")
    print()

    print("TEST (tes_st_min = 25%):")
    print(f"  LCOE: ${test_lcoe:.2f}/MWh")
    print()

    print("DELTA:")
    print(f"  Absolute: ${delta_MWh:.2f}/MWh")
    print(f"  Relative: {delta_pct:.1f}%")
    print()

    if abs(delta_MWh) >= 3 and abs(delta_MWh) <= 5:
        print("✓ Result matches expected range ($3-4/MWh savings)")
    else:
        print(f"⚠️  Result outside expected range (expected: $3-4/MWh, got: ${abs(delta_MWh):.2f}/MWh)")
    print()

    # Update comparison template
    with open(comparison_file, 'r') as f:
        comp = json.load(f)

    comp['baseline']['lcoe_MWh'] = baseline_lcoe
    comp['test']['lcoe_MWh'] = test_lcoe
    comp['comparison']['lcoe_delta_MWh'] = delta_MWh
    comp['comparison']['lcoe_delta_percent'] = delta_pct

    with open(comparison_file, 'w') as f:
        json.dump(comp, f, indent=2)

    print(f"✓ Updated: {comparison_file}")

except FileNotFoundError as e:
    print("Error: Result files not found")
    print("  Make sure both optimization runs have completed")
    print("  Expected files:")
    print(f"    - {baseline_file}")
    print(f"    - {test_file}")
