import json
import os
import yaml
import chromadb
from fastapi import APIRouter
from sentence_transformers import SentenceTransformer

from src.app.models.SQLresponse import SQLResponse
from src.app.models.query_response import QueryRequest
from src.app.scripts.forbid_actions import process_query
from src.app.scripts.extract_variables import extract_variables
from src.app.scripts.gemini_service import gemini_reasoner 
from src.app.scripts.schema import SchemaProvider  # Import your new SchemaProvider

# --- Initialization ---
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

QUERIES_PATH = "data/queries.json"
with open(QUERIES_PATH, "r") as f:
    TEMPLATES_DATA = json.load(f)

router = APIRouter(prefix="", tags=["Items"])

# Model & ChromaDB Setup
model = SentenceTransformer(config["MODEL_PATH"])
client = chromadb.PersistentClient(path=config["CHROMA_PATH"])
collection = client.get_or_create_collection(name="sql_templates")
CONFIDENCE_THRESHOLD = config["CONFIDENCE_THRESHOLD"]

@router.post("/ask", response_model=SQLResponse)
async def ask_sql(request: QueryRequest):
    user_input = request.user_text.strip()
    
    # 1. Security Guardrail
    security_check = process_query(user_input)
    if security_check.get("status") == "BLOCKED":
        return SQLResponse(status="blocked", message=security_check.get("reason") or "Action forbidden.")
    # 2. Vector Search
    query_emb = model.encode(user_input).tolist()
    results = collection.query(query_embeddings=[query_emb], n_results=1)

    final_id = results["ids"][0][0] if results["ids"] and results["ids"][0] else "N/A"
    final_dist = float(results["distances"][0][0]) if results["distances"] else 1.0
    
    # 3. Retrieve Template Data
    matched_template = next((item for item in TEMPLATES_DATA if str(item["id"]) == str(final_id)), {})
    required_fields = matched_template.get("required", [])
    raw_query = matched_template.get("query", "")

    # 4. Local Variable Extraction (Attempt)
    variables = extract_variables(user_input, required_fields) if required_fields else {}
    # 5. Schema Context

    
    needed_tables = matched_template.get("tables", [])
    dynamic_schema = SchemaProvider.get_context(needed_tables)

    # Prepare current_sql (might still have {FirstName} placeholders)
    try:
        current_sql = raw_query.format(**variables)
    except Exception:
        current_sql = raw_query 

    # 6. CALL GEMINI (The "Editor" Phase)
    # Ensure your gemini_reasoner prompt tells Gemini to:
    # "If placeholders like {FirstName} exist, extract them from user_intent and return a valid SQL."
    validation = gemini_reasoner.double_check_generated_sql(
        sql_to_test=current_sql,
        table_schema=dynamic_schema,
        user_intent=user_input,
        params=variables 
    )
    print(validation)
    # Safety Gate
    if not validation.get("is_safe", True): 
        return SQLResponse(status="blocked", message=f"Safety violation: {validation.get('comment')}")

    # If Gemini returns a SQL string, we use it. 
    final_sql = validation.get("sql") if validation.get("sql") else current_sql
    
    # We check if there are still any curly braces {} left in the final string
    import re
    has_unfilled_params = bool(re.search(r'\{.*?\}', final_sql)) # type: ignore
    
    # Logic: 
    # - Success if Gemini says it's correct AND no {placeholders} remain.
    # - If Gemini failed to fill them, return missing_params.
    if validation.get("is_correct", False) and not has_unfilled_params:
        status = "success"
        message = validation.get("comment", "SQL generated successfully")
    elif has_unfilled_params:
        status = "missing_params"
        message = f"Missing data for: {', '.join(required_fields)}"
    else:
        status = "low_confidence"
        message = validation.get("comment", "Could not verify SQL")

    return SQLResponse(
        status=status,
        message=message,
        matched_sql=final_sql, 
        template_id=str(final_id),
        distance=final_dist,
        extracted_params=variables 
    )