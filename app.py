import streamlit as st
from groq import Groq
import PyPDF2
from duckduckgo_search import DDGS
import random
import io
from streamlit_mic_recorder import mic_recorder # New Library

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Voice Coach", page_icon="🎙️", layout="centered")

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
        "started": False, "level": "Internship",
        "last_transcription": ""
    })

# --- HELPER: SPEECH TO TEXT (WHISPER) ---
def transcribe_audio(audio_bytes):
    try:
        client = Groq(api_key=api_key)
        # Convert bytes to a file-like object that Groq can read
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="text"
        )
        return transcription
    except Exception as e:
        return f"Error in transcription: {str(e)}"

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

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🎙️ Voice Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Voice Interview"):
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
    has_study = len(st.session_state.study_context) > 10
    has_resume = len(st.session_state.resume_context) > 10

    if c >= len(data):
        st.header("📊 Final Performance Report")
        for i, item in enumerate(data):
            with st.expander(f"Q{i+1}: {'✅' if item['a'] else '❌'}"):
                st.write(f"**Q:** {item['q']}")
                st.info(item['eval'] if item['a'] else "Skipped.")
        if st.button("🔄 New Session"):
            st.session_state.started = False
            st.rerun()
    else:
        # --- QUESTION GENERATION ---
        if data[c]["q"] is None:
            with st.spinner("🤖 Crafting question..."):
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                if use_resume and has_resume:
                    q_sys = f"You are a {st.session_state.level} interviewer. Ask a technical question based on a project in the RESUME. ONLY the question."
                    u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                else:
                    q_sys = f"You are a {st.session_state.level} interviewer. Ask a technical question based ONLY on the STUDY NOTES. NO preamble."
                    u_content = f"NOTES: {st.session_state.study_context}"

                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # --- VOICE ANSWER SECTION ---
        st.write("---")
        st.write("🗣️ **Answer with your Voice:**")
        
        # This creates the Record button
        audio = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="🛑 Stop Recording", key=f'recorder_{c}')
        
        if audio:
            with st.spinner("Transcribing your voice..."):
                transcript = transcribe_audio(audio['bytes'])
                if transcript:
                    data[c]["a"] = transcript # Put voice text into answer state

        # Text fallback/editor
        data[c]["a"] = st.text_area("Your Answer (Typed or Transcribed):", value=data[c]["a"], key=f"ans_{c}", height=150)

        # Controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next/Skip ➡️"):
                if data[c]["a"]:
                    e_sys = "Provide exactly 2 lines: Line 1 Score & Feedback. Line 2 Verified Ideal Answer."
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                    data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"): st.session_state.curr = len(data); st.rerun()

else:
    st.title("🎙️ AI Voice Interview Coach")
    st.write("Upload your PDFs and speak your way to a better career.")
