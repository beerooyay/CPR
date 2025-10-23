const functions = require('firebase-functions');
const cors = require('cors')({origin: true});
const admin = require('firebase-admin');

if (!admin.apps.length) {
    admin.initializeApp();
}
const db = admin.firestore();

// OpenRouter Chat Proxy Function
exports.chatProxy = functions.https.onRequest(async (req, res) => {
    cors(req, res, async () => {
        if (req.method !== 'POST') {
            return res.status(405).send('Method not allowed');
        }

        try {
            // Get API key from Firebase config
            const openrouterKey = functions.config().openrouter?.api_key;
            
            if (!openrouterKey) {
                console.error('OpenRouter API key not configured');
                return res.status(500).json({
                    error: 'OpenRouter API key not configured in Firebase'
                });
            }

            // Forward request to OpenRouter
            const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${openrouterKey}`,
                    'Content-Type': 'application/json',
                    'HTTP-Referer': req.headers.origin || 'https://cpr-app-54c15.web.app'
                },
                body: JSON.stringify(req.body)
            });

            if (!response.ok) {
                const errorData = await response.text();
                console.error('OpenRouter API error:', response.status, errorData);
                return res.status(response.status).send(errorData);
            }

            // If streaming, manually pipe chunks (Node fetch returns ReadableStream, not Node stream)
            if (req.body.stream) {
                res.setHeader('Content-Type', 'text/event-stream');
                res.setHeader('Cache-Control', 'no-cache');
                res.setHeader('Connection', 'keep-alive');
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                try {
                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;
                        res.write(decoder.decode(value, {stream: true}));
                    }
                    res.end();
                } catch (streamError) {
                    console.error('Stream error:', streamError);
                    res.end();
                }
            } else {
                // If not streaming, return JSON
                const data = await response.json();
                return res.status(200).json(data);
            }

        } catch (error) {
            console.error('Chat proxy error:', error);
            return res.status(500).json({
                error: 'Failed to process chat request',
                details: error.message
            });
        }
    });
});

// Firestore API: CPR rankings
exports.rankings = functions.https.onRequest(async (req, res) => {
    cors(req, res, async () => {
        try {
            const season = req.query.season || '2025';
            const teamsRef = db.collection('teams');
            const snapshot = await teamsRef.get();
            const rankings = [];

            for (const doc of snapshot.docs) {
                const team = doc.data() || {};
                const seasonDoc = await doc.ref.collection('seasons').doc(`season_${season}`).get();
                if (seasonDoc.exists) {
                    const m = seasonDoc.data() || {};
                    rankings.push({
                        team: team.team_name || '',
                        cpr: m.cpr_score || 0,
                        sli: m.sli_score || 0,
                        bsi: m.bsi_score || 0,
                        smi: m.smi_score || 0,
                        ingram: m.ingram_index || 0,
                        alvarado: m.alvarado_index || 0,
                        zion: m.zion_index || 0,
                        rank: m.rank || 0
                    });
                }
            }

            rankings.sort((a, b) => (b.cpr || 0) - (a.cpr || 0));
            rankings.forEach((t, i) => (t.rank = i + 1));

            return res.status(200).json(rankings);
        } catch (e) {
            console.error('rankings error:', e);
            return res.status(200).json([]);
        }
    });
});

// Firestore API: Teams with players
exports.teams = functions.https.onRequest(async (req, res) => {
    cors(req, res, async () => {
        try {
            const season = req.query.season || '2025';
            const playersRef = db.collection('players');
            const snapshot = await playersRef.get();
            const teamRosters = {};

            for (const doc of snapshot.docs) {
                const playerName = doc.id;
                const seasonDoc = await doc.ref.collection('seasons').doc(`season_${season}`).get();
                if (!seasonDoc.exists) continue;
                const s = seasonDoc.data() || {};
                const team = s.team || 'Unknown';
                if (!teamRosters[team]) teamRosters[team] = [];
                teamRosters[team].push({
                    name: playerName,
                    niv: s.niv_final || 0,
                    fp: s.fantasy_points || 0,
                    health: s.health_factor ?? 1.0,
                    consistency: s.consistency ?? 1.0,
                    alvarado: s.alvarado_index || 0,
                    pts: s.pts || 0,
                    reb: s.reb || 0,
                    ast: s.ast || 0,
                    stl: s.stl || 0,
                    blk: s.blk || 0,
                    to: s.tov || 0,
                    fg_pct: s.fg_pct || 0,
                    ft_pct: s.ft_pct || 0,
                    threes: s.tpm || 0
                });
            }

            const teams = Object.keys(teamRosters).map(name => {
                const players = teamRosters[name].sort((a, b) => (b.niv || 0) - (a.niv || 0));
                return { name, players };
            });

            return res.status(200).json(teams);
        } catch (e) {
            console.error('teams error:', e);
            return res.status(200).json([]);
        }
    });
});

// Firestore API: League stats
exports.leagueStats = functions.https.onRequest(async (req, res) => {
    cors(req, res, async () => {
        try {
            const season = req.query.season || '2025';
            const docRef = db.collection('league_metrics').doc(`season_${season}`);
            const docSnap = await docRef.get();
            if (docSnap.exists) {
                const d = docSnap.data() || {};
                return res.status(200).json({
                    gini: d.gini_coefficient || 0,
                    health: d.league_health_index ?? 0.926
                });
            }
            return res.status(200).json({ gini: 0.0, health: 0.926 });
        } catch (e) {
            console.error('league-stats error:', e);
            return res.status(200).json({ gini: 0.0, health: 0.926 });
        }
    });
});

// Firestore API: Database context for AI
exports.databaseContext = functions.https.onRequest(async (req, res) => {
    cors(req, res, async () => {
        try {
            const season = req.query.season || '2025';
            const topPlayers = [];
            const playersRef = db.collection('players');
            const snapshot = await playersRef.get();

            for (const doc of snapshot.docs) {
                const playerName = doc.id;
                const seasonDoc = await doc.ref.collection('seasons').doc(`season_${season}`).get();
                if (!seasonDoc.exists) continue;
                const s = seasonDoc.data() || {};
                topPlayers.push({
                    player_name: playerName,
                    niv_adjusted: s.niv_final || 0,
                    fantasy_points: s.fantasy_points || 0,
                    team: s.team || ''
                });
            }

            topPlayers.sort((a, b) => (b.niv_adjusted || 0) - (a.niv_adjusted || 0));
            const top20 = topPlayers.slice(0, 20);

            const [rankingsResp, leagueResp] = await Promise.all([
                (async () => {
                    const list = [];
                    const teamsRef = db.collection('teams');
                    const snap = await teamsRef.get();
                    for (const d of snap.docs) {
                        const team = d.data() || {};
                        const seasonDoc = await d.ref.collection('seasons').doc(`season_${season}`).get();
                        if (seasonDoc.exists) {
                            const m = seasonDoc.data() || {};
                            list.push({ team: team.team_name || '', cpr: m.cpr_score || 0 });
                        }
                    }
                    list.sort((a, b) => (b.cpr || 0) - (a.cpr || 0));
                    return list;
                })(),
                (async () => {
                    const d = await db.collection('league_metrics').doc(`season_${season}`).get();
                    if (d.exists) {
                        const v = d.data() || {};
                        return { gini: v.gini_coefficient || 0, health: v.league_health_index ?? 0.926 };
                    }
                    return { gini: 0.0, health: 0.926 };
                })()
            ]);

            return res.status(200).json({
                top_players: top20,
                rankings: rankingsResp,
                league: leagueResp
            });
        } catch (e) {
            console.error('database-context error:', e);
            return res.status(200).json({ top_players: [], rankings: [], league: {} });
        }
    });
});

// ESPN Data Fetch Function (optional - if you want ESPN fetching in cloud too)
exports.fetchESPNData = functions.https.onRequest(async (req, res) => {
    cors(req, res, async () => {
        try {
            const leagueId = req.query.league_id || functions.config().espn?.league_id;
            const year = req.query.year || new Date().getFullYear();
            
            // Since espn-api is Python, we'd need to rewrite in JS
            // or call a Python Cloud Function
            // For now, just return a placeholder
            
            return res.status(200).json({
                message: 'ESPN fetching would go here',
                league_id: leagueId,
                year: year
            });
            
        } catch (error) {
            console.error('ESPN fetch error:', error);
            return res.status(500).json({error: error.message});
        }
    });
});
