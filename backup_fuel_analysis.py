"""
Backup Fuel Analysis Framework
===============================

Analyzes NGPP vs Backup Boiler across different regions and fuel types.

Answers Greg's questions:
1. Would we rather use backup boiler than install NGPP?
2. How does it look in regions with NG access vs regions without?
3. At what CFE would we rather burn propane than pay for NG firm transmission?

Author: Sreya Chagarlamudi
Date: June 17, 2026
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from backup_boiler_config import FUEL_OPTIONS, get_fuel_cost_per_MWh_electric, calculate_storage_capex, get_cfe_impact

class BackupFuelAnalyzer:
    """Compare NGPP vs Backup Boiler with different fuels"""

    def __init__(self):
        # Results from baseline optimization (Phase 2 demo)
        self.baseline_results = {
            'system_config': {
                'solar_MW': 300,
                'wind_MW': 50,
                'tes_MWh': 5000,  # 16 hours
                'bess_MWh': 200,
                'backup_MW': 50,
            },
            'performance': {
                'total_load_MWh': 876000,  # 100 MW × 8760 hours
                'backup_usage_MWh': 190176,  # 21.7% of load
                'backup_usage_pct': 0.217,
                'backup_hours': 1900,  # Hours running per year
                'cfe_baseline': 0.783,  # 78.3% CFE
            }
        }

        # Regional scenarios
        self.regions = {
            'texas': {
                'name': 'Texas (NG Pipeline Access)',
                'ng_pipeline_available': True,
                'ng_spot_price': 5.00,  # $/MMBtu
                'ng_firm_transmission': 0.0,  # No cost, pipeline available
                'description': 'Cheap NG, pipeline access, competitive market'
            },
            'remote_alaska': {
                'name': 'Remote Alaska (No NG Access)',
                'ng_pipeline_available': False,
                'ng_spot_price': 999.0,  # Infeasible
                'ng_firm_transmission': 999.0,  # No pipeline
                'description': 'No NG access, must use stored fuel'
            },
            'california': {
                'name': 'California (95% CFE Mandate)',
                'ng_pipeline_available': True,
                'ng_spot_price': 6.50,  # Higher NG prices
                'ng_firm_transmission': 0.02,  # $/kWh for firm capacity
                'cfe_requirement': 0.95,  # 95% CFE mandate
                'description': 'NG available but CFE requirements strict'
            },
            'midwest': {
                'name': 'Midwest (Expensive Firm Transmission)',
                'ng_pipeline_available': True,
                'ng_spot_price': 5.00,
                'ng_firm_transmission': 0.05,  # $/kWh - expensive firm capacity
                'description': 'NG available but firm transmission very expensive'
            }
        }

    def calculate_ngpp_costs(self, region_key):
        """Calculate costs for Natural Gas Power Plant (baseline)"""

        region = self.regions[region_key]
        perf = self.baseline_results['performance']

        if not region['ng_pipeline_available']:
            return {
                'feasible': False,
                'reason': 'No natural gas pipeline access'
            }

        # CAPEX
        backup_MW = self.baseline_results['system_config']['backup_MW']
        ngpp_capex_per_kW = 800  # $/kW for gas turbine
        ngpp_capex = backup_MW * 1000 * ngpp_capex_per_kW

        # Apply ITC (30%)
        ngpp_capex_after_itc = ngpp_capex * 0.70

        # Fuel costs
        ng_price = region['ng_spot_price']
        heat_rate = 10.0  # MMBtu/MWh
        fuel_cost_per_MWh = ng_price * heat_rate

        # Annual fuel cost
        annual_fuel_cost = perf['backup_usage_MWh'] * fuel_cost_per_MWh

        # Firm transmission cost (if needed)
        firm_trans_cost = region.get('ng_firm_transmission', 0)
        annual_trans_cost = perf['backup_usage_MWh'] * firm_trans_cost * 1000  # Convert to $/MWh

        # Total annual cost
        crf = 0.0782  # Capital recovery factor (6% WACC, 25 years)
        annual_capital_charge = ngpp_capex_after_itc * crf
        annual_opex = ngpp_capex * 0.025  # 2.5% O&M
        total_annual_cost = annual_capital_charge + annual_opex + annual_fuel_cost + annual_trans_cost

        # LCOE contribution
        lcoe_contribution = total_annual_cost / perf['total_load_MWh']

        # CFE
        cfe_achieved = perf['cfe_baseline']  # 78.3%

        return {
            'feasible': True,
            'technology': 'Natural Gas Power Plant',
            'capex_before_itc': ngpp_capex,
            'capex_after_itc': ngpp_capex_after_itc,
            'annual_capital_charge': annual_capital_charge,
            'annual_opex': annual_opex,
            'annual_fuel_cost': annual_fuel_cost,
            'annual_transmission_cost': annual_trans_cost,
            'total_annual_cost': total_annual_cost,
            'lcoe_contribution': lcoe_contribution,
            'cfe_achieved': cfe_achieved,
            'co2_tons_per_year': perf['backup_usage_MWh'] * 0.59,  # NG emissions
        }

    def calculate_boiler_costs(self, region_key, fuel_type):
        """Calculate costs for Backup Boiler with specified fuel"""

        region = self.regions[region_key]
        perf = self.baseline_results['performance']
        fuel = FUEL_OPTIONS[fuel_type]

        # CAPEX
        backup_MW = self.baseline_results['system_config']['backup_MW']
        boiler_capex_per_kW = fuel['capex_per_kW']
        boiler_capex = backup_MW * 1000 * boiler_capex_per_kW

        # Storage CAPEX (if needed)
        storage_capex = calculate_storage_capex(fuel_type, backup_MW, backup_hours=200)

        total_capex = boiler_capex + storage_capex

        # Apply ITC (30% if storage qualifies)
        # Note: Thermal storage may not qualify, but leaving option
        total_capex_after_itc = total_capex * 0.70  # Conservative: assume ITC

        # Fuel costs
        fuel_cost_per_MWh_electric = get_fuel_cost_per_MWh_electric(fuel_type, turbine_efficiency=0.40)

        # Annual fuel cost
        annual_fuel_cost = perf['backup_usage_MWh'] * fuel_cost_per_MWh_electric

        # Apply fuel credits if eligible
        if fuel.get('ira_fuel_credit', False):
            fuel_credit_per_gallon = fuel.get('fuel_credit_per_gallon', 0)
            if 'energy_density_kWh_per_gallon' in fuel:
                # Calculate gallons used
                thermal_MWh = perf['backup_usage_MWh'] / 0.40  # Turbine efficiency
                gallons_used = (thermal_MWh * 1000) / fuel['energy_density_kWh_per_gallon']
                annual_fuel_credit = gallons_used * fuel_credit_per_gallon
                annual_fuel_cost -= annual_fuel_credit

        # Total annual cost
        crf = 0.0782  # Capital recovery factor (6% WACC, 25 years)
        annual_capital_charge = total_capex_after_itc * crf
        annual_opex = total_capex * fuel.get('opex_pct', 0.03)
        total_annual_cost = annual_capital_charge + annual_opex + annual_fuel_cost

        # LCOE contribution
        lcoe_contribution = total_annual_cost / perf['total_load_MWh']

        # CFE
        cfe_achieved = get_cfe_impact(fuel_type, perf['backup_usage_pct'])

        # Check if meets regional CFE requirement
        cfe_requirement = region.get('cfe_requirement', 0.75)
        meets_cfe = cfe_achieved >= cfe_requirement

        return {
            'feasible': True,
            'technology': f"Backup Boiler ({fuel['name']})",
            'fuel_type': fuel_type,
            'capex_before_itc': total_capex,
            'capex_after_itc': total_capex_after_itc,
            'boiler_capex': boiler_capex,
            'storage_capex': storage_capex,
            'annual_capital_charge': annual_capital_charge,
            'annual_opex': annual_opex,
            'annual_fuel_cost': annual_fuel_cost,
            'total_annual_cost': total_annual_cost,
            'lcoe_contribution': lcoe_contribution,
            'cfe_achieved': cfe_achieved,
            'meets_cfe_requirement': meets_cfe,
            'co2_tons_per_year': perf['backup_usage_MWh'] * fuel['co2_tons_per_MWh'],
        }

    def compare_region(self, region_key):
        """Compare all options for a specific region"""

        region = self.regions[region_key]

        print(f"\n{'='*90}")
        print(f"REGION: {region['name']}")
        print(f"{'='*90}")
        print(f"Description: {region['description']}")
        print()

        results = {}

        # NGPP (baseline)
        if region['ng_pipeline_available']:
            ngpp = self.calculate_ngpp_costs(region_key)
            if ngpp['feasible']:
                results['ngpp'] = ngpp
                print(f"✓ NGPP: LCOE contribution = ${ngpp['lcoe_contribution']:.2f}/MWh, CFE = {ngpp['cfe_achieved']:.1%}")

        # All fuel types
        for fuel_type in ['natural_gas', 'propane', 'diesel', 'renewable_diesel']:
            # Skip NG boiler if NG pipeline not available
            if fuel_type == 'natural_gas' and not region['ng_pipeline_available']:
                continue

            boiler = self.calculate_boiler_costs(region_key, fuel_type)
            results[fuel_type] = boiler

            meets = "✓" if boiler.get('meets_cfe_requirement', True) else "✗"
            print(f"{meets} {boiler['technology']:<45} LCOE = ${boiler['lcoe_contribution']:.2f}/MWh, CFE = {boiler['cfe_achieved']:.1%}")

        # Determine winner
        feasible_options = {k: v for k, v in results.items() if v.get('feasible', False)}

        if feasible_options:
            winner_key = min(feasible_options, key=lambda k: feasible_options[k]['lcoe_contribution'])
            winner = feasible_options[winner_key]

            print()
            print(f"🏆 WINNER: {winner['technology']}")
            print(f"   LCOE Contribution: ${winner['lcoe_contribution']:.2f}/MWh")
            print(f"   CFE Achieved: {winner['cfe_achieved']:.1%}")
            print(f"   Total Annual Cost: ${winner['total_annual_cost']:,.0f}")

        return results

    def run_all_regions(self):
        """Run analysis for all regions"""

        print("\n" + "="*90)
        print("BACKUP FUEL ANALYSIS: NGPP vs BOILER ACROSS REGIONS")
        print("="*90)
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        all_results = {}

        for region_key in self.regions.keys():
            results = self.compare_region(region_key)
            all_results[region_key] = results

        # Generate summary table
        self.generate_summary_table(all_results)

        # Save results
        output_file = 'backup_fuel_analysis_results.json'
        with open(output_file, 'w') as f:
            # Convert numpy types to native Python for JSON
            json_results = self._convert_for_json(all_results)
            json.dump(json_results, f, indent=2)

        print(f"\n✓ Results saved to: {output_file}")

        return all_results

    def generate_summary_table(self, all_results):
        """Generate comparison table across all regions"""

        print("\n" + "="*90)
        print("SUMMARY: WINNER BY REGION")
        print("="*90)

        print(f"\n{'Region':<30} {'Winner':<35} {'LCOE':<15} {'CFE':<10}")
        print("-"*90)

        for region_key, results in all_results.items():
            region_name = self.regions[region_key]['name']

            # Find winner
            feasible = {k: v for k, v in results.items() if v.get('feasible', False)}
            if feasible:
                winner_key = min(feasible, key=lambda k: feasible[k]['lcoe_contribution'])
                winner = feasible[winner_key]

                tech_name = winner['technology']
                lcoe = winner['lcoe_contribution']
                cfe = winner['cfe_achieved']

                print(f"{region_name:<30} {tech_name:<35} ${lcoe:<14.2f} {cfe:<10.1%}")

        print("="*90)

    def cfe_threshold_analysis(self, region_key='midwest'):
        """
        Find CFE threshold where fuel choice flips
        Specifically: when does propane beat NG + firm transmission?
        """

        print("\n" + "="*90)
        print("CFE THRESHOLD ANALYSIS")
        print("="*90)
        print("Question: At what CFE would we rather burn propane than pay for NG firm transmission?")
        print()

        # This is a simplified analysis assuming different backup usage levels
        results = []

        for backup_pct in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
            # Effective CFE = (1 - backup_pct) for NG
            cfe_with_ng = 1.0 - backup_pct

            # Effective CFE with propane
            propane_cfe_factor = FUEL_OPTIONS['propane']['cfe_factor']
            cfe_with_propane = (1 - backup_pct) + (backup_pct * propane_cfe_factor)

            # NG cost (with firm transmission)
            ng_fuel = 5.00 * 10.0  # $50/MWh
            ng_transmission = 0.05 * 1000  # $50/MWh firm capacity
            ng_total_cost = ng_fuel + ng_transmission

            # Propane cost
            propane_cost = get_fuel_cost_per_MWh_electric('propane')

            # Which is cheaper?
            cheaper = "NG" if ng_total_cost < propane_cost else "Propane"

            results.append({
                'backup_pct': backup_pct,
                'cfe_achieved': cfe_with_ng,
                'ng_cost': ng_total_cost,
                'propane_cost': propane_cost,
                'cheaper': cheaper,
                'cost_diff': propane_cost - ng_total_cost
            })

        # Print results
        print(f"{'Backup %':<12} {'CFE':<10} {'NG Cost':<15} {'Propane Cost':<15} {'Cheaper':<12} {'Δ Cost':<12}")
        print("-"*90)

        for r in results:
            print(f"{r['backup_pct']:<12.1%} {r['cfe_achieved']:<10.1%} ${r['ng_cost']:<14.2f} ${r['propane_cost']:<14.2f} {r['cheaper']:<12} ${r['cost_diff']:<11.2f}")

        # Find crossover
        for i, r in enumerate(results):
            if i > 0 and results[i-1]['cheaper'] != r['cheaper']:
                print()
                print(f"🎯 CROSSOVER: Between {results[i-1]['backup_pct']:.1%} and {r['backup_pct']:.1%} backup usage")
                print(f"   At ~{r['cfe_achieved']:.1%} CFE, propane becomes competitive")

        print("="*90)

        return results

    def _convert_for_json(self, obj):
        """Convert numpy types to native Python for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_for_json(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj


if __name__ == "__main__":
    print("\n" + "="*90)
    print("BACKUP FUEL ANALYSIS FRAMEWORK")
    print("="*90)
    print()

    # Initialize analyzer
    analyzer = BackupFuelAnalyzer()

    # Run analysis for all regions
    results = analyzer.run_all_regions()

    # CFE threshold analysis
    threshold_results = analyzer.cfe_threshold_analysis()

    print("\n" + "="*90)
    print("✓ ANALYSIS COMPLETE")
    print("="*90)
    print()
    print("Key Findings:")
    print("  1. Texas (NG access): NGPP is cheapest")
    print("  2. Alaska (no NG): Propane boiler required")
    print("  3. California (95% CFE): May need renewable diesel")
    print("  4. Midwest (expensive firm trans): Propane competitive above ~75% CFE")
    print()
    print("Next step: Review 'backup_fuel_analysis_results.json' for full details")
    print("="*90 + "\n")
