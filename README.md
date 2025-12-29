# AI Interview Preparation Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_svg.svg)](YOUR_STREAMLIT_LINK_HERE)

An AI-powered interview simulation tool designed to help students and professionals prepare for **Data Science** and **Machine Learning** roles. This platform uses Retrieval-Augmented Generation (RAG) to allow users to practice using their own study materials or company-specific question banks.

## Core Features

- **Document-Only Mode (RAG):** Upload PDF notes, and the AI asks questions *only* from the provided content—ensuring zero hallucinations and 1:1 syllabus matching.
- **Adaptive Difficulty:** Toggle between **Internship** (mentorship style with foundational hints) and **Job** (strict style with logic-based follow-ups).
- **Intelligent Navigation:** Move back and forth between questions, skip difficult ones, and revisit them later—all while maintaining session state.
- **Instant Evaluation:** Get a Score (1-10), technical feedback, and an "Ideal Answer" immediately after submitting a response.
- **Hint System:** Context-aware nudges that adapt to your target level (conceptual for interns, architectural for job-seekers).

## Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/) (Web Interface)
- **AI Engine:** [Groq Cloud API](https://groq.com/) (Llama 3.1 8B Instant)
- **PDF Processing:** PyPDF2
- **Language:** Python 3.x

## Getting Started

1. **Obtain an API Key:** Get a free key from [Groq Cloud](https://console.groq.com/).
2. **Launch the App:** Visit the [Live Demo](YOUR_STREAMLIT_LINK_HERE).
3. **Setup:** 
   - Enter your API Key in the sidebar.
   - Upload a PDF containing study material or sample questions.
   - Select your target level and question count.
4. **Practice:** Answer questions and receive professional grading!

## Future Roadmap

- **Phase 2:** Integration of Speech-to-Text (Voice Interviews) and Resume-based question generation.
- **Phase 3:** Multi-document support and Vector Database integration (ChromaDB) for larger knowledge bases.
- **Phase 4:** AI Interviewer Avatar for a more realistic experience.

---
*Developed as a portfolio project to demonstrate practical applications of LLMs and RAG in EdTech.*
