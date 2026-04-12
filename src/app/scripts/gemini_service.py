import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Importing your prompt templates
from src.app.scripts.prompt import sql_correction_check, sql_double_check

load_dotenv()

class GeminiReasoningService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Using the current standard Flash model for low-latency JSON
        self.model_id = "gemini-2.5-flash" 

    def double_check_generated_sql(self, sql_to_test, table_schema, user_intent, params):
        prompt = sql_double_check(sql_to_test, table_schema, user_intent, params)
        res = self._call_gemini(prompt)

        return {
            "is_safe": res.get("is_safe", True), # Match prompt key
            "is_correct": res.get("is_correct", False), # Match prompt key
            "sql": res.get("sql", sql_to_test), # Match prompt key
            "comment": res.get("comment", "No feedback provided")
        }

    def analyze_user_discrepancy(self, executed_sql, table_schema, user_intent, user_feedback):
        """
        Function 2: Reactive validation.
        Usecase user_message: "This data is wrong."
        It compares what was run vs what the user actually wanted.
        """
        # We craft a specific prompt for the "I didn't get what I intended" scenario
        feedback_prompt = f"""
        You are a SQL Debugger. The user claims the data returned is incorrect.
        
        User's Original Goal: {user_intent}
        SQL That Was Run: {executed_sql}
        Table Schema: {table_schema}
        User's Complaint: "{user_feedback}"

        Task:
        1. Identify the logical gap between the SQL and the User's Goal.
        2. Fix the SQL.

        Return ONLY JSON:
        {{
            "error_identified": true,
            "explanation": "Why the data was wrong",
            "corrected_sql": "SELECT ...",
            "confidence": 0.0-1.0
        }}
        """
        return self._call_gemini(feedback_prompt)

    def _call_gemini(self, prompt: str):
        """Standardized private helper for clean JSON responses."""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text) if response.text else {}
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return {"status": "error", "comment": str(e)}

# Singleton instance
gemini_reasoner = GeminiReasoningService()