import streamlit as st
from groq import Groq
import PyPDF2
import random
import io
from streamlit_mic_recorder import mic_recorder

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Career Master", page_icon="🎙️", layout="centered")

# --- 2. API KEY HANDLING ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

# --- 3. SESSION STATE ---
if "started" not in st.session_state:
    st.session_state.update({
        "curr": 0, "session_data": [],
        "study_context": "", "resume_context": "",
        "started": False, "level": "Internship"
    })

# --- HELPER: SPEECH TO TEXT (WHISPER) ---
def transcribe_audio(audio_bytes):
    try:
        client = Groq(api_key=api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="text"
        )
        return transcription
    except Exception as e:
        return f"Transcription Error: {str(e)}"

# --- DOCUMENT PROCESSOR ---
def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = f"\n--- Source: {file.name} ---\n" + "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv", "portfolio"]):
            r_text += text
        else: s_text += text
    return s_text[:10000], r_text[:5000]

# --- 4. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ Setup")
    if "GROQ_API_KEY" in st.secrets: st.success("✅ API Key Active")
    
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Interview"):
        if api_key and all_files:
            study, resume = process_any_files(all_files)
            st.session_state.update({
                "study_context": study, "resume_context": resume,
                "session_data": [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)],
                "curr": 0, "level": level, "started": True
            })
            st.rerun()

# --- 5. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    has_resume = len(st.session_state.resume_context) > 10

    # --- PHASE A: FINAL PERFORMANCE REPORT ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.divider()

        for i, item in enumerate(data):
            # FIX: Only show questions that were actually generated
            if item["q"] is None:
                continue

            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.write(f"**Q:** {item['q']}")
                
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    # Generate evaluation if missing (clicked finish early)
                    if not item['eval']:
                        with st.spinner("Scoring..."):
                            e_sys = "Score 1-10 and 1-sentence feedback. Then 1-sentence ideal answer. Total 2 lines."
                            res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {item['q']} A: {item['a']}\n{e_sys}"}])
                            item['eval'] = res.choices[0].message.content
                    st.info(item['eval'])
                else:
                    # FIX: Generate REAL Expert Answer for skips (NOT standard verification)
                    st.warning("Skipped.")
                    with st.spinner("Generating expert solution..."):
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Provide exactly 2 lines for the ideal answer to: {item['q']}. Line 1: Summary. Line 2: Technical detail."}]
                        )
                        st.success(f"**Ideal Answer:**\n{res.choices[0].message.content}")
        
        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        # 1. QUESTION GENERATION (ADAPTIVE & UNIQUE)
        if data[c]["q"] is None:
            with st.spinner("🤖 Crafting question..."):
                asked = [item["q"] for item in data if item["q"]]
                
                # Industry Weighting: Job (70% Resume), Internship (30% Resume)
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                
                if use_resume and has_resume:
                    q_sys = f"You are a {st.session_state.level} interviewer. Ask ONE technical question based on a project in the Resume. Do not repeat: {asked}. Output ONLY the question."
                    u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                else:
                    q_sys = f"You are a technical interviewer. Ask ONE specific question based ONLY on the study material. Do not repeat: {asked}. NO preamble."
                    u_content = f"NOTES: {st.session_state.study_context}"

                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # VOICE OPTION
        audio = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop", key=f'v_{c}')
        if audio:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio['bytes'])
                data[c]["a"] = transcript

        # TEXT BOX
        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}", height=100)

        # BUTTONS
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Back") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                with st.spinner(""):
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word hint for: {data[c]['q']}"}])
                    data[c]["hint"] = res.choices[0].message.content
                st.rerun()
        with col3:
            btn_lbl = "Next ➡️" if data[c]["a"] else "Skip ⏩"
            if st.button(btn_lbl):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        e_sys = "Exactly 2 lines. Line 1: Score 1-10 & Feedback. Line 2: Ideal Answer."
                        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                if data[c]["a"] and not data[c]["eval"]:
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n2-line feedback."}])
                    data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Interview Coach")
    st.write("Voice, Resume, and Multi-Doc supported. Upload your materials to begin.")
