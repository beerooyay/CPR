"""CPR v2.0 Core Engine - Streamlined"""
import csv
import statistics as stats
import yaml
import pandas as pd
from pathlib import Path
from collections import defaultdict

try:
    from .scoring_system import calculate_fantasy_points_with_bonuses
except ImportError:
    from scoring_system import calculate_fantasy_points_with_bonuses

def load_config():
    """Load config with fallback defaults."""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            'cpr_weights': {'sli': 0.35, 'bsi': 0.15, 'smi': 0.10, 
                           'ingram': 0.15, 'alvarado': 0.15, 'zion': 0.10},
            'bench_multiplier': 0.3,
            'current_season': 2025
        }

def to_float(x):
    """Safely convert to float."""
    try:
        return float(x) if x is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

def avail_factor(info):
    """Calculate availability factor from player info string."""
    info_upper = str(info).upper()
    if "DTD" in info_upper or "DAY-TO-DAY" in info_upper: return 0.85
    if "O" in info_upper or "OUT" in info_upper: return 0.7
    return 1.0

def parse_positions(info_str):
    """Extract positions from player_info string."""
    if not info_str: return []
    # Simplified and more robust parsing
    return [pos for pos in ['PG', 'SG', 'SF', 'PF', 'C'] if pos in info_str.upper()]

class CPREngine:
    """Main CPR calculation engine."""

    def __init__(self, stats_path, schedule_csv=None):
        self.config = load_config()
        self.stats_path = stats_path
        self.schedule_csv = schedule_csv
        self.players_df = None
        self.teams_df = None

    def load_data(self):
        """Load and validate player stats from CSV using pandas."""
        self.players_df = pd.read_csv(self.stats_path)

        required_columns = ['player_name', 'team', 'salary', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO']
        missing_columns = [col for col in required_columns if col not in self.players_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in stats CSV: {', '.join(missing_columns)}")

        # Data cleaning and type conversion
        for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGM', 'FGA', 'FTM', 'FTA', 'TPM', 'salary']:
            if col in self.players_df.columns:
                self.players_df[col] = pd.to_numeric(self.players_df[col], errors='coerce').fillna(0)

        # Calculate derived stats
        fg_avg = self.players_df['FGM'].sum() / self.players_df['FGA'].sum() if self.players_df['FGA'].sum() > 0 else 0
        ft_avg = self.players_df['FTM'].sum() / self.players_df['FTA'].sum() if self.players_df['FTA'].sum() > 0 else 0
        self.players_df['FG_imp'] = self.players_df['FGM'] - (self.players_df['FGA'] * fg_avg)
        self.players_df['FT_imp'] = self.players_df['FTM'] - (self.players_df['FTA'] * ft_avg)
        self.players_df['A_health'] = self.players_df['player_info'].apply(avail_factor)
        self.players_df['fantasy_points'] = self.players_df.apply(calculate_fantasy_points_with_bonuses, axis=1)

    def calculate_niv(self):
        """Calculate NIV for all players using z-scores."""
        cats = ["FG_imp", "FT_imp", "TPM", "REB", "AST", "STL", "BLK", "TO", "PTS"]
        for cat in cats:
            mean = self.players_df[cat].mean()
            std = self.players_df[cat].std()
            if std == 0: std = 1 # Avoid division by zero
            self.players_df[f'{cat}_z'] = (self.players_df[cat] - mean) / std

        z_cols = [f'{cat}_z' for cat in cats]
        # Invert TOV z-score
        self.players_df['TO_z'] = self.players_df['TO_z'] * -1.5
        self.players_df['NIV_raw'] = self.players_df[z_cols].sum(axis=1)
        self.players_df['NIV'] = self.players_df['NIV_raw'] * self.players_df['A_health']

    def calculate_team_metrics(self):
        """Calculate all team-level indices (SLI, BSI, etc.)."""
        team_groups = self.players_df.groupby('team')
        team_metrics = []

        for name, group in team_groups:
            sorted_players = group.sort_values('NIV', ascending=False)
            top_9 = sorted_players.head(9)
            bench = sorted_players.iloc[9:]

            sli = top_9['NIV'].sum()
            bsi = bench['NIV'].sum() * self.config.get('bench_multiplier', 0.3)
            zion = group['A_health'].mean()
            
            # Ingram Index (HHI)
            total_niv = group['NIV'].sum()
            pos_niv = defaultdict(float)
            for _, player in group.iterrows():
                positions = parse_positions(player['player_info'])
                for pos in positions:
                    pos_niv[pos] += player['NIV']
            hhi = sum((niv / total_niv) ** 2 for niv in pos_niv.values()) if total_niv > 0 else 0
            ingram = 1 / hhi if hhi > 0 else 0

            # Alvarado Index
            total_salary = group['salary'].sum()
            alvarado = total_niv / total_salary if total_salary > 0 else 0

            # SMI
            nba_team_counts = group['nba_team'].value_counts()
            smi_penalty = sum(count - 1 for count in nba_team_counts if count > 1)
            smi = -0.05 * smi_penalty

            team_metrics.append({
                'team': name,
                'team_key': name.lower().replace(' ', '_'), # Ensure team_key is present
                'sli': sli, 'bsi': bsi, 'zion': zion, 'ingram': ingram, 'alvarado': alvarado, 'smi': smi
            })
        
        self.teams_df = pd.DataFrame(team_metrics)

    def normalize_and_rank(self):
        """Z-normalize team metrics and calculate final CPR score."""
        metrics = ['sli', 'bsi', 'zion', 'ingram', 'alvarado', 'smi']
        for metric in metrics:
            mean = self.teams_df[metric].mean()
            std = self.teams_df[metric].std()
            if std == 0: std = 1
            self.teams_df[f'{metric}_z'] = (self.teams_df[metric] - mean) / std

        weights = self.config['cpr_weights']
        self.teams_df['RawPower'] = sum(self.teams_df[f'{m}_z'] * weights[m] for m in metrics)
        self.teams_df['SoS'] = 1.0 # Placeholder for Strength of Schedule
        self.teams_df['CPR'] = self.teams_df['RawPower'] * self.teams_df['SoS']
        self.teams_df = self.teams_df.sort_values('CPR', ascending=False).reset_index(drop=True)
        self.teams_df['rank'] = self.teams_df.index + 1

    def calculate_league_metrics(self):
        """Calculate Gini coefficient and League Health Index."""
        cpr_vals = self.teams_df['CPR'].abs().sort_values().reset_index(drop=True)
        n = len(cpr_vals)
        if n > 1 and cpr_vals.sum() > 0:
            cumsum = (cpr_vals.index + 1).to_numpy().dot(cpr_vals.to_numpy())
            gini = (2 * cumsum) / (n * cpr_vals.sum()) - (n + 1) / n
        else:
            gini = 0
        
        lhi = self.players_df['A_health'].mean()
        return {'gini_coefficient': gini, 'league_health_index': lhi}

    def run(self):
        """Run the full CPR calculation pipeline."""
        self.load_data()
        self.calculate_niv()
        self.calculate_team_metrics()
        self.normalize_and_rank()
        league_metrics = self.calculate_league_metrics()

        # Prepare final output dictionaries
        players_output = self.players_df.to_dict(orient='records')
        cpr_rankings_output = self.teams_df.to_dict(orient='records')

        return {
            'players': players_output,
            'cpr_rankings': cpr_rankings_output,
            'league_metrics': league_metrics
        }

if __name__ == "__main__":
    stats_path = Path(__file__).parent.parent / "data" / "raw" / "current_stats.csv"
    if stats_path.exists():
        engine = CPREngine(str(stats_path))
        results = engine.run()
        print("--- Top 3 Teams ---")
        for team in results['cpr_rankings'][:3]:
            print(f"{team['rank']}. {team['team']}: {team['CPR']:.3f}")
    else:
        print(f"Stats file not found at {stats_path}")
