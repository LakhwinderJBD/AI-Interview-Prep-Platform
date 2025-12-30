# --- PHASE A: FINAL REPORT, ANALYTICS & PERSISTENT REVIEWS ---
    if c >= len(data):
        st.header("📊 Final Master Analytics")
        
        # 1. Skill Radar Chart (Spider-Map)
        # ... [Keep your existing Radar Chart code here] ...
        # (For brevity, I'm focusing on the new Excel/Review logic below)

        st.divider()

        # 2. INDIVIDUAL QUESTION BREAKDOWN
        # ... [Keep your existing expander loop here] ...

        st.divider()

        # 3. PERSISTENT USER REVIEW SYSTEM (Excel/CSV Style)
        st.subheader("🌟 User Review & Quality Assurance")
        
        # Load existing reviews into a DataFrame
        review_file = "user_database.csv"
        if os.path.exists(review_file):
            df_reviews = pd.read_csv(review_file)
        else:
            df_reviews = pd.DataFrame(columns=["Timestamp", "Level", "Rating", "Comment", "Avg_Score"])

        with st.form("feedback_form"):
            u_rating = st.select_slider("Rate AI Accuracy (1-5)", options=[1, 2, 3, 4, 5], value=5)
            u_comments = st.text_area("Developer Note: What should I improve?")
            
            if st.form_submit_button("Submit Review"):
                # Calculate current session average score
                nums = re.findall(r'\d+', str(data))
                session_avg = sum([int(n) for n in nums[:len(data)]]) / len(data) if nums else 0
                
                # Create new entry
                new_data = pd.DataFrame({
                    "Timestamp": [pd.Timestamp.now()],
                    "Level": [st.session_state.level],
                    "Rating": [u_rating],
                    "Comment": [u_comments],
                    "Avg_Score": [session_avg]
                })
                
                # Append and Save
                df_reviews = pd.concat([df_reviews, new_data], ignore_index=True)
                df_reviews.to_csv(review_file, index=False)
                st.success("Review logged in the Master Database!")

        # 4. DATA EXPORT (For your Interviewer)
        st.write("### 📂 Developer Tools")
        col_dl, col_analysis = st.columns(2)
        
        with col_dl:
            # Allow you to download the Excel-ready file to your laptop
            csv_bytes = df_reviews.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Review Database (CSV/Excel)",
                data=csv_bytes,
                file_name="interview_prep_analytics.csv",
                mime="text/csv",
                help="Show this file to your interviewer to demonstrate your data collection."
            )

        with col_analysis:
            if st.button("Run AI Meta-Analysis"):
                if not df_reviews.empty:
                    all_text = " ".join(df_reviews['Comment'].astype(str).tolist())
                    pm_prompt = f"Analyze these user comments: {all_text}. Provide a 2-line product health report."
                    pm_report = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":pm_prompt}])
                    st.info(pm_report.choices[0].message.content)
                else:
                    st.warning("No data yet.")

        if st.button("🔄 Start New Session"):
            st.session_state.started = False
            st.rerun()
