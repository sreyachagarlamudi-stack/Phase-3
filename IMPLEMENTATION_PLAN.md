# Implementation Plan - TES Model Fixes

## Summary of Issues Found

### From Meeting (June 24):
1. ✗ Using synthetic wind/solar data instead of Roman backcast (Wind: 18.7% should be ~50%)
2. ✗ Gas price set to $0 instead of $4/MMBTU
3. ✗ Missing steam turbine OpEx (only have CapEx)
4. ✗ Wrong marginal cost comparison (comparing TES CapEx to gas OpEx)
5. ✗ Using outdated input sheet version
6. ✗ Need to separate TES into charge/discharge/storage costs
7. ✗ Need to add BESS as optimization dimension
8. ✗ Should replace NGPP with boiler (cheaper for high-CFE)

### From Greg's Feedback:
9. ✗ Consider multiple small turbine blocks (25-50 MW) instead of efficiency curve
10. ✗ Add steam header that can take heat from TES OR boiler
11. ✗ Make fuel parameters flexible ($/MMBTU, CFE%)

## Step-by-Step Fix Plan

### STEP 1: Fix Input Sheet (gjt_working_updated.xlsx)

**A. Verify Resource Data**
```python
# Check that St and Wt columns contain Roman backcast data
# Expected: Solar ~30-33% CF, Wind ~50% CF
# If using synthetic data, replace with actual Roman 8760s
```

**B. Update Gas Pricing**
- Create P_NG file with $4/MMBTU (8760 rows)
- Update reference in input sheet

**C. Add TES Parameters Sheet**
Add new sheet named "TES_PARAMS" with:
- Heater CapEx: $200/kW
- Heater OpEx: $5/kW-yr fixed
- Turbine CapEx: $800/kW
- Turbine OpEx: $15/kW-yr fixed, $3/MWh variable
- Storage CapEx: $40/kWh
- Storage OpEx: 0.5%/year
- Turbine efficiency curve: 34% @ 40% load, 39% @ 100% load
- Minimum load: 40%

**D. Add Boiler Parameters**
- Boiler CapEx: $300/kW_thermal
- Boiler efficiency: 85%
- Boiler OpEx: $10/kW-yr fixed, $2/MWh variable

### STEP 2: Update Python Code Structure

**File: `tes_model_fixed.py`**

```python
# 1. Read TES parameters from new sheet
def load_tes_params(excel_path):
    tes_df = pd.read_excel(excel_path, sheet_name='TES_PARAMS')
    return {
        'heater_capex_per_kW': 200,
        'heater_opex_fix_per_kW_yr': 5,
        'turbine_capex_per_kW': 800,
        'turbine_opex_fix_per_kW_yr': 15,
        'turbine_opex_var_per_MWh': 3,
        'storage_capex_per_kWh': 40,
        'storage_opex_pct': 0.005,
        'turbine_eff_at_min': 0.34,
        'turbine_eff_at_max': 0.39,
        'turbine_min_load': 0.40,
        'turbine_size_kW': 100000,  # Fixed at load
    }

# 2. Calculate MARGINAL costs correctly
def calculate_marginal_costs(tes_params, gas_params):
    # TES marginal cost = ONLY variable OpEx
    tes_marginal = tes_params['turbine_opex_var_per_MWh']
    # ~$3/MWh

    # Gas marginal cost = fuel + variable OpEx
    gas_fuel = 4.0 * gas_params['heat_rate'] / 1000  # $/MMBTU * MMBTU/MWh
    gas_var_opex = gas_params['opex_var_per_MWh']
    gas_marginal = gas_fuel + gas_var_opex
    # ~$45-50/MWh

    return tes_marginal, gas_marginal

# 3. Add BESS optimization
svar = {
    'bessD_kW': optimize,  # Variable
    'bessC_kW': optimize,  # Variable
    'bess_kWh': optimize,  # Variable
    'tesC_kW': optimize,   # Heater capacity (variable)
    'tesD_kW': 100000,     # Turbine fixed at load
    'tes_kWh': optimize,   # Storage capacity (variable)
    'boiler_kW': optimize, # Boiler capacity (variable)
}

# 4. Steam header logic
# Heat sources: TES discharge + Boiler output
# Heat to turbine → Electricity out
```

### STEP 3: Run Corrected Model

**Command:**
```bash
python tes_model_fixed.py --input gjt_working_updated.xlsx --output results_corrected.json
```

**Expected Changes:**
- Wind CF: 18.7% → ~50%
- Solar CF: [current] → ~30-33%
- Gas marginal cost: $40 → $45-50/MWh
- TES marginal cost: $121 → $3-5/MWh
- TES utilization: 0.8% → Much higher
- Gas usage: Should decrease significantly

### STEP 4: Validate Results

**Checks:**
1. ✓ Wind capacity factor ~50%?
2. ✓ Solar capacity factor ~30-33%?
3. ✓ TES marginal cost < gas marginal cost?
4. ✓ TES utilization > 10%?
5. ✓ Using actual Roman data (not synthetic)?
6. ✓ Gas cost includes variable O&M?

### STEP 5: Document Changes

**Update files:**
- EXECUTIVE_SUMMARY.md: Correct capacity factors and costs
- 00_DELIVERABLES.md: Update baseline results
- Create RESULTS_COMPARISON.md showing before/after

## Key Formula Corrections

### OLD (WRONG):
```
TES "cost" = (Amortized CapEx) / (Annual discharge)
           = $1,074M / 8,760,000 MWh
           = $121/MWh

Comparison: $121/MWh (TES) vs $40/MWh (gas)
Decision: Always use gas
```

### NEW (CORRECT):
```
TES marginal cost = Variable OpEx only
                  = $3/MWh (turbine wear + minimal maintenance)

Gas marginal cost = Fuel + Variable OpEx
                  = $40/MWh (fuel) + $8/MWh (var O&M)
                  = $48/MWh

Comparison: $3/MWh (TES) vs $48/MWh (gas)
Decision: Use TES whenever charged, only use gas when TES empty
```

## Timeline

**Today (June 24):**
- [ ] Update input sheet with TES parameters
- [ ] Fix P_NG to $4/MMBTU
- [ ] Verify Roman data in St/Wt

**Tomorrow (June 25):**
- [ ] Update Python code with correct marginal cost logic
- [ ] Add BESS optimization variables
- [ ] Run corrected model
- [ ] Validate results

**June 26:**
- [ ] Update all documentation
- [ ] Create before/after comparison
- [ ] Post results to Slack thread

## Questions to Ask Team

1. **Steam turbine OpEx values:** Using $15/kW-yr fixed + $3/MWh variable - confirm?
2. **Boiler approach:** Confirm we want boiler instead of NGPP for backup?
3. **Multiple turbine blocks:** Use 2×50 MW or 4×25 MW blocks?
4. **BESS costs:** What CapEx ($/kW, $/kWh) should we use?
5. **Roman data:** How to access the actual 8760 time series?

## Files Modified

- [x] gjt_working_updated.xlsx (copied to Phase 3)
- [ ] gjt_working_updated.xlsx (add TES_PARAMS sheet)
- [ ] Create C4.csv for P_NG pricing
- [ ] tes_model_fixed.py (new file with corrections)
- [ ] EXECUTIVE_SUMMARY.md (update with correct results)
- [ ] 00_DELIVERABLES.md (update baseline numbers)
