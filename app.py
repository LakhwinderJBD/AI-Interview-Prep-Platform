import streamlit as st
from groq import Groq
import PyPDF2
import random
import time
import re
from supabase import create_client, Client

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Career Master", page_icon="🎯", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #FF4B4B; color: white; }
    .report-card { background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 15px; }
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
        "started": False, "level": "Internship"
    })

# --- 4. API HELPER WITH DYNAMIC TEMPERATURE ---
def safe_groq_call(system_prompt, user_prompt, temp=0.1):
    client = Groq(api_key=api_key)
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                temperature=temp
            )
            return res.choices[0].message.content
        except Exception as e:
            if "429" in str(e): time.sleep(3)
            else: return f"AI Error: {str(e)}"
    return "API Busy."

def process_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv"]): r_text += text
        else: s_text += text
    return s_text[:7000], r_text[:3000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ Setup")
    level = st.selectbox("Preparation Level", ["Internship", "Job"])
    num_q = st.number_input("Questions to practice", min_value=1, max_value=20, value=5)
    all_files = st.file_uploader("Upload PDF (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing materials..."):
                study, resume = process_files(all_files)
                st.session_state.update({
                    "study_context": study, "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "eval": None, "ideal": None, "hint": None} for _ in range(num_q)],
                    "curr": 0, "level": level, "started": True
                })
                st.rerun()

# --- 6. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    lvl = st.session_state.level

    # --- PHASE A: FINAL REPORT ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        for i, item in enumerate(data):
            if item["q"] is None: continue 
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.markdown(f"**Question:** {item['q']}")
                st.write(f"**Your Answer:** {item['a'] if item['a'] else 'No answer provided.'}")
                if item['a'] and not item['eval']:
                    item['eval'] = safe_groq_call("Score 1-10 & Feedback.", f"Q: {item['q']} A: {item['a']}", temp=0.1)
                if item['eval']: st.info(f"**AI Feedback:**\n{item['eval']}")
                
                if not item['ideal']:
                    item['ideal'] = safe_groq_call("Provide a 2-line expert answer. Use LaTeX.", f"Q: {item['q']}", temp=0.1)
                st.success(f"**Interviewer's Ideal Answer:**\n\n{item['ideal']}")

        # REVIEW & SAVE
        st.divider()
        with st.form("feedback"):
            u_rating = st.select_slider("AI Accuracy", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Developer Notes:")
            if st.form_submit_button("Submit to Cloud"):
                if supabase_client:
                    try:
                        all_scores = re.findall(r'\b([1-9]|10)\b', str(data))
                        avg_s = sum([int(s) for s in all_scores]) / len(all_scores) if all_scores else 0
                        supabase_client.table("reviews").insert({"level": lvl, "rating": u_rating, "comment": u_comments, "avg_score": avg_s}).execute()
                        st.success("✅ Saved!")
                    except: pass
        if st.button("🔄 Restart"):
            st.session_state.started = False; st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        # --- FIX: DETERMINISTIC SOURCE SWITCHING ---
        if data[c]["q"] is None:
            with st.spinner("🤖 Crafting your next question..."):
                asked_str = "\n".join([f"- {item['q']}" for item in data if item['q']])
                
                # Check if we have a resume. If not, always use Study Notes.
                has_resume = len(st.session_state.resume_context) > 50
                
                # Logic: Question 1, 3, 5 = RESUME | Question 2, 4, 6 = STUDY NOTES
                # (If no resume, it defaults to study notes)
                if has_resume and (c % 2 == 0):
                    # FORCE RESUME FOCUS
                    q_sys = f"""You are a professional interviewer. 
                    TASK: Pick a specific project or work experience from the RESUME and ask a deep technical question about it.
                    CRITICAL: NO preamble. Output ONLY the question.
                    DO NOT repeat or ask anything similar to: {asked_str}"""
                    u_content = f"RESUME: {st.session_state.resume_context}\nTECH CONTEXT: {st.session_state.study_context}"
                else:
                    # FORCE STUDY NOTES FOCUS
                    q_sys = f"""You are a technical interviewer. 
                    TASK: Ask a theoretical question based ONLY on the STUDY NOTES provided.
                    CRITICAL: DO NOT mention the candidate's resume or projects.
                    CRITICAL: NO preamble. Output ONLY the question text.
                    Use LaTeX ($) for math. Do not repeat: {asked_str}"""
                    u_content = f"STUDY NOTES: {st.session_state.study_context}"

                # Use Higher Temperature (0.7) for Question Generation for variety
                data[c]["q"] = safe_groq_call(q_sys, u_content, temp=0.7)
                st.rerun()

        st.progress((c + 1) / len(data))
        st.markdown(f"### {data[c]['q']}")

        # Answer Input
        user_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}", height=200)
        data[c]["a"] = user_input

        # NAVIGATION
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        data[c]["eval"] = safe_groq_call("Score 1-10 & Feedback", f"Q: {data[c]['q']} A: {data[c]['a']}", temp=0.1)
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                if data[c]["a"] and not data[c]["eval"]:
                    data[c]["eval"] = safe_groq_call("Score 1-10 & Feedback", f"Q: {data[c]['q']} A: {data[c]['a']}", temp=0.1)
                st.session_state.curr = len(data); st.rerun()

        if st.button("💡 Get Hint"):
            with st.spinner(""):
                h_sys = "Provide a 7-word clue. DO NOT give the answer."
                data[c]["hint"] = safe_groq_call(h_sys, f"Question: {data[c]['q']}", temp=0.1)
                st.rerun()
        if data[c].get("hint"): st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Career Master")
    st.write("Professional practice with split-context logic (Resume vs. Theory).")
    st.info("Upload your Resume and Study Material. The AI will alternate between project-based and theoretical questions.")
