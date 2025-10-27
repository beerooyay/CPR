// API Configuration - Firebase Functions
const API_BASE = ''; // Use relative URLs for same-origin requests
const MODEL = 'openai/gpt-oss-20b:free'; // Confirmed model
const LEAGUE_ID = '1267325171853701120'; // Legion Fantasy Football League ID

// State Management
let currentScreen = 'home';
let nivState = 'teams'; // 'teams' or 'roster'
let selectedTeam = null;
let cache = {}; // Data cache (cpr_rankings, niv_data, league_stats, dbContext)
let chatMessages = [];
let uploadedFile = null;

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
        const fragment = document.createDocumentFragment();

        rankings.forEach(team => {
            const row = document.createElement('div');
            row.className = `team-row ${team.rank === 1 ? 'gold' : ''}`;
            
            // Use TEAM NAME from Legion data, not user name
            const teamName = team.team_name || team.name || `Team ${team.rank}`;
            
            row.innerHTML = `
                <div class="team-row-header">
                    <div class="rank-badge">${team.rank}</div>
                    <div class="team-name">${teamName.toUpperCase()}</div>
                    <div class="cpr-value">${team.cpr.toFixed(3)}</div>
                </div>
                <div class="team-details">
                    <div class="metric-row">
                        <div class="metric-label">SLI (Starter Strength)</div>
                        <div class="metric-value ${team.sli > 0 ? 'positive' : team.sli < 0 ? 'negative' : ''}">${team.sli.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">BSI (Bench Strength)</div>
                        <div class="metric-value ${team.bsi > 0 ? 'positive' : team.bsi < 0 ? 'negative' : ''}">${team.bsi.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">SMI (Schedule Momentum)</div>
                        <div class="metric-value">${team.smi.toFixed(2)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">INGRAM (Positional Balance)</div>
                        <div class="metric-value ${team.ingram > 0 ? 'positive' : team.ingram < 0 ? 'negative' : ''}">${team.ingram.toFixed(3)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">ALVARADO (Draft Efficiency)</div>
                        <div class="metric-value ${team.alvarado > 0 ? 'positive' : team.alvarado < 0 ? 'negative' : ''}">${team.alvarado.toFixed(3)}</div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-label">ZION (4D Strength of Schedule)</div>
                        <div class="metric-value ${team.zion > 0 ? 'positive' : team.zion < 0 ? 'negative' : ''}">${team.zion.toFixed(3)}</div>
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
    const container = document.getElementById('niv-container');
    container.innerHTML = '<div class="loading">Loading team NIV metrics...</div>';
    
    try {
        console.log('Loading NIV data for Legion teams...');
        
        const response = await fetch(`/api/niv?league_id=${LEAGUE_ID}&season=2025`);
        if (!response.ok) throw new Error('Failed to fetch NIV data');
        
        const data = await response.json();
        const payload = data.data || data;
        const teamNivData = payload.team_niv || payload.team_rankings || payload;

        // Update cache
        cache.niv_data = teamNivData;

        container.innerHTML = '';
        const fragment = document.createDocumentFragment();

        teamNivData.forEach((team, index) => {
            const row = document.createElement('div');
            row.className = 'team-row';
            
            // Use TEAM NAME from Legion data
            const teamName = team.team_name || team.name || `Team ${index + 1}`;
            
            row.innerHTML = `
                <div class="team-row-header">
                    <div class="rank-badge">${index + 1}</div>
                    <div class="team-name">${teamName.toUpperCase()}</div>
                    <div class="cpr-value">${team.avg_niv.toFixed(3)}</div>
                </div>
            `;

            row.addEventListener('click', () => {
                selectedTeam = {
                    ...team,
                    rank: index + 1,
                    team_name: teamName
                };
                nivState = 'roster';
                console.log('Team clicked:', teamName, 'Loading roster view...');
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

        roster.forEach(player => {
            const row = document.createElement('div');
            row.className = 'player-row';
            
            // Get position and team info
            const position = player.position || 'N/A';
            const nflTeam = player.team || 'FA';
            
            row.innerHTML = `
                <div class="player-row-header">
                    <div class="player-name">${player.name} (${position} - ${nflTeam})</div>
                    <div class="niv-value">${player.niv ? player.niv.toFixed(3) : '0.000'}</div>
                </div>
                <div class="player-details">
                    <div class="last-year-stats-box">
                        <div class="stats-box-header">2024 NFL SEASON STATS</div>
                        <div class="stats-box-grid">
                            <div class="stats-box-item">
                                <div class="stats-box-label">FPTS</div>
                                <div class="stats-box-value">${player.fantasy_points || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">RUSH YDS</div>
                                <div class="stats-box-value">${player.rushing_yards || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">REC YDS</div>
                                <div class="stats-box-value">${player.receiving_yards || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">PASS YDS</div>
                                <div class="stats-box-value">${player.passing_yards || 0}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">TDS</div>
                                <div class="stats-box-value">${(player.rushing_tds || 0) + (player.receiving_tds || 0) + (player.passing_tds || 0)}</div>
                            </div>
                            <div class="stats-box-item">
                                <div class="stats-box-label">GAMES</div>
                                <div class="stats-box-value">${player.games_played || 0}</div>
                            </div>
                        </div>
                    </div>
                    <button class="scouting-report-button" onclick="getScoutingReport('${player.name}', '${position}')">GET SCOUTING REPORT</button>
                </div>
            `;

            row.addEventListener('click', (e) => {
                // Don't expand if clicking the scouting report button
                if (e.target.classList.contains('scouting-report-button')) {
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
    input.value = '';
    
    // Add loading message
    const loadingId = Date.now();
    chatMessages.push({ role: 'assistant', content: '', loading: true, id: loadingId });
    
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
        
        // Extract assistant response
        const assistantText = data.response || data.message || 'No response received';
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
    
    // Store file for sending with message
    uploadedFile = file;
    
    const chatInput = document.getElementById('chat-input');
    const fileName = file.name;
    const fileSize = (file.size / 1024).toFixed(2);
    
    // Show file in input as preview
    chatInput.value = `[FILE: ${fileName} (${fileSize}KB)] ${chatInput.value}`;
    console.log('File selected for upload:', fileName, fileSize + 'KB');
}

// Scouting Report Handler
function getScoutingReport(playerName, position) {
    const chatInput = document.getElementById('chat-input');
    chatInput.value = `Get me a detailed scouting report for ${playerName} (${position})`;
    
    // Switch to chat screen and send message
    showScreen('chat');
    setTimeout(() => sendMessage(), 100);
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
