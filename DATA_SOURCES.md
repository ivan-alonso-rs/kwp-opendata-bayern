# Data sources, licences and attribution

Raw data are **not stored in this repository**. They are downloaded by
`scripts/01_download.py` (milestone M1) into `data/raw/` and recorded with
download date and checksum.

Exact URLs, licences and attribution keys live in **`config/sources.yaml`**
(single source of truth, read by the script). Licences were checked on each
product page on 2026-11-23; `data/raw/manifest.json` records per file the URL,
download time (UTC), size, SHA-256 and licence.

| Dataset | Provider | Used for | Licence | Download unit | Size (2026-11-23) |
|---|---|---|---|---|---|
| 3D building models LoD2 (CityGML, 2 km tiles) | LDBV | footprints, heights, building function | CC BY 4.0 | metalink per municipality `…/lod2/citygml/meta/metalink/{AGS}.meta4`, SHA-256 per tile | Bubenreuth 6 tiles / 220 MB; Hemhofen 6 tiles / 90 MB |
| ALKIS Verwaltungsgebiete | LDBV | municipal boundaries, AGS check | CC BY 4.0 | all Bavaria, `alkis-verwaltung.zip` | 63 MB |
| ALKIS Tatsächliche Nutzung | LDBV | land use, settlement areas | CC BY 4.0 | per district, `tn_{Kreisschlüssel}.zip` (Shape) | < 100 MB |
| ATKIS Basis-DLM plus (GeoPackage) | LDBV | street network (from M5, optional `--with-dlm`) | CC BY 4.0 | all Bavaria only | 1.9 GB |
| Zensus 2022 – 100 m grid: population, construction year (Mikrozensus classes), building type, dwellings per building, energy carrier, heating type, floor area per dwelling | Statistische Ämter des Bundes und der Länder | building age, type and heating distribution | dl-de/by-2-0 | whole Germany per table (Destatis `static/DE/zensus/gitterdaten/`) | not published by server |

Product pages: [LoD2](https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=lod2) ·
[Verwaltungsgebiete](https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=verwaltung) ·
[Tatsächliche Nutzung](https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=tatsaechlichenutzung) ·
[Basis-DLM](https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=atkis_basis_dlm) ·
[Zensus 2022 Gitterdaten](https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Zensus2022/_publikationen.html)

**AGS** used for the downloads come from the LDBV LoD2 index
([gemeinde.kml](https://geodaten.bayern.de/odd/a/lod2/citygml/meta/kml/gemeinde.kml)):
Bubenreuth 09572119, Hemhofen 09572130. They are confirmed locally against ALKIS
Verwaltungsgebiete before `ags_verified` is set to `true`.

## Required attribution (used on all maps and derived datasets)

- `Geobasisdaten: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de (Daten verändert), Lizenz: CC BY 4.0`
- `Zensus 2022: Statistische Ämter des Bundes und der Länder, Datenlizenz Deutschland – Namensnennung – Version 2.0 (www.govdata.de/dl-de/by-2-0), Daten verändert`

## Reference documents (cited, not redistributed)

| Document | Used for |
|---|---|
| Kommunale Wärmeplanung Bubenreuth, Abschlussbericht (GP JOULE Consult, May 2025) | validation targets (`validation/targets_bubenreuth.yaml`) |
| Kommunale Wärmeplanung Hemhofen (Bayernwerk Netz / INEV, Feb 2026) | validation targets (`validation/targets_hemhofen.yaml`) |

Page numbers in `validation/` refer to the **PDF page** of the published document.
