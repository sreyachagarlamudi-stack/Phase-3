"""
Thermal Energy Storage (TES) + Battery Energy Storage System (BESS) Analysis
Architecture: Boiler + Steam Header + Multi-Block Turbine + BESS
"""

import sys
import os
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime

print("="*80)
print("TES + BESS SYSTEM ANALYSIS")
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

# BESS parameters
bess_params = {
    'bess_power_MW': 50,  # Power capacity
    'bess_energy_MWh': 200,  # 4-hour duration
    'bess_rte': 0.88,  # Round-trip efficiency
    'bess_opex_var': 0.5,  # $/MWh variable OpEx
}

print("Parameters loaded")
print(f"  TES turbine OpEx: ${tes_params['tes_turbine_opex_var']}/MWh")
print(f"  Boiler efficiency: {tes_params['boiler_efficiency']:.1%}")
print(f"  BESS: {bess_params['bess_power_MW']} MW / {bess_params['bess_energy_MWh']} MWh")
print(f"  BESS RTE: {bess_params['bess_rte']:.1%}")
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

# Adjust to target capacity factors
if np.mean(solar_cf) < 0.28:
    solar_cf = solar_cf * (0.31 / np.mean(solar_cf))
if np.mean(wind_cf) < 0.48:
    wind_cf = wind_cf * (0.50 / np.mean(wind_cf))

print(f"  Solar CF: {np.mean(solar_cf):.1%}")
print(f"  Wind CF: {np.mean(wind_cf):.1%}")
print()

# ============================================================================
# Calculate Marginal Operating Costs
# ============================================================================

print("Calculating marginal operating costs...")

# TES discharge cost
tes_marginal_cost = tes_params['tes_turbine_opex_var']

# BESS discharge cost (includes round-trip losses)
bess_marginal_cost = bess_params['bess_opex_var']

# Boiler path cost
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

print(f"  Marginal costs ($/MWh_electric):")
print(f"    BESS discharge:  ${bess_marginal_cost:.2f}")
print(f"    TES discharge:   ${tes_marginal_cost:.2f}")
print(f"    Boiler path:     ${boiler_marginal_cost:.2f}")
print()
print(f"  Dispatch priority: Solar/Wind → BESS → TES → Boiler")
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
print(f"  BESS: {bess_params['bess_power_MW']} MW / {bess_params['bess_energy_MWh']} MWh")
print(f"  TES: {tes_storage_MWh} MWh storage, {tes_charge_MW} MW charge")
print(f"  Steam turbine: {num_turbine_blocks}×{turbine_block_size_MW} MW blocks")
print(f"  Boiler: {boiler_thermal_MW:.0f} MW_thermal")
print()

# ============================================================================
# Dispatch Analysis
# ============================================================================

print("Running dispatch analysis...")

solar_gen = solar_MW * solar_cf
wind_gen = wind_MW * wind_cf
renewable_gen = solar_gen + wind_gen

load = np.ones(HOURS) * datacenter_load_MW

# Storage states
bess_soc = np.zeros(HOURS + 1)
bess_charge = np.zeros(HOURS)
bess_discharge = np.zeros(HOURS)

tes_soc = np.zeros(HOURS + 1)
tes_charge = np.zeros(HOURS)
tes_discharge = np.zeros(HOURS)
tes_blocks_active = np.zeros(HOURS)

boiler_thermal = np.zeros(HOURS)
boiler_blocks_active = np.zeros(HOURS)
curtailment = np.zeros(HOURS)

# Initial states
bess_soc[0] = bess_params['bess_energy_MWh'] * 0.5
tes_soc[0] = tes_storage_MWh * 0.3

for t in range(HOURS):
    surplus = renewable_gen[t] - load[t]

    if surplus > 0:
        # Charge storage with excess renewable
        # Priority: BESS first (higher efficiency), then TES

        remaining_surplus = surplus

        # Charge BESS
        bess_charge_possible = min(
            remaining_surplus,
            bess_params['bess_power_MW'],
            (bess_params['bess_energy_MWh'] - bess_soc[t]) / bess_params['bess_rte']
        )
        bess_charge[t] = bess_charge_possible
        remaining_surplus -= bess_charge_possible

        # Charge TES with remaining surplus
        tes_charge_possible = min(
            remaining_surplus,
            tes_charge_MW,
            (tes_storage_MWh - tes_soc[t]) / tes_params['tes_heater_efficiency']
        )
        tes_charge[t] = tes_charge_possible
        remaining_surplus -= tes_charge_possible

        curtailment[t] = remaining_surplus

    else:
        # Deficit - dispatch storage and boiler
        # Priority: BESS (cheapest) → TES → Boiler
        deficit = -surplus

        # BESS discharge
        bess_available = bess_soc[t]
        bess_discharge_possible = min(deficit, bess_params['bess_power_MW'], bess_available)
        bess_discharge[t] = bess_discharge_possible
        deficit -= bess_discharge_possible

        # TES discharge
        if deficit > 0.01:
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

    # Update storage states
    bess_soc[t+1] = bess_soc[t] + bess_charge[t] * bess_params['bess_rte'] - bess_discharge[t]

    charge_thermal = tes_charge[t] * tes_params['tes_heater_efficiency']
    discharge_thermal = tes_discharge[t]
    loss = tes_soc[t] * tes_params['tes_storage_loss_per_day'] / 24
    tes_soc[t+1] = tes_soc[t] + charge_thermal - discharge_thermal - loss

# Annual totals
solar_annual = np.sum(solar_gen)
wind_annual = np.sum(wind_gen)
bess_discharge_annual = np.sum(bess_discharge)
tes_discharge_electric = np.sum(tes_discharge * turbine_efficiency)
boiler_electric = np.sum(boiler_thermal * turbine_efficiency)
curtail_annual = np.sum(curtailment)
load_annual = np.sum(load)

cfe_pct = (solar_annual + wind_annual + tes_discharge_electric + bess_discharge_annual) / load_annual * 100

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
print(f"  BESS discharge:     {bess_discharge_annual:>10,.0f} MWh ({bess_discharge_annual/load_annual*100:>5.1f}%)")
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
bess_cf = bess_discharge_annual / (bess_params['bess_power_MW'] * 8760)
tes_cf = tes_discharge_electric / (tes_discharge_MW * 8760)
boiler_cf = boiler_electric / (boiler_electric_equivalent * 8760)

print("Capacity Factors:")
print(f"  Solar:  {solar_cf_actual:.1%}")
print(f"  Wind:   {wind_cf_actual:.1%}")
print(f"  BESS:   {bess_cf:.1%}")
print(f"  TES:    {tes_cf:.1%}")
print(f"  Boiler: {boiler_cf:.1%}")
print()

# Utilization breakdown
print("Storage Utilization:")
print(f"  BESS cycles: {np.sum(bess_discharge) / bess_params['bess_energy_MWh']:.1f} cycles/year")
print(f"  BESS hours active: {np.sum(bess_discharge > 0)} hours")
print(f"  TES hours active: {np.sum(tes_blocks_active > 0)} hours")
print()

# Steam turbine blocks
print("Steam Turbine Block Utilization:")
total_blocks_active = tes_blocks_active + boiler_blocks_active
for i in range(num_turbine_blocks + 1):
    hours_at_blocks = np.sum(total_blocks_active == i)
    pct = hours_at_blocks / HOURS * 100
    print(f"  {i} blocks: {hours_at_blocks:>4} hours ({pct:>5.1f}%)")
print()

print("  Heat Source:")
print(f"    TES only:    {np.sum((tes_blocks_active > 0) & (boiler_blocks_active == 0)):>4} hours")
print(f"    Boiler only: {np.sum((tes_blocks_active == 0) & (boiler_blocks_active > 0)):>4} hours")
print(f"    Both:        {np.sum((tes_blocks_active > 0) & (boiler_blocks_active > 0)):>4} hours")
print()

# Variable costs
bess_var_cost = bess_discharge_annual * bess_marginal_cost / 1e6
tes_var_cost = tes_discharge_electric * tes_marginal_cost / 1e6
boiler_var_cost = boiler_electric * boiler_marginal_cost / 1e6

boiler_thermal_annual = np.sum(boiler_thermal)
boiler_fuel_annual = boiler_thermal_annual / boiler_efficiency / mmbtu_to_mwh_thermal * fuel_price / 1e6

print("Variable Operating Costs:")
print(f"  BESS:        ${bess_var_cost:.2f}M/year")
print(f"  TES:         ${tes_var_cost:.2f}M/year")
print(f"  Boiler path: ${boiler_var_cost:.2f}M/year")
print(f"    - Fuel:    ${boiler_fuel_annual:.2f}M/year")
print()

# Save results
results = {
    'timestamp': datetime.now().isoformat(),
    'model_version': 'v5_tes_bess_boiler',
    'architecture': 'BESS + TES + Boiler + Steam Header',
    'system_config': {
        'solar_MW': solar_MW,
        'wind_MW': wind_MW,
        'bess_MW': bess_params['bess_power_MW'],
        'bess_MWh': bess_params['bess_energy_MWh'],
        'tes_MWh': tes_storage_MWh,
        'turbine_blocks': num_turbine_blocks,
        'block_size_MW': turbine_block_size_MW,
    },
    'marginal_costs': {
        'bess': float(bess_marginal_cost),
        'tes': float(tes_marginal_cost),
        'boiler': float(boiler_marginal_cost),
    },
    'annual_MWh': {
        'solar': float(solar_annual),
        'wind': float(wind_annual),
        'bess_discharge': float(bess_discharge_annual),
        'tes_output': float(tes_discharge_electric),
        'boiler_output': float(boiler_electric),
        'curtailment': float(curtail_annual),
        'load': float(load_annual),
    },
    'capacity_factors': {
        'solar': float(solar_cf_actual),
        'wind': float(wind_cf_actual),
        'bess': float(bess_cf),
        'tes': float(tes_cf),
        'boiler': float(boiler_cf),
    },
    'variable_costs_M_per_year': {
        'bess': float(bess_var_cost),
        'tes': float(tes_var_cost),
        'boiler': float(boiler_var_cost),
    },
    'performance': {
        'cfe_pct': float(cfe_pct),
        'bess_cycles_per_year': float(np.sum(bess_discharge) / bess_params['bess_energy_MWh']),
    },
}

output_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 3 - Analysis/tes_bess_results.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"Results saved to: tes_bess_results.json")
print()
print("="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print()
