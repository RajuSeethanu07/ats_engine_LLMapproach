from services.parser import extract_text, extract_skills_from_text
from services.llm_service import parse_jd, parse_resume
from services.experience_engine import calculate_tech_experience
from services.skill_matcher import match
from services.scoring_engine import build_output
import json


def main():
    try:
        # -----------------------------
        # 1. EXTRACT TEXT
        # -----------------------------
        jd_text = extract_text("sample_data/Senior Cloud Admin jd.pdf")
        resume_text = extract_text("sample_data/28331-Manoj_Senior-Cloud-Admin.pdf")

        if not jd_text or not resume_text:
            raise ValueError("❌ Failed to extract text from input PDFs.")

        # -----------------------------
        # 2. PARSE JD + RESUME
        # -----------------------------
        jd = parse_jd(jd_text)
        resume = parse_resume(resume_text)

        # -----------------------------
        # 3. SAFE JSON VALIDATION
        # -----------------------------
        if isinstance(resume, dict) and resume.get("error"):
            print("\n❌ Resume Parsing Error:")
            print(json.dumps(resume, indent=2))
            raise ValueError("Resume parsing failed")

        if isinstance(jd, dict) and jd.get("error"):
            print("\n❌ JD Parsing Error:")
            print(json.dumps(jd, indent=2))
            raise ValueError("JD parsing failed")

        # -----------------------------
        # 🔥 4. EXTRA SKILL EXTRACTION (NEW)
        # -----------------------------
        extra_skills = extract_skills_from_text(resume_text)

        print("\n================ EXTRA SKILLS (LLM DEEP SCAN) ================\n")
        print(extra_skills)

        # -----------------------------
        # 🔥 5. MERGE SKILLS (CRITICAL FIX)
        # -----------------------------
        resume["skills"] = list(set(
            (resume.get("skills") or []) + extra_skills
        ))

        # -----------------------------
        # 🔍 DEBUG: CHECK FINAL SKILLS
        # -----------------------------
        print("\n================ FINAL MERGED SKILLS ================\n")
        print(resume["skills"])

        # -----------------------------
        # 6. EXPERIENCE ANALYSIS
        # -----------------------------
        exp_result = calculate_tech_experience(resume)

        print("\n================ EXPERIENCE RESULT ================\n")
        print(json.dumps(exp_result, indent=2))

        # -----------------------------
        # 7. SKILL MATCHING
        # -----------------------------
        skills = match(jd, resume)

        print("\n================ SKILL MATCH RESULT ================\n")
        print(json.dumps(skills, indent=2))

        # -----------------------------
        # 8. SCORING ENGINE
        # -----------------------------
        final = build_output(jd, resume, skills, exp_result)

        # -----------------------------
        # 9. OUTPUT
        # -----------------------------
        print("\n================ ATS RESULT ================\n")
        print(json.dumps(final, indent=2))

    except Exception as e:
        print("\n❌ ERROR IN PIPELINE:\n", str(e))


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    main()