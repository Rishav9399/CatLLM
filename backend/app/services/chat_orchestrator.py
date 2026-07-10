import asyncio
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
import uuid
import time  # For latency tracking
import httpx
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

# NOTE: We NO LONGER import EnterpriseMCPManager here!
# The router injects it dynamically to prevent zombie processes.

logger = logging.getLogger(__name__)

class AgenticOrchestrator:
    """
    The Multi-Agent Swarm Cortex (Production Hardened).
    Now features: Traceability, Graceful Fallbacks, Hot-Swapping, and MCP Peripherals.
    """
    # --- ARCHITECTURAL FIX 1: THE SOCKET (THE CATCHER) ---
    # We added `mcp_manager` to the __init__ signature to catch the injected Singleton.
    def __init__(self, db_session: AsyncSession, vector_engine: EnterpriseVectorEngine, mcp_manager):
        self.db = db_session
        self.vector_engine = vector_engine
        self.mcp_manager = mcp_manager # Store the injected nervous system
        
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

        # Renamed to base_tools to distinguish from dynamic MCP tools
        self.base_tools = [
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
        ROLE_MAP = {"ai": "assistant"}
        return [
            {"role": ROLE_MAP.get(msg.role.value, msg.role.value), "content": msg.content}
            for msg in reversed(messages)
        ]

    async def _triage_and_route(self, raw_query: str, history: List[Dict[str, str]], trace_id: str, attachments: Optional[List[str]] = None) -> Dict[str, str]:
        start_time = time.time()
        
        if attachments and len(attachments) > 0:
            logger.info(f"[TRACE: {trace_id}] Image attachment detected. Routing directly to VISIONARY.")
            return {"clean_query": raw_query, "route": "VISIONARY"}
            
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
            
            latency = round((time.time() - start_time) * 1000)
            logger.info(f"[TRACE: {trace_id}] Router Success | Latency: {latency}ms | Route: {decision.get('route')}")
            return decision
            
        except Exception as e:
            logger.error(f"[TRACE: {trace_id}] Router Failed: {e}. Defaulting to RESEARCHER.")
            return {"clean_query": raw_query, "route": "RESEARCHER"}

    async def stream_agentic_response(self, session_id: uuid.UUID, user_query: str, attachments: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        full_ai_response = ""
        cited_chunks = []
        trace_id = str(uuid.uuid4())[:8]
        logger.info(f"[TRACE: {trace_id}] Initiating Swarm for Session {session_id}")
        
        try:
            yield f"data: {json.dumps({'event': 'status', 'content': '🧠 Waking up Swarm...'})}\n\n"
            history = await self._get_chat_history(session_id)
            
            yield f"data: {json.dumps({'event': 'status', 'content': '⚡ Dispatcher analyzing intent...'})}\n\n"
            dispatch_decision = await self._triage_and_route(user_query, history, trace_id, attachments)
            clean_query = dispatch_decision.get("clean_query", user_query)
            route = dispatch_decision.get("route", "RESEARCHER")
            
            active_expert = self.specialists.get(route, self.specialists["RESEARCHER"])
            expert_client = active_expert["client"]
            expert_model = active_expert["model"]
            fallback_route = active_expert.get("fallback")
            
            yield f"data: {json.dumps({'event': 'status', 'content': f'🚀 Routing to {route} Specialist ({expert_model})...'})}\n\n"

            # --- DYNAMIC TOOL INJECTION ---
            # Ask the MCP manager for any external tools and merge them with native tools
            mcp_tools = await self.mcp_manager.get_dynamic_tools()
            active_tools = self.base_tools + mcp_tools

            system_prompt = (
                f"You are the {route} Specialist Architect in an enterprise AI Swarm. "
                "You have access to a suite of tools (Core and Dynamic). Follow these rules:\n"
                "0. CASUAL CHIT-CHAT BYPASS: If the user simply says hello, greets you, or makes casual small talk, DO NOT invoke any tools. Respond directly, conversationally, and warmly in character.\n"
                "1. ALWAYS call search_enterprise_knowledge first for any domain-specific, factual, or company-related question.\n"
                "2. ONLY call search_the_open_web if the enterprise database returns nothing, OR if the user asks about current events.\n"
                "3. When citing enterprise sources, use [Source ID: X]. When citing web sources, use [Web: <URL>]."
            )
            
            user_message_payload: Dict[str, Any] = {"role": "user"}
            if attachments and len(attachments) > 0:
                import base64
                file_path = "." + attachments[0] 
                try:
                    with open(file_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    user_message_payload["content"] = [
                        {"type": "text", "text": clean_query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                except Exception as e:
                    logger.error(f"[TRACE: {trace_id}] Failed to read image for vision cortex: {e}")
                    user_message_payload["content"] = clean_query
            else:
                user_message_payload["content"] = clean_query
                
            messages = [{"role": "system", "content": system_prompt}] + history + [user_message_payload]
            
            # --- ReAct LOOP ---
            for loop_iteration in range(3):
                yield f"data: {json.dumps({'event': 'status', 'content': '🤔 Evaluating tools...'})}\n\n"
                
                try:
                    response = await expert_client.chat.completions.create(
                        model=expert_model,
                        messages=messages,
                        tools=active_tools if len(active_tools) > 0 else None,
                        tool_choice="auto" if len(active_tools) > 0 else None,
                        temperature=0.1
                    )
                except Exception as api_err:
                    logger.error(f"[TRACE: {trace_id}] Expert {expert_model} crashed during tool evaluation: {api_err}")
                    yield f"data: {json.dumps({'event': 'status', 'content': f'⚠️ {route} unavailable. Hot-swapping to {fallback_route}...'})}\n\n"
                    expert_client = self.specialists[fallback_route]["client"]
                    expert_model = self.specialists[fallback_route]["model"]
                    continue 
                
                response_message = response.choices[0].message
                
                if response_message.tool_calls:
                    messages.append(response_message)
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        
                        # --- ARCHITECTURAL FIX 2: DEFENSIVE PARSING ---
                        # Prevent crashes if the LLM sends "null" for a zero-argument tool
                        raw_args = tool_call.function.arguments
                        try:
                            args = json.loads(raw_args) if raw_args and raw_args.strip() else {}
                            if not isinstance(args, dict):
                                args = {}
                        except Exception:
                            args = {}
                            
                        search_query = args.get("query", clean_query)

                        if tool_name == "search_enterprise_knowledge":
                            logger.info(f"[TRACE: {trace_id}] Tool: KB Search for: '{search_query}'")
                            yield f"data: {json.dumps({'event': 'status', 'content': f'🔍 Searching knowledge base: {search_query}'})}\n\n"
                            retrieved_chunks = await self.vector_engine.hybrid_search_funnel(search_query, top_k=4)
                            if retrieved_chunks:
                                tool_result_str = "\n\n---\n\n".join([f"[Source ID: {c['chunk_id']}]\n{c['content']}" for c in retrieved_chunks])
                                cited_chunks.extend([c['chunk_id'] for c in retrieved_chunks])
                            else:
                                tool_result_str = "No relevant documents found in the enterprise knowledge base."

                        elif tool_name == "search_the_open_web":
                            logger.info(f"[TRACE: {trace_id}] Tool: Web Search for: '{search_query}'")
                            yield f"data: {json.dumps({'event': 'status', 'content': f'🌐 Searching the web: {search_query}'})}\n\n"
                            try:
                                if settings.TAVILY_API_KEY:
                                    async with httpx.AsyncClient() as client:
                                        resp = await client.post(
                                            "https://api.tavily.com/search",
                                            json={"api_key": settings.TAVILY_API_KEY, "query": search_query, "max_results": 3},
                                            timeout=10.0
                                        )
                                        resp.raise_for_status()
                                        results = resp.json().get("results", [])
                                        tool_result_str = "\n\n---\n\n".join([f"[Web: {r.get('url', '')}]\n**{r.get('title', '')}**\n{r.get('content', '')[:400]}…" for r in results]) if results else "No web results found."
                                else:
                                    def fetch_ddg(q):
                                        with DDGS() as ddgs:
                                            return list(ddgs.text(q, max_results=3))
                                    results = await asyncio.to_thread(fetch_ddg, search_query)
                                    tool_result_str = "\n\n---\n\n".join([f"[Web: {r.get('href', 'unknown')}]\n{r.get('title', '')}\n{r.get('body', '')}" for r in results]) if results else "No web results found."
                            except Exception as web_err:
                                logger.error(f"[TRACE: {trace_id}] Web Search Failed: {web_err}")
                                tool_result_str = "Web search encountered a network error or block. Proceed with existing knowledge."
                        
                        else:
                            # --- PERIPHERAL EXECUTION ---
                            # Hand it off to the external Python script
                            logger.info(f"[TRACE: {trace_id}] Accessing Peripheral: {tool_name}")
                            yield f"data: {json.dumps({'event': 'status', 'content': f'🔌 Accessing Peripheral: {tool_name}...'})}\n\n"
                            tool_result_str = await self.mcp_manager.execute_dynamic_tool(tool_name, args)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result_str
                        })

                    continue
                else:
                    break 
            
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
