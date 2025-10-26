# CPR-NFL — Commissioner's Parity Report (NFL)

**A novel, serverless NFL fantasy analytics framework combining game theory, economics, and information theory.**

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE)

---

## What is CPR?

CPR is a novel fantasy sports-agnostic ranking system that uses:
- **Game Theory** (Shapley values for fair attribution)
- **Economics** (HHI for roster balance, Gini for parity)
- **Information Theory** (Entropy for consistency)
- **Stochastic Processes** (Markov chains for injury prediction)
- **Machine Learning** (AI-powered analysis via Jaylen)

### The CPR Equation
```
CPR = (0.30×SLI + 0.25×BSI + 0.20×Ingram + 0.15×Alvarado + 0.10×Zion) × PositionFactor
```

**Components:**
- **SLI** (Strength of Lineup Index) — Top players' NIV scores
- **BSI** (Bench Strength Index) — Bench depth & roster balance
- **Ingram Index** — Player health and availability factors
- **Alvarado Index** — Performance consistency & reliability
- **Zion Index** — Explosive play potential & upside

### NIV (Normalized Impact Value)
NIV is our player-level metric that combines:
- **Recent Performance** (3-week weighted average)
- **Consistency** (Coefficient of variation)
- **Explosive Upside** (Ceiling performance)
- **Market Context** (League-wide benchmarks)
- **Health Factors** (Injury risk & status)

## The Architecture

This project is a 100% serverless, automated NFL fantasy analytics platform.

- **Frontend**: A static web app built with vanilla HTML/CSS/JS, hosted on Firebase Hosting
- **Backend**: A serverless API powered by Firebase Cloud Functions, providing secure access to the database
- **Database**: A Firestore database that serves as the live, scalable source of truth for the app
- **ETL Pipeline**: A Dockerized Python application, designed to be run as a scheduled job (e.g., Google Cloud Run), that automatically fetches data from the Sleeper API, calculates all CPR & NIV metrics, and saves them to Firestore
- **AI Agent**: "Jaylen" - An AI-powered fantasy analyst using OpenRouter's language models
- **MCP Integration**: Multi-Agent Communication Protocol servers for seamless tool integration

---

## Quick Start

See the [Setup Guide](docs/setup.md) for detailed installation and deployment instructions.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/beerooyay/CPR-NFL.git
   cd CPR-NFL
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   npm install  # For frontend dependencies
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Deploy the application:**
   ```bash
   # Deploy to Firebase
   firebase deploy
   ```

5. **Run the data pipeline:**
   ```bash
   # Test the system
   python scripts/test.py --test all
   
   # Fetch data from Sleeper API
   python scripts/fetch.py --save
   
   # Calculate CPR & NIV metrics
   python scripts/calculate.py --save
   ```

6. **Run locally (development):**
   ```bash
   # Start local development server
   python -m http.server 8080 --directory web
   ```

---

## Project Structure

```
cpr-nfl/
├── .env*                # Environment variables (API keys, config)
├── .env.example         # Environment template
├── .gitignore           # Git ignore rules
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── docker-compose.yml  # Container orchestration
├── Dockerfile          # Container definition
├── config/             # Configuration files
│   ├── settings.yaml   # Main configuration
│   ├── logging.yaml    # Logging configuration
│   └── mcp_config.json # MCP server settings
├── data/               # Local data storage
│   └── .gitkeep        # Keep directory in git
├── docs/               # Documentation
│   ├── api.md          # API documentation
│   ├── deployment.md   # Deployment guide
│   ├── troubleshooting.md # Common issues
│   └── project_reference.txt # Project reference
├── mcp/                # MCP servers
│   ├── __init__.py
│   ├── client.py       # MCP client utilities
│   ├── firebase_server.py # Firebase MCP server wrapper
│   └── sleeper_server.py # Sleeper MCP server
├── src/                # Core modules
│   ├── __init__.py
│   ├── cpr.py          # CPR calculations
│   ├── niv.py          # NIV analysis
│   ├── jaylen.py       # AI agent
│   ├── database.py     # Database operations
│   ├── api.py          # Sleeper API client
│   ├── models.py       # Data models
│   └── utils.py        # Shared utilities
├── scripts/            # Execution scripts
│   ├── pipeline.py     # Main data processing
│   ├── fetch.py        # Data fetching
│   ├── calculate.py    # Calculations
│   ├── test.py         # System testing
│   └── deploy.py       # Deployment utilities
├── web/                # Frontend application
│   ├── index.html      # Main page
│   ├── styles.css      # Styling
│   ├── app.js          # Frontend logic
│   └── assets/         # Static assets
│       ├── jaylen.png  # AI avatar
│       └── favicon.ico # Site icon
├── tests/              # Test suite
│   ├── __init__.py
│   ├── test_cpr.py     # CPR engine tests
│   ├── test_niv.py     # NIV calculator tests
│   ├── test_ai.py      # AI agent tests
│   ├── test_mcp.py     # MCP integration tests
│   └── test_integration.py # Full system tests
├── logs/               # Application logs
│   └── .gitkeep        # Keep directory in git
└── deployment/         # Deployment configurations
    ├── kubernetes/     # K8s configurations
    ├── terraform/      # Infrastructure as code
    └── monitoring/     # Monitoring setup
```

---

## Core Features

### CPR Rankings
- **Team-level power rankings** using advanced metrics
- **Positional adjustments** for QB, RB, WR, TE, FLEX
- **Schedule strength** normalization
- **Injury impact** factorization via Ingram Index
- **Consistency measurement** via Alvarado Index
- **Explosive potential** via Zion Index

### NIV Player Analysis
- **Player-level impact scores** (0-1 scale)
- **Position-specific benchmarks**
- **Recent performance weighting**
- **Health & injury risk integration**
- **Market context awareness**

### Jaylen AI Analyst
- **Natural language analysis** of rankings
- **Trade advice** based on CPR & NIV metrics
- **Waiver wire recommendations**
- **Start/sit decisions** with reasoning
- **League strategy** insights

### MCP Integration
- **Sleeper API server** for data fetching
- **Firebase server** for database operations
- **Unified tool interface** for AI agent
- **Extensible architecture** for new data sources

### Real-time Dashboard
- **Interactive CPR rankings** visualization
- **Player NIV trends** over time
- **Team comparison** tools
- **Trade analyzer** interface
- **Mobile-responsive** design

---

## API Integration

### Sleeper API
- **League data** (rosters, matchups, transactions)
- **Player stats** (weekly, season, projections)
- **Market data** (trending players, ADP)
- **Real-time updates** (injuries, depth charts)

### Firebase Backend
- **Secure authentication** via Firebase Auth
- **Real-time database** with Firestore
- **Cloud Functions** for serverless API
- **Hosting** for static frontend

---

## Development

### Running Tests
```bash
# Run all tests
python -m unittest discover tests/

# Run specific test modules
python -m unittest tests.test_cpr
python -m unittest tests.test_niv
python -m unittest tests.test_ai

# Run integration tests
python -m unittest tests.test_integration
```

### Development Workflow
```bash
# 1. Fetch latest data
python scripts/fetch.py --league-id YOUR_LEAGUE_ID

# 2. Calculate metrics
python scripts/calculate.py --save

# 3. Run system tests
python scripts/test.py --test all

# 4. Deploy changes
python scripts/deploy.py --environment development
```

### Configuration
All configuration is managed through YAML files in the `config/` directory:
- `settings.yaml` - Main application settings
- `logging.yaml` - Logging configuration
- `mcp_config.json` - MCP server configuration

---

## Deployment

### Automated Deployment
```bash
# Full deployment to production
python scripts/deploy.py --environment production

# Deploy specific components
python scripts/deploy.py --step firebase
python scripts/deploy.py --step docker
```

### Manual Deployment
```bash
# Deploy Firebase Functions & Hosting
firebase deploy --only functions,hosting

# Build and deploy Docker container
docker build -t cpr-nfl .
docker run cpr-nfl
```

### Environment Setup
- **Development**: Local development with mock data
- **Staging**: Test environment with real data
- **Production**: Live deployment with automated backups

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- **Python**: Follow PEP 8, use black for formatting
- **JavaScript**: Use ES6+ features, consistent indentation
- **Documentation**: Update README and docs for new features

---

## License

This project is released under a custom "source-available" license. See the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: See the `docs/` directory for detailed guides
- **Issues**: Open an issue on GitHub for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Email**: Contact the maintainers for enterprise support

---

## Acknowledgments

- **Sleeper** for the excellent fantasy football API
- **Firebase** for the serverless infrastructure
- **OpenRouter** for AI model access
- **The fantasy football community** for inspiration and feedback
