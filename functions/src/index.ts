import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import * as cors from "cors";
import { Request, Response } from "express";

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

// Database Context - For AI chat
export const databaseContext = functions.https.onRequest(async (request: Request, response: Response) => {
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

// CPR Rankings - Main CPR endpoint
export const rankings = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      console.log('Loading CPR rankings...');
      
      const db = admin.firestore();
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;
      const week = parseInt(request.query.week as string);
      
      // Prefer 'latest' doc written by engine
      const latestDoc = await db.collection('cpr_rankings').doc('latest').get();
      if (latestDoc.exists && !week) {
        const rankingsData = latestDoc.data();
        const sortedRankings = (rankingsData?.rankings || []).sort((a: any, b: any) => b.cpr - a.cpr);
        const result = {
          rankings: sortedRankings,
          week: rankingsData?.week || 0,
          season: rankingsData?.season || CURRENT_SEASON,
          calculated_at: rankingsData?.calculation_timestamp || rankingsData?.calculated_at,
          total_teams: sortedRankings.length
        };
        response.status(200).json(createResponse(result));
        return;
      }

      const baseSnap = await db.collection('cpr_rankings')
        .where('league_id', '==', leagueId)
        .where('season', '==', season)
        .get();

      if (baseSnap.empty) {
        response.status(404).json(handleError(new Error('No CPR rankings found'), 'rankings'));
        return;
      }

      // If week specified, pick that record, else compute latest by max week
      let docData: any | null = null;
      if (week) {
        for (const d of baseSnap.docs) {
          const data = d.data();
          if (data.week === week) { docData = data; break; }
        }
      } else {
        let maxWeek = -1;
        for (const d of baseSnap.docs) {
          const data = d.data();
          if (typeof data.week === 'number' && data.week > maxWeek) {
            maxWeek = data.week; docData = data;
          }
        }
      }

      if (!docData) {
        response.status(404).json(handleError(new Error('No matching CPR rankings found'), 'rankings'));
        return;
      }
      const rankingsData = docData;
      
      // Sort by CPR score
      const sortedRankings = rankingsData.rankings.sort((a: any, b: any) => b.cpr - a.cpr);
      
      const result = {
        rankings: sortedRankings,
        week: rankingsData.week,
        season: rankingsData.season,
        calculated_at: rankingsData.calculated_at,
        total_teams: sortedRankings.length
      };
      
      response.status(200).json(createResponse(result));
      
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
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;
      
      if (!teamName) {
        response.status(400).json(handleError(new Error('Team name is required'), 'teamRoster'));
        return;
      }
      
      console.log(`Loading roster for team: ${teamName}`);
      
      const db = admin.firestore();
      
      // Get team info
      const teamSnapshot = await db.collection('teams')
        .where('league_id', '==', leagueId)
        .where('team_name', '==', teamName)
        .limit(1)
        .get();
      
      if (teamSnapshot.empty) {
        response.status(404).json(handleError(new Error('Team not found'), 'teamRoster'));
        return;
      }
      
      const teamData = teamSnapshot.docs[0].data();
      
      // Get NIV data for team players
      const nivAllSnap = await db.collection('niv_rankings')
        .where('league_id', '==', leagueId)
        .where('season', '==', season)
        .get();

      let teamNIVData: any[] = [];
      if (!nivAllSnap.empty) {
        // find latest week doc
        let latest: any = null; let maxWeek = -1;
        for (const d of nivAllSnap.docs) {
          const data = d.data();
          if (typeof data.week === 'number' && data.week > maxWeek) { maxWeek = data.week; latest = data; }
        }
        const allNIVData = (latest && (latest.player_rankings || latest.niv_data || [])) || [];
        teamNIVData = allNIVData.filter((player: any) => 
          teamData.roster.includes(player.player_id)
        );
      }
      
      const result = {
        team: teamData,
        niv_data: teamNIVData,
        season: season,
        calculated_at: new Date().toISOString()
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
      const { messages, context } = request.body || {};

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
      const systemPrompt = `you are jaylen hendricks, the cpr-nfl analyst. be concise, direct, and use the provided context when helpful. keep outputs tight and actionable.`;
      const orMessages = [
        { role: 'system', content: systemPrompt },
        ...(context ? [{ role: 'system', content: `context:\n${JSON.stringify(context).slice(0, 4000)}` }] : []),
        ...messages.map((m: any) => ({ role: m.role, content: String(m.content ?? '') }))
      ];

      const fetchRes = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: orMessages,
          temperature: 0.3,
        })
      });

      if (!fetchRes.ok) {
        const text = await fetchRes.text();
        throw new Error(`OpenRouter error ${fetchRes.status}: ${text}`);
      }

      const json: any = await fetchRes.json();
      const content = json?.choices?.[0]?.message?.content || '...';
      response.status(200).json(createResponse({ response: { role: 'assistant', content } }));
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

// NIV Rankings - Main NIV endpoint
// NIV Rankings - Read from Firestore (populated by Python pipeline)
export const niv = functions.https.onRequest(async (request: Request, response: Response) => {
  return corsHandler(request, response, async () => {
    try {
      console.log('Loading NIV rankings from Firestore...');
      
      const db = admin.firestore();
      const leagueId = request.query.league_id as string || DEFAULT_LEAGUE_ID;
      const season = parseInt(request.query.season as string) || CURRENT_SEASON;
      
      // Get NIV data from Firestore (populated by Python pipeline)
      const latestDoc = await db.collection('niv_rankings').doc('latest').get();
      
      if (!latestDoc.exists) {
        response.status(404).json(handleError(
          new Error('No NIV data found. Run Python pipeline: scripts/pipeline.py'), 
          'niv'
        ));
        return;
      }

      const nivData = latestDoc.data();
      const result = {
        player_rankings: nivData?.player_rankings || [],
        league_id: leagueId,
        season: season,
        calculated_at: nivData?.calculated_at,
        total_players: (nivData?.player_rankings || []).length,
        source: "Python pipeline"
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
