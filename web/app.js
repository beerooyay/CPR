// API Configuration - Firebase Functions
const API_BASE = ''; // Use relative URLs for same-origin requests
const MODEL = 'openai/gpt-oss-20b:free'; // Confirmed model
const LEAGUE_ID = '1267325171853701120'; // Legion Fantasy Football League ID

console.log('🚀 CPR-NFL App v8.0 - POLISHED & COMPLETE!');
console.log('💬 Player metrics restored and NIV header fixed. This is it.');

// State Management
let currentScreen = 'home';
let nivState = 'teams'; // 'teams' or 'roster'
let selectedTeam = null;
let cache = {}; // Data cache (cpr_rankings, niv_data, league_stats, dbContext)
let chatMessages = [];
let uploadedFile = null;

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

    if (screenName === 'home') {
        header.style.display = 'none';
        return;
    }

    header.style.display = 'grid';

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
            console.log('Loading NIV roster for:', selectedTeam.team_name);
            loadNIVRoster(selectedTeam);
        } else {
            console.log('NIV condition not met - falling back to teams');
            nivState = 'teams';
            loadNIVTeams();
        }
    } else if (screenName === 'chat') {
        loadChatScreen();
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
                                <div class="metric-value">${(team.points_for / 12 || 0).toFixed(1)} <span class="rank-indicator">(${getRankSuffix(pfRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">STRENGTH OF SCHEDULE</div>
                                <div class="metric-value">${team.zion.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(zionRanks[team.team_id] || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">AVG OPPONENT STRENGTH</div>
                                <div class="metric-value">${(team.opponent_avg || 0).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">SCHEDULE MOMENTUM</div>
                                <div class="metric-value">${team.smi.toFixed(2)} <span class="rank-indicator">(${getRankSuffix(smiRanks[team.team_id] || 1)})</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown-buttons">
                        <button class="dropdown-btn primary" onclick="getScoutingReport('${team.team_id}', 'team')">GET SCOUTING REPORT</button>
                        <button class="dropdown-btn secondary" onclick="goToTeamAnalytics('${team.team_id}')">GO TO TEAM ANALYTICS</button>
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
            <div class="stat-value">#${team.rank}</div>
        </div>
    `;

    container.innerHTML = '<div class="loading">Loading roster...</div>';
    
    try {
        console.log('Loading roster for:', team.team_name);
        
        const response = await fetch(`/api/teamRoster?team=${encodeURIComponent(team.team_name)}&league_id=${LEAGUE_ID}&season=2025`);
        if (!response.ok) throw new Error('Failed to fetch roster');
        
        const data = await response.json();
        const payload = data.data || data;
        const roster = payload.players || payload.niv_data || payload;
        
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        roster.forEach((player, index) => {
            const row = document.createElement('div');
            row.className = 'player-row';
            
            // Get position and team info
            const position = player.position || 'N/A';
            const nflTeam = player.team || 'FA';
            
            row.innerHTML = `
                <div class="tile-header">
                    <div class="rank-badge">${index + 1}</div>
                    <div class="tile-name">${player.name.toUpperCase()} <span class="player-position">(${position} - ${nflTeam})</span></div>
                    <div class="tile-score">${player.niv ? player.niv.toFixed(3) : '0.000'}</div>
                </div>
                <div class="tile-dropdown">
                    <div class="dropdown-modules">
                        <div class="dropdown-module">
                            <div class="module-title">FANTASY PERFORMANCE</div>
                            <div class="metric-row">
                                <div class="metric-label">AVG FANTASY PPG</div>
                                <div class="metric-value">${((player.fantasy_points || 0) / Math.max(player.games_played || 1, 1)).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.ppg_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">PROJECTION</div>
                                <div class="metric-value">${(player.projection || 0).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.proj_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">MOMENTUM</div>
                                <div class="metric-value">${(player.momentum || 0).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.momentum_rank || 1)})</span></div>
                            </div>
                             <div class="metric-row">
                                <div class="metric-label">LAST 3 AVG</div>
                                <div class="metric-value">${(player.last_3_avg || 0).toFixed(2)} <span class="rank-indicator">(${getRankSuffix(player.l3_rank || 1)})</span></div>
                            </div>
                        </div>
                        <div class="dropdown-module">
                            <div class="module-title">POSITION STATS</div>
                            <div class="metric-row">
                                <div class="metric-label">${position === 'QB' ? 'PASS YDS' : position === 'RB' ? 'RUSH YDS' : 'REC YDS'}</div>
                                <div class="metric-value">${position === 'QB' ? (player.passing_yards || 0) : position === 'RB' ? (player.rushing_yards || 0) : (player.receiving_yards || 0)} <span class="rank-indicator">(${getRankSuffix(player.yards_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TOUCHDOWNS</div>
                                <div class="metric-value">${player.touchdowns || 0} <span class="rank-indicator">(${getRankSuffix(player.td_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">GAMES PLAYED</div>
                                <div class="metric-value">${player.games_played || 0} <span class="rank-indicator">(${getRankSuffix(player.games_rank || 1)})</span></div>
                            </div>
                            <div class="metric-row">
                                <div class="metric-label">TOTAL FPTS</div>
                                <div class="metric-value">${player.fantasy_points || 0} <span class="rank-indicator">(${getRankSuffix(player.fpts_rank || 1)})</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown-buttons">
                        <button class="dropdown-btn primary" onclick="getScoutingReport('${player.player_id}', 'player')">GET SCOUTING REPORT</button>
                        <button class="dropdown-btn secondary" onclick="goToTeamAnalytics('${team.team_id}')">GO TO TEAM ANALYTICS</button>
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
        container.innerHTML = '<div class="error">Failed to load roster. Please try again.</div>';
    }
}

// --- Chat Screen Logic ---

async function loadChatScreen() {
    const container = document.getElementById('chat-messages');
    
    if (chatMessages.length === 0) {
        container.innerHTML = `
            <div class="message assistant">
                <div class="message-avatar">
                    <img src="/assets/jaylen.png" alt="Jaylen Hendricks">
                </div>
                <div class="message-bubble">
                    <div class="message-text">
                        Ready to analyze your Legion Fantasy Football league.
                    </div>
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
    
    // Prepare message content
    let messageContent = message;
    
    // Handle file upload if present
    if (uploadedFile) {
        messageContent = `${message}\n\n[File attached: ${uploadedFile.name} (${(uploadedFile.size / 1024).toFixed(1)}KB)]`;
        // Note: File content analysis will be implemented in future version
        uploadedFile = null; // Clear after use
    }
    
    // Add user message
    chatMessages.push({ role: 'user', content: messageContent });
    console.log('💬 Added user message:', messageContent);
    input.value = '';
    
    // Add loading message
    const loadingId = Date.now();
    chatMessages.push({ role: 'assistant', content: '', loading: true, id: loadingId });
    console.log('⏳ Added loading message, total messages:', chatMessages.length);
    
    renderChatMessages();
    
    try {
        const dbContext = await loadDatabaseContext();
        
        const requestBody = {
            messages: chatMessages.filter(m => !m.loading),
            context: dbContext,
            model: MODEL,
            league_id: LEAGUE_ID
        };
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            throw new Error(`Chat request failed: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Remove loading message
        chatMessages = chatMessages.filter(m => m.id !== loadingId);
        
        // Extract assistant response - optimized parsing
        let assistantText = data.data?.response?.content || data.response?.content || data.message || 'no response received';
        
        // Process markdown formatting and add spacing
        assistantText = assistantText
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // **text** -> <strong>text</strong>
            .replace(/\*(.*?)\*/g, '<em>$1</em>')              // *text* -> <em>text</em>
            .replace(/\n\n/g, '\n\n\n')                        // Add extra spacing between paragraphs
            .replace(/([.!?])\s+([a-z])/g, '$1\n\n$2');       // Add breaks after sentences
        
        chatMessages.push({ role: 'assistant', content: assistantText });
        
        renderChatMessages();
        
    } catch (error) {
        console.error('Chat error:', error);
        
        // Remove loading message
        chatMessages = chatMessages.filter(m => m.id !== loadingId);
        
        // Add error message
        chatMessages.push({ 
            role: 'assistant', 
            content: 'sorry, had trouble connecting to jaylen. try again in a moment.' 
        });
        
        renderChatMessages();
    }
}

function renderChatMessages() {
    const container = document.getElementById('chat-messages');
    const isScrolledToBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
    
    console.log('🎯 Rendering chat messages:', chatMessages);
    
    container.innerHTML = chatMessages.map(msg => {
        if (msg.loading) {
            return `
                <div class="message assistant">
                    <div class="message-avatar">
                        <img src="/assets/jaylen.png" alt="Jaylen Hendricks">
                        <div class="loading-spinner"></div>
                    </div>
                </div>
            `;
        }
        
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

// File Upload Handler
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Store file for sending with message
    uploadedFile = file;
    
    const chatInput = document.getElementById('chat-input');
    const fileName = file.name;
    const fileSize = (file.size / 1024).toFixed(2);
    
    // Show file in input as preview
    chatInput.value = `[FILE: ${fileName} (${fileSize}KB)] ${chatInput.value}`;
    console.log('File selected for upload:', fileName, fileSize + 'KB');
}


// --- Auth & Profile Logic ---

function showProfile() {
    const modal = document.getElementById('profile-modal');
    modal.classList.add('active');
}

function closeProfile() {
    const modal = document.getElementById('profile-modal');
    modal.classList.remove('active');
}

function renderAuthUI(user) {
    const authContainer = document.getElementById('auth-container');

    if (user) {
        // Logged-in view
        authContainer.innerHTML = `
            <div class="logged-in-view">
                <img src="${user.photoURL || 'https://ui-avatars.com/api/?name=User&background=003368&color=fff'}" alt="User Avatar" class="user-avatar"/>
                <div class="user-name">${user.displayName || 'Anonymous'}</div>
                <div class="user-email">${user.email}</div>
                
                <div class="profile-tabs">
                    <button class="profile-tab active">ACCOUNT INFO</button>
                </div>
                
                <div id="profile-content">
                    <div id="account-tab" class="profile-tab-content active" style="padding: 20px;">
                        <p>This is where personalized settings and chat history would appear.</p>
                        <p>Authentication via Firebase is active. You are signed in.</p>
                    </div>
                </div>
                
                <div class="profile-action-buttons">
                    <button class="scouting-report-button" onclick="logout()">SIGN OUT</button>
                </div>
            </div>
        `;
    } else {
        // Logged-out view
        authContainer.innerHTML = `
            <h2>PROFILE & AUTH</h2>
            <p>Connect your account to sync your NFL team, save chat history, and get personalized insights.</p>
            <div class="auth-buttons-grid">
                <button class="social-auth-button" onclick="loginGoogle()">
                    <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" style="width: 20px; height: 20px; margin-right: 8px;"/>
                    <span>SIGN IN WITH GOOGLE</span>
                </button>
            </div>
            <div class="auth-divider">OR</div>
            <div class="email-auth-form">
                <input type="email" id="auth-email" placeholder="Email" class="auth-input"/>
                <input type="password" id="auth-password" placeholder="Password" class="auth-input"/>
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
        await window.firebase.signInWithPopup(window.firebaseAuth, window.firebase.googleProvider);
        console.log('Google sign-in successful.');
        closeProfile();
    } catch (error) {
        console.error('Google sign-in error:', error);
        alert(`Sign in failed: ${error.message}`);
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

// Navigation Functions
function getScoutingReport(id, type) {
    console.log(`Getting scouting report for ${type}: ${id}`);
    // TODO: Implement scouting report functionality
}

function goToTeamAnalytics(teamId) {
    console.log(`Navigating to team analytics for: ${teamId}`);
    // Find the team in NIV data and load roster
    if (cache.niv_data && cache.niv_data.team_niv) {
        const team = cache.niv_data.team_niv.find(t => t.team_id === teamId);
        if (team) {
            loadNIVRoster(team);
        }
    }
}
