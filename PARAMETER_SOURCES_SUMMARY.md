# Parameter Sources - Quick Reference Guide

**Question:** "Where do I pull fuel costs, capacity limits, CFE constraints, and regional fuel availability from?"

**Answer:** Here's exactly where each parameter comes from! 👇

---

## **Parameter Source Map**

```
YOUR OPTIMIZATION MODEL
    │
    ├─── 1. FUEL COSTS ────────────────────────────────┐
    │         Source: backup_boiler_config.py          │
    │         (I created this for you!)                │
    │         Default values: EIA/market averages      │
    │         Update with your actual fuel prices      │
    │                                                   │
    │         Natural Gas:      $36.75/MWh             │
    │         Propane:          $170.75/MWh            │
    │         Diesel:           $218.25/MWh            │
    │         Renewable Diesel: $280.50/MWh            │
    │                                                   │
    ├─── 2. CAPACITY LIMITS ───────────────────────────┤
    │         Source: svar dictionary (you define)     │
    │         Based on: System design decisions        │
    │                                                   │
    │         Example:                                 │
    │         svar = {                                 │
    │           'ng_boiler_kW': 50000,   # 50 MW       │
    │           'propane_boiler_kW': 0,  # Not using   │
    │           'tesD_kW': 312500,       # 312.5 MW    │
    │         }                                        │
    │                                                   │
    ├─── 3. CFE CONSTRAINTS ───────────────────────────┤
    │         Source: Regional regulations             │
    │         OR: Corporate commitments                │
    │                                                   │
    │         Examples:                                │
    │         Texas:      75% (no mandate)             │
    │         California: 95% (SB 100 goal)            │
    │         Google:     95% (24/7 CFE)               │
    │                                                   │
    ├─── 4. FUEL AVAILABILITY ─────────────────────────┤
    │         Source: Site assessment                  │
    │         Based on: Infrastructure survey          │
    │                                                   │
    │         Texas:      NG pipeline ✓                │
    │         Alaska:     NG pipeline ✗ (use propane)  │
    │         California: NG pipeline ✓ (but use RD99) │
    │                                                   │
    └───────────────────────────────────────────────────┘
```

---

## **1. Fuel Costs 💰**

### **Where They Come From:**

```python
# File: backup_boiler_config.py (lines 15-110)

FUEL_OPTIONS = {
    'natural_gas': {
        'cost_per_MMBtu': 5.00,              # ← EIA Henry Hub average
        'cost_per_kWh_thermal': 0.0147,      # ← Calculated from $/MMBtu
        # Converts to $36.75/MWh electric (÷ turbine efficiency)
    },
    'propane': {
        'cost_per_gallon': 2.50,             # ← Retail delivered price
        'cost_per_kWh_thermal': 0.0683,
        # Converts to $170.75/MWh electric
    },
    # etc.
}
```

### **How to Use:**

```python
from backup_boiler_config import get_fuel_cost_per_MWh_electric

# Get fuel cost
ng_cost = get_fuel_cost_per_MWh_electric('natural_gas')
# Returns: 36.75 ($/MWh)
```

### **How to Update:**

**Option A:** Edit `backup_boiler_config.py` directly
```python
# Line 28: Change NG price
FUEL_OPTIONS['natural_gas']['cost_per_MMBtu'] = 6.50  # Your price

# Line 52: Change propane price
FUEL_OPTIONS['propane']['cost_per_gallon'] = 3.00     # Your price
```

**Option B:** Get quotes from vendors
- Call local NG utility: "What's your commercial rate?"
- Call propane supplier: "What's your delivered price for 200-hour supply?"
- Update `backup_boiler_config.py` with real prices

### **Default Sources (If You Don't Have Real Prices):**

| Fuel | Default Price | Source |
|------|---------------|--------|
| Natural Gas | $5/MMBtu | EIA Henry Hub average 2025 |
| Propane | $2.50/gal | EIA retail average 2025 |
| Diesel | $3.50/gal | EIA diesel retail 2025 |
| Renewable Diesel | $4.50/gal | Market premium over diesel |

---

## **2. Capacity Limits 🏗️**

### **Where They Come From:**

**You define these based on system design!**

```python
# In your optimization runner script:

svar = {
    # Solar capacity (design decision)
    'solar_kW': 300000,        # 300 MW - based on land area, budget

    # Wind capacity (design decision)
    'wind_kW': 50000,          # 50 MW - based on site wind resource

    # TES capacity (design decision)
    'tesD_kW': 312500,         # 312.5 MW thermal

    # BACKUP BOILER CAPACITY (NEW - you decide!)
    'ng_boiler_kW': 50000,     # 50 MW NG boiler
                               # Rule of thumb: size = peak load
                               # (100 MW datacenter → 50-100 MW backup)

    'propane_boiler_kW': 0,    # 0 = not using propane
    'rd99_boiler_kW': 0,       # 0 = not using RD99
}
```

### **How to Decide Backup Capacity:**

**Rule of Thumb:**
- **Minimum:** 50% of peak load (50 MW for 100 MW datacenter)
- **Typical:** 75% of peak load (75 MW)
- **Conservative:** 100% of peak load (100 MW)

**Why not always 100%?**
- Cost! Larger capacity = higher CAPEX
- Backup only runs 21.7% of time in baseline
- 50 MW backup is sufficient with TES/battery

### **Example Decision Process:**

```
1. Peak load = 100 MW
2. Renewables + TES can cover most hours
3. Worst-case gap = 50 MW (evening, cloudy day)
4. → Size backup at 50 MW
5. If needed more, add more TES instead (cheaper)
```

---

## **3. CFE Constraints 📊**

### **Where They Come From:**

**Three sources:**

#### **A. Federal Regulations**
- No federal CFE mandate (yet)
- Default: 75% as "good practice"

#### **B. State Regulations**

| State | CFE Requirement | Source | Year |
|-------|----------------|--------|------|
| **California** | 60% by 2030<br>100% by 2045 | SB 100 | 2018 |
| **New York** | 70% by 2030<br>100% by 2040 | CLCPA | 2019 |
| **Washington** | 80% by 2030<br>100% by 2045 | CETA | 2019 |
| **Texas** | None | - | - |

**Where to find your state:**
- Google: "[Your State] renewable energy mandate"
- Check state energy office website
- Look for "RPS" (Renewable Portfolio Standard)

#### **C. Corporate Commitments**

| Company | CFE Target | Source |
|---------|-----------|--------|
| **Google** | 90% by 2025<br>100% 24/7 by 2030 | Sustainability report |
| **Microsoft** | 100% by 2025 | Carbon negative pledge |
| **Amazon** | 100% by 2025 | Climate Pledge |
| **Meta** | 100% by 2020 (achieved) | RE100 |

**If you're building for a hyperscaler:**
- Use their CFE target (often 90-95%)
- Check PPA requirements
- Ask their procurement team

### **How to Use in Your Model:**

```python
from backup_fuel_configuration_guide import get_cfe_requirements

cfe_reqs = get_cfe_requirements()

# Get requirement for California
ca_cfe = cfe_reqs['california']  # Returns: 0.95 (95%)

# Pass to optimization
config = configure_scenario('california', cfe_target=ca_cfe)
```

### **Default CFE Targets:**

```python
# From backup_fuel_configuration_guide.py
cfe_requirements = {
    'texas': 0.75,              # 75% (no mandate, industry standard)
    'california': 0.95,         # 95% (interim SB 100 target)
    'alaska': 0.75,             # 75% (no mandate)
    'corporate_ambitious': 0.90, # 90% (typical hyperscaler)
}
```

---

## **4. Regional Fuel Availability 🗺️**

### **Where It Comes From:**

**Site-specific infrastructure assessment**

#### **How to Determine:**

**Step 1:** Check NG Pipeline Access
- Visit: [EIA Natural Gas Pipeline Map](https://www.eia.gov/naturalgas/archive/analysis_publications/ngpipeline/)
- Or call local gas utility: "Do you serve [address]?"

**Step 2:** If No NG, What's Available?
- Propane: Always available via truck (rural delivery)
- Diesel: Always available via truck
- Renewable Diesel: Check with suppliers (limited in remote areas)

**Step 3:** Update Configuration

```python
# Texas - NG pipeline available
svar['ng_boiler_kW'] = 50000      # Enable NG
svar['propane_boiler_kW'] = 0     # Disable propane

# Alaska - NO NG pipeline
svar['ng_boiler_kW'] = 0          # Disable NG
svar['propane_boiler_kW'] = 50000 # Enable propane
```

### **Pre-Defined Regions:**

```python
# From backup_fuel_configuration_guide.py

availability = {
    'texas': {
        'natural_gas': True,      # ✓ Extensive pipeline
        'propane': True,
        'renewable_diesel': True,
    },

    'alaska': {
        'natural_gas': False,     # ✗ No pipeline to remote sites
        'propane': True,          # ✓ Barge/truck delivery
        'diesel': True,
    },

    'california': {
        'natural_gas': True,      # ✓ Pipeline available
        'renewable_diesel': True, # ✓ Preferred for CFE
    },
}
```

### **How to Use:**

```python
from backup_fuel_configuration_guide import get_enabled_fuels

# Get available fuels for Alaska
fuels = get_enabled_fuels('alaska')
# Returns: ['propane', 'diesel', 'renewable_diesel']
# Note: 'natural_gas' NOT in list (no pipeline)
```

---

## **Complete Example: Texas Scenario**

Here's how all 4 parameters come together:

```python
from backup_fuel_configuration_guide import configure_scenario

# Configure Texas scenario
config = configure_scenario('texas')

# What you get:
{
    'region': 'texas',

    # 1. FUEL COSTS (from backup_boiler_config.py)
    'fuel_cost_per_MWh': 36.75,        # NG cost

    # 2. CAPACITY LIMITS (from svar)
    'svar': {
        'ng_boiler_kW': 50000,         # 50 MW NG boiler
        'propane_boiler_kW': 0,        # Not using
        'tesD_kW': 312500,             # 312.5 MW TES
        # ... more capacities
    },

    # 3. CFE CONSTRAINT (from regional reqs)
    'cfe_target': 0.75,                # 75% CFE

    # 4. FUEL AVAILABILITY (from site assessment)
    'enabled_fuels': ['natural_gas', 'propane', 'diesel', 'renewable_diesel'],
    'primary_fuel': 'natural_gas',     # Cheapest available
}

# Now pass to optimization:
results = run_optimization(svar=config['svar'])
```

---

## **Quick Start Guide**

### **To Run Your Own Scenario:**

**Step 1:** Determine your site
```python
region = 'texas'  # or 'alaska', 'california', 'midwest'
```

**Step 2:** Check if NG available
- Yes → Use 'texas' or 'midwest' template
- No → Use 'alaska' template

**Step 3:** Get CFE requirement
- Look up state mandate OR
- Check corporate PPA requirement OR
- Use default 75%

**Step 4:** Configure scenario
```python
from backup_fuel_configuration_guide import configure_scenario

config = configure_scenario(
    region_name='texas',      # Your region
    cfe_target=0.75          # Your CFE requirement
)
```

**Step 5:** Run optimization
```python
results = run_optimization(svar=config['svar'])
```

**Done!** The configuration automatically:
- ✅ Sets fuel costs (from market data)
- ✅ Enables appropriate fuels (based on availability)
- ✅ Sizes backup capacity (50 MW default)
- ✅ Applies CFE constraints (if > 95%, switches to RD99)

---

## **Summary Table**

| Parameter | Source File | How to Update | Example Value |
|-----------|-------------|---------------|---------------|
| **Fuel Costs** | `backup_boiler_config.py` | Edit FUEL_OPTIONS dict | NG: $36.75/MWh |
| **Capacity Limits** | Your script (svar) | Edit svar dictionary | 50 MW boiler |
| **CFE Constraints** | State regs / PPA | configure_scenario() | 75% or 95% |
| **Fuel Availability** | Site assessment | configure_scenario() | NG: Yes/No |

---

## **Files You Now Have**

1. ✅ **`backup_boiler_config.py`**
   - Defines all fuel options
   - Provides cost calculations
   - Source for fuel costs

2. ✅ **`backup_fuel_configuration_guide.py`**
   - Complete parameter guide
   - Pre-configured regional scenarios
   - One function to configure everything

3. ✅ **`backup_fuel_analysis.py`**
   - Runs economic comparisons
   - Outputs LCOE for each option

4. ✅ **`BACKUP_FUEL_ANALYSIS_REPORT.md`**
   - 26-page comprehensive report
   - All findings documented

5. ✅ **`PARAMETER_SOURCES_SUMMARY.md`** (this file)
   - Quick reference guide
   - Where to pull each parameter

---

## **Next Steps**

### **For Your Presentation:**

You can now answer:

> **"Where do fuel costs come from?"**
> → `backup_boiler_config.py` - market averages (EIA data), updatable with vendor quotes

> **"Where do capacity limits come from?"**
> → System design (svar dictionary) - you size based on peak load and storage

> **"Where do CFE constraints come from?"**
> → State regulations (CA: 95%) or corporate PPAs (Google: 95%)

> **"Where does regional fuel availability come from?"**
> → Site assessment - check NG pipeline maps, Alaska has no NG access

---

## **Contact Info for Real Data**

If you need actual prices instead of defaults:

**Natural Gas:**
- Contact: Local gas utility
- Ask for: "Commercial/industrial rate for firm capacity"
- Typical: $4-8/MMBtu

**Propane:**
- Contact: Local propane supplier (Ferrellgas, AmeriGas, etc.)
- Ask for: "Delivered price for 200,000 gallons"
- Typical: $2-3/gallon

**Renewable Diesel:**
- Contact: Neste, World Energy, or Renewable Energy Group
- Ask for: "Bulk RD99 delivered price"
- Typical: $4-5/gallon

---

**All parameter sources are now documented and ready to use!** 🎯
