# 🎯 AI Career Master: Intelligent Interview Simulator

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_svg.svg)](https://ai-interview-prep-platform-cwps9szn55ybmqtga6wden.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Groq AI](https://img.shields.io/badge/AI-Groq%20LPU-orange)](https://groq.com/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-green)](https://supabase.com/)

**The Problem:** Most interview prep tools are generic. They ask the same basic questions regardless of your actual experience or the specific syllabus you studied.

**The Solution:** **AI Career Master** is a personalized, RAG-powered (Retrieval-Augmented Generation) platform. It "reads" your specific study notes and your unique resume to simulate a high-pressure technical interview tailored exactly to you.

---

## 🚀 One-Minute Overview: How it Works

1.  **Context Injection:** You upload your PDF notes (Syllabus) and your Resume.
2.  **Hybrid Questioning:** The AI cross-references your projects with technical theory. (e.g., *"I see you built an Ocular Disease model; how does the Cross-Entropy loss mentioned in your notes apply to that specific dataset?"*)
3.  **Adaptive Intelligence:** 
    *   **Internship Mode:** 50/50 split between fundamental concepts and project basics.
    *   **Job Mode:** Focuses 70% on deep architecture, scalability, and project trade-offs.
4.  **Instant Feedback:** Every response receives a 1-10 score, technical feedback, and a 2-line "Interviewer's Ideal Answer."
5.  **Cloud Persistence:** Your progress and feedback are saved permanently to a cloud database (Supabase) for long-term tracking.

---

## 🛠️ The Technical Powerhouse (Tech Stack)

| Layer | Technology | Why? |
| :--- | :--- | :--- |
| **Brain** | **Llama 3.1 8B** | State-of-the-art reasoning for technical evaluation. |
| **Inference** | **Groq LPU™** | Ultra-low latency (<0.5s response) for a real-time feel. |
| **RAG Pipeline** | **PyPDF2 / Python** | Custom logic to parse and route context from multiple PDFs. |
| **Frontend** | **Streamlit** | High-performance reactive web interface. |
| **Database** | **Supabase (Postgres)** | Permanent, secure cloud storage for user reviews and metrics. |
| **Notation** | **LaTeX / Markdown** | Professional rendering of complex Math/ML formulas. |

---

## 🧠 Key Engineering Challenges Solved

### 1. Semantic De-Duplication (The Repetition Fix)
Implemented a **Negative Constraint Pipeline**. By injecting the current session history back into the system prompt as a "Forbidden List," the AI is forced to move to new technical sub-topics, ensuring 100% unique questions in every session.

### 2. Context Routing & Weighting
Developed a **career-level weighting algorithm**. The system dynamically adjusts the probability of "Theory vs. Applied" questions based on the user's goal, simulating real-world hiring rubrics used by Tier-1 tech firms.

### 3. Graceful UI/UX Degradation
Designed the platform with **Standard Math Notation (LaTeX)**. Integrated strict formatting guards to prevent common LLM "chatter," ensuring the interviewer stays in character and the text remains horizontal and readable across devices.

---

## ⚙️ Installation & Usage

1. **Get an API Key:** Sign up at [Groq Cloud](https://console.groq.com/).
2. **Environment Setup:** 
   - Create a `.streamlit/secrets.toml` file.
   - Add your `GROQ_API_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY`.
3. **Run the App:**
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
