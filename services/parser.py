import pdfplumber
import fitz  # PyMuPDF
import os
import re
import json

from services.llm_service import call_llm, clean_llm_output
from core.prompts import JD_PROMPT, RESUME_PROMPT, SKILL_EXTRACTION_PROMPT


# -----------------------------
# SAFE JSON PARSER
# -----------------------------
def safe_json_parse(text):
    try:
        return json.loads(text)
    except Exception:
        return {"error": "Invalid JSON", "raw": text}


# -----------------------------
# MAIN PDF EXTRACTION
# -----------------------------
def extract_text(path: str) -> str:
    """
    Robust PDF text extraction with fallback + normalization
    """

    # VALIDATION
    if not path or not isinstance(path, str):
        print("❌ Invalid file path")
        return ""

    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return ""

    if not path.lower().endswith(".pdf"):
        print(f"❌ Unsupported file format: {path}")
        return ""

    # TRY pdfplumber
    text, extracted_pages, total_pages = extract_with_pdfplumber(path)

    # FALLBACK → PyMuPDF
    if should_fallback(text, extracted_pages, total_pages):
        print("🔄 Switching to PyMuPDF fallback...")
        text2 = extract_with_pymupdf(path)

        if len(text2.strip()) > len(text.strip()):
            text = text2
            print("✅ PyMuPDF extraction improved results")

    # FINAL CLEANING
    text = normalize_text(text)

    if not text.strip():
        print(f"❌ No extractable text: {path}")
        return ""

    print(f"✅ Extracted {len(text)} chars")
    return text


# -----------------------------
# PDFPLUMBER EXTRACTION
# -----------------------------
def extract_with_pdfplumber(path):
    text_parts = []
    extracted_pages = 0
    total_pages = 0

    try:
        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()

                    if page_text and page_text.strip():
                        text_parts.append(page_text)
                        extracted_pages += 1
                    else:
                        print(f"⚠️ pdfplumber: No text on page {i+1}")

                except Exception as e:
                    print(f"⚠️ pdfplumber page {i+1} failed: {e}")

    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}")

    return "\n".join(text_parts), extracted_pages, total_pages


# -----------------------------
# PYMUPDF FALLBACK
# -----------------------------
def extract_with_pymupdf(path):
    text_parts = []

    try:
        doc = fitz.open(path)

        for i, page in enumerate(doc):
            try:
                page_text = page.get_text()

                if page_text:
                    text_parts.append(page_text)
                else:
                    print(f"⚠️ PyMuPDF: No text on page {i+1}")

            except Exception as e:
                print(f"⚠️ PyMuPDF page {i+1} failed: {e}")

    except Exception as e:
        print(f"⚠️ PyMuPDF failed: {e}")

    return "\n".join(text_parts)


# -----------------------------
# TEXT NORMALIZATION
# -----------------------------
def normalize_text(text: str) -> str:
    """
    Clean + normalize extracted text for better LLM understanding
    """

    if not text:
        return ""

    # Remove non-ASCII
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Fix broken words (IMPORTANT)
    text = re.sub(r"(\w)\s+(\w)", r"\1\2", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text)

    # Keep readability
    text = text.replace(". ", ".\n")

    return text.strip()


# -----------------------------
# FALLBACK DECISION
# -----------------------------
def should_fallback(text: str, extracted_pages: int, total_pages: int) -> bool:

    if not text.strip():
        return True

    if total_pages > 0 and (extracted_pages / total_pages) < 0.5:
        return True

    if len(text.strip()) < 500:
        return True

    return False


# -----------------------------
# PARSE JD
# -----------------------------
def parse_jd(text: str):
    if not text:
        return {"error": "Empty JD text"}

    prompt = JD_PROMPT.replace("{text}", text)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    print("\n🔍 JD DEBUG")
    print("RAW:", repr(response[:200]))
    print("CLEANED:", repr(cleaned[:200]))

    return safe_json_parse(cleaned)


# -----------------------------
# PARSE RESUME
# -----------------------------
def parse_resume(text: str):
    if not text:
        return {"error": "Empty resume text"}

    prompt = RESUME_PROMPT.replace("{text}", text)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    print("\n🔍 RESUME DEBUG")
    print("RAW:", repr(response[:200]))
    print("CLEANED:", repr(cleaned[:200]))

    return safe_json_parse(cleaned)


# -----------------------------
# EXTRA SKILL EXTRACTION (🔥 FIX)
# -----------------------------
def extract_skills_from_text(raw_text: str):
    """
    Deep skill extraction from full resume text
    """

    if not raw_text:
        return []

    prompt = SKILL_EXTRACTION_PROMPT.replace("{text}", raw_text)

    response = call_llm(prompt)
    cleaned = clean_llm_output(response)

    try:
        skills = json.loads(cleaned)

        return list(set([
            str(s).strip()
            for s in skills if s
        ]))

    except Exception as e:
        print("⚠️ Skill extraction failed:", e)
        return []