# Database Structure - Complete Player History

**The database stores BOTH raw stats AND calculated metrics for historical analysis**

---

## how it works:

### **when you run CPR:**
```bash
python scripts/run_cpr.py --stats data/raw/current_stats.csv --save-to-db
```

### **it saves 3 things per player:**

**1. Raw Stats** (`player_stats` table):
```sql
FGM, FGA, FTM, FTA, 3PM, REB, AST, STL, BLK, TO, PTS
```

**2. Calculated Metrics** (`player_metrics` table):
```sql
NIV_raw, NIV_final, consistency_score, alvarado_index
```

**3. Salary** (`player_salaries` table):
```sql
salary
```

**all linked by `player_id` and `season_id`**

---

## query examples:

### **get everything for one player:**
```sql
SELECT 
 s.season_year,
 -- raw stats
 ps.fgm, ps.fga, ps.points, ps.rebounds, ps.assists,
 -- calculated
 pm.niv_raw, pm.niv_adjusted, pm.consistency_score,
 -- cost
 sal.salary
FROM players p
JOIN player_stats ps USING (player_id)
JOIN player_metrics pm USING (player_id, season_id)
JOIN player_salaries sal USING (player_id, season_id)
JOIN seasons s USING (season_id)
WHERE p.player_name = 'Stephen Curry';
```

### **compare players:**
```sql
SELECT 
 player_name,
 niv_raw,
 niv_adjusted,
 consistency_score,
 alvarado_index
FROM players p
JOIN player_metrics pm USING (player_id)
WHERE season_id = (SELECT season_id FROM seasons WHERE season_year = 2025)
ORDER BY niv_adjusted DESC
LIMIT 10;
```

### **year-over-year analysis:**
```sql
-- Who improved most from 2024 to 2025?
SELECT 
 p.player_name,
 pm2025.niv_adjusted - pm2024.niv_adjusted as niv_improvement
FROM players p
JOIN player_metrics pm2024 ON p.player_id = pm2024.player_id
JOIN player_metrics pm2025 ON p.player_id = pm2025.player_id
WHERE pm2024.season_id = (SELECT season_id FROM seasons WHERE season_year = 2024)
 AND pm2025.season_id = (SELECT season_id FROM seasons WHERE season_year = 2025)
ORDER BY niv_improvement DESC;
```

---

## python API:

### **save data:**
```python
from cpr_engine import CPREngine
from db_saver import save_all_players_from_cpr

# Run CPR
engine = CPREngine("data/2025_stats.csv")
results = engine.run()

# Save to database (raw stats + calculated metrics)
save_all_players_from_cpr(results, season_year=2025)
```

### **query history:**
```python
from db_saver import query_player_history

# Get complete history
history = query_player_history("Stephen Curry")

for season in history:
 print(f"{season['season_year']}: NIV={season['niv_adjusted']:.2f}, PTS={season['points']:.1f}")
```

output:
```
2025: NIV=5.23, PTS=28.4
2024: NIV=4.87, PTS=26.7
2023: NIV=5.01, PTS=29.4
```

---

## retroactive addition:

### **add old seasons:**
```python
# Add 2023 season
engine = CPREngine("data/2023_stats.csv")
results = engine.run()
save_all_players_from_cpr(results, season_year=2023)

# Add 2024 season
engine = CPREngine("data/2024_stats.csv")
results = engine.run()
save_all_players_from_cpr(results, season_year=2024)

# Now database has 2023, 2024, 2025!
```

### **query across years:**
```sql
SELECT 
 season_year,
 AVG(niv_adjusted) as avg_niv,
 MAX(niv_adjusted) as max_niv
FROM player_metrics pm
JOIN seasons s USING (season_id)
GROUP BY season_year
ORDER BY season_year;
```

---

## what this enables:

### **1. player development tracking:**
```python
# Track a rookie's progression
rookie = query_player_history("Cooper Flagg")
# See NIV improve over seasons
```

### **2. value trends:**
```sql
-- Which players increased value while salary stayed same?
SELECT player_name, 
 niv_2025 - niv_2024 as niv_gain,
 salary_2025 - salary_2024 as salary_change
WHERE salary_change = 0 AND niv_gain > 0
ORDER BY niv_gain DESC;
```

### **3. consistency analysis:**
```sql
-- Most consistent players over time
SELECT player_name,
 AVG(consistency_score) as avg_consistency
FROM player_metrics
GROUP BY player_id
HAVING COUNT(*) >= 3 -- at least 3 seasons
ORDER BY avg_consistency DESC;
```

### **4. alvarado leaders:**
```sql
-- Best value players by year
SELECT season_year, player_name, alvarado_index, salary
FROM player_metrics pm
JOIN players p USING (player_id)
JOIN seasons s USING (season_id)
WHERE alvarado_index = (
 SELECT MAX(alvarado_index) 
 FROM player_metrics 
 WHERE season_id = pm.season_id
)
ORDER BY season_year DESC;
```

---

## current status:

**database:** `/Users/beerooyay/Desktop/CPR/data/cpr_data.db` (148 KB)

**current data:**
- 137 players (names, positions)
- 10 teams
- 1 season (2025)
- player_stats (empty - needs save)
- player_metrics (empty - needs save)
- player_salaries (empty - needs save)

**to populate:**
```bash
python scripts/run_cpr.py --stats data/raw/current_stats.csv --save-to-db
```

**this will save:**
- raw stats for 137 players
- calculated metrics (NIV, consistency, alvarado)
- salaries

---

## the power:

### **before:**
- CSV file with current season only
- No historical comparison
- Can't track player development

### **after:**
- Database with multi-season history
- Query any player across years
- Track NIV evolution
- Analyze value trends
- Compare consistency over time

---

## example workflow:

### **year 1 (2023):**
```python
# Save 2023 season
engine = CPREngine("data/2023_stats.csv")
results = engine.run()
save_all_players_from_cpr(results, 2023)
```

### **year 2 (2024):**
```python
# Save 2024 season
engine = CPREngine("data/2024_stats.csv")
results = engine.run()
save_all_players_from_cpr(results, 2024)

# Compare to 2023
history = query_player_history("Shai Gilgeous-Alexander")
# See: 2023: NIV=4.2, 2024: NIV=5.1 (+0.9 improvement!)
```

### **year 3 (2025):**
```python
# Save 2025 season
engine = CPREngine("data/2025_stats.csv")
results = engine.run()
save_all_players_from_cpr(results, 2025)

# Analyze 3-year trend
```

---

## what you get:

**for each player, each season:**
- raw counting stats (PTS, REB, AST, etc.)
- shooting percentages (FG%, FT%, 3P%)
- calculated NIV (raw and final)
- consistency score (from entropy)
- alvarado index (value per $)
- salary

**all queryable, all historical, all structured.**

**this is a COMPLETE player analytics database.** 
