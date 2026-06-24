"""
Phase 3: TES vs LDES Comparison

Direct comparison of Thermal Energy Storage vs Long Duration Energy Storage
for 24/7 clean firm energy datacenter applications.

Compares:
- Cost
- Performance (CFE achievement)
- Technical characteristics
- Economic viability
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class TES_vs_LDES_Comparator:
    """Compare TES and LDES technologies"""

    def __init__(self):
        # Technology specifications from Phase 1
        self.tech_specs = {
            'TES': {
                'name': 'Thermal Energy Storage (heat battery)',
                'energy_capex_per_kWh': 40,  # $/kWh thermal
                'power_capex_per_kW': 800,   # $/kW (turbine)
                'rte_thermal': 0.90,         # 90% thermal efficiency
                'rte_electric': 0.36,        # 36% electric-to-electric
                'duration_typical': 16,      # hours
                'duration_max': 100,         # hours (scalable)
                'opex_pct': 0.04,            # 4% of capex/year
                'lifetime': 30,              # years
                'response_time': 60,         # minutes (steam turbine startup)
                'efficiency_degradation': 0.002,  # 0.2% per year
            },
            'LDES': {
                'name': 'Generic Long Duration Storage',
                'energy_capex_per_kWh': 150,  # $/kWh (e.g., flow battery, compressed air)
                'power_capex_per_kW': 400,    # $/kW
                'rte_thermal': None,
                'rte_electric': 0.65,         # 65% roundtrip
                'duration_typical': 10,       # hours
                'duration_max': 24,           # hours
                'opex_pct': 0.03,             # 3% of capex/year
                'lifetime': 20,               # years
                'response_time': 5,           # minutes
                'efficiency_degradation': 0.005,  # 0.5% per year
            },
            'Lithium_BESS': {
                'name': 'Lithium-Ion Battery',
                'energy_capex_per_kWh': 200,  # $/kWh
                'power_capex_per_kW': 100,    # $/kW
                'rte_thermal': None,
                'rte_electric': 0.88,         # 88% roundtrip
                'duration_typical': 4,        # hours
                'duration_max': 4,            # hours (not economical beyond this)
                'opex_pct': 0.02,             # 2% of capex/year
                'lifetime': 15,               # years (with 1 replacement)
                'response_time': 0.1,         # minutes (near-instantaneous)
                'efficiency_degradation': 0.02,  # 2% per year
            }
        }

    def calculate_system_cost(self, tech_name, energy_MWh, power_MW):
        """Calculate total system cost for given technology"""

        spec = self.tech_specs[tech_name]

        energy_cost = energy_MWh * 1000 * spec['energy_capex_per_kWh']
        power_cost = power_MW * 1000 * spec['power_capex_per_kW']
        total_capex = energy_cost + power_cost

        # Apply ITC (30% for storage per IRA Section 48E)
        itc_savings = total_capex * 0.30
        capex_after_itc = total_capex - itc_savings

        # Annual operating cost
        annual_opex = total_capex * spec['opex_pct']

        return {
            'energy_cost': energy_cost,
            'power_cost': power_cost,
            'total_capex_before_itc': total_capex,
            'itc_savings': itc_savings,
            'total_capex_after_itc': capex_after_itc,
            'annual_opex': annual_opex,
            'lifetime_years': spec['lifetime'],
        }

    def compare_for_datacenter(self, load_MW=100, target_duration_hours=16):
        """Compare technologies for datacenter application"""

        print("="*70)
        print(f"TES vs LDES Comparison for {load_MW} MW Datacenter")
        print(f"Target Storage Duration: {target_duration_hours} hours")
        print("="*70)
        print()

        # Size each system for the same energy capacity
        energy_MWh = load_MW * target_duration_hours
        power_MW = load_MW

        results = {}

        for tech in ['TES', 'LDES', 'Lithium_BESS']:
            spec = self.tech_specs[tech]

            # Check if technology can support this duration
            if target_duration_hours > spec['duration_max']:
                print(f"⚠️  {tech}: Cannot support {target_duration_hours}hr duration (max: {spec['duration_max']}hr)")
                print()
                continue

            cost = self.calculate_system_cost(tech, energy_MWh, power_MW)

            # Calculate LCOE contribution (storage only)
            crf = 0.06 * (1.06)**spec['lifetime'] / ((1.06)**spec['lifetime'] - 1)
            annual_capital = cost['total_capex_after_itc'] * crf
            annual_total = annual_capital + cost['annual_opex']

            # Annual throughput (assume 300 full cycles per year)
            annual_throughput = energy_MWh * 300 * spec['rte_electric']

            lcoe_storage = annual_total / annual_throughput if annual_throughput > 0 else 999

            results[tech] = {
                'spec': spec,
                'cost': cost,
                'annual_capital': annual_capital,
                'annual_total': annual_total,
                'lcoe_storage_$/MWh': lcoe_storage,
            }

            print(f"{spec['name']}:")
            print(f"  Energy Capacity: {energy_MWh:,.0f} MWh")
            print(f"  Power Rating: {power_MW:.0f} MW")
            print(f"  Roundtrip Efficiency: {spec['rte_electric']*100:.0f}%")
            print(f"  CAPEX (before ITC): ${cost['total_capex_before_itc']/1e6:.1f}M")
            print(f"  CAPEX (after 30% ITC): ${cost['total_capex_after_itc']/1e6:.1f}M")
            print(f"  Annual OpEx: ${cost['annual_opex']/1e6:.2f}M")
            print(f"  Lifetime: {spec['lifetime']} years")
            print(f"  Storage LCOE: ${lcoe_storage:.2f}/MWh")
            print()

        # Summary comparison table
        if results:
            print("="*70)
            print("SUMMARY COMPARISON")
            print("="*70)

            comparison = pd.DataFrame({
                tech: {
                    'CAPEX after ITC ($M)': res['cost']['total_capex_after_itc']/1e6,
                    'Annual Cost ($M)': res['annual_total']/1e6,
                    'Efficiency (%)': res['spec']['rte_electric']*100,
                    'LCOE ($/MWh)': res['lcoe_storage_$/MWh'],
                    'Lifetime (years)': res['spec']['lifetime'],
                    'Max Duration (hrs)': res['spec']['duration_max'],
                }
                for tech, res in results.items()
            })

            print(comparison.T.to_string())
            print()

            # Winner determination
            best_tech = min(results.keys(), key=lambda t: results[t]['lcoe_storage_$/MWh'])
            print(f"🏆 WINNER for {target_duration_hours}hr duration: {self.tech_specs[best_tech]['name']}")
            print(f"   Lowest storage LCOE: ${results[best_tech]['lcoe_storage_$/MWh']:.2f}/MWh")
            print()

        return results

    def plot_duration_crossover(self, output_path):
        """Plot cost vs duration to find crossover points"""

        durations = np.array([2, 4, 8, 12, 16, 24, 48, 72, 96])
        load_MW = 100

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('Storage Technology Comparison: Duration Analysis', fontsize=16, fontweight='bold')

        # Plot 1: Total CAPEX vs Duration
        for tech in ['TES', 'LDES', 'Lithium_BESS']:
            spec = self.tech_specs[tech]
            costs = []

            for dur in durations:
                if dur <= spec['duration_max']:
                    energy_MWh = load_MW * dur
                    cost_data = self.calculate_system_cost(tech, energy_MWh, load_MW)
                    costs.append(cost_data['total_capex_after_itc'] / 1e6)
                else:
                    costs.append(np.nan)

            ax1.plot(durations, costs, marker='o', linewidth=2, markersize=8, label=spec['name'])

        ax1.set_xlabel('Storage Duration (hours)', fontweight='bold', fontsize=12)
        ax1.set_ylabel('Total CAPEX after ITC ($M)', fontweight='bold', fontsize=12)
        ax1.set_title('Capital Cost vs Duration', fontweight='bold', fontsize=14)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, 100)

        # Plot 2: LCOE vs Duration
        for tech in ['TES', 'LDES', 'Lithium_BESS']:
            spec = self.tech_specs[tech]
            lcoes = []

            for dur in durations:
                if dur <= spec['duration_max']:
                    energy_MWh = load_MW * dur
                    cost_data = self.calculate_system_cost(tech, energy_MWh, load_MW)

                    crf = 0.06 * (1.06)**spec['lifetime'] / ((1.06)**spec['lifetime'] - 1)
                    annual_capital = cost_data['total_capex_after_itc'] * crf
                    annual_total = annual_capital + cost_data['annual_opex']
                    annual_throughput = energy_MWh * 300 * spec['rte_electric']

                    lcoe = annual_total / annual_throughput if annual_throughput > 0 else np.nan
                    lcoes.append(lcoe)
                else:
                    lcoes.append(np.nan)

            ax2.plot(durations, lcoes, marker='o', linewidth=2, markersize=8, label=spec['name'])

        ax2.set_xlabel('Storage Duration (hours)', fontweight='bold', fontsize=12)
        ax2.set_ylabel('Storage LCOE ($/MWh)', fontweight='bold', fontsize=12)
        ax2.set_title('Levelized Cost vs Duration', fontweight='bold', fontsize=14)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0, 100)

        # Add crossover annotation
        ax2.axvline(x=12, color='red', linestyle='--', alpha=0.5)
        ax2.text(12, ax2.get_ylim()[1]*0.9, 'TES becomes\neconomical', ha='center',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Success: Duration crossover plot saved: {output_path}")


# Run comparison
if __name__ == "__main__":
    comparator = TES_vs_LDES_Comparator()

    # Compare for 16-hour duration (heat battery baseline)
    print("\n" + "="*70)
    print("SCENARIO 1: 16-Hour Duration (heat battery Baseline)")
    print("="*70)
    comparator.compare_for_datacenter(load_MW=100, target_duration_hours=16)

    print("\n" + "="*70)
    print("SCENARIO 2: 4-Hour Duration (Short Duration)")
    print("="*70)
    comparator.compare_for_datacenter(load_MW=100, target_duration_hours=4)

    print("\n" + "="*70)
    print("SCENARIO 3: 48-Hour Duration (Multi-Day Storage)")
    print("="*70)
    comparator.compare_for_datacenter(load_MW=100, target_duration_hours=48)

    # Create crossover plot
    output_path = "/Users/sreyachagarlamudi/Library/Mobile Documents/com~apple~CloudDocs/Intern Project Phase 2/tes_vs_ldes_duration_analysis.png"
    comparator.plot_duration_crossover(output_path)

    print("\nSuccess: TES vs LDES comparison complete!")
