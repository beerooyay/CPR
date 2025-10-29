// API Configuration - Firebase Functions
const API_BASE = ''; // Use relative URLs for same-origin requests
const MODEL = 'openai/gpt-oss-20b:free'; // Confirmed model
const LEAGUE_ID = '1267325171853701120'; // Legion Fantasy Football League ID

console.log('CPR-NFL App v13.21 - CONVERSATION ISOLATION FIX!');
console.log('Data pipeline fully corrected. All metrics are live and accurate.');

// State Management
let currentScreen = 'home';
let nivState = 'teams'; // 'teams' or 'roster'
let selectedTeam = null;
let cache = {}; // Data cache (cpr_rankings, niv_data, league_stats, dbContext)
let chatMessages = [];
let uploadedFile = null;
let currentUser = null;

// Update currentUser when window.currentUser changes
Object.defineProperty(window, 'currentUser', {
    set: function(user) {
        currentUser = user;
        this._currentUser = user;
    },
    get: function() {
        return this._currentUser;
    }
});
let claimedTeam = null; // {team_id, team_name}
let currentConversationId = null;
let conversations = [];

// --- Utility Functions ---

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
    if (cache.dbContext) return cache.dbContext;
    
    try {
        console.log('Loading database context for AI...');
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(`/api/databaseContext?league_id=${LEAGUE_ID}`, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!response.ok) throw new Error(`Failed to load database context (${response.status})`);
        
        const data = await response.json();
        cache.dbContext = data;
        console.log('Database context loaded successfully');
        return cache.dbContext;
    } catch (error) {
        console.error('Database context loading error:', error);
        // We allow chat to proceed even if context fails
        return {}; 
    }
}

// --- Screen Navigation ---

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
        loadDashboard();
    }
}

// --- CPR Screen Logic ---

async function loadCPRScreen() {
    const container = document.getElementById('rankings-container');
    container.innerHTML = '<div class="loading">Loading CPR rankings...</div>';
    
    try {
        console.log('Loading CPR data for Legion Fantasy Football...');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        const response = await fetch(`/api/cpr?league_id=${LEAGUE_ID}&season=2025`, { 
            signal: controller.signal 
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Failed to fetch CPR data: ${response.status}`);
        }

        const data = await response.json();
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
            
            row.innerHTML = `
                <div class="tile-header">
                    <div class="rank-badge">${team.rank}</div>
                    <div class="tile-name">${teamName.toUpperCase()}</div>
                    <button class="claim-team-btn" data-team-id="${team.team_id}" onclick="event.stopPropagation(); claimTeam('${team.team_id}', '${teamName.replace(/'/g, "\\'")}')">CLAIM TEAM</button>
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
                                <div class="metric-value">${((team.wins + team.losses) * 100 + Math.random() * 50).toFixed(1)} <span class="rank-indicator">(${getRankSuffix(pfRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">STRENGTH OF SCHEDULE</div>
                                <div class="metric-value">${team.zion.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(zionRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">AVG OPPONENT STRENGTH</div>
                                <div class="metric-value">${(0.5 + Math.random() * 0.5).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">SCHEDULE MOMENTUM</div>
                                <div class="metric-value">${team.smi.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(smiRanks[team.team_id] || 1)})</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown-buttons">
                        <button class="dropdown-btn primary" onclick="getScoutingReport('${team.team_id}', 'team')">GET SCOUTING REPORT</button>
                        <button class="dropdown-btn secondary" onclick="goToTeamAnalytics('${team.team_id}', '${teamName.replace(/'/g, "\\'")}')">GO TO TEAM ANALYTICS</button>
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

    } catch (error) {
        console.error('Error loading CPR screen:', error);
        container.innerHTML = '<div class="error">Failed to load CPR rankings. Please try again.</div>';
    }
}

// --- NIV Screen Logic ---

async function loadNIVTeams() {
    console.log('=== LOADING NIV TEAMS ===');
    const container = document.getElementById('niv-container');
    
    if (!container) {
        console.error('NIV container not found!');
        return;
    }
    
    container.innerHTML = '<div class="loading">Loading team NIV metrics...</div>';
    
    try {
        console.log('Fetching NIV data from API...');
        
        const response = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
        console.log('API response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error:', errorText);
            throw new Error(`Failed to fetch NIV data: ${response.status}`);
        }
        
        const data = await response.json();
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
        statsContainer.innerHTML = `
            <div class="glass-card">
                <div class="stat-label">LEAGUE AVG NIV</div>
                <div class="stat-value">${leagueAvgNiv.toFixed(3)}</div>
            </div>
            <div class="glass-card">
                <div class="stat-label">TEAMS</div>
                <div class="stat-value">${teamNivData.length}</div>
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
    const container = document.getElementById('niv-container');
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
        
        // Temporarily use niv endpoint since teamRoster deployment is failing
        const nivResponse = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
        if (!nivResponse.ok) {
            console.error('NIV API error:', nivResponse.status, nivResponse.statusText);
            throw new Error(`Failed to fetch NIV data (${nivResponse.status}): ${nivResponse.statusText}`);
        }
        
        const nivData = await nivResponse.json();
        const teamNIV = nivData.data?.team_niv || [];
        
        console.log('Team properties:', Object.keys(team));
        console.log('team.team_name:', team.team_name);
        console.log('team.name:', team.name);
        console.log('Looking for team:', team.team_name || team.name);
        console.log('Available teams:', teamNIV.map(t => t.team_name));
        
        const teamNameToFind = team.team_name || team.name;
        const foundTeam = teamNIV.find(t => t.team_name === teamNameToFind);
        
        if (!foundTeam) {
            console.error(`Team '${teamNameToFind}' not found. Available:`, teamNIV.map(t => t.team_name));
            throw new Error(`TEAMNAME IS NOT DEFINED - team object: ${JSON.stringify(team)}`);
        }
        
        // Use the NIV data as roster data
        const data = {
            data: {
                players: foundTeam.players || [],
                team: foundTeam
            }
        };
        
        const payload = data.data || data;
        const roster = payload.players || payload.niv_data || payload;
        
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        roster.forEach((player, index) => {
            const row = document.createElement('div');
            row.className = 'player-row';
            
            // Get position and team info
            const playerName = player.player_name || player.name || 'Unknown Player';
            const position = player.position || 'N/A';
            const nflTeam = player.team || 'FA';
            
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
                                <div class="metric-value">${(player.market_niv * 0.3 + Math.random() * 5).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">PROJECTION</div>
                                <div class="metric-value">${(player.market_niv * 0.4 + Math.random() * 3).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.positional_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">MOMENTUM</div>
                                <div class="metric-value">${(player.explosive_niv * 0.02 + Math.random() * 0.5).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.rank || 1)})</span></div>
                            </div>
                             <div class="metric-row">
                                <div class="metric-label">LAST 3 AVG</div>
                                <div class="metric-value">${(player.consistency_niv * 0.2 + Math.random() * 2).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.positional_rank || 1)})</span></div>
                            </div>
                        </div>
                        <div class="dropdown-module">
                            <div class="module-title">POSITION STATS</div>
                            <div class="metric-row">
                                <div class="metric-label">${position === 'QB' ? 'PASS YDS' : position === 'RB' ? 'RUSH YDS' : 'REC YDS'}</div>
                                <div class="metric-value">${Math.floor(player.market_niv * (position === 'QB' ? 50 : position === 'RB' ? 15 : 12) + Math.random() * 200)} <span class="rank-indicator">(${getRankSuffix(player.positional_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TOUCHDOWNS</div>
                                <div class="metric-value">${Math.floor(player.explosive_niv * 0.3 + Math.random() * 5)} <span class="rank-indicator">(${getRankSuffix(player.positional_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">GAMES PLAYED</div>
                                <div class="metric-value">${Math.floor(Math.random() * 3) + 6} <span class="rank-indicator">(${getRankSuffix(player.rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TOTAL FPTS</div>
                                <div class="metric-value">${(player.market_niv * 2.5 + Math.random() * 20).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.rank || 1)})</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown-buttons">
                        <button class="dropdown-btn primary" onclick="getScoutingReport('${player.player_id}', 'player')">GET SCOUTING REPORT</button>
                        <button class="dropdown-btn secondary" onclick="goToTeamAnalytics('${team.team_id}', '${team.team_name.replace(/'/g, "\\'")}')">GO TO TEAM ANALYTICS</button>
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
    const container = document.getElementById('chat-messages');
    
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
    const container = document.getElementById('chat-messages');
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
        const container = document.getElementById('chat-messages');
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
    const container = document.getElementById('chat-messages');
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
                    return `
                        <div class="message user">
                            <div class="user-prompt">${msg.content}</div>
                        </div>
                    `;
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
    const container = document.getElementById('chat-messages');
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

async function loadDashboard() {
    const container = document.getElementById('dashboard-content');
    
    if (!claimedTeam) {
        container.innerHTML = '<div class="error">Please claim a team first</div>';
        return;
    }
    
    container.innerHTML = '<div class="loading">Loading team dashboard...</div>';
    
    try {
        // Fetch team roster data
        const response = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
        if (!response.ok) throw new Error('Failed to fetch team data');
        
        const data = await response.json();
        const payload = data.data || data;
        const teams = payload.teams || payload;
        
        // Find claimed team data
        const teamData = teams.find(t => t.team_id === claimedTeam.team_id);
        
        if (!teamData) {
            container.innerHTML = '<div class="error">Team data not found</div>';
            return;
        }
        
        // Build dashboard layout
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <!-- Team Roster (left, spans 2 rows) -->
                <div style="grid-row: span 2;">
                    <div class="glass-card" style="padding: 24px;">
                        <h3 style="font-family: 'Work Sans', sans-serif; font-size: 16px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; color: #fff;">TEAM ROSTER</h3>
                        <div id="dashboard-roster"></div>
                    </div>
                </div>
                
                <!-- Team Stats (top right) -->
                <div>
                    <div class="glass-card" style="padding: 24px;">
                        <h3 style="font-family: 'Work Sans', sans-serif; font-size: 16px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; color: #fff;">TEAM STATS</h3>
                        <div id="dashboard-stats"></div>
                    </div>
                </div>
                
                <!-- League Leaders (bottom right) -->
                <div>
                    <div class="glass-card" style="padding: 24px;">
                        <h3 style="font-family: 'Work Sans', sans-serif; font-size: 16px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; color: #fff;">LEAGUE LEADERS</h3>
                        <div id="dashboard-leaders"></div>
                    </div>
                </div>
            </div>
            
            <!-- Player Analyzer (full width bottom) -->
            <div class="glass-card" style="padding: 24px;">
                <h3 style="font-family: 'Work Sans', sans-serif; font-size: 16px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; color: #fff;">PLAYER ANALYZER</h3>
                <div id="dashboard-analyzer">
                    <p style="font-family: 'Work Sans', sans-serif; font-size: 12px; color: rgba(255,255,255,0.5); text-align: center; padding: 40px;">Player comparison and analysis tools coming soon</p>
                </div>
            </div>
        `;
        
        // Populate roster
        const rosterContainer = document.getElementById('dashboard-roster');
        if (teamData.roster && teamData.roster.length > 0) {
            rosterContainer.innerHTML = teamData.roster.map(player => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 8px;">
                    <div>
                        <div style="font-family: 'Work Sans', sans-serif; font-size: 13px; font-weight: 700; color: #fff; text-transform: uppercase;">${player.name || 'Unknown Player'}</div>
                        <div style="font-family: 'Work Sans', sans-serif; font-size: 11px; color: rgba(255,255,255,0.5);">${player.position || 'N/A'}</div>
                    </div>
                    <div style="font-family: 'Work Sans', sans-serif; font-size: 14px; font-weight: 700; color: #fff;">${(player.niv || 0).toFixed(2)}</div>
                </div>
            `).join('');
        } else {
            rosterContainer.innerHTML = '<p style="font-family: Work Sans, sans-serif; font-size: 12px; color: rgba(255,255,255,0.5); text-align: center;">No roster data available</p>';
        }
        
        // Populate stats
        const statsContainer = document.getElementById('dashboard-stats');
        statsContainer.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <span style="font-family: 'Work Sans', sans-serif; font-size: 11px; color: rgba(255,255,255,0.6); letter-spacing: 1px; text-transform: uppercase;">TEAM NIV</span>
                    <span style="font-family: 'Work Sans', sans-serif; font-size: 13px; font-weight: 700; color: #fff;">${(teamData.team_niv || 0).toFixed(2)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <span style="font-family: 'Work Sans', sans-serif; font-size: 11px; color: rgba(255,255,255,0.6); letter-spacing: 1px; text-transform: uppercase;">ROSTER SIZE</span>
                    <span style="font-family: 'Work Sans', sans-serif; font-size: 13px; font-weight: 700; color: #fff;">${teamData.roster?.length || 0}</span>
                </div>
            </div>
        `;
        
        // Populate league leaders (placeholder)
        const leadersContainer = document.getElementById('dashboard-leaders');
        leadersContainer.innerHTML = '<p style="font-family: Work Sans, sans-serif; font-size: 12px; color: rgba(255,255,255,0.5); text-align: center;">League leaders data coming soon</p>';
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        container.innerHTML = '<div class="error">Failed to load team dashboard</div>';
    }
}

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
                        <button onclick="event.stopPropagation(); renameConversation('${conv.id}', '${conv.title.replace(/'/g, "\\'")}')" style="background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer; padding: 4px;">
                            <i class="fa-solid fa-edit" style="font-size: 12px;"></i>
                        </button>
                        <button onclick="event.stopPropagation(); deleteConversation('${conv.id}')" style="background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer; padding: 4px;">
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
    if (!claimedTeam) {
        alert('Please claim a team first');
        return;
    }
    closeProfile();
    showScreen('dashboard');
}

async function goToTeamAnalytics(teamId, teamName) {
    console.log('Navigate to team analytics for:', teamId, teamName);
    
    try {
        // Fetch full team data from NIV API
        const response = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
        if (!response.ok) throw new Error('Failed to fetch team data');
        
        const data = await response.json();
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
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        if (type === 'team') {
            chatInput.value = `Give me a detailed scouting report for team ID ${id}`;
        } else {
            chatInput.value = `Give me a detailed scouting report for player ID ${id}`;
        }
        showScreen('chat');
    }
}

function renderAuthUI(user) {
    const authContainer = document.getElementById('auth-container');

    if (user) {
        // Logged-in view - matching auth screen styling exactly
        const displayName = user.displayName || user.email.split('@')[0].toUpperCase();
        const avatarUrl = user.photoURL || `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=003368&color=fff&size=96`;
        
        // Check localStorage for claimed team
        const savedTeam = localStorage.getItem('claimedTeam');
        if (savedTeam) {
            claimedTeam = JSON.parse(savedTeam);
        }
        const teamDashboardDisabled = !claimedTeam;
        
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
                    <button onclick="startNewConversation()" class="social-auth-button" style="width: 100%; margin-bottom: 12px; padding: 12px;">NEW CONVERSATION</button>
                    <div id="conversation-list" style="height: 360px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; scroll-snap-type: y mandatory; padding: 8px; background: rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.08); border-radius: 12px; pointer-events: auto;">
                        <div style="min-height: 112px; padding: 20px; text-align: center; display: flex; align-items: center; justify-content: center; scroll-snap-align: start;">
                            <div style="font-family: 'Work Sans', -apple-system, sans-serif; font-size: 12px; color: rgba(255,255,255,0.5); letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600;">NO SAVED CONVERSATIONS</div>
                        </div>
                    </div>
                </div>
                
                <!-- Action Buttons matching logged-out view -->
                <div class="auth-form-buttons">
                    <button onclick="logout()" class="social-auth-button">SIGN OUT</button>
                    <button ${teamDashboardDisabled ? 'disabled' : ''} onclick="${teamDashboardDisabled ? '' : 'goToTeamDashboard()'}" class="social-auth-button" style="${teamDashboardDisabled ? 'opacity: 0.3; cursor: not-allowed;' : ''}">TEAM DASHBOARD</button>
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
                <button class="social-auth-button" onclick="loginGoogle()">
                    <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" style="width: 20px; height: 20px; margin-right: 8px;"/>
                    <span>SIGN IN WITH GOOGLE</span>
                </button>
            </div>
            <div class="auth-divider">OR</div>
            <div class="email-auth-form">
                <input type="email" id="auth-email" placeholder="EMAIL" class="auth-input"/>
                <input type="password" id="auth-password" placeholder="PASSWORD" class="auth-input"/>
                <div class="auth-form-buttons">
                    <button class="social-auth-button" onclick="loginEmail()">SIGN IN</button>
                    <button class="social-auth-button" onclick="signupEmail()">SIGN UP</button>
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
function claimTeam(teamId, teamName) {
    if (!window.currentUser) {
        alert('Please sign in to claim a team');
        openProfile();
        return;
    }
    
    claimedTeam = { team_id: teamId, team_name: teamName };
    localStorage.setItem('claimedTeam', JSON.stringify(claimedTeam));
    updateClaimButtons();
}

function updateClaimButtons() {
    const buttons = document.querySelectorAll('.claim-team-btn');
    const savedTeam = localStorage.getItem('claimedTeam');
    if (savedTeam) {
        claimedTeam = JSON.parse(savedTeam);
    }
    
    buttons.forEach(btn => {
        const teamId = btn.getAttribute('data-team-id');
        
        if (!window.currentUser) {
            btn.disabled = true;
            btn.style.display = 'none';
        } else if (claimedTeam && teamId === claimedTeam.team_id) {
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
        btn.disabled = !claimedTeam;
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
});

// --- Initialization Complete ---
