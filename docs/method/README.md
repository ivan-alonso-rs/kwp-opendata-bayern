# Method (living document)

This document is filled in milestone by milestone. Every formula states its
source and every assumption states why it was chosen. Status markers:
✅ implemented · 🚧 in progress · 📝 planned.

## 1. Heated buildings 📝 (M2)
Selection of heated buildings from LoD2 via the ALKIS building-function code.
The mapping table (function code → heated yes/no, residential/non-residential)
is a documented human decision, stored in `config/`.

## 2. Heated volume and floor area 📝 (M3)
- Heated volume `V_e` = footprint area (ALKIS-exact LoD2 footprint) × heated height.
- Usable floor area for residential buildings: `A_N = 0.32 m⁻¹ · V_e`, the
  convention of the German energy-saving ordinance (EnEV, Anlage 1 Nr. 1.3.3),
  valid for average storey heights between 2.5 m and 3 m.
- Assumptions on unheated roof and basement volume are documented here when set.

## 3. Specific heat demand 📝 (M3)
Specific demand (kWh/m²·a) by building type and construction period from a
documented typology (candidate sources: federal *Technikkatalog Wärmeplanung*,
IWU/TABULA German building typology). Chosen source and values will be listed
with version and table reference.

## 4. Assigning Zensus 2022 attributes 📝 (M3)
Zensus 2022 gives distributions per 100 m grid cell (e.g. number of buildings
by construction period), not values per building. Attributes are therefore
assigned **probabilistically** and the resulting uncertainty is propagated with
a Monte Carlo simulation. Results are reported per block/street, not per building.

## 5. Heat density 📝 (M5)
- Area density: Σ demand of buildings in a block / block area (MWh/ha·a).
- Line density: Σ demand of buildings assigned to a street segment / segment
  length (MWh/m·a), with connection rates of 100 % and 60 % (as in the Hemhofen plan).

## 6. Validation 📝 (M4)
Comparison with published figures in `validation/targets_*.yaml`; each target
has a page reference and a tolerance with justification.
