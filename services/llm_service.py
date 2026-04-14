import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

from core.prompts import JD_PROMPT, RESUME_PROMPT, CLASSIFY_PROMPT, SKILL_MAPPER_PROMPT

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# 1. BASE LLM CALL
# -----------------------------
def call_llm(prompt: str) -> str:
    try:
        res = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return res.choices[0].message.content or ""
    except Exception as e:
        print(f"⚠️ OpenAI API Error: {e}")
        return ""


# -----------------------------
# 2. CLEAN OUTPUT 
# -----------------------------
def clean_llm_output(text: str) -> str:
    if not text:
        return ""

    # Remove markdown
    text = re.sub(r'```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)

    text = text.strip()

    # 🔥 FIX: Convert double braces → single braces
    text = text.replace("{{", "{").replace("}}", "}")

    # Remove outer quotes
    while len(text) > 2:
        old = text
        text = text.strip('"\'').strip()
        if text == old:
            break

    # Extract JSON safely
    start = text.find('{')
    if start == -1:
        return text

    brace_count = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]

    return text

# -----------------------------
# 3. SAFE JSON PARSER 
# -----------------------------
def safe_json_parse(text: str):
    """
    Never crashes. Always returns dict.
    """
    if not text:
        return {"error": "empty_response"}

    try:
        return json.loads(text)
    except Exception as e:
        print("⚠️ JSON Parse Failed:", text[:300])
        return {
            "error": "invalid_json_format",
            "raw_response": text[:500],
            "parse_error": str(e)
        }


# -----------------------------
# 4. JD PARSER
# -----------------------------
def parse_jd(text: str):
    prompt = JD_PROMPT.replace("{text}", text)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    print("\n🔍 JD DEBUG")
    print("RAW:", repr(response[:150]))
    print("CLEANED:", repr(cleaned[:150]))

    return safe_json_parse(cleaned)


# -----------------------------
# 5. RESUME PARSER
# -----------------------------
def parse_resume(text: str):
    prompt = RESUME_PROMPT.replace("{text}", text)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    print("\n🔍 RESUME DEBUG")
    print("RAW:", repr(response[:150]))
    print("CLEANED:", repr(cleaned[:150]))

    return safe_json_parse(cleaned)


# -----------------------------
# 6. CLASSIFIER (FINAL SAFE)
# -----------------------------
def classify_job_type(role_name: str, description: str) -> str:
    prompt = CLASSIFY_PROMPT \
        .replace("{role_name}", role_name) \
        .replace("{description}", description)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    # Normalize aggressively
    cleaned = cleaned.upper().strip()
    cleaned = re.sub(r'[^A-Z\-]', '', cleaned)

    if "NON-TECH" in cleaned:
        return "NON-TECH"
    if "TECH" in cleaned:
        return "TECH"

    return "NON-TECH"


# -----------------------------
# 7. SEMANTIC MATCHER
# -----------------------------
def get_semantic_matches(jd_requirements: list, candidate_skills: list):
    if not jd_requirements or not candidate_skills:
        return {"matches": []}

    prompt = SKILL_MAPPER_PROMPT \
        .replace("{jd_requirements}", json.dumps(jd_requirements)) \
        .replace("{candidate_skills}", json.dumps(candidate_skills))

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    print("\n🔍 SKILL MATCH DEBUG")
    print("RAW:", repr(response[:150]))
    print("CLEANED:", repr(cleaned[:150]))

    return safe_json_parse(cleaned)