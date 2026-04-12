import spacy
from spacy.matcher import Matcher

# Load the small English model
nlp = spacy.load("en_core_web_sm")

# --- 1. Pattern Definitions ---
PATTERNS = {
    "email": [{"TEXT": {"REGEX": r"[a-zA-Z0-9-_.]+@[a-zA-Z0-9-_.]+"}}],
    
    "jobId": [{"LOWER": "job"}, {"IS_DIGIT": True}],
    
    "status": [{"LOWER": {"IN": ["pending", "completed", "open", "closed", "active", "hired", "rejected"]}}], 
    
    # Matches "John Smith", "john smith", or even "John A. Smith"
    # We include NOUN because spaCy often misses PROPN for lowercase names
    "fullName": [
        {"POS": {"IN": ["PROPN", "NOUN"]}, "OP": "+"}, 
        {"IS_PUNCT": True, "OP": "?"},
        {"POS": {"IN": ["PROPN", "NOUN"]}, "OP": "+"}
    ],

    "jobTitle": [
        {"LOWER": {"IN": ["title", "position", "role"]}}, 
        {"POS": {"IN": ["NOUN", "PROPN", "ADJ"]}, "OP": "+"}
    ]
}

# --- 2. Field Mapping ---
# This maps your SQL Template {Variables} to the PATTERNS keys above
FIELD_MAP = {
    "FirstName": "fullName",
    "LastName": "fullName",
    "Email": "email",
    "Status": "status",
    "JobTitle": "jobTitle"
}

def extract_variables(text: str, required_fields: list) -> dict:
    """
    Extracts variables from text. If a 'fullName' pattern is found,
    it intelligently splits it into FirstName and LastName.
    """
    doc = nlp(text)
    extracted = {}
    matcher = Matcher(nlp.vocab)
    
    # Only add patterns that are actually required by the matched template
    for field in required_fields:
        pattern_key = FIELD_MAP.get(field, field)
        if pattern_key in PATTERNS:
            matcher.add(field, [PATTERNS[pattern_key]])

    matches = matcher(doc)
    
    for match_id, start, end in matches:
        field_name = nlp.vocab.strings[match_id]
        span = doc[start:end]
        value = span.text

        # --- Name Splitting Logic ---
        if field_name == "FirstName":
            # Take the first word (e.g., "John")
            extracted["FirstName"] = value.split()[0]
            
        elif field_name == "LastName":
            # Take the last word (e.g., "Smith")
            parts = value.split()
            if len(parts) > 1:
                extracted["LastName"] = parts[-1]
                
        # --- Handle Keyword Triggers ---
        elif field_name == "JobTitle":
            # Remove the trigger word "title" or "role"
            extracted["JobTitle"] = " ".join([t.text for t in span[1:]])
            
        else:
            extracted[field_name] = value
            
    return extracted
