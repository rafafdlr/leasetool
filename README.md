# Lease Abstraction Tool

Upload a commercial lease PDF, get back a clean summary of key terms (rent, dates,
renewal options, CAM charges, red flags, etc.) powered by Kimi's API.

## Deploy this without running anything locally (Streamlit Community Cloud)

1. Go to https://github.com and create a free account if you don't have one.
2. Create a new repository (e.g. "lease-tool"). Make it Public or Private, either works.
3. Upload these two files into the repo: `app.py` and `requirements.txt`
   (GitHub lets you drag-and-drop files right in the browser — no git commands needed).
4. Go to https://streamlit.io/cloud and sign in with your GitHub account.
5. Click "New app", pick your `lease-tool` repo, branch `main`, and set the main
   file path to `app.py`.
6. Click "Deploy". Streamlit will install the requirements and give you a live URL
   (something like `yourname-lease-tool.streamlit.app`) that anyone can open in a browser.

## Using it

- Open your deployed app URL.
- Paste your Kimi API key into the sidebar (get one at platform.kimi.ai — it's
  never saved anywhere, just used for that session).
- Upload a lease PDF and click "Extract Lease Terms".
- Download the report when it's done.

## Notes

- The API key box is a password field and is only kept in memory for your
  session — it resets every time the page reloads. Nothing is stored on a server.
- If a lease is a scanned image (not real text), the tool automatically falls
  back to OCR to read it — just double-check numbers and dates in that case.
- To change what fields get extracted, edit the `FIELDS_PROMPT` variable near the
  top of `app.py`.
