if c >= len(data):
        # --- 📊 IMPROVED FINAL MASTER REPORT ---
        st.header("📊 Final Performance Report")
        st.markdown("Review your attempts and learn from the questions you skipped.")
        st.divider()

        for i, item in enumerate(data):
            # 1. Handle cases where the question was never even generated (clicked Finish early)
            if item["q"] is None:
                continue # Skip showing empty slots

            status = "✅ Attempted" if item['a'] else "❌ Skipped"
            with st.expander(f"Question {i+1} | {status}", expanded=True):
                st.write(f"**Question:** {item['q']}")
                
                if item['a']:
                    # Display evaluation if answered
                    if not item['eval']:
                        with st.spinner("Finalizing score..."):
                            e_sys = "Provide exactly 2 lines: Line 1 Score & Feedback. Line 2 Verified Ideal Answer."
                            res = client.chat.completions.create(
                                model="llama-3.1-8b-instant", 
                                messages=[{"role":"user","content":f"Q: {item['q']} A: {item['a']}\n{e_sys}"}]
                            )
                            item['eval'] = res.choices[0].message.content
                    st.info(item['eval'])
                else:
                    # IMPROVED: Generate a real Ideal Answer for skipped questions
                    st.warning("You skipped this question. Here is what you should have known:")
                    with st.spinner("Generating ideal answer..."):
                        # We use the LLM to generate a high-quality answer instead of just a search snippet
                        sol_sys = "You are an expert. Provide a concise, professional 2-sentence ideal answer for this question based on technical standards."
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": f"{sol_sys}\nQuestion: {item['q']}"}]
                        )
                        st.success(f"**Expert Solution:** {res.choices[0].message.content}")
        
        if st.button("🔄 Start New Practice Session"):
            st.session_state.started = False
            st.rerun()
