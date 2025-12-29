import streamlit as st
from groq import Groq
import PyPDF2
from duckduckgo_search import DDGS

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="AI Interview Coach", page_icon="🎯", layout="centered")

# --- 2. API KEY HANDLING ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password")

# --- 3. INITIALIZE SESSION STATE ---
if "started" not in st.session_state:
    st.session_state.update({
        "curr": 0,
        "session_data": [],
        "pdf_text": "",
        "started": False,
        "level": "Internship"
    })

# --- INTERNET VERIFICATION FUNCTION ---
def get_verified_context(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=1)]
            return "\n".join(results)
    except:
        return "Technical standard documentation."

# --- 4. SIDEBAR: SETUP ---
with st.sidebar:
    st.title("⚙️ Setup")
    if "GROQ_API_KEY" in st.secrets:
        st.success("✅ API Key Active")
    
    level = st.selectbox("Preparation Level", ["Internship", "Job"])
    num_q = st.number_input("Number of Questions", min_value=1, max_value=20, value=3, step=1)
    uploaded_file = st.file_uploader("Upload PDF Study Material", type="pdf")
    
    if st.button("🚀 Start Interview"):
        if api_key and uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            full_text = "".join([p.extract_text() for p in reader.pages])
            st.session_state.pdf_text = full_text[:7000] 
            st.session_state.session_data = [{"q": None, "a": "", "hint": None, "eval": None} for _ in range(num_q)]
            st.session_state.curr = 0
            st.session_state.level = level
            st.session_state.started = True
            st.rerun()
        else:
            st.error("Please provide an API Key and upload your PDF.")

# --- 5. MAIN INTERFACE ---
if st.session_state.started and api_key:
    client = Groq(api_key=api_key)
    c = st.session_state.curr
    data = st.session_state.session_data
    lvl = st.session_state.level

    # --- PHASE A: FINAL PERFORMANCE REPORT ---
    if c >= len(data):
        st.header("📊 Final Performance Report")
        st.divider()
        for i, item in enumerate(data):
            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}"):
                st.write(f"**Question:** {item['q']}")
                if item['a']:
                    st.write(f"**Your Answer:** {item['a']}")
                    st.info(item['eval'])
                else:
                    st.warning("You skipped this question.")
                    with st.spinner("Fetching verified ideal answer..."):
                        v_context = get_verified_context(item['q'])
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Verified Info: {v_context}. Provide a 2-line ideal answer for: {item['q']}. STRICTLY 2 LINES."}]
                        )
                        st.success(f"**Verified Ideal Answer:**\n{res.choices[0].message.content}")
        
        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()

    # --- PHASE B: ACTIVE INTERVIEW ---
    else:
        st.progress((c + 1) / len(data))
        st.write(f"**Question {c + 1} of {len(data)}** | Level: **{lvl}**")
        
        # --- FIX: UNIQUE QUESTION GENERATION ---
        if data[c]["q"] is None:
            with st.spinner("🤖 Thinking of a unique question..."):
                # Collect all questions that were already asked in this session
                asked_questions = [item["q"] for item in data if item["q"] is not None]
                
                q_sys = f"""You are a {lvl} interviewer. 
                Ask ONE technical question based on the provided text.
                CRITICAL RULE: Do NOT ask any of these questions again: {asked_questions}.
                Output ONLY the question text. No preamble."""
                
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

        # 2. Hint Logic (Strict 7 Words)
        if st.button("💡 Get Hint"):
            with st.spinner(""):
                h_sys = "Provide a hint for this question in EXACTLY 7 words or less. Do NOT give the answer."
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": f"{h_sys}\nQ: {data[c]['q']}"}]
                )
                data[c]["hint"] = res.choices[0].message.content
        
        if data[c]["hint"]:
            st.warning(f"💡 {data[c]['hint']}")

        # 3. Answer Box
        data[c]["a"] = st.text_area("Your Answer:", value=data[c]["a"], height=100, key=f"ans_{c}")

        # 4. Navigation Controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous") and c > 0:
                st.session_state.curr -= 1
                st.rerun()
        with col2:
            btn_label = "Next ➡️" if data[c]["a"] else "Skip ⏩"
            if st.button(btn_label):
                if data[c]["a"] and not data[c]["eval"]:
                    with st.spinner("Checking..."):
                        v_context = get_verified_context(data[c]['q'])
                        e_sys = """Provide exactly 2 lines of response. 
                        Line 1: Score/10 and 1-sentence feedback. 
                        Line 2: A one-sentence verified ideal answer based on the context and PDF."""
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"Verified Info: {v_context}\nPDF Info: {st.session_state.pdf_text[:500]}\nQ: {data[c]['q']}\nA: {data[c]['a']}\n{e_sys}"}]
                        )
                        data[c]["eval"] = res.choices[0].message.content
                st.session_state.curr += 1
                st.rerun()
        with col3:
            if st.button("🏁 Finish"):
                st.session_state.curr = len(data)
                st.rerun()

else:
    st.title("🎯 AI Interview Coach")
    st.write("Professional, document-based practice. Upload your PDF and hit Start.")
