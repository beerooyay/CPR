// Data models for CPR-NFL system

export enum Position {
  QB = "QB",
  RB = "RB", 
  WR = "WR",
  TE = "TE",
  K = "K",
  DEF = "DEF",
  FLEX = "FLEX",
  SUPER_FLEX = "SUPER_FLEX",
  IDP = "IDP"
}

export enum InjuryStatus {
  ACTIVE = "Active",
  QUESTIONABLE = "Questionable", 
  DOUBTFUL = "Doubtful",
  OUT = "Out",
  INJURED_RESERVE = "Injured Reserve",
  SUSPENDED = "Suspended"
}

export interface PlayerStats {
  season: number;
  games_played: number;
  passing_yards?: number;
  passing_tds?: number;
  passing_ints?: number;
  rushing_yards?: number;
  rushing_tds?: number;
  receptions?: number;
  receiving_yards?: number;
  receiving_tds?: number;
  targets?: number;
  fumbles?: number;
  fantasy_points?: number;
  fantasy_points_per_game?: number;
}

export interface Player {
  player_id: string;
  name: string;
  position: Position;
  team: string;
  height?: string;
  weight?: number;
  college?: string;
  draft_year?: number;
  draft_round?: number;
  status?: string;
  injury_status?: InjuryStatus;
  fantasy_positions?: Position[];
  stats?: Record<number, PlayerStats>;
}

export interface Team {
  team_id: string;
  team_name: string;
  owner_name: string;
  wins?: number;
  losses?: number;
  ties?: number;
  fpts?: number;
  fpts_against?: number;
  starters?: string[];
  bench?: string[];
  roster?: string[];
}

export interface CPRMetrics {
  sli: number;      // Strength of Lineup Index
  bsi: number;      // Bench Strength Index  
  smi: number;      // Schedule Momentum Index
  ingram: number;   // Ingram Index (HHI positional balance)
  alvarado: number; // Alvarado Index (Shapley/ADP value efficiency)
  zion: number;     // Zion Tensor (4D strength of schedule)
  cpr: number;      // Overall CPR score
  rank: number;
}

export interface NIVMetrics {
  niv: number;
  positional_niv: number;
  market_niv: number;
  explosive_niv: number;
  consistency_niv: number;
  niv_tier: string;
  rank: number;
  positional_rank: number;
}

export interface LeagueInfo {
  league_id: string;
  name: string;
  season: number;
  current_week: number;
  total_teams: number;
  status: string;
}

export interface LeagueAnalysis {
  league_info: LeagueInfo;
  cpr_rankings: Record<string, CPRMetrics>;
  niv_rankings: Record<string, NIVMetrics>;
  teams: Record<string, Team>;
  players: Record<string, Player>;
  analysis_timestamp: string;
}
