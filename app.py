import streamlit as st
from groq import Groq
import PyPDF2

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Interview Coach", page_icon="🎯", layout="centered")

# --- INITIALIZE SESSION STATE (The Navigation Engine) ---
if "curr" not in st.session_state:
    st.session_state.curr = 0
    st.session_state.session_data = []
    st.session_state.pdf_text = ""
    st.session_state.started = False

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.title("⚙️ Setup")
    api_key = st.text_input("Enter Groq API Key", type="password")
    level = st.selectbox("Preparation Level", ["Internship", "Job (Full-Time)"])
    num_q = st.slider("Number of Questions", 1, 10, 3)
    uploaded_file = st.file_uploader("Upload PDF Study Material", type="pdf")
    
    if st.button("🚀 Start Interview"):
        if api_key and uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            st.session_state.pdf_text = "".join([p.extract_text() for p in reader.pages])
            st.session_state.session_data = [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)]
            st.session_state.curr = 0
            st.session_state.started = True
            st.rerun()
        else:
            st.error("Please provide API Key and PDF.")

# --- MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data

    # --- REPORT PHASE ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        for i, item in enumerate(data):
            with st.expander(f"Question {i+1} - { '✅ Attempted' if item['a'] else '❌ Skipped' }"):
                st.write(f"**Q:** {item['q']}")
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    st.info(item['eval'])
                else:
                    # Generate Ideal Answer for skips
                    st.warning("Skipped. Ideal Answer coming...")
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Ideal answer for: {item['q']}"}])
                    st.success(res.choices[0].message.content)
        
        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- INTERVIEW PHASE ---
    else:
        st.write(f"**Question {c + 1} of {len(data)}** | Level: **{level}**")
        
        # 1. Generate Question (Unique Memory Logic)
        if data[c]["q"] is None:
            with st.spinner("🤖 AI is thinking..."):
                past_q = [item["q"] for item in data if item["q"]]
                q_sys = f"You are a {level} interviewer. Ask ONE tech question from text. DO NOT repeat: {past_q}. NO ANSWERS."
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":st.session_state.pdf_text[:2000]}])
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.subheader(data[c]["q"])

        # 2. Hint Logic
        if st.button("💡 Get Hint"):
            with st.spinner("Nudging..."):
                h_sys = "Provide a 1-sentence nudge (MAX 10 WORDS). No answers."
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Hint for: {data[c]['q']}"}])
                data[c]["hint"] = res.choices[0].message.content
        
        if data[c]["hint"]:
            st.info(f"**Hint:** {data[c]['hint']}")

        # 3. Answer Box
        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], height=150)

        # 4. Navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1; st.rerun()
        with col2:
            if st.button("Next / Skip ➡️"):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Evaluating..."):
                        e_sys = "Score 1-10, Feedback, Ideal Answer. Be strict."
                        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":f"Q: {data[c]['q']} A: {data[c]['a']}"}])
                        data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                st.session_state.curr = len(data); st.rerun()

else:
    st.title("🎯 Welcome to AI Interview Coach")
    st.write("Use the sidebar to upload your notes and start your practice session.")
