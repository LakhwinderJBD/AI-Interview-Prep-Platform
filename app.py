import streamlit as st
from groq import Groq
import PyPDF2
import random
import io
import os
import re
import pandas as pd
from streamlit_mic_recorder import mic_recorder
from supabase import create_client, Client

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Career Master", page_icon="🎙️", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .report-card { background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & API INITIALIZATION ---
supabase_client = None
if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    try:
        supabase_client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        pass

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

# --- 3. SESSION STATE ---
if "started" not in st.session_state:
    st.session_state.update({
        "curr": 0, 
        "session_data": [],
        "study_context": "", 
        "resume_context": "",
        "started": False, 
        "level": "Internship",
        "last_audio_id": None # Track specific recording to avoid infinite loops
    })

# --- 4. HELPER FUNCTIONS ---
def transcribe_audio(audio_bytes):
    try:
        client = Groq(api_key=api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        res = client.audio.transcriptions.create(
            file=audio_file, model="whisper-large-v3", response_format="text"
        )
        return res
    except Exception:
        return ""

def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = f"\n--- Source: {file.name} ---\n" + "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv"]):
            r_text += text
        else:
            s_text += text
    return s_text[:10000], r_text[:5000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Number of Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Interview"):
        if api_key and all_files:
            with st.spinner("Preparing..."):
                study, resume = process_any_files(all_files)
                st.session_state.update({
                    "study_context": study, "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)],
                    "curr": 0, "level": level, "started": True
                })
                st.rerun()

# --- 6. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data

    # --- PHASE A: FINAL REPORT & REVIEWS ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.write("Summary of your session:")
        st.divider()
        
        # Display Results
        for i, item in enumerate(data):
            if item["q"]:
                with st.expander(f"Question {i+1} | {'✅ Answered' if item['a'] else '❌ Skipped'}"):
                    st.write(f"**Question:** {item['q']}")
                    if item['a']:
                        if not item['eval']:
                            res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Score 1-10 & Feedback: Q: {item['q']} A: {item['a']}"}])
                            item['eval'] = res_e.choices[0].message.content
                        st.info(item['eval'])
                    else:
                        st.warning("Question was skipped.")
                        res_sol = client.chat.get_completions = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"2-line answer for: {item['q']}"}])
                        st.success(f"**Ideal Answer:** {res_sol.choices[0].message.content}")

        st.divider()

        # --- UPDATED REVIEW SYSTEM (Supabase) ---
        st.subheader("🌟 User Experience Review")
        with st.form("feedback_form"):
            u_rating = st.select_slider("Rate AI Performance (1-5)", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Feedback?")
            if st.form_submit_button("Submit to Cloud Database"):
                if supabase_client:
                    try:
                        # Extract digits to calculate an average score from evaluation text
                        all_scores = re.findall(r'\b([1-9]|10)\b', str(data))
                        avg_val = sum([int(s) for s in all_scores]) / len(all_scores) if all_scores else 0
                        
                        supabase_client.table("reviews").insert({
                            "level": st.session_state.level, 
                            "rating": u_rating, 
                            "comment": u_comments,
                            "avg_score": avg_val
                        }).execute()
                        st.success("✅ Review saved permanently in Supabase cloud!")
                    except Exception as e:
                        st.error(f"Database error: {e}")
                else:
                    st.warning("Supabase not connected. Check your Secrets.")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking..."):
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                q_sys = f"You are a {st.session_state.level} level interviewer. Ask ONE tech question from text. No preamble."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # --- FIXED VOICE LOGIC ---
        audio_data = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop & Transcribe", key=f'mic_{c}')
        
        if audio_data and st.session_state.last_audio_id != audio_data['id']:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_data['bytes'])
                if len(transcript.strip()) < 5:
                    st.warning("⚠️ Speak louder and clearer, I couldn't understand that!")
                else:
                    data[c]["a"] = transcript
                    st.session_state.last_audio_id = audio_data['id']
                    st.rerun()

        # Input Area
        ans_box = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_input_{c}", height=150)
        data[c]["a"] = ans_box

        # --- NAVIGATION ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                res_h = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word hint for: {data[c]['q']}"}])
                data[c]["hint"] = res_h.choices[0].message.content; st.rerun()
        with col3:
            # Combined Next Logic
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Analyzing..."):
                        e_sys = "Exactly 2 lines. Score 1-10 & Feedback + Ideal Answer."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                # Evaluate last question before finishing
                if data[c]["a"] and not data[c]["eval"]:
                    res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}"}])
                    data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master")
    st.write("Voice, Resume, and Multi-Doc supported. Practice smarter.")
