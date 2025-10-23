// API Configuration
const API_BASE = 'https://us-central1-cpr-app-54c15.cloudfunctions.net/api';

// AI Model (OpenRouter key is stored securely on backend)
const MODEL = 'meta-llama/llama-3.2-3b-instruct:free';

// State
let currentScreen = 'home';
let nivState = 'teams'; // 'teams' or 'roster'
let selectedTeam = null;
let cache = {}; // Data cache (rankings, teams, stats, dbContext)
let chatMessages = [];
let isStreaming = false;

// --- Utility Functions ---

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
        console.log('🖳 Loading database context for AI...');
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(`${API_BASE}/database-context`, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!response.ok) throw new Error(`Failed to load database context (${response.status})`);
        
        const data = await response.json();
        cache.dbContext = data;
        console.log('✅ Database context loaded successfully');
        return cache.dbContext;
    } catch (error) {
        console.error('❌ Database context loading error:', error);
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
                title = selectedTeam ? selectedTeam.name.toUpperCase() : 'ROSTER';
                backAction = () => {
                    nivState = 'teams';
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
        if (nivState === 'teams') {
            loadNIVTeams();
        } else if (nivState === 'roster' && selectedTeam) {
            loadNIVRoster(selectedTeam);
        }
    } else if (screenName === 'chat') {
        loadChatScreen();
    }
}

// --- CPR Screen Logic ---

async function loadCPRScreen() {
    // Use the existing container ID: #rankings-container
    const container = document.getElementById('rankings-container');
    container.innerHTML = '<div class="loading-state">Loading CPR rankings...</div>';
    
    try {
        console.log('📊 Loading CPR data from:', API_BASE);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const [statsRes, rankingsRes] = await Promise.all([
            fetch(`${API_BASE}/league-stats?season=2025`, { signal: controller.signal }),
            fetch(`${API_BASE}/rankings?season=2025`, { signal: controller.signal })
        ]);
        
        clearTimeout(timeoutId);

        if (!statsRes.ok || !rankingsRes.ok) {
            throw new Error(`Failed to fetch CPR data: stats(${statsRes.status}), rankings(${rankingsRes.status})`);
        }

        const stats = await statsRes.json();
        const rankings = await rankingsRes.json();

        // Update cache
        cache.stats = stats;
        cache.rankings = rankings;

        // Update league stats
        document.getElementById('league-health').textContent = `${(stats.health * 100).toFixed(1)}%`;
        document.getElementById('gini-coeff').textContent = stats.gini.toFixed(3);

        // Clear and build rankings
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        rankings.forEach(team => {
            const row = document.createElement('div');
            row.className = `team-row ${team.rank === 1 ? 'gold' : ''}`;
            row.dataset.team = team.team;
            
            const alvaradoValue = team.alvarado != null ? team.alvarado.toFixed(2) : '0.00';

            row.innerHTML = `
                <div class="neon-border"></div>
                <div class="team-row-header">
                    <div class="rank-badge">${team.rank}</div>
                    <div class="team-name">${team.team.toUpperCase()}</div>
                    <button class="claim-team-btn" data-team="${team.team}" style="opacity: 0.5;">CLAIM TEAM (Auth Required)</button>
                    <div class="cpr-value">${team.cpr.toFixed(3)}</div>
                </div>
                <div class="team-details">
                    <div class="metric-row">
                        <div class="metric-label">sli</div>
                        <div class="metric-value ${team.sli > 0 ? 'positive' : team.sli < 0 ? 'negative' : ''}">${team.sli.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">bsi</div>
                        <div class="metric-value ${team.bsi > 0 ? 'positive' : team.bsi < 0 ? 'negative' : ''}">${team.bsi.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">smi</div>
                        <div class="metric-value">${team.smi.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">ingram</div>
                        <div class="metric-value ${team.ingram > 0 ? 'positive' : team.ingram < 0 ? 'negative' : ''}">${team.ingram.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">alvarado</div>
                        <div class="metric-value ${team.alvarado > 0 ? 'positive' : team.alvarado < 0 ? 'negative' : ''}">${alvaradoValue}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">zion</div>
                        <div class="metric-value ${team.zion > 0 ? 'positive' : team.zion < 0 ? 'negative' : ''}">${team.zion.toFixed(2)}</div>
                    </div>
                    <button class="team-analytics-button">GO TO TEAM ANALYTICS</button>
                    <button class="scouting-report-button">GET SCOUTING REPORT</button>
                </div>
            `;
            fragment.appendChild(row);
        });

        container.appendChild(fragment);
        
        // Event delegation
        container.onclick = (e) => {
            const row = e.target.closest('.team-row');
            if (!row) return;

            const teamName = row.dataset.team;
            const teamData = rankings.find(t => t.team === teamName);

            if (e.target.classList.contains('team-analytics-button')) {
                goToTeamAnalytics(teamName);
            } else if (e.target.classList.contains('scouting-report-button')) {
                getTeamScoutingReport(teamData);
            } else if (!e.target.closest('.team-details') && !e.target.classList.contains('claim-team-btn')) {
                row.classList.toggle('expanded');
            }
        };

        // Mode buttons setup (Salary/Performance/Hybrid)
        document.querySelectorAll('.mode-button').forEach(btn => {
            btn.onclick = (e) => {
                document.querySelectorAll('.mode-button').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            };
        });

    } catch (error) {
        console.error('❌ CPR loading error:', error);
        container.innerHTML = `<div class="error-state">
            <div>Failed to load CPR rankings</div>
            <div class="error-detail">${error.message}</div>
            <button onclick="loadCPRScreen()">RETRY</button>
        </div>`;
    }
}

async function goToTeamAnalytics(teamName) {
    // Load teams data if not cached
    if (!cache.teams) {
        try {
            const response = await fetch(`${API_BASE}/teams?season=2025`);
            if (!response.ok) throw new Error('Failed to load teams');
            cache.teams = await response.json();
        } catch (error) {
            console.error('error loading teams:', error);
            alert('Could not load team data.');
            return;
        }
    }

    const team = cache.teams.find(t => t.name.toUpperCase() === teamName.toUpperCase());

    if (team) {
        showScreen('niv');
        nivState = 'roster';
        selectedTeam = team;
        // Need to re-run showScreen to update header correctly
        showScreen('niv'); 
    } else {
        console.error('Team not found:', teamName);
    }
}

// --- NIV Screen Logic ---

async function loadNIVTeams() {
    // Use the existing container ID: #niv-container
    const container = document.getElementById('niv-container');
    const statsContainer = document.getElementById('niv-stats-container');
    
    container.innerHTML = `
        <div class="loading-state">
            <div class="loading-spinner"></div>
            <div>Loading teams...</div>
        </div>`;
    
    statsContainer.style.display = 'none';

    try {
        console.log('👥 Loading NIV teams from:', API_BASE);
        
        if (!cache.teams) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch(`${API_BASE}/teams?season=2025`, { signal: controller.signal });
            clearTimeout(timeoutId);
            
            if (!response.ok) throw new Error(`Failed to load teams (${response.status})`);
            cache.teams = await response.json();
        }

        const teams = cache.teams;
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        teams.forEach(team => {
            const card = document.createElement('div');
            card.className = 'team-row';
            card.dataset.teamName = team.name;
            card.innerHTML = `
                <div class="neon-border"></div>
                <div class="team-row-header">
                    <div class="team-name">${team.name.toUpperCase()}</div>
                    <div style="font-size: 20px; color: #ffffff; font-weight: 600;">→</div>
                </div>
            `;
            fragment.appendChild(card);
        });

        container.appendChild(fragment);

        // Event delegation
        container.onclick = (e) => {
            const card = e.target.closest('.team-row');
            if (!card) return;
            const teamName = card.dataset.teamName;
            const team = teams.find(t => t.name === teamName);
            if (team) {
                selectedTeam = team;
                nivState = 'roster';
                loadNIVRoster(team);
                updateHeader('niv'); // Update header title after state change
            }
        };

    } catch (error) {
        console.error('❌ NIV teams loading error:', error);
        container.innerHTML = `<div class="error-state">
            <div>Failed to load teams</div>
            <div class="error-detail">${error.message}</div>
            <button onclick="loadNIVTeams()">RETRY</button>
        </div>`;
    }
}

function loadNIVRoster(team) {
    const container = document.getElementById('niv-container');
    const statsContainer = document.getElementById('niv-stats-container');

    // Calculate team stats
    const totalPlayers = team.players.length;
    const avgNIV = totalPlayers > 0 ? team.players.reduce((sum, p) => sum + (p.niv || 0), 0) / totalPlayers : 0;
    const totalFP = team.players.reduce((sum, p) => sum + (p.fp || 0), 0);

    statsContainer.innerHTML = `
        <div class="glass-card">
            <div class="neon-border"></div>
            <div class="stat-label">AVG NIV</div>
            <div class="stat-value">${avgNIV.toFixed(2)}</div>
        </div>
        <div class="glass-card">
            <div class="neon-border"></div>
            <div class="stat-label">TOTAL FANTASY PTS</div>
            <div class="stat-value">${totalFP.toFixed(1)}</div>
        </div>
    `;
    statsContainer.style.display = 'grid';

    // Build player rows
    container.innerHTML = '';
    const fragment = document.createDocumentFragment();

    team.players.forEach(player => {
        const row = document.createElement('div');
        row.className = 'player-row';
        row.dataset.playerName = player.name; 
        
        const healthClass = player.health >= 0.9 ? 'positive' : player.health <= 0.7 ? 'negative' : '';
        const consistencyClass = player.consistency >= 0.9 ? 'positive' : player.consistency <= 0.7 ? 'negative' : '';
        const alvaradoClass = player.alvarado > 0 ? 'positive' : 'negative';

        row.innerHTML = `
            <div class="neon-border"></div>
            <div class="player-row-header">
                <div class="player-name">${player.name.toUpperCase()}</div>
                <div class="niv-value">${player.niv.toFixed(2)}</div>
            </div>
            <div class="player-details">
                <div class="metric-row">
                    <div class="metric-label">fantasy points</div>
                    <div class="metric-value" style="font-size: 18px;">${player.fp.toFixed(1)}</div>
                </div>
                <div class="metric-row">
                    <div class="metric-label">health</div>
                    <div class="metric-value ${healthClass}">${(player.health * 100).toFixed(0)}%</div>
                </div>
                <div class="metric-row">
                    <div class="metric-label">consistency</div>
                    <div class="metric-value ${consistencyClass}">${(player.consistency * 100).toFixed(0)}%</div>
                </div>
                <div class="metric-row">
                    <div class="metric-label">alvarado (value/$)</div>
                    <div class="metric-value ${alvaradoClass}">${player.alvarado.toFixed(2)}</div>
                </div>
                <div class="metric-row">
                    <div class="metric-label">pts/reb/ast</div>
                    <div class="metric-value">${player.pts.toFixed(1)} / ${player.reb.toFixed(1)} / ${player.ast.toFixed(1)}</div>
                </div>
                <div class="metric-row">
                    <div class="metric-label">stl/blk/to</div>
                    <div class="metric-value">${player.stl.toFixed(1)} / ${player.blk.toFixed(1)} / ${player.to.toFixed(1)}</div>
                </div>
                <div class="metric-row">
                    <div class="metric-label">fg%/ft%/3pm</div>
                    <div class="metric-value">${(player.fg_pct * 100).toFixed(1)}% / ${(player.ft_pct * 100).toFixed(1)}% / ${player.threes.toFixed(1)}</div>
                </div>
                <button class="scouting-report-button">GET SCOUTING REPORT</button>
            </div>
        `;
        fragment.appendChild(row);
    });

    container.appendChild(fragment);

    // Event delegation
    container.onclick = (e) => {
        const row = e.target.closest('.player-row');
        if (!row) return;

        const playerName = row.dataset.playerName;
        const player = team.players.find(p => p.name === playerName);

        if (e.target.classList.contains('scouting-report-button')) {
            getPlayerScoutingReport(player, team);
        } else if (!e.target.closest('.player-details')) {
            row.classList.toggle('expanded');
        }
    };
}

// --- AI & Chat Logic ---

async function getTeamScoutingReport(team) {
    showScreen('chat');

    const prompt = `[SCOUTING_REPORT:${team.team}]

give me a full scouting report on ${team.team}. here's their current metrics:
- CPR Score: ${team.cpr.toFixed(3)} (rank #${team.rank})
- SLI (Starting Lineup): ${team.sli.toFixed(2)}
- BSI (Bench Strength): ${team.bsi.toFixed(2)}
- SMI (Systemic Momentum Index): ${team.smi.toFixed(2)}
- Ingram Index (positional balance): ${team.ingram.toFixed(2)}
- Alvarado Index (value efficiency): ${team.alvarado.toFixed(2)}
- Zion Index (health): ${team.zion.toFixed(2)}

break down their strengths, weaknesses, roster construction, and what they need to improve. give me the real talk.`;

    const input = document.getElementById('chat-input');
    input.value = prompt;
    sendMessage();
}

async function getPlayerScoutingReport(player, team) {
    showScreen('chat');

    const prompt = `[SCOUTING_REPORT:${player.name}]

give me a full scouting report on ${player.name} (${team.name}). here's his stats:
- NIV Score: ${player.niv.toFixed(2)}
- Fantasy Points: ${player.fp.toFixed(1)}
- Health: ${(player.health * 100).toFixed(0)}%
- Consistency: ${(player.consistency * 100).toFixed(0)}%
- Alvarado (value/$): ${player.alvarado.toFixed(2)}
- Stats: ${player.pts.toFixed(1)} pts, ${player.reb.toFixed(1)} reb, ${player.ast.toFixed(1)} ast
- Defense: ${player.stl.toFixed(1)} stl, ${player.blk.toFixed(1)} blk
- Shooting: ${(player.fg_pct * 100).toFixed(1)}% FG, ${(player.ft_pct * 100).toFixed(1)}% FT, ${player.threes.toFixed(1)} 3PM
- Turnovers: ${player.to.toFixed(1)}

break down his game, fantasy value, strengths, weaknesses, and whether he's underrated or overrated right now. give me the real talk.`;

    const input = document.getElementById('chat-input');
    input.value = prompt;
    sendMessage();
}

async function loadChatScreen() {
    console.log('Loading chat screen...');
    
    if (!cache.dbContext) {
        try {
            await loadDatabaseContext();
        } catch (err) {
            console.warn('⚠ Database context load failed, chat may be less informed:', err);
        }
    }

    if (chatMessages.length === 0) {
        chatMessages = [{
            role: 'assistant',
            content: 'Hey there! I\'m Jaylen Hendricks, your FBA insider. Ask me anything about your league, players, or strategies.'
        }];
    }

    renderChat();
    document.getElementById('chat-input')?.focus();
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    let message = input.value.trim();
    const sendBtn = document.getElementById('send-button');
    
    if (!message || isStreaming) return;

    // 1. Clear input and add user message
    input.value = '';
    chatMessages.push({ role: 'user', content: message });
    renderChat();
    
    // 2. Add temporary streaming message and disable button
    isStreaming = true;
    if (sendBtn) sendBtn.disabled = true;

    // --- STUBBED API CALL (Since Python chat endpoint is missing) ---
    const assistantMessage = { role: 'assistant', content: 'Thinking...' };
    chatMessages.push(assistantMessage);
    renderChat();

    try {
        // In a real app, this would stream the response from the Flask /api/chat endpoint
        console.log(`Sending message to AI model ${MODEL}: ${message}`);
        
        const context = cache.dbContext || {};
        
        // Simulate API delay and streaming
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        const mockResponse = `That's a fantastic question. Based on the latest Commissioner's Parity Report (CPR), ${message.includes("team") ? "that team" : "that player"} is highly rated. 

If you are asking about rankings, the current number one team by CPR score is **${context.rankings?.[0]?.team || 'N/A'}** with a score of **${context.rankings?.[0]?.cpr.toFixed(3) || 'N/A'}**.

The league health index is currently **${(context.league?.health * 100).toFixed(1) || 'N/A'}%**, indicating reasonable parity across the league.

Let me know if you want a deeper dive into any specific metric or player like **${context.top_players?.[0]?.player_name || 'N/A'}**.`;
        
        // Replace temporary message with final content
        chatMessages.pop();
        chatMessages.push({ role: 'assistant', content: mockResponse });

    } catch (error) {
        console.error('Chat error:', error);
        chatMessages.pop(); // Remove placeholder
        chatMessages.push({ 
            role: 'assistant', 
            content: 'Sorry, I encountered an error. The chat API is currently unavailable.' 
        });
    } finally {
        isStreaming = false;
        if (sendBtn) sendBtn.disabled = false;
        renderChat();
        scrollToBottom(true);
    }
    // --- END STUBBED API CALL ---
}


// Simple markdown renderer
function renderMarkdown(text) {
    let result = text;
    
    return result
        // Code blocks
        .replace(/```([\s\S]+?)```/g, '<pre><code>$1</code></pre>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Inline code
        .replace(/`(.+?)`/g, '<code>$1</code>')
        // Headers (Simplified)
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bullet lists
        .replace(/^[*-] (.+)$/gm, '<li>$1</li>')
        // Wrap lists
        .replace(/(<li>.*<\/li>(\s*<li>.*<\/li>)*)/s, '<ul>$1</ul>')
        // Line breaks
        .replace(/\n\n+/g, '<br>')
        .replace(/\n/g, ' ');
}

// Optimized scroll to bottom with debounce
const scrollToBottom = debounce((smooth = false) => {
    const chatMessagesEl = document.getElementById('chat-messages');
    if (!chatMessagesEl) return;

    chatMessagesEl.scrollTo({
        top: chatMessagesEl.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
    });
}, 50);

function renderChat() {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    // Check if user is scrolled to the bottom before rendering
    const isScrolledToBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 50;

    container.innerHTML = chatMessages.map((msg) => {
        const userPhotoURL = window.firebaseAuth?.currentUser?.photoURL || 'https://ui-avatars.com/api/?name=User&background=509ae3&color=fff';
        const avatar = msg.role === 'user' 
            ? `<div class="message-avatar"><img src="${userPhotoURL}" alt="User"></div>` 
            : `<div class="message-avatar"><img src="jaylen.png" alt="Jaylen Hendricks"></div>`;

        // Note: The message structure needs to match the CSS/HTML design
        return `
            <div class="message ${msg.role === 'user' ? 'user-message' : 'assistant-message'}">
                ${avatar}
                <div class="message-bubble">
                    <div class="message-text">${renderMarkdown(msg.content)}</div>
                </div>
            </div>
        `;
    }).join('');

    // Only scroll to bottom if the user was near the bottom before the update
    if (isScrolledToBottom || chatMessages.length === 1) {
        scrollToBottom(true);
    }
}

// File Upload Handler (simplified)
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const chatInput = document.getElementById('chat-input');
    const fileName = file.name;
    const fileSize = (file.size / 1024).toFixed(2);
    
    chatInput.value = `[FILE: ${fileName} (${fileSize}KB)] ${chatInput.value}`;
    console.log('File selected:', fileName, fileSize + 'KB');
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
        // Logged-in view (Simplified)
        authContainer.innerHTML = `
            <div class="logged-in-view">
                <img src="${user.photoURL || 'https://ui-avatars.com/api/?name=User&background=509ae3&color=fff'}" alt="User Avatar" class="user-avatar"/>
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
        // Logged-out view (Kept the original form structure)
        authContainer.innerHTML = `
            <h2>PROFILE & AUTH</h2>
            <p>Connect your account to sync your FBA team, save chat history, and get personalized insights.</p>
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
    console.log('🚀 DOM loaded. Initializing app...');
    
    // Start on the home screen
    showScreen('home');

    // Attach event listener for the chat input "Enter" key
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Close modal on outside click
    document.addEventListener('click', (e) => {
        const modal = document.getElementById('profile-modal');
        if (e.target === modal) {
            closeProfile();
        }
    });
});