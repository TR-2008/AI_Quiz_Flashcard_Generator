import streamlit as st
from common import gemini_text, extract_json, safe_error

st.set_page_config(page_title="AI Quiz & Flashcard Generator", page_icon="🧠", layout="wide")
st.title("🧠 AI Quiz & Flashcard Generator")
st.caption("Turn lesson notes into practice questions, explanations, and revision cards.")

with st.sidebar:
    st.header("Quiz settings")
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Mixed"])
    count = st.slider("Number of MCQs", 3, 20, 10)
    cards_count = st.slider("Flashcards", 0, 20, 8)
    language = st.selectbox("Output language", ["English", "Urdu", "Roman Urdu"])

notes = st.text_area("Paste lesson notes", height=260, placeholder="Paste a lesson, chapter summary, or class notes...")
if st.button("Generate study set", type="primary", disabled=len(notes.strip()) < 80):
    prompt = f"""
Create a high-quality study set based ONLY on the notes below.
Return valid JSON only, with this exact shape:
{{
 "title": "short title",
 "questions": [
  {{"question":"...", "options":{{"A":"...", "B":"...", "C":"...", "D":"..."}},
   "answer":"A", "explanation":"...", "topic":"..."}}
 ],
 "flashcards":[{{"front":"...", "back":"..."}}]
}}
Rules:
- Generate exactly {count} MCQs and exactly {cards_count} flashcards.
- Difficulty: {difficulty}. Language: {language}.
- Exactly four distinct options per question; answer must be A, B, C, or D.
- Only one correct answer. Explanations must be supported by the notes.
- Avoid duplicate questions and trick wording. Do not invent facts outside notes.
NOTES:
{notes[:18000]}
"""
    try:
        with st.spinner("Generating your study set with Gemini..."):
            data = extract_json(gemini_text(
                prompt,
                "You are a careful educational assessment writer. Follow the requested JSON schema exactly."
            ))
        if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
            raise ValueError("Unexpected study-set structure.")
        valid = []
        for q in data["questions"]:
            opts = q.get("options", {})
            ans = str(q.get("answer", "")).upper()
            if q.get("question") and isinstance(opts, dict) and len(opts) == 4 and ans in ["A","B","C","D"]:
                valid.append(q)
        if not valid:
            raise ValueError("No valid MCQs were returned. Try shorter or clearer notes.")
        st.session_state.study_set = {"title": data.get("title", "Study set"), "questions": valid,
                                      "flashcards": data.get("flashcards", [])}
        st.session_state.responses = {}
        st.session_state.submitted = False
    except Exception as e:
        st.error(f"Could not generate the study set. {safe_error(e)}")

study = st.session_state.get("study_set")
if study:
    st.subheader(study["title"])
    qs = study["questions"]
    with st.form("quiz_form"):
        for i, q in enumerate(qs):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            opts = q["options"]
            st.radio("Choose one:", list(opts.keys()), format_func=lambda k, o=opts: f"{k}. {o[k]}",
                     key=f"answer_{i}", index=None)
        submitted = st.form_submit_button("Check my answers")
    if submitted:
        score = 0
        for i, q in enumerate(qs):
            chosen = st.session_state.get(f"answer_{i}")
            if chosen == str(q["answer"]).upper():
                score += 1
        st.session_state.score = score
        st.session_state.submitted = True
    if st.session_state.get("submitted"):
        score = st.session_state.score
        st.metric("Your score", f"{score} / {len(qs)}", f"{score/len(qs)*100:.1f}%")
        for i, q in enumerate(qs):
            chosen = st.session_state.get(f"answer_{i}")
            correct = str(q["answer"]).upper()
            ok = chosen == correct
            st.markdown(f"**Q{i+1}: {'✅ Correct' if ok else '❌ Incorrect'}**")
            st.write(f"Your answer: {chosen or 'Not answered'} · Correct: {correct}. {q['options'].get(correct,'')}")
            st.info(q.get("explanation", "No explanation supplied."))
    if study.get("flashcards"):
        st.divider()
        st.subheader("Flashcards")
        for i, card in enumerate(study["flashcards"]):
            with st.expander(f"Card {i+1}: {card.get('front','Flashcard')}"):
                st.write(card.get("back", ""))
    st.download_button("Download study set (JSON)", data=__import__("json").dumps(study, ensure_ascii=False, indent=2),
                       file_name="study_set.json", mime="application/json")
else:
    st.info("Add at least 80 characters of lesson notes to begin.")
