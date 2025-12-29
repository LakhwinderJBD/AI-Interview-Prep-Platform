import streamlit as st
from groq import Groq
import PyPDF2
from duckduckgo_search import DDGS

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="AI Career Coach", page_icon="💼", layout="centered")

# --- 2. API KEY HANDLING ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

# --- 3. SESSION STATE ---
if "started" not in st.session_state:
    st.session_state.update({
        "curr": 0,
        "session_data": [],
        "pdf_text": "",
        "resume_text": "", # New field for resume
        "started": False,
        "level": "Internship"
    })

def get_verified_context(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=1)]
            return "\n".join(results)
    except:
        return "Technical standard documentation."

# --- 4. SIDEBAR: DOUBLE UPLOADER ---
with st.sidebar:
    st.title("⚙️ Interview Setup")
    if "GROQ_API_KEY" in st.secrets: st.success("✅ API Key Active")
    
    level = st.selectbox("Preparation Level", ["Internship", "Job"])
    num_q = st.number_input("Number of Questions", min_value=1, max_value=15, value=3)
    
    st.divider()
    st.subheader("📁 Upload Documents")
    study_file = st.file_uploader("Upload Study Material (PDF)", type="pdf")
    resume_file = st.file_uploader("Upload Your Resume (PDF)", type="pdf")
    
    if st.button("🚀 Start Personalized Interview"):
        if api_key and study_file and resume_file:
            # Read Study PDF
            reader_s = PyPDF2.PdfReader(study_file)
            st.session_state.pdf_text = "".join([p.extract_text() for p in reader_s.pages])[:6000]
            
            # Read Resume PDF
            reader_r = PyPDF2.PdfReader(resume_file)
            st.session_state.resume_text = "".join([p.extract_text() for p in reader_r.pages])[:3000]
            
            # Reset session
            st.session_state.session_data = [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)]
            st.session_state.curr = 0
            st.session_state.level = level
            st.session_state.started = True
            st.rerun()
        else:
            st.error("Missing API Key, Study Material, or Resume!")

# --- 5. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data

    if c >= len(data):
        # --- REPORT SECTION ---
        st.header("📊 Final Performance Report")
        for i, item in enumerate(data):
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}"):
                st.write(f"**Question:** {item['q']}")
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    st.info(item['eval'])
                else:
                    v_context = get_verified_context(item['q'])
                    res = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": f"Verified Info: {v_context}. Provide a 2-line ideal answer for: {item['q']}"}]
                    )
                    st.success(f"**Ideal Answer:**\n{res.choices[0].message.content}")
        
        if st.button("🔄 Restart"):
            st.session_state.started = False
            st.rerun()

    else:
        # --- INTERVIEW SECTION ---
        st.progress((c + 1) / len(data))
        st.write(f"**Personalized Question {c + 1} of {len(data)}**")
        
        # 1. PERSONALISED QUESTION GENERATION
        if data[c]["q"] is None:
            with st.spinner("🤖 Analyzing your resume and notes..."):
                asked = [item["q"] for item in data if item["q"]]
                
                # The "Magic" Resume Prompt
                q_sys = f"""You are a technical interviewer. 
                I will provide you with a Resume and Study Material.
                TASK: Pick a project or skill from the Resume and ask a technical question about it using concepts from the Study Material.
                EXAMPLE: 'I see you worked on an Eye Disease project. How would you handle class imbalance in that specific dataset based on the techniques in your notes?'
                CRITICAL: {st.session_state.level} level. Do NOT repeat: {asked}. Output ONLY the question."""
                
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": q_sys},
                        {"role": "user", "content": f"RESUME: {st.session_state.resume_text}\nSTUDY NOTES: {st.session_state.pdf_text}"}
                    ]
                )
                data[c]["q"] = res.choices[0].message.content
                st.rerun()

        st.subheader(data[c]["q"])

        # Hint, Answer, Navigation (Same as before but cleaned up)
        if st.button("💡 Get Hint"):
            h_res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": f"Provide a 7-word hint for: {data[c]['q']}"}]
            )
            data[c]["hint"] = h_res.choices[0].message.content
        
        if data[c]["hint"]: st.warning(f"💡 {data[c]['hint']}")

        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], height=100, key=f"ans_{c}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Back") and c > 0: st.session_state.curr -= 1; st.rerun()
        with col2:
            btn_lbl = "Next ➡️" if data[c]["a"] else "Skip ⏩"
            if st.button(btn_lbl):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        e_sys = "Provide 2 lines: Line 1 Score & Feedback. Line 2 Verified Ideal Answer."
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Q: {data[c]['q']}\nA: {data[c]['a']}\n{e_sys}"}]
                        )
                        data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1; st.rerun()
        with col3:
            if st.button("🏁 Finish"): st.session_state.curr = len(data); st.rerun()

else:
    st.title("🎯 AI Career Coach")
    st.write("The only platform that interviews you on YOUR projects and YOUR notes.")
    st.info("Please upload both your Resume and Study Material in the sidebar to begin.")
