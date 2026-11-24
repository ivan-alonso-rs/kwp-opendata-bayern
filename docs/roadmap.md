# Roadmap

Each milestone ends with a concrete, checkable result and a development-log entry
(`docs/devlog/`). A milestone is only "done" when its check passes on the author's machine.

| # | Milestone | Deliverable | Learning goal | Done when |
|---|---|---|---|---|
| M0 | Project setup | repo structure, `environment.yml`, configs, `00_check_setup.py` | Git, reproducible environments | `00_check_setup.py` passes all checks |
| M1 | Data acquisition | `01_download.py` for LoD2, ALKIS, boundaries, Zensus 2022 (Basis-DLM optional, needed from M5); `manifest.json` | open data, licences, metadata, checksums | files downloaded with SHA-256, `tests/` green, AGS verified against ALKIS Verwaltungsgebiete |
| M2 | Load & clean in PostGIS | CityGML → PostGIS, building function codes, heated buildings | CityGML, spatial SQL | residential building count within ±2 % of Zensus 2022 |
| M3 | Heat demand | heated volume → floor area → specific demand; Zensus assignment; Monte Carlo P10–P90 | building-stock modelling, uncertainty | demand per building and per block with ranges |
| M4 | Validation | comparison against `validation/targets_*.yaml` | model validation | validation report with pass/fail per target |
| M5 | Densities & suitability | MWh/ha·a per block, MWh/m·a per street segment, suitability score | network analysis | Hemhofen street-level values reproduced within tolerance |
| M6 | Maps & report | map atlas, tables, static web map | cartography, communication | PDF atlas + HTML map |
| M7 | Release | v1.0, Zenodo DOI, write-up (EN/DE) | open publication | DOI issued, repository public |
