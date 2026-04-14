import json
import re
from datetime import datetime
from services.llm_service import classify_job_type


# -----------------------------
# SAFE FLOAT PARSER
# -----------------------------
def safe_float(value):
    """
    Converts values like '5+ years', '8.5 years' → float
    """
    try:
        return float(value)
    except:
        match = re.search(r"\d+(\.\d+)?", str(value))
        return float(match.group()) if match else 0.0


# -----------------------------
# DATE PARSING
# -----------------------------
def parse_date(date_str):
    """Parses various date formats into datetime objects."""
    if not date_str:
        return None

    date_str = str(date_str).strip().lower()

    if date_str in ["present", "current", "till now", "today"]:
        return datetime.now()

    formats = [
        "%b %Y", "%B %Y", "%Y",
        "%m/%Y", "%d/%m/%Y", "%m-%Y",
        "%b-%Y", "%B-%Y"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if fmt == "%Y":
                return dt.replace(month=1)
            return dt
        except:
            continue

    return None


# -----------------------------
# MERGE EXPERIENCE (NO OVERLAP)
# -----------------------------
def merge_durations(experience_list):
    """
    Merge overlapping date ranges to avoid double counting
    """
    ranges = []

    for exp in experience_list:
        start = parse_date(exp.get("start_date"))
        end = parse_date(exp.get("end_date"))

        if start and end and end >= start:
            ranges.append((start, end))

    if not ranges:
        return 0.0

    # Sort by start date
    ranges.sort(key=lambda x: x[0])

    merged = []
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    total_months = 0
    for start, end in merged:
        total_months += (end.year - start.year) * 12 + (end.month - start.month)

    return total_months / 12


# -----------------------------
# FINAL EXPERIENCE DECIDER
# -----------------------------
def get_final_experience(calculated, summary):
    """
    Smart fusion of calculated and summary experience
    """

    # both available
    if calculated > 0 and summary > 0:
        # if close → trust calculated
        if abs(calculated - summary) <= 2:
            return calculated
        return max(calculated, summary)

    if calculated > 0:
        return calculated

    if summary > 0:
        return summary

    return 0.0


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def calculate_tech_experience(resume_data):
    """
    Production-grade experience calculator
    """

    # -----------------------------
    # INPUT HANDLING
    # -----------------------------
    if isinstance(resume_data, list):
        experience_list = resume_data
        summary_years = 0.0
    else:
        experience_list = resume_data.get("experience") or []
        summary_years = safe_float(resume_data.get("total_years_experience"))

    if not experience_list and summary_years == 0.0:
        return {
            "tech_experience_years": 0.0,
            "total_roles_analyzed": 0,
            "breakdown": [],
            "calculation_source": "none"
        }

    # -----------------------------
    # ROLE ANALYSIS
    # -----------------------------
    tech_experience_list = []
    breakdown = []

    for exp in experience_list:
        role_name = exp.get("role") or "Unknown Role"
        description = exp.get("description", "")

        start = parse_date(exp.get("start_date"))
        end = parse_date(exp.get("end_date"))

        # Classify role
        role_type = classify_job_type(role_name, description)

        if role_type not in ["TECH", "NON-TECH"]:
            role_type = "TECH"  # safe fallback

        # Only include TECH roles for calculation
        if role_type == "TECH" and start and end:
            tech_experience_list.append({
                "start_date": exp.get("start_date"),
                "end_date": exp.get("end_date")
            })

        # breakdown (for debugging/UI)
        duration_years = 0.0
        if start and end:
            duration_years = max(
                ((end.year - start.year) * 12 + (end.month - start.month)) / 12,
                0
            )

        breakdown.append({
            "role": role_name,
            "company": exp.get("company", "Unknown"),
            "type": role_type,
            "duration_years": round(duration_years, 2)
        })

    # -----------------------------
    # EXPERIENCE CALCULATION
    # -----------------------------
    calculated_years = merge_durations(tech_experience_list)

    # -----------------------------
    # FINAL EXPERIENCE
    # -----------------------------
    final_years = get_final_experience(calculated_years, summary_years)

    return {
        "tech_experience_years": round(final_years, 2),
        "total_roles_analyzed": len(experience_list),
        "breakdown": breakdown,
        "calculation_source": (
            "summary"
            if summary_years > calculated_years
            else "date_math"
        )
    }