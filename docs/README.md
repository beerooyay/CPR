# CPR — Commissioner's Parity Report

**A novel, serverless sports analytics framework combining game theory, economics, and information theory.**

[![License](https://img.shields.io/badge/License-Custom-blue.svg)](LICENSE)

---

## What is CPR?

CPR is a novel fantasy basketball ranking system that uses:
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

## The Architecture

This project is a 100% serverless, automated sports analytics platform.

- **Frontend**: A static web app built with vanilla HTML/CSS/JS, hosted on Firebase Hosting.
- **Backend**: A serverless API powered by Firebase Cloud Functions, providing secure access to the database.
- **Database**: A Firestore database that serves as the live, scalable source of truth for the app.
- **ETL Pipeline**: A Dockerized Python application, designed to be run as a scheduled job (e.g., Google Cloud Run), that automatically fetches data from the ESPN API, calculates all CPR metrics, and saves them to Firestore.

---

## Quick Start

See the [Setup Guide](SETUP.md) for detailed installation and deployment instructions.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/beerooyay/CPR.git
    cd CPR
    ```

2.  **Deploy the application:**
    ```bash
    # Follow the setup guide to configure Firebase and API keys
    firebase deploy
    ```

3.  **Run the data pipeline:**
    ```bash
    # Follow the setup guide to build the Docker container and run the pipeline
    # This command runs the full ETL process
    docker run cpr-pipeline
    ```

---

## Project Structure

```
CPR/
├── functions/      # Serverless backend (Firebase Cloud Functions)
├── web/            # Frontend web application
├── src/            # Core Python logic for the CPR engine
├── scripts/        # Python scripts for the ETL pipeline
├── config/         # YAML configuration for the CPR engine
├── data/           # Local data files (e.g., raw CSVs)
├── docs/           # All project documentation
├── Dockerfile      # Blueprint for the ETL pipeline container
├── firebase.json   # Firebase configuration
├── firestore.rules # Firestore security rules
├── requirements.txt  # Python dependencies
└── LICENSE         # Custom source-available license
```

---

## License

This project is released under a custom "source-available" license. See the [LICENSE](LICENSE) file for details.
