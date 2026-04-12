def sql_double_check(sql_to_test, table_schema, user_intent, params):
    return f"""
    You are an expert SQL Auditor. Your job is to validate and correct SQL queries for an HCM system.

    ### SCHEMA:
    {table_schema}

    ### USER INTENT:
    "{user_intent}"

    ### CURRENT SQL:
    {sql_to_test}

    ### EXTRACTED PARAMETERS:
    {params}

    ### INSTRUCTIONS:
    1. **Validation**: Does the CURRENT SQL accurately reflect the USER INTENT given the SCHEMA?
    2. **Variable Repair**: If the EXTRACTED PARAMETERS are missing names (like FirstName/LastName) or IDs that are clearly present in the USER INTENT, rewrite the SQL to include them.
    3. **Safety**: Ensure no destructive operations (DROP, DELETE, UPDATE) are present unless explicitly part of the intent.
    4. **Refinement**: If the query is logically correct but uses wrong column names (e.g., 'name' instead of 'FirstName'), fix it.

    ### OUTPUT FORMAT (STRICT JSON):
    {{
      "is_correct": bool,
      "is_safe": bool,
      "sql": "the_corrected_or_original_sql",
      "comment": "Brief explanation of changes or 'Looks good'"
    }}
    """

def sql_correction_check(result, table, user_text, param):
    return f"""
You are a SQL debugging and repair engine.

Context:
- User intent: {user_text}
- Original SQL: {result}
- Table schema: {table}
- Extracted parameters: {param}

Task:
1. Identify why the SQL fails (logic, schema mismatch, joins, filters, aggregation).
2. Ensure all referenced columns and tables exist in schema.
3. Fix the SQL while preserving original intent.
4. If correction is impossible, explain why clearly.

Return ONLY a Python dictionary:

{{
    "corrected_sql": "Fixed SQL query or original if already correct",
    "issue": "Main problem in the original query",
    "notes": "Assumptions or edge cases (empty string if none)"
}}

Rules:
- No extra text outside dictionary.
- Never invent schema elements.
- Prefer minimal edits over full rewrites unless necessary.
"""