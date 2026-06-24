"""
LDES Technology Comparison Framework

Purpose: Extensible base class for comparing different Long-Duration Energy Storage
         technologies on an apples-to-apples basis

Created: June 22, 2026 (per meeting discussion on LDES comparison)

Design Philosophy:
    - Common interface for all LDES technologies
    - Technology-specific implementations capture unique constraints
    - Enables fair comparison: TES vs Li-ion vs Flow Battery vs H2 vs others
"""

from abc import ABC, abstractmethod
import numpy as np


class LDESSystem(ABC):
    """
    Abstract base class for Long-Duration Energy Storage systems.

    All LDES technologies should inherit from this class and implement
    the required methods for their specific performance characteristics.
    """

    def __init__(self, name, energy_cost_per_kWh, power_cost_per_kW,
                 duration_hours, roundtrip_efficiency):
        """
        Initialize LDES system with basic parameters.

        Args:
            name: Technology name (e.g., "TES", "Lithium-Ion", "Flow Battery")
            energy_cost_per_kWh: Storage capacity cost ($/kWh)
            power_cost_per_kW: Power conversion cost ($/kW)
            duration_hours: Rated duration at full power (hours)
            roundtrip_efficiency: Nominal round-trip efficiency (0-1)
        """
        self.name = name
        self.energy_cost = energy_cost_per_kWh
        self.power_cost = power_cost_per_kW
        self.duration = duration_hours
        self.rte_nominal = roundtrip_efficiency

    @abstractmethod
    def get_discharge_efficiency(self, load_factor, time_stored=0):
        """
        Get discharge efficiency based on operating conditions.

        Args:
            load_factor: Operating power as fraction of rated (0-1)
            time_stored: Hours energy has been stored (for time-dependent loss)

        Returns:
            efficiency: Discharge efficiency (0-1)
        """
        pass

    @abstractmethod
    def get_charge_efficiency(self, charge_rate):
        """
        Get charge efficiency based on charging rate.

        Args:
            charge_rate: Charging power as fraction of rated (0-1)

        Returns:
            efficiency: Charge efficiency (0-1)
        """
        pass

    @abstractmethod
    def get_time_dependent_loss(self, time_stored, energy_stored):
        """
        Get energy loss due to self-discharge or thermal loss.

        Args:
            time_stored: Hours since last state change
            energy_stored: Current state of charge (kWh)

        Returns:
            energy_loss: Energy lost (kWh)
        """
        pass

    @abstractmethod
    def get_minimum_load_constraint(self):
        """
        Get minimum operating load as fraction of rated power.

        Returns:
            min_load_fraction: Minimum load (0-1), or None if no constraint
        """
        pass

    @abstractmethod
    def get_cycle_degradation(self, cycle_count, depth_of_discharge):
        """
        Get capacity degradation based on cycling.

        Args:
            cycle_count: Number of full equivalent cycles
            depth_of_discharge: Average depth of discharge (0-1)

        Returns:
            capacity_retention: Remaining capacity as fraction of original (0-1)
        """
        pass

    def get_total_capital_cost(self, energy_capacity_kWh, power_capacity_kW):
        """
        Calculate total capital cost for given system size.

        Args:
            energy_capacity_kWh: Energy storage capacity (kWh)
            power_capacity_kW: Power conversion capacity (kW)

        Returns:
            total_cost: Total capital cost ($)
        """
        energy_component = energy_capacity_kWh * self.energy_cost
        power_component = power_capacity_kW * self.power_cost
        return energy_component + power_component


# =============================================================================
# THERMAL ENERGY STORAGE (TES) IMPLEMENTATION
# =============================================================================

class ThermalES(LDESSystem):
    """
    Thermal Energy Storage implementation (firebrick/refractory storage).

    Key Characteristics:
    - High-temperature thermal storage (1,500°C)
    - Electric heater for charging (95% efficient)
    - Steam turbine for discharging (efficiency varies with load)
    - Thermal losses: ~1% per day
    - Minimum load: 40% of rated capacity
    - Very low $/kWh but requires steam turbine for discharge
    """

    def __init__(self, turbine_eff_at_min_load=0.35, turbine_eff_at_rated=0.42):
        """
        Initialize TES system.

        Sources:
            - Energy cost: $40/kWh (Rondo/Anora vendor quotes)
            - Power cost: $800/kW (steam turbine + $300/kW heater)
            - Duration: 16 hours (datacenter overnight requirement)
            - RTE: 0.95 * 0.40 ≈ 0.38 (heater × turbine, approximate)

        Args:
            turbine_eff_at_min_load: Efficiency at 40% load (default 0.35 = 35%)
            turbine_eff_at_rated: Efficiency at 100% load (default 0.42 = 42%)
        """
        super().__init__(
            name="Thermal Energy Storage (TES)",
            energy_cost_per_kWh=40,   # $/kWh - Source: Rondo/Anora
            power_cost_per_kW=800,     # $/kW - Source: Steam turbine industry avg
            duration_hours=16,         # hours - Source: Overnight backup requirement
            roundtrip_efficiency=0.38  # Approximate, varies with load
        )

        # Turbine efficiency curve parameters (from meeting 6/22/26)
        self.turbine_eff_min_load = turbine_eff_at_min_load  # NEEDS VALIDATION
        self.turbine_eff_rated = turbine_eff_at_rated        # NEEDS VALIDATION
        self.thermal_loss_rate = 0.01 / 24  # 1% per day = 0.01/24 per hour

    def get_discharge_efficiency(self, load_factor, time_stored=0):
        """
        Steam turbine efficiency as function of load factor.

        ⚠️ IMPORTANT: 40% is MINIMUM LOAD, not efficiency.
        Efficiency varies with load factor.

        Args:
            load_factor: Operating load as fraction of rated (0-1)
            time_stored: Not used for discharge efficiency, but affects total RTE

        Returns:
            efficiency: Thermal-to-electric efficiency (0-1)
        """
        # Below minimum load - cannot operate
        if load_factor < 0.4:
            return 0.0

        # At or above rated load
        elif load_factor >= 1.0:
            return self.turbine_eff_rated

        # Between 40% and 100% load - linear interpolation (SIMPLIFIED)
        # TODO: Replace with actual curve from research
        else:
            slope = (self.turbine_eff_rated - self.turbine_eff_min_load) / 0.6
            return self.turbine_eff_min_load + slope * (load_factor - 0.4)

    def get_charge_efficiency(self, charge_rate):
        """
        Electric heater efficiency (constant for resistive heating).

        Args:
            charge_rate: Charging power as fraction of rated (not used)

        Returns:
            efficiency: Electric-to-thermal efficiency (0-1)
        """
        return 0.95  # 95% - Source: Industry standard for resistive heating

    def get_time_dependent_loss(self, time_stored, energy_stored):
        """
        Thermal loss rate: 1% per day.

        Source: Industry standard for well-insulated thermal storage

        Args:
            time_stored: Hours stored
            energy_stored: Current energy (kWh)

        Returns:
            energy_loss: Energy lost (kWh)
        """
        return energy_stored * self.thermal_loss_rate * time_stored

    def get_minimum_load_constraint(self):
        """
        Steam turbine minimum load: 40% of rated capacity.

        Source: Greg's PtX baseline parameter
        Physical reason: Flow instability below 40%

        Returns:
            min_load_fraction: 0.4 (40%)
        """
        return 0.40

    def get_cycle_degradation(self, cycle_count, depth_of_discharge):
        """
        TES has minimal cycle degradation (mechanical/thermal system).

        Documentation: This is a simplification. Real degradation includes:
        - Refractory material degradation over time
        - Thermal cycling stress
        - Insulation degradation

        For now, assume negligible degradation over 20-year lifetime.
        """
        return 1.0  # No degradation (simplified)


# =============================================================================
# LITHIUM-ION BATTERY IMPLEMENTATION
# =============================================================================

class LithiumBattery(LDESSystem):
    """
    Lithium-Ion Battery implementation.

    Key Characteristics:
    - High $/kWh but mature technology
    - Flat efficiency curve (no minimum load constraint)
    - Negligible self-discharge (<5% per month)
    - Cycle degradation is significant consideration
    - Typical duration: 2-4 hours
    """

    def __init__(self):
        """
        Initialize Li-ion battery system.

        Sources:
            - Energy cost: $150/kWh (2023 industry average)
            - Power cost: $400/kW (inverter/power electronics)
            - Duration: 4 hours (typical for grid-scale)
            - RTE: 88% (round-trip AC-to-AC efficiency)
        """
        super().__init__(
            name="Lithium-Ion Battery",
            energy_cost_per_kWh=150,   # $/kWh - Source: Industry average 2023
            power_cost_per_kW=400,     # $/kW - Source: Inverter costs
            duration_hours=4,          # hours - Typical grid-scale system
            roundtrip_efficiency=0.88  # Round-trip efficiency
        )

        self.cycle_life = 5000  # Full equivalent cycles (typical warranty)

    def get_discharge_efficiency(self, load_factor, time_stored=0):
        """
        Battery discharge efficiency (relatively flat with load).

        Args:
            load_factor: Operating power as fraction of rated
            time_stored: Not significantly affecting efficiency

        Returns:
            efficiency: Discharge efficiency (0-1)
        """
        # Li-ion efficiency is relatively flat across operating range
        # Slight decrease at very high C-rates, but typically 92-95%
        if load_factor > 1.5:  # Beyond rated power
            return 0.90
        else:
            return 0.94

    def get_charge_efficiency(self, charge_rate):
        """
        Battery charge efficiency.

        Args:
            charge_rate: Charging power as fraction of rated

        Returns:
            efficiency: Charge efficiency (0-1)
        """
        # Similar to discharge, relatively flat
        if charge_rate > 1.5:
            return 0.90
        else:
            return 0.94

    def get_time_dependent_loss(self, time_stored, energy_stored):
        """
        Self-discharge for Li-ion: ~2-5% per month.

        Args:
            time_stored: Hours stored
            energy_stored: Current energy (kWh)

        Returns:
            energy_loss: Energy lost (kWh)
        """
        monthly_loss_rate = 0.03  # 3% per month
        hourly_loss_rate = monthly_loss_rate / (30 * 24)
        return energy_stored * hourly_loss_rate * time_stored

    def get_minimum_load_constraint(self):
        """
        No minimum load constraint for batteries.

        Returns:
            None
        """
        return None

    def get_cycle_degradation(self, cycle_count, depth_of_discharge):
        """
        Battery capacity degrades with cycling.

        Simplified model: Linear degradation to 80% capacity at end of life.

        Args:
            cycle_count: Number of full equivalent cycles
            depth_of_discharge: Average DOD (affects degradation rate)

        Returns:
            capacity_retention: Remaining capacity (0-1)
        """
        # Simple linear model: 80% capacity at cycle_life cycles
        degradation_per_cycle = 0.20 / self.cycle_life
        capacity_loss = degradation_per_cycle * cycle_count

        # DOD effect: Deeper cycles cause faster degradation
        dod_factor = 1 + (depth_of_discharge - 0.5) * 0.5  # Arbitrary scaling

        return max(0.5, 1.0 - capacity_loss * dod_factor)


# =============================================================================
# HYDROGEN STORAGE IMPLEMENTATION (PLACEHOLDER)
# =============================================================================

class HydrogenStorage(LDESSystem):
    """
    Hydrogen storage implementation (electrolyzer + storage + fuel cell).

    Key Characteristics:
    - Very long duration capability (days to weeks)
    - Low round-trip efficiency (~35-40%)
    - High capital cost
    - No minimum load constraint for fuel cell
    - Minimal self-discharge (H2 storage losses very low)

    TODO: Implement detailed H2 system model
    """

    def __init__(self):
        super().__init__(
            name="Hydrogen Storage",
            energy_cost_per_kWh=10,    # H2 storage is cheap per kWh
            power_cost_per_kW=2000,    # But electrolyzer + fuel cell expensive
            duration_hours=168,        # Week-long storage
            roundtrip_efficiency=0.38  # electrolyzer (70%) × fuel cell (55%)
        )

    def get_discharge_efficiency(self, load_factor, time_stored=0):
        return 0.55  # Fuel cell efficiency (simplified)

    def get_charge_efficiency(self, charge_rate):
        return 0.70  # Electrolyzer efficiency (simplified)

    def get_time_dependent_loss(self, time_stored, energy_stored):
        return 0.0  # Negligible for compressed H2 storage

    def get_minimum_load_constraint(self):
        return None  # Fuel cells can operate at low loads

    def get_cycle_degradation(self, cycle_count, depth_of_discharge):
        return 0.95  # Some degradation in electrolyzer/fuel cell


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Example usage: Compare LDES technologies.
    """

    print("=" * 80)
    print("LDES TECHNOLOGY COMPARISON FRAMEWORK")
    print("=" * 80)

    # Instantiate different technologies
    tes = ThermalES()
    battery = LithiumBattery()
    hydrogen = HydrogenStorage()

    technologies = [tes, battery, hydrogen]

    print("\nSystem Parameters:")
    print("-" * 80)
    print(f"{'Technology':<25} {'Energy Cost':<15} {'Power Cost':<15} {'Duration':<10} {'RTE':<10}")
    print(f"{'':25} {'($/kWh)':<15} {'($/kW)':<15} {'(hours)':<10} {'(%)':<10}")
    print("-" * 80)

    for tech in technologies:
        print(f"{tech.name:<25} ${tech.energy_cost:<14.0f} ${tech.power_cost:<14.0f} "
              f"{tech.duration:<10.0f} {tech.rte_nominal*100:<10.1f}")

    print("\n" + "=" * 80)
    print("Efficiency Curves (Discharge):")
    print("=" * 80)

    load_factors = [0.2, 0.4, 0.6, 0.8, 1.0]
    print(f"\n{'Load Factor':<15}", end="")
    for tech in technologies:
        print(f"{tech.name:<20}", end="")
    print()

    for lf in load_factors:
        print(f"{lf:<15.1f}", end="")
        for tech in technologies:
            eff = tech.get_discharge_efficiency(lf)
            print(f"{eff*100:<20.1f}", end="")
        print()

    print("\n" + "=" * 80)
    print("Minimum Load Constraints:")
    print("=" * 80)

    for tech in technologies:
        min_load = tech.get_minimum_load_constraint()
        if min_load:
            print(f"{tech.name}: {min_load*100:.0f}%")
        else:
            print(f"{tech.name}: None (can operate at any load)")

    print("\n" + "=" * 80)
    print("Capital Cost Comparison (100 MW, 16-hour system):")
    print("=" * 80)

    power_capacity = 100000  # 100 MW = 100,000 kW
    duration = 16  # hours
    energy_capacity = power_capacity * duration  # 1,600 MWh

    for tech in technologies:
        cost = tech.get_total_capital_cost(energy_capacity, power_capacity)
        cost_per_kw = cost / power_capacity
        print(f"{tech.name:<25} ${cost:>15,.0f}   (${cost_per_kw:>8,.0f}/kW)")

    print("\n" + "=" * 80)
