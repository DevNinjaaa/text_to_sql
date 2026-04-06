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

# --- Initialization ---
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

QUERIES_PATH = "data/queries.json"
with open(QUERIES_PATH, "r") as f:
    TEMPLATES_DATA = json.load(f)

router = APIRouter(prefix="", tags=["Items"])

# Model Setup
model_path = config["MODEL_PATH"]
if os.path.exists(model_path):
    model = SentenceTransformer(model_path)
    print(f"Loaded model locally from {model_path}")
else:
    print("Local model path not found. Downloading...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    model.save(model_path)

# ChromaDB Setup
client = chromadb.PersistentClient(path=config["CHROMA_PATH"])
collection = client.get_or_create_collection(name="sql_templates")
CONFIDENCE_THRESHOLD = config["CONFIDENCE_THRESHOLD"]

@router.post("/ask", response_model=SQLResponse)
async def ask_sql(request: QueryRequest):
    user_input = request.user_text.strip()
    
    # 1. Security Guardrail
    security_check = process_query(user_input)
    if security_check.get("status") == "BLOCKED":
        return SQLResponse(
            status="blocked",
            message=security_check.get("reason") or "Action forbidden."
        )

    # 2. Vector Search
    query_emb = model.encode(user_input).tolist()
    results = collection.query(query_embeddings=[query_emb], n_results=1)

    if not results["ids"] or not results["ids"][0]:
        return SQLResponse(status="no_match", message="No templates found in database.")

    # Extract match metadata
    final_id = int(results["ids"][0][0])
    final_dist = float(results["distances"][0][0]) if results["distances"] else 1.0
    
    # Determine confidence status without exiting early
    is_low_confidence = final_dist > CONFIDENCE_THRESHOLD

    # 3. Retrieve Template Data
    matched_template = next((item for item in TEMPLATES_DATA if item["id"] == final_id), None)
    if not matched_template:
        return SQLResponse(status="error", message=f"Template ID {final_id} not found in JSON.")

    # 4. Variable Extraction & SQL Formatting
    required_fields = matched_template.get("required", [])
    raw_query = matched_template.get("query", "")
    variables = {}

    if required_fields:
        variables = extract_variables(user_input, required_fields)
        
        # Check for missing parameters
        missing = [f for f in required_fields if f not in variables]
        if missing:
            return SQLResponse(
                status="missing_params", 
                message=f"Please provide: {', '.join(missing)}",
                extracted_params=variables,
                distance=final_dist
            )
    
    try:
        # Generate the final SQL string
        final_sql = raw_query.format(**variables)
    except Exception as e:
        return SQLResponse(status="error", message=f"SQL Formatting failed: {str(e)}")

    # 5. Final Response
    # Even if confidence is low, we now return the matched_sql
    return SQLResponse(
        status="success" if not is_low_confidence else "low_confidence",
        message="Match found." if not is_low_confidence else "Low confidence match generated.",
        matched_sql=final_sql,
        template_id=str(final_id),
        distance=final_dist,
        extracted_params=variables
    )