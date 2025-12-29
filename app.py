import streamlit as st
from groq import Groq
import PyPDF2
from duckduckgo_search import DDGS
import random

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Adaptive Coach", page_icon="🤖", layout="centered")

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

# --- SMART FILE CLASSIFIER ---
def process_any_files(uploaded_files):
    s_text = ""
    r_text = ""
    for file in uploaded_files:
        reader = PyPDF2.PdfReader(file)
        text = f"\n--- Source: {file.name} ---\n" + "".join([p.extract_text() for p in reader.pages])
        
        # Categorize
        if any(word in file.name.lower() for word in ["resume", "cv", "portfolio"]):
            r_text += text
        else:
            s_text += text
    return s_text[:10000], r_text[:5000]

def get_verified_ans(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=1)]
            return results[0]
    except: return "Standard technical verification."

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Adaptive Setup")
    level = st.selectbox("Interview Level", ["Internship", "Job"])
    num_q = st.number_input("Questions", min_value=1, max_value=25, value=3)
    
    st.divider()
    all_files = st.file_uploader("Upload PDFs (Notes, Resume, or both)", 
                                 type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Start Interview"):
        if api_key and all_files:
            with st.spinner("Analyzing sources..."):
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
            st.error("Please provide an API Key and at least one PDF.")

# --- 5. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    
    # Check what is available
    has_study = len(st.session_state.study_context) > 10
    has_resume = len(st.session_state.resume_context) > 10

    if c >= len(data):
        st.header("📊 Final Performance Report")
        for i, item in enumerate(data):
            with st.expander(f"Q{i+1}: {'✅' if item['a'] else '❌'}"):
                st.write(f"**Q:** {item['q']}")
                if item['a']:
                    st.info(item['eval'])
                else:
                    st.success(f"**Ideal Answer:** {get_verified_ans(item['q'])[:300]}")
        if st.button("🔄 New Session"):
            st.session_state.started = False
            st.rerun()
    else:
        # --- ADAPTIVE QUESTION GENERATION ---
        if data[c]["q"] is None:
            with st.spinner("🤖 Crafting question..."):
                # Determine Source based on availability
                if has_study and has_resume:
                    # Use Industry Weighting (70/30)
                    use_resume = (random.random() < 0.7) if st.session_state.level == "Job" else (random.random() < 0.3)
                elif has_resume:
                    use_resume = True
                else:
                    use_resume = False

                if use_resume:
                    q_sys = f"You are a {st.session_state.level} interviewer. Ask a technical question based on a project in the RESUME. Use STUDY NOTES if available for technical depth. ONLY the question."
                    u_content = f"RESUME: {st.session_state.resume_context}\nNOTES: {st.session_state.study_context}"
                    source_label = "Source: Resume + Projects"
                else:
                    q_sys = f"You are a {st.session_state.level} interviewer. Ask a technical question based ONLY on the STUDY NOTES/QUESTION BANK. NO preamble."
                    u_content = f"NOTES: {st.session_state.study_context}"
                    source_label = "Source: Study Material"

                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": q_sys}, {"role": "user", "content": u_content}]
                )
                data[c]["q"] = res.choices[0].message.content
                st.session_state.current_source = source_label
                st.rerun()

        st.progress((c + 1) / len(data))
        st.caption(st.session_state.get('current_source', 'Technical'))
        st.subheader(data[c]["q"])
        
        # Hint & Answer
        if st.button("💡 Hint"):
            h_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"7-word hint for: {data[c]['q']}"}])
            data[c]["hint"] = h_res.choices[0].message.content
        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], key=f"ans_{c}")

        # Nav
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Back") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next/Skip ➡️"):
                if data[c]["a"]:
                    e_sys = "Provide exactly 2 lines: Line 1 Score & Feedback. Line 2 Verified Ideal Answer."
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}\n{e_sys}"}])
                    data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"): st.session_state.curr = len(data); st.rerun()

else:
    st.title("🎯 AI Adaptive Coach")
    st.write("Upload any combination of PDFs (Study Material, Question Banks, or Resumes).")
