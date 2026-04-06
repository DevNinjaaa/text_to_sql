import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm")

patterns = {
    "email": [{"TEXT": {"REGEX": r"[a-zA-Z0-9-_.]+@[a-zA-Z0-9-_.]+"}}],
    "departmentId": [{"IS_DIGIT": True}],
    "employeeId": [{"IS_DIGIT": True}],
    "managerId": [{"IS_DIGIT": True}],
    "jobId": [{"IS_DIGIT": True}],
    "applicantId": [{"IS_DIGIT": True}],
    "limit": [{"IS_DIGIT": True}],
    "status": [{"LOWER": {"IN": ["pending", "completed", "open", "closed", "active", "backend"]}}], 
    "gender": [{"LOWER": {"IN": ["male", "female", "other"]}}],
    "domain": [{"TEXT": {"REGEX": r"@[a-zA-Z0-9-.]+"}}],
    
    "jobTitle": [{"LOWER": {"IN": ["title", "tittle", "position"]}}, {"IS_ALPHA": True, "OP": "+"}],
    "keyword": [{"LOWER": {"IN": ["with", "containing", "called"]}}, {"IS_ALPHA": True, "OP": "+"}]
}

def extract_variables(text, required_fields):
    doc = nlp(text)
    extracted = {}
    
    matcher = Matcher(nlp.vocab)
    for field in required_fields:
        if field in patterns:
            matcher.add(field, [patterns[field]])
    
    matches = matcher(doc)
    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]
        span = doc[start:end]
        
        if string_id in ["jobTitle", "keyword"]:
            extracted[string_id] = " ".join([token.text for token in span[1:]])
        else:
            extracted[string_id] = span.text
            
    return extracted