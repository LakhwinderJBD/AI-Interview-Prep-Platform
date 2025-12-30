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
st.set_page_config(page_title="AI Career Architect", page_icon="🏛️", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .report-card { background-color: #f9f9f9; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & API INITIALIZATION ---
# Initialize Supabase
supabase_client = None
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        supabase_client: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.sidebar.warning("Cloud Database not linked. Reviews won't be saved permanently.")

# Initialize Groq API Key
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
        return f"Error: {str(e)}"

def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = f"\n--- Source: {file.name} ---\n" + "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv", "portfolio"]):
            r_text += text
        else:
            s_text += text
    return s_text[:10000], r_text[:5000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ System Setup")
    if api_key:
        st.success("✅ API Key Active")
    
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Number of Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Personalized Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing materials..."):
                study, resume = process_any_files(all_files)
                st.session_state.update({
                    "study_context": study, 
                    "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)],
                    "curr": 0, 
                    "level": level, 
                    "started": True
                })
                st.rerun()
        else:
            st.error("Please provide API Key and upload documents.")

# --- 6. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    has_resume = len(st.session_state.resume_context) > 10

    # --- PHASE A: FINAL REPORT & ANALYTICS ---
    if c >= len(data):
        st.header("📊 Final Master Analytics")
        
        # 1. Skill Radar Chart
        st.subheader("Your Skill Spider-Map")
        with st.spinner("Analyzing skill metrics..."):
            summary_prompt = f"Analyze these interview results: {str(data)}. Output ONLY 4 numbers (1-10) separated by commas for: Technical Knowledge, Communication, Confidence, and Problem Solving logic."
            res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":summary_prompt}])
            try:
                scores = [int(s.strip()) for s in res.choices[0].message.content.split(",")]
            except:
                scores = [7, 7, 7, 7]
            
            df_plot = pd.DataFrame(dict(r=scores, theta=['Technical', 'Communication', 'Confidence', 'Logic']))
            fig = px.line_polar(df_plot, r='r', theta='theta', line_close=True)
            fig.update_traces(fill='toself', line_color='#FF4B4B')
            st.plotly_chart(fig)

        st.divider()
        
        # 2. Question Breakdown
        for i, item in enumerate(data):
            if item["q"] is None: continue
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}"):
                st.write(f"**Q:** {item['q']}")
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    if not item['eval']:
                        eval_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Score this 1-10 and feedback for Q: {item['q']} A: {item['a']}"}])
                        item['eval'] = eval_res.choices[0].message.content
                    st.info(item['eval'])
                else:
                    st.warning("Skipped.")
                    res_sol = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"Provide exactly 2 lines for the ideal answer to: {item['q']}"}])
                    st.success(f"**Ideal Answer:**\n{res_sol.choices[0].message.content}")

        st.divider()

        # 3. PERMANENT REVIEW SYSTEM
        st.subheader("🌟 Permanent User Review")
        with st.form("database_feedback"):
            u_rating = st.select_slider("Rate AI Accuracy (1-5)", options=[1, 2, 3, 4, 5], value=5)
            u_comments = st.text_area("Developer Note: What should I improve?")
            if st.form_submit_button("Send to Cloud Database"):
                if supabase_client:
                    try:
                        # Simple extraction of score for average
                        nums = re.findall(r'\d+', str(data))
                        session_avg = sum([int(n) for n in nums[:len(data)]]) / len(data) if nums else 0
                        
                        supabase_client.table("reviews").insert({
                            "level": st.session_state.level,
                            "rating": u_rating,
                            "comment": u_comments,
                            "avg_score": session_avg
                        }).execute()
                        st.success("Review saved permanently in the cloud!")
                    except Exception as e:
                        st.error(f"Database Error: {e}")
                else:
                    st.error("Database not connected. Please check your secrets.")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 AI is thinking..."):
                asked = [item["q"] for item in data if item["q"]]
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                
                if use_resume and has_resume:
                    q_sys = f"You are a {st.session_state.level} level interviewer. Ask ONE technical question based on a project in the Resume. Do not repeat: {asked}. Output ONLY the question text."
                    u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                else:
                    q_sys = f"You are a technical interviewer. Ask ONE specific question based ONLY on the study material. Do not repeat: {asked}. NO preamble. ONLY question text."
                    u_content = f"NOTES: {st.session_state.study_context}"

                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # Voice Input
        audio = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop & Transcribe", key=f'v_{c}')
        if audio:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio['bytes'])
                data[c]["a"] = transcript

        # Text Input
        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}", height=120)

        # BUTTONS
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1
                st.rerun()
        with col2:
            if st.button("💡 Hint"):
                res_h = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word technical hint for: {data[c]['q']}"}])
                data[c]["hint"] = res_h.choices[0].message.content
                st.rerun()
        with col3:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking answer..."):
                        e_sys = "Exactly 2 lines. Line 1: Score 1-10 & Feedback. Line 2: Ideal Answer."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1
                st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                if data[c]["a"] and not data[c]["eval"]:
                    res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n2-line feedback."}])
                    data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr = len(data)
                st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master")
    st.write("Professional Interview Platform. Upload your Resume and Study Materials to start.")
    st.info("Upload multiple PDFs (Notes, Resume, CV) in the sidebar to begin.")
