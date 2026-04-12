import string
import spacy
import re
from thefuzz import fuzz
import yaml


with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# 1. Load the spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# --- CONFIGURATION ---
danger_verbs = config["DANGER_VERBS"]
# ___ allowed tables
tables = config["TABLES"]

# --- LAYER 1: FUZZY TYPO PROTECTION ---
def is_suspicious(text: str) -> bool:
    words = text.lower().split()
    for word in words:
        word = word.strip(string.punctuation)
        for danger in danger_verbs:
            if fuzz.ratio(word, danger.lower()) > 85:  # maybe increase threshold
                print(f"--- [SECURITY BLOCK]: Detected '{word}' (looks like '{danger}') ---")
                return True
    return False

# LAYER 2: INTENT & EXTRACTION
def process_query(user_text: str):
    # 1. Fuzzy typo
    if is_suspicious(user_text):
        return {"status": "BLOCKED", "reason": "Forbidden action detected (typo check)."}

    # 2. NLP Analysis
    doc = nlp(user_text.lower())
    actions = [token.lemma_ for token in doc if token.pos_ == "VERB"]

    # 3. Intent Validation
    if any(a.lower() in [v.lower() for v in danger_verbs] for a in actions):
        return {"status": "BLOCKED", "reason": "Forbidden verb intent detected."}

    return {"status": "ALLOWED"}
