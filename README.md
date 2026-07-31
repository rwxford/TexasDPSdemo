# TexasDPSdemo — Statewide Criminal Activity Tracking System (CATS)

A **demonstration** application that tracks criminal activity across Texas that falls
under the **Texas Department of Public Safety (DPS)** purview. It models how incidents,
offenders, and arrests are recorded, investigated, and reported across DPS divisions and
Texas counties, using the same offense taxonomy Texas uses for state crime reporting.

> ⚠️ **Demo / synthetic data only.** Every person, incident, and record in this project is
> fictional and randomly generated for demonstration purposes. This is **not** a real law
> enforcement system and contains **no** real criminal justice information (CJI/CHRI).

---

## What it models

Texas DPS is responsible for public safety and law enforcement across the state — highway
patrol, criminal investigations, driver licensing, emergency management, and homeland
security — operating through more than a dozen divisions such as the Texas Highway Patrol,
Texas Rangers, Criminal Investigations Division, and Intelligence & Counterterrorism.
This demo focuses on the **criminal activity** side of that mission.

### Data taxonomy (public references)

Texas reports crime through the **National Incident-Based Reporting System (NIBRS)**, which
classifies every offense into one of three categories:

- **Crimes Against Persons** — e.g. Murder, Assault, Kidnapping, Sex Offenses, Human Trafficking
- **Crimes Against Property** — e.g. Robbery, Burglary, Theft, Motor Vehicle Theft, Arson, Fraud
- **Crimes Against Society** — e.g. Drug/Narcotic Violations, Weapon Law Violations, Gambling, Prostitution

Offenses are further split into **Group A** (full incident report: incident + arrest data) and
**Group B** (arrest data only). Offense codes in this demo mirror the NIBRS/Texas UCR codes
(e.g. `09A` Murder, `13A` Aggravated Assault, `240` Motor Vehicle Theft, `35A` Drug Violations).

### DPS divisions represented

- Texas Rangers (major/violent crime, unsolved & serial crime, public corruption, officer-involved shootings)
- Texas Highway Patrol
- Criminal Investigations Division (CID)
- CID — Narcotics
- Intelligence & Counterterrorism Division (ICT)
- Crime Laboratory Division

## Data model

| Entity | Purpose |
| --- | --- |
| `incidents` | A reported criminal incident: NIBRS offense code/category/group, status, dates, county, city, agency, assigned DPS division, narrative |
| `offenders` | Persons linked to an incident: name, DOB, demographics, State ID (SID), status |
| `arrests` | Arrest events linking an offender to an incident: date, arrest type, arresting agency |

Reference data (NIBRS offense catalog, DPS divisions, Texas counties, incident statuses) is
seeded automatically so the taxonomy is consistent.

## Features

- **Dashboard** — totals by NIBRS category, by status, and by DPS division
- **Incidents** — searchable/filterable list (category, status, division, county) with detail view
- **Offenders & arrests** — linked to each incident
- **Create incident** — simple form that enforces the NIBRS offense taxonomy
- **JSON API** — everything the UI uses is available under `/api/...`

## Running the demo

Requires **Python 3.9+**. No third-party packages, no build step.

```bash
python3 app.py
```

Then open <http://localhost:8000>. On first run the app creates `cats.db` (SQLite) and
seeds it with reference data and ~40 synthetic incidents. To reset, delete `cats.db` and
restart. To use a different port: `PORT=9000 python3 app.py`.

## API quick reference

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/stats` | Dashboard aggregates |
| GET | `/api/incidents` | List incidents (filters: `category`, `status`, `division`, `county`, `q`) |
| GET | `/api/incidents/<id>` | Incident detail incl. offenders & arrests |
| POST | `/api/incidents` | Create an incident |
| GET | `/api/reference` | Offense catalog, divisions, counties, statuses |

## Public references

- Texas DPS — Criminal Investigations & Texas Rangers responsibilities (dps.texas.gov)
- Texas DPS Uniform Crime Reporting — NIBRS offense categories & codes (dps.texas.gov/ucr)
- FBI UCR/NIBRS — Crimes Against Persons, Property, and Society (ucr.fbi.gov/nibrs)

## Disclaimer

Built as a technical demonstration. Not affiliated with or endorsed by the Texas Department
of Public Safety. All data is synthetic. Do not load real criminal justice information into
this application.
