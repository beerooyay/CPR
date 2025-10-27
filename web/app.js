// API Configuration - Firebase Functions
const API_BASE = ''; // Use relative URLs for same-origin requests
const MODEL = 'openai/gpt-oss-20b:free'; // Updated model
const LEAGUE_ID = '1267325171853701120'; // Your league ID

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
        
        const response = await fetch(`/api/databaseContext?league_id=${LEAGUE_ID}`, { signal: controller.signal });
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
            fetch(`/api/league?league_id=${LEAGUE_ID}&season=2025`, { signal: controller.signal }),
            fetch(`/api/cpr?league_id=${LEAGUE_ID}&season=2025`, { signal: controller.signal })
        ]);
        
        clearTimeout(timeoutId);

        if (!statsRes.ok || !rankingsRes.ok) {
            throw new Error(`Failed to fetch CPR data: stats(${statsRes.status}), rankings(${rankingsRes.status})`);
        }

        const statsJson = await statsRes.json();
        const rankingsJson = await rankingsRes.json();
        const stats = statsJson.data || statsJson;
        const rankingsPayload = (rankingsJson.data && rankingsJson.data) || rankingsJson;
        const rankings = rankingsPayload.rankings || rankingsPayload;

        // Update cache
        cache.stats = stats;
        cache.rankings = rankings;

        // Update league stats from CPR payload when available, else compute from rankings
        const healthFromApi = rankingsPayload.league_health;
        const giniFromApi = rankingsPayload.gini_coefficient;
        let leagueHealth = typeof healthFromApi === 'number' ? healthFromApi : null;
        let giniCoeff = typeof giniFromApi === 'number' ? giniFromApi : null;

        if (leagueHealth == null || giniCoeff == null) {
            // compute gini from CPR list as fallback
            const values = (rankings || []).map(t => t.cpr).filter(v => typeof v === 'number');
            const n = values.length;
            if (n > 0) {
                const sorted = values.slice().sort((a,b)=>a-b);
                const sum = sorted.reduce((a,b)=>a+b,0);
                if (sum > 0) {
                    let cum = 0;
                    for (let i=0;i<n;i++) cum += (i+1)*sorted[i];
                    giniCoeff = (n+1 - 2*cum/sum) / n;
                    giniCoeff = Math.max(0, Math.min(1, giniCoeff));
                    leagueHealth = Math.max(0, 1 - giniCoeff);
                } else {
                    giniCoeff = 0;
                    leagueHealth = 1;
                }
            } else {
                giniCoeff = 0;
                leagueHealth = 1;
            }
        }

        const healthEl = document.getElementById('league-health');
        const giniEl = document.getElementById('gini-coeff');
        if (healthEl) healthEl.textContent = `${(leagueHealth * 100).toFixed(1)}%`;
        if (giniEl) giniEl.textContent = (giniCoeff).toFixed(3);

        // Clear and build rankings
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        rankings.forEach(team => {
            const row = document.createElement('div');
            row.className = `team-row ${team.rank === 1 ? 'gold' : ''}`;
            const teamName = (team.team_name || team.team || '').toString();
            row.dataset.team = teamName;
            
            const alvaradoValue = team.alvarado != null ? team.alvarado.toFixed(2) : '0.00';

            row.innerHTML = `
                <div class="neon-border"></div>
                <div class="team-row-header">
                    <div class="rank-badge">${team.rank}</div>
                    <div class="team-name">${teamName.toUpperCase()}</div>
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
                </div>
            `;

            // Add click handler for expanding/collapsing
            row.addEventListener('click', (e) => {
                // Don't expand if clicking on the claim button
                if (e.target.classList.contains('claim-team-btn')) {
                    return;
                }
                row.classList.toggle('expanded');
            });

            fragment.appendChild(row);
        });

        container.appendChild(fragment);

        // Add mode button handlers
        document.querySelectorAll('.mode-button').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // TODO: Reload CPR data with new mode
                console.log('Alvarado mode changed to:', btn.dataset.mode);
            });
        });

    } catch (error) {
        console.error('Error loading CPR screen:', error);
        container.innerHTML = '<div class="error">Failed to load CPR rankings. Please try again.</div>';
    }
}

// --- NIV Screen Logic ---

async function loadNIVTeams() {
    const container = document.getElementById('niv-container');
    container.innerHTML = '<div class="loading-state">Loading teams...</div>';
    
    try {
        // Use cached rankings or fetch new ones
        let rankings = cache.rankings;
        if (!rankings) {
            const response = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
            if (!response.ok) throw new Error('Failed to fetch NIV data');
            const rj = await response.json();
            const payload = (rj.data && rj.data) || rj;
            const playerRankings = payload.player_rankings || [];
            
            // Group players by team for team view
            const teamMap = {};
            playerRankings.forEach(player => {
                const teamId = player.team_id || 'FREE';
                if (!teamMap[teamId]) {
                    teamMap[teamId] = {
                        team_id: teamId,
                        team_name: teamId === 'FREE' ? 'Free Agents' : teamId,
                        players: [],
                        avg_niv: 0
                    };
                }
                teamMap[teamId].players.push(player);
            });
            
            // Calculate team averages and convert to array
            rankings = Object.values(teamMap).map(team => {
                const avgNiv = team.players.reduce((sum, p) => sum + p.niv, 0) / team.players.length;
                return {
                    team_id: team.team_id,
                    team: team.team_name,
                    rank: 0, // Will be set below
                    cpr: avgNiv, // Use NIV as the ranking metric for display
                    avg_niv: avgNiv,
                    player_count: team.players.length
                };
            }).sort((a, b) => b.avg_niv - a.avg_niv);
            
            // Set ranks after sorting
            rankings.forEach((team, index) => {
                team.rank = index + 1;
            });
            
            cache.rankings = rankings;
        }

        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        rankings.forEach(team => {
            const row = document.createElement('div');
            row.className = 'team-row';
            row.innerHTML = `
                <div class="team-row-header">
                    <div class="rank-badge">${team.rank}</div>
                    <div class="team-name">${team.team.toUpperCase()}</div>
                    <div class="cpr-value">${team.avg_niv.toFixed(3)}</div>
                </div>
            `;

            row.addEventListener('click', () => {
                selectedTeam = team;
                nivState = 'roster';
                console.log('Team clicked:', team.name, 'Loading roster view...');
                showScreen('niv');
            });

            fragment.appendChild(row);
        });

        container.appendChild(fragment);
    } catch (error) {
        console.error('Error loading NIV teams:', error);
        container.innerHTML = '<div class="error">Failed to load teams.</div>';
    }
}

async function loadNIVRoster(team) {
    const container = document.getElementById('niv-container');
    const statsContainer = document.getElementById('niv-stats-container');
    
    // Show team stats
    statsContainer.style.display = 'grid';
    statsContainer.innerHTML = `
        <div class="glass-card">
            <div class="stat-label">TEAM CPR</div>
            <div class="stat-value">${team.cpr.toFixed(3)}</div>
        </div>
        <div class="glass-card">
            <div class="stat-label">RANK</div>
            <div class="stat-value">#${team.rank}</div>
        </div>
    `;

    container.innerHTML = '<div class="loading-state">Loading roster...</div>';
    
    try {
        const response = await fetch(`/api/rosters?team=${encodeURIComponent(team.team_name || team.team || '')}&league_id=${LEAGUE_ID}&season=2025`);
        if (!response.ok) throw new Error('Failed to fetch roster');
        const rosterJson = await response.json();
        const rosterPayload = rosterJson.data || rosterJson;
        const roster = rosterPayload.niv_data || rosterPayload;
        
        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        roster.forEach(player => {
            const row = document.createElement('div');
            row.className = 'player-row';
            row.innerHTML = `
                <div class="player-row-header">
                    <div class="player-name">${player.name}</div>
                    <div class="niv-value">${player.niv ? player.niv.toFixed(2) : '0.00'}</div>
                </div>
                <div class="player-details">
                    <div class="last-year-stats-box">
                        <div class="stats-box-header">2024 SEASON STATS</div>
                        <div class="stats-box-grid">
                            <div class="stats-box-item">
                                <div class="stats-box-label">PTS</div>
                                <div class="stats-box-value">${player.pts || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">REB</div>
                                <div class="stats-box-value">${player.reb || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">AST</div>
                                <div class="stats-box-value">${player.ast || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">STL</div>
                                <div class="stats-box-value">${player.stl || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">BLK</div>
                                <div class="stats-box-value">${player.blk || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">TO</div>
                                <div class="stats-box-value">${player.to || 0}</div>
                            </div>
                        </div>
                    </div>
                    <button class="scouting-report-button">GET SCOUTING REPORT</button>
                </div>
            `;

            row.addEventListener('click', () => {
                row.classList.toggle('expanded');
            });

            fragment.appendChild(row);
        });

        container.appendChild(fragment);
    } catch (error) {
        console.error('Error loading roster:', error);
        container.innerHTML = '<div class="error">Failed to load roster.</div>';
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
                        <strong>what's up, i'm jaylen hendricks.</strong><br><br>
                        i've got your cpr rankings, player niv, and trade logic loaded. ask me anything about teams, players, or strategy.<br><br>
                        <em>what's on your mind?</em>
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
    
    // Add user message
    chatMessages.push({ role: 'user', content: message });
    input.value = '';
    
    // Add loading message
    const loadingId = Date.now();
    chatMessages.push({ role: 'assistant', content: '', loading: true, id: loadingId });
    
    renderChatMessages();
    
    try {
        const dbContext = await loadDatabaseContext();
        
        const response = await fetch(`/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: chatMessages.filter(m => !m.loading),
                context: dbContext
            })
        });
        
        if (!response.ok) throw new Error('Chat request failed');
        
        const data = await response.json();
        
        // Remove loading message
        chatMessages = chatMessages.filter(m => m.id !== loadingId);
        
        // Add assistant response
        const assistantText = (data && data.data && data.data.response && (data.data.response.content || data.data.response))
            || data.response?.content || data.response || data.message || '...';
        chatMessages.push({ role: 'assistant', content: assistantText });
        
        renderChatMessages();
    } catch (error) {
        console.error('Chat error:', error);
        // Remove loading message
        chatMessages = chatMessages.filter(m => m.id !== loadingId);
        
        // Add error message
        chatMessages.push({ 
            role: 'assistant', 
            content: 'sorry fam, had trouble connecting to jaylen. try again in a sec.' 
        });
        
        renderChatMessages();
    }
}

function renderChatMessages() {
    const container = document.getElementById('chat-messages');
    const isScrolledToBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
    
    container.innerHTML = chatMessages.map(msg => {
        if (msg.loading) {
            return `
                <div class="message assistant">
                    <div class="message-avatar">
                        <img src="/assets/jaylen.png" alt="Jaylen Hendricks">
                    </div>
                    <div class="message-bubble">
                        <div class="loading-spinner"></div>
                    </div>
                </div>
            `;
        }
        
        const isUser = msg.role === 'user';
        return `
            <div class="message ${isUser ? 'user' : 'assistant'}">
                <div class="message-avatar">
                    ${isUser ? '' : '<img src="/assets/jaylen.png" alt="Jaylen Hendricks">'}
                </div>
                <div class="message-bubble">
                    <div class="message-text">${msg.content}</div>
                </div>
            </div>
        `;
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
    console.log('🚀 DOM loaded. Initializing NFL CPR app...');
    
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
