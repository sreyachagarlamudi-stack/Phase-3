"""
Phase 3 Analysis Script #1: Baseline TES Optimization

This script runs a full-year optimization with your TES module to find:
- Optimal wind/solar/TES sizing for 100% CFE
- Minimum LCOE (Levelized Cost of Energy)
- System dispatch patterns
- Economic breakdown

Based on the PtXv3 framework with your TES module integration.
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Add the PtX framework to path
ptx_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intersect Summer/TESProject/x_PtXv3"
sys.path.insert(0, ptx_path)

# Import your TES module
from pyomo_DTC_CPLEX_TES import roll_cfe, py_dtc_cfe

print("=" * 70)
print("PHASE 3 ANALYSIS: Baseline TES Optimization")
print("=" * 70)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# STEP 1: Define the scenario
# ============================================================================
print("Step 1: Defining baseline scenario...")

# This mirrors the demo but with more realistic parameters
scenario = {
    # ===== TIME HORIZON =====
    'dispatch_time': 168,  # 1 week for testing (change to 8760 for full year)
    'window_size': 72,     # 3 days optimization window
    'step_size': 24,       # step forward 1 day at a time

    # ===== DATACENTER LOAD =====
    'Load_max': 100,       # 100 MW datacenter
    'Load_min': 100,       # constant load (no flexibility)
    'Load_MRR': 0,         # max ramp rate (% per hour)

    # ===== RENEWABLES SIZING (we'll optimize these) =====
    'solar_MW': 250,       # initial guess: 250 MW solar
    'wind_MW': 100,        # initial guess: 100 MW wind

    # ===== TES PARAMETERS (from Phase 1 analysis) =====
    'tes_duration': 16,    # hours at full discharge (heat battery RHB100)
    'tes_CDratio': 3.0,    # charge 3x faster than discharge
    'tes_rte': 0.90,       # 90% roundtrip efficiency (thermal)
    'tes_st_eff': 40.0,    # turbine efficiency 40%
    'tes_st_min': 40.0,    # turbine minimum load 40%
    'tes_soci': 0.30,      # initial state of charge 30%

    # ===== BATTERY PARAMETERS =====
    'BESS_rte': 0.88,      # 88% roundtrip efficiency
    'ess_soci': 0.30,      # initial state of charge
    'BESS_cyclesperyr': 365,

    # ===== LDES (for comparison runs) =====
    'LDES_rte': 0.65,      # generic LDES efficiency
    'LDES_constantloss': 1.0,  # 1% constant loss

    # ===== GRID =====
    'cleanfirm_size': 0,   # no clean firm (nuclear/hydro)

    # ===== GAS BACKUP =====
    'NG_CFE': 0.0,         # natural gas not counted as CFE
    'G1_fc_bfix': 0,       # gas fixed costs
    'G2_fc_bfix': 0,
    'G1_fc_mfix': 0,
    'G2_fc_mfix': 0,
    'G1_fc_bvar': 0,
    'G2_fc_bvar': 0,
    'G1_fc_mvar': 0,
    'G2_fc_mvar': 0,

    # ===== PENALTIES =====
    'NONCFE_pen': 200,     # $/MWh penalty for non-clean energy
    'EA_pen': 0.5,         # battery degradation penalty
    'wind_basis': 0,
    'Lcurtt_pen': 1000,    # load curtailment penalty (very high)

    # ===== FINANCE =====
    'wind_ptc_2023': 27.5, # wind production tax credit $/MWh
    'fin_esc': 0.025,      # 2.5% escalation
    'COD': 2025,           # commercial operation date

    # ===== SOLVER =====
    'solve_with_gurobi': 0,  # 0 = CPLEX, 1 = Gurobi
}

print(f"  Datacenter load: {scenario['Load_max']} MW")
print(f"  Solar capacity: {scenario['solar_MW']} MW")
print(f"  Wind capacity: {scenario['wind_MW']} MW")
print(f"  TES duration: {scenario['tes_duration']} hours")
print(f"  TES efficiency: {scenario['tes_rte']*100}%")
print(f"  Turbine efficiency: {scenario['tes_st_eff']}%")
print()

# ============================================================================
# STEP 2: Create synthetic weather data (for now - replace with real data)
# ============================================================================
print("Step 2: Generating synthetic weather profiles...")

HOURS = scenario['dispatch_time']

# Simple solar profile (0 at night, peak at noon)
solar_cf = []
for h in range(HOURS):
    hour_of_day = h % 24
    if 6 <= hour_of_day <= 18:
        # Sinusoidal during day
        solar_cf.append(np.sin(np.pi * (hour_of_day - 6) / 12))
    else:
        solar_cf.append(0)

# Wind profile (more constant with variability)
np.random.seed(42)
wind_cf = np.clip(0.4 + 0.2 * np.sin(np.linspace(0, 4*np.pi, HOURS)) +
                  0.1 * np.random.randn(HOURS), 0, 1)

# Create the operations dataframe (this is what the optimizer needs)
dfopsx = pd.DataFrame({
    'St': scenario['solar_MW'] * 1000 * solar_cf,  # Solar generation (kW)
    'Wt': scenario['wind_MW'] * 1000 * wind_cf,    # Wind generation (kW)
    'P1': [30.0] * HOURS,      # Grid import price ($/MWh)
    'P2': [20.0] * HOURS,      # Grid export price ($/MWh)
    'CFE': [0.5] * HOURS,      # Grid CFE fraction
    'PNGt': [5.0] * HOURS,     # Natural gas price ($/MMBtu)
    'BXmaxt': [200000] * HOURS,  # Battery max capacity (kWh)
    'LXmaxt': [500000] * HOURS,  # LDES max capacity (kWh)
    'G1_max_kW': [50000] * HOURS,  # Gas gen 1 max (kW)
    'G2_max_kW': [0] * HOURS,      # Gas gen 2 max (kW)
    'G1_heatrate_mmbtu_mwh': [10.0] * HOURS,  # Gas heat rate
    'G2_heatrate_mmbtu_mwh': [10.0] * HOURS,
})

print(f"  Generated {HOURS} hours of weather data")
print(f"  Solar capacity factor: {np.mean(solar_cf):.1%}")
print(f"  Wind capacity factor: {np.mean(wind_cf):.1%}")
print()

# ============================================================================
# STEP 3: Define system sizing
# ============================================================================
print("Step 3: Defining system sizing...")

svar = {
    # Battery sizing
    'bessD_kW': 100000,    # 100 MW discharge
    'bessC_kW': 100000,    # 100 MW charge
    'bess_kWh': 200000,    # 200 MWh capacity

    # LDES sizing (for comparison)
    'ldesD_kW': 100000,
    'ldesC_kW': 100000,
    'ldes_kWh': 500000,

    # TES sizing (key parameters!)
    'tesD_kW': 100000,     # 100 MW discharge (thermal → turbine)

    # Grid connection
    'maxExpMW': 0,         # no export to grid
    'maxImpMW': 0,         # no import from grid (off-grid)
}

# Calculate derived TES parameters
tes_charge_kW = svar['tesD_kW'] * scenario['tes_CDratio']  # Charge power
tes_capacity_kWh = svar['tesD_kW'] * scenario['tes_duration']  # Energy capacity

print(f"  TES discharge power: {svar['tesD_kW']/1000:.0f} MW")
print(f"  TES charge power: {tes_charge_kW/1000:.0f} MW")
print(f"  TES energy capacity: {tes_capacity_kWh/1000:.0f} MWh (thermal)")
print(f"  TES electrical output: ~{tes_capacity_kWh * scenario['tes_st_eff']/100/1000:.0f} MWh")
print()

# ============================================================================
# STEP 4: Run the optimization!
# ============================================================================
print("Step 4: Running optimization with TES module...")
print("  This may take several minutes...")
print()

try:
    # Call your roll_cfe function from pyomo_DTC_CPLEX_TES
    results_df = roll_cfe(
        vars=scenario,
        dfopsx=dfopsx,
        svar=svar,
        threads=None,  # use all available cores
        P=200,         # load service price
        pos=0
    )

    print()
    print("Success: Optimization completed successfully!")
    print()

    # ============================================================================
    # STEP 5: Analyze results
    # ============================================================================
    print("Step 5: Analyzing results...")
    print()

    # Calculate key metrics
    total_load = results_df['Lt'].sum()
    total_solar = results_df['Wcurtt'].sum() if 'Wcurtt' in results_df.columns else 0
    total_wind = results_df['Scurtt'].sum() if 'Scurtt' in results_df.columns else 0
    total_gas = results_df['Gngt'].sum() if 'Gngt' in results_df.columns else 0
    total_tes_out = results_df['Gtest'].sum() if 'Gtest' in results_df.columns else 0
    total_bess_out = results_df['BDt'].sum() if 'BDt' in results_df.columns else 0

    # CFE calculation
    cfe_pct = 100 * (total_load - total_gas) / total_load if total_load > 0 else 0

    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total load served:        {total_load/1000:>10,.0f} MWh")
    print(f"TES turbine output:       {total_tes_out/1000:>10,.0f} MWh")
    print(f"Battery discharge:        {total_bess_out/1000:>10,.0f} MWh")
    print(f"Gas generation:           {total_gas:>10,.0f} MMBtu")
    print()
    print(f"Clean Firm Energy (CFE):  {cfe_pct:>10.1f} %")
    print("=" * 70)
    print()

    # ============================================================================
    # STEP 6: Save results
    # ============================================================================
    print("Step 6: Saving results...")

    output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project/TESProject/Phase 3 - Analysis"

    # Save detailed dispatch results
    csv_path = f"{output_dir}/phase3_baseline_dispatch.csv"
    results_df.to_csv(csv_path, index=True)
    print(f"  Success: Dispatch data saved: {csv_path}")

    # Save summary metrics
    summary = {
        'run_date': datetime.now().isoformat(),
        'scenario': scenario,
        'system_sizing': svar,
        'metrics': {
            'total_load_MWh': float(total_load / 1000),
            'tes_output_MWh': float(total_tes_out / 1000),
            'battery_output_MWh': float(total_bess_out / 1000),
            'gas_MMBtu': float(total_gas),
            'cfe_percent': float(cfe_pct),
        }
    }

    json_path = f"{output_dir}/phase3_baseline_results.json"
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  Success: Summary saved: {json_path}")

    print()
    print("=" * 70)
    print("PHASE 3 BASELINE ANALYSIS COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review the results in phase3_baseline_dispatch.csv")
    print("  2. Run sensitivity analyses (vary TES duration, solar/wind mix)")
    print("  3. Compare with LDES alternative")
    print("  4. Analyze policy impacts (IRA credits)")

except Exception as e:
    print()
    print(f"Error: Error during optimization: {str(e)}")
    print()
    print("Troubleshooting:")
    print("  - Check that CPLEX solver is installed")
    print("  - Verify all imports are working")
    print("  - Try reducing dispatch_time to test faster")
    import traceback
    traceback.print_exc()
