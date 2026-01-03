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
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
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

# --- 4. API HELPER WITH RETRY LOGIC ---
def safe_groq_call(system_prompt, user_prompt):
    """Automatically handles Rate Limits (Error 429)"""
    client = Groq(api_key=api_key)
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                temperature=0.1
            )
            return res.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                time.sleep(3) # Wait for rate limit reset
            else:
                return f"AI busy. Error: {str(e)}"
    return "Error: API Rate Limit exceeded. Please try again in 1 minute."

def process_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv"]): r_text += text
        else: s_text += text
    # Optimized context size to stay under token limits
    return s_text[:6000], r_text[:3000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Total Questions Planned", min_value=1, max_value=20, value=5)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Personalized Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing materials..."):
                study, resume = process_files(all_files)
                st.session_state.update({
                    "study_context": study, "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "eval": None, "ideal": None} for _ in range(num_q)],
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
        st.write("Complete analysis of your session. Questions not reached are hidden.")
        st.divider()
        
        for i, item in enumerate(data):
            if item["q"] is None: continue # Skip slots if user finished early (e.g. at Q6 of 10)

            status = "✅ Answered" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.markdown(f"**Question:** {item['q']}")
                st.write(f"**Your Answer:** {item['a'] if item['a'] else 'No answer provided.'}")
                
                # 1. EVALUATION (Score/Feedback)
                if item['a']:
                    if not item['eval']:
                        with st.spinner("Calculating score..."):
                            e_sys = "You are a recruiter. Give Score (1-10) and 1-sentence feedback. Be brief."
                            item['eval'] = safe_groq_call(e_sys, f"Q: {item['q']} A: {item['a']}")
                    st.info(f"**AI Feedback:**\n{item['eval']}")
                
                # 2. THE IDEAL ANSWER (Generated for ALL questions)
                if not item['ideal']:
                    with st.spinner("Synthesizing interviewer's ideal answer..."):
                        sol_sys = "You are a senior technical lead. Provide a perfect 2-line answer that an interviewer would expect. Use LaTeX ($) for math."
                        item['ideal'] = safe_groq_call(sol_sys, f"Question: {item['q']}")
                
                st.success(f"**Interviewer's Ideal Answer:**\n\n{item['ideal']}")

        # REVIEWS
        st.divider()
        st.subheader("🌟 Developer Review")
        with st.form("feedback"):
            u_rating = st.select_slider("AI Accuracy Rating", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Suggest improvements:")
            if st.form_submit_button("Submit to Cloud"):
                if supabase_client:
                    try:
                        all_scores = re.findall(r'\b([1-9]|10)\b', str(data))
                        avg_s = sum([int(s) for s in all_scores]) / len(all_scores) if all_scores else 0
                        supabase_client.table("reviews").insert({
                            "level": lvl, "rating": u_rating, "comment": u_comments, "avg_score": avg_s
                        }).execute()
                        st.success("✅ Logged in Database!")
                    except: st.error("Database connection error.")

        if st.button("🔄 Restart Interview"):
            st.session_state.started = False; st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        # Question Generation Logic
        if data[c]["q"] is None:
            with st.spinner("🤖 AI is thinking..."):
                asked = [item["q"] for item in data if item["q"]]
                use_resume = (random.random() < 0.7) if lvl == "Job" else (random.random() < 0.3)
                
                q_sys = f"""You are a technical interviewer. Ask ONE {lvl} level question.
                CRITICAL: NO preamble. Output ONLY the raw question.
                If asking math, use LaTeX ($) (e.g. $\sigma$).
                Do not repeat: {asked}."""
                
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                data[c]["q"] = safe_groq_call(q_sys, u_content)
                st.rerun()

        st.progress((c + 1) / len(data))
        st.markdown(f"### {data[c]['q']}")

        user_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}", height=150, placeholder="Type your answer clearly...")
        data[c]["a"] = user_input

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next ➡️"):
                # Pre-evaluate if answer exists to save time in report
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        data[c]["eval"] = safe_groq_call("Score 1-10 & Feedback (2 lines).", f"Q: {data[c]['q']} A: {data[c]['a']}")
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                # Safety evaluation for the current question
                if data[c]["a"] and not data[c]["eval"]:
                    data[c]["eval"] = safe_groq_call("Score 1-10 & Feedback", f"Q: {data[c]['q']} A: {data[c]['a']}")
                st.session_state.curr = len(data); st.rerun()

        # Hint Logic
        if st.button("💡 Get Hint"):
            with st.spinner(""):
                h_sys = "Provide a 7-word technical hint. NO answers."
                data[c]["hint"] = safe_groq_call(h_sys, f"Question: {data[c]['q']}")
        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Interview Coach")
    st.write("Professional practice with Math support. Voice and PDF Export removed for maximum speed.")
