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
        # Using the flash model for speed and reliability in JSON mode
        self.model_id = "gemini-2.5-flash-lite" 
        
        # We update the "Brain" to include SQL generation logic
        self.system_instruction = """
        You are an SQL Expert and Debugging Assistant. 
        You receive a user's natural language request, the SQL template matched, and the parameters extracted.

        The user marked this result as WRONG. Your job is:
        1. Find the error (Intent mismatch or missing parameters).
        2. If the user provided information that wasn't extracted (e.g., a name, ID, or title), 
           re-generate the SQL query by filling the template placeholders with the correct values.
        3. Wrap string values in single quotes (e.g., WHERE name = 'John').

        Return a JSON object with:
        - "error_type": (e.g., "WRONG_INTENT", "MISSING_VALUE", "EXTRACTION_MISMATCH")
        - "explanation": Short explanation of what went wrong.
        - "fix_suggestion": How the user should rephrase.
        - "corrected_sql": The complete, valid SQL query with placeholders replaced by actual values from the user input. If you cannot fix it, return null.
        """

    def analyze_sql_failure(self, user_text: str, matched_template: str, extracted_params: dict):
        user_context = f"""
        User Input: "{user_text}"
        Matched SQL Template: "{matched_template}"
        Extracted Params: {json.dumps(extracted_params)}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=user_context,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                return json.loads(response.text)
        
        except Exception as e:
            print(f"Gemini Error: {e}")

        # Fallback if generation fails
        return {
            "error_type": "UNKNOWN_ERROR",
            "explanation": "Failed to generate a correction.",
            "fix_suggestion": "Please try rephrasing your request.",
            "corrected_sql": None
        }

# Instantiate as a singleton
gemini_reasoner = GeminiReasoningService()