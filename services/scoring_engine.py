import re

# -----------------------------
# NORMALIZE
# -----------------------------
def normalize(text):
    """
    Standardized normalization to match skill_matcher.py.
    Removes special characters to ensure dictionary keys align.
    """
    text = str(text or "").lower().strip()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

# -----------------------------
# CALCULATE WEIGHTED MATCH SCORE 
# -----------------------------
def calculate_weighted_score(requirements, matched_list, debug_map, total_weight):
    """
    Calculates score based on a binary match.
    If the skill exists in the matched list, it gets 100% credit for that skill.
    """
    if not requirements:
        return 0

    matched_count = 0
    # Pre-normalize the matched list for consistent lookup
    norm_matched_list = [normalize(m) for m in matched_list]

    for skill in requirements:
        key = normalize(skill)
        
        # Binary check: If confirmed by Matcher or present in the debug map
        if key in norm_matched_list or key in debug_map:
            matched_count += 1

    # Match Ratio (e.g., 12/12 = 1.0)
    match_ratio = matched_count / (len(requirements) + 1e-6)
    
    # Scale to the weight (e.g., 1.0 * 55 = 55.0)
    return round(match_ratio * total_weight, 1)


# -----------------------------
# MAIN BUILD FUNCTION
# -----------------------------
def build_output(jd, resume, skills_result, exp_result):
    """
    Assembles the final JSON response with scores, breakdowns, and explanations.
    """
    # 1. SKILLS INPUT
    p_req = jd.get("primary_skills") or []
    g_req = jd.get("good_to_have") or []

    # Get data from the Matcher output
    primary_data = skills_result.get("primarySkillsMatch", {})
    good_data    = skills_result.get("goodToHave", {})

    p_matched = primary_data.get("matchedSkills", []) or []
    g_matched = good_data.get("matchedSkills", []) or []

    p_missing = primary_data.get("missingSkills", []) or []
    g_missing = good_data.get("missingSkills", []) or []

    # Extract metadata maps (used primarily for normalization/fallback)
    p_debug = primary_data.get("debug", {}) or {}
    g_debug = good_data.get("debug", {}) or {}


    # 2. SKILL SCORING (Flat Logic)
    primary_score = calculate_weighted_score(
        requirements=p_req,
        matched_list=p_matched,
        debug_map=p_debug,
        total_weight=55
    )
    
    good_score = calculate_weighted_score(
        requirements=g_req,
        matched_list=g_matched,
        debug_map=g_debug,
        total_weight=20
    )


    # 3. EXPERIENCE SCORING (20 points)
    req_min = jd.get("experience_min_years") or 0
    req_max = jd.get("experience_max_years") or 0
    cand_exp = exp_result.get("tech_experience_years", 0)

    # Formatting experience strings
    req_exp_str = f"{req_min}-{req_max} years" if req_max else f"{req_min}+ years"

    c_years = int(cand_exp)
    c_months = int(round((cand_exp - c_years) * 12))
    y_lab = "years" if c_years != 1 else "year"
    m_lab = "months" if c_months != 1 else "month"

    cand_exp_str = (
        f"{c_years} {y_lab} {c_months} {m_lab}"
        if c_months > 0 else f"{c_years} {y_lab}"
    )

    # Experience Logic: Binary score (Meet/Not Meet)
    exp_score = 20 if cand_exp >= req_min else 0

    exp_explanation = (
        f"Candidate has {cand_exp_str} which "
        f"{'meets' if exp_score > 0 else 'does not meet'} "
        f"the minimum required {req_min} years."
    )


    # 4. LOCATION MATCH (5 points)
    loc_jd = jd.get("location", "")
    loc_res = resume.get("location", "")

    n_loc_jd  = normalize(loc_jd)
    n_loc_res = normalize(loc_res)

    loc_matched = False
    if n_loc_jd and n_loc_res:
        loc_matched = n_loc_res in n_loc_jd or n_loc_jd in n_loc_res

    location_score = 5 if loc_matched else 0


    # 5. FINAL SCORE ASSEMBLY
    overall = primary_score + good_score + exp_score + location_score


    # 6. FINAL OUTPUT OBJECT
    return {
        "message": "Contest processed successfully",
        "data": {
            "finalScores": {
                "snsScoringResult": {
                    "resumeMatch": {
                        "OverallScore": round(overall, 1),
                        "scoreOutOf": 100
                    },
                    "scoreBreakdown": {
                        "primarySkillsMatch": {
                            "score": primary_score,
                            "weight": 55,
                            "matchedSkills": p_matched,
                            "missingSkills": p_missing,
                            "explanation": (
                                f"Candidate has matched {len(p_matched)} "
                                f"out of {len(p_req)} primary skills."
                            ),
                            "requirements": p_req,
                        },
                        "goodToHave": {
                            "score": good_score,
                            "weight": 20,
                            "matchedSkills": g_matched,
                            "missingSkills": g_missing,
                            "explanation": (
                                f"Candidate has matched {len(g_matched)} "
                                f"out of {len(g_req)} good-to-have skills."
                            ),
                            "requirements": g_req,
                        },
                        "experienceMatch": {
                            "score": exp_score,
                            "weight": 20,
                            "requiredExperience": req_exp_str,
                            "candidateExperience": cand_exp_str,
                            "explanation": exp_explanation
                        },
                        "locationMatch": {
                            "score": location_score,
                            "weight": 5,
                            "jobLocationRequirement": loc_jd,
                            "candidateLocation": loc_res if loc_res else "Not specified",
                            "matched": loc_matched
                        }
                    }
                }
            }
        }
    }