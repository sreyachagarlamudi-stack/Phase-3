"""
Backup Boiler Fuel Configuration
=================================

Defines fuel options for the backup boiler system.
This enables analysis of NGPP vs fuel-flexible backup boiler.

Based on Greg's request:
"It's a binary option when you configure the TES system - do you want to add
a backup boiler, and if so what fuel are you using."

Author: Sreya Chagarlamudi
Date: June 17, 2026
"""

FUEL_OPTIONS = {
    'natural_gas': {
        'name': 'Natural Gas (Pipeline)',
        'description': 'Pipeline natural gas, lowest cost when available',

        # Cost parameters
        'cost_per_MMBtu': 5.00,  # $/MMBtu delivered
        'cost_per_kWh_thermal': 0.0147,  # $5/MMBtu ÷ 3.412 MMBtu/MWh ÷ 1000
        'heat_rate_MMBtu_per_MWh': 10.0,  # Boiler efficiency ~85%

        # Environmental
        'cfe_factor': 0.0,  # 0% clean
        'co2_lbs_per_MMBtu': 117,  # lbs CO2 per MMBtu
        'co2_tons_per_MWh': 0.59,  # tons CO2 per MWh output

        # CAPEX (cheaper than turbine - just a boiler)
        'capex_per_kW': 300,  # $/kW capacity
        'opex_pct': 0.025,  # 2.5% of CAPEX per year

        # Infrastructure requirements
        'availability': 'pipeline_required',
        'storage_required': False,
        'firm_transmission_cost': 0.02,  # $/kWh for firm capacity (if needed)

        # IRA eligibility
        'ira_itc_eligible': False,  # No ITC for NG equipment
        'ira_fuel_credit': False,
    },

    'propane': {
        'name': 'Propane (LPG)',
        'description': 'Liquified petroleum gas, stored on-site',

        # Cost parameters
        'cost_per_gallon': 2.50,  # $/gallon delivered
        'cost_per_kWh_thermal': 0.0683,  # $2.50/gal ÷ 36.6 kWh/gal
        'heat_rate_MMBtu_per_MWh': 10.5,  # Boiler efficiency ~81%
        'energy_density_kWh_per_gallon': 36.6,

        # Environmental
        'cfe_factor': 0.0,  # 0% clean
        'co2_lbs_per_gallon': 12.7,  # lbs CO2 per gallon
        'co2_tons_per_MWh': 0.60,  # tons CO2 per MWh output

        # CAPEX (includes storage tank)
        'capex_per_kW': 350,  # $/kW capacity (boiler + storage)
        'storage_capex_per_gallon': 2.5,  # Tank cost
        'opex_pct': 0.03,  # 3% of CAPEX per year

        # Infrastructure requirements
        'availability': 'stored_onsite',
        'storage_required': True,
        'storage_days': 30,  # 30 days fuel storage typical
        'firm_transmission_cost': 0.0,  # No pipeline needed

        # IRA eligibility
        'ira_itc_eligible': False,
        'ira_fuel_credit': False,
    },

    'diesel': {
        'name': 'Diesel Fuel (#2)',
        'description': 'Petroleum diesel, stored on-site',

        # Cost parameters
        'cost_per_gallon': 3.50,  # $/gallon delivered
        'cost_per_kWh_thermal': 0.0873,  # $3.50/gal ÷ 40.1 kWh/gal
        'heat_rate_MMBtu_per_MWh': 10.2,  # Boiler efficiency ~83%
        'energy_density_kWh_per_gallon': 40.1,

        # Environmental
        'cfe_factor': 0.0,  # 0% clean
        'co2_lbs_per_gallon': 22.4,  # lbs CO2 per gallon
        'co2_tons_per_MWh': 0.63,  # tons CO2 per MWh output

        # CAPEX (includes storage tank)
        'capex_per_kW': 350,  # $/kW capacity
        'storage_capex_per_gallon': 2.0,
        'opex_pct': 0.03,

        # Infrastructure requirements
        'availability': 'stored_onsite',
        'storage_required': True,
        'storage_days': 30,
        'firm_transmission_cost': 0.0,

        # IRA eligibility
        'ira_itc_eligible': False,
        'ira_fuel_credit': False,
    },

    'renewable_diesel': {
        'name': 'Renewable Diesel (RD99)',
        'description': 'Drop-in replacement for diesel, lifecycle carbon-neutral',

        # Cost parameters
        'cost_per_gallon': 4.50,  # $/gallon (premium over diesel)
        'cost_per_kWh_thermal': 0.1122,  # $4.50/gal ÷ 40.1 kWh/gal
        'heat_rate_MMBtu_per_MWh': 10.2,  # Same as diesel
        'energy_density_kWh_per_gallon': 40.1,

        # Environmental (KEY DIFFERENCE)
        'cfe_factor': 0.95,  # 95% CFE (lifecycle carbon neutral)
        'co2_lbs_per_gallon': 2.0,  # Net lifecycle CO2
        'co2_tons_per_MWh': 0.06,  # 90% reduction vs diesel

        # CAPEX (same as diesel - drop-in replacement)
        'capex_per_kW': 350,
        'storage_capex_per_gallon': 2.0,
        'opex_pct': 0.03,

        # Infrastructure requirements
        'availability': 'stored_onsite',
        'storage_required': True,
        'storage_days': 30,
        'firm_transmission_cost': 0.0,

        # IRA eligibility (BIG ADVANTAGE)
        'ira_itc_eligible': False,
        'ira_fuel_credit': True,  # Renewable fuel tax credit
        'fuel_credit_per_gallon': 1.00,  # $1/gallon credit (Section 40B)
    },

    'biodiesel': {
        'name': 'Biodiesel (B100)',
        'description': '100% biodiesel, renewable but lower energy density',

        # Cost parameters
        'cost_per_gallon': 5.00,  # $/gallon
        'cost_per_kWh_thermal': 0.1310,  # $5.00/gal ÷ 38.2 kWh/gal
        'heat_rate_MMBtu_per_MWh': 10.8,  # Slightly less efficient
        'energy_density_kWh_per_gallon': 38.2,  # 5% lower than diesel

        # Environmental
        'cfe_factor': 0.90,  # 90% CFE (some lifecycle emissions)
        'co2_lbs_per_gallon': 3.5,  # Net lifecycle CO2
        'co2_tons_per_MWh': 0.11,  # 82% reduction vs diesel

        # CAPEX
        'capex_per_kW': 375,  # Slightly higher (fuel system mods)
        'storage_capex_per_gallon': 2.5,
        'opex_pct': 0.035,  # Higher maintenance

        # Infrastructure requirements
        'availability': 'stored_onsite',
        'storage_required': True,
        'storage_days': 30,
        'firm_transmission_cost': 0.0,

        # IRA eligibility
        'ira_itc_eligible': False,
        'ira_fuel_credit': True,
        'fuel_credit_per_gallon': 1.00,  # Biodiesel blenders credit
    },
}


def get_fuel_cost_per_MWh_thermal(fuel_type, usage_hours_per_year=None):
    """
    Calculate cost per MWh of thermal energy output

    Args:
        fuel_type: Key from FUEL_OPTIONS
        usage_hours_per_year: Optional, for calculating fuel credits

    Returns:
        Cost in $/MWh thermal
    """
    fuel = FUEL_OPTIONS[fuel_type]

    # Base cost per kWh thermal
    cost_per_kWh = fuel['cost_per_kWh_thermal']

    # Convert to $/MWh
    cost_per_MWh = cost_per_kWh * 1000

    # Apply fuel credits if applicable
    if fuel.get('ira_fuel_credit', False) and usage_hours_per_year:
        # Credit per gallon
        credit_per_gallon = fuel.get('fuel_credit_per_gallon', 0)

        # Gallons per MWh thermal
        if 'energy_density_kWh_per_gallon' in fuel:
            gallons_per_MWh = 1000 / fuel['energy_density_kWh_per_gallon']
            credit_per_MWh = credit_per_gallon * gallons_per_MWh
            cost_per_MWh -= credit_per_MWh

    return cost_per_MWh


def get_fuel_cost_per_MWh_electric(fuel_type, turbine_efficiency=0.40):
    """
    Calculate cost per MWh of electrical energy output
    Accounts for thermal-to-electric conversion efficiency

    Args:
        fuel_type: Key from FUEL_OPTIONS
        turbine_efficiency: Steam turbine efficiency (default 40%)

    Returns:
        Cost in $/MWh electric
    """
    thermal_cost = get_fuel_cost_per_MWh_thermal(fuel_type)

    # Electric output = thermal × efficiency
    # So cost per MWh electric = thermal cost / efficiency
    electric_cost = thermal_cost / turbine_efficiency

    return electric_cost


def calculate_storage_capex(fuel_type, capacity_MW, backup_hours=200):
    """
    Calculate fuel storage tank CAPEX

    Args:
        fuel_type: Key from FUEL_OPTIONS
        capacity_MW: Boiler capacity in MW
        backup_hours: Hours of fuel storage (default 200 = ~8 days full load)

    Returns:
        Storage tank CAPEX in $
    """
    fuel = FUEL_OPTIONS[fuel_type]

    if not fuel.get('storage_required', False):
        return 0  # No storage needed (e.g., pipeline NG)

    # Total energy needed
    energy_MWh = capacity_MW * backup_hours

    # Convert to gallons
    if 'energy_density_kWh_per_gallon' in fuel:
        gallons_needed = (energy_MWh * 1000) / fuel['energy_density_kWh_per_gallon']

        # Storage cost
        storage_cost = gallons_needed * fuel.get('storage_capex_per_gallon', 2.0)

        return storage_cost

    return 0


def get_cfe_impact(fuel_type, backup_usage_pct):
    """
    Calculate impact of backup fuel on overall CFE percentage

    Args:
        fuel_type: Key from FUEL_OPTIONS
        backup_usage_pct: Percentage of load from backup (e.g., 0.217 for 21.7%)

    Returns:
        Effective CFE percentage
    """
    fuel = FUEL_OPTIONS[fuel_type]
    fuel_cfe = fuel['cfe_factor']

    # Base CFE from renewables + TES
    renewable_cfe = 1.0 - backup_usage_pct

    # Backup contribution to CFE
    backup_cfe = backup_usage_pct * fuel_cfe

    # Total CFE
    total_cfe = renewable_cfe + backup_cfe

    return total_cfe


def compare_fuels_summary():
    """Generate comparison table of all fuels"""

    print("="*90)
    print("BACKUP BOILER FUEL OPTIONS COMPARISON")
    print("="*90)
    print()

    print(f"{'Fuel Type':<25} {'Cost':<15} {'CFE':<10} {'CO2':<15} {'Storage':<15}")
    print(f"{'':25} {'($/MWh elec)':<15} {'Factor':<10} {'(tons/MWh)':<15} {'Required':<15}")
    print("-"*90)

    for key, fuel in FUEL_OPTIONS.items():
        name = fuel['name']
        cost = get_fuel_cost_per_MWh_electric(key)
        cfe = fuel['cfe_factor']
        co2 = fuel['co2_tons_per_MWh']
        storage = "Yes" if fuel.get('storage_required', False) else "Pipeline"

        print(f"{name:<25} ${cost:<14.2f} {cfe:<10.1%} {co2:<15.2f} {storage:<15}")

    print("="*90)
    print()

    print("KEY INSIGHTS:")
    print("  • Natural gas: Cheapest if pipeline available")
    print("  • Propane: Best for no-pipeline regions")
    print("  • Renewable diesel: Boosts CFE to 95%+ (but expensive)")
    print("  • Diesel: Most expensive, highest emissions")
    print()


if __name__ == "__main__":
    print("\n" + "="*90)
    print("BACKUP BOILER FUEL CONFIGURATION MODULE")
    print("="*90)
    print()

    compare_fuels_summary()

    # Example calculations
    print("\nEXAMPLE CALCULATIONS:")
    print("-"*90)

    print("\n1. Fuel Cost Comparison (per MWh electric output):")
    for fuel_type in FUEL_OPTIONS.keys():
        cost = get_fuel_cost_per_MWh_electric(fuel_type)
        print(f"   {FUEL_OPTIONS[fuel_type]['name']:<30} ${cost:>8.2f}/MWh")

    print("\n2. Storage Requirements (50 MW boiler, 200 hours backup):")
    for fuel_type in FUEL_OPTIONS.keys():
        if FUEL_OPTIONS[fuel_type].get('storage_required'):
            storage_cost = calculate_storage_capex(fuel_type, 50, 200)
            print(f"   {FUEL_OPTIONS[fuel_type]['name']:<30} ${storage_cost:>12,.0f}")

    print("\n3. CFE Impact (assuming 21.7% backup usage):")
    baseline_cfe = 0.783  # 78.3% from renewables + TES
    for fuel_type in FUEL_OPTIONS.keys():
        total_cfe = get_cfe_impact(fuel_type, 0.217)
        improvement = total_cfe - baseline_cfe
        print(f"   {FUEL_OPTIONS[fuel_type]['name']:<30} {total_cfe:>6.1%} (Δ{improvement:+.1%})")

    print("\n" + "="*90)
    print("✓ Fuel configuration module loaded successfully")
    print("="*90 + "\n")
