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
        "level": "Internship",
        "processed_audio": None  # New flag to prevent infinite transcribing
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
        return "" # Return empty on error to trigger "Speak Louder" logic

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

    # --- PHASE A: FINAL REPORT ---
    if c >= len(data):
        st.header("📊 Performance Dashboard")
        
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
            # Horizontal Bar Chart - Easier to explain!
            fig = px.bar(df_plot, x='Score', y='Skill Area', orientation='h', color='Score', 
                         color_continuous_scale='RdYlGn', range_x=[0,10])
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        for i, item in enumerate(data):
            if item["q"]:
                with st.expander(f"Q{i+1}: {item['q'][:60]}..."):
                    st.write(f"**Question:** {item['q']}")
                    if item['a']:
                        st.write(f"**Your Answer:** {item['a']}")
                        st.info(item['eval'])
                    else:
                        st.warning("Skipped.")
                        res_sol = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"2-line answer for: {item['q']}"}])
                        st.success(f"**Expert Solution:** {res_sol.choices[0].message.content}")

        if st.button("🔄 Restart"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking..."):
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                q_sys = f"You are a {st.session_state.level} interviewer. Ask ONE tech question. No preamble."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # --- VOICE LOGIC (IMPROVED) ---
        audio_data = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop & Transcribe", key=f'mic_{c}')
        
        # Check if new audio was just recorded
        if audio_data and st.session_state.processed_audio != audio_data['id']:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_data['bytes'])
                
                # Validation Logic: If too short, ask to speak again
                if len(transcript.strip()) < 5:
                    st.error("⚠️ Speak louder and clearer! The AI couldn't hear you.")
                else:
                    data[c]["a"] = transcript
                    st.session_state.processed_audio = audio_data['id'] # Mark this ID as done
                    st.rerun()

        # Text Area synced to transcript
        ans_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_input_{c}", height=120)
        data[c]["a"] = ans_input

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                res_h = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word technical hint for: {data[c]['q']}"}])
                data[c]["hint"] = res_h.choices[0].message.content; st.rerun()
        with col3:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Analyzing..."):
                        e_sys = "Exactly 2 lines. Line 1: Score 1-10 & Feedback. Line 2: Ideal Answer."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master")
    st.write("Professional Interview Platform. Upload your Resume and Notes to start.")
