# CPR v2.0 Setup Guide

## Quick Start: The Serverless Way

This guide assumes you have the Firebase CLI installed and configured.

### 1. Install Frontend & Backend Dependencies

```bash
# Install backend Node.js dependencies
cd functions
npm install
cd ..

# Install python dependencies for the data pipeline
pip install -r requirements.txt
```

### 2. Configure Firebase & API Keys

- **Project ID**: Make sure your `.firebaserc` file points to your correct Firebase project (`cpr-app-54c15`).
- **OpenRouter API Key**: Securely set your OpenRouter API key in the Firebase environment:
  ```bash
  firebase functions:config:set openrouter.api_key="YOUR_API_KEY"
  ```

### 3. Deploy the App & Backend

```bash
# Deploy the backend Cloud Functions and the frontend web app
firebase deploy
```

### 4. Run the Automated Data Pipeline

The Python ETL pipeline is designed to be run as an automated, containerized job (e.g., on Google Cloud Run). To run it manually:

```bash
# This master script fetches data, calculates all metrics, and saves to Firestore.
python scripts/master_pipeline.py
```

---

## GitHub Actions Setup

### Prerequisites
1. Push this repo to GitHub
2. Add secrets to your repository:
 - `ESPN_API_KEY` (if using ESPN API)
 - `SENDGRID_API_KEY` (for email reports)

### Workflows

**Daily Update** (`.github/workflows/daily_update.yml`)
- Runs every day at 6 AM EST
- Pulls latest NBA stats
- Updates database

**Weekly Report** (`.github/workflows/weekly_report.yml`)
- Runs every Monday at 9 AM EST
- Calculates CPR
- Sends email report

### Manual Trigger
You can manually trigger workflows from GitHub Actions tab:
1. Go to Actions
2. Select workflow
3. Click "Run workflow"

---

## Email Setup

### Option A: SendGrid (Recommended)
1. Sign up at sendgrid.com
2. Get API key
3. Add to GitHub secrets as `SENDGRID_API_KEY`
4. Update `scripts/send_report.py` with SendGrid integration

### Option B: Gmail SMTP
1. Enable "Less secure app access" in Gmail
2. Use app-specific password
3. Update SMTP settings in `send_report.py`

### Option C: Local Testing
Reports are saved to `reports/` directory as HTML files

---

## Configuration Options

### CPR Weights (`config/settings.yaml`)
```yaml
cpr_weights:
 sli: 0.40 # Starting Lineup Index
 bsi: 0.20 # Bench Strength Index
 ingram: 0.15 # Positional Balance
 alvarado: 0.15 # Value Efficiency
 zion: 0.10 # Health Index
```

### Alvarado Index Mode (`config/alvarado_mode.yaml`)
```yaml
mode: "hybrid" # Options: salary, performance, hybrid
```

**Salary Mode:**
- Best for: Identifying undervalued contracts
- Formula: `AI = shapley / (salary/avg_salary)²`

**Performance Mode:**
- Best for: When salary data is unreliable
- Formula: `AI = shapley / (NIV/avg_NIV)²`

**Hybrid Mode (Recommended):**
- Best for: Comprehensive value assessment
- Formula: `AI = shapley / [(NIV_z + salary_z)/2]²`

---

## Database

The SQLite database (`data/cpr_data.db`) contains:
- Player stats by season
- Salary data
- Calculated metrics (NIV, Alvarado, etc.)
- Team rankings
- League metrics (Gini, LHI)

### Query Examples
```python
from src.db_utils import get_team_rankings, get_player_stats

# Get current rankings
rankings = get_team_rankings(2025)

# Get player stats
curry = get_player_stats("Stephen Curry", 2025)
```

---

## Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

---

## Project Structure

```
CPR/
 src/ # Source code
 cpr_engine.py # Core calculation
 db_utils.py # Database utilities
 alvarado_variants.py # Alvarado Index modes
 data_fetcher.py # ESPN/NBA API (TODO)
 data/
 cpr_data.db # SQLite database
 raw/ # Raw CSV files
 config/
 settings.yaml # Main configuration
 alvarado_mode.yaml # Alvarado mode selection
 scripts/
 run_cpr.py # Main runner
 send_report.py # Email reports
 docs/ # Documentation
 tests/ # Unit tests
 .github/workflows/ # GitHub Actions
```

---

## Troubleshooting

### Database locked
```bash
# Close all connections and try again
rm data/cpr_data.db-journal
```

### Missing dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Email not sending
- Check SendGrid API key
- Verify email address
- Check spam folder
- Review logs in GitHub Actions

---

## Updating Data

### Manual Update
```bash
# Add new stats CSV to data/raw/
cp new_stats.csv data/raw/current_stats.csv

# Run CPR
python scripts/run_cpr.py --save-to-db
```

### Automated Update (GitHub Actions)
Push changes to trigger daily workflow, or manually trigger from Actions tab.

---

## Next Steps

1. Set up GitHub repository
2. Configure secrets
3. Test workflows locally
4. Push to GitHub
5. Verify automated runs
6. Add ESPN API integration
7. Implement Shapley values
8. Add entropy calculations

---

## Tips

- **Backup database regularly:** `cp data/cpr_data.db data/cpr_data_backup.db`
- **Test locally first:** Run scripts manually before relying on automation
- **Monitor GitHub Actions:** Check logs if workflows fail
- **Update weights:** Adjust CPR weights based on backtesting results

---

**Questions?** Check the docs or open an issue on GitHub.
