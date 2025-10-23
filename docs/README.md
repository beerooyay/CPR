# CPR v2.0 — Commissioner's Power Rankings

**A groundbreaking sports analytics framework combining game theory, economics, information theory, and stochastic processes.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What is CPR?

CPR v2.0 is a novel fantasy basketball ranking system that uses:
- **Game Theory** (Shapley values for fair attribution)
- **Economics** (HHI for roster balance, Gini for parity)
- **Information Theory** (Entropy for consistency)
- **Stochastic Processes** (Markov chains for injury prediction)

### The CPR Equation
```
CPR = (0.40×SLI + 0.20×BSI + 0.15×Ingram + 0.15×Alvarado + 0.10×Zion) × SoS
```

**Components:**
- **SLI** (Starting Lineup Index) — Top 9 players' NIV
- **BSI** (Bench Strength Index) — Bench depth
- **Ingram Index** — Positional balance via HHI
- **Alvarado Index** — Value per dollar
- **Zion Index** — Health + injury prediction

---

## Quick Start

### Installation
```bash
git clone https://github.com/yourusername/cpr-v2.git
cd cpr-v2
pip install -r requirements.txt
```

### Run CPR
```bash
python scripts/run_cpr.py
```

### Query Database
```python
from src.db_utils import get_team_rankings

rankings = get_team_rankings(2025)
for team in rankings:
 print(f"{team['rank']}. {team['team_name']}: {team['cpr_score']:.3f}")
```

---

## Features

### Active Components
- [x] NIV (Normalized Impact Value) with health adjustment
- [x] SMI (Systemic Momentum Index) - NOVEL metric
- [x] HHI-based positional balance (Ingram Index)
- [x] Salary efficiency (Alvarado Index)
- [x] Health tracking (Zion Index)
- [x] League parity (Gini coefficient)
- [x] SQLite database with full history
- [x] Fantasy scoring system (machine precision)
- [x] 5-year historical data fetcher
- [x] Mobile app with AI chat

### In Development
- [ ] Game-by-game entropy calculation (coded, not activated)
- [ ] Shapley value computation (foundation laid)
- [ ] Automated daily updates via GitHub Actions
- [ ] Email reports

---

## Project Structure

```
CPR/
 src/
 cpr_engine.py # Core CPR calculation
 db_utils.py # Database utilities
 data_fetcher.py # ESPN/NBA API integration
 alvarado_variants.py # Alvarado Index options
 data/
 cpr_data.db # SQLite database
 raw/ # Raw CSV imports
 config/
 settings.yaml # Configuration
 alvarado_mode.yaml # Alvarado Index mode selection
 scripts/
 run_cpr.py # Main runner
 daily_update.sh # Daily automation
 send_report.py # Email reports
 docs/
 DATABASE_GUIDE.md # Database schema
 BREAKTHROUGH.md # Research notes
 API.md # API documentation
 tests/
 test_cpr.py # Unit tests
 .github/
 workflows/
 daily_update.yml # Daily data pull
 weekly_report.yml # Monday CPR report
 requirements.txt
 README.md
```

---

## Configuration

### Alvarado Index Modes

Edit `config/alvarado_mode.yaml`:

```yaml
mode: "hybrid" # Options: "salary", "performance", "hybrid"

# Option A: Salary-based
# AI = shapley_value / (salary / league_avg_salary)²

# Option B: Performance-based
# AI = shapley_value / (NIV / league_avg_NIV)²

# Option C: Hybrid (recommended)
# AI = shapley_value / [(NIV_z + salary_z) / 2]²
```

### Email Reports

Edit `config/settings.yaml`:

```yaml
email:
 recipient: "ezialb777@gmail.com"
 schedule: "Monday 9:00 AM"
 on_demand: true
```

---

## Automation

### Daily Updates (GitHub Actions)
Runs every day at 6 AM EST:
- Pulls latest NBA stats
- Updates ESPN fantasy scores
- Recalculates NIV
- Saves to database

### Weekly Reports (GitHub Actions)
Runs every Monday at 9 AM EST:
- Calculates full CPR
- Generates rankings
- Sends email to ezialb777@gmail.com

### On-Demand Reports
```bash
python scripts/send_report.py --email ezialb777@gmail.com
```

---

## What Makes This Novel?

1. **Health-adjusted NIV** — `NIV = NIV_raw × (health × consistency)`
2. **HHI for roster construction** — First application to positional balance
3. **Unified framework** — 5 indices with theoretical grounding
4. **Modular architecture** — Easy to swap components

**Novelty Score: 60% active, 100% potential**

---

## Results (Season 6)

| Rank | Team | CPR | SLI_z | BSI_z | Ing_z | Alv_z | Zio_z |
|------|------|-----|-------|-------|-------|-------|-------|
| 1 | Normal Normals | 1.275 | 1.731 | 0.706 | 2.507 | 0.452 | 0.280 |
| 2 | Albuquerque Blue Rocks | 1.086 | 0.628 | 1.482 | 1.048 | 2.271 | 0.453 |
| 3 | Kingston Captains | 0.376 | 1.229 | -0.456 | -0.272 | -0.416 | 0.862 |

**Key Insights:**
- Albuquerque has best value efficiency (Alv_z = 2.271)
- Normal Normals has best positional balance (Ing_z = 2.507)
- Kingston is overpaying for talent (Alv_z = -0.416)

---

## Web App

**Mobile-optimized web interface with AI-powered league assistant.**

### Features:
- CPR Rankings with expandable metrics
- Player Analytics (NIV scores)
- AI Chat Assistant (trash-talking, research-capable)
- Liquid glass design (NBA blue + professional UI)
- Works on ANY device (phone, tablet, desktop)
- Real-time data from Flask API

### Usage:

**IMPORTANT: You must start the Flask API server before using the web app!**

```bash
# Step 1: Start the Flask API server (required!)
source venv/bin/activate
python3 web_server.py

# Step 2: In another terminal, open the web app
open web/index.html

# Or serve with Python (in another terminal):
cd web
python3 -m http.server 8000
# Visit http://localhost:8000
```

The web app connects to the Flask API at `http://localhost:5001` to fetch live CPR data.

### Screens:
1. **CPR** - Live rankings, league stats, Alvarado mode toggle
2. **NIV** - Team rosters, player stats, fantasy points
3. **CHAT** - AI assistant powered by Cogito-v2 (405B)

**See web/README.md for deployment instructions.**

---

## Documentation

- [Database Guide](DATABASE_STRUCTURE.md) — Schema and queries
- [Setup Guide](SETUP.md) — Installation instructions
- [Automation Guide](AUTOMATION_GUIDE.md) — GitHub Actions
- [SMI Metric](SMI_NOVEL_METRIC.md) — Novel systemic momentum index
- [Leif Commands](LEIF_COMMANDS_COMPLETE.md) — Implementation details
- [Web App](web/README.md) — Mobile-optimized interface

---

## Contributing

This is a research project. If you want to contribute:
1. Fork the repo
2. Create a feature branch
3. Submit a PR with tests

---

## License

MIT License — See LICENSE file

---

## CURRENT STRUCTURE (Clean)

```
CPR/
├── .github/
│   └── workflows/
│       ├── daily_update.yml
│       └── weekly_report.yml
│
├── config/
│   ├── alvarado_mode.yaml
│   └── settings.yaml
│
├── data/
│   ├── cpr_data.db
│   └── raw/
│       └── current_stats.csv
│
├── reports/
│   (generated reports go here)
│
├── scripts/
│   ├── daily_update.py
│   ├── initialize_system.py
│   ├── run_cpr.py
│   └── send_report.py
│
├── src/
│   ├── alvarado_variants.py
│   ├── cpr_engine.py
│   ├── db_saver.py
│   ├── db_schema_update.py
│   ├── db_utils.py
│   ├── entropy_calculator.py
│   ├── historical_fetcher.py
│   ├── nba_api_fetcher.py
│   ├── scoring_system.py
│   ├── sportradar_fetcher.py
│   └── teammate_chemistry.py
│
├── .gitignore
├── AUTOMATION_GUIDE.md
├── DATABASE_STRUCTURE.md
├── LEIF_COMMANDS_COMPLETE.md
├── LICENSE
├── README.md
├── RECOMMENDATION.md
├── SETUP.md
├── SMI_NOVEL_METRIC.md
└── requirements.txt
