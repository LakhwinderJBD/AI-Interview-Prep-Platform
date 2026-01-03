import streamlit as st
from groq import Groq
import PyPDF2
import random
import os
import re
import pandas as pd
from supabase import create_client, Client

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="AI Career Master", page_icon="🎯", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stTextArea>div>div>textarea { font-size: 16px; }
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

# --- 4. DOCUMENT PROCESSOR ---
def process_any_files(uploaded_files):
    s_text, r_text = "", ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = f"\n--- Source: {file.name} ---\n" + "".join([p.extract_text() for p in reader.pages])
        if any(word in file.name.lower() for word in ["resume", "cv"]): r_text += text
        else: s_text += text
    return s_text[:12000], r_text[:5000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Personalized Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing materials..."):
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
    lvl = st.session_state.level

    # --- PHASE A: FINAL REPORT (WITH AUTOMATIC IDEAL ANSWERS) ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.write("Review your results and learn from skipped questions.")
        st.divider()
        
        for i, item in enumerate(data):
            if item["q"]:
                status = "✅ Attempted" if item['a'] else "❌ Skipped"
                with st.expander(f"Question {i+1} | {status}", expanded=True):
                    # Show Question with Markdown (for Math)
                    st.markdown(f"**Question:** {item['q']}")
                    
                    if item['a']:
                        st.write(f"**Your Answer:** {item['a']}")
                        # Generate evaluation if it doesn't exist
                        if not item['eval']:
                            with st.spinner("Grading..."):
                                e_res = client.chat.completions.create(
                                    model="llama-3.1-8b-instant",
                                    messages=[{"role":"user","content":f"Grade 1-10 with feedback and ideal answer (2 lines total). Q: {item['q']} A: {item['a']}"}]
                                )
                                item['eval'] = e_res.choices[0].message.content
                        st.info(item['eval'])
                    else:
                        # FIX: FORCE IDEAL ANSWER FOR SKIPS
                        st.warning("You skipped this question.")
                        with st.spinner(f"Generating expert solution for Q{i+1}..."):
                            sol_prompt = f"Provide exactly 2 lines of a verified ideal answer for: {item['q']}. Use LaTeX for math symbols."
                            res_sol = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "user", "content": sol_prompt}]
                            )
                            st.success(f"**Expert Ideal Answer:**\n\n{res_sol.choices[0].message.content}")

        st.divider()
        # SUPABASE REVIEW SYSTEM
        with st.form("review_form"):
            u_rating = st.select_slider("Rate AI Accuracy", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Developer Notes / Feedback:")
            if st.form_submit_button("Submit Review"):
                if supabase_client:
                    try:
                        all_scores = re.findall(r'\b([1-9]|10)\b', str(data))
                        avg_s = sum([int(s) for s in all_scores]) / len(all_scores) if all_scores else 0
                        supabase_client.table("reviews").insert({
                            "level": lvl, "rating": u_rating, "comment": u_comments, "avg_score": avg_s
                        }).execute()
                        st.success("Review logged in Master Database!")
                    except Exception as e: st.error(f"Error: {e}")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False; st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        st.progress((c + 1) / len(data))
        
        if data[c]["q"] is None:
            with st.spinner("🤖 Crafting question..."):
                asked = [item["q"] for item in data if item["q"]]
                use_resume = (random.random() < 0.7) if lvl == "Job" else (random.random() < 0.3)
                
                q_sys = f"""You are a {lvl} interviewer. Ask ONE technical question.
                CRITICAL: No preamble. Output ONLY the raw question.
                If asking math, use LaTeX (e.g. $y = mx + b$). Do not repeat: {asked}."""
                
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.markdown(f"### {data[c]['q']}")

        # Answer Input
        user_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}", height=150)
        data[c]["a"] = user_input

        # Navigation
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("💡 Hint"):
                res_h = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word technical hint for: {data[c]['q']}"}])
                data[c]["hint"] = res_h.choices[0].message.content; st.rerun()
        with col3:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Evaluating..."):
                        e_sys = "Exactly 2 lines. Line 1: Score 1-10 & Feedback. Line 2: Ideal Answer with Math."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col4:
            if st.button("🏁 Finish"):
                if data[c]["a"] and not data[c]["eval"]:
                    res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}"}])
                    data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr = len(data); st.rerun()

        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

else:
    st.title("🎯 AI Interview Coach")
    st.write("Professional practice for Data Science and ML roles.")
    st.info("Upload multiple PDFs (Syllabus, Resume, Books) in the sidebar to begin.")
