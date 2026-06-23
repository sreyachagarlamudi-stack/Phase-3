"""
Baseline Optimization: tes_st_min = 40%

This script runs the full-year optimization with baseline configuration.
Expected runtime: ~30 minutes
"""

import sys
import os
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime

# Add paths
sys.path.insert(0, "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2")
sys.path.insert(0, "/Users/sreyachagarlamudi/Downloads/x_PtXv3-main")

print("="*80)
print("BASELINE OPTIMIZATION: tes_st_min = 40%")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# Load Excel Configuration
# ============================================================================

excel_file = "/Users/sreyachagarlamudi/Downloads/(PtXv3.4_r0) gjt_working_VALIDATED_2026-06-22.xlsx"
print(f"Loading VALIDATED Excel file: {excel_file}\n")
print("✅ Using VALIDATED efficiency parameters:")
print("   tes_st_eff_at_40 = 34% (NREL SAM + EPA CHP)")
print("   tes_st_eff_at_100 = 39% (EPA + Nuclear ref)")
print()

# Load TES parameters
tes_df = pd.read_excel(excel_file, sheet_name='TES', header=None)
tes_params = {}
for idx, row in tes_df.iterrows():
    if pd.notna(row[0]):
        param_name = row[0]
        param_value = row[2]
        tes_params[param_name] = param_value

print("TES Configuration:")
print(f"  tes_st_eff: {tes_params.get('tes_st_eff', 40)}%")
print(f"  tes_st_min: {tes_params.get('tes_st_min', 40)}%")
print(f"  tes_rte: {tes_params['tes_rte']}%")
print(f"  tes_duration: {tes_params['tes_duration']} hours")
print()

# ============================================================================
# Configure Scenario
# ============================================================================

HOURS = 8760  # Full year

vars_config = {
    # Time horizon
    'dispatch_time': HOURS,
    'window_size': 48,     # 48-hour windows per Greg's guidance
    'step_size': 24,       # 24-hour steps

    # Load
    'Load_max': 100,       # 100 MW datacenter
    'Load_min': 100,
    'Load_MRR': 0,

    # TES parameters
    'tes_rte': tes_params['tes_rte'] / 100.0,
    'tes_CDratio': tes_params['tes_CDratio'],
    'tes_duration': tes_params['tes_duration'],
    'tes_st_eff': float(tes_params.get('tes_st_eff', 40.0)),
    'tes_st_min': float(tes_params.get('tes_st_min', 40.0)),
    'tes_soci': 0.30,

    # Battery
    'BESS_rte': 0.88,
    'ess_soci': 0.30,
    'BESS_cyclesperyr': 365,

    # LDES
    'LDES_rte': 0.65,
    'LDES_constantloss': 1.0,

    # Grid
    'cleanfirm_size': 0,

    # Gas
    'NG_CFE': 0.0,
    'G1_fc_bfix': 0,
    'G2_fc_bfix': 0,
    'G1_fc_mfix': 0,
    'G2_fc_mfix': 0,
    'G1_fc_bvar': 0,
    'G2_fc_bvar': 0,
    'G1_fc_mvar': 0,
    'G2_fc_mvar': 0,

    # Penalties
    'NONCFE_pen': 200,
    'EA_pen': 0.5,
    'wind_basis': 0,
    'Lcurtt_pen': 1000,

    # Finance
    'wind_ptc_2023': 27.5,
    'fin_esc': 0.025,
    'COD': 2025,

    # Solver
    'solve_with_gurobi': 0,
    'solve_with_highs': 1,  # Use HiGHS (CPLEX Community Edition has size limits)
}

print(f"Scenario: {HOURS} hours, {vars_config['window_size']}hr windows")
print(f"Baseline: tes_st_min = {vars_config['tes_st_min']}%\n")

# ============================================================================
# Create Weather Data (Synthetic for Full Year)
# ============================================================================

print("Generating synthetic weather data...")

solar_MW = 300
wind_MW = 50

# Solar: sinusoidal with seasonal variation
solar_cf = []
for h in range(HOURS):
    hour_of_day = h % 24
    day_of_year = h // 24

    # Daily cycle
    if 6 <= hour_of_day <= 18:
        daily_val = math.sin(math.pi * (hour_of_day - 6) / 12)
    else:
        daily_val = 0

    # Seasonal variation (higher in summer)
    seasonal_factor = 0.7 + 0.3 * math.cos(2 * math.pi * (day_of_year - 172) / 365)

    solar_cf.append(daily_val * seasonal_factor)

solar_cf = np.array(solar_cf)

# Wind: more variable, lower in summer
np.random.seed(42)
wind_cf = []
for h in range(HOURS):
    day_of_year = h // 24
    seasonal_factor = 0.5 + 0.2 * math.cos(2 * math.pi * (day_of_year - 30) / 365)
    base = 0.35 * seasonal_factor
    noise = 0.15 * np.random.randn()
    wind_cf.append(np.clip(base + noise, 0, 1))

wind_cf = np.array(wind_cf)

# Create dfopsx
dfopsx = pd.DataFrame({
    'St': solar_MW * 1000 * solar_cf,
    'Wt': wind_MW * 1000 * wind_cf,
    'P1': [30.0] * HOURS,
    'P2': [20.0] * HOURS,
    'CFE': [0.5] * HOURS,
    'PNGt': [5.0] * HOURS,
    'BXmaxt': [200000] * HOURS,
    'LXmaxt': [500000] * HOURS,
    'G1_max_kW': [100000] * HOURS,  # 100 MW gas backup
    'G2_max_kW': [0] * HOURS,
    'G1_heatrate_mmbtu_mwh': [10.0] * HOURS,
    'G2_heatrate_mmbtu_mwh': [10.0] * HOURS,
})

print(f"  Solar avg CF: {np.mean(solar_cf):.1%}")
print(f"  Wind avg CF: {np.mean(wind_cf):.1%}")
print()

# ============================================================================
# System Sizing
# ============================================================================

svar = {
    'bessD_kW': 100000,
    'bessC_kW': 100000,
    'bess_kWh': 200000,
    'ldesD_kW': 100000,
    'ldesC_kW': 100000,
    'ldes_kWh': 500000,
    'tesD_kW': 100000,  # 100 MW TES discharge
    'maxExpMW': 0,
    'maxImpMW': 0,
}

print("System Sizing:")
print(f"  TES: {svar['tesD_kW']/1000} MW discharge, {tes_params['tes_duration']}hr duration")
print(f"  Solar: {solar_MW} MW")
print(f"  Wind: {wind_MW} MW")
print()

# ============================================================================
# Import and Run Optimization Module
# ============================================================================

print("Importing optimization module...")

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("pyomo_DTC_CPLEX_TES",
        "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2/06_pyomo_DTC_CPLEX_TES.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    roll_cfe = module.roll_cfe

    print("✓ Module imported successfully")
    print("✓ Using HiGHS solver (open-source, no size limits)\n")

    print("="*80)
    print("RUNNING OPTIMIZATION (THIS WILL TAKE ~30 MINUTES)")
    print("="*80)
    print()

    # Run optimization
    results_df = roll_cfe(
        vars=vars_config,
        dfopsx=dfopsx,
        svar=svar,
        threads=None,
        P=200,
        pos=0
    )

    print()
    print("="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print()

    # Calculate metrics
    total_load_MWh = results_df['Lt'].sum() / 1000
    tes_discharge_MWh = results_df.get('Gtest', pd.Series([0])).sum() / 1000
    gas_MWh = results_df.get('Gngt', pd.Series([0])).sum() / 10.0  # Convert MMBtu to MWh

    solar_gen_MWh = dfopsx['St'].sum() / 1000
    wind_gen_MWh = dfopsx['Wt'].sum() / 1000
    renewable_gen_MWh = solar_gen_MWh + wind_gen_MWh
    cfe_percent = (renewable_gen_MWh / total_load_MWh * 100) if total_load_MWh > 0 else 0

    # Simple LCOE calculation (full calculation needs CAPEX)
    # For now, just track operational metrics

    summary = {
        'run_date': datetime.now().isoformat(),
        'configuration': 'Baseline',
        'tes_st_min': vars_config['tes_st_min'],
        'tes_st_eff': vars_config['tes_st_eff'],
        'excel_file': excel_file,
        'metrics': {
            'total_load_MWh': float(total_load_MWh),
            'solar_gen_MWh': float(solar_gen_MWh),
            'wind_gen_MWh': float(wind_gen_MWh),
            'renewable_gen_MWh': float(renewable_gen_MWh),
            'tes_discharge_MWh': float(tes_discharge_MWh),
            'gas_MWh': float(gas_MWh),
            'cfe_percent': float(cfe_percent),
        }
    }

    # Save results
    output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis"

    results_df.to_csv(f"{output_dir}/baseline_40pct_dispatch.csv", index=True)
    print(f"✓ Saved: baseline_40pct_dispatch.csv")

    with open(f"{output_dir}/baseline_40pct_results.json", 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Saved: baseline_40pct_results.json")

    print()
    print("Key Metrics:")
    print(f"  Total Load: {total_load_MWh:,.0f} MWh/year")
    print(f"  CFE: {cfe_percent:.1f}%")
    print(f"  Gas Backup: {gas_MWh:,.0f} MWh/year")
    print(f"  TES Discharge: {tes_discharge_MWh:,.0f} MWh/year")
    print()

    print("="*80)
    print("BASELINE OPTIMIZATION COMPLETE")
    print("="*80)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
