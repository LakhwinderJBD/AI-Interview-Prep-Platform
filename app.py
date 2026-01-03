import streamlit as st
from groq import Groq
import PyPDF2
import random
import os
import re
from supabase import create_client, Client

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="AI Career Master", page_icon="🎯", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; any(word in file.name.lower() for word in ["resume", "cv"]): r_text += text
        else: s_text += text
    return s_text[:12000], r_text[:5000]

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Questions", min_value=1, max_value=20, value=3)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing materials..."):
                study, resume = process_any_files(all_files)
                st.session_ font-weight: bold; }
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
state.update({
                    "study_context": study, "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "eval": None} for _ in range(num_q)],
                    "curr": 0, "level": level, "started": True
                })
                st.rerun()

# --- 6. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data

    # --- PHASE A: FINAL REPORT & REVIEWS ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.divider()

        for i, item in enumerate(data):
            # FIX: Only show questions that were actually generated (handles early finish)
            if item["q"] is None:
                continue

            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.markdown(f"**Q:** {item['q']}")
                
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    # Generate evaluation if missing
                    if not item['eval']:
                        with st.spinner("Evaluating..."):
                            e_sys = "Provide exactly 2 lines. Line         if any(word in file.name.lower() for word in ["resume", "cv"]): r_text += text
        else: s_text += text
    return s_text[:12000], r_text[:5000]

# --- 5. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ System Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Total Questions Planned", min_value=1, max_value=20, value=5)
    all_files = st.file_uploader("Upload PDFs (Notes + Resume)", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Personalized Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing materials..."):
                study, resume = process_any_files(all_files)
                st.session_state.update({
                    "study_context": study, "resume_context": resume,
                    "session_data": [{"q": None, "a": "", "eval": None} for _ in range(num_q)],
                    "curr": 0, "level": level, "started": True
                })
                st.rerun()

# --- 6. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    lvl = st.session_state.level

    # --- PHASE A: FINAL PERFORMANCE REPORT ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.write("Review your progress below. Questions not reached were hidden.")
        st.divider()
        
        for i, item in enumerate(data):
            # FIX: If the question was never even asked (Finish early), hide it.
            if item["q"] is None:
                continue

            status = "✅ Answered" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.markdown(f"**Question:** {item['q']}")
                
                if item['a']:
1: Score 1-10 & Feedback. Line 2: VERIFIED IDEAL ANSWER. Use LaTeX for math."
                            res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {item['q']} A: {item['a']}\n{e_sys}"}])
                            item['eval'] = res.choices[0].message.content
                    st.info(item['eval'])
                else:
                    # FIX: Generate Ideal Answer for skipped questions
                    st.warning("Skipped.")
                    with st.spinner("Generating expert solution..."):
                        sol_sys = "Provide exactly 2 lines of a verified ideal answer for this question. Use LaTeX for math symbols."
                        res_sol = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role                    st.write(f"**Your Answer:** {item['a']}")
                    # If evaluation is missing, generate it now
                    if not item['eval']:
                        with st.spinner("Final scoring..."):
                            res_e = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role":"user","content":f"Grade this 1-10 with feedback and a clear 1-line ideal answer. Q: {item['q']} A: {item['a']}"}]
                            )
                            item['eval'] = res_e.choices[0].message.content
                    st.info(f"**AI Feedback & Ideal Answer:**\n\n{item['eval']}")
                else:
                    # FIX: Generate Ideal Answer for Skipped Questions
                    st.warning("You skipped this question.")
                    with st.spinner("Generating expert solution..."):
                        sol_prompt = f"Provide exactly 2 lines of a verified ideal answer for: {item['q']}. Use LaTeX ($) for math."
                        res_sol = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": sol": "user", "content": f"{sol_sys}\nQuestion: {item['q']}"}])
                        st.success(f"**Interviewer's Ideal Answer:**\n\n{res_sol.choices[0].message.content}")

        st.divider()
        with st.form("feedback"):
            u_rating = st.select_slider("Rate AI Accuracy", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Developer Notes:")
            if st.form_submit_button("Submit Review"):
                if supabase_client:
                    try:
                        all_scores = re.findall(r'\b([1-9]|10)\b', str(data))
                        avg_s = sum([int(s) for s in all_scores]) / len(all_scores) if all_scores else 0
                        supabase_client.table("reviews").insert({"level": st.session_state.level, "rating": u_rating, "comment": u_comments, "avg_score": avg_s}).execute()
                        st.success("✅ Saved to Cloud!")
                    except Exception as e: st.error(f"Error: {e}")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False; st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner_prompt}]
                        )
                        st.success(f"**Interviewer's Ideal Answer:**\n\n{res_sol.choices[0].message.content}")

        st.divider()
        # REVIEWS
        with st.form("feedback"):
            u_rating = st.select_slider("Rate AI Accuracy", options=[1,2,3,4,5], value=5)
            u_comments = st.text_area("Developer Notes:")
            if st.form_submit_button("Submit to Cloud"):
                if supabase_client:
                    all_scores = re.findall(r'\b([1-9]|10)\b', str(data))
                    avg_s = sum([int(s) for s in all_scores]) / len(all_scores) if all_scores else 0
                    supabase_client.table("reviews").insert({"level": lvl, "rating": u_rating, "comment": u_comments, "avg_score": avg_s}).execute()
                    st.success("✅ Logged in Database!")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False; st("🤖 AI is thinking..."):
                asked = [item["q"] for item in data if item["q"]]
                use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                
                # STRICT PROMPT: NO INTRO, NO PREAMBLE
                q_sys = f"You are an expert interviewer. Ask ONE {st.session_state.level} level question. Use LaTeX for any math symbols ($). NO PREAMBLE. NO intro text like 'Here is a question'. Output ONLY the raw question text."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", ".rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking..."):
                asked = [item["q"] for item in data if item["q"]]
                use_resume = (random.random() < 0.7) if lvl == "Job" else (random.random() < 0.3)
                q_syscontent": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.markdown(f"### {data[c]['q']}")

        # Answer Box
        user_ans = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{ = f"You are a technical interviewer. Ask ONE {lvl} level question. Use LaTeX for math. NO PREAMBLE. Output ONLY the question. Do not repeat: {asked}."
                u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.progress((c + 1) / len(data))
        st.markdown(f"### {data[c]['q']}")

        user_input = st.text_area("Your Answer:", value=data[c]["a"], key=f"c}", height=150)
        data[c]["a"] = user_ans

        # Navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1; st.rerun()
        with col2:
            # COMBINED NEXT/SKIP BUTTON
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Analyzing..."):
                        e_sys = "Exactly 2 lines. Line 1: Score 1-10 & Feedback. Line 2: Ideal Answer with Math."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                ifans_{c}", height=150, placeholder="Type your answer. Use $..$ for math if needed.")
        data[c]["a"] = user_input

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        e_sys = "Exactly 2 lines. Line 1: Score & Feedback. Line 2: Ideal Answer with Math."
                        res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                        data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                # Safety evaluation for the current question before finishing
                if data[c]["a"] and not data[c]["eval"]:
                    res_e = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Grade this: Q: {data[c]['q']} A: {data[c]['a']}"}])
                    data[c]["eval"] = res_e.choices[0].message.content
                st.session_state.curr = len(data); st.rerun()

else:
    st.title("🎯 AI Interview Coach")
    st.write("Professional text-only platform optimized for technical roles.")
