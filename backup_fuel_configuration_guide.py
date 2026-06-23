"""
BACKUP FUEL CONFIGURATION GUIDE
================================

This file shows you exactly where to pull:
1. Fuel costs
2. Capacity limits
3. CFE constraints
4. Regional fuel availability

Use this as a template for running scenarios.

Author: Sreya Chagarlamudi
Date: June 17, 2026
"""

from backup_boiler_config import FUEL_OPTIONS, get_fuel_cost_per_MWh_electric

# ==============================================================================
# 1. FUEL COSTS
# ==============================================================================
# Source: backup_boiler_config.py (already created)
# These are market-based averages - update with your actual prices

def get_fuel_costs():
    """
    Get fuel costs for all backup options
    Returns costs in $/MWh electric output
    """
    fuel_costs = {}

    for fuel_type in FUEL_OPTIONS.keys():
        fuel_costs[fuel_type] = get_fuel_cost_per_MWh_electric(fuel_type)

    return fuel_costs


# Example usage:
FUEL_COSTS = get_fuel_costs()
print("\n" + "="*80)
print("FUEL COSTS ($/MWh electric output)")
print("="*80)
for fuel, cost in FUEL_COSTS.items():
    print(f"{fuel:20s} ${cost:>8.2f}/MWh")
print("="*80)

# To update prices, edit backup_boiler_config.py:
# FUEL_OPTIONS['natural_gas']['cost_per_MMBtu'] = YOUR_PRICE


# ==============================================================================
# 2. CAPACITY LIMITS (System Sizing)
# ==============================================================================
# Source: You define these based on system design
# Units: kW (kilowatts)

def get_system_sizing_baseline():
    """
    Baseline system sizing for 100 MW datacenter
    This is what goes in the 'svar' dictionary
    """
    svar = {
        # Solar
        'solar_kW': 300000,  # 300 MW solar

        # Wind
        'wind_kW': 50000,    # 50 MW wind

        # Battery (short-duration)
        'bessD_kW': 100000,      # 100 MW discharge
        'bessC_kW': 100000,      # 100 MW charge
        'bess_kWh': 200000,      # 200 MWh capacity

        # TES (long-duration)
        'tesD_kW': 312500,       # 312.5 MW thermal discharge
                                 # → 125 MW electric (40% turbine efficiency)

        # LDES (generic, optional)
        'ldesD_kW': 0,           # Not using LDES in baseline
        'ldesC_kW': 0,
        'ldes_kWh': 0,

        # Grid connection (0 = off-grid)
        'maxExpMW': 0,           # No export
        'maxImpMW': 0,           # No import

        # ============================================================
        # BACKUP FUEL CAPACITIES (NEW)
        # ============================================================
        # Set to 0 to disable a fuel option

        'ng_boiler_kW': 50000,       # 50 MW NG boiler (if NG available)
        'propane_boiler_kW': 0,      # 0 MW propane (not using in baseline)
        'diesel_boiler_kW': 0,       # 0 MW diesel (not using)
        'rd99_boiler_kW': 0,         # 0 MW renewable diesel (not using)
    }

    return svar


def get_system_sizing_for_region(region_name):
    """
    Get system sizing for specific region
    Automatically enables/disables fuels based on region

    Args:
        region_name: 'texas', 'alaska', 'california', 'midwest'

    Returns:
        svar dictionary with appropriate fuel options
    """
    # Start with baseline
    svar = get_system_sizing_baseline()

    # Regional fuel availability
    if region_name == 'texas':
        # NG pipeline available, use NG boiler
        svar['ng_boiler_kW'] = 50000
        svar['propane_boiler_kW'] = 0
        svar['rd99_boiler_kW'] = 0

    elif region_name == 'alaska':
        # NO NG pipeline, must use stored fuel
        svar['ng_boiler_kW'] = 0           # No NG available
        svar['propane_boiler_kW'] = 50000  # Use propane
        svar['diesel_boiler_kW'] = 0       # Diesel backup option
        svar['rd99_boiler_kW'] = 0

    elif region_name == 'california':
        # NG available, but may need RD99 for CFE compliance
        svar['ng_boiler_kW'] = 50000       # NG available
        svar['propane_boiler_kW'] = 0
        svar['rd99_boiler_kW'] = 0         # Enable if CFE > 95% required

    elif region_name == 'midwest':
        # NG available but expensive firm transmission
        svar['ng_boiler_kW'] = 50000
        svar['propane_boiler_kW'] = 0      # Alternative option
        svar['rd99_boiler_kW'] = 0

    return svar


# ==============================================================================
# 3. CFE CONSTRAINTS
# ==============================================================================
# Source: Regional regulations or project requirements

def get_cfe_requirements():
    """
    CFE requirements by region
    Source: State/federal regulations or corporate commitments
    """
    cfe_requirements = {
        'federal_default': 0.75,    # 75% CFE (typical)
        'texas': 0.75,              # 75% (no state mandate)
        'alaska': 0.75,             # 75% (no state mandate)
        'california': 0.95,         # 95% (SB 100 - 100% by 2045, interim targets)
        'midwest': 0.75,            # 75% (varies by state)
        'corporate_ambitious': 0.90, # 90% (voluntary commitment)
        'google_247': 0.95,         # 95% (Google's 24/7 CFE goal)
    }

    return cfe_requirements


def should_use_renewable_diesel(region, cfe_requirement):
    """
    Determine if renewable diesel needed for CFE compliance

    Args:
        region: Region name
        cfe_requirement: Target CFE percentage (0.0 to 1.0)

    Returns:
        bool: True if RD99 recommended
    """
    # Baseline system achieves 78.3% CFE with NG backup
    baseline_cfe = 0.783

    # RD99 boosts to 98.9% CFE (renewable fuel counts as 95% CFE)
    rd99_cfe = 0.989

    if cfe_requirement <= baseline_cfe:
        # Can meet with NG backup
        return False

    elif baseline_cfe < cfe_requirement < rd99_cfe:
        # Two options:
        # 1. Add more TES/renewables (cheaper)
        # 2. Switch to RD99 (easier)

        if cfe_requirement >= 0.95:
            # Very high target, RD99 recommended
            return True
        else:
            # Mid-range, consider adding TES first
            print(f"⚠️  CFE target {cfe_requirement:.1%} may be achievable by adding TES")
            print(f"    Alternative: Use RD99 to reach {rd99_cfe:.1%}")
            return False  # Let user decide

    else:
        # Target exceeds even RD99 capability (99%+)
        print(f"❌ CFE target {cfe_requirement:.1%} requires 100% renewable backup")
        return True


# ==============================================================================
# 4. REGIONAL FUEL AVAILABILITY
# ==============================================================================
# Source: Site-specific infrastructure assessment

def get_regional_fuel_availability():
    """
    Defines which fuels are available in each region
    Source: Infrastructure surveys, pipeline maps, site assessments

    Returns:
        dict: {region: {fuel: available (bool)}}
    """
    availability = {
        'texas': {
            'natural_gas': True,      # Extensive pipeline network
            'propane': True,          # Available via truck delivery
            'diesel': True,           # Available via truck
            'renewable_diesel': True, # Available via truck
            'biodiesel': True,        # Available via truck
            'notes': 'Major NG hub, all fuels readily available'
        },

        'alaska': {
            'natural_gas': False,     # NO pipeline to remote sites
            'propane': True,          # Delivered via barge/truck
            'diesel': True,           # Primary fuel for remote Alaska
            'renewable_diesel': True, # Available but expensive
            'biodiesel': False,       # Limited availability
            'notes': 'Remote sites have no NG access, rely on stored fuels'
        },

        'california': {
            'natural_gas': True,      # Pipeline available
            'propane': True,          # Available
            'diesel': True,           # Available
            'renewable_diesel': True, # Preferred due to CFE reqs
            'biodiesel': True,        # Available
            'notes': 'All fuels available, but CFE regulations favor RD99'
        },

        'midwest': {
            'natural_gas': True,      # Pipeline available
            'propane': True,          # Common heating fuel, available
            'diesel': True,           # Available
            'renewable_diesel': True, # Growing availability
            'biodiesel': True,        # Corn-belt, common
            'notes': 'NG available but firm transmission may be expensive'
        },
    }

    return availability


def get_enabled_fuels(region_name):
    """
    Get list of fuels to enable for a specific region

    Args:
        region_name: 'texas', 'alaska', 'california', 'midwest'

    Returns:
        list: Fuel types that should be enabled (capacity > 0)
    """
    availability = get_regional_fuel_availability()

    if region_name not in availability:
        print(f"⚠️  Region '{region_name}' not found, using default")
        return ['natural_gas']  # Default to NG

    region = availability[region_name]

    # Return list of available fuels
    enabled = [fuel for fuel, available in region.items()
               if available and fuel != 'notes']

    return enabled


# ==============================================================================
# 5. COMPLETE SCENARIO CONFIGURATION
# ==============================================================================

def configure_scenario(region_name, cfe_target=None):
    """
    Complete scenario configuration for a region
    Returns all parameters needed for optimization

    Args:
        region_name: 'texas', 'alaska', 'california', 'midwest'
        cfe_target: Optional CFE requirement (0.0-1.0)
                   If None, uses regional default

    Returns:
        dict: Complete configuration with all parameters
    """

    # Get regional CFE requirement
    cfe_reqs = get_cfe_requirements()
    if cfe_target is None:
        cfe_target = cfe_reqs.get(region_name, 0.75)

    # Get fuel availability
    enabled_fuels = get_enabled_fuels(region_name)

    # Get system sizing
    svar = get_system_sizing_for_region(region_name)

    # Determine if RD99 needed
    use_rd99 = should_use_renewable_diesel(region_name, cfe_target)

    if use_rd99 and 'renewable_diesel' in enabled_fuels:
        # Enable RD99, disable other backup fuels
        svar['ng_boiler_kW'] = 0
        svar['propane_boiler_kW'] = 0
        svar['rd99_boiler_kW'] = 50000
        primary_fuel = 'renewable_diesel'
    elif 'natural_gas' in enabled_fuels:
        # Use NG (cheapest option)
        svar['ng_boiler_kW'] = 50000
        svar['propane_boiler_kW'] = 0
        svar['rd99_boiler_kW'] = 0
        primary_fuel = 'natural_gas'
    elif 'propane' in enabled_fuels:
        # No NG, use propane
        svar['ng_boiler_kW'] = 0
        svar['propane_boiler_kW'] = 50000
        svar['rd99_boiler_kW'] = 0
        primary_fuel = 'propane'
    else:
        # Default to diesel if nothing else available
        svar['ng_boiler_kW'] = 0
        svar['propane_boiler_kW'] = 0
        svar['diesel_boiler_kW'] = 50000
        primary_fuel = 'diesel'

    # Get fuel cost
    fuel_costs = get_fuel_costs()

    # Build configuration
    config = {
        'region': region_name,
        'cfe_target': cfe_target,
        'primary_fuel': primary_fuel,
        'fuel_cost_per_MWh': fuel_costs[primary_fuel],
        'enabled_fuels': enabled_fuels,
        'svar': svar,
        'vars': {
            # These would come from your gjt_working.xlsx
            # Shown here for completeness
            'BESS_rte': 0.88,
            'LDES_rte': 0.65,
            'tes_rte': 0.90,
            'tes_CDratio': 3.0,
            'tes_duration': 16,
            'tes_st_eff': 40.0,
            'tes_st_min': 40.0,
            'Load_max': 100,  # MW
            'Load_min': 100,
            # ... other vars from Excel
        }
    }

    return config


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("BACKUP FUEL CONFIGURATION GUIDE")
    print("="*80)
    print()

    # Example 1: Texas scenario
    print("EXAMPLE 1: Texas (NG Access)")
    print("-"*80)
    config_texas = configure_scenario('texas')
    print(f"Region:        {config_texas['region']}")
    print(f"CFE Target:    {config_texas['cfe_target']:.1%}")
    print(f"Primary Fuel:  {config_texas['primary_fuel']}")
    print(f"Fuel Cost:     ${config_texas['fuel_cost_per_MWh']:.2f}/MWh")
    print(f"NG Capacity:   {config_texas['svar']['ng_boiler_kW']/1000:.0f} MW")
    print()

    # Example 2: Alaska scenario
    print("EXAMPLE 2: Alaska (No NG Access)")
    print("-"*80)
    config_alaska = configure_scenario('alaska')
    print(f"Region:          {config_alaska['region']}")
    print(f"CFE Target:      {config_alaska['cfe_target']:.1%}")
    print(f"Primary Fuel:    {config_alaska['primary_fuel']}")
    print(f"Fuel Cost:       ${config_alaska['fuel_cost_per_MWh']:.2f}/MWh")
    print(f"Propane Capacity: {config_alaska['svar']['propane_boiler_kW']/1000:.0f} MW")
    print()

    # Example 3: California with 95% CFE
    print("EXAMPLE 3: California (95% CFE Requirement)")
    print("-"*80)
    config_ca = configure_scenario('california', cfe_target=0.95)
    print(f"Region:        {config_ca['region']}")
    print(f"CFE Target:    {config_ca['cfe_target']:.1%}")
    print(f"Primary Fuel:  {config_ca['primary_fuel']}")
    print(f"Fuel Cost:     ${config_ca['fuel_cost_per_MWh']:.2f}/MWh")
    print(f"RD99 Capacity: {config_ca['svar']['rd99_boiler_kW']/1000:.0f} MW")
    print()

    print("="*80)
    print("✓ Configuration guide complete")
    print()
    print("TO USE IN YOUR OPTIMIZATION:")
    print("  1. Import: from backup_fuel_configuration_guide import configure_scenario")
    print("  2. Get config: config = configure_scenario('your_region')")
    print("  3. Pass to model: results = run_optimization(svar=config['svar'])")
    print("="*80 + "\n")
