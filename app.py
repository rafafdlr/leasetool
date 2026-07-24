import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
import io
import json

st.set_page_config(page_title="Lease Abstraction Tool", page_icon="📄", layout="wide")

# ---------- Sidebar: API key ----------
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input(
        "Kimi API Key",
        type="password",
        help="Get this from platform.kimi.ai → Console → API Keys. "
             "It's only stored for this session and never saved anywhere.",
    )
    model = st.selectbox(
        "Model",
        options=["kimi-k3", "kimi-k2.7-code", "kimi-k2.6"],
        index=0,
        help="kimi-k3 is the most capable (best for catching tricky clauses). "
             "kimi-k2.7-code is cheaper and faster for routine leases.",
    )
    st.markdown("---")
    st.caption(
        "This tool sends the lease text to Kimi's API for analysis. "
        "Don't upload documents with information you're not allowed to share externally."
    )

st.title("📄 Commercial Lease Abstraction Tool")
st.write(
    "Upload a commercial lease PDF and get back a clean summary of the key terms — "
    "rent, dates, options, and anything that needs a second look."
)

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


def extract_pdf_text(uploaded_file) -> str:
    """Try normal text extraction first. If that returns almost nothing
    (i.e. the PDF is a scanned image), fall back to OCR."""
    file_bytes = uploaded_file.read()

    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts)

    if len(text.strip()) >= 50:
        return text, False  # normal text extraction worked

    # Fallback: OCR the pages as images
    images = convert_from_bytes(file_bytes)
    ocr_parts = []
    for img in images:
        ocr_parts.append(pytesseract.image_to_string(img))
    return "\n".join(ocr_parts), True  # OCR was used


def call_kimi(api_key: str, model: str, lease_text: str) -> str:
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.ai/v1")
    prompt = FIELDS_PROMPT.format(lease_text=lease_text[:400000])  # generous cap for long leases
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise, detail-oriented commercial real estate analyst."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content


# ---------- Main flow ----------
uploaded_file = st.file_uploader("Upload lease PDF", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.warning("Enter your Kimi API key in the sidebar to run the analysis.")
    else:
        if st.button("Extract Lease Terms", type="primary"):
            with st.spinner("Reading document..."):
                try:
                    lease_text, used_ocr = extract_pdf_text(uploaded_file)
                except Exception as e:
                    st.error(f"Couldn't read the PDF: {e}")
                    st.stop()

            if used_ocr:
                st.info("This looked like a scanned document, so OCR was used to read it. Double-check numbers and dates carefully — OCR can occasionally misread characters.")

            if len(lease_text.strip()) < 50:
                st.error(
                    "Couldn't extract readable text from this PDF, even with OCR. "
                    "The scan quality may be too low — try a clearer copy."
                )
                st.stop()

            with st.spinner(f"Analyzing lease with {model}... this can take 30-90 seconds for long leases."):
                try:
                    report = call_kimi(api_key, model, lease_text)
                except Exception as e:
                    st.error(f"API call failed: {e}")
                    st.stop()

            st.success("Done!")
            st.markdown("---")
            st.markdown(report)

            st.download_button(
                label="Download Report (Markdown)",
                data=report,
                file_name=f"lease_abstract_{uploaded_file.name.rsplit('.', 1)[0]}.md",
                mime="text/markdown",
            )
else:
    st.info("Upload a lease PDF to get started.")
