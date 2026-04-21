import json
import os 
import re
import time
from openai import OpenAI
from dotenv import load_dotenv

from core.prompts import JD_PROMPT, RESUME_PROMPT, CLASSIFY_PROMPT, SKILL_MAPPER_PROMPT

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# CONFIG
# -----------------------------
DYNAMIC_INFERENCE_FLOOR = 0.45
MAX_RETRIES = 2


# -----------------------------
# NORMALIZE (LOCAL SAFETY)
# -----------------------------
def normalize(text):
    text = str(text or "").lower().strip()
    text = re.sub(r'[^a-z0-9\s#+.]', ' ', text)
    return " ".join(text.split())


# -----------------------------
# 1. BASE LLM CALL (RETRY SAFE)
# -----------------------------
def call_llm(prompt: str) -> str:
    for attempt in range(MAX_RETRIES + 1):
        try:
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return res.choices[0].message.content or ""

        except Exception as e:
            print(f"⚠️ OpenAI API Error (Attempt {attempt+1}): {e}")
            time.sleep(1)

    return ""


# -----------------------------
# 2. CLEAN OUTPUT (STRONG)
# -----------------------------
def clean_llm_output(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r'```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```', '', text)

    text = text.strip()
    text = text.replace("{{", "{").replace("}}", "}")

    while len(text) > 2:
        new_text = text.strip('"\'').strip()
        if new_text == text:
            break
        text = new_text

    start = text.find('{')
    if start != -1:
        brace_count = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start:i+1]

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)

    return text


# -----------------------------
# 3. SAFE JSON PARSER
# -----------------------------
def safe_json_parse(text: str):
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
# 6. CLASSIFIER
# -----------------------------
def classify_job_type(role_name: str, description: str) -> str:
    prompt = CLASSIFY_PROMPT \
        .replace("{role_name}", role_name) \
        .replace("{description}", description)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    cleaned = cleaned.upper().strip()
    cleaned = re.sub(r'[^A-Z\-]', '', cleaned)

    if "NON-TECH" in cleaned:
        return "NON-TECH"
    if "TECH" in cleaned:
        return "TECH"

    return "NON-TECH"


# -----------------------------
# 7. SEMANTIC MATCHER (STRICT HYBRID)
# -----------------------------
def get_semantic_matches(jd_requirements: list, candidate_skills: list):
    if not jd_requirements or not candidate_skills:
        return {"matches": [], "total_matches": 0}

    prompt = SKILL_MAPPER_PROMPT \
        .replace("{jd_requirements}", json.dumps(jd_requirements)) \
        .replace("{candidate_skills}", json.dumps(candidate_skills))

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    print("\n🔍 SKILL MATCH DEBUG")
    print("RAW:", repr(response[:150]))
    print("CLEANED:", repr(cleaned[:150]))

    parsed = safe_json_parse(cleaned)

    matches = parsed.get("matches", [])
    filtered_matches = []

    for m in matches:
        jd_skill = m.get("jd_skill")
        candidate_skill = m.get("candidate_skill")
        score = m.get("score")

        if not jd_skill or not candidate_skill:
            continue

        jd_norm = normalize(jd_skill)
        cand_norm = normalize(candidate_skill)

        # 🚫 Reject garbage tokens like "c"
        if len(jd_norm) <= 1:
            continue

        # -----------------------------
        # STRICT HYBRID LOGIC
        # -----------------------------
        if score is None:
            # ✅ Only allow exact normalized match
            if jd_norm == cand_norm:
                filtered_matches.append(m)
            continue

        try:
            score = float(score)

            if score >= DYNAMIC_INFERENCE_FLOOR:
                filtered_matches.append(m)

        except (ValueError, TypeError):
            continue

    return {
        "matches": filtered_matches,
        "total_matches": len(filtered_matches)
    }