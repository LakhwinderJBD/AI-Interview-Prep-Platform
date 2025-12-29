import streamlit as st
from groq import Groq
import PyPDF2
import os

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Interview Coach", page_icon="🎯", layout="centered")

# --- 2. API KEY HANDLING (Secrets + Sidebar Fallback) ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password", help="Get your key at console.groq.com")

# --- 3. INITIALIZE SESSION STATE ---
if "started" not in st.session_state:
    st.session_state.update({
        "curr": 0,
        "session_data": [],
        "pdf_text": "",
        "started": False,
        "level": "Internship"
    })

# --- 4. SIDEBAR: SETTINGS ---
with st.sidebar:
    st.title("⚙️ Setup")
    
    if "GROQ_API_KEY" in st.secrets:
        st.success("✅ API Key loaded from Secrets")
    
    level = st.selectbox("Preparation Level", ["Internship", "Job"], index=0)
    
    # CHANGED: Slider replaced with Number Input
    num_q = st.number_input("Number of Questions", min_value=1, max_value=50, value=3, step=1)
    
    uploaded_file = st.file_uploader("Upload PDF Study Material", type="pdf")
    
    if st.button("🚀 Start Interview"):
        if api_key and uploaded_file:
            # Setup fresh session
            reader = PyPDF2.PdfReader(uploaded_file)
            full_text = "".join([p.extract_text() for p in reader.pages])
            
            st.session_state.pdf_text = full_text[:8000] # Optimized context size
            st.session_state.session_data = [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)]
            st.session_state.curr = 0
            st.session_state.level = level
            st.session_state.started = True
            st.rerun()
        else:
            st.error("Please provide an API Key (in Secrets or Sidebar) and upload a PDF.")

# --- 5. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    current_level = st.session_state.level

    # --- PHASE A: FINAL REPORT ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.divider()
        for i, item in enumerate(data):
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}"):
                st.write(f"**Q:** {item['q']}")
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    st.info(item['eval'])
                else:
                    st.warning("You skipped this question.")
                    # Fast Ideal Answer Generation for skipped items
                    with st.spinner("Generating solution..."):
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Provide a concise ideal answer for this interview question: {item['q']}"}]
                        )
                        st.success(f"**Ideal Answer:**\n{res.choices[0].message.content}")
        
        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: INTERVIEW QUESTIONS ---
    else:
        st.progress((c + 1) / len(data))
        st.write(f"**Question {c + 1} of {len(data)}** | Level: **{current_level}**")
        
        # 1. Generate Question
        if data[c]["q"] is None:
            with st.spinner("🤖 AI is analyzing your document..."):
                past_qs = [item["q"] for item in data if item["q"]]
                q_sys = f"You are a {current_level} level interviewer. Ask ONE specific technical question based on the document text. Do NOT repeat these questions: {past_qs}. Ask only the question text."
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": q_sys},
                        {"role": "user", "content": st.session_state.pdf_text}
                    ]
                )
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.subheader(data[c]["q"])

        # 2. Hint Logic
        if st.button("💡 Get Hint"):
            with st.spinner("Nudging..."):
                h_sys = f"Provide a 1-sentence {current_level}-level hint for this question. Do NOT give the answer."
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": f"{h_sys}\nQuestion: {data[c]['q']}"}]
                )
                data[c]["hint"] = res.choices[0].message.content
        
        if data[c]["hint"]:
            st.info(f"**Hint:** {data[c]['hint']}")

        # 3. Answer Box
        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], height=150, key=f"text_{c}")

        # 4. Navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1
                st.rerun()
        with col2:
            btn_label = "Next ➡️" if data[c]["a"] else "Skip ⏩"
            if st.button(btn_label):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Evaluating..."):
                        e_sys = "You are a professional evaluator. Provide a Score (1-10), brief feedback, and an Ideal Answer."
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Q: {data[c]['q']}\nA: {data[c]['a']}"}]
                        )
                        data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1
                st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                st.session_state.curr = len(data)
                st.rerun()

else:
    st.title("🎯 Welcome to AI Interview Coach")
    st.write("Professional interview practice tailored to your materials.")
    st.markdown("""
    1. **Upload your PDF** in the sidebar.
    2. Choose your **Level** (Internship/Job).
    3. Enter the **Number of Questions** you want to practice.
    4. Start and get instant feedback!
    """)
