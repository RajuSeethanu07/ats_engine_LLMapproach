from services.llm_service import get_semantic_matches


def normalize(text):
    """Normalize text for consistent comparison."""
    return str(text or "").strip().lower()


def match(jd, resume):
    """
    Semantic Skill Matcher using LLM + strong Python safeguards
    """

    # -----------------------------
    # 1. SAFE INPUT EXTRACTION
    # -----------------------------
    primary_reqs = jd.get("primary_skills") or []
    good_to_have_reqs = jd.get("good_to_have") or []
    candidate_skills = resume.get("skills") or []

    # Normalize inputs
    primary_reqs_norm = [normalize(s) for s in primary_reqs]
    good_reqs_norm = [normalize(s) for s in good_to_have_reqs]
    candidate_skills_norm = [normalize(s) for s in candidate_skills]

    all_jd_reqs = primary_reqs + good_to_have_reqs

    # -----------------------------
    # 2. LLM SEMANTIC MATCHING
    # -----------------------------
    mapping_data = get_semantic_matches(all_jd_reqs, candidate_skills) or {}
    matches = mapping_data.get("matches", []) or []

    # -----------------------------
    # 3. SAFE MATCH EXTRACTION
    # -----------------------------
    matched_jd_names = set()

    for m in matches:
        jd_skill = normalize(m.get("jd_skill"))
        cand_skill = normalize(m.get("candidate_skill"))

        if jd_skill and cand_skill:
            matched_jd_names.add(jd_skill)

    # -----------------------------
    # 4. MATCH CLASSIFICATION
    # -----------------------------
    primary_matched = [
        s for s in primary_reqs
        if normalize(s) in matched_jd_names
    ]

    primary_missing = [
        s for s in primary_reqs
        if normalize(s) not in matched_jd_names
    ]

    good_matched = [
        s for s in good_to_have_reqs
        if normalize(s) in matched_jd_names
    ]

    good_missing = [
        s for s in good_to_have_reqs
        if normalize(s) not in matched_jd_names
    ]

    # -----------------------------
    # 5. SCORING (SAFE DIVISION)
    # -----------------------------
    p_score = (
        (len(primary_matched) / len(primary_reqs)) * 55
        if primary_reqs else 0
    )

    g_score = (
        (len(good_matched) / len(good_to_have_reqs)) * 20
        if good_to_have_reqs else 0
    )

    # -----------------------------
    # 6. DEBUG LOG (CLEAN)
    # -----------------------------
    print("\n🔍 SKILL MATCH DEBUG")
    print("JD Skills:", all_jd_reqs)
    print("Candidate Skills:", candidate_skills)
    print("LLM Matches:", matches)
    print("Matched JD Skills:", matched_jd_names)

    # -----------------------------
    # 7. FINAL OUTPUT
    # -----------------------------
    return {
        "primary_matched": primary_matched,
        "primary_missing": primary_missing,
        "good_matched": good_matched,
        "good_missing": good_missing,
        "primary_score": round(p_score, 1),
        "good_score": round(g_score, 1),
        "match_score": round(p_score + g_score, 2)
    }