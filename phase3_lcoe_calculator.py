"""
Phase 3: LCOE (Levelized Cost of Energy) Calculator

Calculates the true cost of energy including:
- Capital costs (CAPEX)
- Operating costs (OPEX)
- Financing (discount rate)
- IRA tax credits (Section 48E ITC, Section 45 PTC)

Based on your Phase 1 cost assumptions.
"""

import pandas as pd
import numpy as np

class LCOECalculator:
    """Calculate LCOE for TES + Renewables system"""

    def __init__(self, config):
        """
        config should include:
        - solar_MW, wind_MW, tes_MWh, bess_MWh
        - project lifetime, discount rate
        - tax credit parameters
        """
        self.config = config

        # Cost assumptions from Phase 1
        self.costs = {
            # Solar ($/kW-DC)
            'solar_capex': 1000,  # $1000/kW
            'solar_opex_pct': 0.015,  # 1.5% of capex per year

            # Wind ($/kW)
            'wind_capex': 1500,  # $1500/kW
            'wind_opex_pct': 0.025,  # 2.5% of capex per year

            # TES ($/kWh thermal)
            'tes_energy_capex': 40,  # $40/kWh thermal
            'tes_power_capex': 800,  # $800/kW discharge (turbine)
            'tes_opex_pct': 0.04,  # 4% of capex per year

            # Battery ($/kWh)
            'bess_energy_capex': 200,  # $200/kWh
            'bess_power_capex': 100,  # $100/kW
            'bess_opex_pct': 0.02,  # 2% per year

            # Gas backup ($/kW)
            'gas_capex': 800,  # $800/kW
            'gas_opex_pct': 0.03,
            'gas_fuel_cost': 5.0,  # $/MMBtu
        }

        # Financial parameters
        self.finance = {
            'project_lifetime': 25,  # years
            'discount_rate': 0.06,  # 6% WACC
            'inflation': 0.025,  # 2.5%

            # IRA Tax Credits
            'itc_solar': 0.30,  # 30% ITC for solar
            'itc_wind': 0.30,   # 30% ITC for wind
            'itc_tes': 0.30,    # 30% ITC for energy storage (Section 48E)
            'ptc_wind': 27.5,   # $/MWh production tax credit
        }

    def calculate_capex(self):
        """Calculate total capital expenditure"""
        c = self.config
        costs = self.costs

        capex = {
            'solar': c['solar_MW'] * 1000 * costs['solar_capex'],
            'wind': c['wind_MW'] * 1000 * costs['wind_capex'],
            'tes_energy': c['tes_MWh'] * 1000 * costs['tes_energy_capex'],
            'tes_power': c['tes_power_MW'] * 1000 * costs['tes_power_capex'],
            'bess_energy': c.get('bess_MWh', 0) * 1000 * costs['bess_energy_capex'],
            'bess_power': c.get('bess_MW', 0) * 1000 * costs['bess_power_capex'],
            'gas': c.get('gas_MW', 0) * 1000 * costs['gas_capex'],
        }

        # Apply ITC credits
        capex_after_itc = {
            'solar': capex['solar'] * (1 - self.finance['itc_solar']),
            'wind': capex['wind'] * (1 - self.finance['itc_wind']),
            'tes_energy': capex['tes_energy'] * (1 - self.finance['itc_tes']),
            'tes_power': capex['tes_power'] * (1 - self.finance['itc_tes']),
            'bess_energy': capex['bess_energy'] * (1 - self.finance['itc_tes']),
            'bess_power': capex['bess_power'] * (1 - self.finance['itc_tes']),
            'gas': capex['gas'],  # No ITC for gas
        }

        return {
            'capex_before_itc': capex,
            'capex_after_itc': capex_after_itc,
            'total_before_itc': sum(capex.values()),
            'total_after_itc': sum(capex_after_itc.values()),
            'itc_savings': sum(capex.values()) - sum(capex_after_itc.values()),
        }

    def calculate_annual_opex(self):
        """Calculate annual operating expenses"""
        c = self.config
        costs = self.costs
        capex = self.calculate_capex()['capex_before_itc']

        opex = {
            'solar': capex['solar'] * costs['solar_opex_pct'],
            'wind': capex['wind'] * costs['wind_opex_pct'],
            'tes': (capex['tes_energy'] + capex['tes_power']) * costs['tes_opex_pct'],
            'bess': (capex['bess_energy'] + capex['bess_power']) * costs['bess_opex_pct'],
            'gas_fixed': capex['gas'] * costs['gas_opex_pct'],
        }

        return {
            'annual_opex': opex,
            'total_annual': sum(opex.values()),
        }

    def calculate_lcoe(self, annual_generation_MWh, annual_gas_usage_MMBtu=0):
        """
        Calculate LCOE ($/MWh)

        annual_generation_MWh: Total MWh delivered per year
        annual_gas_usage_MMBtu: Total gas fuel usage (if any)
        """

        capex_data = self.calculate_capex()
        opex_data = self.calculate_annual_opex()

        # Capital Recovery Factor
        r = self.finance['discount_rate']
        n = self.finance['project_lifetime']
        crf = (r * (1 + r)**n) / ((1 + r)**n - 1)

        # Annual capital charge
        annual_capital_charge = capex_data['total_after_itc'] * crf

        # Annual operating costs
        annual_opex = opex_data['total_annual']

        # Annual fuel costs
        annual_fuel_cost = annual_gas_usage_MMBtu * self.costs['gas_fuel_cost']

        # PTC benefits (wind only)
        annual_ptc_benefit = self.config.get('annual_wind_gen_MWh', 0) * self.finance['ptc_wind']

        # Total annual cost
        total_annual_cost = (annual_capital_charge + annual_opex + annual_fuel_cost - annual_ptc_benefit)

        # LCOE
        lcoe = total_annual_cost / annual_generation_MWh if annual_generation_MWh > 0 else 0

        return {
            'lcoe_$/MWh': lcoe,
            'annual_capital_charge': annual_capital_charge,
            'annual_opex': annual_opex,
            'annual_fuel_cost': annual_fuel_cost,
            'annual_ptc_benefit': annual_ptc_benefit,
            'total_annual_cost': total_annual_cost,
            'annual_generation_MWh': annual_generation_MWh,
            'capex_breakdown': capex_data,
            'opex_breakdown': opex_data,
        }

    def compare_with_without_ira(self, annual_generation_MWh, annual_gas_usage_MMBtu=0):
        """Compare LCOE with and without IRA tax credits"""

        # With IRA
        lcoe_with_ira = self.calculate_lcoe(annual_generation_MWh, annual_gas_usage_MMBtu)

        # Without IRA (temporarily disable credits)
        original_itc = self.finance.copy()
        self.finance['itc_solar'] = 0
        self.finance['itc_wind'] = 0
        self.finance['itc_tes'] = 0
        self.finance['ptc_wind'] = 0

        lcoe_without_ira = self.calculate_lcoe(annual_generation_MWh, annual_gas_usage_MMBtu)

        # Restore original
        self.finance = original_itc

        return {
            'with_ira': lcoe_with_ira,
            'without_ira': lcoe_without_ira,
            'ira_savings_per_MWh': lcoe_without_ira['lcoe_$/MWh'] - lcoe_with_ira['lcoe_$/MWh'],
            'ira_savings_pct': 100 * (lcoe_without_ira['lcoe_$/MWh'] - lcoe_with_ira['lcoe_$/MWh']) / lcoe_without_ira['lcoe_$/MWh'],
        }


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("PHASE 3: LCOE Analysis for TES System")
    print("="*70)
    print()

    # Example system configuration
    system_config = {
        'solar_MW': 300,
        'wind_MW': 50,
        'tes_MWh': 5000,  # 5 GWh thermal
        'tes_power_MW': 312.5,  # Discharge power (thermal)
        'bess_MWh': 200,
        'bess_MW': 100,
        'gas_MW': 50,
        'annual_wind_gen_MWh': 3328 * (8760/168),  # Scale from our 1-week result
    }

    # Example dispatch results (from optimization)
    annual_generation = 100 * 8760  # 100 MW datacenter × 8760 hours
    annual_gas_usage = 3648 * (8760/168) * 10  # Scale gas usage, × heat rate

    calc = LCOECalculator(system_config)

    # Calculate LCOE
    result = calc.calculate_lcoe(annual_generation, annual_gas_usage)

    print("CAPEX Breakdown (before ITC):")
    for component, cost in result['capex_breakdown']['capex_before_itc'].items():
        print(f"  {component:15s}: ${cost:>15,.0f}")
    print(f"  {'TOTAL':15s}: ${result['capex_breakdown']['total_before_itc']:>15,.0f}")
    print()

    print("CAPEX Breakdown (after ITC):")
    for component, cost in result['capex_breakdown']['capex_after_itc'].items():
        print(f"  {component:15s}: ${cost:>15,.0f}")
    print(f"  {'TOTAL':15s}: ${result['capex_breakdown']['total_after_itc']:>15,.0f}")
    print(f"  ITC SAVINGS: ${result['capex_breakdown']['itc_savings']:>15,.0f}")
    print()

    print("Annual Costs:")
    print(f"  Capital charge:  ${result['annual_capital_charge']:>12,.0f}")
    print(f"  Operating costs: ${result['annual_opex']:>12,.0f}")
    print(f"  Fuel costs:      ${result['annual_fuel_cost']:>12,.0f}")
    print(f"  PTC benefit:    -${result['annual_ptc_benefit']:>12,.0f}")
    print(f"  {'TOTAL:':17s} ${result['total_annual_cost']:>12,.0f}")
    print()

    print("="*70)
    print(f"LCOE: ${result['lcoe_$/MWh']:.2f}/MWh")
    print("="*70)
    print()

    # Compare with/without IRA
    comparison = calc.compare_with_without_ira(annual_generation, annual_gas_usage)

    print("IRA Tax Credit Impact:")
    print(f"  LCOE with IRA:    ${comparison['with_ira']['lcoe_$/MWh']:.2f}/MWh")
    print(f"  LCOE without IRA: ${comparison['without_ira']['lcoe_$/MWh']:.2f}/MWh")
    print(f"  Savings:          ${comparison['ira_savings_per_MWh']:.2f}/MWh ({comparison['ira_savings_pct']:.1f}%)")
    print()

    print("Success: LCOE calculator ready for Phase 3 analysis!")
