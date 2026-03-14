# Golf Launch Monitor Analytics

A lightweight web app that parses CSV exports from a Square golf launch monitor, stores shot data persistently, and generates Club Matrix and Wedge Matrix reports with configurable percentile statistics.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## Importing Data

1. Navigate to **Import** (`/import`)
2. Click **Choose File** and select a CSV export from your Square launch monitor
3. Preview the parsed shots, then click **Save** to store them

CSV files follow this format (the app reads the header row for session date and location):

```
Dates,03-12-2026,Place,Driving Ranges
Club,Index,Ball Speed(mph),Launch Direction,...,Carry(yd),Total(yd),...
Driver,0,152.3,R2.1,...,215.0,245.0,...
```

## Features

### Club Matrix (`/club-matrix`)

Full bag distance summary: **Club | Carry | Total | Max** for every club in your data, ordered by standard loft (Driver through LW). Values are calculated using the selected percentile (default P75).

### Wedge Matrix (`/wedge-matrix`)

Swing size breakdown for AW, SW, and LW only (PW excluded). Shows carry distances by swing size:

| Swing Size | Type | Display |
|------------|------|---------|
| 4/4, 3/4, 2/4, 1/4 | Fraction | Carry only |
| 10:2, 10:3, 9:3, 8:4 | Clock position | Carry + Max |

### Shot Browser (`/shots`)

View all imported shots with filtering by session and club. Toggle individual shots as excluded so they don't affect percentile calculations.

### Sessions (`/sessions`)

Manage import sessions. View session details or delete entire sessions (and all associated shots).

### Analytics (`/analytics`)

Interactive charts: dispersion, spin vs carry, shot shape, and carry distribution.

### Print Views (`/print`)

Print-friendly versions of the club matrix, wedge matrix, and a pocket card combining both.

## Percentile Modes

Use the percentile dropdown on matrix pages to switch between modes:

| Mode | Use Case |
|------|----------|
| P50 (Median) | What you hit most often |
| P75 (Default) | Solid, repeatable distance |
| P80 | Slightly aspirational |
| P90 | Your best swings |
| P95/P99 | Near-max capability |

## Club Name Mapping

The app normalizes Square's club names automatically:

| Square Name | Short Name |
|-------------|------------|
| Driver | 1W |
| 3 Wood | 3W |
| 2 Hybrid | 2H |
| 3 Hybrid | 3H |
| 4-9 Iron | 4i-9i |
| P-Wedge | PW |
| G-Wedge | AW |
| S-Wedge | SW |
| L-Wedge | LW |

Note: G-Wedge maps to AW (gap = approach wedge).

## Excluding Bad Shots

- On the **Shots** page, click the exclude toggle on any row to remove it from calculations
- On the **Analytics** page, use the auto-flag feature to mark shots outside the P10-P90 range as errant

Excluded shots remain in the database but are filtered out of all percentile math, matrices, and charts.

## Loft Analysis

The app compares each shot's dynamic loft against the club's standard loft. A "good" shot has dynamic loft at or below standard (indicating compression). This data appears in the analytics views.

## Data Storage

All data is stored in `golf_analytics.db` (SQLite), created automatically on first run in the project directory. Delete this file to start fresh.

## Project Structure

```
app.py                  Flask application and routes
config.py               Configuration (DB path, upload limits, default percentile)
models/
  database.py           SQLAlchemy models: Session, Shot, ClubLoft
  seed.py               Standard loft reference data (14 clubs)
services/
  analytics.py          Percentile math, errant flagging, chart data
  club_matrix.py        Club matrix builder
  wedge_matrix.py       Wedge matrix builder
  csv_parser.py         CSV parsing and club name normalization
  loft_analysis.py      Dynamic loft vs standard loft analysis
templates/              Jinja2 HTML templates (Bootstrap 5)
static/                 CSS and JavaScript (Chart.js)
tests/                  pytest test suite (79 tests)
```

## Running Tests

```bash
python -m pytest tests/ -v
```
