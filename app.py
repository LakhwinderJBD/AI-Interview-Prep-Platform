import streamlit as st
from groq import Groq
import PyPDF2
import random
import io
import os
import re
import pandas as pd
import plotly.express as px
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
        "level": "Internship"
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
    except Exception as e:
        return f"Transcription Error: {str(e)}"

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
    has_resume = len(st.session_state.resume_context) > 10

    # --- PHASE A: FINAL REPORT ---
    if c >= len(data):
        st.header("📊 Performance Dashboard")
        
        # 1. Horizontal Bar Chart (The easier matrix)
        st.subheader("Skill Proficiency Breakdown")
        with st.spinner("Calculating metrics..."):
            summary_prompt = f"Analyze these results: {str(data)}. Output ONLY 4 numbers (1-10) separated by commas for: Technical, Communication, Confidence, Logic."
            res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":summary_prompt}])
            try:
                scores = [int(s.strip()) for s in res.choices[0].message.content.split(",")]
            except:
                scores = [7, 7, 7, 7]
            
            df_plot = pd.DataFrame({
                "Skill Area": ['Technical', 'Communication', 'Confidence', 'Logic'],
                "Score": scores
            })
            # Horizontal Bar Chart
            fig = px.bar(df_plot, x='Score', y='Skill Area', orientation='h', color='Score', 
                         color_continuous_scale='RdYlGn', range_x=[0,10])
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        # 2. Results List
        for i, item in enumerate(data):
            if item["q"]:
                with st.expander(f"Q{i+1}: {item['q'][:50]}..."):
                    st.write(f"**Full Question:** {item['q']}")
                    if item['a']:
                        st.write(f"**Your Answer:** {item['a']}")
                        st.info(item['eval'])
                    else:
                        st.warning("Skipped.")
                        res_sol = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"2-line answer for: {item['q']}"}])
                        st.success(f"**Expert Solution:** {res_sol.choices[0].message.content}")

        # 3. Supabase Review
        st.subheader("🌟 Permanent Review")
        with st.form("db_feedback"):
            u_rating = st.select_slider("Rate Experience (1-5)", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Notes for Developer:")
            if st.form_submit_button("Submit to Cloud"):
                if supabase_client:
                    supabase_client.table("reviews").insert({"level": st.session_state.level, "rating": u_rating, "comment": u_comments}).execute()
                    st.success("Saved to Cloud!")

        if st.button("🔄 Restart"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking..."):
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                q_sys = f"You are a {st.session_state.level} interviewer. Ask ONE tech question from text. No preamble."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # --- VOICE FIX: Sync with Session State ---
        audio = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop & Transcribe", key=f'mic_{c}')
        
        if audio and "last_mic" not in st.session_state:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio['bytes'])
                data[c]["a"] = transcript # Update answer logic
                st.session_state[f"ans_input_{c}"] = transcript # Update text area value
                st.rerun()

        # Text Input
        ans_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_input_{c}", height=150)
        data[c]["a"] = ans_input # Keep sync

        # Navigation
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                res_h = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word hint for: {data[c]['q']}"}])
                data[c]["hint"] = res_h.choices[0].message.content; st.rerun()
        with col3:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        e_sys = "Score 1-10 & Feedback + Ideal Answer. 2 lines total."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master")
    st.write("Upload your Resume and Notes in the sidebar to begin.")
