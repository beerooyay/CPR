# Sleeper API Guide for CPR Framework

## Verified Working Endpoints

### 1. NFL Stats (Historical & Current)
```
✅ stats/nfl/regular/{year}        # Years: 2019-2025
✅ projections/nfl/regular/{year}  # Years: 2019-2025
✅ state/nfl                       # Current NFL state
✅ players/nfl                     # All NFL players database
✅ players/nfl/trending/add        # Trending adds
✅ players/nfl/trending/drop       # Trending drops
```

### 2. League Data (Current Season Only)
```
✅ league/{league_id}                    # Basic league info
✅ league/{league_id}/rosters            # Current rosters
✅ league/{league_id}/users              # League members
✅ league/{league_id}/matchups/{week}    # Weekly matchups (1-18)
✅ league/{league_id}/transactions/{week} # Weekly transactions
✅ league/{league_id}/drafts             # Draft list
✅ league/{league_id}/winners_bracket    # Playoff bracket
✅ league/{league_id}/losers_bracket     # Consolation bracket
```

### 3. Draft Data
```
✅ draft/{draft_id}        # Draft metadata
✅ draft/{draft_id}/picks  # All draft picks
✅ draft/{draft_id}/traded_picks # Traded picks
```

### 4. User Data
```
✅ user/{user_id}                    # User profile
✅ user/{user_id}/leagues/nfl/{year} # User's leagues by year
```

### 5. Metadata Structure (CRITICAL for Team Names & Avatars)
```
✅ League Metadata:
   - league/{league_id} → metadata: {auto_continue, keeper_deadline}
   - league/{league_id} → settings: {playoff_teams, num_teams, etc.}

✅ Roster Metadata:
   - league/{league_id}/rosters → metadata: {record, streak, p_nick_*}
   - Contains: win/loss streaks, player nicknames
   - Does NOT contain team names (common mistake)

✅ User Metadata (TEAM NAMES SOURCE):
   - league/{league_id}/users → metadata: {team_name, avatar, allow_pn}
   - TEAM NAMES: user.metadata.team_name (NOT roster.metadata.team_name)
   - AVATARS: user.metadata.avatar (full URLs) OR user.avatar (IDs)
   - Example: "Fort Garland Altitude", "Kingston Rasta Rockets"

✅ Avatar URLs:
   - Full size: https://sleepercdn.com/avatars/{avatar_id}
   - Thumbnail: https://sleepercdn.com/avatars/thumbs/{avatar_id}
   - User avatars may be full URLs in metadata.avatar
```

---

## CPR Data Pipeline Architecture

### Phase 1: Global NFL Data Collection (2019-2025)

#### 1.1 Player Universe Creation
```python
# Get complete player database
players_db = GET players/nfl
# Structure: {player_id: {name, position, team, etc.}}

# Create player timeline tracking
player_timeline = {
    player_id: {
        'years_active': [],
        'teams_played_for': {},
        'positions': [],
        'career_stats': {}
    }
}
```

#### 1.2 Historical Stats Collection
```python
for year in range(2019, 2026):
    # Get season rankings/stats
    year_stats = GET stats/nfl/regular/{year}
    
    # Get projections for context
    year_projections = GET projections/nfl/regular/{year}
    
    # Structure per year:
    {
        year: {
            player_id: {
                'pos_rank_ppr': int,
                'pos_rank_half_ppr': int, 
                'pos_rank_std': int,
                'rank_ppr': int,
                'rank_half_ppr': int,
                'rank_std': int,
                'projection': float  # from projections endpoint
            }
        }
    }
```

#### 1.3 Player Career Profiles
```python
# Build comprehensive player profiles
player_profiles = {
    player_id: {
        'metadata': players_db[player_id],
        'career_data': {
            2019: year_stats[2019].get(player_id),
            2020: year_stats[2020].get(player_id),
            # ... through 2025
        },
        'career_metrics': {
            'years_active': count_active_years(),
            'peak_rank': min(all_ranks),
            'consistency_score': calculate_rank_variance(),
            'trajectory': calculate_trend_slope()
        }
    }
}
```

### Phase 2: Legion League Data Collection (2025 Only)

#### 2.1 League Structure
```python
# Basic league info
league_info = GET league/{league_id}

# Team rosters (current)
rosters = GET league/{league_id}/rosters
# Structure: [{roster_id, user_id, players[], settings{}}]

# League members (CONTAINS TEAM NAMES)
users = GET league/{league_id}/users
# Structure: [{user_id, display_name, metadata{team_name, avatar}}]

# CORRECT team name extraction
def get_team_names():
    rosters = GET league/{league_id}/rosters
    users = GET league/{league_id}/users
    user_lookup = {user['user_id']: user for user in users}
    
    teams = []
    for roster in rosters:
        user_id = roster['owner_id']
        user_info = user_lookup[user_id]
        
        team_name = user_info['metadata'].get('team_name', f'Team {roster["roster_id"]}')
        owner_name = user_info['display_name']
        
        teams.append({
            'roster_id': roster['roster_id'],
            'team_name': team_name,  # "Fort Garland Altitude"
            'owner_name': owner_name, # "beerooyay"
            'logo_url': get_avatar_url(user_info)
        })
    
    return teams
```

#### 2.2 Weekly Performance Data
```python
# Collect all weeks (1-8 current, up to 18 total)
weekly_data = {}
for week in range(1, 19):
    matchups = GET league/{league_id}/matchups/{week}
    if matchups:
        weekly_data[week] = {
            matchup['roster_id']: {
                'points': matchup['points'],
                'starters': matchup['starters'],
                'players_points': matchup['players_points'],
                'matchup_id': matchup['matchup_id']
            }
            for matchup in matchups
        }
```

#### 2.3 Draft Analysis
```python
# Get draft info
drafts = GET league/{league_id}/drafts
draft_id = drafts[0]['draft_id']

# Get all picks
draft_picks = GET draft/{draft_id}/picks
# Structure: [{pick_no, round, player_id, roster_id, metadata}]

# Create ADP mapping
adp_mapping = {
    pick['player_id']: {
        'pick_no': pick['pick_no'],
        'round': pick['round'],
        'roster_id': pick['roster_id']
    }
    for pick in draft_picks
}
```

#### 2.4 Transaction History
```python
# Collect all transactions
all_transactions = {}
for week in range(1, 19):
    transactions = GET league/{league_id}/transactions/{week}
    if transactions:
        all_transactions[week] = transactions

# Track roster changes
roster_changes = track_adds_drops(all_transactions)
waiver_activity = analyze_waiver_patterns(all_transactions)
```

### Phase 3: CPR Metrics Calculation

#### 3.1 NIV Calculation (Hybrid)
```python
def calculate_player_niv(player_id, year=2025):
    if year == 2025:
        # Use Legion league performance
        legion_performance = extract_legion_performance(player_id)
        nfl_context = year_stats[2025].get(player_id, {})
        return calculate_niv_hybrid(legion_performance, nfl_context)
    else:
        # Use general NFL stats
        return calculate_niv_from_nfl_stats(year_stats[year][player_id])

# Multi-year NIV trending
player_niv_history = {
    player_id: {
        year: calculate_player_niv(player_id, year)
        for year in range(2019, 2026)
        if player_existed_in_year(player_id, year)
    }
}
```

#### 3.2 Ingram Index (Positional Balance)
```python
def calculate_team_ingram(roster_id):
    roster = rosters[roster_id]
    starters = get_current_starters(roster_id)
    bench = get_bench_players(roster_id)
    
    # Calculate HHI for starters and bench
    starter_hhi = calculate_positional_hhi(starters)
    bench_hhi = calculate_positional_hhi(bench)
    
    # Weighted combination
    return 1 - (0.7 * starter_hhi + 0.3 * bench_hhi)

team_ingram_scores = {
    roster['roster_id']: calculate_team_ingram(roster['roster_id'])
    for roster in rosters
}
```

#### 3.3 Alvarado Index (Value Efficiency)
```python
def calculate_player_alvarado(player_id, roster_id):
    # Get draft position (or waiver = 0)
    adp = adp_mapping.get(player_id, {'pick_no': 999})['pick_no']
    
    # Calculate Shapley value from lineup combinations
    shapley_value = calculate_shapley_from_lineups(player_id, roster_id)
    
    # Get NIV z-score
    niv_z = calculate_niv_zscore(player_id)
    adp_z = calculate_adp_zscore(adp)
    
    # Alvarado formula
    return shapley_value / ((niv_z + adp_z) / 2) ** 2

player_alvarado_scores = {
    player_id: calculate_player_alvarado(player_id, roster_id)
    for roster_id, roster in enumerate(rosters)
    for player_id in roster['players']
}
```

#### 3.4 4D SoS Tensor
```python
def calculate_4d_sos_tensor(roster_id, current_week=8):
    opponents = get_opponents_through_week(roster_id, current_week)
    
    # Dimension 1: Traditional SoS (opponent win %)
    dim1 = calculate_opponent_win_percentage(opponents)
    
    # Dimension 2: Volatility exposure (opponent variance)
    dim2 = calculate_opponent_volatility(opponents)
    
    # Dimension 3: Positional stress (Ingram-derived)
    dim3 = calculate_positional_matchup_stress(roster_id, opponents)
    
    # Dimension 4: Efficiency pressure (Alvarado-derived)
    dim4 = calculate_efficiency_pressure(roster_id, opponents)
    
    # Create 4D tensor
    tensor = np.array([dim1, dim2, dim3, dim4])
    tensor_magnitude = np.linalg.norm(tensor)
    
    return {
        'tensor_vector': tensor,
        'tensor_magnitude': tensor_magnitude,
        'dimensions': {
            'traditional': dim1,
            'volatility': dim2, 
            'positional': dim3,
            'efficiency': dim4
        }
    }

team_sos_tensors = {
    roster['roster_id']: calculate_4d_sos_tensor(roster['roster_id'])
    for roster in rosters
}
```

### Phase 4: CPR Final Calculation

#### 4.1 Team CPR Assembly
```python
def calculate_team_cpr(roster_id):
    # Get team's players and their NIVs
    team_players = rosters[roster_id]['players']
    team_niv = sum(player_niv_history[p][2025] for p in team_players)
    
    # Get team's indices
    ingram_score = team_ingram_scores[roster_id]
    
    # Average Alvarado for team
    team_alvarado = np.mean([
        player_alvarado_scores.get(p, 0) for p in team_players
    ])
    
    # SoS tensor magnitude
    sos_tensor = team_sos_tensors[roster_id]['tensor_magnitude']
    
    # CPR formula
    cpr = (team_niv * ingram_score * team_alvarado) / (1 + sos_tensor)
    
    return {
        'cpr_score': cpr,
        'components': {
            'team_niv': team_niv,
            'ingram_index': ingram_score,
            'alvarado_index': team_alvarado,
            'sos_tensor': sos_tensor
        }
    }

final_cpr_rankings = {
    roster['roster_id']: calculate_team_cpr(roster['roster_id'])
    for roster in rosters
}
```

### Phase 5: Database Structure

#### 5.1 Core Tables
```sql
-- Players table
players: {player_id, name, position, team, active, metadata}

-- Player stats by year
player_stats: {player_id, year, pos_rank_ppr, rank_ppr, niv_score}

-- Legion league structure  
league_teams: {roster_id, user_id, team_name}
league_rosters: {roster_id, player_id, starter_status}

-- Weekly performance
weekly_matchups: {week, roster_id, points, opponent_id}
player_weekly: {week, player_id, roster_id, points, starter}

-- Draft data
draft_picks: {player_id, roster_id, pick_no, round}

-- CPR metrics
team_cpr: {roster_id, week, cpr_score, ingram, alvarado, sos_tensor}
```

#### 5.2 API Call Sequence
```python
# 1. Initialize global data (run once)
load_nfl_players()           # players/nfl
load_historical_stats()      # stats/nfl/regular/{2019-2025}
load_projections()          # projections/nfl/regular/{2019-2025}

# 2. Initialize league data (run once per season)
load_league_structure()     # league/{id}, rosters, users
load_draft_data()          # league/{id}/drafts, draft/{id}/picks

# 3. Update weekly (run each week)
update_weekly_matchups()    # league/{id}/matchups/{week}
update_transactions()       # league/{id}/transactions/{week}
recalculate_cpr()          # All CPR metrics

# 4. Generate reports
generate_cpr_rankings()
generate_player_analysis()
generate_trade_recommendations()
```

---

## Implementation Priority

1. **Phase 1**: Global NFL data (foundation)
2. **Phase 2**: Legion league data (current season)
3. **Phase 3**: Basic CPR metrics (NIV, Ingram, Alvarado)
4. **Phase 4**: 4D SoS tensor (advanced)
5. **Phase 5**: Database optimization and reporting

## Key Features

- **7-year historical context** (2019-2025 NFL stats)
- **Real-time Legion league analysis** (2025 season)
- **Hybrid accuracy** (league-specific + historical trends)
- **Novel 4D tensor SoS** (world's first implementation)
- **Dynamic player profiles** (career trajectories)
- **Automated weekly updates** (matchups + transactions)
