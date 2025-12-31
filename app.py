import streamlit as st
from groq import Groq
import PyPDF2
import random
import io
import os
import re
from streamlit_mic_recorder import mic_recorder
from supabase import create_client, Client
from fpdf import FPDF

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Career Master Pro", page_icon="🎙️", layout="centered")

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
        "processed_audio_id": None  # Key fix for Voice logic
    })

# --- 4. HELPER FUNCTIONS ---

def generate_pdf_report(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Interview Performance Report", ln=True, align='C')
    pdf.ln(10)
    for i, item in enumerate(data):
        if item["q"]:
            pdf.set_font("Arial", "B", 12)
            pdf.multi_cell(0, 10, txt=f"Q{i+1}: {item['q']}")
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 10, txt=f"Your Answer: {item['a'] if item['a'] else 'Skipped'}")
            if item['eval']:
                pdf.set_text_color(0, 50, 150)
                pdf.multi_cell(0, 10, txt=f"Feedback: {item['eval']}")
                pdf.set_text_color(0, 0, 0)
            pdf.ln(5)
            pdf.cell(0, 0, "", "T")
            pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

def transcribe_audio(audio_bytes):
    try:
        client = Groq(api_key=api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        res = client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", response_format="text")
        return res
    except:
        return ""

def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv"]):
            r_text += text
        else:
            s_text += text
    return s_text[:15000], r_text[:5000]

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

    # --- PHASE A: FINAL REPORT & DOWNLOAD ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        
        pdf_data = generate_pdf_report(data)
        st.download_button(label="📥 Download Results as PDF", data=pdf_data, file_name="Interview_Report.pdf", mime="application/pdf")
        st.divider()
        
        for i, item in enumerate(data):
            if item["q"]:
                with st.expander(f"Question {i+1}"):
                    st.write(f"**Q:** {item['q']}")
                    if item['a']:
                        if not item['eval']:
                            res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Score 1-10 & Feedback: Q: {item['q']} A: {item['a']}"}])
                            item['eval'] = res_e.choices[0].message.content
                        st.info(item['eval'])
                    else:
                        st.warning("Skipped.")

        # --- REVIEWS & SUPABASE ---
        st.subheader("🌟 Submit Feedback")
        with st.form("feedback_form"):
            u_rating = st.select_slider("Rate AI Accuracy", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Your Review:")
            if st.form_submit_button("Submit to Cloud"):
                if supabase_client:
                    try:
                        # Extract average score
                        scores = re.findall(r'\b([1-9]|10)\b', str(data))
                        avg = sum([int(s) for s in scores]) / len(scores) if scores else 0
                        
                        supabase_client.table("reviews").insert({
                            "level": st.session_state.level, 
                            "rating": u_rating, 
                            "comment": u_comments,
                            "avg_score": avg
                        }).execute()
                        st.success("✅ Saved to Database!")
                    except Exception as e:
                        st.error(f"Database error: {e}")
                else:
                    st.warning("Database not connected.")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking..."):
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                q_sys = f"You are an expert {st.session_state.level} level interviewer. Ask ONE specific question based on the text. NO preamble."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # --- 🎤 VOICE LOGIC FIX ---
        st.write("🗣️ **Speak Answer:**")
        audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="🛑 Stop & Transcribe", key=f'mic_{c}')
        
        if audio_data and st.session_state.processed_audio_id != audio_data['id']:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_data['bytes'])
                if len(transcript.strip()) < 5:
                    st.warning("⚠️ Speak louder and clearer!")
                else:
                    data[c]["a"] = transcript
                    st.session_state.processed_audio_id = audio_data['id']
                    st.rerun()

        # Text Area bound to session data
        ans_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_box_{c}", height=150)
        data[c]["a"] = ans_input

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                res_h = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word hint for: {data[c]['q']}"}])
                data[c]["hint"] = res_h.choices[0].message.content; st.rerun()
        with col3:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Analyzing..."):
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}. Give 2-line score and feedback."}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                # Evaluate last question
                if data[c]["a"] and not data[c]["eval"]:
                    res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}"}])
                    data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master Pro")
    st.write("Professional Interview Platform. Upload materials and start.")
