"""
Phase 3: Advanced Visualization Suite

Creates publication-ready charts for Phase 3 analysis:
- CFE achievement comparison
- Cost breakdown by technology
- Dispatch patterns
- Sensitivity analyses
- Policy impact visualization
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json

class Phase3Visualizer:
    """Create all Phase 3 visualizations"""

    def __init__(self, results_dir):
        self.results_dir = results_dir

    def plot_scenario_comparison(self, comparison_df, output_path):
        """Compare different TES configurations"""

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Phase 3: TES Configuration Comparison', fontsize=18, fontweight='bold')

        scenarios = comparison_df['scenario'].values
        x = np.arange(len(scenarios))
        width = 0.6

        # Plot 1: CFE Achievement
        ax1 = axes[0, 0]
        bars = ax1.bar(x, comparison_df['cfe_percent'], width, color=['#2ecc71', '#3498db', '#e74c3c'])
        ax1.axhline(y=100, color='black', linestyle='--', linewidth=2, label='100% CFE Target')
        ax1.set_ylabel('Clean Firm Energy (%)', fontweight='bold', fontsize=12)
        ax1.set_title('CFE Achievement', fontweight='bold', fontsize=14)
        ax1.set_xticks(x)
        ax1.set_xticklabels(scenarios, rotation=15, ha='right')
        ax1.set_ylim(0, 105)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Add value labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

        # Plot 2: Cost Comparison
        ax2 = axes[0, 1]
        bars = ax2.bar(x, comparison_df['cost_per_MWh'], width, color=['#9b59b6', '#e67e22', '#1abc9c'])
        ax2.set_ylabel('Cost ($/MWh)', fontweight='bold', fontsize=12)
        ax2.set_title('Levelized Cost Comparison', fontweight='bold', fontsize=14)
        ax2.set_xticks(x)
        ax2.set_xticklabels(scenarios, rotation=15, ha='right')
        ax2.grid(True, alpha=0.3)

        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.2f}', ha='center', va='bottom', fontweight='bold')

        # Plot 3: Energy Mix
        ax3 = axes[1, 0]
        energy_sources = ['solar_gen_MWh', 'wind_gen_MWh', 'tes_output_MWh', 'battery_output_MWh', 'gas_MWh']
        source_labels = ['Solar', 'Wind', 'TES', 'Battery', 'Gas']
        colors_mix = ['#f39c12', '#3498db', '#e74c3c', '#2ecc71', '#95a5a6']

        bottom = np.zeros(len(scenarios))
        for i, source in enumerate(energy_sources):
            if source in comparison_df.columns:
                values = comparison_df[source].values
                ax3.bar(x, values, width, label=source_labels[i], bottom=bottom, color=colors_mix[i])
                bottom += values

        ax3.set_ylabel('Energy (MWh)', fontweight='bold', fontsize=12)
        ax3.set_title('Energy Generation Mix', fontweight='bold', fontsize=14)
        ax3.set_xticks(x)
        ax3.set_xticklabels(scenarios, rotation=15, ha='right')
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3, axis='y')

        # Plot 4: Gas Usage
        ax4 = axes[1, 1]
        bars = ax4.bar(x, comparison_df['gas_hours'], width, color=['#c0392b', '#d35400', '#8e44ad'])
        ax4.set_ylabel('Hours', fontweight='bold', fontsize=12)
        ax4.set_title('Gas Backup Usage', fontweight='bold', fontsize=14)
        ax4.set_xticks(x)
        ax4.set_xticklabels(scenarios, rotation=15, ha='right')
        ax4.grid(True, alpha=0.3)

        for i, bar in enumerate(bars):
            height = bar.get_height()
            pct = 100 * height / 8760
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}h\n({pct:.1f}%)', ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Scenario comparison saved: {output_path}")

    def plot_dispatch_heatmap(self, dispatch_df, output_path, num_days=14):
        """Create heatmap of dispatch patterns"""

        # Use first num_days of data
        hours_to_plot = min(num_days * 24, len(dispatch_df))
        df_subset = dispatch_df.iloc[:hours_to_plot]

        fig, axes = plt.subplots(4, 1, figsize=(18, 12))
        fig.suptitle(f'Dispatch Patterns - First {num_days} Days', fontsize=16, fontweight='bold')

        hours = df_subset['hour'].values

        # Plot 1: Generation sources
        ax1 = axes[0]
        ax1.fill_between(hours, 0, df_subset['solar'], label='Solar', alpha=0.7, color='#f39c12')
        ax1.fill_between(hours, df_subset['solar'], df_subset['solar'] + df_subset['wind'],
                        label='Wind', alpha=0.7, color='#3498db')
        ax1.plot(hours, df_subset['load'], 'k--', linewidth=2, label='Load')
        ax1.set_ylabel('Power (MW)', fontweight='bold')
        ax1.set_title('Renewable Generation vs Load', fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, hours_to_plot)

        # Plot 2: Storage dispatch
        ax2 = axes[1]
        ax2.bar(hours, df_subset['tes_chg'], width=1, label='TES Charging', color='red', alpha=0.6)
        ax2.bar(hours, -df_subset['turbine_out'], width=1, label='TES Discharging', color='orange', alpha=0.6)
        ax2.bar(hours, df_subset['bess_chg'], width=1, label='Battery Charging', color='blue', alpha=0.4)
        ax2.bar(hours, -df_subset['bess_dis'], width=1, label='Battery Discharging', color='lightblue', alpha=0.4)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.set_ylabel('Power (MW)', fontweight='bold')
        ax2.set_title('Storage Charging & Discharging', fontweight='bold')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0, hours_to_plot)

        # Plot 3: State of charge
        ax3 = axes[2]
        ax3.plot(hours, df_subset['tes_soc']/1000, label='TES SOC', color='red', linewidth=2)
        ax3.plot(hours, df_subset['bess_soc'], label='Battery SOC', color='blue', linewidth=2)
        ax3.set_ylabel('Energy (GWh / MWh)', fontweight='bold')
        ax3.set_title('Storage State of Charge', fontweight='bold')
        ax3.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(0, hours_to_plot)

        # Plot 4: Gas backup
        ax4 = axes[3]
        ax4.fill_between(hours, 0, df_subset['gas'], where=(df_subset['gas']>0),
                        label='Gas Backup', color='gray', alpha=0.7)
        ax4.set_ylabel('Power (MW)', fontweight='bold')
        ax4.set_xlabel('Hour', fontweight='bold')
        ax4.set_title('Gas Backup Usage', fontweight='bold')
        ax4.legend(loc='upper right')
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(0, hours_to_plot)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Dispatch heatmap saved: {output_path}")

    def plot_ira_impact(self, with_ira, without_ira, output_path):
        """Visualize IRA tax credit impact"""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('IRA Tax Credit Impact Analysis', fontsize=16, fontweight='bold')

        # Plot 1: LCOE comparison
        scenarios = ['With IRA\nCredits', 'Without IRA\nCredits']
        lcoe_values = [with_ira['lcoe_$/MWh'], without_ira['lcoe_$/MWh']]
        colors = ['#27ae60', '#e74c3c']

        bars = ax1.bar(scenarios, lcoe_values, color=colors, width=0.6)
        ax1.set_ylabel('LCOE ($/MWh)', fontweight='bold', fontsize=12)
        ax1.set_title('Levelized Cost of Energy', fontweight='bold', fontsize=14)
        ax1.grid(True, alpha=0.3, axis='y')

        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.2f}/MWh', ha='center', va='bottom',
                    fontweight='bold', fontsize=12)

        # Add savings annotation
        savings = without_ira['lcoe_$/MWh'] - with_ira['lcoe_$/MWh']
        ax1.annotate('', xy=(1, lcoe_values[1]), xytext=(0, lcoe_values[0]),
                    arrowprops=dict(arrowstyle='<->', color='black', lw=2))
        ax1.text(0.5, (lcoe_values[0] + lcoe_values[1])/2,
                f'${savings:.2f}/MWh\nsavings', ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7),
                fontweight='bold')

        # Plot 2: Cost breakdown
        components = ['Capital\nCharge', 'Operating\nCosts', 'Fuel\nCosts', 'PTC\nBenefit']
        with_ira_costs = [
            with_ira['annual_capital_charge']/1e6,
            with_ira['annual_opex']/1e6,
            with_ira['annual_fuel_cost']/1e6,
            -with_ira['annual_ptc_benefit']/1e6
        ]
        without_ira_costs = [
            without_ira['annual_capital_charge']/1e6,
            without_ira['annual_opex']/1e6,
            without_ira['annual_fuel_cost']/1e6,
            0  # No PTC without IRA
        ]

        x = np.arange(len(components))
        width = 0.35

        bars1 = ax2.bar(x - width/2, with_ira_costs, width, label='With IRA', color='#27ae60')
        bars2 = ax2.bar(x + width/2, without_ira_costs, width, label='Without IRA', color='#e74c3c')

        ax2.set_ylabel('Annual Cost ($M)', fontweight='bold', fontsize=12)
        ax2.set_title('Annual Cost Breakdown', fontweight='bold', fontsize=14)
        ax2.set_xticks(x)
        ax2.set_xticklabels(components)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.axhline(y=0, color='black', linewidth=0.5)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ IRA impact visualization saved: {output_path}")


# Example usage
if __name__ == "__main__":
    print("Phase 3 Visualizer ready!")
    print("Load your results and call the plotting functions.")
