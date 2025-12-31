# --- IMPROVED DOCUMENT PROCESSOR FOR MOBILE ---
def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        try:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            
            # Check if text was actually extracted (Mobile Scan Check)
            if len(text.strip()) < 10:
                st.sidebar.error(f"⚠️ {file.name} looks like a scan/image. Please upload a digital PDF with selectable text.")
                continue

            if any(word in file.name.lower() for word in ["resume", "cv"]):
                r_text += f"\n--- Resume Source: {file.name} ---\n" + text
            else:
                s_text += f"\n--- Study Source: {file.name} ---\n" + text
        except Exception as e:
            st.sidebar.error(f"Error reading {file.name}: {str(e)}")
            
    return s_text[:15000], r_text[:5000]

# --- UPDATED START BUTTON LOGIC ---
if st.button("🚀 Start Interview"):
    if api_key and all_files:
        with st.spinner("Preparing for mobile/desktop..."):
            study, resume = process_any_files(all_files)
            
            # Only start if we successfully got text
            if len(study) > 20 or len(resume) > 20:
                st.session_state.update({
                    "study_context": study, "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)],
                    "curr": 0, "level": level, "started": True
                })
                st.rerun()
            else:
                st.error("Could not read any text from the uploaded PDFs. If you scanned them with a camera, this app cannot read them.")

