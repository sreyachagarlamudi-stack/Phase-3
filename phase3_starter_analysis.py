"""
Phase 3 Starter Analysis
========================
Simplified version using the working demo module with HiGHS solver.
This will help you start Phase 3 analysis without needing CPLEX.

Analysis Goals:
1. Find optimal solar/wind/TES mix for 100% CFE
2. Calculate LCOE
3. Compare different TES durations
4. Analyze policy impacts
"""

import pyomo.environ as pyo
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
from datetime import datetime
import json

print("=" * 70)
print("PHASE 3: TES System Optimization Analysis")
print("=" * 70)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# CONFIGURATION: Test different scenarios
# ============================================================================

scenarios_to_test = [
    {
        'name': 'Baseline: 16hr TES',
        'solar_MW': 300,
        'wind_MW': 50,
        'tes_MWh': 5000,    # 16 hours × 312.5 MW thermal
        'tes_chg_MW': 200,
        'tes_duration': 16,
    },
    {
        'name': 'Long Duration: 50hr TES',
        'solar_MW': 300,
        'wind_MW': 50,
        'tes_MWh': 15625,   # 50 hours × 312.5 MW thermal
        'tes_chg_MW': 200,
        'tes_duration': 50,
    },
    {
        'name': 'More Wind: Balanced Mix',
        'solar_MW': 250,
        'wind_MW': 150,
        'tes_MWh': 5000,
        'tes_chg_MW': 200,
        'tes_duration': 16,
    },
]

# Run parameters
HOURS = 8760  # FULL YEAR - LET'S GO!!!
load_MW = 100.0

# ============================================================================
# BUILD THE MODEL (same as demo, but parameterized)
# ============================================================================

def run_tes_scenario(config, weather_data):
    """Run optimization for one scenario configuration"""

    print(f"\n{'='*70}")
    print(f"Running: {config['name']}")
    print(f"{'='*70}")
    print(f"  Solar: {config['solar_MW']} MW")
    print(f"  Wind: {config['wind_MW']} MW")
    print(f"  TES: {config['tes_MWh']/1000:.0f} GWh ({config['tes_duration']}hr duration)")

    # System parameters
    solar_MW = config['solar_MW']
    wind_MW = config['wind_MW']
    bess_MWh = 200
    bess_MW = 100
    bess_rte = 0.88

    tes_MWh = config['tes_MWh']
    tes_chg_MW = config['tes_chg_MW']
    tes_chg_eff = 0.95
    tes_self_d = 0.01 / 24

    turbine_MW = 100
    turbine_eff = 0.33
    turbine_min_frac = 0.40

    gas_max_MW = 50
    gas_heat_rate = 10
    gas_price = 5.0

    penalty_unserved = 1000
    penalty_non_cfe = 200

    # Build Pyomo model
    m = pyo.ConcreteModel(name=f"TES_{config['name'].replace(' ','_')}")
    m.T = pyo.RangeSet(0, HOURS - 1)

    # Time series parameters
    m.solar = pyo.Param(m.T, initialize={t: solar_MW * weather_data['solar'][t] for t in range(HOURS)})
    m.wind = pyo.Param(m.T, initialize={t: wind_MW * weather_data['wind'][t] for t in range(HOURS)})
    m.dc_load = pyo.Param(m.T, initialize={t: load_MW for t in range(HOURS)})

    # Decision variables
    m.bess_chg = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, bess_MW))
    m.bess_dis = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, bess_MW))
    m.bess_soc = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, bess_MWh))

    m.tes_chg = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, tes_chg_MW))
    m.tes_dis_heat = pyo.Var(m.T, within=pyo.NonNegativeReals)
    m.tes_soc = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, tes_MWh))
    m.turbine_out = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, turbine_MW))
    m.turbine_on = pyo.Var(m.T, within=pyo.Binary)

    m.gas = pyo.Var(m.T, within=pyo.NonNegativeReals, bounds=(0, gas_max_MW))
    m.curtail = pyo.Var(m.T, within=pyo.NonNegativeReals)
    m.unserved = pyo.Var(m.T, within=pyo.NonNegativeReals)

    # Constraints
    def balance(m, t):
        return (m.solar[t] + m.wind[t] + m.bess_dis[t] + m.turbine_out[t] + m.gas[t] + m.unserved[t]
                == m.dc_load[t] + m.bess_chg[t] + m.tes_chg[t] + m.curtail[t])
    m.c_balance = pyo.Constraint(m.T, rule=balance)

    def bess_soc_rule(m, t):
        if t == 0:
            return m.bess_soc[t] == 0.3 * bess_MWh + bess_rte * m.bess_chg[t] - m.bess_dis[t]
        return m.bess_soc[t] == m.bess_soc[t-1] + bess_rte * m.bess_chg[t] - m.bess_dis[t]
    m.c_bess = pyo.Constraint(m.T, rule=bess_soc_rule)

    def tes_soc_rule(m, t):
        if t == 0:
            return m.tes_soc[t] == 0.3 * tes_MWh + tes_chg_eff * m.tes_chg[t] - m.tes_dis_heat[t]
        return (m.tes_soc[t] == (1 - tes_self_d) * m.tes_soc[t-1]
                + tes_chg_eff * m.tes_chg[t] - m.tes_dis_heat[t])
    m.c_tes = pyo.Constraint(m.T, rule=tes_soc_rule)

    def turbine_eff_rule(m, t):
        return m.turbine_out[t] == turbine_eff * m.tes_dis_heat[t]
    m.c_turbine_eff = pyo.Constraint(m.T, rule=turbine_eff_rule)

    def turbine_max(m, t):
        return m.turbine_out[t] <= turbine_MW * m.turbine_on[t]
    m.c_turb_max = pyo.Constraint(m.T, rule=turbine_max)

    def turbine_min_load(m, t):
        return m.turbine_out[t] >= turbine_min_frac * turbine_MW * m.turbine_on[t]
    m.c_turb_min = pyo.Constraint(m.T, rule=turbine_min_load)

    # Objective
    def objective(m):
        return sum(
            m.gas[t] * gas_heat_rate * gas_price
            + m.gas[t] * penalty_non_cfe
            + m.unserved[t] * penalty_unserved
            for t in m.T
        )
    m.obj = pyo.Objective(rule=objective, sense=pyo.minimize)

    # Solve
    print("  Solving...")
    solver = pyo.SolverFactory('appsi_highs')
    results = solver.solve(m, tee=False)

    if results.solver.termination_condition != pyo.TerminationCondition.optimal:
        print(f"  ✗ Solver failed: {results.solver.termination_condition}")
        return None

    # Extract results
    df = pd.DataFrame({
        'hour': list(range(HOURS)),
        'solar': [pyo.value(m.solar[t]) for t in m.T],
        'wind': [pyo.value(m.wind[t]) for t in m.T],
        'bess_chg': [pyo.value(m.bess_chg[t]) for t in m.T],
        'bess_dis': [pyo.value(m.bess_dis[t]) for t in m.T],
        'bess_soc': [pyo.value(m.bess_soc[t]) for t in m.T],
        'tes_chg': [pyo.value(m.tes_chg[t]) for t in m.T],
        'tes_soc': [pyo.value(m.tes_soc[t]) for t in m.T],
        'turbine_out': [pyo.value(m.turbine_out[t]) for t in m.T],
        'gas': [pyo.value(m.gas[t]) for t in m.T],
        'curtail': [pyo.value(m.curtail[t]) for t in m.T],
        'unserved': [pyo.value(m.unserved[t]) for t in m.T],
        'load': [load_MW] * HOURS
    })

    # Calculate metrics
    total_load = df['load'].sum()
    total_gas = df['gas'].sum()
    cfe_pct = 100 * (total_load - total_gas) / total_load if total_load > 0 else 0
    total_cost = pyo.value(m.obj)

    metrics = {
        'scenario': config['name'],
        'total_load_MWh': float(total_load),
        'solar_gen_MWh': float(df['solar'].sum()),
        'wind_gen_MWh': float(df['wind'].sum()),
        'tes_output_MWh': float(df['turbine_out'].sum()),
        'battery_output_MWh': float(df['bess_dis'].sum()),
        'gas_MWh': float(total_gas),
        'curtailment_MWh': float(df['curtail'].sum()),
        'cfe_percent': float(cfe_pct),
        'total_cost_$': float(total_cost),
        'cost_per_MWh': float(total_cost / total_load) if total_load > 0 else 0,
        'gas_hours': int((df['gas'] > 0.01).sum()),
        'turbine_hours': int((df['turbine_out'] > 0.01).sum()),
    }

    print(f"  ✓ CFE: {cfe_pct:.1f}%")
    print(f"  ✓ Cost: ${total_cost:,.0f} (${metrics['cost_per_MWh']:.2f}/MWh)")
    print(f"  ✓ Gas usage: {total_gas:.0f} MWh ({metrics['gas_hours']} hours)")

    return {'config': config, 'metrics': metrics, 'dispatch': df}


# ============================================================================
# GENERATE WEATHER DATA
# ============================================================================

print("\nGenerating weather profiles...")

# Solar profile with seasonal variation and weather
solar_profile = []
np.random.seed(42)
for h in range(HOURS):
    hour_of_day = h % 24
    day_of_year = h // 24

    # Seasonal factor (stronger in summer, weaker in winter)
    seasonal_factor = 0.85 + 0.15 * math.sin(2 * math.pi * (day_of_year - 80) / 365)

    # Daily profile
    if 6 <= hour_of_day <= 18:
        base_val = math.sin(math.pi * (hour_of_day - 6) / 12)
    else:
        base_val = 0

    # Weather variability (some cloudy days)
    weather_factor = 1.0
    if np.random.random() < 0.15:  # 15% chance of cloudy day
        weather_factor = 0.3 + 0.4 * np.random.random()

    solar_profile.append(base_val * seasonal_factor * weather_factor)

# Wind profile with seasonal patterns
wind_profile = []
np.random.seed(43)
for h in range(HOURS):
    day_of_year = h // 24

    # Wind is typically higher in winter/spring
    seasonal_wind = 0.45 + 0.15 * math.cos(2 * math.pi * (day_of_year - 0) / 365)

    # Add multi-timescale variability
    fast_var = 0.15 * math.sin(2 * math.pi * h / 12)  # 12-hour cycles
    slow_var = 0.1 * math.sin(2 * math.pi * h / 168)  # weekly patterns
    noise = 0.08 * np.random.randn()

    wind_cf = seasonal_wind + fast_var + slow_var + noise
    wind_profile.append(max(0, min(1, wind_cf)))  # Clip to [0,1]

weather = {'solar': solar_profile, 'wind': wind_profile}

print(f"  Generated {HOURS} hours")
print(f"  Solar avg CF: {np.mean(solar_profile):.1%}")
print(f"  Wind avg CF: {np.mean(wind_profile):.1%}")

# ============================================================================
# RUN ALL SCENARIOS
# ============================================================================

all_results = []

for scenario in scenarios_to_test:
    result = run_tes_scenario(scenario, weather)
    if result:
        all_results.append(result)

# ============================================================================
# COMPARATIVE ANALYSIS
# ============================================================================

print(f"\n{'='*70}")
print("COMPARATIVE ANALYSIS")
print(f"{'='*70}\n")

comparison = pd.DataFrame([r['metrics'] for r in all_results])
print(comparison[['scenario', 'cfe_percent', 'cost_per_MWh', 'gas_MWh', 'tes_output_MWh']].to_string(index=False))

# ============================================================================
# SAVE RESULTS
# ============================================================================

output_dir = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project/TESProject/Phase 3 - Analysis"

# Save comparison
comparison.to_csv(f"{output_dir}/phase3_scenario_comparison.csv", index=False)
print(f"\n✓ Comparison saved: phase3_scenario_comparison.csv")

# Save detailed results
for result in all_results:
    safe_name = result['config']['name'].replace(' ', '_').replace(':', '')
    result['dispatch'].to_csv(f"{output_dir}/phase3_dispatch_{safe_name}.csv", index=False)

# Save summary JSON
summary = {
    'run_date': datetime.now().isoformat(),
    'duration_hours': HOURS,
    'scenarios': [r['metrics'] for r in all_results]
}

with open(f"{output_dir}/phase3_summary.json", 'w') as f:
    json.dump(summary, f, indent=2)

print(f"✓ Summary saved: phase3_summary.json")

print(f"\n{'='*70}")
print("PHASE 3 STARTER ANALYSIS COMPLETE!")
print(f"{'='*70}")
print("\nKey Findings:")
print("1. Check which TES duration achieves best CFE at lowest cost")
print("2. Compare balanced wind/solar vs solar-heavy configurations")
print("3. Identify when gas backup is needed")
print("\nNext Steps:")
print("1. Run with full year data (HOURS = 8760)")
print("2. Add LCOE calculations (capex + opex)")
print("3. Test policy scenarios (IRA credits)")
print("4. Compare with LDES alternative")
