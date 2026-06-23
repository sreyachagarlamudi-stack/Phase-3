"""
PHASE 3: SYSTEM OPTIMIZATION
Find optimal mix of wind, solar, and TES to achieve 100% CFE at lowest LCOE

This script sweeps different system configurations to answer:
1. What is the optimal mix for 100% CFE?
2. How does LCOE vary with different solar/wind/TES ratios?
3. How do TES economics compare to LDES?
4. What is the minimum cost configuration?
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
import itertools

# Add paths
sys.path.insert(0, "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2")
sys.path.insert(0, "/Users/sreyachagarlamudi/Downloads/x_PtXv3-main")

print("="*80)
print("PHASE 3: SYSTEM OPTIMIZATION - Finding Optimal CFE Mix")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# STEP 1: Define Parameter Sweep Ranges
# ============================================================================

print("Step 1: Defining parameter sweep ranges...")

# Load base TES parameters from Excel
excel_file = "/Users/sreyachagarlamudi/Downloads/(PtXv3.4_r0) gjt_working.xlsx"
tes_df = pd.read_excel(excel_file, sheet_name='TES', header=None)
tes_params = {}
for idx, row in tes_df.iterrows():
    param_name = row[0]
    param_value = row[2]
    tes_params[param_name] = param_value

# Define sweep ranges for optimization
LOAD_MW = 100  # Fixed datacenter load

# Solar capacity sweep (MW)
SOLAR_RANGE = [200, 250, 300, 350, 400]

# Wind capacity sweep (MW)
WIND_RANGE = [25, 50, 75, 100]

# TES discharge capacity sweep (MW)
TES_RANGE = [50, 75, 100, 125, 150]

# Storage comparison scenarios
STORAGE_SCENARIOS = {
    'TES_only': {'use_tes': True, 'use_bess': False, 'use_ldes': False},
    'TES_Battery': {'use_tes': True, 'use_bess': True, 'use_ldes': False},
    'TES_LDES': {'use_tes': True, 'use_bess': False, 'use_ldes': True},
    'TES_Battery_LDES': {'use_tes': True, 'use_bess': True, 'use_ldes': True},
    'Battery_LDES_only': {'use_tes': False, 'use_bess': True, 'use_ldes': True},
}

print(f"  Solar range: {SOLAR_RANGE} MW")
print(f"  Wind range: {WIND_RANGE} MW")
print(f"  TES range: {TES_RANGE} MW")
print(f"  Storage scenarios: {len(STORAGE_SCENARIOS)}")
print(f"  Total configurations: {len(SOLAR_RANGE) * len(WIND_RANGE) * len(TES_RANGE) * len(STORAGE_SCENARIOS)}")
print()

# ============================================================================
# STEP 2: Create Base Operational Data (8760 hours)
# ============================================================================

print("Step 2: Creating base operational data...")

HOURS = 8760

# Generate realistic annual weather profiles
import math

def generate_solar_profile(solar_MW, hours=8760):
    """Generate realistic solar profile with seasonal variation"""
    solar_cf = []
    for h in range(hours):
        hour_of_day = h % 24
        day_of_year = h // 24

        # Daytime hours (6 AM to 6 PM)
        if 6 <= hour_of_day <= 18:
            val = math.sin(math.pi * (hour_of_day - 6) / 12)
            seasonal_factor = 0.85 + 0.3 * math.sin(2 * math.pi * (day_of_year - 80) / 365)

            # Cloud cover on some days
            if (day_of_year % 7 == 3) or (day_of_year % 11 == 5):
                val *= 0.3

            val *= seasonal_factor
        else:
            val = 0

        solar_cf.append(val)

    return np.array(solar_cf) * solar_MW * 1000  # Convert to kW

def generate_wind_profile(wind_MW, hours=8760):
    """Generate realistic wind profile with seasonal variation"""
    np.random.seed(42)
    seasonal_wind = 0.4 + 0.2 * np.sin(2 * np.pi * (np.arange(hours) / 24 - 350) / 365)
    wind_cf = np.clip(seasonal_wind + 0.15 * np.sin(np.linspace(0, 50*np.pi, hours)) +
                      0.1 * np.random.randn(hours), 0, 1)
    return wind_cf * wind_MW * 1000  # Convert to kW

print(f"  Weather profiles ready for {HOURS} hours")
print()

# ============================================================================
# STEP 3: Run Optimization Sweeps
# ============================================================================

print("Step 3: Running optimization sweeps...")
print()

# Try to import the Phase 2 module
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("pyomo_DTC_CPLEX_TES",
        "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2/06_pyomo_DTC_CPLEX_TES.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    roll_cfe = module.roll_cfe

    import pyomo.environ as pyo
    solver = pyo.SolverFactory('appsi_highs')
    solver.available(exception_flag=True)

    print("✓ Phase 2 module and HiGHS solver ready!")
    print()

    # Storage for results
    results_list = []

    # Counter for progress
    total_runs = len(SOLAR_RANGE) * len(WIND_RANGE) * len(TES_RANGE) * len(STORAGE_SCENARIOS)
    run_count = 0

    # Iterate through all configurations
    for solar_mw in SOLAR_RANGE:
        for wind_mw in WIND_RANGE:
            for tes_mw in TES_RANGE:
                for scenario_name, scenario_config in STORAGE_SCENARIOS.items():

                    run_count += 1
                    print(f"[{run_count}/{total_runs}] Running: {solar_mw}MW solar, {wind_mw}MW wind, {tes_mw}MW TES, {scenario_name}")

                    # Generate weather data for this configuration
                    solar_gen = generate_solar_profile(solar_mw, HOURS)
                    wind_gen = generate_wind_profile(wind_mw, HOURS)

                    # Create operational data
                    dfopsx = pd.DataFrame({
                        'St': solar_gen,
                        'Wt': wind_gen,
                        'P1': [30.0] * HOURS,
                        'P2': [20.0] * HOURS,
                        'CFE': [0.5] * HOURS,
                        'PNGt': [5.0] * HOURS,
                        'BXmaxt': [200000] * HOURS,
                        'LXmaxt': [500000] * HOURS,
                        'G1_max_kW': [150000] * HOURS,  # 150 MW gas backup for flexibility
                        'G2_max_kW': [0] * HOURS,
                        'G1_heatrate_mmbtu_mwh': [10.0] * HOURS,
                        'G2_heatrate_mmbtu_mwh': [10.0] * HOURS,
                    })

                    # Create vars config
                    vars_config = {
                        'dispatch_time': 8760,
                        'window_size': 48,  # Use 48hr windows (Greg's recommendation)
                        'step_size': 24,
                        'Load_max': LOAD_MW,
                        'Load_min': LOAD_MW,
                        'Load_MRR': 0,
                        'tes_rte': tes_params['tes_rte'] / 100.0,
                        'tes_CDratio': tes_params['tes_CDratio'],
                        'tes_duration': tes_params['tes_duration'],
                        'tes_st_eff': 40.0,
                        'tes_st_min': 40.0,
                        'tes_soci': 0.30,
                        'BESS_rte': 0.88,
                        'ess_soci': 0.30,
                        'BESS_cyclesperyr': 365,
                        'LDES_rte': 0.65,
                        'LDES_constantloss': 1.0,
                        'cleanfirm_size': 0,
                        'NG_CFE': 0.0,
                        'G1_max': 150,
                        'G1_fc_bfix': 0,
                        'G2_fc_bfix': 0,
                        'G1_fc_mfix': 0,
                        'G2_fc_mfix': 0,
                        'G1_fc_bvar': 0,
                        'G2_fc_bvar': 0,
                        'G1_fc_mvar': 0,
                        'G2_fc_mvar': 0,
                        'NONCFE_pen': 200,
                        'EA_pen': 0.5,
                        'wind_basis': 0,
                        'Lcurtt_pen': 1000,
                        'wind_ptc_2023': 27.5,
                        'fin_esc': 0.025,
                        'COD': 2025,
                        'solve_with_gurobi': 0,
                        'solve_with_highs': 1,
                    }

                    # Create system sizing
                    svar = {
                        'bessD_kW': 100000 if scenario_config['use_bess'] else 0,
                        'bessC_kW': 100000 if scenario_config['use_bess'] else 0,
                        'bess_kWh': 200000 if scenario_config['use_bess'] else 0,
                        'ldesD_kW': 100000 if scenario_config['use_ldes'] else 0,
                        'ldesC_kW': 100000 if scenario_config['use_ldes'] else 0,
                        'ldes_kWh': 500000 if scenario_config['use_ldes'] else 0,
                        'tesD_kW': tes_mw * 1000 if scenario_config['use_tes'] else 0,
                        'maxExpMW': 0,
                        'maxImpMW': 0,
                    }

                    try:
                        # Run optimization
                        results_df = roll_cfe(
                            vars=vars_config,
                            dfopsx=dfopsx,
                            svar=svar,
                            threads=None,
                            P=200,
                            pos=0
                        )

                        # Calculate metrics
                        total_load_MWh = results_df['Lt'].sum() / 1000
                        gas_MMBtu = results_df['Gngt'].sum() if 'Gngt' in results_df.columns else 0
                        gas_MWh = gas_MMBtu / 10
                        cfe_pct = ((total_load_MWh - gas_MWh) / total_load_MWh) * 100 if total_load_MWh > 0 else 0

                        total_cost = results_df['Ct'].sum() if 'Ct' in results_df.columns else 0
                        lcoe = total_cost / total_load_MWh if total_load_MWh > 0 else 0

                        # Store results
                        results_list.append({
                            'solar_MW': solar_mw,
                            'wind_MW': wind_mw,
                            'tes_MW': tes_mw,
                            'storage_scenario': scenario_name,
                            'total_load_MWh': total_load_MWh,
                            'gas_MWh': gas_MWh,
                            'cfe_percent': cfe_pct,
                            'total_cost': total_cost,
                            'lcoe_per_MWh': lcoe,
                            'tes_discharge_MWh': results_df['Gtest'].sum() / 1000 if 'Gtest' in results_df.columns else 0,
                            'battery_discharge_MWh': results_df['BDt'].sum() / 1000 if 'BDt' in results_df.columns else 0,
                            'ldes_discharge_MWh': results_df['LdDt'].sum() / 1000 if 'LdDt' in results_df.columns else 0,
                            'status': 'success'
                        })

                        print(f"  → CFE: {cfe_pct:.1f}%, LCOE: ${lcoe:.2f}/MWh")

                    except Exception as e:
                        print(f"  → FAILED: {str(e)[:100]}")
                        results_list.append({
                            'solar_MW': solar_mw,
                            'wind_MW': wind_mw,
                            'tes_MW': tes_mw,
                            'storage_scenario': scenario_name,
                            'status': 'failed',
                            'error': str(e)[:200]
                        })

    # Save results
    results_df = pd.DataFrame(results_list)
    output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project/TESProject/Phase 3 - Analysis"
    results_df.to_csv(f"{output_dir}/phase3_optimization_sweep_results.csv", index=False)

    print()
    print("="*80)
    print("OPTIMIZATION SWEEP COMPLETE!")
    print("="*80)
    print(f"Total configurations tested: {len(results_list)}")
    print(f"Successful runs: {sum(1 for r in results_list if r['status'] == 'success')}")
    print(f"Results saved: phase3_optimization_sweep_results.csv")

    # Find best configurations
    successful_results = results_df[results_df['status'] == 'success']
    if len(successful_results) > 0:
        print()
        print("TOP 5 CONFIGURATIONS BY CFE:")
        top_cfe = successful_results.nlargest(5, 'cfe_percent')[['solar_MW', 'wind_MW', 'tes_MW', 'storage_scenario', 'cfe_percent', 'lcoe_per_MWh']]
        print(top_cfe.to_string(index=False))

        print()
        print("TOP 5 CONFIGURATIONS BY LOWEST LCOE:")
        top_lcoe = successful_results.nsmallest(5, 'lcoe_per_MWh')[['solar_MW', 'wind_MW', 'tes_MW', 'storage_scenario', 'cfe_percent', 'lcoe_per_MWh']]
        print(top_lcoe.to_string(index=False))

        print()
        print("CONFIGURATIONS ACHIEVING 100% CFE:")
        perfect_cfe = successful_results[successful_results['cfe_percent'] >= 99.9]
        if len(perfect_cfe) > 0:
            print(perfect_cfe[['solar_MW', 'wind_MW', 'tes_MW', 'storage_scenario', 'cfe_percent', 'lcoe_per_MWh']].to_string(index=False))
        else:
            print("  None found - need larger renewable capacity")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
