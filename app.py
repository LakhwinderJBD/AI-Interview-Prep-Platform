import streamlit as st
from groq import Groq
import PyPDF2
from duckduckgo_search import DDGS
import random

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Master Coach", page_icon="🎓", layout="centered")

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
        "started": False, "level": "Internship"
    })

# --- DOCUMENT PROCESSOR (Handles 5-6+ Files) ---
def process_multiple_files(uploaded_files):
    study_combined = ""
    resume_combined = ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = "".join([p.extract_text() for p in reader.pages])
        
        # Logic: If file name has 'resume' or 'cv', treat as Resume context
        if "resume" in file.name.lower() or "cv" in file.name.lower():
            resume_combined += f"\n[FILE: {file.name}]\n{text}"
        else:
            study_combined += f"\n[FILE: {file.name}]\n{text}"
            
    # Return limited context to fit AI memory (approx 8k chars for notes, 3k for resume)
    return study_combined[:8000], resume_combined[:3000]

def get_verified_ans(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=1)]
            return results[0]
    except: return "Verified Technical Standard."

# --- 4. SIDEBAR: MULTI-UPLOADER ---
with st.sidebar:
    st.title("⚙️ Setup")
    level = st.selectbox("Career Level", ["Internship", "Job"])
    num_q = st.number_input("Total Questions", min_value=1, max_value=20, value=5)
    
    st.divider()
    # MULTI-FILE UPLOADER ENABLED
    all_files = st.file_uploader("Upload PDFs (Notes, Resume, Books)", 
                                 type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Master Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing all documents..."):
                study, resume = process_multiple_files(all_files)
                st.session_state.study_context = study
                st.session_state.resume_context = resume
                st.session_state.session_data = [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)]
                st.session_state.curr = 0
                st.session_state.level = level
                st.session_state.started = True
                st.rerun()

# --- 5. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    lvl = st.session_state.level

    if c >= len(data):
        # --- REPORT SECTION ---
        st.header("📊 Final Master Performance Report")
        for i, item in enumerate(data):
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}"):
                st.write(f"**Question:** {item['q']}")
                if item['a']:
                    if not item['eval']:
                        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Score 1-10 and 2-line ideal answer for: {item['q']} A: {item['a']}"}])
                        item['eval'] = res.choices[0].message.content
                    st.info(item['eval'])
                else:
                    v_ans = get_verified_ans(item['q'])
                    st.success(f"**Ideal Answer:** {v_ans[:300]}")
        
        if st.button("🔄 Restart"):
            st.session_state.started = False
            st.rerun()

    else:
        # --- INTERVIEW SECTION ---
        st.progress((c + 1) / len(data))
        
        # 1. INDUSTRY-WEIGHTED QUESTION GENERATION
        if data[c]["q"] is None:
            with st.spinner("🤖 Consulting sources..."):
                # Research-Based Weighting:
                # Internship: 70% chance PDF (Theory focus)
                # Job: 70% chance Resume (Experience focus)
                is_resume_turn = (random.random() < 0.7) if lvl == "Job" else (random.random() < 0.3)
                
                # Force at least one resume question if resume uploaded
                if c == 0 and st.session_state.resume_context and lvl == "Job": is_resume_turn = True

                if is_resume_turn and st.session_state.resume_context:
                    q_sys = f"You are a {lvl} interviewer. Pick a project from the RESUME and ask a technical question about it using concepts from the STUDY NOTES. ONLY THE QUESTION."
                    user_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                else:
                    q_sys = f"You are a {lvl} interviewer. Ask ONE technical question based ONLY on the STUDY NOTES PDFs. DO NOT mention the resume. ONLY THE QUESTION."
                    user_content = f"STUDY NOTES: {st.session_state.study_context}"

                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": user_content}]
                )
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.subheader(data[c]["q"])
        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")
        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}")

        # Controls
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Back") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                h_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word hint for: {data[c]['q']}"}])
                data[c]["hint"] = h_res.choices[0].message.content
                st.rerun()
        with col3:
            btn_lbl = "Next ➡️" if data[c]["a"] else "Skip ⏩"
            if st.button(btn_lbl):
                if data[c]["a"]:
                    e_sys = "Provide exactly 2 lines: Line 1 Score & Feedback. Line 2 Verified Ideal Answer."
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                    data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                st.session_state.curr = len(data); st.rerun()

else:
    st.title("🎯 AI Master Interviewer")
    st.write("Upload multiple Study Notes + your Resume to begin.")
