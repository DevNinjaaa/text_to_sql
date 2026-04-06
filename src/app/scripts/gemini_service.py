import os
from google import genai
from google.genai import types
import json
import yaml
from dotenv import load_dotenv
# Loading config for API Key and Model Name
load_dotenv()


class GeminiReasoningService:
    def __init__(self):
        # Initialize the modern client
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-3-flash-preview"
        
        # This defines the "Brain" of The fallback logic
        self.system_instruction = """
        You are an SQL Debugging Assistant. You receive a user's natural language request, 
        the SQL template the system matched, and the parameters extracted.
        
        The user said this result was WRONG. Your job is to find the error.
        Return a JSON object with:
        - "error_type": (e.g., "WRONG_INTENT", "MISSING_VALUE", "EXTRACTION_MISMATCH")
        - "explanation": Short explanation of what went wrong.
        - "fix_suggestion": How the user should rephrase or what value is missing.
        """

    def analyze_sql_failure(self, user_text: str, matched_template: str, extracted_params: dict):
            user_context = f"""
            User Input: {user_text}
            Matched SQL Template: {matched_template}
            Extracted Params: {json.dumps(extracted_params)}
            """

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=user_context,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json"
                )
            )
            
            # 1. Check if text exists to satisfy Pylance/Type Safety
            if response.text:
                return json.loads(response.text)
            
            # 2. Fallback if Gemini fails to return text
            return {
                "error_type": "UNKNOWN_ERROR",
                "explanation": "failed to generate a response.",
                "fix_suggestion": "Please try rephrasing your request."
            }

# Instantiate as a singleton
gemini_reasoner = GeminiReasoningService()