import streamlit as st
from groq import Groq
import PyPDF2
import random
import io
import os
import re
from streamlit_mic_recorder import mic_recorder
from supabase import create_client, Client
from fpdf import FPDF # modern fpdf2 library

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
    except: pass

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
        "last_audio_id": None
    })

# --- 4. HELPER FUNCTIONS ---

def clean_for_pdf(text):
    """Replaces Unicode characters that break standard PDF fonts."""
    if not text: return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2026': '...'
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    # Remove emojis or other characters that can't be encoded in Latin-1
    return text.encode('latin-1', 'ignore').decode('latin-1')

def generate_pdf_report(data):
    # fpdf2 is used here
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, txt="Interview Performance Report", ln=True, align='C')
    pdf.ln(10)
    
    for i, item in enumerate(data):
        if item["q"]:
            pdf.set_font("helvetica", "B", 12)
            pdf.multi_cell(0, 10, txt=clean_for_pdf(f"Question {i+1}: {item['q']}"))
            
            pdf.set_font("helvetica", "", 11)
            ans = item['a'] if item['a'] else "Skipped"
            pdf.multi_cell(0, 8, txt=clean_for_pdf(f"Your Answer: {ans}"))
            
            if item['eval']:
                pdf.set_text_color(0, 50, 150)
                pdf.multi_cell(0, 8, txt=clean_for_pdf(f"AI Feedback: {item['eval']}"))
                pdf.set_text_color(0, 0, 0)
            
            pdf.ln(5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
    return pdf.output() # In fpdf2, output() returns bytes by default for streaming

def transcribe_audio(audio_bytes):
    try:
        client = Groq(api_key=api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        res = client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", response_format="text")
        return res
    except: return ""

def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            text = "".join([p.extract_text() for p in pdf_reader.pages])
            if any(word in file.name.lower() for word in ["resume", "cv"]):
                r_text += f"\n[Resume: {file.name}]\n{text}"
            else:
                s_text += f"\n[Study: {file.name}]\n{text}"
        except: st.sidebar.error(f"Error reading {file.name}")
    return s_text[:12000], r_text[:4000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Number of Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Interview"):
        if api_key and all_files:
            with st.spinner("Preparing materials..."):
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

    if c >= len(data):
        st.header("📊 Final Performance Report")
        
        # DOWNLOAD SECTION
        try:
            pdf_output = generate_pdf_report(data)
            st.download_button(
                label="📥 Download Report as PDF",
                data=pdf_output,
                file_name="Interview_Results.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Could not generate PDF: {e}")

        st.divider()
        
        for i, item in enumerate(data):
            if item["q"]:
                with st.expander(f"Question {i+1}"):
                    st.write(f"**Q:** {item['q']}")
                    if item['a']:
                        if not item['eval']:
                            res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"2-line feedback for Q: {item['q']} A: {item['a']}"}])
                            item['eval'] = res_e.choices[0].message.content
                        st.info(item['eval'])
                    else:
                        st.warning("Skipped.")

        with st.form("feedback_form"):
            u_rating = st.select_slider("Rate AI", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Feedback?")
            if st.form_submit_button("Submit to Cloud"):
                if supabase_client:
                    supabase_client.table("reviews").insert({"level": st.session_state.level, "rating": u_rating, "comment": u_comments}).execute()
                    st.success("✅ Saved!")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking..."):
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                q_sys = f"You are a expert interviewer. Ask ONE {st.session_state.level} level question. No preamble."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.subheader(data[c]["q"])

        # VOICE LOGIC
        audio_data = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop & Transcribe", key=f'mic_{c}')
        if audio_data and st.session_state.last_audio_id != audio_data['id']:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_data['bytes'])
                if transcript.strip():
                    data[c]["a"] = transcript
                    st.session_state[f"ans_input_{c}"] = transcript 
                    st.session_state.last_audio_id = audio_data['id']
                    st.rerun()

        # Text Area synced to Voice
        ans_key = f"ans_input_{c}"
        if ans_key not in st.session_state:
            st.session_state[ans_key] = data[c]["a"]

        user_input = st.text_area("Your Answer:", value=st.session_state[ans_key], key=f"widget_{c}", height=150)
        data[c]["a"] = user_input
        st.session_state[ans_key] = user_input

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
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master Pro")
    st.write("Professional Interview Platform. Voice, Mobile PDFs, and Resume context supported.")
