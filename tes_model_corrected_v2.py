"""
TES Model - CORRECTED VERSION v4
Uses proper Roman-style capacity factors while waiting for actual 8760 data
Fixes based on June 24 meeting feedback
V3: Multiple turbine blocks (4×25 MW) for better turndown flexibility
V4: Boiler + steam header architecture (replaces NGPP)
    - Boiler burns fuel → thermal energy
    - Steam header receives heat from TES or boiler
    - Steam turbine converts thermal → electric
"""

import sys
import os
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime

print("="*80)
print("TES ANALYSIS - CORRECTED MODEL V4 (Boiler + Steam Header)")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# STEP 1: Load TES Parameters from Excel
# ============================================================================

print("Step 1: Loading TES and boiler parameters...")

excel_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/gjt_working_updated.xlsx"

# Load TES parameters
tes_params_df = pd.read_excel(excel_path, sheet_name='TES_PARAMS')
tes_params = {}
for idx, row in tes_params_df.iterrows():
    tes_params[row['Parameter']] = row['Value']

print("✓ TES Parameters Loaded")
print(f"  Turbine OpEx (variable): ${tes_params['tes_turbine_opex_var']}/MWh")
print(f"  Boiler efficiency: {tes_params['boiler_efficiency']:.1%}")
print(f"  Boiler OpEx (variable): ${tes_params['boiler_opex_var']}/MWh_thermal")
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
print("  Architecture: Boiler → Steam Header ← TES → Steam Turbine → Electricity")
print()

# TES Marginal Cost = Variable OpEx ONLY (thermal already stored)
tes_marginal_cost = tes_params['tes_turbine_opex_var']
print(f"  TES discharge marginal cost: ${tes_marginal_cost:.2f}/MWh_electric")
print(f"    (turbine variable OpEx only)")

# Boiler path: Fuel → Boiler → Thermal → Turbine → Electric
# To produce 1 MWh_electric:
fuel_price = 4.0  # $/MMBTU
mmbtu_to_mwh_thermal = 0.293  # MMBTU to MWh conversion
boiler_efficiency = tes_params['boiler_efficiency']
turbine_efficiency = tes_params['tes_turbine_eff_max']

# Thermal energy needed for 1 MWh electric
thermal_per_electric = 1.0 / turbine_efficiency  # MWh_thermal per MWh_electric

# Fuel needed (MMBTU) to produce that thermal energy
fuel_per_thermal_mwh = 1.0 / (mmbtu_to_mwh_thermal * boiler_efficiency)  # MMBTU per MWh_thermal
fuel_needed = thermal_per_electric * fuel_per_thermal_mwh  # MMBTU per MWh_electric

# Costs per MWh_electric
boiler_fuel_cost = fuel_needed * fuel_price
boiler_var_opex = thermal_per_electric * tes_params['boiler_opex_var']
turbine_var_opex = tes_params['tes_turbine_opex_var']
boiler_marginal_cost = boiler_fuel_cost + boiler_var_opex + turbine_var_opex

print()
print(f"  Boiler path marginal cost: ${boiler_marginal_cost:.2f}/MWh_electric")
print(f"    - Fuel: ${boiler_fuel_cost:.2f}/MWh ({fuel_needed:.1f} MMBTU @ ${fuel_price}/MMBTU)")
print(f"    - Boiler var OpEx: ${boiler_var_opex:.2f}/MWh ({thermal_per_electric:.2f} MWh_thermal @ ${tes_params['boiler_opex_var']}/MWh)")
print(f"    - Turbine var OpEx: ${turbine_var_opex:.2f}/MWh")
print()
print(f"  → TES is ${boiler_marginal_cost - tes_marginal_cost:.2f}/MWh cheaper than boiler path!")
print(f"  → Dispatch priority: Solar/Wind → TES → Boiler")
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

# Boiler for backup thermal generation (replaces NGPP)
boiler_thermal_MW = tes_discharge_MW / turbine_efficiency  # Size to match turbine capacity
boiler_electric_equivalent = 100  # MW electric equivalent through turbine

tes_storage_MWh = tes_discharge_MW * tes_storage_hours

print("Step 4: System configuration...")
print(f"  Solar: {solar_MW} MW")
print(f"  Wind: {wind_MW} MW")
print(f"  TES: {tes_storage_MWh} MWh storage, {tes_charge_MW} MW charge")
print(f"  Steam Header + Turbine: {num_turbine_blocks}×{turbine_block_size_MW} MW blocks = {tes_discharge_MW} MW total")
print(f"    - Heat sources: TES storage OR Boiler")
print(f"  Boiler: {boiler_thermal_MW:.0f} MW_thermal ({boiler_electric_equivalent} MW_electric equivalent)")
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
tes_discharge = np.zeros(HOURS)  # Thermal discharge from TES (MWh_thermal)
tes_blocks_active = np.zeros(HOURS)  # Track how many blocks are running
boiler_thermal = np.zeros(HOURS)  # Thermal output from boiler (MWh_thermal)
boiler_blocks_active = np.zeros(HOURS)  # Blocks running on boiler heat
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
        # Deficit - use TES first (cheaper), then boiler
        deficit = -surplus

        # Step 1: TES discharge to steam header
        # Each turbine block operates at high efficiency (39%) when on
        tes_thermal_available = tes_soc[t]
        tes_electric_available = tes_thermal_available * turbine_efficiency

        # Calculate how many blocks needed for total deficit
        blocks_needed = np.ceil(deficit / turbine_block_size_MW)

        # Check if we have enough TES thermal for at least one block
        min_thermal_needed = turbine_block_size_MW / turbine_efficiency

        tes_blocks = 0
        if tes_thermal_available >= min_thermal_needed:
            # Use TES for as many blocks as possible
            tes_blocks = int(min(blocks_needed, num_turbine_blocks,
                               np.floor(tes_thermal_available / min_thermal_needed)))
            tes_electric_output = min(deficit, tes_blocks * turbine_block_size_MW, tes_electric_available)
            tes_discharge[t] = tes_electric_output / turbine_efficiency  # Thermal consumed
            tes_blocks_active[t] = tes_blocks
            deficit -= tes_electric_output

        # Step 2: Boiler for remaining deficit
        if deficit > 0.01:  # Small threshold to avoid numerical issues
            # Calculate blocks needed for remaining deficit
            boiler_blocks_needed = np.ceil(deficit / turbine_block_size_MW)
            boiler_blocks = int(min(boiler_blocks_needed, num_turbine_blocks - tes_blocks))

            # Boiler generates thermal, which goes through turbine
            boiler_electric_output = min(deficit, boiler_blocks * turbine_block_size_MW)
            boiler_thermal[t] = boiler_electric_output / turbine_efficiency  # Thermal needed
            boiler_blocks_active[t] = boiler_blocks
            deficit -= boiler_electric_output

    # Update SOC
    charge_thermal = tes_charge[t] * tes_params['tes_heater_efficiency']
    discharge_thermal = tes_discharge[t]
    loss = tes_soc[t] * tes_params['tes_storage_loss_per_day'] / 24
    tes_soc[t+1] = tes_soc[t] + charge_thermal - discharge_thermal - loss

# Annual totals
solar_annual = np.sum(solar_gen)
wind_annual = np.sum(wind_gen)
tes_discharge_electric = np.sum(tes_discharge * turbine_efficiency)
boiler_electric = np.sum(boiler_thermal * turbine_efficiency)
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
print(f"  Solar:           {solar_annual:>10,.0f} MWh ({solar_annual/load_annual*100:>5.1f}%)")
print(f"  Wind:            {wind_annual:>10,.0f} MWh ({wind_annual/load_annual*100:>5.1f}%)")
print(f"  TES → Turbine:   {tes_discharge_electric:>10,.0f} MWh ({tes_discharge_electric/load_annual*100:>5.1f}%)")
print(f"  Boiler → Turbine:{boiler_electric:>10,.0f} MWh ({boiler_electric/load_annual*100:>5.1f}%)")
print(f"  Curtailment:     {curtail_annual:>10,.0f} MWh")
print(f"  Total Load:      {load_annual:>10,.0f} MWh")
print()
print(f"  CFE: {cfe_pct:.1f}%")
print()

# Capacity factors
solar_cf_actual = solar_annual / (solar_MW * 8760)
wind_cf_actual = wind_annual / (wind_MW * 8760)
tes_cf = tes_discharge_electric / (tes_discharge_MW * 8760)
boiler_cf = boiler_electric / (boiler_electric_equivalent * 8760)

print("Capacity Factors:")
print(f"  Solar:  {solar_cf_actual:.1%}")
print(f"  Wind:   {wind_cf_actual:.1%}")
print(f"  TES:    {tes_cf:.1%}")
print(f"  Boiler: {boiler_cf:.1%}")
print()

# Turbine block utilization by heat source
print("Steam Header & Turbine Block Utilization:")
total_blocks_active = tes_blocks_active + boiler_blocks_active
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = np.sum(total_blocks_active == i)
    pct = hours_at_blocks / HOURS * 100
    print(f"  {i} blocks active: {hours_at_blocks:>4} hours ({pct:>5.1f}%)")
print()

print("  Heat Source Breakdown:")
print(f"    TES only:         {np.sum((tes_blocks_active > 0) & (boiler_blocks_active == 0)):>4} hours")
print(f"    Boiler only:      {np.sum((tes_blocks_active == 0) & (boiler_blocks_active > 0)):>4} hours")
print(f"    Both (TES+Boil):  {np.sum((tes_blocks_active > 0) & (boiler_blocks_active > 0)):>4} hours")
print(f"    Neither:          {np.sum((tes_blocks_active == 0) & (boiler_blocks_active == 0)):>4} hours")
print()

# Costs
tes_var_cost = tes_discharge_electric * tes_marginal_cost / 1e6
boiler_var_cost = boiler_electric * boiler_marginal_cost / 1e6

# Detailed boiler cost breakdown
boiler_thermal_annual = np.sum(boiler_thermal)
boiler_fuel_annual = boiler_thermal_annual / boiler_efficiency / mmbtu_to_mwh_thermal * fuel_price / 1e6
boiler_opex_annual = boiler_thermal_annual * tes_params['boiler_opex_var'] / 1e6
turbine_opex_from_boiler = boiler_electric * tes_params['tes_turbine_opex_var'] / 1e6

print("Variable Costs:")
print(f"  TES discharge:      ${tes_var_cost:.2f}M/year (turbine OpEx)")
print(f"  Boiler path:        ${boiler_var_cost:.2f}M/year")
print(f"    - Fuel:           ${boiler_fuel_annual:.2f}M/year ({boiler_thermal_annual/1e3:.1f} GWh_thermal)")
print(f"    - Boiler OpEx:    ${boiler_opex_annual:.2f}M/year")
print(f"    - Turbine OpEx:   ${turbine_opex_from_boiler:.2f}M/year")
print()

# Save results
block_utilization = {}
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = int(np.sum(tes_blocks_active == i))
    block_utilization[f'{i}_blocks'] = hours_at_blocks

results = {
    'timestamp': datetime.now().isoformat(),
    'model_version': 'corrected_v4_boiler_steam_header',
    'architecture': 'Boiler + Steam Header (replaces NGPP)',
    'turbine_config': {
        'num_blocks': num_turbine_blocks,
        'block_size_MW': turbine_block_size_MW,
        'total_capacity_MW': tes_discharge_MW,
        'efficiency': float(turbine_efficiency),
    },
    'boiler_config': {
        'thermal_capacity_MW': float(boiler_thermal_MW),
        'electric_equivalent_MW': boiler_electric_equivalent,
        'efficiency': float(boiler_efficiency),
        'fuel_price_per_mmbtu': fuel_price,
    },
    'resource_data': {
        'solar_cf_avg': float(np.mean(solar_cf)),
        'wind_cf_avg': float(np.mean(wind_cf)),
        'note': 'Roman-style profiles with target CFs',
    },
    'marginal_costs': {
        'tes_discharge': float(tes_marginal_cost),
        'boiler_path': float(boiler_marginal_cost),
        'tes_advantage': float(boiler_marginal_cost - tes_marginal_cost),
    },
    'annual_MWh': {
        'solar': float(solar_annual),
        'wind': float(wind_annual),
        'tes_output': float(tes_discharge_electric),
        'boiler_output': float(boiler_electric),
        'boiler_thermal': float(boiler_thermal_annual),
        'curtailment': float(curtail_annual),
        'load': float(load_annual),
    },
    'capacity_factors': {
        'solar': float(solar_cf_actual),
        'wind': float(wind_cf_actual),
        'tes': float(tes_cf),
        'boiler': float(boiler_cf),
    },
    'block_utilization_hours': block_utilization,
    'variable_costs_M_per_year': {
        'tes': float(tes_var_cost),
        'boiler': float(boiler_var_cost),
        'boiler_fuel': float(boiler_fuel_annual),
        'boiler_opex': float(boiler_opex_annual),
        'boiler_turbine_opex': float(turbine_opex_from_boiler),
    },
    'performance': {
        'cfe_pct': float(cfe_pct),
    },
}

output_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/results_corrected_v4.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"✓ Results saved to: results_corrected_v4.json")
print()

print("="*80)
print("KEY IMPROVEMENTS FROM MEETING FEEDBACK")
print("="*80)
print()
print(f"✓ Solar CF:   22.1% → {solar_cf_actual:.1%}")
print(f"✓ Wind CF:    18.7% → {wind_cf_actual:.1%}")
print(f"✓ TES Cost:   $121/MWh (wrong) → ${tes_marginal_cost}/MWh (correct)")
print(f"✓ Boiler Cost: ${boiler_marginal_cost:.1f}/MWh (fuel+boiler+turbine OpEx)")
print(f"✓ TES Util:   0.8% → {tes_cf:.1%}")
print(f"✓ Turbine:    Single 100 MW (40 MW min) → {num_turbine_blocks}×{turbine_block_size_MW} MW blocks ({turbine_block_size_MW} MW min)")
print(f"✓ Architecture: NGPP (direct electric) → Boiler + Steam Header (thermal → electric)")
print()
