# PowerPoint Changes Needed - Phase 3 Deck

## Slide 2: Dispatch Results - CRITICAL FIXES NEEDED

### Issue: Dispatch data appears incorrect
**Problems identified:**
1. Wind NCF shown as 18.7% (low, needs verification)
2. TES utilization only 0.8% (economics favor gas over TES)
3. Solar curtailment not clearly shown
4. BESS presence unclear

### Changes to make:
1. **Add clarification text:**
   "Baseline case shows economic preference for gas backup ($40/MWh) over TES cycling (equivalent $121-125/MWh due to 32-33% round-trip efficiency). TES underutilized at 0.8% capacity factor."

2. **Add bullet point:**
   "Solar curtailment: [X] MWh/year due to oversupply during peak generation"

3. **Clarify wind capacity factor:**
   "Wind: 18.7% CF (conservative resource assumption - verify site-specific data)"

4. **Add callout box:**
   "Key Finding: Zero-gas constraint required to force TES utilization and achieve 100% CFE"

## Slide: Steam Turbine Architecture

### Issue: Need to address turndown strategy

### Changes to make:
1. **Update architecture diagram:**
   - Show multiple small turbine blocks (25-50 MW each) instead of single large unit
   - Label: "Modular approach: 2-4 turbine blocks for turndown flexibility"

2. **Revise efficiency discussion:**
   - Remove efficiency curve complexity
   - Add: "Multiple small blocks operated at constant high efficiency (~39%)"
   - Add: "Turndown achieved by shutting off individual blocks, not reducing load per block"

3. **Add slide note:**
   "Antora recommendation: smaller turbine blocks (25 or 50 MW) provide operational flexibility without efficiency penalty"

## Slide: System Architecture / Component Costs

### Issue: Need to show boiler as alternative to NGPP

### Changes to make:
1. **Add new architecture option:**
   - "Configuration A: NGPP (combined cycle) - High CapEx, high efficiency"
   - "Configuration B: Boiler + Steam Turbine - Low CapEx, lower efficiency"
   - "Recommendation: Configuration B for high-CFE systems (backup used rarely)"

2. **Update cost breakdown:**
   - Add: "Boiler CapEx: $[X]/kW (vs NGPP: $800-1000/kW)"
   - Add: "Fuel flexibility: Natural gas, renewable diesel, other"

3. **Update optimization variables:**
   - Separate: Charge power ($/kW heaters)
   - Separate: Discharge power ($/kW turbine) - fixed at 100 MW
   - Separate: Energy storage ($/kWh thermal)

## Slide: Water Usage

### Issue: Clarify water usage source

### Changes to make:
1. **Add clarification:**
   "Water usage: Evaporative cooling for steam turbine condenser loop (300-500 gal/MWh)"
   "Blowdown: Additional 20-40 gal/MWh"

## New Slide Needed: Model Limitations & Next Steps

### Add slide with:
1. **Current Model Limitations:**
   - Solar resource basis needs verification (DC vs AC)
   - Wind capacity factor may be conservative (18.7% vs typical 25-35%)
   - TES utilization artificially low due to gas competition
   - Single turbine efficiency curve vs modular approach

2. **Recommended Analysis Updates:**
   - Run zero-gas constraint scenarios
   - Implement boiler + steam header architecture
   - Separate TES charge/discharge/energy optimization
   - Add BESS as optimization dimension
   - Model small turbine blocks (25-50 MW each)

3. **Expected Impact:**
   - Higher TES utilization in zero-gas scenarios
   - Lower system CapEx with boiler vs NGPP
   - More realistic operational flexibility

## Slide: LDES Technology Comparison

### Changes to make:
1. **Add note about TES architecture:**
   "TES costs shown as integrated system. Revised analysis will separate:
   - Charge equipment: Power electronics + heaters
   - Discharge equipment: Steam turbine (fixed at load)
   - Energy storage: Thermal mass"

## General Presentation Updates

### Talking Points to Add:
1. "Current results show baseline scenario with gas competition - explains low TES utilization"
2. "Model being refined to implement boiler architecture and separate cost optimization"
3. "Small turbine blocks (per Antora) will improve operational flexibility"
4. "Zero-gas scenarios will show true TES performance for 100% CFE target"

### Visual Updates:
- Add color-coding: Green for CFE sources, Red for gas backup, Yellow for curtailment
- Add arrows showing "Economic preference" on dispatch charts
- Update architecture diagrams to show modular turbine blocks
- Add steam header to system diagram

## Summary for Presenter

**Key Message:**
"The baseline analysis shows that TES is economically underutilized when competing with gas backup. The next phase will model zero-gas scenarios with boiler architecture and modular turbine design to demonstrate true 100% CFE performance."

**Questions to Anticipate:**
1. Q: "Why is TES utilization so low?"
   A: "Economics favor gas at $40/MWh over TES cycling at equivalent $121-125/MWh. Zero-gas constraint removes this competition."

2. Q: "Why not just use the efficiency curve?"
   A: "Modular turbine blocks (25-50 MW) allow turndown without efficiency penalty - simpler and more realistic."

3. Q: "What about BESS?"
   A: "BESS should be included as separate optimization dimension alongside TES for short-duration vs long-duration storage."
