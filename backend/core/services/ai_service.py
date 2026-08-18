"""
AI Service — Intent routing between Live WMS Tools and RAG Handbook.
Uses Gemini with function calling. Backend authorization is authoritative;
the LLM layer never decides permissions.
"""
import json
from typing import Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

from commons.logger import get_logger
from core.models.user_model import UserModel
from core.services.ai_tools import AIToolsService

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = """You are the Whitfield Fulfillment WMS Operational Assistant.
You help warehouse operators by answering questions about live inventory levels, orders, 
and receiving activity, as well as standard operating procedures (SOPs) from the warehouse handbook.

RULES:
1. For live operational data (inventory counts, order statuses, receiving records), 
   ALWAYS call the appropriate tool to fetch live data. Never guess stock levels or order states.
2. For procedural questions (SOPs, safety procedures, receiving guidelines), 
   search the knowledge base using the `search_knowledge_base` tool.
3. Always be concise and precise. Present numbers clearly.
4. If you don't know something and no tool can help, say so honestly.
5. Format responses clearly: use the warehouse code (RENO/COLUMBUS) when presenting location-specific data.
"""


class AIRequest(BaseModel):
    query: str
    warehouse_code: Optional[str] = None


class SourceType:
    LIVE_DATA = "LIVE_DATA"
    HANDBOOK = "HANDBOOK"
    COMBINED = "COMBINED"
    ERROR = "ERROR"


class AIResponse(BaseModel):
    response: str
    source: str
    sources: list[dict] = []
    warehouse_context: Optional[str] = None


class AIService:
    """Routes queries between Live WMS Tools and RAG Handbook using Gemini function calling."""

    def __init__(self):
        self.tools_service = AIToolsService()
        self.model = "gemini-2.5-flash"
        self._client = None

    def _get_client(self):
        """Lazily initialize Google GenAI Client if API key is provided."""
        if self._client is not None:
            return self._client
        try:
            self._client = genai.Client()
            return self._client
        except Exception as e:
            logger.warning(f"Google GenAI Client could not be initialized (likely missing API key): {e}")
            return None

    def _build_tools_for_user(self, current_user: UserModel) -> list:
        """Build the Gemini tool declarations. The user context is captured in the closure."""
        wh_desc = (
            "Optional warehouse code filter. Valid values: 'RENO', 'COLUMBUS'. "
            "If not provided, returns data for all accessible warehouses."
        )
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_inventory",
                        description="Fetch live inventory levels from the WMS. Use for questions about stock, available units, reserved quantities.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "warehouse_code": types.Schema(type=types.Type.STRING, description=wh_desc),
                                "sku": types.Schema(type=types.Type.STRING, description="Optional product SKU to filter by."),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_inventory_summary",
                        description="Get a high-level inventory summary: total SKU count and total available units. Use for broad questions like 'how much stock do we have?'",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "warehouse_code": types.Schema(type=types.Type.STRING, description=wh_desc),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="list_orders",
                        description="Fetch live orders from the WMS. Use for questions about order counts, statuses, pending/shipped orders.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "warehouse_code": types.Schema(type=types.Type.STRING, description=wh_desc),
                                "status": types.Schema(
                                    type=types.Type.STRING,
                                    description="Optional order status filter: PENDING, CONFIRMED, RESERVED, PICKING, PACKED, SHIPPED, CANCELLED.",
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_order_summary",
                        description="Get a high-level order summary grouped by status. Use for broad questions like 'how many orders are pending?'",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "warehouse_code": types.Schema(type=types.Type.STRING, description=wh_desc),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="search_knowledge_base",
                        description="Search the warehouse operations handbook (SOPs, receiving procedures, safety guidelines). Use for procedural or policy questions.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "query": types.Schema(type=types.Type.STRING, description="The question or topic to search for."),
                            },
                            required=["query"],
                        ),
                    ),
                ]
            )
        ]

    async def _execute_tool_call(
        self, name: str, args: dict, current_user: UserModel
    ) -> tuple[dict, str]:
        """Execute a tool call and return (result_dict, source_type)."""
        wh = args.get("warehouse_code") or None

        if name == "get_inventory":
            result = await self.tools_service.get_inventory(
                current_user=current_user,
                warehouse_code=wh,
                sku=args.get("sku"),
            )
            return {"inventory": result[:20]}, SourceType.LIVE_DATA  # cap for context

        elif name == "get_inventory_summary":
            result = await self.tools_service.get_inventory_summary(
                current_user=current_user, warehouse_code=wh
            )
            return result, SourceType.LIVE_DATA

        elif name == "list_orders":
            result = await self.tools_service.list_orders(
                current_user=current_user,
                warehouse_code=wh,
                status=args.get("status"),
            )
            return {"orders": result[:20]}, SourceType.LIVE_DATA

        elif name == "get_order_summary":
            result = await self.tools_service.get_order_summary(
                current_user=current_user, warehouse_code=wh
            )
            return result, SourceType.LIVE_DATA

        elif name == "search_knowledge_base":
            # Import lazily to avoid startup cost if RAG not initialized
            from core.rag.retriever import RAGRetriever
            retriever = RAGRetriever()
            result = await retriever.search(args.get("query", ""))
            return result, SourceType.HANDBOOK

        return {"error": f"Unknown tool: {name}"}, SourceType.ERROR

    async def ask(self, request: AIRequest, current_user: UserModel) -> AIResponse:
        """Process an AI query with function calling, then return a grounded response."""
        logger.info(f"AI ask: '{request.query}' by {current_user.email} (wh={request.warehouse_code})")

        client = self._get_client()
        if not client:
            # Fallback when no Gemini API key is configured
            q_lower = request.query.lower()
            if any(k in q_lower for k in ["sop", "handbook", "policy", "procedure", "how to", "guideline", "rule", "safety"]):
                from core.rag.retriever import RAGRetriever
                retriever = RAGRetriever()
                rag_res = await retriever.search(request.query)
                return AIResponse(
                    response=rag_res.get("answer") or "Here is the relevant SOP handbook information.",
                    source=SourceType.HANDBOOK,
                    sources=rag_res.get("sources", []),
                    warehouse_context=request.warehouse_code,
                )
            elif "order" in q_lower:
                summary = await self.tools_service.get_order_summary(current_user, request.warehouse_code)
                return AIResponse(
                    response=f"Live order summary for {summary.get('warehouse_code')}: {summary.get('total_orders')} total orders. Breakdown: {summary.get('by_status')}.",
                    source=SourceType.LIVE_DATA,
                    warehouse_context=request.warehouse_code,
                )
            else:
                summary = await self.tools_service.get_inventory_summary(current_user, request.warehouse_code)
                return AIResponse(
                    response=f"Live inventory summary for {summary.get('warehouse_code')}: {summary.get('total_available_units')} units available across {summary.get('total_sku_count')} SKUs.",
                    source=SourceType.LIVE_DATA,
                    warehouse_context=request.warehouse_code,
                )

        # Inject warehouse context into query if provided
        user_query = request.query
        if request.warehouse_code:
            user_query = f"[Active warehouse: {request.warehouse_code}] {request.query}"

        tools = self._build_tools_for_user(current_user)
        messages = [types.Content(role="user", parts=[types.Part(text=user_query)])]

        source_types_used = set()
        rag_sources = []

        # Agentic loop — allow up to 3 tool rounds
        for _ in range(3):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=tools,
                        temperature=0.1,
                    ),
                )
            except Exception as e:
                logger.error(f"Gemini API error during generation: {e}")
                break

            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                break

            # Check for function calls
            has_tool_calls = any(
                part.function_call for part in candidate.content.parts if hasattr(part, "function_call") and part.function_call
            )

            if not has_tool_calls:
                # Final text response
                final_text = "".join(
                    part.text for part in candidate.content.parts if hasattr(part, "text") and part.text
                )
                source = (
                    SourceType.COMBINED if len(source_types_used) > 1
                    else (next(iter(source_types_used)) if source_types_used else SourceType.LIVE_DATA)
                )
                return AIResponse(
                    response=final_text,
                    source=source,
                    sources=rag_sources,
                    warehouse_context=request.warehouse_code,
                )

            # Execute all tool calls in this round
            tool_results = []
            messages.append(candidate.content)

            for part in candidate.content.parts:
                if not hasattr(part, "function_call") or not part.function_call:
                    continue
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args) if part.function_call.args else {}

                try:
                    tool_result, source_type = await self._execute_tool_call(fn_name, fn_args, current_user)
                    source_types_used.add(source_type)
                    if source_type == SourceType.HANDBOOK and "sources" in tool_result:
                        rag_sources.extend(tool_result.get("sources", []))
                    tool_results.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"result": json.dumps(tool_result, default=str)},
                            )
                        )
                    )
                except Exception as e:
                    logger.error(f"Tool call error {fn_name}: {e}")
                    tool_results.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_name,
                                response={"error": str(e)},
                            )
                        )
                    )

            messages.append(types.Content(role="tool", parts=tool_results))

        return AIResponse(
            response="I was unable to complete this query. Please try rephrasing.",
            source=SourceType.ERROR,
            warehouse_context=request.warehouse_code,
        )
