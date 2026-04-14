import pdfplumber
import fitz  # PyMuPDF
import os


# -----------------------------
# MAIN EXTRACTION FUNCTION
# -----------------------------
def extract_text(path: str) -> str:
    """
    Robust PDF text extraction with fallback + fault tolerance
    """

    # -----------------------------
    # 1. VALIDATION
    # -----------------------------
    if not path or not isinstance(path, str):
        print("❌ Invalid file path")
        return ""

    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return ""

    if not path.lower().endswith(".pdf"):
        print(f"❌ Unsupported file format: {path}")
        return ""

    # -----------------------------
    # 2. TRY pdfplumber
    # -----------------------------
    text, extracted_pages, total_pages = extract_with_pdfplumber(path)

    # -----------------------------
    # 3. FALLBACK → PyMuPDF
    # -----------------------------
    if should_fallback(text, extracted_pages, total_pages):
        print("🔄 Switching to PyMuPDF fallback...")
        text2 = extract_with_pymupdf(path)

        if len(text2.strip()) > len(text.strip()):
            text = text2
            print("✅ PyMuPDF extraction improved results")

    # -----------------------------
    # 4. FINAL VALIDATION
    # -----------------------------
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
                        clean = " ".join(page_text.split())
                        text_parts.append(clean)
                        extracted_pages += 1
                    else:
                        print(f"⚠️ pdfplumber: No text on page {i+1}")

                except Exception as e:
                    print(f"⚠️ pdfplumber page {i+1} failed: {e}")

    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}")

    return "\n\n".join(text_parts), extracted_pages, total_pages


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
                    clean = " ".join(page_text.split())
                    text_parts.append(clean)
                else:
                    print(f"⚠️ PyMuPDF: No text on page {i+1}")

            except Exception as e:
                print(f"⚠️ PyMuPDF page {i+1} failed: {e}")

    except Exception as e:
        print(f"⚠️ PyMuPDF failed: {e}")

    return "\n\n".join(text_parts)


# -----------------------------
# FALLBACK DECISION LOGIC
# -----------------------------
def should_fallback(text: str, extracted_pages: int, total_pages: int) -> bool:
    """
    Decide when to trigger fallback extraction
    """

    if not text.strip():
        return True

    # Low extraction coverage
    if total_pages > 0 and (extracted_pages / total_pages) < 0.5:
        return True

    # Very low text
    if len(text.strip()) < 500:
        return True

    return False


# -----------------------------
# SCANNED PDF DETECTION (OPTIONAL)
# -----------------------------
def is_scanned_pdf(text: str) -> bool:
    """
    Loose detection (DO NOT block pipeline)
    """
    return len(text.strip()) < 200