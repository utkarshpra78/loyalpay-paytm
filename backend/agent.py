"""
LoyalPay Conversational AI Agent

Provides a Hindi/Hinglish conversational interface with tool calling.
Uses Gemini API for natural language understanding and grounded responses.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


@dataclass
class ToolResult:
    """Result from a tool call."""
    tool_name: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class AgentResponse:
    """Response from the AI agent."""
    response: str
    tools_used: List[str]
    data: Optional[Dict[str, Any]] = None
    language: str = "hinglish"


class LoyalPayAgent:
    """
    AI-powered conversational agent for LoyalPay.
    
    Uses Gemini for natural language understanding and response generation,
    with fallback to rule-based responses when API is unavailable.
    """
    
    def __init__(
        self,
        api_key: str = None,
        tool_handlers: Dict[str, Callable] = None
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.tool_handlers = tool_handlers or {}
        self.model = None
        
        # Initialize Gemini if available
        if GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"Warning: Could not initialize Gemini: {e}")
                self.model = None
    
    def register_tool(self, name: str, handler: Callable):
        """Register a tool handler."""
        self.tool_handlers[name] = handler
    
    def _detect_language(self, text: str) -> str:
        """Detect if text is Hindi, Hinglish, or English."""
        if re.search(r'[\u0900-\u097F]', text):
            return "hindi"
        
        hinglish_words = [
            "kya", "hai", "hain", "nahi", "kaise", "kitne", "kaun", "wapas",
            "bhejo", "batao", "dekho", "aaye", "gaye", "achha", "theek",
            "aur", "mein", "se", "ko", "ka", "ki", "ke", "ji", "karo",
            "bata", "dikhao", "sabse"
        ]
        
        text_lower = text.lower()
        hinglish_count = sum(1 for word in hinglish_words if word in text_lower)
        
        if hinglish_count >= 1:
            return "hinglish"
        
        return "english"
    
    def _execute_tool(self, tool_name: str, params: Dict[str, Any] = None) -> ToolResult:
        """Execute a registered tool."""
        if tool_name not in self.tool_handlers:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error=f"Tool '{tool_name}' not registered"
            )
        
        try:
            handler = self.tool_handlers[tool_name]
            result = handler(**(params or {}))
            return ToolResult(
                tool_name=tool_name,
                success=True,
                data=result if isinstance(result, dict) else {"result": result}
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error=str(e)
            )
    
    def _determine_tools_needed(self, message: str) -> List[str]:
        """Determine which tools to call based on the message."""
        msg_lower = message.lower()
        tools = []
        
        # At-risk / churn related
        if any(word in msg_lower for word in ["at-risk", "risk", "wapas", "nahi aaye", "churn", "lost", "missing", "gaye", "churning"]):
            tools.append("get_at_risk_customers")
        
        # Campaign / offer / notification related
        if any(word in msg_lower for word in ["suggest", "offer", "campaign", "cashback", "bhejo", "send", "recommendation", "notification", "notify", "all of them", "sabko", "sab ko"]):
            tools.append("suggest_offer")
            tools.append("get_at_risk_customers")
        
        # Decision questions - need full context
        if any(word in msg_lower for word in ["should i", "kya", "karu", "karein", "best", "recommend", "advice"]):
            tools.append("get_store_summary")
            tools.append("get_at_risk_customers")
            tools.append("suggest_offer")
        
        # ROI / results related
        if any(word in msg_lower for word in ["roi", "return", "result", "kitna mila", "kamaya", "recovered"]):
            tools.append("get_campaign_roi")
        
        # Insights / trends
        if any(word in msg_lower for word in ["insight", "trend", "pattern", "habit", "analysis", "analyze"]):
            tools.append("get_insights")
        
        # Segments
        if any(word in msg_lower for word in ["segment", "champion", "loyal", "new customer"]):
            tools.append("get_segments")
        
        # ANY question about customers or payments needs customer data
        if any(word in msg_lower for word in ["customer", "customers", "coustomer", "coustemer", "payment", "spend", "average", "above", "more than", "greater", "zyada", "upar", "₹", "rupee", "rs", "inr"]):
            tools.append("get_all_customers")
        
        # Check for numbers - likely asking about thresholds
        if re.search(r'\d+', msg_lower):
            tools.append("get_all_customers")
        
        # Summary / general stats
        if any(word in msg_lower for word in ["kitne", "total", "summary", "how many", "store", "kamai"]):
            tools.append("get_store_summary")
        
        # If message contains "how many" or "kitne" with any context, need customer data
        if "how many" in msg_lower or "kitne" in msg_lower:
            tools.append("get_all_customers")
        
        # If no specific tools matched, get all data for context
        if not tools:
            tools = ["get_store_summary", "get_all_customers"]
        
        # Always include summary for context if not already there
        if "get_store_summary" not in tools:
            tools.insert(0, "get_store_summary")
        
        return list(set(tools))  # Remove duplicates
    
    def _generate_with_gemini(self, message: str, tool_results: Dict[str, ToolResult], language: str) -> str:
        """Generate response using Gemini with real data context."""
        if not self.model:
            return None
        
        # Build rich context from tool results
        context_parts = []
        for tool_name, result in tool_results.items():
            if result.success and result.data:
                # Format data nicely
                data_str = json.dumps(result.data, ensure_ascii=False, indent=2)
                context_parts.append(f"=== {tool_name} ===\n{data_str}")
        
        context = "\n\n".join(context_parts)
        
        lang_instruction = {
            "hindi": "Respond in Hindi (Devanagari script).",
            "hinglish": "Respond in Hinglish (Hindi words in Roman script mixed with English). Example: 'Aapke 307 regular customers hain.'",
            "english": "Respond in English."
        }.get(language, "Respond in Hinglish.")
        
        prompt = f"""You are a helpful AI assistant for LoyalPay, a customer retention app for small Indian merchants like kirana stores.

YOUR TASK: Answer the merchant's SPECIFIC question using the data provided. 

CRITICAL RULES:
1. {lang_instruction}
2. DIRECTLY answer what was asked - if they ask about ₹500+ spenders, count and list those specific customers
3. Use ACTUAL numbers from the data - count them yourself if needed
4. Keep response concise (2-3 sentences)
5. Use ₹ symbol for money
6. Mention specific customer labels like #B60, #A14 when relevant
7. If the data doesn't have what's needed, say so clearly

EXAMPLES:
- Q: "How many customers spend more than ₹100 average?" → Look at monetary_avg field, count customers where monetary_avg > 100
- Q: "Who are my top spenders?" → List top customers by monetary_avg
- Q: "Kitne at-risk customers hain?" → Count from at-risk data

MERCHANT'S QUESTION: {message}

STORE DATA:
{context}

Answer the specific question asked (use the data to compute/filter if needed):"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini error: {e}")
            return None
    
    def _generate_fallback_response(self, message: str, tool_results: Dict[str, ToolResult], language: str) -> str:
        """Generate a fallback response without Gemini."""
        msg_lower = message.lower()
        
        # Get data from tools
        summary = tool_results.get("get_store_summary", ToolResult("", False, {})).data or {}
        at_risk = tool_results.get("get_at_risk_customers", ToolResult("", False, {})).data or {}
        suggestion = tool_results.get("suggest_offer", ToolResult("", False, {})).data or {}
        insights = tool_results.get("get_insights", ToolResult("", False, {})).data or {}
        roi = tool_results.get("get_campaign_roi", ToolResult("", False, {})).data or {}
        segments = tool_results.get("get_segments", ToolResult("", False, {})).data or {}
        all_customers = tool_results.get("get_all_customers", ToolResult("", False, {})).data or {}
        
        # Check if we have data
        total_customers = summary.get("total_customers", 0)
        if total_customers == 0:
            if language == "hinglish":
                return "Abhi koi data nahi hai. Pehle 'Simulate 60 Days' button click karein demo data load karne ke liye."
            return "No data available yet. Click 'Simulate 60 Days' to load demo data first."
        
        # Campaign/notification decision questions
        if any(word in msg_lower for word in ["should i", "send", "notification", "notify", "bhejo", "all of them", "sabko", "campaign"]):
            at_risk_customers = at_risk.get("customers", [])
            at_risk_count = at_risk.get("total", len(at_risk_customers))
            sugg = suggestion.get("suggestion", {})
            
            if at_risk_count > 0:
                # Calculate recommendation
                high_risk = [c for c in at_risk_customers if c.get('churn_probability', 0.5) > 0.6]
                expected_roi = sugg.get("expected_roi", 8)
                
                if language == "hinglish":
                    return f"Haan, {at_risk_count} at-risk customers ko notification bhejein! {len(high_risk)} customers high risk mein hain. 10-15% cashback offer se ~{expected_roi}x ROI expect kar sakte hain. Offers tab mein jaake customers select karein aur send karein."
                return f"Yes, send notifications to {at_risk_count} at-risk customers! {len(high_risk)} are high risk. With 10-15% cashback, expect ~{expected_roi}x ROI. Go to Offers tab, select customers, and send."
            else:
                if language == "hinglish":
                    return "Abhi koi at-risk customer nahi hai. Sab customers active hain!"
                return "No at-risk customers right now. All customers are active!"
        
        # Spending/payment queries - extract number from message
        if any(word in msg_lower for word in ["spend", "average", "avg", "payment", "above", "more than", "greater", "zyada", "upar", "top"]) or re.search(r'\d+', msg_lower):
            customers = all_customers.get("customers", [])
            if customers:
                # Extract threshold from message - find any number
                numbers = re.findall(r'\d+', msg_lower)
                threshold = int(numbers[0]) if numbers else 100
                
                high_spenders = [c for c in customers if c.get('monetary_avg', 0) >= threshold]
                count = len(high_spenders)
                
                if count > 0:
                    top_3 = ", ".join([f"{c['label']} (₹{c['monetary_avg']:.0f})" for c in high_spenders[:3]])
                    if language == "hinglish":
                        return f"{count} customers hain jo ₹{threshold}+ average spend karte hain. Top 3: {top_3}"
                    return f"{count} customers have ₹{threshold}+ average spend. Top 3: {top_3}"
                else:
                    max_spender = customers[0] if customers else None
                    if max_spender:
                        if language == "hinglish":
                            return f"Koi customer ₹{threshold}+ average spend nahi karta. Sabse zyada spend: {max_spender['label']} (₹{max_spender['monetary_avg']:.0f})"
                        return f"No customers with ₹{threshold}+ average spend. Highest spender: {max_spender['label']} (₹{max_spender['monetary_avg']:.0f})"
        
        # At-risk query
        if any(word in msg_lower for word in ["at-risk", "risk", "wapas", "nahi aaye", "churn"]):
            customers = at_risk.get("customers", [])
            count = at_risk.get("total", len(customers))
            if customers:
                top_3 = ", ".join([f"{c['label']} ({c['recency_days']} din)" for c in customers[:3]])
                if language == "hinglish":
                    return f"{count} customers at-risk hain jo 2 hafte se nahi aaye. Top 3: {top_3}. Inhe cashback offer bhejein?"
                return f"{count} at-risk customers haven't visited in 2+ weeks. Top 3: {top_3}. Want to send them a cashback offer?"
            return f"{count} at-risk customers found." if language == "english" else f"{count} at-risk customers hain."
        
        # Summary query
        if any(word in msg_lower for word in ["kitne", "total", "summary", "customer", "how many"]):
            regular = summary.get("regular_customers", 0)
            revenue = summary.get("total_revenue", 0)
            seg = summary.get("segments", segments) or segments
            at_risk_count = seg.get("At-Risk", 0) + seg.get("Lost", 0)
            
            if language == "hinglish":
                return f"Aapke store mein {regular} regular customers hain. Total revenue: ₹{revenue:,.0f}. {at_risk_count} customers at-risk hain jinhe attention chahiye."
            return f"Your store has {regular} regular customers. Total revenue: ₹{revenue:,.0f}. {at_risk_count} customers need attention."
        
        # Campaign suggestion
        if any(word in msg_lower for word in ["suggest", "campaign", "offer", "recommend"]):
            sugg = suggestion.get("suggestion", {})
            if sugg:
                targets = sugg.get("target_count", 0)
                cashback = sugg.get("cashback_per_customer", 20)
                expected = sugg.get("expected_revenue", 0)
                if language == "hinglish":
                    return f"Suggestion: {targets} at-risk customers ko ₹{cashback} cashback offer bhejein. Expected return: ₹{expected:,.0f}."
                return f"Suggestion: Send ₹{cashback} cashback to {targets} at-risk customers. Expected return: ₹{expected:,.0f}."
            return "Campaign suggestion available in Offers tab." if language == "english" else "Campaign suggestion Offers tab mein dekhein."
        
        # ROI query
        if any(word in msg_lower for word in ["roi", "result", "return"]):
            if roi and roi.get("redemptions_count", 0) > 0:
                recovered = roi.get("revenue_recovered", 0)
                redemptions = roi.get("redemptions_count", 0)
                multiple = roi.get("roi_multiple", 0)
                if language == "hinglish":
                    return f"Campaign results: {redemptions} customers wapas aaye! Revenue: ₹{recovered:,.0f}. ROI: {multiple}x"
                return f"Campaign results: {redemptions} customers returned! Revenue: ₹{recovered:,.0f}. ROI: {multiple}x"
            return "Koi active campaign nahi hai. Pehle campaign bhejein." if language == "hinglish" else "No active campaign. Send a campaign first."
        
        # Insights
        if any(word in msg_lower for word in ["insight", "trend", "pattern"]):
            insight_list = insights.get("insights", [])
            if insight_list:
                top_insight = insight_list[0].get("description", "")
                if language == "hinglish":
                    return f"Key insight: {top_insight}"
                return f"Key insight: {top_insight}"
            return "Insights Insights tab mein dekhein." if language == "hinglish" else "Check the Insights tab for trends."
        
        # Default response with summary
        regular = summary.get("regular_customers", 0)
        at_risk_count = (summary.get("segments", {}) or segments).get("At-Risk", 0)
        
        if language == "hinglish":
            return f"Aapke {regular} regular customers hain. {at_risk_count} at-risk hain. Kya jaanna chahte hain - at-risk customers, campaign suggestion, ya insights?"
        return f"You have {regular} regular customers. {at_risk_count} are at-risk. What would you like to know - at-risk customers, campaign suggestions, or insights?"
    
    async def process_message(self, message: str) -> AgentResponse:
        """Process a user message and return a response."""
        language = self._detect_language(message)
        tools_needed = self._determine_tools_needed(message)
        
        tools_used = []
        tool_results = {}
        
        # Execute all needed tools
        for tool_name in tools_needed:
            result = self._execute_tool(tool_name)
            tool_results[tool_name] = result
            if result.success:
                tools_used.append(tool_name)
        
        # Try Gemini first
        response_text = self._generate_with_gemini(message, tool_results, language)
        
        # Fallback to rule-based if Gemini fails
        if not response_text:
            response_text = self._generate_fallback_response(message, tool_results, language)
        
        # Compile data from tool results
        data = {}
        for tool_name, result in tool_results.items():
            if result.success:
                data[tool_name] = result.data
        
        return AgentResponse(
            response=response_text,
            tools_used=tools_used,
            data=data if data else None,
            language=language
        )
    
    def process_message_sync(self, message: str) -> AgentResponse:
        """Synchronous version of process_message."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.process_message(message))
                    return future.result()
            return loop.run_until_complete(self.process_message(message))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.process_message(message))


if __name__ == "__main__":
    # Quick test
    print("Testing LoyalPay Agent...")
    print("=" * 60)
    
    agent = LoyalPayAgent()
    
    # Register mock tools
    agent.register_tool("get_store_summary", lambda: {
        "regular_customers": 307,
        "total_customers": 345,
        "total_revenue": 258165,
        "segments": {"Champion": 83, "Loyal": 77, "At-Risk": 59, "New": 35, "Lost": 5}
    })
    
    agent.register_tool("get_at_risk_customers", lambda limit=50: {
        "customers": [
            {"label": "#B60", "recency_days": 16, "churn_probability": 0.72, "monetary_avg": 154},
            {"label": "#B57", "recency_days": 15, "churn_probability": 0.75, "monetary_avg": 144},
            {"label": "#C31", "recency_days": 14, "churn_probability": 0.68, "monetary_avg": 132},
        ],
        "total": 29
    })
    
    agent.register_tool("suggest_offer", lambda budget=500: {
        "suggestion": {
            "target_count": 29,
            "cashback_per_customer": 20,
            "total_budget": 500,
            "expected_revenue": 2950,
            "expected_roi": 8.9
        },
        "summary": "Send ₹20 cashback to 29 at-risk regulars"
    })
    
    agent.register_tool("get_insights", lambda: {"insights": []})
    agent.register_tool("get_campaign_roi", lambda campaign_id=None: {})
    agent.register_tool("get_segments", lambda: {"Champion": 83, "Loyal": 77, "At-Risk": 59})
    
    # Test queries
    test_queries = [
        "Kaun se customers wapas nahi aaye?",
        "Kitne regular customers hain?",
        "Campaign suggest karo",
        "Store ka summary batao",
        "Hello"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        response = agent.process_message_sync(query)
        print(f"🤖 Response: {response.response}")
        print(f"   Tools: {response.tools_used}")
    
    print("\n" + "=" * 60)
    print("Agent tests completed! ✓")
