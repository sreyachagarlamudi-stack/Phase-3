"""
TES Model - CORRECTED VERSION
Fixes based on June 24 meeting feedback:
1. Uses actual Roman backcast data (not synthetic)
2. Correct gas pricing ($4/MMBTU)
3. Proper marginal cost calculation (OpEx only)
4. Steam turbine OpEx included
5. Separated TES charge/discharge/storage costs
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Add paths for imports
sys.path.insert(0, "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2")

print("="*80)
print("TES ANALYSIS - CORRECTED MODEL")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# STEP 1: Load TES Parameters from Excel
# ============================================================================

print("Step 1: Loading TES parameters from updated input sheet...")

excel_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/gjt_working_updated.xlsx"

# Load TES parameters
tes_params_df = pd.read_excel(excel_path, sheet_name='TES_PARAMS')
tes_params = {}
for idx, row in tes_params_df.iterrows():
    tes_params[row['Parameter']] = row['Value']

print("TES Parameters Loaded:")
print(f"  Heater CapEx: ${tes_params['tes_heater_capex']}/kW")
print(f"  Turbine CapEx: ${tes_params['tes_turbine_capex']}/kW")
print(f"  Turbine OpEx (fixed): ${tes_params['tes_turbine_opex_fixed']}/kW-year")
print(f"  Turbine OpEx (variable): ${tes_params['tes_turbine_opex_var']}/MWh")
print(f"  Storage CapEx: ${tes_params['tes_storage_capex']}/kWh")
print(f"  Turbine Efficiency: {tes_params['tes_turbine_eff_min']:.1%} @ 40% load, {tes_params['tes_turbine_eff_max']:.1%} @ 100% load")
print(f"  Turbine Min Load: {tes_params['tes_turbine_min_load']:.0%}")
print()

# ============================================================================
# STEP 2: Load Resource Data (Roman Backcast)
# ============================================================================

print("Step 2: Loading resource data...")

# Load solar and wind profiles
# These should be the actual Roman backcast 8760 time series
try:
    solar_df = pd.read_excel(excel_path, sheet_name='solar_cf')
    wind_df = pd.read_excel(excel_path, sheet_name='wind_cf')

    solar_cf = solar_df['cf'].values
    wind_cf = wind_df['cf'].values

    print(f"  Loaded Roman solar data: {len(solar_cf)} hours")
    print(f"  Loaded Roman wind data: {len(wind_cf)} hours")
    print(f"  Solar avg CF: {np.mean(solar_cf):.1%}")
    print(f"  Wind avg CF: {np.mean(wind_cf):.1%}")

except Exception as e:
    print(f"  Warning: Could not load Roman data from Excel: {e}")
    print(f"  Using Roman backcast from dfopsx sheet instead...")

    # Try to load from main data sheet
    dfopsx = pd.read_excel(excel_path, sheet_name='dfopsx')

    # Assuming columns are St (solar kW) and Wt (wind kW)
    # Calculate capacity factors
    solar_capacity_MW = 300  # Baseline
    wind_capacity_MW = 50     # Baseline

    solar_cf = dfopsx['St'].values / (solar_capacity_MW * 1000)
    wind_cf = dfopsx['Wt'].values / (wind_capacity_MW * 1000)

    print(f"  Solar avg CF: {np.mean(solar_cf):.1%}")
    print(f"  Wind avg CF: {np.mean(wind_cf):.1%}")

print()

# Verify capacity factors are reasonable
if np.mean(solar_cf) < 0.25:
    print("  ⚠️  WARNING: Solar CF < 25% - may be using wrong data or DC instead of AC")
if np.mean(wind_cf) < 0.40:
    print("  ⚠️  WARNING: Wind CF < 40% - may be using wrong data or poor site")

print()

# ============================================================================
# STEP 3: Calculate Marginal Costs (CORRECTED)
# ============================================================================

print("Step 3: Calculating marginal costs (OpEx only - CORRECTED)...")

# TES Marginal Cost = Variable OpEx ONLY (not CapEx!)
tes_marginal_cost = tes_params['tes_turbine_opex_var']  # $/MWh
print(f"  TES marginal cost: ${tes_marginal_cost:.2f}/MWh (variable OpEx only)")

# Gas Marginal Cost = Fuel + Variable OpEx
gas_fuel_price = 4.0  # $/MMBTU
gas_heat_rate = 10.0  # MMBTU/MWh (typical combined cycle)
gas_var_opex = 8.0    # $/MWh (variable O&M)
gas_fuel_cost = gas_fuel_price * gas_heat_rate / 1000 * 1000  # Convert to $/MWh
gas_marginal_cost = gas_fuel_cost + gas_var_opex

print(f"  Gas fuel cost: ${gas_fuel_cost:.2f}/MWh (${gas_fuel_price}/MMBTU × {gas_heat_rate} MMBTU/MWh)")
print(f"  Gas variable O&M: ${gas_var_opex:.2f}/MWh")
print(f"  Gas marginal cost: ${gas_marginal_cost:.2f}/MWh (TOTAL)")
print()

print(f"  Cost comparison: TES ${tes_marginal_cost:.2f}/MWh vs Gas ${gas_marginal_cost:.2f}/MWh")
print(f"  → TES is {(gas_marginal_cost/tes_marginal_cost - 1)*100:.0f}% cheaper on marginal basis!")
print()

# ============================================================================
# STEP 4: System Configuration
# ============================================================================

print("Step 4: Configuring system...")

HOURS = 8760
datacenter_load_MW = 100

# Baseline configuration
solar_MW = 300
wind_MW = 50
tes_storage_hours = 16
tes_discharge_MW = 100  # Fixed at load per Greg's feedback
tes_charge_MW = 100     # Can be optimized separately
gas_backup_MW = 100

# Calculate capacities
tes_storage_MWh = tes_discharge_MW * tes_storage_hours

print(f"  Datacenter Load: {datacenter_load_MW} MW")
print(f"  Solar: {solar_MW} MW")
print(f"  Wind: {wind_MW} MW")
print(f"  TES Storage: {tes_storage_MWh} MWh ({tes_storage_hours} hours)")
print(f"  TES Discharge: {tes_discharge_MW} MW (fixed at load)")
print(f"  TES Charge: {tes_charge_MW} MW")
print(f"  Gas Backup: {gas_backup_MW} MW")
print()

# ============================================================================
# STEP 5: Calculate Levelized Costs (for reference)
# ============================================================================

print("Step 5: Calculating levelized costs (for CapEx planning)...")

# Assume 25-year life, 10% WACC, 30% IRA credit
wacc = 0.10
lifetime = 25
ira_credit = 0.30
crf = (wacc * (1 + wacc)**lifetime) / ((1 + wacc)**lifetime - 1)

# TES System Total CapEx
tes_heater_capex = tes_charge_MW * 1000 * tes_params['tes_heater_capex']
tes_turbine_capex = tes_discharge_MW * 1000 * tes_params['tes_turbine_capex']
tes_storage_capex = tes_storage_MWh * 1000 * tes_params['tes_storage_capex']
tes_total_capex = tes_heater_capex + tes_turbine_capex + tes_storage_capex

# Apply IRA credit
tes_capex_after_ira = tes_total_capex * (1 - ira_credit)

# Annual costs
tes_annual_capex = tes_capex_after_ira * crf
tes_annual_opex_fixed = (
    tes_charge_MW * 1000 * tes_params['tes_heater_opex_fixed'] +
    tes_discharge_MW * 1000 * tes_params['tes_turbine_opex_fixed'] +
    tes_storage_MWh * 1000 * tes_params['tes_storage_capex'] * tes_params['tes_storage_opex_pct']
)

print(f"  TES CapEx Breakdown:")
print(f"    Heaters: ${tes_heater_capex/1e6:.1f}M")
print(f"    Turbine: ${tes_turbine_capex/1e6:.1f}M")
print(f"    Storage: ${tes_storage_capex/1e6:.1f}M")
print(f"    Total: ${tes_total_capex/1e6:.1f}M")
print(f"    After IRA: ${tes_capex_after_ira/1e6:.1f}M")
print()
print(f"  TES Annual Costs:")
print(f"    Capital (amortized): ${tes_annual_capex/1e6:.2f}M/year")
print(f"    Fixed OpEx: ${tes_annual_opex_fixed/1e6:.2f}M/year")
print(f"    Variable OpEx: ${tes_marginal_cost:.2f}/MWh × dispatch")
print()

# ============================================================================
# STEP 6: Simple Dispatch Logic
# ============================================================================

print("Step 6: Running simple dispatch analysis...")
print("  (For full optimization, use pyomo module)")
print()

# Create hourly generation
solar_gen = solar_MW * solar_cf  # MW
wind_gen = wind_MW * wind_cf     # MW
renewable_gen = solar_gen + wind_gen  # MW

# Simple dispatch logic
load = np.ones(HOURS) * datacenter_load_MW  # MW
tes_soc = np.zeros(HOURS)
tes_charge = np.zeros(HOURS)
tes_discharge = np.zeros(HOURS)
gas_dispatch = np.zeros(HOURS)
curtailment = np.zeros(HOURS)

tes_soc[0] = tes_storage_MWh * 0.3  # Start at 30% SOC

for t in range(HOURS):
    surplus = renewable_gen[t] - load[t]

    if surplus > 0:
        # Excess renewable - charge TES if space available
        charge_possible = min(surplus, tes_charge_MW, tes_storage_MWh - tes_soc[t])
        tes_charge[t] = charge_possible
        remaining_surplus = surplus - charge_possible
        curtailment[t] = remaining_surplus

    else:
        # Deficit - use TES if available, otherwise gas
        deficit = -surplus

        # Discharge TES (consider efficiency and min load)
        tes_available = tes_soc[t] * tes_params['tes_turbine_eff_max']  # MW available
        tes_min_output = tes_discharge_MW * tes_params['tes_turbine_min_load']

        if tes_available >= tes_min_output:
            # Can use TES
            tes_output = min(deficit, tes_discharge_MW, tes_available)
            tes_discharge[t] = tes_output / tes_params['tes_turbine_eff_max']  # Thermal MW
            remaining_deficit = deficit - tes_output
        else:
            # TES below minimum, use gas
            remaining_deficit = deficit

        # Use gas for remainder
        gas_dispatch[t] = remaining_deficit

    # Update SOC for next hour
    if t < HOURS - 1:
        charge_thermal = tes_charge[t] * tes_params['tes_heater_efficiency']
        discharge_thermal = tes_discharge[t]
        loss = tes_soc[t] * tes_params['tes_storage_loss_per_day'] / 24
        tes_soc[t+1] = tes_soc[t] + charge_thermal - discharge_thermal - loss

# Calculate annual totals
solar_annual = np.sum(solar_gen)
wind_annual = np.sum(wind_gen)
tes_discharge_annual = np.sum(tes_discharge * tes_params['tes_turbine_eff_max'])
gas_annual = np.sum(gas_dispatch)
curtail_annual = np.sum(curtailment)
load_annual = np.sum(load)

# Calculate CFE
renewable_to_load = solar_annual + wind_annual + tes_discharge_annual
cfe_pct = renewable_to_load / load_annual * 100

print("Annual Results:")
print(f"  Solar generation: {solar_annual:,.0f} MWh ({solar_annual/load_annual*100:.1f}% of load)")
print(f"  Wind generation: {wind_annual:,.0f} MWh ({wind_annual/load_annual*100:.1f}% of load)")
print(f"  TES discharge: {tes_discharge_annual:,.0f} MWh ({tes_discharge_annual/load_annual*100:.1f}% of load)")
print(f"  Gas backup: {gas_annual:,.0f} MWh ({gas_annual/load_annual*100:.1f}% of load)")
print(f"  Curtailment: {curtail_annual:,.0f} MWh")
print(f"  Total load: {load_annual:,.0f} MWh")
print()
print(f"  CFE Achievement: {cfe_pct:.1f}%")
print()

# Calculate capacity factors
solar_cf_actual = solar_annual / (solar_MW * 8760)
wind_cf_actual = wind_annual / (wind_MW * 8760)
tes_cf_actual = tes_discharge_annual / (tes_discharge_MW * 8760)
gas_cf_actual = gas_annual / (gas_backup_MW * 8760)

print("Capacity Factors:")
print(f"  Solar: {solar_cf_actual:.1%}")
print(f"  Wind: {wind_cf_actual:.1%}")
print(f"  TES: {tes_cf_actual:.1%}")
print(f"  Gas: {gas_cf_actual:.1%}")
print()

# ============================================================================
# STEP 7: Cost Analysis
# ============================================================================

print("Step 7: Cost analysis...")

# Variable costs incurred
tes_var_cost_total = tes_discharge_annual * tes_marginal_cost
gas_var_cost_total = gas_annual * gas_marginal_cost

print(f"  TES variable cost: ${tes_var_cost_total/1e6:.2f}M/year")
print(f"  Gas variable cost: ${gas_var_cost_total/1e6:.2f}M/year")
print()

# Total annual cost (capital + fixed OpEx + variable OpEx)
total_annual_cost = tes_annual_capex + tes_annual_opex_fixed + tes_var_cost_total + gas_var_cost_total

# LCOE
lcoe = total_annual_cost / load_annual

print(f"  Total Annual Cost: ${total_annual_cost/1e6:.2f}M")
print(f"  LCOE: ${lcoe:.2f}/MWh")
print()

# ============================================================================
# STEP 8: Save Results
# ============================================================================

print("Step 8: Saving results...")

results = {
    'timestamp': datetime.now().isoformat(),
    'configuration': {
        'solar_MW': solar_MW,
        'wind_MW': wind_MW,
        'tes_storage_MWh': tes_storage_MWh,
        'tes_discharge_MW': tes_discharge_MW,
        'tes_charge_MW': tes_charge_MW,
        'gas_backup_MW': gas_backup_MW,
    },
    'resource_data': {
        'solar_cf_avg': float(np.mean(solar_cf)),
        'wind_cf_avg': float(np.mean(wind_cf)),
        'data_source': 'Roman backcast',
    },
    'marginal_costs': {
        'tes_$/MWh': float(tes_marginal_cost),
        'gas_fuel_$/MWh': float(gas_fuel_cost),
        'gas_var_opex_$/MWh': float(gas_var_opex),
        'gas_total_$/MWh': float(gas_marginal_cost),
    },
    'annual_generation_MWh': {
        'solar': float(solar_annual),
        'wind': float(wind_annual),
        'tes_discharge': float(tes_discharge_annual),
        'gas': float(gas_annual),
        'curtailment': float(curtail_annual),
        'load': float(load_annual),
    },
    'capacity_factors': {
        'solar': float(solar_cf_actual),
        'wind': float(wind_cf_actual),
        'tes': float(tes_cf_actual),
        'gas': float(gas_cf_actual),
    },
    'performance': {
        'cfe_pct': float(cfe_pct),
        'lcoe_$/MWh': float(lcoe),
    },
    'costs_M$_per_year': {
        'tes_capital_amortized': float(tes_annual_capex/1e6),
        'tes_fixed_opex': float(tes_annual_opex_fixed/1e6),
        'tes_variable_opex': float(tes_var_cost_total/1e6),
        'gas_variable': float(gas_var_cost_total/1e6),
        'total': float(total_annual_cost/1e6),
    }
}

output_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/results_corrected.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"✓ Results saved to: results_corrected.json")
print()

print("="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print()
print("Key Findings:")
print(f"  1. Using Roman backcast data: Solar {np.mean(solar_cf):.1%} CF, Wind {np.mean(wind_cf):.1%} CF")
print(f"  2. Marginal costs corrected: TES ${tes_marginal_cost}/MWh vs Gas ${gas_marginal_cost:.2f}/MWh")
print(f"  3. CFE Achievement: {cfe_pct:.1f}%")
print(f"  4. TES Utilization: {tes_cf_actual:.1%} capacity factor")
print(f"  5. LCOE: ${lcoe:.2f}/MWh")
print()

if tes_cf_actual < 0.10:
    print("⚠️  WARNING: TES utilization still low (<10%)")
    print("   → Check that gas pricing is correct ($4/MMBTU)")
    print("   → Verify marginal cost logic in dispatch")
print()
