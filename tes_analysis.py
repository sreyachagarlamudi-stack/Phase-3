"""
Thermal Energy Storage (TES) System Analysis
Architecture: Boiler + Steam Header + Multi-Block Turbine Configuration
"""

import sys
import os
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime

print("="*80)
print("TES SYSTEM ANALYSIS")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# Load System Parameters
# ============================================================================

print("Loading system parameters...")

excel_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/gjt_working_updated.xlsx"

tes_params_df = pd.read_excel(excel_path, sheet_name='TES_PARAMS')
tes_params = {}
for idx, row in tes_params_df.iterrows():
    tes_params[row['Parameter']] = row['Value']

print("Parameters loaded")
print(f"  Turbine OpEx (variable): ${tes_params['tes_turbine_opex_var']}/MWh")
print(f"  Boiler efficiency: {tes_params['boiler_efficiency']:.1%}")
print(f"  Boiler OpEx (variable): ${tes_params['boiler_opex_var']}/MWh_thermal")
print()

# ============================================================================
# Generate Resource Profiles
# ============================================================================

print("Generating resource profiles...")

HOURS = 8760
np.random.seed(42)

# Solar profile - AC basis, 30-33% capacity factor
solar_cf = []
for h in range(HOURS):
    hour_of_day = h % 24
    day_of_year = h // 24

    if 6 <= hour_of_day <= 18:
        daily_val = math.sin(math.pi * (hour_of_day - 6) / 12)
    else:
        daily_val = 0

    seasonal_factor = 0.9 + 0.2 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
    weather = 1.0 + 0.15 * np.random.randn()
    weather = np.clip(weather, 0.7, 1.2)

    cf = daily_val * seasonal_factor * weather * 0.35
    solar_cf.append(np.clip(cf, 0, 1))

solar_cf = np.array(solar_cf)

# Wind profile - 50% capacity factor
wind_cf = []
for h in range(HOURS):
    day_of_year = h // 24
    seasonal_factor = 0.9 + 0.3 * math.cos(2 * math.pi * (day_of_year - 30) / 365)
    base = 0.50 * seasonal_factor
    noise = 0.20 * np.random.randn()
    cf = base + noise
    wind_cf.append(np.clip(cf, 0, 1))

wind_cf = np.array(wind_cf)

print(f"  Solar CF: {np.mean(solar_cf):.1%}")
print(f"  Wind CF: {np.mean(wind_cf):.1%}")
print()

# Adjust to target capacity factors if needed
if np.mean(solar_cf) < 0.28:
    solar_cf = solar_cf * (0.31 / np.mean(solar_cf))
    print(f"  Solar CF (adjusted): {np.mean(solar_cf):.1%}")

if np.mean(wind_cf) < 0.48:
    wind_cf = wind_cf * (0.50 / np.mean(wind_cf))
    print(f"  Wind CF (adjusted): {np.mean(wind_cf):.1%}")

print()

# ============================================================================
# Calculate Marginal Operating Costs
# ============================================================================

print("Calculating marginal operating costs...")
print("  System: Boiler → Steam Header ← TES → Steam Turbine → Electricity")
print()

# TES discharge cost (turbine variable OpEx only)
tes_marginal_cost = tes_params['tes_turbine_opex_var']
print(f"  TES discharge: ${tes_marginal_cost:.2f}/MWh_electric")

# Boiler path: Fuel → Boiler → Thermal → Turbine → Electric
fuel_price = 4.0  # $/MMBTU
mmbtu_to_mwh_thermal = 0.293
boiler_efficiency = tes_params['boiler_efficiency']
turbine_efficiency = tes_params['tes_turbine_eff_max']

thermal_per_electric = 1.0 / turbine_efficiency
fuel_per_thermal_mwh = 1.0 / (mmbtu_to_mwh_thermal * boiler_efficiency)
fuel_needed = thermal_per_electric * fuel_per_thermal_mwh

boiler_fuel_cost = fuel_needed * fuel_price
boiler_var_opex = thermal_per_electric * tes_params['boiler_opex_var']
turbine_var_opex = tes_params['tes_turbine_opex_var']
boiler_marginal_cost = boiler_fuel_cost + boiler_var_opex + turbine_var_opex

print(f"  Boiler path: ${boiler_marginal_cost:.2f}/MWh_electric")
print(f"    - Fuel: ${boiler_fuel_cost:.2f}/MWh")
print(f"    - Boiler OpEx: ${boiler_var_opex:.2f}/MWh")
print(f"    - Turbine OpEx: ${turbine_var_opex:.2f}/MWh")
print()
print(f"  Dispatch priority: Solar/Wind → TES → Boiler")
print()

# ============================================================================
# System Configuration
# ============================================================================

datacenter_load_MW = 100
solar_MW = 300
wind_MW = 50
tes_storage_hours = 16

# Multi-block turbine configuration
num_turbine_blocks = 4
turbine_block_size_MW = 25
tes_discharge_MW = num_turbine_blocks * turbine_block_size_MW

tes_charge_MW = 100
boiler_thermal_MW = tes_discharge_MW / turbine_efficiency
boiler_electric_equivalent = 100

tes_storage_MWh = tes_discharge_MW * tes_storage_hours

print("System configuration:")
print(f"  Solar: {solar_MW} MW")
print(f"  Wind: {wind_MW} MW")
print(f"  TES: {tes_storage_MWh} MWh storage, {tes_charge_MW} MW charge")
print(f"  Steam turbine: {num_turbine_blocks}×{turbine_block_size_MW} MW blocks = {tes_discharge_MW} MW total")
print(f"  Boiler: {boiler_thermal_MW:.0f} MW_thermal ({boiler_electric_equivalent} MW_electric equivalent)")
print()

# ============================================================================
# Dispatch Analysis
# ============================================================================

print("Running dispatch analysis...")

solar_gen = solar_MW * solar_cf
wind_gen = wind_MW * wind_cf
renewable_gen = solar_gen + wind_gen

load = np.ones(HOURS) * datacenter_load_MW
tes_soc = np.zeros(HOURS + 1)
tes_charge = np.zeros(HOURS)
tes_discharge = np.zeros(HOURS)
tes_blocks_active = np.zeros(HOURS)
boiler_thermal = np.zeros(HOURS)
boiler_blocks_active = np.zeros(HOURS)
curtailment = np.zeros(HOURS)

tes_soc[0] = tes_storage_MWh * 0.3

for t in range(HOURS):
    surplus = renewable_gen[t] - load[t]

    if surplus > 0:
        # Charge TES with excess renewable
        charge_possible = min(
            surplus,
            tes_charge_MW,
            (tes_storage_MWh - tes_soc[t]) / tes_params['tes_heater_efficiency']
        )
        tes_charge[t] = charge_possible
        curtailment[t] = surplus - charge_possible

    else:
        # Deficit - dispatch TES first, then boiler
        deficit = -surplus

        # TES discharge to steam header
        tes_thermal_available = tes_soc[t]
        tes_electric_available = tes_thermal_available * turbine_efficiency

        blocks_needed = np.ceil(deficit / turbine_block_size_MW)
        min_thermal_needed = turbine_block_size_MW / turbine_efficiency

        tes_blocks = 0
        if tes_thermal_available >= min_thermal_needed:
            tes_blocks = int(min(blocks_needed, num_turbine_blocks,
                               np.floor(tes_thermal_available / min_thermal_needed)))
            tes_electric_output = min(deficit, tes_blocks * turbine_block_size_MW, tes_electric_available)
            tes_discharge[t] = tes_electric_output / turbine_efficiency
            tes_blocks_active[t] = tes_blocks
            deficit -= tes_electric_output

        # Boiler for remaining deficit
        if deficit > 0.01:
            boiler_blocks_needed = np.ceil(deficit / turbine_block_size_MW)
            boiler_blocks = int(min(boiler_blocks_needed, num_turbine_blocks - tes_blocks))

            boiler_electric_output = min(deficit, boiler_blocks * turbine_block_size_MW)
            boiler_thermal[t] = boiler_electric_output / turbine_efficiency
            boiler_blocks_active[t] = boiler_blocks
            deficit -= boiler_electric_output

    # Update TES state of charge
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

print("Dispatch complete")
print()

# ============================================================================
# Results
# ============================================================================

print("="*80)
print("RESULTS")
print("="*80)
print()

print("Annual Generation:")
print(f"  Solar:              {solar_annual:>10,.0f} MWh ({solar_annual/load_annual*100:>5.1f}%)")
print(f"  Wind:               {wind_annual:>10,.0f} MWh ({wind_annual/load_annual*100:>5.1f}%)")
print(f"  TES → Turbine:      {tes_discharge_electric:>10,.0f} MWh ({tes_discharge_electric/load_annual*100:>5.1f}%)")
print(f"  Boiler → Turbine:   {boiler_electric:>10,.0f} MWh ({boiler_electric/load_annual*100:>5.1f}%)")
print(f"  Curtailment:        {curtail_annual:>10,.0f} MWh")
print(f"  Total Load:         {load_annual:>10,.0f} MWh")
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

# Turbine block utilization
print("Steam Turbine Block Utilization:")
total_blocks_active = tes_blocks_active + boiler_blocks_active
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = np.sum(total_blocks_active == i)
    pct = hours_at_blocks / HOURS * 100
    print(f"  {i} blocks active: {hours_at_blocks:>4} hours ({pct:>5.1f}%)")
print()

print("  Heat Source:")
print(f"    TES only:        {np.sum((tes_blocks_active > 0) & (boiler_blocks_active == 0)):>4} hours")
print(f"    Boiler only:     {np.sum((tes_blocks_active == 0) & (boiler_blocks_active > 0)):>4} hours")
print(f"    Both:            {np.sum((tes_blocks_active > 0) & (boiler_blocks_active > 0)):>4} hours")
print(f"    Neither:         {np.sum((tes_blocks_active == 0) & (boiler_blocks_active == 0)):>4} hours")
print()

# Variable costs
tes_var_cost = tes_discharge_electric * tes_marginal_cost / 1e6
boiler_var_cost = boiler_electric * boiler_marginal_cost / 1e6

boiler_thermal_annual = np.sum(boiler_thermal)
boiler_fuel_annual = boiler_thermal_annual / boiler_efficiency / mmbtu_to_mwh_thermal * fuel_price / 1e6
boiler_opex_annual = boiler_thermal_annual * tes_params['boiler_opex_var'] / 1e6
turbine_opex_from_boiler = boiler_electric * tes_params['tes_turbine_opex_var'] / 1e6

print("Variable Operating Costs:")
print(f"  TES discharge:   ${tes_var_cost:.2f}M/year")
print(f"  Boiler path:     ${boiler_var_cost:.2f}M/year")
print(f"    - Fuel:        ${boiler_fuel_annual:.2f}M/year")
print(f"    - Boiler OpEx: ${boiler_opex_annual:.2f}M/year")
print(f"    - Turbine OpEx:${turbine_opex_from_boiler:.2f}M/year")
print()

# Save results
block_utilization = {}
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = int(np.sum(total_blocks_active == i))
    block_utilization[f'{i}_blocks'] = hours_at_blocks

results = {
    'timestamp': datetime.now().isoformat(),
    'model_version': 'v4_boiler_steam_header',
    'architecture': 'Boiler + Steam Header with Multi-Block Turbine',
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
    },
    'marginal_costs': {
        'tes_discharge': float(tes_marginal_cost),
        'boiler_path': float(boiler_marginal_cost),
        'differential': float(boiler_marginal_cost - tes_marginal_cost),
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

output_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/tes_results.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"Results saved to: tes_results.json")
print()
print("="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print()
