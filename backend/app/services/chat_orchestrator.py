import asyncio
import json
import logging
from typing import AsyncGenerator, List, Dict, Any
import uuid
import time  # For latency tracking
import httpx
# Revert to the stable synchronous import
# pyrefly: ignore [missing-import]
from duckduckgo_search import DDGS

from app.core.config import settings

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
# pyrefly: ignore [missing-import]
from openai import AsyncOpenAI

from app.database.models import ChatSession, Message
from app.schemas.chat import MessageRole
from app.services.vector_engine import EnterpriseVectorEngine
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgenticOrchestrator:
    """
    The Multi-Agent Swarm Cortex (Production Hardened).
    Now features: Traceability, Graceful Fallbacks, and Hot-Swapping.
    """
    def __init__(self, db_session: AsyncSession, vector_engine: EnterpriseVectorEngine):
        self.db = db_session
        self.vector_engine = vector_engine
        
        # 1. The Gatekeeper
        self.gatekeeper_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
            max_retries=1 # Fail fast on the router
        )
        self.gatekeeper_model = "llama-3.1-8b-instant"

        # 2. The Specialist Fleet
        self.specialists = {
            "RESEARCHER": {
                "client": AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.GROQ_API_KEY),
                "model": "llama-3.3-70b-versatile",
                "fallback": "VISIONARY" # If Groq fails, fallback to Google
            },
            "VISIONARY": {
                "client": AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=settings.GEMINI_API_KEY or ""),
                "model": "gemini-2.5-flash",
                "fallback": "RESEARCHER" # If Google fails, fallback to Groq
            },
            "CODER": {
                "client": AsyncOpenAI(base_url="https://open.bigmodel.cn/api/paas/v4/", api_key=settings.GLM_API_KEY or ""),
                "model": "glm-4-plus",
                "fallback": "RESEARCHER"
            }
        }

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_enterprise_knowledge",
                    "description": (
                        "Searches the company's private hybrid vector/sparse knowledge base. "
                        "ALWAYS call this tool first for any question about company data, "
                        "internal policies, documents, or domain-specific knowledge."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Specific search query."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_the_open_web",
                    "description": (
                        "Searches the public internet via DuckDuckGo. "
                        "ONLY use this tool if: (1) the enterprise knowledge base returned no results, "
                        "OR (2) the user explicitly asks about recent news, current events, "
                        "or real-time information that cannot be in a private database. "
                        "Do NOT use this as a first resort."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Web search query."}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    async def _get_chat_history(self, session_id: uuid.UUID, limit: int = 5) -> List[Dict[str, str]]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        # CRITICAL: Map internal "ai" role → OpenAI-standard "assistant".
        # Groq/Gemini reject any role that is not "user", "assistant", or "system".
        ROLE_MAP = {"ai": "assistant"}
        return [
            {"role": ROLE_MAP.get(msg.role.value, msg.role.value), "content": msg.content}
            for msg in reversed(messages)
        ]

    async def _triage_and_route(self, raw_query: str, history: List[Dict[str, str]], trace_id: str) -> Dict[str, str]:
        """
        AGENT 1: The Dispatcher (Now with Confidence & Fallback)
        """
        start_time = time.time()
        history_context = str(history[-2:]) if history else "No history."
            
        system_prompt = (
            "You are the Swarm Dispatcher. Analyze the user query. "
            "1. Rewrite the query resolving pronouns. "
            "2. Decide the ROUTE: 'RESEARCHER', 'VISIONARY', or 'CODER'. "
            "Respond ONLY in valid JSON format: {\"clean_query\": \"...\", \"route\": \"RESEARCHER\"}"
        )
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"History: {history_context}\nQuery: {raw_query}"}]
        
        try:
            response = await self.gatekeeper_client.chat.completions.create(
                model=self.gatekeeper_model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},
                max_tokens=100
            )
            decision = json.loads(response.choices[0].message.content)
            
            # Observability Log
            latency = round((time.time() - start_time) * 1000)
            logger.info(f"[TRACE: {trace_id}] Router Success | Latency: {latency}ms | Route: {decision.get('route')}")
            return decision
            
        except Exception as e:
            # Flaw 1 Fix: Never let the router crash the system. Fail gracefully.
            logger.error(f"[TRACE: {trace_id}] Router Failed: {e}. Defaulting to RESEARCHER.")
            return {"clean_query": raw_query, "route": "RESEARCHER"}

    async def stream_agentic_response(self, session_id: uuid.UUID, user_query: str) -> AsyncGenerator[str, None]:
        """The Autonomous Swarm Pipeline (Production Hardened)."""
        full_ai_response = ""
        cited_chunks = []
        
        # --- ARCHITECTURAL FIX: OBSERVABILITY ---
        trace_id = str(uuid.uuid4())[:8] # Unique ID for this specific network request
        logger.info(f"[TRACE: {trace_id}] Initiating Swarm for Session {session_id}")
        
        try:
            yield f"data: {json.dumps({'event': 'status', 'content': '🧠 Waking up Swarm...'})}\n\n"
            history = await self._get_chat_history(session_id)
            
            yield f"data: {json.dumps({'event': 'status', 'content': '⚡ Dispatcher analyzing intent...'})}\n\n"
            dispatch_decision = await self._triage_and_route(user_query, history, trace_id)
            clean_query = dispatch_decision.get("clean_query", user_query)
            route = dispatch_decision.get("route", "RESEARCHER")
            
            # Get active specialist
            active_expert = self.specialists.get(route, self.specialists["RESEARCHER"])
            expert_client = active_expert["client"]
            expert_model = active_expert["model"]
            fallback_route = active_expert.get("fallback")
            
            yield f"data: {json.dumps({'event': 'status', 'content': f'🚀 Routing to {route} Specialist ({expert_model})...'})}\n\n"

            system_prompt = (
                f"You are the {route} Specialist Architect in an enterprise AI Swarm. "
                "You have access to two tools. Follow this strict routing hierarchy:\n"
                "1. ALWAYS call search_enterprise_knowledge first for any domain-specific or company-related question.\n"
                "2. ONLY call search_the_open_web if the enterprise database returns nothing, "
                "OR if the user explicitly asks about current events, real-time data, or public news.\n"
                "3. Never call search_the_open_web as a first resort — the private knowledge base takes priority.\n"
                "When citing enterprise sources, use [Source ID: X]. "
                "When citing web sources, use [Web: <URL>]."
            )
            messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": clean_query}]
            
            # --- ReAct LOOP ---
            for loop_iteration in range(3):
                yield f"data: {json.dumps({'event': 'status', 'content': '🤔 Evaluating tools...'})}\n\n"
                
                try:
                    response = await expert_client.chat.completions.create(
                        model=expert_model,
                        messages=messages,
                        tools=self.tools,
                        tool_choice="auto",
                        temperature=0.1
                    )
                except Exception as api_err:
                    # --- ARCHITECTURAL FIX: GRACEFUL DEGRADATION ---
                    logger.error(f"[TRACE: {trace_id}] Expert {expert_model} crashed during tool evaluation: {api_err}")
                    yield f"data: {json.dumps({'event': 'status', 'content': f'⚠️ {route} unavailable. Hot-swapping to {fallback_route}...'})}\n\n"
                    # Hot swap logic!
                    expert_client = self.specialists[fallback_route]["client"]
                    expert_model = self.specialists[fallback_route]["model"]
                    continue # Try the loop again with the new brain
                
                response_message = response.choices[0].message
                
                if response_message.tool_calls:
                    messages.append(response_message)
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        search_query = args.get("query", clean_query)

                        # -------------------------------------------------------
                        # TOOL: Enterprise Knowledge Base (private RAG)
                        # -------------------------------------------------------
                        if tool_name == "search_enterprise_knowledge":
                            logger.info(f"[TRACE: {trace_id}] Tool: KB Search for: '{search_query}'")
                            yield f"data: {json.dumps({'event': 'status', 'content': f'🔍 Searching knowledge base: {search_query}'})}\n\n"

                            retrieved_chunks = await self.vector_engine.hybrid_search_funnel(search_query, top_k=4)

                            if retrieved_chunks:
                                tool_result_str = "\n\n---\n\n".join(
                                    [f"[Source ID: {c['chunk_id']}]\n{c['content']}" for c in retrieved_chunks]
                                )
                                cited_chunks.extend([c['chunk_id'] for c in retrieved_chunks])
                            else:
                                tool_result_str = "No relevant documents found in the enterprise knowledge base."

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": tool_result_str
                            })

                        # -------------------------------------------------------
                        # TOOL: Open Web Search (DuckDuckGo fallback)
                        # Safety rules:
                        #   - Top 3 results only (prevent context flood)
                        #   - 400 chars per result (prevent context window degradation)
                        #   - Runs in a thread (DDGS is synchronous/blocking)
                        # -------------------------------------------------------
                        elif tool_name == "search_the_open_web":
                            logger.info(f"[TRACE: {trace_id}] Tool: Web Search for: '{search_query}'")
                            yield f"data: {json.dumps({'event': 'status', 'content': f'🌐 Searching the web: {search_query}'})}\n\n"

                            try:
                                # The Architect's Switch: Brave API vs Tavily vs Scraper
                                if settings.BRAVE_API_KEY:
                                    logger.info(f"[TRACE: {trace_id}] Using Enterprise Route: Brave Search API")
                                    # Enterprise Free-Tier Standard: Brave Search API
                                    async with httpx.AsyncClient() as client:
                                        resp = await client.get(
                                            "https://api.search.brave.com/res/v1/web/search",
                                            params={"q": search_query, "count": 3},
                                            headers={
                                                "Accept": "application/json",
                                                "X-Subscription-Token": settings.BRAVE_API_KEY
                                            },
                                            timeout=10.0
                                        )
                                        resp.raise_for_status()
                                        
                                        # Brave nests its results inside a 'web' -> 'results' object
                                        results = resp.json().get("web", {}).get("results", [])
                                        
                                        if results:
                                            # Brave uses 'description' instead of 'content' or 'body'
                                            tool_result_str = "\n\n---\n\n".join([f"[Web: {r.get('url', 'unknown')}]\n**{r.get('title', '')}**\n{r.get('description', '')}" for r in results])
                                        else:
                                            tool_result_str = "No web results found via Brave Search."

                                elif settings.TAVILY_API_KEY:
                                    logger.info(f"[TRACE: {trace_id}] Using Enterprise Route: Tavily Search API")
                                    async with httpx.AsyncClient() as client:
                                        resp = await client.post(
                                            "https://api.tavily.com/search",
                                            json={"api_key": settings.TAVILY_API_KEY, "query": search_query, "max_results": 3},
                                            timeout=10.0
                                        )
                                        resp.raise_for_status()
                                        results = resp.json().get("results", [])
                                        if results:
                                            formatted = []
                                            for r in results:
                                                title = r.get('title', 'No title')
                                                url = r.get('url', '')
                                                body = r.get('content', '')[:400]
                                                formatted.append(f"[Web: {url}]\n**{title}**\n{body}…")
                                            tool_result_str = "\n\n---\n\n".join(formatted)
                                        else:
                                            tool_result_str = "No web results found via Tavily API."
                                            
                                else:
                                    logger.info(f"[TRACE: {trace_id}] Using Fallback Route: DuckDuckGo Scraper")
                                    # Fallback: Synchronous DDGS wrapped in a thread to prevent blocking
                                    def fetch_ddg(q):
                                        with DDGS() as ddgs:
                                            return list(ddgs.text(q, max_results=3))
                                            
                                    results = await asyncio.to_thread(fetch_ddg, search_query)
                                    
                                    if results:
                                        tool_result_str = "\n\n---\n\n".join([f"[Web: {r.get('href', 'unknown')}]\n{r.get('title', '')}\n{r.get('body', '')}" for r in results])
                                    else:
                                        tool_result_str = "No web results found via Scraper."

                            except Exception as web_err:
                                logger.error(f"[TRACE: {trace_id}] Web Search Failed: {web_err}")
                                tool_result_str = "Web search encountered a network error or block. Proceed with existing knowledge."

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": tool_result_str
                            })

                    continue
                else:
                    break # ReAct finished. Proceed to generation.
            
            # --- FINAL SYNTHESIS STREAM ---
            yield f"data: {json.dumps({'event': 'status', 'content': f'💡 Synthesizing ({route})...'})}\n\n"
            
            try:
                stream = await expert_client.chat.completions.create(
                    model=expert_model,
                    messages=messages,
                    stream=True,
                    temperature=0.3
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_ai_response += token
                        yield f"data: {json.dumps({'event': 'token', 'content': token})}\n\n"
                        
            except Exception as stream_err:
                logger.error(f"[TRACE: {trace_id}] Stream failed on {expert_model}: {stream_err}")
                error_msg = f"\n\n[System Alert]: Connection to {expert_model} was interrupted."
                full_ai_response += error_msg
                yield f"data: {json.dumps({'event': 'token', 'content': error_msg})}\n\n"
                    
        except Exception as e:
            logger.error(f"[TRACE: {trace_id}] Fatal Orchestration Error: {e}")
            error_msg = "Critical system failure during Swarm reasoning."
            full_ai_response = error_msg
            yield f"data: {json.dumps({'event': 'error', 'content': error_msg})}\n\n"
            
        finally:
            if full_ai_response:
                try:
                    ai_msg = Message(
                        session_id=session_id,
                        role=MessageRole.AI,
                        content=full_ai_response,
                        citations_snapshot={"cited_chunk_ids": list(set(cited_chunks))} 
                    )
                    self.db.add(ai_msg)
                    await self.db.commit()
                    logger.info(f"[TRACE: {trace_id}] Response saved. Transaction complete.")
                except Exception as db_e:
                    logger.error(f"[TRACE: {trace_id}] Failed to save AI message: {db_e}")
            
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            