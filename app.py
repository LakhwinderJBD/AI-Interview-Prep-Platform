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

# --- 4. API HELPER ---
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
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Total Questions", min_value=1, max_value=20, value=5)
    all_files = st.file_uploader("Upload PDF (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Personalized Session"):
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

    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.divider()
        
        for i, item in enumerate(data):
            if item["q"] is None: continue 
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.markdown(f"**Question:** {item['q']}")
                st.write(f"**Your Answer:** {item['a'] if item['a'] else 'No answer provided.'}")
                
                if item['a']:
                    if not item['eval']:
                        e_sys = "You are a recruiter. Grade 1-10 and give feedback in PLAIN TEXT. NO special formatting or LaTeX for feedback."
                        item['eval'] = safe_groq_call(e_sys, f"Q: {item['q']} A: {item['a']}")
                    st.info(f"**Interviewer Feedback:**\n{item['eval']}")
                
                if not item['ideal']:
                    sol_sys = "Provide a professional 2-line answer in PLAIN TEXT. Use LaTeX ($) ONLY for math formulas. Ensure text is horizontal and readable."
                    item['ideal'] = safe_groq_call(sol_sys, f"Q: {item['q']}")
                st.success(f"**Interviewer's Ideal Answer:**\n\n{item['ideal']}")

        st.divider()
        with st.form("feedback"):
            u_rating = st.select_slider("AI Accuracy", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Notes for Developer:")
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

    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 AI is thinking..."):
                asked_questions = [item["q"] for item in data if item["q"]]
                asked_list = "\n".join([f"- {q}" for q in asked_questions])
                
                has_resume = len(st.session_state.resume_context) > 50
                is_resume_turn = (c + 1) % 2 != 0 if lvl == "Internship" else (c + 1) % 3 != 0

                if has_resume and is_resume_turn:
                    q_sys = f"""You are a senior hiring lead. 
                    TASK: Pick a project or skill from the RESUME that HAS NOT been discussed yet.
                    CRITICAL: Ask a DEEP technical question. NO preamble. NO vertical text.
                    FORBIDDEN TOPICS (Do not repeat these): {asked_list}"""
                    u_content = f"RESUME: {st.session_state.resume_context}\nTECH: {st.session_state.study_context}"
                else:
                    q_sys = f"""You are a technical interviewer. 
                    TASK: Ask a theoretical question based ONLY on the STUDY NOTES. 
                    CRITICAL: DO NOT repeat topics discussed in: {asked_list}.
                    Output ONLY the question text. Use LaTeX ($) for math formulas."""
                    u_content = f"NOTES: {st.session_state.study_context}"

                data[c]["q"] = safe_groq_call(q_sys, u_content, temp=0.7)
                st.rerun()

        st.progress((c + 1) / len(data))
        st.markdown(f"### {data[c]['q']}")
        user_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}", height=180)
        data[c]["a"] = user_input

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    data[c]["eval"] = safe_groq_call("2-line feedback & score 1-10.", f"Q: {data[c]['q']} A: {data[c]['a']}")
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                if data[c]["a"] and not data[c]["eval"]:
                    data[c]["eval"] = safe_groq_call("Score 1-10 & Feedback", f"Q: {data[c]['q']} A: {data[c]['a']}")
                st.session_state.curr = len(data); st.rerun()

        if st.button("💡 Get Hint"):
            with st.spinner(""):
                h_sys = "Provide a 7-word nudge clue. NO answers. NO vertical text."
                data[c]["hint"] = safe_groq_call(h_sys, f"Q: {data[c]['q']}")
                st.rerun()
        if data[c].get("hint"): st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Interview Coach")
    st.write("Personalized practice to land ₹50k+ internships.")
