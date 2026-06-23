"""
Comprehensive Validation Checks for TES Optimization Results

Purpose: Catch errors and inconsistencies in optimization outputs
Created: June 22, 2026 (per meeting action items)
"""

import pandas as pd
import numpy as np


def validate_optimization_results(results_df, tes_capacity_kWh, turbine_capacity_kW,
                                  solar_capacity_kW, wind_capacity_kW,
                                  min_turbine_load_fraction=0.4,
                                  turbine_efficiency=0.39):
    """
    Comprehensive validation of optimization outputs.

    Args:
        results_df: DataFrame with hourly results from optimization
        tes_capacity_kWh: TES energy storage capacity (kWh)
        turbine_capacity_kW: TES turbine rated capacity (kW)
        min_turbine_load_fraction: Minimum load as fraction of rated (default 0.4 = 40%)
        solar_capacity_kW: Solar generation capacity (kW)
        wind_capacity_kW: Wind generation capacity (kW)

    Returns:
        errors: List of error messages (critical issues)
        warnings: List of warning messages (potential issues)
    """

    errors = []
    warnings = []

    print("=" * 80)
    print("VALIDATION CHECKS - TES OPTIMIZATION RESULTS")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. ENERGY BALANCE CHECK
    # -------------------------------------------------------------------------
    print("\n1. Checking Energy Balance...")

    required_cols = ['Lt', 'St', 'Wt', 'Gtest', 'G1t', 'G2t', 'CleanFirm',
                     'Zt', 'BDt', 'LdDt', 'TCt', 'BCt', 'LdCt', 'Scurtt', 'Wcurtt']

    missing_cols = [col for col in required_cols if col not in results_df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        print(f"   ❌ ERROR: Missing columns for energy balance check")
    else:
        for t in results_df.index:
            # Supply side
            generation = (results_df.loc[t, 'St'] + results_df.loc[t, 'Wt'] +
                         results_df.loc[t, 'Gtest'] + results_df.loc[t, 'G1t'] +
                         results_df.loc[t, 'G2t'] + results_df.loc[t, 'CleanFirm'] +
                         results_df.loc[t, 'Zt'] + results_df.loc[t, 'BDt'] +
                         results_df.loc[t, 'LdDt'])

            # Demand side
            load = (results_df.loc[t, 'Lt'] + results_df.loc[t, 'TCt'] +
                   results_df.loc[t, 'BCt'] + results_df.loc[t, 'LdCt'] +
                   results_df.loc[t, 'Scurtt'] + results_df.loc[t, 'Wcurtt'])

            imbalance = abs(generation - load)
            if imbalance > 1.0:  # Tolerance: 1 kW
                errors.append(f"Energy imbalance at hour {t}: Gen={generation:.2f} kW, Load={load:.2f} kW, Diff={imbalance:.2f} kW")

        if not any("Energy imbalance" in e for e in errors):
            print(f"   ✓ PASS: Energy balance maintained (tolerance: 1 kW)")
        else:
            print(f"   ❌ FAIL: {sum(1 for e in errors if 'Energy imbalance' in e)} hours with imbalance")

    # -------------------------------------------------------------------------
    # 2. TES STATE OF CHARGE BOUNDS CHECK
    # -------------------------------------------------------------------------
    print("\n2. Checking TES State of Charge Bounds...")

    if 'TXt' in results_df.columns:
        soc_below_zero = (results_df['TXt'] < -0.1).sum()  # Small tolerance for numerical errors
        soc_above_max = (results_df['TXt'] > tes_capacity_kWh + 0.1).sum()

        if soc_below_zero > 0:
            errors.append(f"TES SOC below zero in {soc_below_zero} hours")
            print(f"   ❌ FAIL: SOC < 0 in {soc_below_zero} hours")

        if soc_above_max > 0:
            errors.append(f"TES SOC above capacity in {soc_above_max} hours")
            print(f"   ❌ FAIL: SOC > capacity in {soc_above_max} hours")

        if soc_below_zero == 0 and soc_above_max == 0:
            print(f"   ✓ PASS: SOC within bounds [0, {tes_capacity_kWh:.0f} kWh]")
            print(f"           Min SOC: {results_df['TXt'].min():.2f} kWh")
            print(f"           Max SOC: {results_df['TXt'].max():.2f} kWh")
    else:
        warnings.append("TXt (TES SOC) column not found - cannot validate SOC bounds")
        print(f"   ⚠️  WARNING: TXt column missing")

    # -------------------------------------------------------------------------
    # 3. TURBINE MINIMUM LOAD CHECK
    # -------------------------------------------------------------------------
    print("\n3. Checking Turbine Minimum Load Constraint...")

    if 'Gtest' in results_df.columns and 'Kstt' in results_df.columns:
        # Minimum ELECTRIC output = turbine_capacity_kW × efficiency × min_load_fraction
        # Per pyomo code: T3min = tesD_kW * tes_st_eff / 100 * tes_st_min / 100
        # Example: 100,000 kW * 0.39 * 0.40 = 15,600 kW electric minimum
        min_electric_power = turbine_capacity_kW * turbine_efficiency * min_turbine_load_fraction

        violations = 0

        for t in results_df.index:
            turbine_power = results_df.loc[t, 'Gtest']
            turbine_on = results_df.loc[t, 'Kstt']

            # If turbine is on (status = 1), power must be >= minimum
            if turbine_on > 0.5:  # Binary variable = 1
                if turbine_power < min_electric_power - 0.1 and turbine_power > 0.1:  # Small tolerance
                    errors.append(f"Turbine below minimum load at hour {t}: {turbine_power:.2f} kW < {min_electric_power:.2f} kW")
                    violations += 1

        if violations == 0:
            operating_hours = (results_df['Kstt'] > 0.5).sum()
            print(f"   ✓ PASS: No minimum load violations")
            print(f"           Operating hours: {operating_hours}")
            print(f"           Minimum electric output: {min_electric_power:.0f} kW")
            print(f"           (= {turbine_capacity_kW:.0f} kW × {turbine_efficiency:.0%} eff × {min_turbine_load_fraction:.0%} min load)")
        else:
            print(f"   ❌ FAIL: {violations} hours with minimum load violations")
    else:
        warnings.append("Gtest or Kstt columns not found - cannot validate minimum load")
        print(f"   ⚠️  WARNING: Missing turbine columns")

    # -------------------------------------------------------------------------
    # 4. SOLAR ALLOCATION CHECK (if tracking variables exist)
    # -------------------------------------------------------------------------
    print("\n4. Checking Solar Allocation...")

    if all(col in results_df.columns for col in ['St', 'SolarToLoad', 'SolarToTES', 'Scurtt']):
        allocation_errors = 0

        for t in results_df.index:
            solar_gen = results_df.loc[t, 'St']
            solar_allocated = (results_df.loc[t, 'SolarToLoad'] +
                              results_df.loc[t, 'SolarToTES'] +
                              results_df.loc[t, 'Scurtt'])

            if abs(solar_gen - solar_allocated) > 0.1:  # 0.1 kW tolerance
                errors.append(f"Solar allocation mismatch at hour {t}: Gen={solar_gen:.2f}, Allocated={solar_allocated:.2f}")
                allocation_errors += 1

        if allocation_errors == 0:
            total_solar = results_df['St'].sum()
            total_to_load = results_df['SolarToLoad'].sum()
            total_to_tes = results_df['SolarToTES'].sum()
            total_curtailed = results_df['Scurtt'].sum()

            print(f"   ✓ PASS: Solar allocation balanced")
            print(f"           Total solar: {total_solar/1e6:.2f} GWh")
            print(f"           To load: {total_to_load/1e6:.2f} GWh ({total_to_load/total_solar*100:.1f}%)")
            print(f"           To TES: {total_to_tes/1e6:.2f} GWh ({total_to_tes/total_solar*100:.1f}%)")
            print(f"           Curtailed: {total_curtailed/1e6:.2f} GWh ({total_curtailed/total_solar*100:.1f}%)")
        else:
            print(f"   ❌ FAIL: {allocation_errors} hours with allocation mismatch")
    else:
        print(f"   ⚠️  INFO: Solar allocation tracking not enabled (SolarToLoad/SolarToTES columns missing)")

    # -------------------------------------------------------------------------
    # 5. TURBINE EFFICIENCY RANGE CHECK
    # -------------------------------------------------------------------------
    print("\n5. Checking Turbine Efficiency Range...")

    if 'Gtest' in results_df.columns and 'TDt' in results_df.columns:
        unusual_efficiency = 0

        for t in results_df.index:
            thermal_discharge = results_df.loc[t, 'TDt']
            electric_output = results_df.loc[t, 'Gtest']

            if thermal_discharge > 1.0:  # Avoid division by near-zero
                efficiency = electric_output / thermal_discharge

                # Typical steam turbine efficiency: 25-50%
                if efficiency < 0.25 or efficiency > 0.50:
                    warnings.append(f"Unusual turbine efficiency at hour {t}: {efficiency*100:.1f}%")
                    unusual_efficiency += 1

        if unusual_efficiency == 0:
            print(f"   ✓ PASS: All efficiencies in expected range (25-50%)")
        else:
            print(f"   ⚠️  WARNING: {unusual_efficiency} hours with unusual efficiency")
            print(f"              (Typical range: 25-50% for steam turbines)")
    else:
        warnings.append("Cannot calculate turbine efficiency - missing TDt or Gtest")
        print(f"   ⚠️  WARNING: Missing columns for efficiency check")

    # -------------------------------------------------------------------------
    # 6. CAPACITY FACTOR CHECKS
    # -------------------------------------------------------------------------
    print("\n6. Checking Capacity Factors...")

    if 'St' in results_df.columns and solar_capacity_kW > 0:
        solar_cf = (results_df['St'].sum() / (len(results_df) * solar_capacity_kW)) * 100
        print(f"   Solar CF: {solar_cf:.1f}%")

        if solar_cf > 100:
            errors.append(f"Solar capacity factor > 100%: {solar_cf:.1f}%")
            print(f"   ❌ ERROR: Solar CF > 100%")

    if 'Wt' in results_df.columns and wind_capacity_kW > 0:
        wind_cf = (results_df['Wt'].sum() / (len(results_df) * wind_capacity_kW)) * 100
        print(f"   Wind CF: {wind_cf:.1f}%")

        if wind_cf > 100:
            errors.append(f"Wind capacity factor > 100%: {wind_cf:.1f}%")
            print(f"   ❌ ERROR: Wind CF > 100%")

    if 'Gtest' in results_df.columns and turbine_capacity_kW > 0:
        tes_cf = (results_df['Gtest'].sum() / (len(results_df) * turbine_capacity_kW)) * 100
        print(f"   TES Turbine CF: {tes_cf:.1f}%")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    if len(errors) == 0 and len(warnings) == 0:
        print("✓ ALL CHECKS PASSED - No errors or warnings")
    else:
        if len(errors) > 0:
            print(f"\n❌ ERRORS FOUND: {len(errors)}")
            for i, error in enumerate(errors[:10], 1):  # Show first 10
                print(f"   {i}. {error}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")

        if len(warnings) > 0:
            print(f"\n⚠️  WARNINGS: {len(warnings)}")
            for i, warning in enumerate(warnings[:10], 1):  # Show first 10
                print(f"   {i}. {warning}")
            if len(warnings) > 10:
                print(f"   ... and {len(warnings) - 10} more warnings")

    print("=" * 80)

    return errors, warnings


def validate_solar_allocation_detailed(results_df):
    """
    Detailed validation of solar allocation priority logic.

    Verifies:
    1. Solar to load first (priority 1)
    2. Excess solar to TES charging (priority 2)
    3. Remainder curtailed (priority 3)
    """

    print("\n" + "=" * 80)
    print("DETAILED SOLAR ALLOCATION VALIDATION")
    print("=" * 80)

    required_cols = ['St', 'Lt', 'SolarToLoad', 'SolarToTES', 'Scurtt', 'TCt']
    if not all(col in results_df.columns for col in required_cols):
        print("⚠️  Cannot perform detailed validation - missing columns")
        return

    priority_violations = 0

    for t in results_df.index:
        solar_gen = results_df.loc[t, 'St']
        load = results_df.loc[t, 'Lt']
        solar_to_load = results_df.loc[t, 'SolarToLoad']
        solar_to_tes = results_df.loc[t, 'SolarToTES']
        curtailed = results_df.loc[t, 'Scurtt']

        # Check priority logic
        # If solar is curtailed, TES should be fully charged (or at max charge rate)
        if curtailed > 0.1 and solar_to_tes < solar_gen * 0.9:
            priority_violations += 1

    if priority_violations == 0:
        print("✓ Solar allocation priority logic validated")
    else:
        print(f"⚠️  {priority_violations} hours with potential priority violations")

    print("=" * 80)


if __name__ == "__main__":
    """
    Example usage of validation functions.
    """

    print("TES Optimization Validation Module")
    print("=" * 80)
    print("\nUsage:")
    print("  from validation_checks import validate_optimization_results")
    print("  errors, warnings = validate_optimization_results(results_df, ...)")
    print("\n" + "=" * 80)
