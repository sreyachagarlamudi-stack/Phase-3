"""
TES Model - CORRECTED VERSION v3
Uses proper Roman-style capacity factors while waiting for actual 8760 data
Fixes based on June 24 meeting feedback
V3: Multiple turbine blocks (4×25 MW) for better turndown flexibility
"""

import sys
import os
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime

print("="*80)
print("TES ANALYSIS - CORRECTED MODEL V3 (Multiple Turbine Blocks)")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# STEP 1: Load TES Parameters from Excel
# ============================================================================

print("Step 1: Loading TES parameters...")

excel_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/gjt_working_updated.xlsx"

# Load TES parameters
tes_params_df = pd.read_excel(excel_path, sheet_name='TES_PARAMS')
tes_params = {}
for idx, row in tes_params_df.iterrows():
    tes_params[row['Parameter']] = row['Value']

print("✓ TES Parameters Loaded")
print(f"  Turbine OpEx (variable): ${tes_params['tes_turbine_opex_var']}/MWh")
print()

# ============================================================================
# STEP 2: Generate Roman-Style Resource Data (Target CFs)
# ============================================================================

print("Step 2: Generating Roman-style resource profiles...")
print("  (Using target capacity factors from meeting feedback)")
print()

HOURS = 8760
np.random.seed(42)

# Solar: Target 30-33% AC capacity factor
solar_cf = []
for h in range(HOURS):
    hour_of_day = h % 24
    day_of_year = h // 24

    # Daily pattern (peaks at solar noon)
    if 6 <= hour_of_day <= 18:
        daily_val = math.sin(math.pi * (hour_of_day - 6) / 12)
    else:
        daily_val = 0

    # Seasonal variation (higher in summer)
    seasonal_factor = 0.9 + 0.2 * math.sin(2 * math.pi * (day_of_year - 80) / 365)

    # Add weather variability
    weather = 1.0 + 0.15 * np.random.randn()
    weather = np.clip(weather, 0.7, 1.2)

    cf = daily_val * seasonal_factor * weather * 0.35  # Scale to get ~30% average
    solar_cf.append(np.clip(cf, 0, 1))

solar_cf = np.array(solar_cf)

# Wind: Target 50% capacity factor
wind_cf = []
for h in range(HOURS):
    day_of_year = h // 24

    # Seasonal variation (higher in winter)
    seasonal_factor = 0.9 + 0.3 * math.cos(2 * math.pi * (day_of_year - 30) / 365)

    # Wind is more variable than solar
    base = 0.50 * seasonal_factor
    noise = 0.20 * np.random.randn()

    cf = base + noise
    wind_cf.append(np.clip(cf, 0, 1))

wind_cf = np.array(wind_cf)

print(f"  Solar avg CF: {np.mean(solar_cf):.1%} (target: 30-33%)")
print(f"  Wind avg CF: {np.mean(wind_cf):.1%} (target: ~50%)")
print()

if np.mean(solar_cf) < 0.28:
    print("  ⚠️  Solar CF slightly low - adjusting...")
    solar_cf = solar_cf * (0.31 / np.mean(solar_cf))
    print(f"  Solar avg CF (adjusted): {np.mean(solar_cf):.1%}")

if np.mean(wind_cf) < 0.48:
    print("  ⚠️  Wind CF slightly low - adjusting...")
    wind_cf = wind_cf * (0.50 / np.mean(wind_cf))
    print(f"  Wind avg CF (adjusted): {np.mean(wind_cf):.1%}")

print()

# ============================================================================
# STEP 3: Calculate Marginal Costs (CORRECTED)
# ============================================================================

print("Step 3: Calculating marginal costs (OpEx only)...")

# TES Marginal Cost = Variable OpEx ONLY
tes_marginal_cost = tes_params['tes_turbine_opex_var']
print(f"  TES marginal cost: ${tes_marginal_cost:.2f}/MWh (variable OpEx)")

# Gas Marginal Cost = Fuel + Variable OpEx
gas_fuel_price = 4.0  # $/MMBTU
gas_heat_rate = 10.0  # MMBTU/MWh
gas_var_opex = 8.0    # $/MWh
gas_fuel_cost = gas_fuel_price * gas_heat_rate
gas_marginal_cost = gas_fuel_cost + gas_var_opex

print(f"  Gas fuel: ${gas_fuel_cost:.2f}/MWh (${gas_fuel_price}/MMBTU × {gas_heat_rate} MMBTU/MWh)")
print(f"  Gas var O&M: ${gas_var_opex:.2f}/MWh")
print(f"  Gas marginal cost: ${gas_marginal_cost:.2f}/MWh")
print()
print(f"  → TES is ${gas_marginal_cost - tes_marginal_cost:.2f}/MWh cheaper on marginal basis!")
print(f"  → TES should be dispatched whenever available")
print()

# ============================================================================
# STEP 4: System Configuration
# ============================================================================

datacenter_load_MW = 100
solar_MW = 300
wind_MW = 50
tes_storage_hours = 16

# Multiple turbine blocks for better turndown (Greg feedback)
num_turbine_blocks = 4
turbine_block_size_MW = 25
tes_discharge_MW = num_turbine_blocks * turbine_block_size_MW  # 100 MW total

tes_charge_MW = 100
gas_backup_MW = 100

tes_storage_MWh = tes_discharge_MW * tes_storage_hours

print("Step 4: System configuration...")
print(f"  Solar: {solar_MW} MW")
print(f"  Wind: {wind_MW} MW")
print(f"  TES: {tes_storage_MWh} MWh storage, {num_turbine_blocks}×{turbine_block_size_MW} MW turbine blocks = {tes_discharge_MW} MW total")
print(f"  Gas: {gas_backup_MW} MW")
print()

# ============================================================================
# STEP 5: Dispatch Analysis
# ============================================================================

print("Step 5: Running dispatch analysis...")

solar_gen = solar_MW * solar_cf
wind_gen = wind_MW * wind_cf
renewable_gen = solar_gen + wind_gen

load = np.ones(HOURS) * datacenter_load_MW
tes_soc = np.zeros(HOURS + 1)
tes_charge = np.zeros(HOURS)
tes_discharge = np.zeros(HOURS)
tes_blocks_active = np.zeros(HOURS)  # Track how many blocks are running
gas_dispatch = np.zeros(HOURS)
curtailment = np.zeros(HOURS)

tes_soc[0] = tes_storage_MWh * 0.3

for t in range(HOURS):
    surplus = renewable_gen[t] - load[t]

    if surplus > 0:
        # Excess renewable - charge TES
        charge_possible = min(
            surplus,
            tes_charge_MW,
            (tes_storage_MWh - tes_soc[t]) / tes_params['tes_heater_efficiency']
        )
        tes_charge[t] = charge_possible
        curtailment[t] = surplus - charge_possible

    else:
        # Deficit - use TES first (cheaper), then gas
        deficit = -surplus

        # TES discharge using multiple turbine blocks
        # Each block operates at high efficiency (39%) when on
        tes_thermal_available = tes_soc[t]
        tes_electric_available = tes_thermal_available * tes_params['tes_turbine_eff_max']

        # Calculate how many blocks to dispatch
        blocks_needed = np.ceil(deficit / turbine_block_size_MW)
        blocks_to_dispatch = int(min(blocks_needed, num_turbine_blocks))

        # Check if we have enough thermal energy for at least one block
        min_thermal_needed = turbine_block_size_MW / tes_params['tes_turbine_eff_max']

        if tes_thermal_available >= min_thermal_needed:
            # Dispatch blocks as needed
            tes_output_possible = blocks_to_dispatch * turbine_block_size_MW
            tes_output = min(deficit, tes_output_possible, tes_electric_available)
            tes_discharge[t] = tes_output / tes_params['tes_turbine_eff_max']
            tes_blocks_active[t] = blocks_to_dispatch
            deficit -= tes_output

        # Use gas for remainder
        gas_dispatch[t] = deficit

    # Update SOC
    charge_thermal = tes_charge[t] * tes_params['tes_heater_efficiency']
    discharge_thermal = tes_discharge[t]
    loss = tes_soc[t] * tes_params['tes_storage_loss_per_day'] / 24
    tes_soc[t+1] = tes_soc[t] + charge_thermal - discharge_thermal - loss

# Annual totals
solar_annual = np.sum(solar_gen)
wind_annual = np.sum(wind_gen)
tes_discharge_electric = np.sum(tes_discharge * tes_params['tes_turbine_eff_max'])
gas_annual = np.sum(gas_dispatch)
curtail_annual = np.sum(curtailment)
load_annual = np.sum(load)

cfe_pct = (solar_annual + wind_annual + tes_discharge_electric) / load_annual * 100

print("✓ Dispatch complete")
print()

# ============================================================================
# STEP 6: Results
# ============================================================================

print("="*80)
print("RESULTS")
print("="*80)
print()

print("Annual Generation:")
print(f"  Solar:        {solar_annual:>10,.0f} MWh ({solar_annual/load_annual*100:>5.1f}%)")
print(f"  Wind:         {wind_annual:>10,.0f} MWh ({wind_annual/load_annual*100:>5.1f}%)")
print(f"  TES Output:   {tes_discharge_electric:>10,.0f} MWh ({tes_discharge_electric/load_annual*100:>5.1f}%)")
print(f"  Gas Backup:   {gas_annual:>10,.0f} MWh ({gas_annual/load_annual*100:>5.1f}%)")
print(f"  Curtailment:  {curtail_annual:>10,.0f} MWh")
print(f"  Total Load:   {load_annual:>10,.0f} MWh")
print()
print(f"  CFE: {cfe_pct:.1f}%")
print()

# Capacity factors
solar_cf_actual = solar_annual / (solar_MW * 8760)
wind_cf_actual = wind_annual / (wind_MW * 8760)
tes_cf = tes_discharge_electric / (tes_discharge_MW * 8760)
gas_cf = gas_annual / (gas_backup_MW * 8760)

print("Capacity Factors:")
print(f"  Solar: {solar_cf_actual:.1%}")
print(f"  Wind:  {wind_cf_actual:.1%}")
print(f"  TES:   {tes_cf:.1%}")
print(f"  Gas:   {gas_cf:.1%}")
print()

# Turbine block utilization
print("Turbine Block Utilization:")
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = np.sum(tes_blocks_active == i)
    pct = hours_at_blocks / HOURS * 100
    print(f"  {i} blocks active: {hours_at_blocks:>4} hours ({pct:>5.1f}%)")
print()

# Costs
tes_var_cost = tes_discharge_electric * tes_marginal_cost / 1e6
gas_var_cost = gas_annual * gas_marginal_cost / 1e6

print("Variable Costs:")
print(f"  TES:  ${tes_var_cost:.2f}M/year")
print(f"  Gas:  ${gas_var_cost:.2f}M/year")
print()

# Save results
block_utilization = {}
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = int(np.sum(tes_blocks_active == i))
    block_utilization[f'{i}_blocks'] = hours_at_blocks

results = {
    'timestamp': datetime.now().isoformat(),
    'model_version': 'corrected_v3_multiple_blocks',
    'turbine_config': {
        'num_blocks': num_turbine_blocks,
        'block_size_MW': turbine_block_size_MW,
        'total_capacity_MW': tes_discharge_MW,
    },
    'resource_data': {
        'solar_cf_avg': float(np.mean(solar_cf)),
        'wind_cf_avg': float(np.mean(wind_cf)),
        'note': 'Roman-style profiles with target CFs',
    },
    'marginal_costs': {
        'tes': float(tes_marginal_cost),
        'gas': float(gas_marginal_cost),
        'tes_advantage': float(gas_marginal_cost - tes_marginal_cost),
    },
    'annual_MWh': {
        'solar': float(solar_annual),
        'wind': float(wind_annual),
        'tes_output': float(tes_discharge_electric),
        'gas': float(gas_annual),
        'curtailment': float(curtail_annual),
        'load': float(load_annual),
    },
    'capacity_factors': {
        'solar': float(solar_cf_actual),
        'wind': float(wind_cf_actual),
        'tes': float(tes_cf),
        'gas': float(gas_cf),
    },
    'block_utilization_hours': block_utilization,
    'performance': {
        'cfe_pct': float(cfe_pct),
    },
}

output_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/results_corrected_v3.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"✓ Results saved to: results_corrected_v3.json")
print()

print("="*80)
print("KEY IMPROVEMENTS FROM MEETING FEEDBACK")
print("="*80)
print()
print(f"✓ Solar CF:  22.1% → {solar_cf_actual:.1%}")
print(f"✓ Wind CF:   18.7% → {wind_cf_actual:.1%}")
print(f"✓ TES Cost:  $121/MWh (wrong) → ${tes_marginal_cost}/MWh (correct)")
print(f"✓ Gas Cost:  $40/MWh (incomplete) → ${gas_marginal_cost}/MWh (with O&M)")
print(f"✓ TES Util:  0.8% → {tes_cf:.1%}")
print(f"✓ Turbine:   Single 100 MW (40 MW min) → {num_turbine_blocks}×{turbine_block_size_MW} MW blocks ({turbine_block_size_MW} MW min)")
print()
