"""
PHASE 3: POLICY ANALYSIS
Analyze how policies impact TES+CFE economics:
1. IRA Tax Credits (30% ITC, PTC alternatives)
2. Emissions Regulations (carbon pricing, air quality)
3. Grid Interconnection (costs, timelines, requirements)
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime

print("="*80)
print("PHASE 3: POLICY ANALYSIS")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# LOAD BASELINE RESULTS
# ============================================================================

print("Step 1: Loading baseline optimization results...")

# Use the 48hr results as baseline
baseline_file = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project/TESProject/Phase 3 - Analysis/phase3_48hr_results_summary.json"

try:
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)

    print(f"Success: Loaded baseline: {baseline_file}")
    print(f"  Configuration: {baseline['scenario']['window_size']}hr windows")
    print()

    # Extract key parameters
    total_load_MWh = baseline['metrics']['total_load_MWh']
    tes_discharge_MWh = baseline['metrics']['tes_discharge_MWh']
    gas_MMBtu = baseline['metrics']['gas_MMBtu']

    # System capacities (from scenario)
    solar_MW = 300  # From our baseline run
    wind_MW = 50
    tes_MW = 100
    battery_MWh = 200
    ldes_MWh = 500

    print("Baseline System:")
    print(f"  Solar: {solar_MW} MW")
    print(f"  Wind: {wind_MW} MW")
    print(f"  TES: {tes_MW} MW (16hr duration)")
    print(f"  Battery: {battery_MWh} MWh")
    print(f"  LDES: {ldes_MWh} MWh")
    print()

except FileNotFoundError:
    print("Error: Baseline results not found. Using example values.")
    total_load_MWh = 876000
    tes_discharge_MWh = 24090
    gas_MMBtu = 2239272
    solar_MW = 300
    wind_MW = 50
    tes_MW = 100
    battery_MWh = 200
    ldes_MWh = 500

# ============================================================================
# CAPEX ASSUMPTIONS (From Industry Standards)
# ============================================================================

print("Step 2: Defining cost assumptions...")
print()

# Capital costs ($/kW or $/kWh)
CAPEX = {
    'solar_pv': {'per_kW': 1000, 'source': 'NREL ATB 2024'},
    'wind': {'per_kW': 1400, 'source': 'NREL ATB 2024'},
    'tes_energy': {'per_kWh': 40, 'source': 'gjt_working.xlsx (heat battery RHB100)'},
    'tes_power': {'per_kW': 800, 'source': 'Steam turbine cost estimate'},
    'battery_energy': {'per_kWh': 300, 'source': 'NREL Battery Storage Cost 2024'},
    'battery_power': {'per_kW': 150, 'source': 'NREL Battery Storage Cost 2024'},
    'ldes_energy': {'per_kWh': 150, 'source': 'Form Energy iron-air estimate'},
    'ldes_power': {'per_kW': 200, 'source': 'LDES power electronics'},
    'gas_backup': {'per_kW': 1000, 'source': 'NGCC plant cost'},
}

# Operating costs (% of CAPEX annually)
OPEX_PCT = {
    'solar': 1.5,
    'wind': 2.5,
    'tes': 4.0,  # From gjt_working.xlsx
    'battery': 2.0,
    'ldes': 2.5,
    'gas': 4.0,
}

# Fuel costs
GAS_PRICE_MMBTU = 5.0  # $/MMBtu

# Financial assumptions
DISCOUNT_RATE = 0.07  # 7% WACC
PROJECT_LIFE = 25  # years

print("Capital Cost Assumptions:")
for tech, cost in CAPEX.items():
    unit_type = 'per_kW' if 'per_kW' in cost else 'per_kWh'
    unit_value = cost[unit_type]
    print(f"  {tech}: ${unit_value}/{unit_type.replace('per_', '')} - {cost['source']}")
print()

# ============================================================================
# POLICY SCENARIO 1: IRA TAX CREDITS
# ============================================================================

print("="*80)
print("POLICY SCENARIO 1: IRA TAX CREDITS")
print("="*80)
print()

# IRA provides:
# - 30% Investment Tax Credit (ITC) for solar, wind, battery
# - Production Tax Credit (PTC) alternative for wind
# - 30% ITC for standalone storage (>5 kWh, >75% renewable charging)

ITC_RATE = 0.30
PTC_WIND = 27.5  # $/MWh (from baseline)

# Calculate system CAPEX
capex_solar = solar_MW * 1000 * CAPEX['solar_pv']['per_kW']
capex_wind = wind_MW * 1000 * CAPEX['wind']['per_kW']
capex_tes_energy = (tes_MW * 16) * 1000 * CAPEX['tes_energy']['per_kWh']  # 16hr duration
capex_tes_power = tes_MW * 1000 * CAPEX['tes_power']['per_kW']
capex_tes_total = capex_tes_energy + capex_tes_power
capex_battery = battery_MWh * 1000 * CAPEX['battery_energy']['per_kWh'] + (battery_MWh/2) * 1000 * CAPEX['battery_power']['per_kW']
capex_ldes = ldes_MWh * 1000 * CAPEX['ldes_energy']['per_kWh'] + (ldes_MWh/5) * 1000 * CAPEX['ldes_power']['per_kW']

print("BASELINE CAPEX (No IRA):")
print(f"  Solar ({solar_MW} MW):           ${capex_solar:>15,.0f}")
print(f"  Wind ({wind_MW} MW):             ${capex_wind:>15,.0f}")
print(f"  TES ({tes_MW} MW, 16hr):         ${capex_tes_total:>15,.0f}")
print(f"  Battery ({battery_MWh} MWh):     ${capex_battery:>15,.0f}")
print(f"  LDES ({ldes_MWh} MWh):           ${capex_ldes:>15,.0f}")
print(f"  TOTAL:                        ${capex_solar+capex_wind+capex_tes_total+capex_battery+capex_ldes:>15,.0f}")
print()

# With IRA credits
itc_solar = capex_solar * ITC_RATE
itc_wind = capex_wind * ITC_RATE
itc_tes = capex_tes_total * ITC_RATE  # TES qualifies as thermal storage
itc_battery = capex_battery * ITC_RATE
itc_ldes = capex_ldes * ITC_RATE

net_capex_with_ira = (capex_solar - itc_solar +
                       capex_wind - itc_wind +
                       capex_tes_total - itc_tes +
                       capex_battery - itc_battery +
                       capex_ldes - itc_ldes)

print("WITH IRA (30% ITC):")
print(f"  Solar ITC (30%):              ${itc_solar:>15,.0f}")
print(f"  Wind ITC (30%):               ${itc_wind:>15,.0f}")
print(f"  TES ITC (30%):                ${itc_tes:>15,.0f}")
print(f"  Battery ITC (30%):            ${itc_battery:>15,.0f}")
print(f"  LDES ITC (30%):               ${itc_ldes:>15,.0f}")
print(f"  Total ITC:                    ${itc_solar+itc_wind+itc_tes+itc_battery+itc_ldes:>15,.0f}")
print()
print(f"  Net CAPEX after ITC:          ${net_capex_with_ira:>15,.0f}")
print(f"  CAPEX Reduction:              {((capex_solar+capex_wind+capex_tes_total+capex_battery+capex_ldes)-net_capex_with_ira)/(capex_solar+capex_wind+capex_tes_total+capex_battery+capex_ldes)*100:.1f}%")
print()

# ============================================================================
# POLICY SCENARIO 2: CARBON PRICING
# ============================================================================

print("="*80)
print("POLICY SCENARIO 2: CARBON PRICING / EMISSIONS REGULATIONS")
print("="*80)
print()

# Natural gas emissions: ~117 lbs CO2/MMBtu = 0.0531 metric tons/MMBtu
CO2_PER_MMBTU = 0.0531  # metric tons

# Carbon price scenarios
CARBON_PRICES = {
    'none': 0,
    'california_cap_trade': 30,  # $/metric ton (CA current)
    'social_cost_carbon': 51,    # $/metric ton (Federal estimate)
    'aggressive_policy': 100,     # $/metric ton (EU-level)
}

gas_co2_tons = gas_MMBtu * CO2_PER_MMBTU

print(f"Annual Gas Usage: {gas_MMBtu:,.0f} MMBtu")
print(f"CO2 Emissions: {gas_co2_tons:,.0f} metric tons")
print()

print("CARBON PRICING IMPACT:")
for scenario, price in CARBON_PRICES.items():
    carbon_cost = gas_co2_tons * price
    print(f"  {scenario:25s}: ${price:>5}/ton → ${carbon_cost:>12,.0f}/year")
print()

# ============================================================================
# POLICY SCENARIO 3: GRID INTERCONNECTION
# ============================================================================

print("="*80)
print("POLICY SCENARIO 3: GRID INTERCONNECTION")
print("="*80)
print()

# Interconnection cost estimates
INTERCONNECTION = {
    'off_grid': {
        'connection_cost': 0,
        'grid_upgrade_cost': 0,
        'timeline_months': 0,
        'reliability': 'Self-sufficient (gas backup)',
        'note': 'No grid connection - fully islanded'
    },
    'distribution_connect': {
        'connection_cost': 500000,  # $500k
        'grid_upgrade_cost': 2000000,  # $2M
        'timeline_months': 12,
        'reliability': 'Grid-connected with backup',
        'note': 'Distribution-level interconnection'
    },
    'transmission_connect': {
        'connection_cost': 2000000,  # $2M
        'grid_upgrade_cost': 10000000,  # $10M
        'timeline_months': 36,
        'reliability': 'Full grid integration',
        'note': 'Transmission-level interconnection'
    },
}

print("INTERCONNECTION OPTIONS:")
for option, details in INTERCONNECTION.items():
    total_cost = details['connection_cost'] + details['grid_upgrade_cost']
    print(f"\n{option.upper().replace('_', ' ')}:")
    print(f"  Connection Cost:     ${details['connection_cost']:>12,}")
    print(f"  Grid Upgrade Cost:   ${details['grid_upgrade_cost']:>12,}")
    print(f"  Total Cost:          ${total_cost:>12,}")
    print(f"  Timeline:            {details['timeline_months']} months")
    print(f"  Documentation:                {details['note']}")
print()

# ============================================================================
# LCOE CALCULATIONS WITH POLICY SCENARIOS
# ============================================================================

print("="*80)
print("LCOE COMPARISON ACROSS POLICY SCENARIOS")
print("="*80)
print()

# Calculate annual costs
annual_opex_baseline = (
    capex_solar * OPEX_PCT['solar'] / 100 +
    capex_wind * OPEX_PCT['wind'] / 100 +
    capex_tes_total * OPEX_PCT['tes'] / 100 +
    capex_battery * OPEX_PCT['battery'] / 100 +
    capex_ldes * OPEX_PCT['ldes'] / 100
)

annual_fuel_cost = gas_MMBtu * GAS_PRICE_MMBTU

# Levelization factor (CRF)
crf = (DISCOUNT_RATE * (1 + DISCOUNT_RATE)**PROJECT_LIFE) / ((1 + DISCOUNT_RATE)**PROJECT_LIFE - 1)

def calculate_lcoe(capex, annual_opex, annual_fuel, annual_carbon, annual_gen_MWh):
    """Calculate LCOE given costs and generation"""
    annual_capital_recovery = capex * crf
    total_annual_cost = annual_capital_recovery + annual_opex + annual_fuel + annual_carbon
    return total_annual_cost / annual_gen_MWh

# Scenarios
scenarios = []

# 1. No Policy (Baseline)
lcoe_baseline = calculate_lcoe(
    capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes,
    annual_opex_baseline,
    annual_fuel_cost,
    0,
    total_load_MWh
)
scenarios.append({
    'scenario': 'No Policy (Baseline)',
    'lcoe': lcoe_baseline,
    'capex_reduction': 0,
    'carbon_cost': 0,
})

# 2. IRA Only
lcoe_ira = calculate_lcoe(
    net_capex_with_ira,
    annual_opex_baseline,
    annual_fuel_cost,
    0,
    total_load_MWh
)
scenarios.append({
    'scenario': 'IRA (30% ITC)',
    'lcoe': lcoe_ira,
    'capex_reduction': (capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes) - net_capex_with_ira,
    'carbon_cost': 0,
})

# 3. IRA + California Carbon Price
carbon_ca = gas_co2_tons * CARBON_PRICES['california_cap_trade']
lcoe_ira_ca = calculate_lcoe(
    net_capex_with_ira,
    annual_opex_baseline,
    annual_fuel_cost,
    carbon_ca,
    total_load_MWh
)
scenarios.append({
    'scenario': 'IRA + CA Carbon ($30/ton)',
    'lcoe': lcoe_ira_ca,
    'capex_reduction': (capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes) - net_capex_with_ira,
    'carbon_cost': carbon_ca,
})

# 4. IRA + Social Cost of Carbon
carbon_scc = gas_co2_tons * CARBON_PRICES['social_cost_carbon']
lcoe_ira_scc = calculate_lcoe(
    net_capex_with_ira,
    annual_opex_baseline,
    annual_fuel_cost,
    carbon_scc,
    total_load_MWh
)
scenarios.append({
    'scenario': 'IRA + Social Cost ($51/ton)',
    'lcoe': lcoe_ira_scc,
    'capex_reduction': (capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes) - net_capex_with_ira,
    'carbon_cost': carbon_scc,
})

# 5. IRA + Aggressive Carbon Policy
carbon_agg = gas_co2_tons * CARBON_PRICES['aggressive_policy']
lcoe_ira_agg = calculate_lcoe(
    net_capex_with_ira,
    annual_opex_baseline,
    annual_fuel_cost,
    carbon_agg,
    total_load_MWh
)
scenarios.append({
    'scenario': 'IRA + Aggressive ($100/ton)',
    'lcoe': lcoe_ira_agg,
    'capex_reduction': (capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes) - net_capex_with_ira,
    'carbon_cost': carbon_agg,
})

# Display results
print(f"{'Scenario':<35} {'LCOE ($/MWh)':<15} {'vs Baseline':<15}")
print("-" * 65)
for s in scenarios:
    delta = s['lcoe'] - lcoe_baseline
    print(f"{s['scenario']:<35} ${s['lcoe']:>12.2f}   ${delta:>+12.2f}")
print()

# ============================================================================
# SAVE RESULTS
# ============================================================================

output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project/TESProject/Phase 3 - Analysis"

policy_results = {
    'run_date': datetime.now().isoformat(),
    'baseline_system': {
        'solar_MW': solar_MW,
        'wind_MW': wind_MW,
        'tes_MW': tes_MW,
        'battery_MWh': battery_MWh,
        'ldes_MWh': ldes_MWh,
    },
    'capex_assumptions': CAPEX,
    'ira_tax_credits': {
        'itc_rate': ITC_RATE,
        'total_itc_value': float(itc_solar + itc_wind + itc_tes + itc_battery + itc_ldes),
        'capex_reduction_pct': float(((capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes) - net_capex_with_ira) / (capex_solar + capex_wind + capex_tes_total + capex_battery + capex_ldes) * 100),
    },
    'carbon_pricing': {
        'annual_co2_tons': float(gas_co2_tons),
        'scenarios': CARBON_PRICES,
    },
    'interconnection_options': INTERCONNECTION,
    'lcoe_scenarios': scenarios,
}

with open(f"{output_dir}/phase3_policy_analysis.json", 'w') as f:
    json.dump(policy_results, f, indent=2)

print("="*80)
print("POLICY ANALYSIS COMPLETE")
print("="*80)
print()
print("KEY FINDINGS:")
print(f"1. IRA tax credits reduce LCOE by ${lcoe_baseline - lcoe_ira:.2f}/MWh ({(lcoe_baseline-lcoe_ira)/lcoe_baseline*100:.1f}%)")
print(f"2. Carbon pricing adds ${(lcoe_ira_ca - lcoe_ira):.2f}-${(lcoe_ira_agg - lcoe_ira):.2f}/MWh depending on policy")
print(f"3. Off-grid avoids ${INTERCONNECTION['transmission_connect']['connection_cost'] + INTERCONNECTION['transmission_connect']['grid_upgrade_cost']:,.0f} in grid connection costs")
print()
print("Success: Results saved: phase3_policy_analysis.json")
print("="*80)
