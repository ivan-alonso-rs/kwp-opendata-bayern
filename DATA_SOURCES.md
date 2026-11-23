# Data sources, licences and attribution

Raw data are **not stored in this repository**. They are downloaded by
`scripts/01_download.py` (milestone M1) into `data/raw/` and recorded with
download date and checksum.

> Licence terms are defined per product by each provider. They are re-checked
> in M1 and the exact licence of each downloaded file is logged.

| Dataset | Provider | Used for | Licence | Product page |
|---|---|---|---|---|
| 3D building models LoD2 (CityGML) | Bayerische Vermessungsverwaltung (LDBV) | footprints, heights, building function | CC BY 4.0 (check per product) | https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=lod2 |
| ALKIS tatsächliche Nutzung | LDBV | land use, settlement areas | CC BY 4.0 (check per product) | https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=tatsaechlichenutzung |
| ATKIS Basis-DLM | LDBV | street network | CC BY 4.0 (check per product) | https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=atkis_basis_dlm |
| Verwaltungsgebiete | LDBV | municipal boundaries | CC BY 4.0 (check per product) | via https://geodaten.bayern.de/opengeodata/ |
| Zensus 2022 – 100 m grid (buildings, construction year, heating, energy carrier, floor area) | Statistische Ämter des Bundes und der Länder | building age and heating distribution | Datenlizenz Deutschland – Namensnennung – 2.0 (dl-de/by-2-0) | https://www.destatis.de (Zensus 2022 → Gitterdaten) |

## Required attribution (used on all maps and derived datasets)

- `Geobasisdaten: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de (Daten verändert), Lizenz: CC BY 4.0`
- `Zensus 2022: Statistische Ämter des Bundes und der Länder, Datenlizenz Deutschland – Namensnennung – Version 2.0 (www.govdata.de/dl-de/by-2-0), Daten verändert`

## Reference documents (cited, not redistributed)

| Document | Used for |
|---|---|
| Kommunale Wärmeplanung Bubenreuth, Abschlussbericht (GP JOULE Consult, May 2025) | validation targets (`validation/targets_bubenreuth.yaml`) |
| Kommunale Wärmeplanung Hemhofen (Bayernwerk Netz / INEV, Feb 2026) | validation targets (`validation/targets_hemhofen.yaml`) |

Page numbers in `validation/` refer to the **PDF page** of the published document.
