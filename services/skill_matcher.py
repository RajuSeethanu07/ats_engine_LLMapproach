from services.llm_service import get_semantic_matches
from services.embedding_engine import get_embeddings_batch
from sklearn.metrics.pairwise import cosine_similarity
import re

# -----------------------------
# CONFIG
# -----------------------------
EMBEDDING_THRESHOLD = 0.85
LLM_VALIDATION_FLOOR = 0.48
DYNAMIC_INFERENCE_FLOOR = 0.45

# -----------------------------
# CACHE
# -----------------------------
embedding_cache = {}

# -----------------------------
# NORMALIZE (STRICT FIX)
# -----------------------------
def normalize(text):
    text = str(text or "").lower().strip()
    # Keep #, +, . (C#, C++, .NET safe)
    text = re.sub(r'[^a-z0-9\s#+.]', ' ', text)
    return " ".join(text.split())

# -----------------------------
# KEYWORD MATCH (STRICT TOKEN MATCH)
# -----------------------------
def keyword_match(jd_skill, cand_skill):
    jd = normalize(jd_skill)
    cand = normalize(cand_skill)

    if not jd or not cand:
        return False

    # Exact match
    if jd == cand:
        return True

    jd_tokens = jd.split()
    cand_tokens = cand.split()

    # Strict token containment (no substring bugs)
    return all(token in cand_tokens for token in jd_tokens)

# -----------------------------
# EMBEDDING CACHE MANAGEMENT
# -----------------------------
def build_embedding_cache(all_skills):
    to_fetch = []
    for skill in all_skills:
        key = normalize(skill)
        if key not in embedding_cache:
            to_fetch.append(skill)

    if not to_fetch:
        return

    vectors = get_embeddings_batch(to_fetch)

    for skill, vec in zip(to_fetch, vectors):
        if vec is not None:
            embedding_cache[normalize(skill)] = vec

def get_cached_embedding(skill):
    return embedding_cache.get(normalize(skill))

# -----------------------------
# LLM SEMANTIC MAPPING (WITH SCORE)
# -----------------------------
def get_llm_match_map(jd_list, candidate_skills):
    response = get_semantic_matches(jd_list, candidate_skills) or {}
    matches = response.get("matches", []) or []

    return {
        normalize(m.get("jd_skill")): {
            "candidate": m.get("candidate_skill"),
            "score": m.get("score")
        }
        for m in matches if m.get("jd_skill")
    }

# -----------------------------
# FINAL MATCH ENGINE
# -----------------------------
def extract_matches(jd_list, candidate_skills):
    if not jd_list:
        return {}

    final_map = {}

    # Build embeddings once
    build_embedding_cache(jd_list + candidate_skills)

    # LLM mapping
    llm_map = get_llm_match_map(jd_list, candidate_skills)

    for jd_skill in jd_list:
        norm_jd = normalize(jd_skill)

        # -----------------------------
        # A. KEYWORD MATCH
        # -----------------------------
        keyword_hit = False
        matched_keyword_skill = None

        for cand in candidate_skills:
            if keyword_match(jd_skill, cand):
                keyword_hit = True
                matched_keyword_skill = cand
                break

        # -----------------------------
        # B. EMBEDDING MATCH
        # -----------------------------
        jd_emb = get_cached_embedding(jd_skill)
        best_emb_score = 0.0
        best_cand_name = None

        if jd_emb is not None:
            for cand in candidate_skills:
                cand_emb = get_cached_embedding(cand)
                if cand_emb is None:
                    continue

                score = float(cosine_similarity([jd_emb], [cand_emb])[0][0])

                if score > best_emb_score:
                    best_emb_score = score
                    best_cand_name = cand

                if best_emb_score >= 0.98:  # early exit
                    break

        # -----------------------------
        # C. LLM MATCH (WITH VALIDATION)
        # -----------------------------
        llm_entry = llm_map.get(norm_jd)

        llm_hit = llm_entry is not None
        llm_suggested_cand_skill = None
        llm_score = 0.0

        if llm_hit:
            llm_suggested_cand_skill = llm_entry.get("candidate")
            llm_score = float(llm_entry.get("score") or 0.0)

        is_llm_validated = False

        if llm_hit:
            if (
                best_emb_score >= LLM_VALIDATION_FLOOR and
                llm_score >= DYNAMIC_INFERENCE_FLOOR
            ):
                is_llm_validated = True

        # -----------------------------
        # FINAL DECISION
        # -----------------------------
        strong_match = (
            keyword_hit or
            best_emb_score >= EMBEDDING_THRESHOLD or
            is_llm_validated
        )

        if strong_match:
            if keyword_hit:
                display_match = matched_keyword_skill
            elif is_llm_validated:
                display_match = llm_suggested_cand_skill
            else:
                display_match = best_cand_name or "embedding"

            final_map[norm_jd] = {
                "jd_skill": jd_skill,
                "matched_with": display_match,
                "embedding_score": round(float(best_emb_score), 3),
                "keyword": keyword_hit,
                "llm": is_llm_validated
            }

    return final_map

# -----------------------------
# MAIN ENTRY POINT
# -----------------------------
def match(jd, resume):
    primary_reqs = jd.get("primary_skills") or []
    good_reqs = jd.get("good_to_have") or []
    candidate_skills = resume.get("skills") or []

    primary_map = extract_matches(primary_reqs, candidate_skills)
    good_map = extract_matches(good_reqs, candidate_skills)

    primary_matched = [s for s in primary_reqs if normalize(s) in primary_map]
    good_matched = [s for s in good_reqs if normalize(s) in good_map]

    return {
        "primarySkillsMatch": {
            "matched_count": len(primary_matched),
            "total_count": len(primary_reqs),
            "matchedSkills": primary_matched,
            "missingSkills": [s for s in primary_reqs if s not in primary_matched],
            "debug": primary_map
        },
        "goodToHave": {
            "matched_count": len(good_matched),
            "total_count": len(good_reqs),
            "matchedSkills": good_matched,
            "missingSkills": [s for s in good_reqs if s not in good_matched],
            "debug": good_map
        }
    }