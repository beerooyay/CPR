"""CPR v2.0 Core Engine - Streamlined"""
import csv
import statistics as stats
import yaml
from pathlib import Path
from collections import defaultdict

try:
    from .scoring_system import calculate_fantasy_points_with_bonuses
except ImportError:
    from scoring_system import calculate_fantasy_points_with_bonuses

def load_config():
    """load config with fallback defaults"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except:
        # default config if file missing
        return {
            'cpr_weights': {'sli': 0.35, 'bsi': 0.15, 'smi': 0.10, 
                           'ingram': 0.15, 'alvarado': 0.15, 'zion': 0.10},
            'bench_multiplier': 0.3,
            'current_season': 2025
        }

def to_float(x):
    """Safely convert to float"""
    try:
        return float(x) if x else 0.0
    except (ValueError, TypeError):
        return 0.0

def avail_factor(info):
    """Calculate availability factor from player info"""
    info_upper = str(info).upper()
    if "DTD" in info_upper or "DAY-TO-DAY" in info_upper:
        return 0.85
    elif "OUT" in info_upper or "QUESTIONABLE" in info_upper:
        return 0.7
    elif "INJ" in info_upper or "DOUBTFUL" in info_upper:
        return 0.5
    else:
        return 1.0

def parse_positions(info_str):
    """Extract positions from player_info string"""
    if not info_str:
        return []

    positions = []
    info_upper = info_str.upper()

    for delimiter in ['/', '-', ',']:
        info_upper = info_upper.replace(delimiter, ' ')

    for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
        if pos in info_upper.split():
            positions.append(pos)

    return positions if positions else []

class CPREngine:
    """Main CPR calculation engine"""

    def __init__(self, stats_path, schedule_csv=None):
        self.config = load_config()
        self.stats_path = stats_path
        self.schedule_csv = schedule_csv
        self.players = []
        self.team_players = defaultdict(list)
        self.team_rows = []

    def load_data(self):
        """Load player stats from CSV"""
        with open(self.stats_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Calculate league FG/FT averages
        sum_fgm = sum(to_float(r.get("FGM", 0)) for r in rows)
        sum_fga = sum(to_float(r.get("FGA", 0)) for r in rows)
        sum_ftm = sum(to_float(r.get("FTM", 0)) for r in rows)
        sum_fta = sum(to_float(r.get("FTA", 0)) for r in rows)
        fg_avg = (sum_fgm / sum_fga) if sum_fga > 0 else 0.0
        ft_avg = (sum_ftm / sum_fta) if sum_fta > 0 else 0.0

        # unified field mapping
        for r in rows:
            # fantasy team (from ESPN)
            team = r.get("team", "").strip()
            team_id = r.get("team_id", team.lower().replace(' ', '_'))
            
            # player info
            name = r.get("player_name", "").strip()
            info = r.get("player_info", "")
            nba_team = r.get("nba_team", "")  # real NBA team for SMI
            
            # stats - handle all possible field names
            fgm = to_float(r.get("FGM", 0))
            fga = to_float(r.get("FGA", 0))
            ftm = to_float(r.get("FTM", 0))
            fta = to_float(r.get("FTA", 0))
            tpm = to_float(r.get("TPM", 0) or r.get("3PM", 0) or r.get("3M", 0))
            reb = to_float(r.get("REB", 0))
            ast = to_float(r.get("AST", 0))
            stl = to_float(r.get("STL", 0))
            blk = to_float(r.get("BLK", 0))
            tov = to_float(r.get("TO", 0) or r.get("TOV", 0))
            pts = to_float(r.get("PTS", 0))
            salary = to_float(r.get("salary", 10000000))  # default $10M if missing

            A_health = avail_factor(info)
            fg_imp = fgm - fg_avg * fga
            ft_imp = ftm - ft_avg * fta

            # Calculate fantasy points using league scoring
            fantasy_stats = {
                'FGM': fgm,
                'FGA': fga,
                'FTM': ftm,
                'FTA': fta,
                'TPM': tpm,
                'REB': reb,
                'AST': ast,
                'STL': stl,
                'BLK': blk,
                'TO': tov,
                'PTS': pts
            }
            fantasy_points = calculate_fantasy_points_with_bonuses(fantasy_stats)

            self.players.append({
                "team": team,
                "team_key": team_id,
                "team_id": team_id,
                "name": name,
                "player_info": info,
                "nba_team": nba_team,  # for SMI calculation
                "FGM": fgm, "FGA": fga,
                "FTM": ftm, "FTA": fta,
                "FG_imp": fg_imp, "FT_imp": ft_imp,
                "3PM": tpm, "REB": reb, "AST": ast,
                "STL": stl, "BLK": blk, "TO": tov, "PTS": pts,
                "A_health": A_health,
                "salary": salary,
                "fantasy_points": fantasy_points
            })

    def calculate_niv(self, use_entropy=False):
        """calculate NIV for all players"""
        cats = ["FG_imp", "FT_imp", "3PM", "REB", "AST", "STL", "BLK", "TO", "PTS"]
        means, stds = {}, {}

        for c in cats:
            vals = [p[c] for p in self.players]
            m = stats.mean(vals) if vals else 0.0
            s = stats.pstdev(vals) if vals else 1.0
            if s == 0:
                s = 1.0
            means[c] = m
            stds[c] = s

        # Calculate raw NIV for all players
        for p in self.players:
            zsum = 0.0
            for c in cats:
                zc = (p[c] - means[c]) / stds[c]
                if c == "TO":
                    zsum += -1.5 * zc
                else:
                    zsum += zc
            p["NIV_raw"] = zsum

            # Parse positions
            p["positions"] = parse_positions(p["player_info"])

        # fast mode - just use health as consistency
        for p in self.players:
            p["consistency"] = p["A_health"]
            p["NIV"] = p["NIV_raw"] * p["consistency"]


    def calculate_team_metrics(self):
        """calculate team-level indices"""
        # group by team
        for p in self.players:
            if p["team_key"]:
                self.team_players[p["team_key"]].append(p)

        for tk, plist in self.team_players.items():
            ps = sorted(plist, key=lambda x: x["NIV"], reverse=True)

            # SLI (top 9)
            top9 = ps[:9]
            SLI = sum(x["NIV"] for x in top9)

            # BSI (bench)
            bench = ps[9:]
            bench_mult = self.config['bench_multiplier']
            BSI = bench_mult * sum(x["NIV"] for x in bench)

            # Ingram Index (HHI-based positional balance)
            pos_niv = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
            total_niv = sum(p["NIV"] for p in ps)
            for p in ps:
                for pos in p["positions"]:
                    if pos in pos_niv:
                        pos_niv[pos] += p["NIV"]

            if total_niv > 0:
                shares = {pos: (niv / total_niv) for pos, niv in pos_niv.items()}
                HHI = sum(share**2 for share in shares.values())
                ingram = 1 / HHI if HHI > 0 else 0
            else:
                ingram = 0

            # alvarado index - simplified value metric
            if total_niv > 0 and sum(p["salary"] for p in ps) > 0:
                avg_salary = stats.mean([p["salary"] for p in ps if p["salary"] > 0])
                league_avg_salary = 15000000  # $15M average
                salary_mult = avg_salary / league_avg_salary if league_avg_salary > 0 else 1
                alvarado_team = total_niv / (salary_mult ** 2) if salary_mult > 0 else total_niv
            else:
                alvarado_team = total_niv

            # Zion Index (health)
            games_missed = sum(1 - p["A_health"] for p in ps)
            total_possible = len(ps)
            health_ratio = 1 - (games_missed / total_possible) if total_possible > 0 else 1.0
            zion = health_ratio

            # SMI - check for teammate correlations
            from collections import Counter
            nba_teams = [p.get('nba_team', '') for p in ps if p.get('nba_team')]
            team_counts = Counter(nba_teams)
            # penalty for having multiple players from same NBA team
            smi = -0.05 * sum(count - 1 for count in team_counts.values() if count > 1)

            disp = ps[0]["team"] if ps else tk
            self.team_rows.append({
                "team": disp,
                "team_key": tk,
                "SLI": SLI,
                "BSI": BSI,
                "ingram": ingram,
                "alvarado_team": alvarado_team,
                "zion": zion,
                "smi": smi
            })

    def normalize_and_rank(self):
        """Z-normalize team metrics and calculate CPR"""
        # Z-normalize
        for metric in ["SLI", "BSI", "smi", "ingram", "alvarado_team", "zion"]:
            vals = [tr[metric] for tr in self.team_rows]
            m = stats.mean(vals) if vals else 0.0
            s = stats.pstdev(vals) if vals else 1.0
            if s == 0:
                s = 1.0

            for tr in self.team_rows:
                tr[f"{metric}_z"] = (tr[metric] - m) / s

        # Calculate RawPower
        weights = self.config['cpr_weights']
        for tr in self.team_rows:
            tr["RawPower"] = (
                weights['sli'] * tr["SLI_z"] +
                weights['bsi'] * tr["BSI_z"] +
                weights.get('smi', 0.10) * tr["smi_z"] +  # NEW!
                weights['ingram'] * tr["ingram_z"] +
                weights['alvarado'] * tr["alvarado_team_z"] +
                weights['zion'] * tr["zion_z"]
            )

        # Calculate SoS (if schedule provided)
        if self.schedule_csv:
            # TODO: Implement SoS calculation
            for tr in self.team_rows:
                tr["SoS"] = 1.0
        else:
            for tr in self.team_rows:
                tr["SoS"] = 1.0

        # Calculate CPR
        for tr in self.team_rows:
            tr["CPR"] = tr["RawPower"] * tr["SoS"]

        # Sort and rank
        self.team_rows.sort(key=lambda x: x["CPR"], reverse=True)
        for i, tr in enumerate(self.team_rows, 1):
            tr["rank"] = i

    def calculate_league_metrics(self):
        """Calculate Gini and LHI"""
        # Gini coefficient - using absolute values for stability
        cpr_vals = [abs(tr["CPR"]) for tr in self.team_rows]
        n = len(cpr_vals)
        if n > 1:
            sorted_vals = sorted(cpr_vals)
            cumsum = sum((i + 1) * val for i, val in enumerate(sorted_vals))
            total = sum(sorted_vals)
            if total > 0:
                gini = (2 * cumsum) / (n * total) - (n + 1) / n
            else:
                gini = 0
        else:
            gini = 0

        # League Health Index
        lhi = stats.mean([p["A_health"] for p in self.players]) if self.players else 0

        # Team Health Index
        thi = {}
        for tk, plist in self.team_players.items():
            thi[tk] = stats.mean([p["A_health"] for p in plist]) if plist else 0

        return {"gini": gini, "lhi": lhi, "thi": thi}

    def run(self):
        """Run full CPR calculation"""
        self.load_data()
        self.calculate_niv()
        self.calculate_team_metrics()
        self.normalize_and_rank()
        league_metrics = self.calculate_league_metrics()

        return {
        "teams": self.team_rows,
        "players": self.players,
        "league": league_metrics
        }

if __name__ == "__main__":
    from pathlib import Path
    stats_path = Path(__file__).parent.parent / "data" / "raw" / "current_stats.csv"
    if stats_path.exists():
        engine = CPREngine(str(stats_path))
        results = engine.run()
        for team in results["teams"][:3]:
            print(f"{team['rank']}. {team['team']}: {team['CPR']:.3f}")
    else:
        print(f"no stats file at {stats_path}")
