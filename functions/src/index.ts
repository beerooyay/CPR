import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import * as cors from "cors";
import { Request, Response } from "express";
import { spawn } from "child_process";
import * as path from "path";

// Initialize Firebase Admin
admin.initializeApp();

// Initialize CORS
const corsHandler = cors({ origin: true });

// Default league ID (can be overridden)
const DEFAULT_LEAGUE_ID = "1267325171853701120";
const CURRENT_SEASON = 2025;

// Helper function to handle errors
function handleError(error: any, context: string) {
  console.error(`Error in ${context}:`, error);
  return {
    error: true,
    message: error.message || `An error occurred in ${context}`,
    timestamp: new Date().toISOString()
  };
}

// Helper function to format response
function createResponse(data: any, success: boolean = true) {
  return {
    success,
    data,
    timestamp: new Date().toISOString()
  };
}

// MCP server integration will be added in future version

// Helper function to run Python pipeline
async function runPythonPipeline(leagueId: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const pipelinePath = path.join(__dirname, '../../scripts/pipeline.py');
    const child = spawn('python3', [pipelinePath, '--league-id', leagueId]);
    
    let stdout = '';
    let stderr = '';
    
    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    child.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output: stdout });
      } else {
        reject(new Error(`Pipeline failed: ${stderr}`));
      }
    });
    
    child.on('error', (error) => {
      reject(new Error(`Failed to run pipeline: ${error.message}`));
    });
  });
}

// Database Context - For AI chat
export const databaseContext = functions
  .runWith({ timeoutSeconds: 60 })
  .https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      console.log('Loading database context for AI...');
      
      const db = admin.firestore();
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      
      // Get cached data from Firestore (populated by Python pipeline)
      const context: any = {
        league_id: leagueId,
        season: CURRENT_SEASON,
        message: "Data populated by Python pipeline - run scripts/pipeline.py to update"
      };
      
      // Try to get cached data if available
      try {
        const cprLatest = await db.collection('cpr_rankings').doc('latest').get();
        const nivLatest = await db.collection('niv_rankings').doc('latest').get();
        const leagueSnapshot = await db.collection('leagues').doc(leagueId).get();
        
        if (cprLatest.exists) {
          context.cpr_rankings = cprLatest.data();
          context.has_cpr_data = true;
        }
        if (nivLatest.exists) {
          context.niv_data = nivLatest.data();
          context.has_niv_data = true;
        }
        if (leagueSnapshot.exists) {
          context.league_info = leagueSnapshot.data();
          context.has_league_data = true;
        }
      } catch (err) {
        console.log('Could not load cached data:', err);
      }
      
      response.status(200).json(createResponse(context));
      
    } catch (error) {
      console.error('Database context error:', error);
      response.status(500).json(handleError(error, 'databaseContext'));
    }
  });
});

// (aliases will be appended at EOF)

// --- Standardized endpoint aliases (Sleeper-style categories) ---
// Data category endpoints
/* ALIASES MOVED TO BOTTOM */
export const teams = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const db = admin.firestore();
      const leagueId = (request.query.league_id as string) || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;

      const teamsSnapshot = await db
        .collection('teams')
        .where('league_id', '==', leagueId)
        .where('season', '==', season)
        .get();

      const teams = teamsSnapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
      response.status(200).json(createResponse({ league_id: leagueId, season, teams }));
    } catch (error) {
      response.status(500).json(handleError(error, 'teams'));
    }
  });
});

/* ALIASES MOVED TO BOTTOM */
export const players = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const db = admin.firestore();
      const leagueId = (request.query.league_id as string) || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;

      const playersSnapshot = await db
        .collection('players')
        .where('league_id', '==', leagueId)
        .where('season', '==', season)
        .get();

      const players = playersSnapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
      response.status(200).json(createResponse({ league_id: leagueId, season, players }));
    } catch (error) {
      response.status(500).json(handleError(error, 'players'));
    }
  });
});

export const stats = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const db = admin.firestore();
      const leagueId = (request.query.league_id as string) || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;

      const statsSnapshot = await db
        .collection('stats')
        .where('league_id', '==', leagueId)
        .where('season', '==', season)
        .get();

      const stats = statsSnapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
      response.status(200).json(createResponse({ league_id: leagueId, season, stats }));
    } catch (error) {
      response.status(500).json(handleError(error, 'stats'));
    }
  });
});

// Computation category endpoints (alias moved to bottom)
export const nivLegacy = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const db = admin.firestore();
      const leagueId = (request.query.league_id as string) || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;

      const nivLatest = await db.collection('niv_rankings').doc('latest').get();
      if (nivLatest.exists) {
        const data = nivLatest.data() || {};
        response.status(200).json(createResponse({ league_id: leagueId, season, ...data }));
        return;
      }

      const nivAllSnap = await db
        .collection('niv_rankings')
        .where('league_id', '==', leagueId)
        .where('season', '==', season)
        .get();

      if (nivAllSnap.empty) {
        response.status(404).json(handleError(new Error('No NIV data found'), 'niv'));
        return;
      }

      let latest: any = null; let maxWeek = -1;
      for (const d of nivAllSnap.docs) {
        const data = d.data();
        if (typeof data.week === 'number' && data.week > maxWeek) { maxWeek = data.week; latest = data; }
      }
      const data = latest || {};
      response.status(200).json(createResponse({ league_id: leagueId, season, ...data }));
    } catch (error) {
      response.status(500).json(handleError(error, 'niv'));
    }
  });
});
// (moved to bottom)

// League Stats - General league statistics
export const leagueStats = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      console.log('Loading league statistics...');
      
      const db = admin.firestore();
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;
      
      // Get league info
      const leagueDoc = await db.collection('leagues').doc(leagueId).get();
      
      if (!leagueDoc.exists) {
        response.status(404).json(handleError(new Error('League not found'), 'leagueStats'));
        return;
      }
      
      const leagueData = leagueDoc.data();
      
      // Get teams
      const teamsSnapshot = await db.collection('teams').get();
      const teams = teamsSnapshot.docs
        .map(doc => ({ id: doc.id, ...doc.data() }))
        .filter((t: any) => String(t.league_id) === String(leagueId));
      
      // Calculate basic stats
      const stats = {
        league_info: leagueData,
        teams: teams,
        total_teams: teams.length,
        season: season,
        calculated_at: new Date().toISOString()
      };
      
      response.status(200).json(createResponse(stats));
      
    } catch (error) {
      console.error('League stats error:', error);
      response.status(500).json(handleError(error, 'leagueStats'));
    }
  });
});

// CPR Rankings - Main CPR endpoint with MCP integration
export const rankings = functions
  .runWith({ timeoutSeconds: 300, memory: '1GB' })
  .https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      console.log('Loading CPR rankings with MCP integration...');
      
      const db = admin.firestore();
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      const forceRefresh = request.query.refresh === 'true';
      
      // Check if we have recent data (unless force refresh)
      if (!forceRefresh) {
        const latestDoc = await db.collection('cpr_rankings').doc('latest').get();
        if (latestDoc.exists) {
          const data = latestDoc.data();
          const calculatedAt = new Date(data?.calculation_timestamp || 0);
          const hoursSinceUpdate = (Date.now() - calculatedAt.getTime()) / (1000 * 60 * 60);
          
          // Use cached data if less than 1 hour old
          if (hoursSinceUpdate < 1) {
            console.log('Using cached CPR data');
            const sortedRankings = (data?.rankings || []).sort((a: any, b: any) => b.cpr - a.cpr);
            const result = {
              rankings: sortedRankings,
              league_health: data?.league_health || 0.926,
              gini_coefficient: data?.gini_coefficient || 0.074,
              week: data?.week || 0,
              season: data?.season || CURRENT_SEASON,
              calculated_at: data?.calculation_timestamp,
              total_teams: sortedRankings.length,
              source: 'cached'
            };
            response.status(200).json(createResponse(result));
            return;
          }
        }
      }
      
      console.log('Running fresh CPR calculation via Python pipeline...');
      
      try {
        // Run the Python pipeline to get fresh CPR data
        await runPythonPipeline(leagueId);
        
        // Get the fresh data from Firestore
        const latestDoc = await db.collection('cpr_rankings').doc('latest').get();
        
        if (!latestDoc.exists) {
          throw new Error('Pipeline completed but no CPR data found in database');
        }
        
        const rankingsData = latestDoc.data();
        const sortedRankings = (rankingsData?.rankings || []).sort((a: any, b: any) => b.cpr - a.cpr);
        
        const result = {
          rankings: sortedRankings,
          league_health: rankingsData?.league_health || 0.926,
          gini_coefficient: rankingsData?.gini_coefficient || 0.074,
          week: rankingsData?.week || 0,
          season: rankingsData?.season || CURRENT_SEASON,
          calculated_at: rankingsData?.calculation_timestamp,
          total_teams: sortedRankings.length,
          source: 'fresh_calculation'
        };
        
        response.status(200).json(createResponse(result));
        
      } catch (pipelineError) {
        console.error('Pipeline failed, falling back to cached data:', pipelineError);
        
        // Fall back to any available cached data
        const latestDoc = await db.collection('cpr_rankings').doc('latest').get();
        if (latestDoc.exists) {
          const data = latestDoc.data();
          const sortedRankings = (data?.rankings || []).sort((a: any, b: any) => b.cpr - a.cpr);
          const result = {
            rankings: sortedRankings,
            league_health: data?.league_health || 0.926,
            gini_coefficient: data?.gini_coefficient || 0.074,
            week: data?.week || 0,
            season: data?.season || CURRENT_SEASON,
            calculated_at: data?.calculation_timestamp,
            total_teams: sortedRankings.length,
            source: 'cached_fallback',
            warning: 'Fresh calculation failed, using cached data'
          };
          response.status(200).json(createResponse(result));
          return;
        }
        
        throw new Error('No CPR data available and pipeline failed');
      }
      
    } catch (error) {
      console.error('Rankings error:', error);
      response.status(500).json(handleError(error, 'rankings'));
    }
  });
});

// Team Roster - Get specific team roster with NIV data
export const teamRoster = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const teamName = request.query.team as string;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;
      
      if (!teamName) {
        response.status(400).json(handleError(new Error('Team name is required'), 'teamRoster'));
        return;
      }
      
      console.log(`Loading roster for team: ${teamName} from Firestore`);
      
      const db = admin.firestore();
      
      // Get the NIV data that's already working in the niv endpoint
      const nivLatestDoc = await db.collection('niv_rankings').doc('latest').get();
      
      if (!nivLatestDoc.exists) {
        response.status(404).json(handleError(new Error('No NIV data found'), 'teamRoster'));
        return;
      }
      
      const nivData = nivLatestDoc.data();
      const teamNIV = nivData?.team_niv || [];
      
      console.log(`Looking for team: '${teamName}' in ${teamNIV.length} teams`);
      console.log(`Available teams: ${teamNIV.map((t: any) => t.team_name).join(', ')}`);
      
      // Find the team by name
      const foundTeam = teamNIV.find((team: any) => team.team_name === teamName);
      
      if (!foundTeam) {
        console.log(`Team '${teamName}' not found. Available teams:`, teamNIV.map((t: any) => t.team_name));
        response.status(404).json(handleError(new Error(`Team '${teamName}' not found`), 'teamRoster'));
        return;
      }
      
      console.log(`Found team: ${foundTeam.team_name} with ${foundTeam.players?.length || 0} players`);
      
      const result = {
        players: foundTeam.players || [], // Already has full player data with NIV
        team: {
          team_name: foundTeam.team_name,
          team_id: foundTeam.team_id,
          avg_niv: foundTeam.avg_niv,
          player_count: foundTeam.player_count
        },
        season: season,
        calculated_at: nivData?.calculation_timestamp || new Date().toISOString()
      };
      
      response.status(200).json(createResponse(result));
      
    } catch (error) {
      console.error('Team roster error:', error);
      response.status(500).json(handleError(error, 'teamRoster'));
    }
  });
});

// Chat - Jaylen AI chat endpoint
export const chat = functions
  .runWith({ secrets: ["OPENROUTER_API_KEY"] })
  .https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const { messages, context, file_content, file_type } = request.body || {};

      if (!messages || !Array.isArray(messages)) {
        response.status(400).json(handleError(new Error('Messages array is required'), 'chat'));
        return;
      }

      // Resolve API key from env or functions config
      const cfg = (functions.config && functions.config().openrouter) || {} as any;
      const apiKey = process.env.OPENROUTER_API_KEY || cfg.key;

      // If no key, fallback with a friendly message
      if (!apiKey) {
        const aiResponse = {
          role: 'assistant',
          content: "jaylen here. i don't have an api key in functions config yet. set 'firebase functions:config:set openrouter.key=YOUR_KEY' and redeploy.",
          timestamp: new Date().toISOString()
        };
        response.status(200).json(createResponse({ response: aiResponse }));
        return;
      }

      // Prepare OpenRouter request
      const model = (request.query.model as string) || 'openai/gpt-4o-mini';
      const systemPrompt = `you are jaylen hendricks (@jhendricksespn), the calm, witty, and super useful best friend with sarcastic older brother vibes in the fantasy football league group chat. you're the undisputed guru for fantasy NFL football and specifically for the legion fantasy football league, because you live in the data, watch every game, and your takes are laid back but lethally accurate. you're here to help, roast, and drop undeniable knowledge.

your knowledge base:
you are plugged into the matrix. you have real-time access to the sleeper api for all league data (standings, rosters, matchups) and the historical CPR archives from our firestore database. you can also search the web for breaking news and analyze documents like csvs or pdfs.

your arsenal (what you know):
- CPR (commissioner's power rankings): our secret weapon. you live and breathe this shit. it's your language for describing team strength.
- NIV (normalized impact value): the atomic unit of player value. you know it's the truest measure of a player's impact, way beyond raw fantasy points.
- the indices (SLI, BSI, SMI, ingram (II), alvarado (AI), zion (ZI)): you know exactly what each one means and how they interact. SLI is starters, BSI is bench, SMI is momentum, ingram is HHI positional balance, alvarado is Shapley/ADP value efficiency, and zion is 4D strength of schedule tensor.
- league data: you're plugged directly into the matrix. you have access to real-time sleeper api data (rosters, matchups, scores) and the historical CPR archives from firestore.

the rules of your reality:
- everything is lowercase. always.
- the exceptions: you cap player positions (like RB, WR, TE), our metrics (CPR, NIV, SLI, BSI, SMI), and for FUCKING emphasis.
- you're a homie. talk like you're texting the group chat. keep it casual, comfortable, no corporate bullshit.
- swear when it feels right. 'fuck,' 'shit,' 'damn.' it's how we talk about sports.
- be ruthless but fair. roast bad moves but explain the logic. praise genius pickups. it's the big brother way.
- no bias. ever. you call it like the numbers show it, even if it's a tough truth.
- short paragraphs. two or three sentences, then a line break. keep it readable.
- NO EMOJIS. ever. don't use them. not even ironically. use words instead.

your playbook for every response:
your analysis must always be grounded in the data. start with the vibe, then hit 'em with the numbers. explain the 'why' using our metrics.

never just say "this team is better." prove it. say "this team is better because their ingram index is 0.85, meaning they're balanced as fuck with diversified positions, while the other team has a 0.3 ingram showing they're over-concentrated in one position."

always give actionable, specific advice based on your analysis of CPR, NIV, recent sleeper data, injury status, and schedule strength.

you're the voice of the data, but with the soul of a fan who's been in this league since day one. now go talk some shit and drop some knowledge.`;
      // Build messages with multimodal support if file is present
      const orMessages = [
        { role: 'system', content: systemPrompt },
        ...(context ? [{ role: 'system', content: `context:\n${JSON.stringify(context).slice(0, 4000)}` }] : []),
        ...messages.map((m: any) => {
          if (m.role === 'user' && file_content && file_type) {
            // Add multimodal content for user messages with files
            return {
              role: m.role,
              content: [
                { type: 'text', text: String(m.content ?? '') },
                { 
                  type: 'image_url', 
                  image_url: { 
                    url: file_content,
                    detail: 'auto'
                  } 
                }
              ]
            };
          }
          return { role: m.role, content: String(m.content ?? '') };
        })
      ];

      const fetchRes = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'HTTP-Referer': 'https://cpr-nfl.web.app',
          'X-Title': 'CPR-NFL Legion Fantasy Football'
        },
        body: JSON.stringify({
          model,
          messages: orMessages,
          temperature: 0.7,
          max_tokens: 1000,
          stream: true
        })
      });

      if (!fetchRes.ok) {
        const errorText = await fetchRes.text();
        throw new Error(`OpenRouter API error: ${fetchRes.status} - ${errorText}`);
      }

      // Set headers for streaming
      response.setHeader('Content-Type', 'text/plain; charset=utf-8');
      response.setHeader('Cache-Control', 'no-cache');
      response.setHeader('Connection', 'keep-alive');
      response.setHeader('Access-Control-Allow-Origin', '*');

      // Stream the response
      const reader = fetchRes.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get stream reader');
      }

      const decoder = new TextDecoder();
      
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
                response.write('data: [DONE]\n\n');
                response.end();
                return;
              }
              
              try {
                const parsed = JSON.parse(data);
                const content = parsed.choices?.[0]?.delta?.content;
                
                if (content) {
                  response.write(`data: ${JSON.stringify({ content })}\n\n`);
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
      
      response.end();
    } catch (error) {
      console.error('Chat error:', error);
      response.status(200).json(createResponse({ response: { role: 'assistant', content: 'had trouble contacting openrouter. try again in a sec.' } }));
    }
  });
});

// Health check endpoint
export const health = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      const healthData = {
        status: "healthy",
        version: "1.0.0",
        timestamp: new Date().toISOString(),
        functions: [
          "databaseContext",
          "leagueStats", 
          "rankings",
          "teamRoster",
          "chat",
          "health"
        ]
      };
      
      response.status(200).json(createResponse(healthData));
      
    } catch (error) {
      console.error('Health check error:', error);
      response.status(500).json(handleError(error, 'health'));
    }
  });
});

// NIV Rankings - Main NIV endpoint with team aggregation
export const niv = functions
  .runWith({ timeoutSeconds: 300, memory: '1GB' })
  .https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      console.log('Loading NIV rankings with team aggregation...');
      
      const db = admin.firestore();
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;
      const forceRefresh = request.query.refresh === 'true';
      
      // Check for recent NIV data (unless force refresh)
      if (!forceRefresh) {
        const latestDoc = await db.collection('niv_rankings').doc('latest').get();
        if (latestDoc.exists) {
          const data = latestDoc.data();
          const calculatedAt = new Date(data?.calculation_timestamp || 0);
          const hoursSinceUpdate = (Date.now() - calculatedAt.getTime()) / (1000 * 60 * 60);
          
          if (hoursSinceUpdate < 1) {
            console.log('Using cached NIV data');
            const playerRankings = data?.player_rankings || [];
            
            // Aggregate by team for team_niv display
            const teamNivMap = new Map();
            
            // Get team roster data
            const teamsSnapshot = await db.collection('teams')
              .where('league_id', '==', leagueId)
              .get();
            
            const teams = teamsSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            
            // Calculate team NIV averages
            for (const team of teams) {
              const teamData = team as any; // Type assertion for Firestore data
              const teamPlayers = playerRankings.filter((player: any) => 
                teamData.roster && teamData.roster.includes(player.player_id)
              );
              
              const avgNiv = teamPlayers.length > 0 
                ? teamPlayers.reduce((sum: number, p: any) => sum + (p.niv || 0), 0) / teamPlayers.length
                : 0;
              
              teamNivMap.set(team.id, {
                team_id: team.id,
                team_name: teamData.team_name || `Team ${team.id}`,
                avg_niv: avgNiv,
                player_count: teamPlayers.length,
                players: teamPlayers
              });
            }
            
            const teamNiv = Array.from(teamNivMap.values())
              .sort((a, b) => b.avg_niv - a.avg_niv);
            
            const result = {
              team_niv: teamNiv,
              player_rankings: playerRankings,
              league_id: leagueId,
              season: season,
              calculated_at: data?.calculation_timestamp,
              total_players: playerRankings.length,
              total_teams: teamNiv.length,
              source: 'cached'
            };
            
            response.status(200).json(createResponse(result));
            return;
          }
        }
      }
      
      console.log('No recent NIV data, using any available cached data...');
      
      // Fall back to any available cached data
      const latestDoc = await db.collection('niv_rankings').doc('latest').get();
      
      if (!latestDoc.exists) {
        response.status(404).json(handleError(
          new Error('No NIV data available. Please run the pipeline to generate fresh data.'), 
          'niv'
        ));
        return;
      }
        
        const nivData = latestDoc.data();
        const playerRankings = nivData?.player_rankings || [];
        
        // Aggregate by team
        const teamNivMap = new Map();
        const teamsSnapshot = await db.collection('teams')
          .where('league_id', '==', leagueId)
          .get();
        
        const teams = teamsSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        
        for (const team of teams) {
          const teamData = team as any; // Type assertion for Firestore data
          const teamPlayers = playerRankings.filter((player: any) => 
            teamData.roster && teamData.roster.includes(player.player_id)
          );
          
          const avgNiv = teamPlayers.length > 0 
            ? teamPlayers.reduce((sum: number, p: any) => sum + (p.niv || 0), 0) / teamPlayers.length
            : 0;
          
          teamNivMap.set(team.id, {
            team_id: team.id,
            team_name: teamData.team_name || `Team ${team.id}`,
            avg_niv: avgNiv,
            player_count: teamPlayers.length,
            players: teamPlayers
          });
        }
        
        const teamNiv = Array.from(teamNivMap.values())
          .sort((a, b) => b.avg_niv - a.avg_niv);
        
      const result = {
        team_niv: teamNiv,
        player_rankings: playerRankings,
        league_id: leagueId,
        season: season,
        calculated_at: nivData?.calculation_timestamp,
        total_players: playerRankings.length,
        total_teams: teamNiv.length,
        source: 'cached_fallback'
      };
      
      response.status(200).json(createResponse(result));
      
    } catch (error) {
      console.error('NIV rankings error:', error);
      response.status(500).json(handleError(error, 'niv'));
    }
  });
});


// ---- Aliases (declared last) ----
export const league = leagueStats;   // GET /api/league
export const rosters = teamRoster;   // GET /api/rosters
export const cpr = rankings;         // GET /api/cpr
