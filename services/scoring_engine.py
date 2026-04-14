def normalize(text):
    return str(text or "").lower().strip()

def build_output(jd, resume, skills, exp_result):
    # 1. Skills Scoring
    p_req = jd.get("primary_skills") or []
    p_matched = skills.get("primary_matched") or []
    primary_score = round((len(p_matched) / (len(p_req) + 1e-6)) * 55, 1)

    g_req = jd.get("good_to_have") or []
    g_matched = skills.get("good_matched") or []
    good_score = round((len(g_matched) / (len(g_req) + 1e-6)) * 20, 1)

    # 2. Experience Logic
    req_min = jd.get("experience_min_years") or 0
    req_max = jd.get("experience_max_years") or 0
    cand_exp = exp_result.get("tech_experience_years", 0)

    req_exp_str = f"{req_min}-{req_max} years" if req_max else f"{req_min}+ years"

    c_years = int(cand_exp)
    c_months = int(round((cand_exp - c_years) * 12))
    
    y_lab = "years" if c_years != 1 else "year"
    m_lab = "months" if c_months != 1 else "month"
    cand_exp_str = f"{c_years} {y_lab} {c_months} {m_lab}" if c_months > 0 else f"{c_years} {y_lab}"

    exp_score = 20 if cand_exp >= req_min else 0
    exp_explanation = f"Candidate has {cand_exp_str} which {'meets' if exp_score > 0 else 'does not meet'} the minimum required {req_min} years."

    # 3. Location Match (FIXED)
    loc_jd = jd.get("location", "")
    loc_res = resume.get("location", "")
    
    n_loc_jd = normalize(loc_jd)
    n_loc_res = normalize(loc_res)

    # Check if both strings have content before matching
    # This prevents an empty candidate location from matching "" in the JD
    if n_loc_res and n_loc_jd:
        loc_matched = n_loc_res in n_loc_jd or n_loc_jd in n_loc_res
    else:
        loc_matched = False

    location_score = 5 if loc_matched else 0

    overall = primary_score + good_score + exp_score + location_score

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
                            "missingSkills": skills.get("primary_missing", []),
                            "explanation": f"Candidate has matched {len(p_matched)} out of {len(p_req)} primary skills.",
                            "requirements": p_req
                        },
                        "goodToHave": {
                            "score": good_score,
                            "weight": 20,
                            "matchedSkills": g_matched,
                            "missingSkills": skills.get("good_missing", []),
                            "explanation": f"Candidate has matched {len(g_matched)} out of {len(g_req)} good-to-have skills.",
                            "requirements": g_req
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