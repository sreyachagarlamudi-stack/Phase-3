# Technical Clarifications - Team Feedback Response

## Model Architecture Changes Needed

### 1. Steam Turbine Sizing Strategy
**Current approach:** Single large turbine with efficiency curve
**Revised approach:** Multiple small turbine blocks (25-50 MW each)

**Benefits:**
- Greater turndown flexibility (can turn off individual blocks)
- Operate remaining blocks at high efficiency
- Simplifies model - can assume constant high efficiency rather than efficiency curve

**Implementation:** Fix Steam Turbine total capacity = Load (100 MW)

### 2. System Configuration
**Replace:** Natural Gas Power Plant (NGPP)
**With:** Boiler + Steam Turbine

**Rationale:**
- Much lower CapEx than combined cycle plant
- Acceptable for high-CFE systems where backup is rare
- Fuel flexibility (natural gas, renewable diesel, etc.)

### 3. TES System Architecture
**Components to model separately:**
- **Charge cost:** Power electronics + electric heaters ($/kW)
- **Discharge cost:** Steam turbine ($/kW) - fixed at 100 MW
- **Energy cost:** Thermal storage medium ($/kWh)

**Add steam header:**
- Heat sources: TES inventory OR boiler
- Fuel parameters: $/MMBTU, CFE%

### 4. Optimization Variables
**Current:** Coupled power and energy in LDES
**Revised:** Separate optimization dimensions
- TES charge capacity (MW electric)
- TES discharge capacity (MW thermal → electric via turbine)
- TES energy storage (MWh thermal)
- Boiler capacity (MW thermal)

## Key Questions Answered

### Wind Capacity Factor (18.7%)
This is based on the resource profile used. Typical commercial wind:
- Onshore: 25-35% CF
- Offshore: 40-50% CF
- Poor sites: 15-25% CF

**Action:** Verify wind resource data or adjust to site-specific values.

### Solar Resource Basis
**Critical:** Need to verify if solar generation data is:
- DC (nameplate capacity)
- AC (after inverter losses, typically 0.95-0.98 × DC)

**Impact:** 2-5% difference in all solar calculations.

### Water Usage for Steam Turbine
**Source:** Evaporative cooling for condenser
**Not:** Blowdown (which is much smaller)

**Typical rates:**
- 300-500 gallons/MWh for evaporative cooling
- 20-40 gallons/MWh for blowdown

### Low TES Utilization (0.8% CF)
**Root cause:** Economics favor gas backup over TES cycling
- Gas: $40/MWh
- TES equivalent: $121-125/MWh (due to 32-33% round-trip efficiency)

**Solar curtailment:** Yes, optimizer curtails rather than store in TES

**Solution:** Constrain gas to zero to force TES utilization

## Implementation Priorities

### High Priority
1. Add boiler as alternative heat source to steam header
2. Separate TES charge/discharge/energy optimization
3. Fix steam turbine size = 100 MW
4. Run zero-gas constraint cases

### Medium Priority
1. Verify solar DC vs AC basis
2. Update wind capacity factor to realistic values
3. Add BESS as separate optimization dimension
4. Model multiple small turbine blocks instead of efficiency curve

### Low Priority
1. Refine water usage calculations
2. Add fuel flexibility parameters (NG, renewable diesel, etc.)

## Recommended Analysis Updates

**Scenario 1:** Baseline with current architecture
**Scenario 2:** Zero gas constraint (forces TES utilization)
**Scenario 3:** Boiler + TES (no NGPP)
**Scenario 4:** Optimized small turbine blocks
**Scenario 5:** Full multi-dimensional optimization (TES power/energy, BESS, boiler)

## Notes for PowerPoint Updates
See separate document: POWERPOINT_CHANGES_NEEDED.md
