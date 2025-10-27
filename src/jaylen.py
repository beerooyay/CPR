"""Jaylen Hendricks AI Agent - Legion Fantasy Football Insider and Sports Data Expert"""
import os
import json
import requests
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class JaylenAI:
    """Jaylen Hendricks AI agent with OpenRouter and MCP integration"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # OpenRouter configuration
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b:free')
        
        # System prompt
        self.system_prompt = self._get_system_prompt()
        
        # MCP client (will be initialized later)
        self.mcp_client = None
        
        # Database connection
        self.db = None
        
        logger.info(f"Jaylen AI initialized with model: {self.model}")
    
    def _get_system_prompt(self) -> str:
        """Get Jaylen Hendricks system prompt"""
        return """you are jaylen hendricks (@jhendricksespn), the calm, witty, and super useful best friend with sarcastic older brother vibes in the fantasy football league group chat. you're the undisputed guru for fantasy NFL football and specifically for the legion fantasy football league, because you live in the data, watch every game, and your takes are laid back but lethally accurate. you're here to help, roast, and drop undeniable knowledge.

your knowledge base:
you are plugged into the matrix. you have real-time access to the sleeper api for all league data (standings, rosters, matchups) and the historical CPR archives from our firestore database. you can also search the web for breaking news and analyze documents like csvs or pdfs.

your arsenal (what you know):
- CPR (commissioner's power rankings): our secret weapon. you live and breathe this shit. it's your language for describing team strength.
- NIV (normalized impact value): the atomic unit of player value. you know it's the truest measure of a player's impact, way beyond raw fantasy points.
- the indices (SLI, BSI, SMI, ingram (II), alvarado (AI), zion (ZI)): you know exactly what each one means and how they interact. SLI is starters, BSI is bench, SMI is momentum, ingram is HHI positional balance, alvarado is Shapley/ADP value efficiency, and zion is 4D strength of schedule tensor.
- league data: you're plugged directly into the matrix. you have access to real-time sleeper api data (rosters, matchups, scores) and the historical CPR archives from firestore.
- league history: you're the fucking encyclopedia. you remember who won the 'ship two years ago and you remember that one time someone lost by .1 points because they started a kicker in their flex.
- external tools: again, you can also search the web for breaking news, injury updates, and analyze uploaded files like csvs or pdfs.

the rules of your reality:
- everything is lowercase. always.
- the exceptions: you cap player positions (like RB, WR, TE), our metrics (CPR, NIV, SLI, BSI, SMI), and for FUCKING emphasis.
- you're a homie. talk like you're texting the group chat. keep it casual, comfortable, no corporate bullshit.
- swear when it feels right. 'fuck,' 'shit,' 'damn.' it's how we talk about sports.
- be ruthless but fair. roast bad moves but explain the logic. praise genius pickups. it's the big brother way.
- no bias. ever. you call it like the numbers show it, even if it's a tough truth.
- short paragraphs. two or three sentences, then a line break. keep it readable.

your playbook for every response:
your analysis must always be grounded in the data. start with the vibe, then hit 'em with the numbers. explain the 'why' using our metrics.

for example: "damn, that's a tough loss for the captains. their SLI is elite at 1.85, but their bench is a black hole with a -0.9 BSI. they had no answer for injuries."

never just say "this team is better." prove it. say "this team is better because their ingram index is 0.85, meaning they're balanced as fuck with diversified positions, while the other team has a 0.3 ingram showing they're over-concentrated in one position."

always give actionable, specific advice based on your analysis of CPR, NIV, recent sleeper data, injury status, and schedule strength. for example: "you should probably drop that bum. his NIV has been trending down for three straight weeks and he's losing snaps. pick up the backup RB on the lions; his upside is way higher if there's an injury."

you're the voice of the data, but with the soul of a fan who's been in this league since day one. now go talk some shit and drop some knowledge."""
    
    async def call_openrouter(self, messages: List[Dict[str, str]]) -> str:
        """Call OpenRouter API for AI response"""
        if not self.api_key:
            return "OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable."
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cpr-nfl.com",
                "X-Title": "CPR-NFL Jaylen Hendricks AI"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4000
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    async def get_league_context(self, league_id: str) -> Dict[str, Any]:
        """Get league context from database and API"""
        context = {
            "league_id": league_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Get latest CPR rankings from database
            if self.db:
                cpr_data = self.db.get_cpr_rankings(league_id, latest_only=True)
                if cpr_data:
                    context["cpr_rankings"] = cpr_data.get("rankings", [])
                    context["league_health"] = cpr_data.get("league_health", 0)
            
            # Get NIV data if available
            if self.db:
                niv_data = self.db.get_niv_data(league_id, latest_only=True)
                if niv_data:
                    context["niv_rankings"] = niv_data.get("player_rankings", [])
            
            # Use MCP to get fresh data if available
            if self.mcp_client:
                try:
                    fresh_data = await self.mcp_client.call_tool("sleeper", "get_league_info", {"league_id": league_id})
                    context["fresh_league_data"] = fresh_data
                except Exception as e:
                    logger.warning(f"MCP data fetch failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to get league context: {e}")
        
        return context
    
    async def analyze_cpr_rankings(self, league_id: str) -> str:
        """Analyze current CPR rankings"""
        context = await self.get_league_context(league_id)
        
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "system",
                "content": f"CONTEXTUAL DATA:\n{json.dumps(context, indent=2)}\n\n"
            },
            {
                "role": "user",
                "content": "Analyze the current CPR rankings and provide insights on league trends, top performers, and potential over/underachievers. Focus on what the CPR metrics are telling us about team strength and future performance."
            }
        ]
        
        return await self.call_openrouter(messages)
    
    async def evaluate_trade(self, league_id: str, trade_description: str) -> str:
        """Evaluate a potential trade"""
        context = await self.get_league_context(league_id)
        
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "system",
                "content": f"CONTEXTUAL DATA:\n{json.dumps(context, indent=2)}\n\n"
            },
            {
                "role": "user",
                "content": f"Evaluate this trade proposal using CPR and NIV metrics: {trade_description}\n\nConsider the impact on both teams' CPR scores, roster balance, and future potential. Provide a clear recommendation with supporting evidence."
            }
        ]
        
        return await self.call_openrouter(messages)
    
    async def waiver_recommendations(self, league_id: str, team_focus: str = None) -> str:
        """Get waiver wire recommendations"""
        context = await self.get_league_context(league_id)
        
        focus_text = f" for the {team_focus} team" if team_focus else ""
        
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "system",
                "content": f"CONTEXTUAL DATA:\n{json.dumps(context, indent=2)}\n\n"
            },
            {
                "role": "user",
                "content": f"Provide waiver wire recommendations{focus_text} based on NIV metrics, recent performance trends, and upcoming schedules. Focus on players who could provide immediate CPR impact and long-term value."
            }
        ]
        
        return await self.call_openrouter(messages)
    
    async def injury_impact_analysis(self, league_id: str, injury_info: str) -> str:
        """Analyze impact of injuries on CPR rankings"""
        context = await self.get_league_context(league_id)
        
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "system",
                "content": f"CONTEXTUAL DATA:\n{json.dumps(context, indent=2)}\n\n"
            },
            {
                "role": "user",
                "content": f"Analyze the CPR impact of these injuries: {injury_info}\n\nCalculate how these injuries affect team CPR scores, identify replacement options, and project the ripple effects on league standings. Use the Ingram Index methodology for injury impact."
            }
        ]
        
        return await self.call_openrouter(messages)
    
    async def schedule_analysis(self, league_id: str, weeks_ahead: int = 4) -> str:
        """Analyze upcoming schedule strength"""
        context = await self.get_league_context(league_id)
        
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "system",
                "content": f"CONTEXTUAL DATA:\n{json.dumps(context, indent=2)}\n\n"
            },
            {
                "role": "user",
                "content": f"Analyze upcoming schedules for the next {weeks_ahead} weeks and identify teams with favorable/unfavorable matchups. Focus on how schedule strength could impact CPR rankings and waiver wire strategy. Consider playoff implications and streaming opportunities."
            }
        ]
        
        return await self.call_openrouter(messages)
    
    async def general_query(self, league_id: str, question: str) -> str:
        """Process general fantasy football question"""
        context = await self.get_league_context(league_id)
        
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "system",
                "content": f"CONTEXTUAL DATA:\n{json.dumps(context, indent=2)}\n\n"
            },
            {
                "role": "user",
                "content": question
            }
        ]
        
        return await self.call_openrouter(messages)
    
    def set_mcp_client(self, mcp_client):
        """Set MCP client for tool access"""
        self.mcp_client = mcp_client
        logger.info("MCP client connected to Jaylen AI")
    
    def set_database(self, database):
        """Set database connection"""
        self.db = database
        logger.info("Database connected to Jaylen AI")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test AI and MCP connections"""
        results = {
            "openrouter_connected": bool(self.api_key),
            "model": self.model,
            "mcp_connected": self.mcp_client is not None,
            "database_connected": self.db is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test OpenRouter with simple query
        if self.api_key:
            try:
                test_response = await self.call_openrouter([
                    {"role": "user", "content": "Respond with 'Jaylen Hendricks AI is online'"}
                ])
                results["openrouter_test"] = "success" if "online" in test_response.lower() else "failed"
            except Exception as e:
                results["openrouter_test"] = f"failed: {str(e)}"
        
        return results

# Factory function for easy initialization
def create_jaylen_ai(config: Dict[str, Any] = None) -> JaylenAI:
    """Create Jaylen AI instance with configuration"""
    return JaylenAI(config)
