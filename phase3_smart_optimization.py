"""
PHASE 3: SMART TWO-STAGE SYSTEM OPTIMIZATION
Find optimal mix efficiently using a coarse-then-fine approach

Stage 1: Coarse sweep (few configurations, quick) to find promising region
Stage 2: Fine sweep in best region to find optimal configuration

Target: 100% CFE at lowest LCOE
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Add paths
sys.path.insert(0, "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2")
sys.path.insert(0, "/Users/sreyachagarlamudi/Downloads/x_PtXv3-main")

print("="*80)
print("PHASE 3: SMART TWO-STAGE OPTIMIZATION")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# CONFIGURATION
# ============================================================================

LOAD_MW = 100  # Fixed datacenter load
HOURS = 8760

# Load TES parameters
excel_file = "/Users/sreyachagarlamudi/Downloads/(PtXv3.4_r0) gjt_working.xlsx"
tes_df = pd.read_excel(excel_file, sheet_name='TES', header=None)
tes_params = {}
for idx, row in tes_df.iterrows():
    tes_params[row[0]] = row[2]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

import math

def generate_solar_profile(solar_MW, hours=8760):
    """Generate realistic solar profile"""
    solar_cf = []
    for h in range(hours):
        hour_of_day = h % 24
        day_of_year = h // 24
        if 6 <= hour_of_day <= 18:
            val = math.sin(math.pi * (hour_of_day - 6) / 12)
            seasonal_factor = 0.85 + 0.3 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
            if (day_of_year % 7 == 3) or (day_of_year % 11 == 5):
                val *= 0.3
            val *= seasonal_factor
        else:
            val = 0
        solar_cf.append(val)
    return np.array(solar_cf) * solar_MW * 1000

def generate_wind_profile(wind_MW, hours=8760):
    """Generate realistic wind profile"""
    np.random.seed(42)
    seasonal_wind = 0.4 + 0.2 * np.sin(2 * np.pi * (np.arange(hours) / 24 - 350) / 365)
    wind_cf = np.clip(seasonal_wind + 0.15 * np.sin(np.linspace(0, 50*np.pi, hours)) +
                      0.1 * np.random.randn(hours), 0, 1)
    return wind_cf * wind_MW * 1000

def run_config(solar_mw, wind_mw, tes_mw, use_bess, use_ldes, roll_cfe):
    """Run a single configuration and return metrics"""

    # Generate weather data
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
        'G1_max_kW': [150000] * HOURS,
        'G2_max_kW': [0] * HOURS,
        'G1_heatrate_mmbtu_mwh': [10.0] * HOURS,
        'G2_heatrate_mmbtu_mwh': [10.0] * HOURS,
    })

    # Vars config
    vars_config = {
        'dispatch_time': 8760,
        'window_size': 48,
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

    # System sizing
    svar = {
        'bessD_kW': 100000 if use_bess else 0,
        'bessC_kW': 100000 if use_bess else 0,
        'bess_kWh': 200000 if use_bess else 0,
        'ldesD_kW': 100000 if use_ldes else 0,
        'ldesC_kW': 100000 if use_ldes else 0,
        'ldes_kWh': 500000 if use_ldes else 0,
        'tesD_kW': tes_mw * 1000,
        'maxExpMW': 0,
        'maxImpMW': 0,
    }

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

    return {
        'solar_MW': solar_mw,
        'wind_MW': wind_mw,
        'tes_MW': tes_mw,
        'use_bess': use_bess,
        'use_ldes': use_ldes,
        'cfe_percent': cfe_pct,
        'lcoe_per_MWh': lcoe,
        'gas_MWh': gas_MWh,
        'total_cost': total_cost,
    }

# ============================================================================
# IMPORT PHASE 2 MODULE
# ============================================================================

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

    print("✓ Phase 2 module and HiGHS solver ready!\n")

    # ========================================================================
    # STAGE 1: COARSE SWEEP
    # ========================================================================

    print("="*80)
    print("STAGE 1: COARSE SWEEP (Finding Promising Region)")
    print("="*80)
    print()

    # Coarse grid: fewer points, wider spacing
    coarse_solar = [250, 350, 450]  # 3 points
    coarse_wind = [50, 100]          # 2 points
    coarse_tes = [75, 125]           # 2 points

    print(f"Testing {len(coarse_solar)} × {len(coarse_wind)} × {len(coarse_tes)} = {len(coarse_solar)*len(coarse_wind)*len(coarse_tes)} configurations")
    print()

    coarse_results = []
    count = 0
    total = len(coarse_solar) * len(coarse_wind) * len(coarse_tes)

    for solar in coarse_solar:
        for wind in coarse_wind:
            for tes in coarse_tes:
                count += 1
                print(f"[{count}/{total}] Testing: {solar}MW solar, {wind}MW wind, {tes}MW TES (with Battery+LDES)")

                try:
                    result = run_config(solar, wind, tes, use_bess=True, use_ldes=True, roll_cfe=roll_cfe)
                    coarse_results.append(result)
                    print(f"  → CFE: {result['cfe_percent']:.1f}%, LCOE: ${result['lcoe_per_MWh']:.2f}/MWh\n")
                except Exception as e:
                    print(f"  → FAILED: {str(e)[:80]}\n")

    # Find best region from coarse sweep
    coarse_df = pd.DataFrame(coarse_results)

    # Target: High CFE, Low LCOE
    # Score = CFE% - (LCOE normalized penalty)
    max_lcoe = coarse_df['lcoe_per_MWh'].max()
    coarse_df['score'] = coarse_df['cfe_percent'] - (coarse_df['lcoe_per_MWh'] / max_lcoe * 50)

    best_coarse = coarse_df.loc[coarse_df['score'].idxmax()]

    print("="*80)
    print("STAGE 1 RESULTS:")
    print(coarse_df.to_string(index=False))
    print()
    print("BEST COARSE CONFIGURATION:")
    print(f"  Solar: {best_coarse['solar_MW']:.0f} MW")
    print(f"  Wind: {best_coarse['wind_MW']:.0f} MW")
    print(f"  TES: {best_coarse['tes_MW']:.0f} MW")
    print(f"  CFE: {best_coarse['cfe_percent']:.1f}%")
    print(f"  LCOE: ${best_coarse['lcoe_per_MWh']:.2f}/MWh")
    print("="*80)
    print()

    # ========================================================================
    # STAGE 2: FINE SWEEP (Around Best Region)
    # ========================================================================

    print("="*80)
    print("STAGE 2: FINE SWEEP (Optimizing Around Best Region)")
    print("="*80)
    print()

    # Fine grid: narrow range around best, smaller steps
    fine_solar = [best_coarse['solar_MW'] - 50, best_coarse['solar_MW'], best_coarse['solar_MW'] + 50]
    fine_wind = [best_coarse['wind_MW'] - 25, best_coarse['wind_MW'], best_coarse['wind_MW'] + 25]
    fine_tes = [best_coarse['tes_MW'] - 25, best_coarse['tes_MW'], best_coarse['tes_MW'] + 25]

    # Filter to valid ranges
    fine_solar = [s for s in fine_solar if s >= 200]
    fine_wind = [w for w in fine_wind if w >= 25]
    fine_tes = [t for t in fine_tes if t >= 50]

    print(f"Testing {len(fine_solar)} × {len(fine_wind)} × {len(fine_tes)} = {len(fine_solar)*len(fine_wind)*len(fine_tes)} configurations")
    print()

    fine_results = []
    count = 0
    total = len(fine_solar) * len(fine_wind) * len(fine_tes)

    for solar in fine_solar:
        for wind in fine_wind:
            for tes in fine_tes:
                count += 1
                print(f"[{count}/{total}] Testing: {solar}MW solar, {wind}MW wind, {tes}MW TES (with Battery+LDES)")

                try:
                    result = run_config(solar, wind, tes, use_bess=True, use_ldes=True, roll_cfe=roll_cfe)
                    fine_results.append(result)
                    print(f"  → CFE: {result['cfe_percent']:.1f}%, LCOE: ${result['lcoe_per_MWh']:.2f}/MWh\n")
                except Exception as e:
                    print(f"  → FAILED: {str(e)[:80]}\n")

    # Find optimal configuration
    fine_df = pd.DataFrame(fine_results)
    fine_df['score'] = fine_df['cfe_percent'] - (fine_df['lcoe_per_MWh'] / fine_df['lcoe_per_MWh'].max() * 50)

    best_fine = fine_df.loc[fine_df['score'].idxmax()]
    highest_cfe = fine_df.loc[fine_df['cfe_percent'].idxmax()]
    lowest_lcoe = fine_df.loc[fine_df['lcoe_per_MWh'].idxmin()]

    print("="*80)
    print("STAGE 2 RESULTS:")
    print(fine_df.to_string(index=False))
    print()
    print("="*80)
    print("FINAL OPTIMIZATION RESULTS")
    print("="*80)
    print()
    print("BEST OVERALL (Balanced CFE + LCOE):")
    print(f"  Solar: {best_fine['solar_MW']:.0f} MW")
    print(f"  Wind: {best_fine['wind_MW']:.0f} MW")
    print(f"  TES: {best_fine['tes_MW']:.0f} MW")
    print(f"  CFE: {best_fine['cfe_percent']:.1f}%")
    print(f"  LCOE: ${best_fine['lcoe_per_MWh']:.2f}/MWh")
    print()
    print("HIGHEST CFE:")
    print(f"  Solar: {highest_cfe['solar_MW']:.0f} MW")
    print(f"  Wind: {highest_cfe['wind_MW']:.0f} MW")
    print(f"  TES: {highest_cfe['tes_MW']:.0f} MW")
    print(f"  CFE: {highest_cfe['cfe_percent']:.1f}%")
    print(f"  LCOE: ${highest_cfe['lcoe_per_MWh']:.2f}/MWh")
    print()
    print("LOWEST LCOE:")
    print(f"  Solar: {lowest_lcoe['solar_MW']:.0f} MW")
    print(f"  Wind: {lowest_lcoe['wind_MW']:.0f} MW")
    print(f"  TES: {lowest_lcoe['tes_MW']:.0f} MW")
    print(f"  CFE: {lowest_lcoe['cfe_percent']:.1f}%")
    print(f"  LCOE: ${lowest_lcoe['lcoe_per_MWh']:.2f}/MWh")
    print("="*80)

    # Save results
    output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project/TESProject/Phase 3 - Analysis"

    all_results = pd.concat([coarse_df, fine_df], ignore_index=True)
    all_results.to_csv(f"{output_dir}/phase3_optimization_results.csv", index=False)

    # Save summary
    summary = {
        'run_date': datetime.now().isoformat(),
        'best_overall': best_fine.to_dict(),
        'highest_cfe': highest_cfe.to_dict(),
        'lowest_lcoe': lowest_lcoe.to_dict(),
        'all_results_file': 'phase3_optimization_results.csv'
    }

    with open(f"{output_dir}/phase3_optimization_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print()
    print("✓ Results saved:")
    print("  - phase3_optimization_results.csv")
    print("  - phase3_optimization_summary.json")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("OPTIMIZATION COMPLETE!")
print("="*80)
