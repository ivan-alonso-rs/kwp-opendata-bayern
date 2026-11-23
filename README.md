# kwp-opendata-bayern

**Reproducible open-data GIS workflow for municipal heat planning (*kommunale Wärmeplanung*) in Bavaria.**

> Status: 🚧 **M0 – project setup** (see [roadmap](docs/roadmap.md)). Nothing here is a finished result yet.

---

## What this project does

German municipalities must produce a municipal heat plan under the federal
*Wärmeplanungsgesetz* (WPG), implemented in Bavaria by the *AVEn*. At its core,
every plan needs the same GIS analysis: *where is heat needed, how dense is that
demand, and which streets could support a heating network?*

This repository rebuilds that GIS core **using only open data** and documents every
formula and assumption, so that the results can be checked, reproduced and reused
for any Bavarian municipality:

```
LoD2 3D buildings + ALKIS land use + Zensus 2022 grid
        │
        ▼
heated buildings (PostGIS)  ──►  heat demand per building, with uncertainty (Monte Carlo)
        │
        ▼
heat density per block (MWh/ha·a) and per street (MWh/m·a)  ──►  suitability map
        │
        ▼
validation against published municipal heat plans
```

**Case studies** (Landkreis Erlangen-Höchstadt):

| Role | Municipality | Why |
|---|---|---|
| Main case | Bubenreuth | Small municipality (~4,500 inhabitants), published heat plan 2025 |
| Validation | Hemhofen | Published plan (2026) with LoD2-based method and street-level values to compare against |

The same code runs for both via `--gemeinde <name>`; that is the point.

## What this project is *not*

- **Not an official heat plan** and not a substitute for one. Results are an
  independent methodological exercise.
- **No personal data.** Chimney-sweep registers (*Kehrbuch*), metered consumption or
  any other personal data are never used or stored here.
- **No redistribution of third-party documents.** Published heat plans are cited
  (with page numbers) but not included.

## Quickstart (Windows)

Requirements: [Miniconda/Anaconda](https://docs.conda.io), PostgreSQL ≥ 16 with PostGIS ≥ 3.4, Git.

```bash
git clone https://github.com/ivan-alonso-rs/kwp-opendata-bayern.git
cd kwp-opendata-bayern
conda env create -f environment.yml        # creates the "kwp" environment
conda activate kwp
copy .env.example .env                      # then edit .env with your PostGIS password
python scripts/00_check_setup.py --gemeinde bubenreuth
```

`00_check_setup.py` verifies Python, GDAL (incl. the GML/CityGML driver), PROJ and the
PostGIS connection, and loads the municipality configuration.

## Repository structure

```
config/          one YAML per municipality + shared defaults
validation/      figures from published plans (with page refs) and tolerances
src/kwp/         reusable Python package (config, database, analysis modules)
scripts/         numbered pipeline steps (00_, 01_, ...)
data/            local only – raw / interim / processed (git-ignored)
docs/            roadmap, method documentation, development log
```

## Data sources and attribution

See [DATA_SOURCES.md](DATA_SOURCES.md). Raw data are **downloaded by script, not
redistributed**. Derived results carry the attribution required by each licence
(CC BY 4.0 for Bavarian surveying open data, dl-de/by-2-0 for Zensus 2022).

## Authorship and AI assistance

**Author and maintainer: Ivan Alonso** – project idea, method decisions, execution on
real data, validation and interpretation (≈ 70 %).

**AI assistance: Claude (Anthropic)** – code drafts, reviews and documentation
drafts (≈ 30 %). Commits where AI-drafted code was used carry a
`Co-Authored-By: Claude` trailer. Every line was reviewed and run by the author.
Details in [AUTHORS.md](AUTHORS.md).

## License

- Code: **GNU AGPL-3.0** ([LICENSE](LICENSE))
- Documentation, figures and maps: **CC BY 4.0** ([LICENSE-docs.txt](LICENSE-docs.txt))
- Third-party data keep their own licences ([DATA_SOURCES.md](DATA_SOURCES.md)).

## How to cite

See [CITATION.cff](CITATION.cff) (GitHub shows a "Cite this repository" button).

---

## Kurzfassung (Deutsch)

**Reproduzierbarer Open-Data-GIS-Workflow für die kommunale Wärmeplanung in Bayern.**
Aus LoD2-Gebäudemodellen, ALKIS und dem Zensus 2022 werden der Wärmebedarf je Gebäude
(mit Unsicherheitsbandbreite), die Wärmedichte je Baublock und die Wärmeliniendichte je
Straßenabschnitt berechnet und mit veröffentlichten Wärmeplänen (Bubenreuth, Hemhofen)
verglichen. Alle Formeln und Annahmen sind dokumentiert.

**Hinweis:** Dies ist **kein amtlicher Wärmeplan**, sondern eine unabhängige
methodische Fallstudie. Es werden ausschließlich offene Daten und keine
personenbezogenen Daten verwendet.
