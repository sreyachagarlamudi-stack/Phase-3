# TES Input Sheet Updates Required

Based on meeting feedback from June 24, 2026

## Critical Issues to Fix

### 1. Resource Data (HIGHEST PRIORITY)
**Problem:** Using synthetic wind/solar profiles instead of actual Roman backcast data
**Current:** Wind 18.7% CF, Solar lower than expected
**Target:** Wind ~50% CF, Solar ~30-33% AC
**Action:** Ensure 8760 time series uses actual Roman data, not generated profiles

### 2. Gas Pricing
**Problem:** P_NG set to C0 (zero dollars)
**Target:** P_NG = C4 ($4/MMBTU)
**Impact:** Proper fuel cost ~$40/MWh before variable O&M

### 3. Steam Turbine OpEx (MISSING)
**Problem:** Only modeling CapEx, no variable O&M
**Need to add:**
- Fixed O&M ($/kW-year)
- Variable O&M ($/MWh)
**Why:** Marginal cost calculation currently wrong - comparing amortized CapEx to gas marginal cost

### 4. TES Component Costs (Need to separate)
**Current:** Integrated TES cost
**Need:**
- Charge equipment: Heaters + power electronics ($/kW)
- Discharge equipment: Steam turbine ($/kW) - fixed at 100 MW
- Energy storage: Thermal mass ($/kWh)

## Input Sheet Additions Needed

### New TES Sheet Structure

```
Parameter                    | Value    | Unit        | Source
----------------------------|----------|-------------|--------
# Charge Equipment
tes_heater_capex            | 200      | $/kW        | Industry estimate
tes_heater_efficiency       | 0.95     | fraction    | Resistive heating standard
tes_heater_opex_fixed       | 5        | $/kW-year   | Minimal maintenance
tes_heater_opex_var         | 0        | $/MWh       | No fuel, minimal wear

# Discharge Equipment (Steam Turbine)
tes_turbine_capex           | 800      | $/kW        | Similar to gas turbine
tes_turbine_size_fixed      | 100000   | kW          | Fixed at datacenter load
tes_turbine_eff_min         | 0.34     | fraction    | At 40% load (NREL/EPA)
tes_turbine_eff_max         | 0.39     | fraction    | At 100% load (NREL/EPA)
tes_turbine_min_load        | 0.40     | fraction    | Physics constraint
tes_turbine_opex_fixed      | 15       | $/kW-year   | Similar to gas turbine
tes_turbine_opex_var        | 3        | $/MWh       | Maintenance/wear

# Energy Storage
tes_storage_capex           | 40       | $/kWh       | Thermal mass cost
tes_storage_loss_rate       | 0.01     | fraction/day| Heat loss (1%/day)
tes_storage_opex            | 0.5      | %/year      | Minimal maintenance

# Alternative: Boiler (for backup heat)
boiler_capex                | 300      | $/kW_th     | Much cheaper than NGPP
boiler_efficiency           | 0.85     | fraction    | NG to thermal
boiler_opex_fixed           | 10       | $/kW-year   |
boiler_opex_var             | 2        | $/MWh_th    |
boiler_fuel_type            | NG       | -           | Or renewable diesel
boiler_fuel_cfe             | 0.0      | fraction    | Zero for NG, adjust for RD
```

### Gas Cost Update

```
P_NG file: Change from C0 to C4
Content: 8760 rows, all values = 4.0 ($/MMBTU)
```

### Resource Data Fix

**Solar Sheet:**
- Verify "St" column uses Roman AC data
- Expected average: 30-33% capacity factor
- Source: Roman backcast 8760 time series

**Wind Sheet:**
- Verify "Wt" column uses Roman data
- Expected average: ~50% capacity factor
- Source: Roman backcast 8760 time series

## Calculation Corrections Needed

### Current (WRONG):
```
TES marginal cost = Amortized CapEx / Discharge MWh
= $121/MWh
```

### Correct:
```
TES marginal cost = Variable OpEx only
= Steam turbine var O&M + minimal TES maintenance
= ~$3-5/MWh

Gas marginal cost = Fuel + Variable OpEx
= $40/MWh (fuel) + $5-10/MWh (var O&M)
= ~$45-50/MWh
```

**Key insight:** TES should be MUCH cheaper on marginal basis, but currently comparing apples (CapEx) to oranges (OpEx).

## Model Architecture Changes

### Replace in Pyomo:
1. **Remove:** LDES variables (or repurpose for TES)
2. **Remove:** NGPP (natural gas power plant)
3. **Add:** Boiler variables (much cheaper backup)
4. **Add:** Steam header (receives heat from TES OR boiler)
5. **Add:** BESS as separate optimization dimension

### Steam Header Logic:
```
Heat to steam turbine = TES discharge + Boiler output
Steam turbine electricity = Heat × turbine_efficiency(load)
```

## Implementation Steps

1. **Update gjt_working.xlsx:**
   - Add TES sheet with parameters above
   - Change P_NG from C0 to C4
   - Verify Roman data in St/Wt columns

2. **Update Python code:**
   - Read TES parameters from new sheet
   - Separate charge/discharge/storage costs
   - Add steam turbine OpEx calculation
   - Fix marginal cost comparison (OpEx only)

3. **Re-run optimization:**
   - Should see higher wind/solar capacity factors
   - Should see different TES utilization
   - Gas marginal cost should be ~$45-50/MWh
   - TES marginal cost should be ~$3-5/MWh

## Expected Results After Fix

**Wind:** ~50% CF (not 18.7%)
**Solar:** ~30-33% CF (AC basis confirmed)
**TES utilization:** Should increase significantly when marginal costs are correct
**Gas usage:** Should decrease when proper cost comparison is used

## Questions for Team

1. Exact steam turbine OpEx values? (Using $15/kW-yr fixed, $3/MWh variable as placeholder)
2. Boiler CapEx assumption? (Using $300/kW thermal as placeholder)
3. Should we model multiple turbine blocks (25-50 MW each) or single 100 MW?
4. BESS parameters for optimization? (Need power/energy costs and efficiency)
