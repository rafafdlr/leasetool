import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
import requests
import io

st.set_page_config(page_title="Lease with Ease", page_icon="📄", layout="centered")

# ---------- Secrets (hidden from users, set in Streamlit Cloud "Secrets") ----------
AI_API_KEY = st.secrets["AI_API_KEY"]
AI_BASE_URL = st.secrets.get("AI_BASE_URL", "https://api.moonshot.ai/v1")
AI_MODEL = st.secrets.get("AI_MODEL", "kimi-k3")

TEST_PASSWORD = st.secrets.get("TEST_PASSWORD", "testcode123")

FIELDS_PROMPT = """You are a commercial real estate analyst. Read the following commercial lease document and extract the key terms into a structured, clean report.

Extract these fields (mark as "Not specified" if not found in the document):

1. **Parties**
   - Landlord name
   - Tenant name

2. **Property**
   - Property address / premises description
   - Square footage (if stated)

3. **Lease Term**
   - Commencement date
   - Expiration date
   - Term length
   - Any renewal options (number of options, length of each, notice required)

4. **Rent**
   - Base rent amount
   - Rent escalation schedule (e.g., annual % increase, fixed steps)
   - Any percentage rent (for retail)

5. **Additional Charges**
   - CAM (Common Area Maintenance) charges and how they're calculated
   - Property tax and insurance responsibility (who pays)
   - Utilities responsibility

6. **Security & Deposits**
   - Security deposit amount
   - Conditions for return

7. **Use & Restrictions**
   - Permitted use of the property
   - Exclusivity clauses (if any)
   - Assignment / subletting rights

8. **Termination & Risk**
   - Early termination rights
   - Default provisions
   - Any co-tenancy or kick-out clauses

9. **Red Flags**
   - List anything unusual, ambiguous, or that a broker/property manager should double-check with the client (e.g., unusual escalation formulas, missing standard clauses, one-sided termination rights)

Format your response in clean markdown with clear headers matching the sections above. Be precise — if a term isn't in the document, say "Not specified" rather than guessing.

LEASE DOCUMENT TEXT:
---
{lease_text}
---
"""


def check_and_use_code(code: str):
    """TEMPORARY: simple password check while Airtable is being fixed.
    Not truly one-time-use yet -- just unblocks testing the core tool."""
    code = code.strip()
    if not code:
        return False, "Please enter an access code."
    if code == TEST_PASSWORD:
        return True, "Code accepted."
    return False, "That code isn't valid. Please check and try again."


def extract_pdf_text(uploaded_file):
    """Try normal text extraction first; fall back to OCR for scanned PDFs."""
    file_bytes = uploaded_file.read()

    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(text_parts)

    if len(text.strip()) >= 50:
        return text, False

    images = convert_from_bytes(file_bytes)
    ocr_parts = [pytesseract.image_to_string(img) for img in images]
    return "\n".join(ocr_parts), True


def analyze_lease(lease_text: str) -> str:
    client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
    prompt = FIELDS_PROMPT.format(lease_text=lease_text[:400000])
   response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise, detail-oriented commercial real estate analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


# ---------- App state ----------
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

st.title("📄 Lease with Ease")
st.write("Upload a commercial lease and get a clean summary of the key terms in minutes.")

# ---------- Access gate ----------
if not st.session_state.unlocked:
    st.subheader("Enter your access code")
    code_input = st.text_input("Access code", placeholder="e.g. ABCD1234")
    if st.button("Unlock", type="primary"):
        success, message = check_and_use_code(code_input)
        if success:
            st.session_state.unlocked = True
            st.rerun()
        else:
            st.error(message)
    st.caption("Don't have a code? Contact us to purchase one.")

# ---------- Main tool (only visible after a valid code) ----------
else:
    uploaded_file = st.file_uploader("Upload lease PDF", type=["pdf"])

    if uploaded_file is not None:
        if st.button("Analyze Lease", type="primary"):
            with st.spinner("Reading document..."):
                try:
                    lease_text, used_ocr = extract_pdf_text(uploaded_file)
                except Exception as e:
                    st.error(f"Couldn't read the PDF: {e}")
                    st.stop()

            if used_ocr:
                st.info("This looked like a scanned document — text was read using OCR. Please double-check numbers and dates.")

            if len(lease_text.strip()) < 50:
                st.error("Couldn't extract readable text from this PDF, even with OCR. Try a clearer copy.")
                st.stop()

            with st.spinner("Analyzing lease... this can take 30-90 seconds for long documents."):
                try:
                    report = analyze_lease(lease_text)
                except Exception as e:
                    st.error(f"Something went wrong during analysis: {e}")
                    st.stop()

            st.success("Done!")
            st.markdown("---")
            st.markdown(report)

            st.download_button(
                label="Download Report",
                data=report,
                file_name=f"lease_summary_{uploaded_file.name.rsplit('.', 1)[0]}.md",
                mime="text/markdown",
            )
    else:
        st.info("Upload a lease PDF to get started.")
