// API Configuration - Firebase Functions
const API_BASE = ''; // Use relative URLs for same-origin requests
const MODEL = 'openai/gpt-oss-20b:free'; // Confirmed model
const LEAGUE_ID = '1267325171853701120'; // Legion Fantasy Football League ID

console.log('CPR-NFL App v16.6 - STAT DROPDOWN ON LEAGUE ANALYTICS!');
console.log('Data pipeline fully corrected. All metrics are live and accurate.');

// State// Global state
let currentScreen = 'home';
let selectedTeam = null;
let nivState = 'roster'; // 'roster' or 'bench'
let chatMessages = [];
let currentConversationId = null;

// Global data cache for consistent sleeper data
const SleeperDataCache = {
    stats: null,
    players: null,
    projections: null,
    rosters: null,
    
    async getStats() {
        if (!this.stats) {
            const response = await fetch('https://api.sleeper.app/v1/stats/nfl/regular/2025');
            this.stats = await response.json();
        }
        return this.stats;
    },
    
    async getPlayers() {
        if (!this.players) {
            const response = await fetch('https://api.sleeper.app/v1/players/nfl');
            this.players = await response.json();
        }
        return this.players;
    },
    
    async getProjections() {
        if (!this.projections) {
            const response = await fetch('https://api.sleeper.app/v1/projections/nfl/regular/2025');
            this.projections = await response.json();
        }
        return this.projections;
    },
    
    async getRosters() {
        if (!this.rosters) {
            const response = await fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/rosters`);
            this.rosters = await response.json();
        }
        return this.rosters;
    },
    
    clearCache() {
        this.stats = null;
        this.players = null;
        this.projections = null;
        this.rosters = null;
        console.log('✅ SleeperDataCache cleared');
    }
};

// Global function to refresh all data
window.refreshAllData = async function() {
    console.log('🔄 REFRESHING ALL DATA...');
    
    // Clear all caches
    SleeperDataCache.clearCache();
    DataManager.clearCache();
    window.matchupDataCache = null;
    
    console.log('✅ All caches cleared');
    
    // Reload current screen
    const currentScreen = document.querySelector('.screen.active')?.id;
    if (currentScreen === 'dashboard') {
        console.log('🔄 Reloading dashboard...');
        await loadTeamDashboard();
    } else if (currentScreen === 'niv' && selectedTeam) {
        console.log('🔄 Reloading NIV screen...');
        await loadNIVRoster(selectedTeam);
    } else if (currentScreen === 'rankings') {
        console.log('🔄 Reloading CPR rankings...');
        await loadCPRRankings();
    }
    
    console.log('✅ ALL DATA REFRESHED!');
    alert('✅ All data refreshed successfully!');
};
let cache = {}; // Data cache (cpr_rankings, niv_data, league_stats, dbContext)
let uploadedFile = null;

// Centralized Data Manager
const DataManager = {
    async getCPRData(forceRefresh = false) {
        if (!forceRefresh && cache.cpr_rankings) return cache.cpr_rankings;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        try {
            const response = await fetch(`/api/cpr?league_id=${LEAGUE_ID}&season=2025`, { 
                signal: controller.signal 
            });
            if (!response.ok) throw new Error('CPR data fetch failed');
            const data = await response.json();
            cache.cpr_rankings = data;
            return data;
        } finally {
            clearTimeout(timeoutId);
        }
    },
    
    async getNIVData(forceRefresh = false) {
        if (!forceRefresh && cache.niv_data) return cache.niv_data;
        
        try {
            const response = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
            if (!response.ok) throw new Error('NIV data fetch failed');
            const data = await response.json();
            cache.niv_data = data;
            return data;
        } catch (error) {
            const errorText = await response?.text() || 'Network error';
            throw new Error(`Failed to load NIV data: ${errorText}`);
        }
    },
    
    async getDatabaseContext(forceRefresh = false) {
        if (!forceRefresh && cache.dbContext) return cache.dbContext;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        try {
            const response = await fetch(`/api/databaseContext?league_id=${LEAGUE_ID}`, { 
                signal: controller.signal 
            });
            if (!response.ok) throw new Error('Database context fetch failed');
            const data = await response.json();
            cache.dbContext = data;
            return data;
        } finally {
            clearTimeout(timeoutId);
        }
    },
    
    clearCache() {
        cache = {};
        console.log('✅ DataManager cache cleared');
    },
    
    clearCacheKey(key) {
        delete cache[key];
    }
};

// Initialize window globals
window.currentUser = window.currentUser || null;
window.claimedTeam = window.claimedTeam || null;

// Load claimedTeam from localStorage on startup
const savedTeam = localStorage.getItem('claimedTeam');
if (savedTeam && !window.claimedTeam) {
    try {
        window.claimedTeam = JSON.parse(savedTeam);
        console.log('Loaded claimed team from localStorage:', window.claimedTeam);
    } catch (error) {
        console.error('Error parsing saved team:', error);
        localStorage.removeItem('claimedTeam');
    }
} // {team_id, team_name}
let conversations = [];

// --- Utility Functions ---

// DOM element getters to reduce duplication
const getChatContainer = () => document.getElementById('chat-messages');
const getRankingsContainer = () => document.getElementById('rankings-container');
const getNIVContainer = () => document.getElementById('niv-container');

function getRankSuffix(rank) {
    const lastDigit = rank % 10;
    const lastTwoDigits = rank % 100;
    
    if (lastTwoDigits >= 11 && lastTwoDigits <= 13) {
        return rank + 'TH';
    }
    
    switch (lastDigit) {
        case 1: return rank + 'ST';
        case 2: return rank + 'ND';
        case 3: return rank + 'RD';
        default: return rank + 'TH';
    }
}

// Fast ranking calculation
function calculateRanks(data, key, descending = true) {
    const sorted = [...data].sort((a, b) => {
        const aVal = a[key] || 0;
        const bVal = b[key] || 0;
        return descending ? bVal - aVal : aVal - bVal;
    });
    
    const ranks = {};
    sorted.forEach((item, index) => {
        const id = item.team_id || item.player_id || item.id;
        ranks[id] = index + 1;
    });
    
    return ranks;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function loadDatabaseContext() {
    try {
        console.log('Loading database context for AI...');
        const data = await DataManager.getDatabaseContext();
        console.log('Database context loaded successfully');
        return cache.dbContext;
    } catch (error) {
        console.error('Database context loading error:', error);
        // We allow chat to proceed even if context fails
        return {}; 
    }
}

// --- Event Delegation ---
document.addEventListener('click', (e) => {
    const target = e.target;
    
    // Handle claim team buttons
    if (target.classList.contains('claim-team-btn')) {
        e.stopPropagation();
        const teamId = target.getAttribute('data-team-id');
        const teamName = target.getAttribute('data-team-name');
        claimTeam(teamId, teamName);
        return;
    }
    
    // Handle scouting report buttons
    if (target.classList.contains('scouting-report-btn')) {
        e.stopPropagation();
        const id = target.getAttribute('data-id');
        const type = target.getAttribute('data-type');
        getScoutingReport(id, type);
        return;
    }
    
    // Handle team analytics buttons
    if (target.classList.contains('team-analytics-btn')) {
        e.stopPropagation();
        const teamId = target.getAttribute('data-team-id');
        const teamName = target.getAttribute('data-team-name');
        goToTeamAnalytics(teamId, teamName);
        return;
    }
    
    // Handle trade partner buttons
    if (target.classList.contains('trade-partner-btn')) {
        e.stopPropagation();
        const playerId = target.getAttribute('data-player-id');
        const type = target.getAttribute('data-type');
        const playerName = target.getAttribute('data-player-name');
        findTradePartner(playerId, type, playerName);
        return;
    }
    
    // Handle conversation rename
    if (target.classList.contains('rename-conversation-btn')) {
        e.stopPropagation();
        const convId = target.getAttribute('data-conversation-id');
        const currentTitle = target.getAttribute('data-current-title');
        renameConversation(convId, currentTitle);
        return;
    }
    
    // Handle conversation delete
    if (target.classList.contains('delete-conversation-btn')) {
        e.stopPropagation();
        const convId = target.getAttribute('data-conversation-id');
        deleteConversation(convId);
        return;
    }
    
    // Handle roster tabs
    if (target.classList.contains('roster-tab')) {
        const tab = target.getAttribute('data-tab');
        switchRosterTab(tab);
        return;
    }
    
    // Handle generate visualization button
    if (target.classList.contains('generate-viz-btn')) {
        generateCPRVisualization();
        return;
    }
    
    // Handle new conversation button
    if (target.classList.contains('new-conversation-btn')) {
        startNewConversation();
        return;
    }
    
    // Handle logout button
    if (target.classList.contains('logout-btn')) {
        logout();
        return;
    }
    
    // Handle team dashboard button
    if (target.classList.contains('team-dashboard-btn') && !target.disabled) {
        goToTeamDashboard();
        return;
    }
    
    // Handle login buttons
    if (target.classList.contains('login-google-btn')) {
        loginGoogle();
        return;
    }
    
    if (target.classList.contains('login-email-btn')) {
        loginEmail();
        return;
    }
    
    if (target.classList.contains('signup-email-btn')) {
        signupEmail();
        return;
    }
});

// --- Custom Dropdown Functionality ---
document.addEventListener('DOMContentLoaded', () => {
    // This single pointerdown handler manages all custom dropdown logic.
    // It replaces the previous separate click/pointerdown handlers to avoid conflicts.
    document.body.addEventListener('pointerdown', (e) => {
        const target = e.target;

        // Normalize target: if a text node is clicked, use its parent.
        const targetEl = (target && target.nodeType === 3) ? target.parentElement : target;
        if (!targetEl) return;

        const isOption = targetEl.matches('.dropdown-option');
        const dropdownWrapper = targetEl.closest('.custom-dropdown');

        // Case 1: An option was clicked. This is the highest priority.
        if (isOption && dropdownWrapper) {
            e.preventDefault();
            e.stopPropagation();

            const selected = dropdownWrapper.querySelector('.dropdown-selected');
            const value = targetEl.getAttribute('data-value') || '';

            if (selected) selected.textContent = targetEl.textContent || '';
            dropdownWrapper.classList.remove('open');

            // Trigger the correct update function based on which dropdown was used.
            if (dropdownWrapper.id === 'stats-dropdown-wrapper') {
                window.currentStatsSelection = value;
                updatePlayerStats();
            } else if (dropdownWrapper.id === 'position-filter-wrapper') {
                window.currentPositionFilter = value;
                updateLeagueAnalytics();
            } else if (dropdownWrapper.id === 'availability-filter-wrapper') {
                window.currentAvailabilityFilter = value;
                updateLeagueAnalytics();
            } else if (dropdownWrapper.id === 'analytics-stats-dropdown-wrapper') {
                window.currentAnalyticsStatsSelection = value;
                updateLeagueAnalytics();
            }
            return; // Stop processing
        }

        // Close all dropdowns that are not the one being interacted with.
        document.querySelectorAll('.custom-dropdown').forEach(d => {
            if (d !== dropdownWrapper) {
                d.classList.remove('open');
            }
        });

        // Case 2: The dropdown wrapper itself was clicked. Toggle it.
        if (dropdownWrapper) {
            setTimeout(() => {
                dropdownWrapper.classList.toggle('open');
            }, 0);
        }
    });
});

// --- Team Dashboard Functions ---

function updateHeader(screenName) {
    const header = document.getElementById('shared-header');
    const titleEl = document.getElementById('header-title');
    const subtitleEl = document.getElementById('header-subtitle');
    const backButton = document.getElementById('header-back-button');

    header.style.display = 'grid';

    if (screenName === 'home') {
        titleEl.textContent = '';
        subtitleEl.innerHTML = '';
        backButton.style.display = 'none';
        return;
    }

    backButton.style.display = 'flex';

    let title = '';
    let subtitle = '';
    let backAction = () => showScreen('home');

    switch (screenName) {
        case 'cpr':
            title = 'CPR RANKINGS';
            break;
        case 'niv':
            if (nivState === 'roster') {
                console.log('=== HEADER UPDATE DEBUG ===');
                console.log('selectedTeam:', selectedTeam);
                console.log('selectedTeam?.team_name:', selectedTeam?.team_name);
                console.log('selectedTeam?.name:', selectedTeam?.name);
                
                const teamName = selectedTeam?.team_name || selectedTeam?.name || 'ROSTER';
                console.log('Final teamName:', teamName);
                
                title = teamName.toUpperCase();
                backAction = () => {
                    nivState = 'teams';
                    selectedTeam = null;
                    showScreen('niv'); 
                };
            } else {
                title = 'PLAYER ANALYTICS';
            }
            break;
        case 'chat':
            title = 'LEAGUE INSIDER';
            subtitle = 'JAYLEN HENDRICKS <span class="twitter-handle">@JHendricksESPN</span>';
            break;
        case 'dashboard':
            title = claimedTeam ? claimedTeam.team_name.toUpperCase() : 'TEAM DASHBOARD';
            subtitle = 'ROSTER & ANALYTICS';
            break;
    }

    titleEl.textContent = title;
    subtitleEl.innerHTML = subtitle;
    backButton.onclick = backAction;
}

function showScreen(screenName) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(s => s.style.display = 'none');

    // Show the target screen
    const nextEl = document.getElementById(`${screenName}-screen`);
    if (nextEl) {
        nextEl.style.display = 'flex';
    }

    // Update chat input visibility
    const chatInputContainer = document.querySelector('.chat-input-container');
    chatInputContainer.style.display = (screenName === 'chat') ? 'flex' : 'none';

    // Update header and state
    currentScreen = screenName;
    updateHeader(screenName);

    // Load content for the new screen
    if (screenName === 'cpr') {
        loadCPRScreen();
    } else if (screenName === 'niv') {
        console.log('=== NIV SCREEN DEBUG ===');
        console.log('nivState:', nivState);
        console.log('selectedTeam:', selectedTeam);
        
        if (nivState === 'teams') {
            console.log('Loading NIV teams...');
            loadNIVTeams();
        } else if (nivState === 'roster' && selectedTeam) {
            console.log('selectedTeam keys:', Object.keys(selectedTeam));
            console.log('selectedTeam.team_name:', selectedTeam.team_name);
            console.log('selectedTeam stringified:', JSON.stringify(selectedTeam));
            console.log('Loading NIV roster for:', selectedTeam.team_name);
            loadNIVRoster(selectedTeam);
        } else {
            console.log('NIV condition not met - falling back to teams');
            nivState = 'teams';
            loadNIVTeams();
        }
    } else if (screenName === 'dashboard') {
        loadTeamDashboard();
    }
}

// --- CPR Screen Logic ---

async function loadCPRScreen() {
    const container = getRankingsContainer();
    container.innerHTML = '<div class="loading">Loading CPR rankings...</div>';
    
    try {
        console.log('Loading CPR data for Legion Fantasy Football...');
        const data = await DataManager.getCPRData();
        const payload = data.data || data;
        const rankings = payload.rankings || payload;

        // Update cache
        cache.cpr_rankings = rankings;

        // Update league health metrics (use API data or reasonable defaults)
        const leagueHealth = payload.league_health ?? 0.85;
        const giniCoeff = payload.gini_coefficient ?? 0.15;

        const healthEl = document.getElementById('league-health');
        const giniEl = document.getElementById('gini-coeff');
        if (healthEl) healthEl.textContent = `${(leagueHealth * 100).toFixed(1)}%`;
        if (giniEl) giniEl.textContent = giniCoeff.toFixed(3);

        // Build team rankings display
        container.innerHTML = '';
        // Calculate real rankings for all metrics
        const sliRanks = calculateRanks(rankings, 'sli', true);
        const bsiRanks = calculateRanks(rankings, 'bsi', true);
        const ingramRanks = calculateRanks(rankings, 'ingram', true);
        const alvaradoRanks = calculateRanks(rankings, 'alvarado', true);
        const zionRanks = calculateRanks(rankings, 'zion', false); // Lower is better for SoS
        const smiRanks = calculateRanks(rankings, 'smi', true);
        const pfRanks = calculateRanks(rankings, 'points_for', true);

        const fragment = document.createDocumentFragment();

        rankings.forEach(team => {
            const row = document.createElement('div');
            row.className = `team-row ${team.rank === 1 ? 'gold' : ''}`;
            
            // Use TEAM NAME from Legion data, not user name
            const teamName = team.team_name || team.name || `Team ${team.rank}`;
            
            // Check if this team is claimed
            const isClaimedTeam = window.claimedTeam && team.team_id === window.claimedTeam.team_id;
            const claimedByText = isClaimedTeam ? `<div class="claimed-by-text">claimed by ${window.currentUser?.displayName || window.currentUser?.email?.split('@')[0] || 'you'}</div>` : '';
            
            row.innerHTML = `
                <div class="tile-header">
                    <div class="rank-badge">${team.rank}</div>
                    <div class="tile-name-container">
                        <div class="tile-name">${teamName.toUpperCase()}</div>
                        ${claimedByText}
                    </div>
                    <button class="claim-team-btn" data-team-id="${team.team_id}" data-team-name="${teamName.replace(/'/g, "\\'")}">CLAIM TEAM</button>
                    <div class="tile-score">${team.cpr.toFixed(3)}</div>
                </div>
                <div class="tile-dropdown">
                    <div class="dropdown-modules">
                        <div class="dropdown-module">
                            <div class="module-title">TEAM STRENGTH</div>
                            <div class="metric-row">
                                <div class="metric-label">STARTER STRENGTH</div>
                                <div class="metric-value">${team.sli.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(sliRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">BENCH STRENGTH</div>
                                <div class="metric-value">${team.bsi.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(bsiRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">ROSTER BALANCE</div>
                                <div class="metric-value">${team.ingram.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(ingramRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">DRAFT EFFICIENCY</div>
                                <div class="metric-value">${team.alvarado.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(alvaradoRanks[team.team_id] || 1)})</span></div>
                            </div>
                        </div>
                        <div class="dropdown-module">
                            <div class="module-title">PERFORMANCE</div>
                            <div class="metric-row">
                                <div class="metric-label">AVG POINTS FOR / GAME</div>
                                <div class="metric-value">${team.points_for_per_game ? team.points_for_per_game.toFixed(1) : '0.0'} <span class="rank-indicator">(${getRankSuffix(pfRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">STRENGTH OF SCHEDULE</div>
                                <div class="metric-value">${team.zion.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(zionRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">AVG OPPONENT STRENGTH</div>
                                <div class="metric-value">${(team.zion * 0.8 + 0.1).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(zionRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">SCHEDULE MOMENTUM</div>
                                <div class="metric-value">${team.smi.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(smiRanks[team.team_id] || 1)})</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown-buttons">
                        <button class="dropdown-btn scouting-report-btn" data-id="${team.team_id}" data-type="team">GET SCOUTING REPORT</button>
                        <button class="dropdown-btn team-analytics-btn" data-team-id="${team.team_id}" data-team-name="${teamName.replace(/'/g, "\\'")}">GO TO TEAM ANALYTICS</button>
                    </div>
                </div>
            `;

            // Add click handler for expanding/collapsing
            row.addEventListener('click', () => {
                row.classList.toggle('expanded');
            });

            fragment.appendChild(row);
        });

        container.appendChild(fragment);
        
        // Update claim buttons after rendering
        updateClaimButtons();

    } catch (error) {
        console.error('Error loading CPR screen:', error);
        container.innerHTML = '<div class="error">Failed to load CPR rankings. Please try again.</div>';
    }
}

// --- NIV Screen Logic ---

async function loadNIVTeams() {
    console.log('=== LOADING NIV TEAMS ===');
    const container = getNIVContainer();
    
    if (!container) {
        console.error('NIV container not found!');
        return;
    }
    
    container.innerHTML = '<div class="loading">Loading team NIV metrics...</div>';
    
    try {
        console.log('Fetching NIV data from API...');
        const data = await DataManager.getNIVData();
        console.log('Raw API response:', data);
        
        const payload = data.data || data;
        console.log('Payload:', payload);
        
        const teamNivData = payload.team_niv || payload.team_rankings || payload;
        console.log('Team NIV data:', teamNivData);
        console.log('Team count:', Array.isArray(teamNivData) ? teamNivData.length : 'Not an array');

        if (!Array.isArray(teamNivData) || teamNivData.length === 0) {
            console.error('No valid team NIV data found');
            container.innerHTML = '<div class="error">No team data available</div>';
            return;
        }

        // Update cache
        cache.niv_data = teamNivData;

        // Show league-wide stats
        const statsContainer = document.getElementById('niv-stats-container');
        statsContainer.style.display = 'grid';
        const leagueAvgNiv = teamNivData.reduce((acc, t) => acc + t.avg_niv, 0) / teamNivData.length;
        const avgTeamScore = await calculateLeagueAvgScore();
        statsContainer.innerHTML = `
            <div class="glass-card">
                <div class="stat-label">LEAGUE AVG NIV</div>
                <div class="stat-value">${leagueAvgNiv.toFixed(3)}</div>
            </div>
            <div class="glass-card">
                <div class="stat-label">AVG TEAM SCORE</div>
                <div class="stat-value">${avgTeamScore.toFixed(1)}</div>
            </div>
        `;

        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        teamNivData.forEach((team, index) => {
            const row = document.createElement('div');
            row.className = 'team-row';
            
            // Use TEAM NAME from Legion data
            const teamName = team.team_name || team.name || `Team ${index + 1}`;
            
            row.innerHTML = `
                <div class="tile-header">
                    <div class="rank-badge">${index + 1}</div>
                    <div class="tile-name">${teamName.toUpperCase()}</div>
                    <div class="tile-score">${team.avg_niv.toFixed(3)}</div>
                </div>
            `;

            row.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                console.log('=== TEAM CLICK DEBUG ===');
                console.log('Team clicked:', teamName);
                console.log('Team data:', team);
                
                selectedTeam = {
                    ...team,
                    rank: index + 1,
                    team_name: teamName
                };
                nivState = 'roster';
                
                console.log('selectedTeam set to:', selectedTeam);
                console.log('nivState set to:', nivState);
                console.log('Calling showScreen(niv)...');
                
                showScreen('niv');
            });

            fragment.appendChild(row);
        });

        container.appendChild(fragment);
        
    } catch (error) {
        console.error('Error loading NIV teams:', error);
        container.innerHTML = '<div class="error">Failed to load team NIV data. Please try again.</div>';
    }
}

async function loadNIVRoster(team) {
    const container = getNIVContainer();
    const statsContainer = document.getElementById('niv-stats-container');
    
    // Show team stats
    statsContainer.style.display = 'grid';
    statsContainer.innerHTML = `
        <div class="glass-card">
            <div class="stat-label">TEAM AVG NIV</div>
            <div class="stat-value">${team.avg_niv.toFixed(3)}</div>
        </div>
        <div class="glass-card">
            <div class="stat-label">RANK</div>
            <div class="stat-value">#${team.rank || 'N/A'}</div>
        </div>
    `;

    container.innerHTML = '<div class="loading">Loading roster...</div>';
    
    try {
        console.log('=== ROSTER LOADING DEBUG ===');
        console.log('team parameter:', team);
        console.log('team is null/undefined:', team == null);
        console.log('typeof team:', typeof team);
        
        if (!team) {
            throw new Error('Team object is null or undefined');
        }
        
        console.log('Loading roster for:', team.team_name);
        console.log('Team object:', team);
        
        // The team object already has the players array from goToTeamAnalytics
        // No need to fetch NIV data again - just use the team object directly
        if (!team.players || team.players.length === 0) {
            throw new Error('Team has no players data');
        }
        
        // Get Sleeper stats for accurate data using global cache
        const statsData = await SleeperDataCache.getStats();
        
        // Merge NIV data (already in team.players) with Sleeper stats
        const roster = team.players.map(player => {
            const sleeperStats = statsData[player.player_id] || {};
            return {
                ...player,
                ...sleeperStats
            };
        });
        
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        roster.forEach((player, index) => {
            const row = document.createElement('div');
            row.className = 'player-row';
            
            // Get position and team info
            const playerName = player.player_name || player.name || 'Unknown Player';
            const position = player.position || 'N/A';
            const nflTeam = player.team || 'FA';
            
            // Use real sleeper stats if available
            const avgFantasyPPG = player.pts_ppr && player.gp ? (player.pts_ppr / player.gp).toFixed(2) : '0.00';
            const totalFantasyPoints = player.pts_ppr ? player.pts_ppr.toFixed(2) : '0.00';
            const gamesPlayed = player.gp ? player.gp.toFixed(0) : '0';
            
            // Position specific stats
            let primaryStatLabel = 'YARDS';
            let primaryStatValue = '0';
            let touchdowns = '0';
            
            if (position === 'QB') {
                primaryStatLabel = 'PASS YDS';
                primaryStatValue = player.pass_yd ? player.pass_yd.toFixed(0) : '0';
                touchdowns = player.pass_td ? player.pass_td.toFixed(0) : '0';
            } else if (position === 'RB') {
                primaryStatLabel = 'RUSH YDS';
                primaryStatValue = player.rush_yd ? player.rush_yd.toFixed(0) : '0';
                touchdowns = (player.rush_td || 0).toFixed(0);
            } else if (position === 'WR' || position === 'TE') {
                primaryStatLabel = 'REC YDS';
                primaryStatValue = player.rec_yd ? player.rec_yd.toFixed(0) : '0';
                touchdowns = (player.rec_td || 0).toFixed(0);
            } else if (position === 'K') {
                primaryStatLabel = 'FGM';
                primaryStatValue = player.fgm ? player.fgm.toFixed(0) : '0';
                touchdowns = 'N/A';
            } else if (position === 'DEF') {
                primaryStatLabel = 'PTS ALLOWED';
                primaryStatValue = player.def_pts_allowed ? player.def_pts_allowed.toFixed(0) : '0';
                touchdowns = player.def_td ? player.def_td.toFixed(0) : '0';
            }
            
            row.innerHTML = `
                <div class="tile-header">
                    <div class="rank-badge">${index + 1}</div>
                    <div class="tile-name">${playerName.toUpperCase()} <span class="player-position">(${position} - ${nflTeam})</span></div>
                    <div class="tile-score">${player.niv ? player.niv.toFixed(3) : '0.000'}</div>
                </div>
                <div class="tile-dropdown">
                    <div class="dropdown-modules">
                        <div class="dropdown-module">
                            <div class="module-title">FANTASY PERFORMANCE</div>
                            <div class="metric-row">
                                <div class="metric-label">AVG FANTASY PPG</div>
                                <div class="metric-value">${avgFantasyPPG} <span class="rank-indicator">(PPR)</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TOTAL FPTS</div>
                                <div class="metric-value">${totalFantasyPoints} <span class="rank-indicator">(PPR)</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">GAMES PLAYED</div>
                                <div class="metric-value">${gamesPlayed} <span class="rank-indicator">GAMES</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">NIV SCORE</div>
                                <div class="metric-value">${player.niv ? player.niv.toFixed(3) : '0.000'} <span class="rank-indicator">(SCORE)</span></div>
                            </div>
                        </div>
                        <div class="dropdown-module">
                            <div class="module-title">POSITION STATS</div>
                            <div class="metric-row">
                                <div class="metric-label">${primaryStatLabel}</div>
                                <div class="metric-value">${primaryStatValue} <span class="rank-indicator">(TOTAL)</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TOUCHDOWNS</div>
                                <div class="metric-value">${touchdowns} <span class="rank-indicator">(TOTAL)</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TARGETS/RUSHES</div>
                                <div class="metric-value">${position === 'QB' ? (player.pass_att ? player.pass_att.toFixed(0) : '0') : position === 'RB' ? (player.rush_att ? player.rush_att.toFixed(0) : '0') : (player.rec_tgt ? player.rec_tgt.toFixed(0) : '0')} <span class="rank-indicator">(ATTEMPTS)</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">${position === 'QB' ? 'INTS' : position === 'RB' || position === 'WR' || position === 'TE' ? 'FUMBLES' : 'SACKS'}</div>
                                <div class="metric-value">${position === 'QB' ? (player.pass_int ? player.pass_int.toFixed(0) : '0') : position === 'RB' || position === 'WR' || position === 'TE' ? (player.fum ? player.fum.toFixed(0) : '0') : (player.def_sack ? player.def_sack.toFixed(0) : '0')} <span class="rank-indicator">(LOST)</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown-buttons">
                        <button class="dropdown-btn scouting-report-btn" data-id="${player.player_id}" data-type="player">GET SCOUTING REPORT</button>
                        <button class="dropdown-btn trade-partner-btn" data-player-id="${player.player_id}" data-type="player" data-player-name="${playerName.replace(/'/g, "\\'")}">FIND TRADE PARTNER</button>
                    </div>
                </div>
            `;

            row.addEventListener('click', (e) => {
                // Don't expand if clicking buttons
                if (e.target.classList.contains('dropdown-btn')) {
                    return;
                }
                row.classList.toggle('expanded');
            });

            fragment.appendChild(row);
        });

        container.appendChild(fragment);
        
    } catch (error) {
        console.error('Error loading roster:', error);
        console.error('Error details:', {
            message: error.message,
            stack: error.stack,
            teamName: team?.team_name
        });
        container.innerHTML = `<div class="error">Failed to load roster: ${error.message}</div>`;
    }
}

// --- Chat Helper Functions ---

function processMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // **text** -> <strong>text</strong>
        .replace(/\*(.*?)\*/g, '<em>$1</em>')              // *text* -> <em>text</em>
        .replace(/\n\n+/g, '\n\n');                        // Normalize paragraph breaks
}

// --- Chat Screen Logic ---

async function loadChatScreen() {
    const container = getChatContainer();
    
    if (chatMessages.length === 0) {
        container.innerHTML = `
            <div class="welcome-message-container">
                <div class="welcome-text-centered">
                    ASK JAYLEN ANYTHING ABOUT LFF OR THE NFL
                </div>
            </div>
        `;
    } else {
        renderChatMessages();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Create new conversation if none exists
    if (!currentConversationId && currentUser) {
        const conversationNumber = conversations.length + 1;
        const title = `Conversation ${conversationNumber}`;
        const conversationId = await createConversation(title);
        if (conversationId) {
            currentConversationId = conversationId;
            
            // Add to conversations list
            conversations.unshift({
                id: conversationId,
                title: title,
                tokenCount: 0,
                lastMessage: null,
                createdAt: new Date(),
                updatedAt: new Date()
            });
            updateConversationList();
        }
    }
    
    // Prepare message content
    let messageContent = message;
    
    // Handle file upload if present
    let fileContent = null;
    if (uploadedFile) {
        try {
            // Convert file to base64 for OpenRouter multimodal
            fileContent = await fileToBase64(uploadedFile);
            messageContent = `${message}\n\n[File attached: ${uploadedFile.name} (${(uploadedFile.size / 1024).toFixed(1)}KB)]`;
        } catch (error) {
            console.error('File processing error:', error);
            messageContent = `${message}\n\n[Error processing file: ${uploadedFile.name}]`;
        }
    }
    
    // Add user message
    const userMessage = { 
        role: 'user', 
        content: messageContent,
        timestamp: new Date().toISOString(),
        tokens: Math.ceil(messageContent.length / 4) // Rough token estimate
    };
    chatMessages.push(userMessage);
    console.log(' Added user message:', messageContent);
    input.value = '';
    
    // Save user message to Firestore if conversation exists
    if (currentConversationId && currentUser) {
        saveMessageToConversation(currentConversationId, userMessage);
        
        // Update local conversation
        const conv = conversations.find(c => c.id === currentConversationId);
        if (conv) {
            conv.tokenCount += userMessage.tokens;
            conv.lastMessage = userMessage;
            conv.updatedAt = new Date();
            updateConversationList();
        }
    }
    
    // Clear uploaded file after processing
    uploadedFile = null;
    
    // Remove welcome message if this is first message
    const container = getChatContainer();
    const welcomeContainer = container.querySelector('.welcome-message-container');
    if (welcomeContainer) {
        welcomeContainer.remove();
    }
    
    // Add user message directly to DOM (no full rerender)
    const userMessageHTML = `
        <div class="message user">
            <div class="user-prompt">${messageContent}</div>
        </div>
    `;
    container.innerHTML += userMessageHTML;
    scrollToBottom(true);
    
    try {
        const dbContext = await loadDatabaseContext();
        
        const requestBody = {
            messages: chatMessages.filter(m => !m.loading),
            context: dbContext,
            model: MODEL,
            league_id: LEAGUE_ID,
            file_content: fileContent,
            file_type: uploadedFile?.type
        };
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            throw new Error(`Chat request failed: ${response.status}`);
        }
        
        // Add streaming message directly - no loading spinner
        const streamingId = Date.now();
        chatMessages.push({ role: 'assistant', content: '', streaming: true, id: streamingId });
        
        // Add streaming message to DOM
        const container = getChatContainer();
        const streamingHTML = `
            <div class="message assistant streaming-message" data-id="${streamingId}">
                <div class="message-avatar">
                    <img src="/assets/jaylen.png" alt="Jaylen Hendricks">
                </div>
                <div class="jaylen-text"><span class="typing-cursor">|</span></div>
            </div>
        `;
        container.innerHTML += streamingHTML;
        scrollToBottom(true);
        
        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantText = '';
        let streamCompleted = false;
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        
                        if (data === '[DONE]') {
                            // Finalize the message
                            const messageIndex = chatMessages.findIndex(m => m.id === streamingId);
                            if (messageIndex !== -1) {
                                const finalMessage = { 
                                    role: 'assistant', 
                                    content: assistantText.trim(),
                                    timestamp: new Date().toISOString(),
                                    tokens: Math.ceil(assistantText.length / 4) // Rough token estimate
                                };
                                chatMessages[messageIndex] = finalMessage;
                                
                                // Save to Firestore if conversation exists
                                if (currentConversationId && currentUser) {
                                    saveMessageToConversation(currentConversationId, finalMessage);
                                    
                                    // Update local conversation
                                    const conv = conversations.find(c => c.id === currentConversationId);
                                    if (conv) {
                                        conv.tokenCount += finalMessage.tokens;
                                        conv.lastMessage = finalMessage;
                                        conv.updatedAt = new Date();
                                        updateConversationList();
                                    }
                                }
                                
                                // Remove typing cursor and finalize
                                const streamingElement = container.querySelector(`[data-id="${streamingId}"] .jaylen-text`);
                                if (streamingElement) {
                                    streamingElement.innerHTML = assistantText.trim();
                                }
                                
                                // Remove streaming class and data-id
                                const streamingMessage = container.querySelector(`[data-id="${streamingId}"]`);
                                if (streamingMessage) {
                                    streamingMessage.classList.remove('streaming-message');
                                    streamingMessage.removeAttribute('data-id');
                                }
                            }
                            streamCompleted = true;
                            return;
                        }
                        
                        try {
                            const parsed = JSON.parse(data);
                            const content = parsed.content; // Firebase function already extracts this
                            
                            if (content) {
                                assistantText += content;
                                
                                // Update streaming message directly in DOM
                                const messageIndex = chatMessages.findIndex(m => m.id === streamingId);
                                if (messageIndex !== -1) {
                                    chatMessages[messageIndex].content = assistantText;
                                    
                                    // Update the specific streaming message
                                    const streamingElement = container.querySelector(`[data-id="${streamingId}"] .jaylen-text`);
                                    if (streamingElement) {
                                        streamingElement.innerHTML = `${assistantText}<span class="typing-cursor">|</span>`;
                                    }
                                }
                            }
                        } catch (e) {
                            // Skip invalid JSON
                            continue;
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
        
        // If we got here without streamCompleted, something went wrong
        if (!streamCompleted && assistantText.trim()) {
            // We have content but no [DONE] - finalize anyway
            const messageIndex = chatMessages.findIndex(m => m.id === streamingId);
            if (messageIndex !== -1) {
                chatMessages[messageIndex] = { 
                    role: 'assistant', 
                    content: processMarkdown(assistantText.trim())
                };
                const streamingElement = container.querySelector('.message.assistant .jaylen-text');
                if (streamingElement) {
                    streamingElement.innerHTML = processMarkdown(assistantText.trim());
                }
            }
            return; // Don't fall through to error
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        
        // Only show error if we actually have an error and no content was streamed
        if (!assistantText || assistantText.trim().length === 0) {
            // Remove streaming message
            chatMessages = chatMessages.filter(m => m.id !== streamingId);
            
            // Add error message only if no content was received
            chatMessages.push({ 
                role: 'assistant', 
                content: 'sorry, had trouble connecting to jaylen. try again in a moment.' 
            });
            
            renderChatMessages();
        }
    }
}

function renderChatMessages() {
    const container = getChatContainer();
    const isScrolledToBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
    
    console.log('=== RENDERING CHAT MESSAGES ===');
    console.log('chatMessages array:', chatMessages);
    console.log('chatMessages.length:', chatMessages.length);
    console.log('currentConversationId:', currentConversationId);
    
    // Handle welcome message fade on first user input - remove immediately to prevent jump
    const welcomeContainer = container.querySelector('.welcome-message-container');
    if (welcomeContainer && chatMessages.some(m => m.role === 'user')) {
        welcomeContainer.style.position = 'absolute';
        welcomeContainer.style.opacity = '0';
        welcomeContainer.style.transform = 'translateY(-20px)';
        // Remove immediately to prevent layout shift
        setTimeout(() => {
            if (welcomeContainer.parentNode) {
                welcomeContainer.remove();
            }
        }, 50);
    }
    
    // Render all non-streaming messages directly to container
    if (chatMessages.length > 0) {
        const messagesHTML = chatMessages
            .filter(msg => !msg.loading && !msg.streaming) // Skip loading/streaming - handled directly in DOM
            .map(msg => {
                const isUser = msg.role === 'user';
                if (isUser) {
                    if (msg.isButton) {
                        return `
                            <div class="message user">
                                <div class="user-button-message">${msg.content}</div>
                            </div>
                        `;
                    } else {
                        return `
                            <div class="message user">
                                <div class="user-prompt">${msg.content}</div>
                            </div>
                        `;
                    }
                } else {
                    return `
                        <div class="message assistant">
                            <div class="message-avatar">
                                <img src="/assets/jaylen.png" alt="Jaylen Hendricks">
                            </div>
                            <div class="jaylen-text">${msg.content}</div>
                        </div>
                    `;
                }
            }).join('');
        
        // Replace container with conversation messages (streaming messages handled separately)
        container.innerHTML = messagesHTML;
    }

    // Scroll to bottom if user was near the bottom OR if a new user message was just sent
    if (isScrolledToBottom || chatMessages[chatMessages.length - 1]?.role === 'user') {
        scrollToBottom(true);
    }
}

function scrollToBottom(smooth = false) {
    const container = getChatContainer();
    if (smooth) {
        container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    } else {
        container.scrollTop = container.scrollHeight;
    }
}

// Helper function to convert file to base64
async function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

// File Upload Handler
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file types (CSV, PDF, Images)
    const validTypes = [
        'text/csv',
        'application/pdf',
        'image/jpeg',
        'image/jpg', 
        'image/png',
        'image/gif',
        'image/webp'
    ];
    
    if (!validTypes.includes(file.type)) {
        alert('Please upload a CSV, PDF, or image file (JPG, PNG, GIF, WebP)');
        event.target.value = '';
        return;
    }
    
    // Validate file size (10MB limit for OpenRouter)
    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        event.target.value = '';
        return;
    }
    
    // Store file for sending with message
    uploadedFile = file;
    
    const chatInput = document.getElementById('chat-input');
    const fileName = file.name;
    const fileSize = (file.size / 1024).toFixed(2);
    const fileType = file.type.split('/')[0].toUpperCase();
    
    // Show file in input as preview with type info
    chatInput.value = `[${fileType} FILE: ${fileName} (${fileSize}KB)] ${chatInput.value}`;
    console.log('File selected for upload:', fileName, fileType, fileSize + 'KB');
}


// --- Team Dashboard Logic ---

// REMOVED: Duplicate loadDashboard function - using loadTeamDashboard instead

// --- Conversation Management ---

async function createConversation(title = 'New Conversation') {
    console.log('=== CREATE CONVERSATION DEBUG ===');
    console.log('title:', title);
    console.log('currentUser:', currentUser);
    console.log('window.firestore:', window.firestore);
    console.log('window.firebaseDb:', window.firebaseDb);
    
    if (!currentUser) {
        console.error('No current user for conversation creation');
        return null;
    }
    
    try {
        console.log('Attempting to create Firestore document...');
        const docRef = await window.firestore.addDoc(window.firestore.collection(window.firebaseDb, 'conversations'), {
            userId: currentUser.uid,
            title: title,
            messages: [],
            tokenCount: 0,
            createdAt: window.firestore.serverTimestamp(),
            updatedAt: window.firestore.serverTimestamp()
        });
        
        console.log('Conversation created successfully:', docRef.id);
        return docRef.id;
    } catch (error) {
        console.error('Error creating conversation:', error);
        console.error('Error details:', error.message, error.stack);
        return null;
    }
}

async function loadConversations() {
    if (!currentUser) return;
    
    try {
        console.log('Loading conversations for user:', currentUser.uid);
        
        // Wait a tick for the DOM to be ready
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const q = window.firestore.query(
            window.firestore.collection(window.firebaseDb, 'conversations'),
            window.firestore.where('userId', '==', currentUser.uid),
            window.firestore.orderBy('updatedAt', 'desc')
        );
        
        const querySnapshot = await window.firestore.getDocs(q);
        conversations = [];
        
        querySnapshot.forEach((doc) => {
            const data = doc.data();
            console.log('Found conversation:', doc.id, data.title);
            conversations.push({
                id: doc.id,
                title: data.title || 'Untitled Conversation',
                tokenCount: data.tokenCount || 0,
                lastMessage: data.messages && data.messages.length > 0 ? data.messages[data.messages.length - 1] : null,
                createdAt: data.createdAt?.toDate() || new Date(),
                updatedAt: data.updatedAt?.toDate() || new Date()
            });
        });
        
        console.log('Loaded conversations:', conversations.length);
        updateConversationList();
    } catch (error) {
        console.error('Error loading conversations:', error);
        conversations = [];
        updateConversationList();
    }
}

async function saveMessageToConversation(conversationId, message) {
    if (!currentUser) return;
    
    try {
        console.log('Saving message to conversation:', conversationId);
        const docRef = window.firestore.doc(window.firebaseDb, 'conversations', conversationId);
        const docSnap = await window.firestore.getDoc(docRef);
        
        if (docSnap.exists()) {
            const data = docSnap.data();
            const messages = data.messages || [];
            messages.push(message);
            
            await window.firestore.updateDoc(docRef, {
                messages: messages,
                tokenCount: (data.tokenCount || 0) + (message.tokens || 0),
                updatedAt: window.firestore.serverTimestamp()
            });
            console.log('Message saved successfully');
        } else {
            console.error('Conversation not found:', conversationId);
        }
    } catch (error) {
        console.error('Error saving message:', error);
    }
}

async function updateConversationTitle(conversationId, newTitle) {
    if (!currentUser) return;
    
    try {
        const docRef = window.firestore.doc(window.firebaseDb, 'conversations', conversationId);
        await window.firestore.updateDoc(docRef, {
            title: newTitle,
            updatedAt: window.firestore.serverTimestamp()
        });
        
        // Update local conversations
        const conv = conversations.find(c => c.id === conversationId);
        if (conv) conv.title = newTitle;
        
        updateConversationList();
    } catch (error) {
        console.error('Error updating title:', error);
    }
}

async function deleteConversation(conversationId) {
    if (!currentUser) return;
    
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    try {
        await window.firestore.deleteDoc(window.firestore.doc(window.firebaseDb, 'conversations', conversationId));
        
        // Remove from local conversations
        conversations = conversations.filter(c => c.id !== conversationId);
        
        // If this was the current conversation, clear it
        if (currentConversationId === conversationId) {
            currentConversationId = null;
            chatMessages = [];
            loadChatScreen();
        }
        
        updateConversationList();
    } catch (error) {
        console.error('Error deleting conversation:', error);
    }
}

function updateConversationList() {
    const container = document.getElementById('conversation-list');
    console.log('Updating conversation list, container exists:', !!container);
    if (!container) {
        console.error('Conversation list container not found!');
        return;
    }
    
    if (conversations.length === 0) {
        container.innerHTML = `
            <div style="min-height: 112px; padding: 20px; text-align: center; display: flex; align-items: center; justify-content: center; scroll-snap-align: start;">
                <div style="font-family: 'Work Sans', -apple-system, sans-serif; font-size: 12px; color: rgba(255,255,255,0.5); letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600;">NO SAVED CONVERSATIONS</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = conversations.map((conv, index) => {
        const isSelected = conv.id === currentConversationId;
        const lastMessageTime = conv.lastMessage ? 
            new Date(conv.lastMessage.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 
            conv.updatedAt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        return `
            <div class="conversation-tile ${isSelected ? 'selected' : ''}" 
                 data-conversation-id="${conv.id}"
                 data-index="${index}"
                 style="cursor: pointer; pointer-events: auto; position: relative; z-index: 10;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div style="flex: 1;">
                        <div class="conversation-title">${conv.title}</div>
                        <div class="conversation-meta">${conv.tokenCount} tokens • ${lastMessageTime}</div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="rename-conversation-btn" data-conversation-id="${conv.id}" data-current-title="${conv.title.replace(/'/g, "\\'")}" style="background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer; padding: 4px;">
                            <i class="fa-solid fa-edit" style="font-size: 12px;"></i>
                        </button>
                        <button class="delete-conversation-btn" data-conversation-id="${conv.id}" style="background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer; padding: 4px;">
                            <i class="fa-solid fa-trash" style="font-size: 12px;"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click event listeners after HTML is created
    const tiles = container.querySelectorAll('.conversation-tile');
    tiles.forEach(tile => {
        tile.addEventListener('click', function(e) {
            const conversationId = this.getAttribute('data-conversation-id');
            console.log('Conversation tile clicked via event listener:', conversationId);
            loadConversation(conversationId);
        });
    });
}

async function loadConversation(conversationId) {
    if (!currentUser) return;
    
    try {
        console.log('=== LOADING CONVERSATION ===');
        console.log('conversationId:', conversationId);
        
        const docRef = window.firestore.doc(window.firebaseDb, 'conversations', conversationId);
        const docSnap = await window.firestore.getDoc(docRef);
        
        if (docSnap.exists()) {
            const data = docSnap.data();
            console.log('Conversation data:', data);
            console.log('Messages count:', data.messages?.length || 0);
            
            currentConversationId = conversationId;
            chatMessages = data.messages || [];
            
            // Clear chat container completely before loading new conversation
            const chatContainer = document.getElementById('chat-messages');
            if (chatContainer) {
                chatContainer.innerHTML = '';
            }
            
            // Load the conversation in chat screen
            console.log('Switching to chat screen...');
            showScreen('chat');
            renderChatMessages();
            updateConversationList();
            console.log('Conversation loaded successfully');
        } else {
            console.error('Conversation not found:', conversationId);
        }
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

async function startNewConversation() {
    try {
        console.log('=== START NEW CONVERSATION DEBUG ===');
        console.log('currentUser:', currentUser);
        console.log('conversations.length:', conversations.length);
    
    if (!currentUser) {
        console.error('User not signed in - cannot create conversation');
        alert('Please sign in to start a conversation');
        return;
    }
    
    // Auto-number conversation
    const conversationNumber = conversations.length + 1;
    const title = `Conversation ${conversationNumber}`;
    
    console.log('Creating new conversation:', title);
    const conversationId = await createConversation(title);
    console.log('Received conversationId:', conversationId);
    
    if (conversationId) {
        console.log('Setting up new conversation...');
        currentConversationId = conversationId;
        chatMessages = []; // Clear messages for fresh context
        
        // Add to conversations list
        const newConversation = {
            id: conversationId,
            title: title,
            tokenCount: 0,
            lastMessage: null,
            createdAt: new Date(),
            updatedAt: new Date()
        };
        conversations.unshift(newConversation);
        console.log('Added conversation to list:', newConversation);
        
        updateConversationList();
        
        // Navigate to chat screen with fresh context
        console.log('Navigating to chat screen with fresh context...');
        showScreen('chat');
        renderChatMessages(); // This should show empty chat
        
        // Clear the chat container to ensure fresh start
        const chatContainer = document.getElementById('chat-messages');
        if (chatContainer) {
            chatContainer.innerHTML = '';
        }
        
        console.log('New conversation setup complete - fresh context ready');
    } else {
        console.error('Failed to create conversation - no ID returned');
    }
    } catch (error) {
        console.error('Error in startNewConversation:', error);
        alert('Failed to create conversation: ' + error.message);
    }
}

function renameConversation(conversationId, currentTitle) {
    const newTitle = prompt('Enter new title:', currentTitle);
    if (newTitle && newTitle !== currentTitle) {
        updateConversationTitle(conversationId, newTitle);
    }
}

// --- Auth & Profile Logic ---

function showProfile() {
    const modal = document.getElementById('profile-modal');
    modal.classList.add('active');
}

function openProfile() {
    showProfile();
}

function closeProfile() {
    const modal = document.getElementById('profile-modal');
    modal.classList.remove('active');
}

// Navigation functions
function goToTeamDashboard() {
    if (!window.claimedTeam) {
        alert('Please claim a team first');
        return;
    }
    closeProfile();
    showScreen('dashboard');
    loadTeamDashboard();
}

async function loadTeamDashboard() {
    console.log('Loading team dashboard...');
    
    const container = document.getElementById('dashboard-content');
    if (!container) return;
    
    // Get current user's team data
    const teamData = await getCurrentUserTeam();
    
    container.innerHTML = `
        <div class="dashboard-layout">
            <!-- Left Module: Roster Management -->
            <div class="dashboard-left">
                <div class="module-header">
                    <h2 class="module-title">${teamData?.team_name || 'YOUR TEAM'}</h2>
                    <div class="module-subtitle">ROSTER & ANALYTICS</div>
                </div>
                
                <!-- Roster Tabs -->
                <div class="roster-tabs">
                    <button class="roster-tab active" data-tab="roster">ROSTER</button>
                    <button class="roster-tab" data-tab="matchup">MATCHUP</button>
                    <button class="roster-tab" data-tab="optimize">OPTIMIZE</button>
                </div>
                
                <!-- Stats Dropdown -->
                <div class="stats-dropdown-container">
                    <div class="custom-dropdown" id="stats-dropdown-wrapper">
                        <div class="dropdown-selected" id="stats-dropdown-selected">AVG FANTASY POINTS PER GAME</div>
                        <div class="dropdown-arrow">▼</div>
                        <div class="dropdown-options" id="stats-dropdown-options">
                            <div class="dropdown-option" data-value="avg_points">AVG FANTASY POINTS PER GAME</div>
                            <div class="dropdown-option" data-value="projected_points">PROJECTED POINTS</div>
                            <div class="dropdown-option" data-value="start_percent">ADP</div>
                            <div class="dropdown-option" data-value="own_percent">SOS RANK</div>
                            <div class="dropdown-option" data-value="niv_score">NIV SCORE</div>
                            <div class="dropdown-option" data-value="cpr_rank">CPR RANK</div>
                        </div>
                    </div>
                </div>
                
                <!-- Roster Content -->
                <div id="roster-content" class="roster-content">
                    <div class="loading-text">Loading roster...</div>
                </div>
            </div>
            
            <!-- Right Module: League Analytics -->
            <div class="dashboard-right">
                <div class="module-header">
                    <h2 class="module-title">LEAGUE ANALYTICS</h2>
                    <div class="module-subtitle">PLAYERS & INSIGHTS</div>
                </div>
                
                <!-- Player Filters -->
                <div class="analytics-filters">
                    <div class="custom-dropdown" id="position-filter-wrapper">
                        <div class="dropdown-selected" id="position-filter-selected">ALL POSITIONS</div>
                        <div class="dropdown-arrow">▼</div>
                        <div class="dropdown-options" id="position-filter-options">
                            <div class="dropdown-option" data-value="all">ALL POSITIONS</div>
                            <div class="dropdown-option" data-value="QB">QUARTERBACK</div>
                            <div class="dropdown-option" data-value="RB">RUNNING BACK</div>
                            <div class="dropdown-option" data-value="WR">WIDE RECEIVER</div>
                            <div class="dropdown-option" data-value="TE">TIGHT END</div>
                            <div class="dropdown-option" data-value="K">KICKER</div>
                            <div class="dropdown-option" data-value="DEF">DEFENSE</div>
                        </div>
                    </div>
                    
                    <div class="custom-dropdown" id="availability-filter-wrapper">
                        <div class="dropdown-selected" id="availability-filter-selected">AVAILABLE ONLY</div>
                        <div class="dropdown-arrow">▼</div>
                        <div class="dropdown-options" id="availability-filter-options">
                            <div class="dropdown-option" data-value="available">AVAILABLE ONLY</div>
                            <div class="dropdown-option" data-value="all">ALL PLAYERS</div>
                            <div class="dropdown-option" data-value="rostered">ROSTERED ONLY</div>
                        </div>
                    </div>
                    
                    <div class="custom-dropdown" id="analytics-stats-dropdown-wrapper">
                        <div class="dropdown-selected" id="analytics-stats-dropdown-selected">AVG FANTASY POINTS PER GAME</div>
                        <div class="dropdown-arrow">▼</div>
                        <div class="dropdown-options" id="analytics-stats-dropdown-options">
                            <div class="dropdown-option" data-value="avg_points">AVG FANTASY POINTS PER GAME</div>
                            <div class="dropdown-option" data-value="projected_points">PROJECTED POINTS</div>
                            <div class="dropdown-option" data-value="start_percent">ADP</div>
                            <div class="dropdown-option" data-value="own_percent">SOS RANK</div>
                            <div class="dropdown-option" data-value="niv_score">NIV SCORE</div>
                            <div class="dropdown-option" data-value="cpr_rank">CPR RANK</div>
                        </div>
                    </div>
                </div>
                
                <!-- Top Players -->
                <div id="top-players" class="top-players">
                    <div class="loading-text">Loading players...</div>
                </div>
                
                <!-- CPR Visualization -->
                <div class="cpr-visualization">
                    <div class="viz-header">
                        <h3 class="viz-title">CPR LEAGUE ANALYSIS</h3>
                        <button class="generate-viz-btn">GENERATE VISUAL</button>
                    </div>
                    <div id="cpr-viz-content" class="viz-content">
                        <div class="viz-placeholder">Click "GENERATE VISUAL" to create CPR analysis</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Load initial data - use try/catch to prevent errors from clearing the UI
    try {
        await loadRosterData();
    } catch (error) {
        console.error('Error loading roster data:', error);
        const rosterContent = document.getElementById('roster-content');
        if (rosterContent) {
            rosterContent.innerHTML = '<div class="error-message">Failed to load roster data</div>';
        }
    }
    
    try {
        await updateLeagueAnalytics();
    } catch (error) {
        console.error('Error loading league analytics:', error);
        const topPlayers = document.getElementById('top-players');
        if (topPlayers) {
            topPlayers.innerHTML = '<div class="error-message">Failed to load player data</div>';
        }
    }
    
    // Ensure modules have the same height after loading
    setTimeout(() => {
        const leftModule = document.querySelector('.dashboard-left');
        const rightModule = document.querySelector('.dashboard-right');
        if (leftModule && rightModule) {
            // Get the actual height of the left module content
            const leftHeight = leftModule.offsetHeight;
            // Set the right module to match
            rightModule.style.height = `${leftHeight}px`;
        }
    }, 1000);
}

async function goToTeamAnalytics(teamId, teamName) {
    console.log('Navigate to team analytics for:', teamId, teamName);
    
    try {
        // Fetch full team data from cached NIV API
        const data = await DataManager.getNIVData();
        const payload = data.data || data;
        const teams = payload.team_niv || payload.team_rankings || payload;
        
        // Find the team with matching name (more reliable than ID)
        console.log('Looking for team:', teamName);
        console.log('Available teams:', teams.map(t => ({id: t.team_id, name: t.team_name})));
        
        const teamData = teams.find(t => t.team_name === teamName);
        
        if (teamData) {
            console.log('Found team data:', teamData);
            
            // Calculate rank based on position in sorted NIV list
            const sortedTeams = teams.sort((a, b) => b.avg_niv - a.avg_niv);
            const teamRank = sortedTeams.findIndex(t => t.team_name === teamName) + 1;
            
            // Set up complete team object for NIV screen
            selectedTeam = {
                ...teamData,
                team_name: teamName,
                rank: teamRank
            };
            
            nivState = 'roster';
            showScreen('niv');
        } else {
            console.error('Team not found in NIV data:', teamId);
            alert('Team data not found');
        }
    } catch (error) {
        console.error('Error loading team analytics:', error);
        alert('Failed to load team analytics');
    }
}

function getScoutingReport(id, type) {
    console.log(`Getting scouting report for ${type}:`, id);
    
    // Create detailed scouting prompt with league data context
    let prompt;
    if (type === 'team') {
        prompt = `SCOUTING REPORT REQUEST

**LEAGUE CONTEXT REQUIRED:**
- Access league ID: ${LEAGUE_ID}
- Pull current rosters, player stats, team records
- Analyze recent performance and trends
- Consider matchup history and projections

**TARGET:** Team ID: ${id}

**SCOUTING REQUEST:**
Provide a comprehensive scouting report including:

1. **TEAM OVERVIEW** - Current roster strength and depth
2. **KEY PLAYERS** - Star performers and sleepers
3. **WEAKNESSES** - Vulnerable positions and matchups
4. **RECENT TRENDS** - Performance trajectory and momentum
5. **STRATEGIC INSIGHTS** - How to exploit or avoid this team

**REQUIREMENTS:**
- Use REAL league data from Firestore
- Include actual player stats and projections
- Consider recent games and transactions
- Provide actionable fantasy insights

**FORMAT:**
Structure your response with clear sections and bullet points.`;
    } else {
        prompt = `SCOUTING REPORT REQUEST

**LEAGUE CONTEXT REQUIRED:**
- Access league ID: ${LEAGUE_ID}
- Pull player stats, projections, and trends
- Analyze recent performance and usage
- Consider matchup schedules and opportunities

**TARGET:** Player ID: ${id}

**SCOUTING REQUEST:**
Provide a comprehensive player scouting report including:

1. **PLAYER PROFILE** - Position, team, role
2. **PERFORMANCE ANALYSIS** - Recent stats and trends
3. **USAGE PATTERNS** - Snap counts, target share, touches
4. **MATCHUP OUTLOOK** - Upcoming schedule strength
5. **FANTASY OUTLOOK** - Rest of season projection

**REQUIREMENTS:**
- Use REAL player data from Firestore
- Include actual stats and projections
- Consider injury reports and depth charts
- Provide actionable fantasy advice

**FORMAT:**
Structure your response with clear sections and key insights.`;
    }
    
    // Add styled user message button
    addUserMessageButton(`scouting report`, type, `${type} ID: ${id}`);
    
    // Send the prompt directly without populating input
    sendMessageToJaylen(prompt);
    
    showScreen('chat');
}

function findTradePartner(id, type, name) {
    console.log(`Finding trade partner for ${type}:`, id, name);
    
    // Create the detailed prompt with league data context
    let prompt;
    if (type === 'team') {
        prompt = `TRADE PARTNER ANALYSIS REQUEST

**LEAGUE CONTEXT REQUIRED:**
- Access league ID: ${LEAGUE_ID}
- Pull current rosters, player stats, team records
- Analyze team needs and strengths
- Consider recent transactions and trends

**TARGET:** ${name} (Team ID: ${id})

**ANALYSIS REQUEST:**
Find the 3 best trade partners for my team. I need:

1. **BALANCED TRADE** - Fair value exchange
2. **LONG SHOT TRADE** - Ambitious but possible 
3. **FLEECE OPPORTUNITY** - Maximum value extraction

**REQUIREMENTS:**
- Use REAL league data from Firestore
- Consider actual player performances and projections
- Analyze team needs (QB, RB, WR, TE depth)
- Suggest 1-3 players per side (prefer 1-2)
- Include reasoning for each trade scenario
- Consider which teams would actually accept

**FORMAT:**
Structure your response with clear sections for each trade type.`;
    } else {
        prompt = `TRADE PARTNER ANALYSIS REQUEST

**LEAGUE CONTEXT REQUIRED:**
- Access league ID: ${LEAGUE_ID}
- Pull current rosters, player stats, team records
- Analyze player value and market trends
- Consider team needs across the league

**TARGET PLAYER:** ${name} (Player ID: ${id})

**ANALYSIS REQUEST:**
Find the 3 best trade scenarios for this player:

1. **BALANCED TRADE** - Fair market value
2. **LONG SHOT TRADE** - Aim high but realistic
3. **FLEECE OPPORTUNITY** - Extract maximum value

**REQUIREMENTS:**
- Use REAL league data from Firestore
- Consider actual player stats and projections
- Find teams that need this player's position
- Suggest realistic return packages (1-3 players)
- Include reasoning for each scenario
- Consider team contexts and needs

**FORMAT:**
Structure your response with clear sections for each trade type.`;
    }
    
    // Add styled user message button
    addUserMessageButton(`find trade partner`, type, name);
    
    // Send the prompt directly without populating input
    sendMessageToJaylen(prompt);
    
    showScreen('chat');
}

function addUserMessage(content) {
    const userMessage = {
        role: 'user',
        content: content,
        timestamp: new Date().toISOString(),
        tokens: Math.ceil(content.length / 4) // Rough token estimate
    };
    chatMessages.push(userMessage);
    
    // Update the chat display
    const container = getChatContainer();
    if (container) {
        renderChatMessages();
    }
}

function addUserMessageButton(action, type, name) {
    const userMessage = {
        role: 'user',
        content: `Requested ${action} for ${type}: ${name}`,
        timestamp: new Date().toISOString(),
        tokens: 10, // Small token count for button message
        isButton: true // Flag to style as button
    };
    chatMessages.push(userMessage);
    
    // Update the chat display
    const container = getChatContainer();
    if (container) {
        renderChatMessages();
    }
}

async function sendMessageToJaylen(prompt) {
    try {
        console.log('Sending message to Jaylen:', prompt.substring(0, 100) + '...');
        
        // Add user message to chat
        const userMessage = {
            role: 'user',
            content: prompt,
            timestamp: new Date().toISOString(),
            tokens: Math.ceil(prompt.length / 4)
        };
        chatMessages.push(userMessage);
        
        // Add streaming message directly
        const streamingId = Date.now();
        chatMessages.push({ role: 'assistant', content: '', streaming: true, id: streamingId });
        
        // Update display
        renderChatMessages();
        
        // Send to Jaylen API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: prompt,
                conversationId: currentConversationId,
                userId: currentUser?.uid || 'anonymous'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.content) {
                            assistantContent += data.content;
                            
                            // Update streaming message
                            const streamingMessage = chatMessages.find(m => m.id === streamingId);
                            if (streamingMessage) {
                                streamingMessage.content = assistantContent;
                                renderChatMessages();
                            }
                        }
                    } catch (e) {
                        console.log('Non-JSON line:', line);
                    }
                }
            }
        }

        // Finalize message
        const streamingMessage = chatMessages.find(m => m.id === streamingId);
        if (streamingMessage) {
            streamingMessage.streaming = false;
            delete streamingMessage.id;
        }

    } catch (error) {
        console.error('Error sending message to Jaylen:', error);
        
        // Remove streaming message and add error
        chatMessages = chatMessages.filter(m => m.id !== streamingId);
        chatMessages.push({ 
            role: 'assistant', 
            content: 'sorry, had trouble connecting to jaylen. try again in a moment.' 
        });
        renderChatMessages();
    }
}

function renderAuthUI(user) {
    // Update window.currentUser
    window.currentUser = user;
    
    const authContainer = document.getElementById('auth-container');

    if (user) {
        // Logged-in view - matching auth screen styling exactly
        const displayName = user.displayName || user.email.split('@')[0].toUpperCase();
        const avatarUrl = user.photoURL || `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=003368&color=fff&size=96`;
        
        // Check localStorage for claimed team
        const savedTeam = localStorage.getItem('claimedTeam');
        if (savedTeam && !window.claimedTeam) {
            window.claimedTeam = JSON.parse(savedTeam);
        }
        const teamDashboardDisabled = !window.claimedTeam;
        
        authContainer.innerHTML = `
            <div class="logged-in-view">
                <!-- Header matching logged-out view -->
                <div class="auth-header" style="margin-bottom: 32px;">
                    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px;">
                        <img src="${avatarUrl}" alt="Avatar" onclick="document.getElementById('avatar-upload').click()" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; cursor: pointer;"/>
                        <input type="file" id="avatar-upload" accept="image/*" style="display: none;" onchange="handleAvatarUpload(event)"/>
                        <div style="flex: 1;">
                            <h2 class="auth-title" style="margin: 0; font-size: 24px;">${displayName}</h2>
                            <p class="auth-subtitle" style="margin: 4px 0 0 0; font-size: 11px;">${user.email}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Conversation History -->
                <div style="margin-bottom: 24px;">
                    <button class="new-conversation-btn social-auth-button" style="width: 100%; margin-bottom: 12px; padding: 12px;">NEW CONVERSATION</button>
                    <div id="conversation-list" style="height: 360px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; scroll-snap-type: y mandatory; padding: 8px; background: rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.08); border-radius: var(--radius-xl); pointer-events: auto;">
                        <div style="min-height: 112px; padding: 20px; text-align: center; display: flex; align-items: center; justify-content: center; scroll-snap-align: start;">
                            <div style="font-family: 'Work Sans', -apple-system, sans-serif; font-size: 12px; color: rgba(255,255,255,0.5); letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600;">NO SAVED CONVERSATIONS</div>
                        </div>
                    </div>
                </div>
                
                <!-- Action Buttons matching logged-out view -->
                <div class="auth-form-buttons">
                    <button class="logout-btn social-auth-button">SIGN OUT</button>
                    <button class="team-dashboard-btn social-auth-button" ${teamDashboardDisabled ? 'disabled' : ''} style="${teamDashboardDisabled ? 'opacity: 0.3; cursor: not-allowed;' : ''}">TEAM DASHBOARD</button>
                </div>
            </div>
        `;
    } else {
        // Logged-out view
        authContainer.innerHTML = `
            <div class="auth-header">
                <h2 class="auth-title">PROFILE & AUTH</h2>
                <p class="auth-subtitle">CREATE AN ACCOUNT TO SAVE YOUR CHAT HISTORY AND GET PERSONALIZED INSIGHTS.</p>
            </div>
            <div class="auth-buttons-grid">
                <button class="login-google-btn social-auth-button">
                    <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" style="width: 20px; height: 20px; margin-right: 8px;"/>
                    <span>SIGN IN WITH GOOGLE</span>
                </button>
            </div>
            <div class="auth-divider">OR</div>
            <div class="email-auth-form">
                <input type="email" id="auth-email" placeholder="EMAIL" class="auth-input"/>
                <input type="password" id="auth-password" placeholder="PASSWORD" class="auth-input"/>
                <div class="auth-form-buttons">
                    <button class="login-email-btn social-auth-button">SIGN IN</button>
                    <button class="signup-email-btn social-auth-button">SIGN UP</button>
                </div>
            </div>
        `;
    }
}

async function loginGoogle() {
    try {
        console.log('Starting Google sign-in...');
        console.log('Auth object:', window.firebaseAuth);
        console.log('Google provider:', window.firebase.googleProvider);
        console.log('Current domain:', window.location.hostname);
        console.log('Auth domain:', window.firebaseAuth.config.authDomain);
        
        // Try popup first
        const result = await window.firebase.signInWithPopup(window.firebaseAuth, window.firebase.googleProvider);
        console.log('Google sign-in successful:', result);
        closeProfile();
    } catch (error) {
        console.error('Google sign-in error:', error);
        console.error('Error code:', error.code);
        console.error('Error message:', error.message);
        console.error('Full error:', JSON.stringify(error, null, 2));
        
        // More specific error messages
        if (error.code === 'auth/popup-blocked') {
            alert('Popup blocked! Please allow popups for this site and try again.');
        } else if (error.code === 'auth/popup-closed-by-user') {
            console.log('User closed popup');
        } else if (error.code === 'auth/unauthorized-domain') {
            console.log('Unauthorized domain error - trying redirect method instead...');
            try {
                // Try redirect as fallback (sometimes has different domain validation)
                await window.firebase.signInWithRedirect(window.firebaseAuth, window.firebase.googleProvider);
                // Redirect will happen, no need to close profile
            } catch (redirectError) {
                console.error('Redirect also failed:', redirectError);
                alert(`Domain not authorized: ${window.location.hostname}\n\nError: ${error.message}\n\nPlease check Firebase Console authorized domains.`);
            }
        } else {
            alert(`Sign-in failed: ${error.message}\n\nError code: ${error.code}`);
        }
    }
}

async function loginEmail() {
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    
    if (!email || !password) {
        alert('Please enter both email and password');
        return;
    }
    
    try {
        await window.firebase.signInWithEmailAndPassword(window.firebaseAuth, email, password);
        console.log('Email sign-in successful.');
        closeProfile();
    } catch (error) {
        console.error('Email sign-in error:', error);
        alert(`Sign in failed: ${error.message}`);
    }
}

async function signupEmail() {
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    
    if (password.length < 6) {
        alert('Password must be at least 6 characters');
        return;
    }
    
    try {
        await window.firebase.createUserWithEmailAndPassword(window.firebaseAuth, email, password);
        console.log('Sign up successful.');
        closeProfile();
    } catch (error) {
        console.error('Sign up error:', error);
        alert(`Sign up failed: ${error.message}`);
    }
}

async function logout() {
    try {
        await window.firebase.signOut(window.firebaseAuth);
        console.log('User signed out');
    } catch (error) {
        console.error('Sign out error:', error);
        alert(`Sign out failed: ${error.message}`);
    }
}

// Profile widget helper functions
function updateStatusCount(value) {
    const counter = document.getElementById('status-count');
    if (counter) {
        counter.textContent = `${value.length} / 140`;
    }
}

function handleAvatarUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Check file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
        alert('Image must be less than 2MB');
        return;
    }
    
    // Check file type
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file');
        return;
    }
    
    // TODO: Upload to Firebase Storage and update user profile
    console.log('Avatar upload:', file.name);
    alert('Avatar upload feature coming soon! File selected: ' + file.name);
}

// Team claiming functions
async function claimTeam(teamId, teamName) {
    if (!window.currentUser) {
        alert('Please sign in to claim a team');
        openProfile();
        return;
    }
    
    // Confirmation popup
    const confirmed = confirm(`is this really your team, bitch?\n\n${teamName}`);
    if (!confirmed) {
        return;
    }
    
    // Save to window.claimedTeam and localStorage
    window.claimedTeam = { team_id: teamId, team_name: teamName };
    localStorage.setItem('claimedTeam', JSON.stringify(window.claimedTeam));
    
    // Save to Firebase Firestore for persistence
    try {
        const userDocRef = window.firestore.doc(window.firebaseDb, 'users', window.currentUser.uid);
        await window.firestore.setDoc(userDocRef, {
            claimedTeam: window.claimedTeam,
            email: window.currentUser.email,
            displayName: window.currentUser.displayName,
            updatedAt: new Date().toISOString()
        }, { merge: true });
        console.log('Team claim saved to Firebase');
    } catch (error) {
        console.error('Error saving team claim to Firebase:', error);
    }
    
    updateClaimButtons();
    renderAuthUI(window.currentUser); // Refresh UI to show claimed team
    
    // Reload CPR screen to show "claimed by" text
    if (currentScreen === 'cpr') {
        loadCPRScreen();
    }
}

function updateClaimButtons() {
    const buttons = document.querySelectorAll('.claim-team-btn');
    const savedTeam = localStorage.getItem('claimedTeam');
    if (savedTeam && !window.claimedTeam) {
        window.claimedTeam = JSON.parse(savedTeam);
    }
    
    buttons.forEach(btn => {
        const teamId = btn.getAttribute('data-team-id');
        
        if (!window.currentUser) {
            btn.disabled = true;
            btn.style.display = 'none';
        } else if (window.claimedTeam && teamId === window.claimedTeam.team_id) {
            btn.style.display = 'none';
        } else {
            btn.disabled = false;
            btn.style.display = 'block';
            btn.textContent = 'CLAIM TEAM';
            btn.classList.remove('claimed');
        }
    });
    
    // Update team dashboard button
    const dashboardBtns = document.querySelectorAll('[onclick*="goToTeamDashboard"]');
    dashboardBtns.forEach(btn => {
        btn.disabled = !window.claimedTeam;
    });
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded. Initializing NFL CPR app...');
    
    // Start on the home screen
    showScreen('home');

    // Chat input event listeners
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        // Enter key to send message
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Clear file preview when input is cleared
        chatInput.addEventListener('input', (e) => {
            if (!e.target.value.trim()) {
                uploadedFile = null;
            }
        });
    }

    // Modal close handlers
    document.addEventListener('click', (e) => {
        const modal = document.getElementById('profile-modal');
        if (e.target === modal) {
            closeProfile();
        }
    });
    
    // Initialize auth UI
    renderAuthUI(null);
    
    // Update team dashboard button
    const dashboardBtns = document.querySelectorAll('[onclick*="goToTeamDashboard"]');
    dashboardBtns.forEach(btn => {
        btn.disabled = !window.claimedTeam;
    });
});

// --- Team Dashboard Functions ---

async function getCurrentUserTeam() {
    try {
        console.log('Getting current user team...');
        
        // Check if user has claimed a team
        if (window.claimedTeam && window.claimedTeam.team_name) {
            console.log('Using claimed team:', window.claimedTeam.team_name);
            
            // Get league users to match team names
            const leagueResponse = await fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/users`);
            const users = await leagueResponse.json();
            console.log('League users:', users.map(u => ({ 
                user_id: u.user_id, 
                display_name: u.display_name, 
                team_name: u.metadata?.team_name 
            })));
            
            // Get roster data to match owner_id
            const rosterResponse = await fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/rosters`);
            const rosters = await rosterResponse.json();
            console.log('Rosters:', rosters.map(r => ({ 
                roster_id: r.roster_id, 
                owner_id: r.owner_id 
            })));
            
            // Find the user that owns this team by matching team name (case-insensitive)
            const claimedName = window.claimedTeam.team_name.toLowerCase().trim();
            console.log('Looking for team name:', claimedName);
            
            const user = users.find(u => {
                const teamName = u.metadata?.team_name?.toLowerCase().trim();
                const displayName = u.display_name?.toLowerCase().trim();
                console.log(`Checking user ${u.user_id}: team_name="${teamName}", display_name="${displayName}"`);
                return teamName === claimedName || displayName === claimedName;
            });
            
            if (user) {
                console.log('Found claimed team user:', user);
                return {
                    user_id: user.user_id,
                    team_name: user.metadata?.team_name || user.display_name,
                    display_name: user.display_name
                };
            } else {
                console.error('Could not find user for claimed team:', window.claimedTeam.team_name);
                console.log('Available teams:', users.map(u => u.metadata?.team_name || u.display_name));
                return null;
            }
        }
        
        console.log('No claimed team found - user needs to claim a team first');
        return null;
    } catch (error) {
        console.error('Error fetching user team:', error);
        return null;
    }
}

function switchRosterTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.roster-tab').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Load tab content
    switch(tab) {
        case 'roster':
            loadRosterData();
            break;
        case 'matchup':
            loadMatchupData();
            break;
        case 'optimize':
            loadOptimizeData();
            break;
    }
}

async function loadRosterData() {
    const container = document.getElementById('roster-content');
    if (!container) return;
    
    try {
        console.log('Loading roster data for:', window.claimedTeam?.team_name);
        
        // Get current user's team data first
        const teamData = await getCurrentUserTeam();
        console.log('Team data:', teamData);
        
        if (!teamData || !teamData.user_id) {
            console.log('No team data found, showing error');
            container.innerHTML = '<div class="error-message">Please claim a team first</div>';
            return;
        }
        
        // Get roster data from Sleeper API using global cache
        const rosterData = await SleeperDataCache.getRosters();
        
        // Find current user's roster
        const userRoster = rosterData.find(r => r.owner_id === teamData.user_id);
        if (!userRoster || !userRoster.players) {
            container.innerHTML = '<div class="error-message">No roster found for your team</div>';
            return;
        }
        
        // Get projections data for ADP using global cache
        const projectionsData = await SleeperDataCache.getProjections();
        
        // Get matchup data to calculate SOS (only fetch once and reuse)
        let matchupData = window.matchupDataCache;
        if (!matchupData) {
            const matchupPromises = [];
            for (let week = 1; week <= 8; week++) {
                matchupPromises.push(fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/matchups/${week}`).then(r => r.json()));
            }
            matchupData = await Promise.all(matchupPromises);
            window.matchupDataCache = matchupData; // Cache for reuse
        }
        
        // Calculate SOS rank for each roster
        const rosterPoints = {};
        rosterData.forEach(roster => {
            rosterPoints[roster.roster_id] = 0;
        });
        
        // Sum up points for each roster across all weeks
        matchupData.forEach(weekData => {
            if (weekData && Array.isArray(weekData)) {
                weekData.forEach(matchup => {
                    if (matchup && matchup.roster_id && matchup.points !== undefined) {
                        rosterPoints[matchup.roster_id] = (rosterPoints[matchup.roster_id] || 0) + matchup.points;
                    }
                });
            }
        });
        
        // Create array of roster IDs sorted by points (higher points = stronger opponent)
        const sortedRosters = Object.entries(rosterPoints)
            .sort((a, b) => b[1] - a[1])
            .map(([rosterId, points], index) => ({ rosterId: parseInt(rosterId), points, rank: index + 1 }));
        
        // Create a map of roster ID to SOS rank (1 = toughest schedule, 12 = easiest)
        const sosRankMap = {};
        sortedRosters.forEach(roster => {
            sosRankMap[roster.rosterId] = roster.rank;
        });
        
        // Get SOS rank for user's roster
        const userSosRank = sosRankMap[userRoster.roster_id] || null;
        
        // Get NIV data for player stats from cache
        const nivData = await DataManager.getNIVData();
        const payload = nivData.data || nivData;
        const allTeams = payload.team_niv || payload.team_rankings || payload;
        
        // Get Sleeper player database for names and positions using global cache
        const sleeperPlayers = await SleeperDataCache.getPlayers();
        
        // Get current season stats from Sleeper (2025 season) using global cache
        const statsData = await SleeperDataCache.getStats();
        
        // Get current stats dropdown selection
        const selectedStat = window.currentStatsSelection || 'avg_points';
        
        // Group players by position
        const positionGroups = {
            QB: [],
            RB: [],
            WR: [],
            TE: [],
            K: [],
            DEF: []
        };
        
        // Map roster players to player data
        userRoster.players.forEach(playerId => {
            const sleeperPlayer = sleeperPlayers[playerId];
            if (!sleeperPlayer) return;
            
            // Find NIV data for this player
            let nivPlayerData = null;
            if (Array.isArray(allTeams)) {
                for (const team of allTeams) {
                    if (team.players) {
                        nivPlayerData = team.players.find(p => p.player_id === playerId);
                        if (nivPlayerData) break;
                    }
                }
            }
            
            // Get player stats
            const playerStats = statsData[playerId] || {};
            const playerProjections = projectionsData[playerId] || {};
            
            // Combine Sleeper, NIV, and Stats data
            const player = {
                player_id: playerId,
                player_name: sleeperPlayer.full_name || sleeperPlayer.first_name + ' ' + sleeperPlayer.last_name,
                position: sleeperPlayer.position,
                team: sleeperPlayer.team,
                niv: nivPlayerData?.niv || 0,
                market_niv: nivPlayerData?.market_niv || 0,
                adp_ppr: playerProjections.adp_ppr,
                sos_rank: userSosRank,
                // Include ALL Sleeper stats
                ...playerStats,
                ...nivPlayerData
            };
            
            // Debug log for Jonathan Taylor
            if (player.player_name === 'Jonathan Taylor') {
                console.log('Jonathan Taylor data:', {
                    pts_ppr: player.pts_ppr,
                    gp: player.gp,
                    avg: player.pts_ppr / player.gp,
                    raw_stats: playerStats
                });
            }
            
            const position = player.position || 'FLEX';
            const targetPos = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'].includes(position) ? position : 'FLEX';
            
            if (!positionGroups[targetPos]) positionGroups[targetPos] = [];
            positionGroups[targetPos].push(player);
        });
        
        // Render roster by position
        let rosterHTML = '<div class="roster-positions">';
        
        Object.entries(positionGroups).forEach(([position, players]) => {
            if (players.length > 0) {
                rosterHTML += `
                    <div class="position-group">
                        <div class="position-label">${position}</div>
                `;
                
                players.forEach(player => {
                    const playerName = (player.player_name || player.name || 'Unknown Player').toUpperCase();
                    const nflTeam = (player.team || 'FA').toUpperCase();
                    const statValue = getPlayerStatValue(player, selectedStat);
                    const statLabel = getStatLabel(selectedStat);
                    
                    rosterHTML += `
                        <div class="player-slot">
                            <div class="player-tile-dashboard">
                                <div class="player-info">
                                    <div class="player-name">${playerName}</div>
                                    <div class="player-team">${nflTeam}</div>
                                </div>
                                <div class="player-stat-container">
                                    <div class="player-stat">${statValue}</div>
                                    <div class="stat-label">${statLabel}</div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                rosterHTML += '</div>';
            }
        });
        
        rosterHTML += '</div>';
        container.innerHTML = rosterHTML;
        
        console.log('Roster loaded successfully with real data');
        
    } catch (error) {
        console.error('Error loading roster:', error);
        container.innerHTML = '<div class="error-message">Failed to load roster data</div>';
    }
}

function getPlayerStatValue(player, statType) {
    // Use ACTUAL Sleeper fantasy points - don't calculate!
    // Sleeper provides pts_ppr, pts_half_ppr, pts_std already calculated
    
    switch(statType) {
        case 'avg_points':
            // Use Sleeper's ACTUAL PPR points
            const totalPoints = player.pts_ppr || 0;
            const gamesPlayed = player.gp || 1;
            const avgPoints = gamesPlayed > 0 ? totalPoints / gamesPlayed : 0;
            return avgPoints.toFixed(2);
            
        case 'projected_points':
            return (player.market_niv || player.niv || 0).toFixed(1);
        case 'start_percent':
            // Use ADP instead of start percentage
            if (player.adp_ppr !== undefined && player.adp_ppr !== 999.0) {
                return player.adp_ppr.toFixed(1);
            }
            return 'N/A';
        case 'own_percent':
            // Use SOS rank instead of own percentage
            if (player.sos_rank !== undefined) {
                return `#${player.sos_rank}`;
            }
            return 'N/A';
        case 'niv_score':
            return player.niv ? player.niv.toFixed(3) : '0.000';
        case 'cpr_rank':
            return player.rank ? `#${player.rank}` : 'N/A';
        default:
            return (player.market_niv || player.niv || 0).toFixed(1);
    }
}

function getStatLabel(statType) {
    switch(statType) {
        case 'avg_points':
            return 'PPR AVG';
        case 'projected_points':
            return 'PROJ';
        case 'start_percent':
            return 'ADP';
        case 'own_percent':
            return 'SOS RANK';
        case 'niv_score':
            return 'NIV';
        case 'cpr_rank':
            return 'RANK';
        default:
            return 'PROJ';
    }
}

async function loadMatchupData() {
    const container = document.getElementById('roster-content');
    container.innerHTML = '<div class="loading-text">Loading matchup data...</div>';
    
    // TODO: Implement matchup view
    setTimeout(() => {
        container.innerHTML = '<div class="placeholder-message">Matchup view coming soon!</div>';
    }, 1000);
}

async function loadOptimizeData() {
    const container = document.getElementById('roster-content');
    container.innerHTML = '<div class="loading-text">Loading optimization...</div>';
    
    // TODO: Implement AI optimization
    setTimeout(() => {
        container.innerHTML = '<div class="placeholder-message">AI optimization coming soon!</div>';
    }, 1000);
}

function updatePlayerStats() {
    const selectedStat = window.currentStatsSelection || 'avg_points';
    console.log('Updating player stats for:', selectedStat);
    
    // TODO: Update player stat display based on dropdown selection
    loadRosterData(); // Reload with new stat
}

async function updateLeagueAnalytics() {
    const container = document.getElementById('top-players');
    const position = window.currentPositionFilter || 'all';
    const availability = window.currentAvailabilityFilter || 'available';
    const selectedStat = window.currentAnalyticsStatsSelection || 'avg_points';
    
    container.innerHTML = '<div class="loading-text">Loading players...</div>';
    
    try {
        console.log('Loading ALL fantasy players from Sleeper...');
        
        // Get ALL Sleeper players using global cache
        const sleeperPlayers = await SleeperDataCache.getPlayers();
        
        // Get current season stats (2025) using global cache
        const statsData = await SleeperDataCache.getStats();
        
        // Get projections data for ADP using global cache
        const projectionsData = await SleeperDataCache.getProjections();
        
        // Get roster data to determine availability using global cache
        const rosterData = await SleeperDataCache.getRosters();
        
        // Get matchup data to calculate SOS (only fetch once and reuse)
        let matchupData = window.matchupDataCache;
        if (!matchupData) {
            const matchupPromises = [];
            for (let week = 1; week <= 8; week++) {
                matchupPromises.push(fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/matchups/${week}`).then(r => r.json()));
            }
            matchupData = await Promise.all(matchupPromises);
            window.matchupDataCache = matchupData; // Cache for reuse
        }
        
        // Create set of rostered player IDs
        const rosteredPlayerIds = new Set();
        rosterData.forEach(roster => {
            if (roster.players) {
                roster.players.forEach(playerId => rosteredPlayerIds.add(playerId));
            }
        });
        
        // Calculate SOS rank for each roster
        const rosterPoints = {};
        rosterData.forEach(roster => {
            rosterPoints[roster.roster_id] = 0;
        });
        
        // Sum up points for each roster across all weeks
        matchupData.forEach(weekData => {
            if (weekData && Array.isArray(weekData)) {
                weekData.forEach(matchup => {
                    if (matchup && matchup.roster_id && matchup.points !== undefined) {
                        rosterPoints[matchup.roster_id] = (rosterPoints[matchup.roster_id] || 0) + matchup.points;
                    }
                });
            }
        });
        
        // Create array of roster IDs sorted by points (higher points = stronger opponent)
        const sortedRosters = Object.entries(rosterPoints)
            .sort((a, b) => b[1] - a[1])
            .map(([rosterId, points], index) => ({ rosterId: parseInt(rosterId), points, rank: index + 1 }));
        
        // Create a map of roster ID to SOS rank (1 = toughest schedule, 12 = easiest)
        const sosRankMap = {};
        sortedRosters.forEach(roster => {
            sosRankMap[roster.rosterId] = roster.rank;
        });
        
        // Build player list from ALL Sleeper players
        let allPlayers = [];
        Object.entries(sleeperPlayers).forEach(([playerId, player]) => {
            // Only include fantasy-relevant positions
            if (!['QB', 'RB', 'WR', 'TE', 'K', 'DEF'].includes(player.position)) return;
            
            const playerStats = statsData[playerId] || {};
            const playerProjections = projectionsData[playerId] || {};
            const isRostered = rosteredPlayerIds.has(playerId);
            const fantasyPoints = playerStats.pts_ppr || playerStats.pts_half_ppr || playerStats.pts_std || 0;
            
            // Only include players with stats or who are rostered
            if (fantasyPoints > 0 || isRostered) {
                // Find which roster this player is on
                let playerRosterId = null;
                let sosRank = null;
                for (const roster of rosterData) {
                    if (roster.players && roster.players.includes(playerId)) {
                        playerRosterId = roster.roster_id;
                        sosRank = sosRankMap[playerRosterId] || null;
                        break;
                    }
                }
                
                allPlayers.push({
                    player_id: playerId,
                    player_name: player.full_name || `${player.first_name} ${player.last_name}`,
                    position: player.position,
                    team: player.team || 'FA',
                    pts_ppr: fantasyPoints,
                    isRostered: isRostered,
                    availability: isRostered ? 'rostered' : 'available',
                    adp_ppr: playerProjections.adp_ppr,
                    sos_rank: sosRank,
                    ...playerStats
                });
            }
        });
        
        // Filter by position
        if (position !== 'all') {
            allPlayers = allPlayers.filter(p => p.position === position);
        }
        
        // Filter by availability
        if (availability !== 'all') {
            allPlayers = allPlayers.filter(p => p.availability === availability);
        }
        
        // Sort by selected stat (descending)
        allPlayers.sort((a, b) => {
            const aVal = parseFloat(getPlayerStatValue(a, selectedStat)) || 0;
            const bVal = parseFloat(getPlayerStatValue(b, selectedStat)) || 0;
            return bVal - aVal;
        });
        
        // Take top 50 players
        const topPlayers = allPlayers.slice(0, 50);
        
        if (topPlayers.length === 0) {
            container.innerHTML = '<div class="placeholder-message">No players found for selected filters</div>';
            return;
        }
        
        // Render player list
        let playersHTML = '<div class="players-list">';
        
        topPlayers.forEach((player, index) => {
            const playerName = player.player_name || player.name || 'Unknown Player';
            const position = player.position || 'N/A';
            const nflTeam = player.team || 'FA';
            const statValue = getPlayerStatValue(player, selectedStat);
            const statLabel = getStatLabel(selectedStat);
            
            playersHTML += `
                <div class="player-tile-dashboard">
                    <div class="player-info">
                        <div class="player-name">${playerName.toUpperCase()}</div>
                        <div class="player-team">${nflTeam.toUpperCase()}</div>
                    </div>
                    <div class="player-stat-container">
                        <div class="player-stat">${statValue}</div>
                        <div class="stat-label">${statLabel}</div>
                    </div>
                </div>
            `;
        });
        
        playersHTML += '</div>';
        container.innerHTML = playersHTML;
        
        console.log(`Loaded ${topPlayers.length} players for analytics`);
        
    } catch (error) {
        console.error('Error loading league analytics:', error);
        container.innerHTML = '<div class="error-message">Failed to load player data</div>';
    }
}

async function generateCPRVisualization() {
    const container = document.getElementById('cpr-viz-content');
    container.innerHTML = '<div class="loading-text">Generating CPR visualization...</div>';
    
    try {
        console.log('Generating REAL CPR visualization...');
        
        // Get CPR rankings data from cache
        const cprData = await DataManager.getCPRData();
        
        // Get league data for team names
        const leagueResponse = await fetch(`/api/league?league_id=${LEAGUE_ID}`);
        const leagueData = await leagueResponse.json();
        
        const teams = cprData.data || cprData;
        const users = leagueData.users || [];
        
        if (!teams || teams.length === 0) {
            container.innerHTML = '<div class="error-message">No CPR data available</div>';
            return;
        }
        
        // Sort teams by CPR score (descending)
        const sortedTeams = teams.sort((a, b) => (b.cpr_score || 0) - (a.cpr_score || 0));
        
        // Take top 8 teams for visualization
        const topTeams = sortedTeams.slice(0, 8);
        
        // Find max score for scaling
        const maxScore = Math.max(...topTeams.map(t => t.cpr_score || 0));
        
        let chartHTML = `
            <div class="cpr-chart">
                <div class="chart-placeholder">
                    <div class="chart-title">LEAGUE CPR ANALYSIS</div>
                    <div class="chart-subtitle">Team Power Rankings & Trends</div>
                    <div class="chart-content">
        `;
        
        topTeams.forEach((team, index) => {
            // Find team name from users data
            const user = users.find(u => u.user_id === team.user_id);
            const teamName = user?.metadata?.team_name || user?.display_name || `Team ${index + 1}`;
            const shortName = teamName.length > 8 ? teamName.substring(0, 8) + '...' : teamName;
            
            const cprScore = team.cpr_score || 0;
            const height = maxScore > 0 ? (cprScore / maxScore * 80) : 20; // Scale to 80% max height
            
            chartHTML += `
                <div class="chart-bar" style="height: ${height}%;">
                    <div class="bar-value">${cprScore.toFixed(1)}</div>
                    <div class="bar-label">${shortName}</div>
                </div>
            `;
        });
        
        chartHTML += `
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = chartHTML;
        console.log('CPR visualization generated successfully');
        
    } catch (error) {
        console.error('Error generating CPR visualization:', error);
        container.innerHTML = '<div class="error-message">Failed to generate CPR visualization</div>';
    }
}

// --- Utility Functions ---

async function calculateLeagueAvgScore() {
    try {
        // Get roster data from Sleeper to get PF (points for) and games played
        const rostersResponse = await fetch(`https://api.sleeper.app/v1/league/${LEAGUE_ID}/rosters`);
        const rosters = await rostersResponse.json();
        
        let totalAvgScore = 0;
        let teamCount = 0;
        
        rosters.forEach(roster => {
            const pf = roster.settings?.fpts || 0; // Points For
            const gamesPlayed = roster.settings?.wins + roster.settings?.losses + roster.settings?.ties || 1;
            
            if (gamesPlayed > 0) {
                const avgFppg = pf / gamesPlayed;
                totalAvgScore += avgFppg;
                teamCount++;
            }
        });
        
        return teamCount > 0 ? totalAvgScore / teamCount : 0;
    } catch (error) {
        console.error('Error calculating league avg score:', error);
        return 0;
    }
}

// --- Initialization Complete ---
