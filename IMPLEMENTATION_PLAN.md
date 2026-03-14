# Golf Launch Monitor Analytics — Implementation Plan

## Problem Statement

Build a web application that ingests CSV data exported from a golf launch monitor, stores it persistently, and produces analytics — primarily a **Club Matrix** and **Wedge Matrix** that can be printed as pocket-sized reference cards. The app should emphasize percentile-based analysis over simple averages and provide dynamic loft assessment and rich shot analytics.

---

## Recommended Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Interpreted, excellent data ecosystem |
| **Web Framework** | Flask | Lightweight, well-understood, easy to maintain |
| **Database** | SQLite (via SQLAlchemy) | Portable, zero-config, persistent storage |
| **Data Processing** | Pandas / NumPy | Best-in-class for percentile calculations and CSV parsing |
| **Frontend** | HTML + Bootstrap 5 + Chart.js | Clean responsive UI, no build step, good print CSS support |
| **Print** | CSS `@media print` + dedicated pocket card view | Purpose-built print-friendly layout |

---

## Data Model

### Tables

#### `sessions`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| filename | TEXT | Original CSV filename |
| session_date | DATE | Date from CSV header (row 1) |
| location | TEXT | Place from CSV header (row 1) |
| data_type | TEXT | `"club"` or `"wedge"` — user-selected at import |
| imported_at | DATETIME | Timestamp of import |
| notes | TEXT | Optional user notes |

#### `shots`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| session_id | INTEGER FK | References sessions.id |
| club | TEXT | Raw club name from CSV (e.g., "5 Iron") |
| club_short | TEXT | Normalized short name (e.g., "5i") |
| club_index | INTEGER | Shot index within club group |
| swing_size | TEXT | One of 8 sizes for wedge data; `"full"` for club data |
| ball_speed | REAL | mph |
| launch_direction | TEXT | Raw direction string (e.g., "R8.5") |
| launch_direction_deg | REAL | Parsed numeric (positive=right, negative=left) |
| launch_angle | REAL | degrees |
| spin_rate | INTEGER | rpm |
| spin_axis | TEXT | Raw spin axis string |
| spin_axis_deg | REAL | Parsed numeric |
| back_spin | INTEGER | rpm |
| side_spin | INTEGER | rpm (signed: positive=right) |
| apex | REAL | yards |
| carry | REAL | yards |
| total | REAL | yards |
| offline | REAL | yards (signed: positive=right) |
| landing_angle | REAL | degrees |
| club_path | REAL | degrees (parsed from R/L prefix) |
| face_angle | REAL | degrees (parsed from R/L prefix) |
| attack_angle | REAL | degrees |
| dynamic_loft | REAL | degrees |
| excluded | BOOLEAN | User-toggled to exclude errant shots |

#### `club_lofts` (reference data, pre-seeded)
| Column | Type | Description |
|--------|------|-------------|
| club_short | TEXT PK | e.g., "5i" |
| standard_loft | REAL | Standard fixed loft angle in degrees |

### Club Name Mapping

| CSV Name | Short Name | Standard Loft |
|----------|-----------|---------------|
| Driver | 1W | 10.5° |
| 3 Wood | 3W | 15° |
| 2 Hybrid | 2H | 18° |
| 3 Hybrid | 3H | 21° |
| 4 Iron | 4i | 21° |
| 5 Iron | 5i | 24° |
| 6 Iron | 6i | 27° |
| 7 Iron | 7i | 31° |
| 8 Iron | 8i | 35° |
| 9 Iron | 9i | 39° |
| P-Wedge | PW | 44° |
| G-Wedge | AW | 50° |
| S-Wedge | SW | 56° |
| L-Wedge | LW | 60° |

> Note: Standard lofts are pre-seeded defaults. The user should be able to edit them to match their actual club specs.

---

## Swing Sizes

The 8 valid swing sizes for wedge data:

| Size | Type | Display Format in Wedge Matrix |
|------|------|-------------------------------|
| 4/4 | Fraction | Carry only |
| 3/4 | Fraction | Carry only |
| 2/4 | Fraction | Carry only |
| 1/4 | Fraction | Carry only |
| 10:2 | Clock-hand | Carry/Max |
| 10:3 | Clock-hand | Carry/Max |
| 9:3 | Clock-hand | Carry/Max |
| 8:4 | Clock-hand | Carry/Max |

Club data always uses swing size `"full"`.

---

## Core Features (by Priority)

### 1. CSV Import & Session Management
- Upload a CSV file via the web UI
- Auto-parse header row (Dates/Place) and shot data
- Skip summary/average/deviation rows during import (detect by blank Club or Club = "Average"/"Deviation")
- Prompt user: "Is this **club data** or **wedge data**?"
- For club data: all shots tagged `swing_size = "full"`
- For wedge data: present the shots grouped by club → user assigns swing size to **batches** of contiguous rows
  - UI shows shot rows in order; user selects a range and assigns a swing size
  - Pre-populate with intelligent grouping suggestions
- Parse directional values (L/R prefixes → signed floats)
- Store all parsed shots in the database

### 2. Club Matrix
- Columns: **Club | Carry | Total | Max**
- Rows: All clubs from Driver (1W) down to LW, ordered by standard loft
- **Carry**: Percentile-based value (default P75, configurable) of carry distances for non-excluded shots
- **Total**: Percentile-based value of total distances for non-excluded shots
- **Max**: Maximum total distance ever recorded for that club across included shots
- Scope: configurable to show data from **all sessions** or a **single session**
- Round values to nearest whole yard

### 3. Wedge Matrix
- Columns: **Swing Size | AW | SW | LW**
- Rows: The 8 swing sizes (4/4, 3/4, 2/4, 1/4, 10:2, 10:3, 9:3, 8:4)
- Fraction sizes (4/4, 3/4, 2/4, 1/4): Cell shows **Carry** only (percentile-based, rounded)
- Clock-hand sizes (10:2, 10:3, 9:3, 8:4): Cell shows **Carry/Max** (e.g., "47/52")
  - Carry = percentile, Max = maximum carry for that club+swing combo
- Empty cell if no data exists for a club+swing combination
- Scope: configurable (all sessions or single session)

### 4. Pocket Card Print View
- Dedicated print-optimized views for Club Matrix and Wedge Matrix
- CSS `@media print` styling for wallet/pocket card size (~3.5" × 2" or ~85mm × 55mm)
- Clean, high-contrast table with no UI chrome
- Option to print both matrices on one card (front/back) or separately
- Print button triggers browser print dialog

### 5. Shot Data Management
- View all shots, filterable by session, club, swing size
- Toggle individual shots as **excluded** (errant shot)
- Percentile-based filtering: configurable threshold (default: exclude shots below P10 and above P90 based on carry distance)
  - Auto-flag errant shots based on threshold, but user has final say
- Batch operations: exclude/include multiple rows

### 6. Dynamic Loft Analysis
- Compare each shot's Dynamic Loft to the club's standard (fixed) loft angle
- Good shot: dynamic loft ≤ standard loft (indicates proper compression)
- Bad shot: dynamic loft > standard loft (indicates scooping/flipping)
- Visual indicator per shot (green/red or ✓/✗)
- Summary stats: % of shots with good dynamic loft, per club

### 7. Analytics Dashboard
Interpret and visualize key launch monitor metrics:

| Metric | What It Tells You | Good Range (general) |
|--------|-------------------|---------------------|
| **Spin Rate** | Ball control & stopping power | Varies by club — irons: 4000–7000, woods: 2000–3000 |
| **Offline** | Accuracy — how far left/right of target | Closer to 0 is better |
| **Landing Angle** | How steeply the ball descends | 45°+ for irons = good stopping power |
| **Launch Angle** | Initial ball trajectory | Club-dependent; driver ~12-15°, irons higher |
| **Ball Speed** | Energy transfer efficiency | Higher is better for given club |
| **Apex** | Max height of ball flight | Context-dependent |
| **Attack Angle** | Club head path at impact | Negative for irons (downward), positive for driver |
| **Face Angle / Club Path** | Determines shot shape (draw/fade/slice/hook) | Small difference = straight; path > face = draw |
| **Spin Axis** | Tilt of spin = curve direction | Closer to 0° = straighter |

Charts to include:
- **Carry distance distribution** per club (box plot or histogram)
- **Dispersion pattern** (Offline vs Carry scatter plot — bird's-eye view)
- **Spin rate vs carry** correlation
- **Dynamic loft trend** per club (are you improving?)
- **Shot shape analysis** (face angle - club path → draw/fade tendency)
- **Club comparison** (overlay multiple clubs)

### 8. Session Management
- List all imported sessions with date, location, data type, shot count
- View single session or aggregate across sessions
- Delete a session (cascades to shots)
- Re-assign swing sizes for wedge sessions

---

## Percentile Configuration

- Default: **P75** (represents your reliable "good shot" — filters out mishits naturally while not being as optimistic as P90)
- Configurable at runtime via a control in the UI (dropdown or slider: P50, P60, P70, P75, P80, P90)
- Changing the percentile recalculates matrices and analytics in real-time
- P75 rationale: In golf analytics, P75 captures your expected distance when you make solid contact. P50 (median) is too conservative; P90 too aspirational.

---

## Errant Shot Filtering

Two complementary approaches:
1. **Percentile-based auto-flagging**: Shots with carry distance outside the configurable range (e.g., P10–P90) are auto-flagged as errant but not excluded by default — the user reviews and confirms
2. **Manual exclusion**: Toggle any individual row to excluded/included
3. **Heuristic flags** (informational): Shots with anomalous metrics (e.g., carry < 50% of club's median, negative launch angle, extreme offline) are highlighted for review

---

## CSV Parsing Details

### Header Row
```
Dates,03-12-2026,Place,Driving Ranges
```
Parse: date = column 2, location = column 4.

### Shot Data Columns
```
Club,Index,Ball Speed(mph),Launch Direction,Launch Angle,Spin Rate,Spin Axis,Back Spin,Side Spin,Apex(yd),Carry(yd),Total(yd),Offline(yd),Landing Angle,Club Path,Face Angle,Attack Angle, Dynamic Loft
```

### Rows to Skip
- Blank rows (row 2 in samples)
- Rows where Club is empty and Index is "Average" or "Deviation"
- These are the per-club summary rows generated by the launch monitor

### Direction Parsing
Values like `R8.5`, `L3.2`, `R0.0`, `L0.0`:
- `R` prefix → positive value
- `L` prefix → negative value
- Plain numeric → as-is
- Handle edge case: `0.0` with no prefix

---

## Project Structure

```
wedgeMatrix/
├── app.py                     # Flask application entry point
├── config.py                  # Configuration (DB path, defaults)
├── requirements.txt           # Python dependencies
├── models/
│   ├── __init__.py
│   ├── database.py            # SQLAlchemy setup, table definitions
│   └── seed.py                # Seed club lofts reference data
├── services/
│   ├── __init__.py
│   ├── csv_parser.py          # CSV import & parsing logic
│   ├── analytics.py           # Percentile calculations, stats
│   ├── club_matrix.py         # Club matrix generation
│   ├── wedge_matrix.py        # Wedge matrix generation
│   └── loft_analysis.py       # Dynamic loft comparison
├── static/
│   ├── css/
│   │   ├── style.css          # Main styles
│   │   └── print.css          # Print-specific styles for pocket cards
│   └── js/
│       ├── app.js             # Main client-side logic
│       ├── charts.js          # Chart.js visualizations
│       └── import.js          # CSV import & swing size tagging UI
├── templates/
│   ├── base.html              # Base layout with nav
│   ├── dashboard.html         # Analytics dashboard
│   ├── import.html            # CSV import page
│   ├── sessions.html          # Session list
│   ├── shots.html             # Shot data viewer with exclusion toggles
│   ├── club_matrix.html       # Club matrix view
│   ├── wedge_matrix.html      # Wedge matrix view
│   └── print_card.html        # Pocket card print layout
└── tests/
    ├── test_csv_parser.py     # CSV parsing tests
    ├── test_analytics.py      # Percentile & stats tests
    ├── test_club_matrix.py    # Club matrix output tests
    └── test_wedge_matrix.py   # Wedge matrix output tests
```

---

## Implementation Todos

### Phase 1: Foundation
1. **project-setup** — Initialize Python project, install dependencies (Flask, SQLAlchemy, Pandas, NumPy), create folder structure, `requirements.txt`
2. **data-model** — Define SQLAlchemy models (sessions, shots, club_lofts), create migration/init script, seed club loft reference data
3. **csv-parser** — Build CSV parser: read header, parse shot rows, skip summaries, handle L/R direction parsing, club name normalization

### Phase 2: Core Matrices
4. **import-ui** — Build CSV upload page: file upload, club/wedge selection, swing size batch-tagging for wedge data
5. **club-matrix** — Implement club matrix: percentile Carry/Total, Max total, all-sessions vs single-session scope, configurable percentile
6. **wedge-matrix** — Implement wedge matrix: percentile Carry for fractions, Carry/Max for clock-hands, configurable percentile

### Phase 3: Print & Filtering
7. **pocket-card** — Create pocket card print view with dedicated CSS for wallet-sized output
8. **shot-management** — Shot data viewer with exclusion toggles, percentile-based errant auto-flagging, manual exclude/include

### Phase 4: Analytics
9. **loft-analysis** — Dynamic loft vs standard loft comparison, good/bad indicators, per-club summary
10. **analytics-dashboard** — Charts: carry distribution, dispersion pattern, spin analysis, shot shape, club comparison
11. **session-management** — Session list, single/multi-session views, delete, re-assign swing sizes

### Phase 5: Polish
12. **percentile-config** — Runtime percentile selector affecting all views
13. **testing** — Unit tests for CSV parser, analytics, matrix generation
14. **ux-polish** — Responsive layout, error handling, loading states, validation

---

## Open Questions / Assumptions

1. **Loft angles are editable** — Defaulting to standard lofts but user can customize to match their actual club specs
2. **"Anywhere Wedge" = Gap Wedge** — CSV "G-Wedge" maps to "AW" in the wedge matrix per user's requirement
3. **Wedge matrix only shows AW, SW, LW** — PW is NOT included in the wedge matrix (only in club matrix)
4. **Pocket card size** — Targeting standard business card / wallet card dimensions (~3.5" × 2")
5. **Single user** — No authentication; single-user local web app
6. **Browser** — App runs locally via `python app.py` and opens in the browser
