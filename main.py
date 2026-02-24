import streamlit as st
import re
import numpy as np
import pdfplumber
import docx
import plotly.graph_objects as go
import heapq

from textblob import TextBlob
from textblob import download_corpora


download_corpora.download_all()


st.set_page_config(
    page_title="PaperIQ",
    page_icon=" ",
    layout="wide"
)


st.markdown("""
<style>
.main { background-color: #f4f6fb; }

h1 { color: #1f4e79; font-weight: 700; }

.stTabs [data-baseweb="tab-list"] { gap: 24px; }

.stTabs [data-baseweb="tab"] {
    font-size: 16px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)



def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def clean_text(text):
    return re.sub(r'\n+', '\n', text).strip()



def extract_sections(text):
    lines = text.split('\n')
    sections = {}
    current_header = "Introduction / Preamble"
    current_content = []

    common_headers = [
        "ABSTRACT", "INTRODUCTION", "LITERATURE REVIEW",
        "METHODOLOGY", "RESULTS", "DISCUSSION",
        "CONCLUSION", "REFERENCES",
        "Abstract", "Introduction", "Methodology", "Conclusion"
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_header = False

        if re.match(r'^\d+(\.\d+)*\s+[A-Za-z]', line) and len(line) < 60:
            is_header = True
        elif line in common_headers or (line.isupper() and len(line) < 40 and len(line) > 3):
            is_header = True

        if is_header:
            if current_content:
                sections[current_header] = " ".join(current_content)
            current_header = line
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_header] = " ".join(current_content)

    return sections



def evaluate_abstract(text):
    sections = extract_sections(text)
    abstract_text = ""

    for key in sections:
        if "abstract" in key.lower():
            abstract_text = sections[key]
            break

    if not abstract_text:
        return {"error": "No Abstract section detected."}

    word_count = len(abstract_text.split())

    def keyword_check(keywords):
        return any(word in abstract_text.lower() for word in keywords)

    return {
        "word_count": word_count,
        "length_status": "Good Length" if 150 <= word_count <= 250 else "Length Issue ",
        "problem_present": keyword_check(["problem","challenge","issue","aim","objective"]),
        "method_present": keyword_check(["method","approach","proposed","model","algorithm"]),
        "result_present": keyword_check(["result","accuracy","performance","outcome"]),
        "conclusion_present": keyword_check(["conclude","suggest","demonstrate","indicate"])
    }



def calculate_readability(text):
    sentences = text.count('.') + text.count('!') + text.count('?')
    words = len(text.split())
    syllables = int(words * 1.5)

    if sentences == 0 or words == 0:
        return 0

    score = 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
    return max(0, min(100, score))



def analyze_full_document(text):
    blob = TextBlob(text)
    sentences = blob.sentences
    words = blob.words

    if len(sentences) == 0:
        return None

    word_count = len(words)
    sentence_count = len(sentences)
    avg_sentence_len = np.mean([len(s.words) for s in sentences])
    avg_word_len = np.mean([len(w) for w in words])
    sentiment = blob.sentiment.polarity

    language_score = min(100, (avg_sentence_len * 1.5) + (avg_word_len * 5))
    coherence_score = min(100, sentence_count * 0.5 + 40)
    reasoning_score = min(100, text.lower().count("because") * 5 + 30)

    complex_words = [w for w in words if len(w) > 6]
    lexical_score = min(100, (len(complex_words)/word_count)*300) if word_count else 0
    readability_score = calculate_readability(text)

    final_score = (
        language_score * 0.3 +
        coherence_score * 0.2 +
        reasoning_score * 0.2 +
        lexical_score * 0.15 +
        readability_score * 0.15
    )

    sections = extract_sections(text)

    return {
        "scores": {
            "Language": round(language_score,2),
            "Coherence": round(coherence_score,2),
            "Reasoning": round(reasoning_score,2),
            "Sophistication": round(lexical_score,2),
            "Readability": round(readability_score,2),
            "Composite": round(final_score,2)
        },
        "stats": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_len": round(avg_sentence_len,2),
            "avg_word_len": round(avg_word_len,2)
        },
        "sentiment": round(sentiment,2),
        "issues": [s.raw for s in sentences if len(s.words) > 30],
        "blob": blob,
        "sections": sections,
        "abstract_analysis": evaluate_abstract(text)
    }



st.title("PaperIQ")
st.caption("AI-Powered Academic Writing Insights")

uploaded_file = st.file_uploader("Upload your document", type=["pdf","docx","txt"])

if uploaded_file and st.button("Analyze Document", type="primary"):

    with st.spinner("Analyzing..."):

        if uploaded_file.name.endswith(".pdf"):
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.name.endswith(".docx"):
            text = extract_text_from_docx(uploaded_file)
        else:
            text = uploaded_file.getvalue().decode("utf-8")

        cleaned = clean_text(text)
        results = analyze_full_document(cleaned)

        if results:
            st.session_state["results"] = results


if "results" in st.session_state:

    res = st.session_state["results"]
    scores = res["scores"]
    stats = res["stats"]

    st.markdown("Analysis Results")

    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Composite", f"{scores['Composite']}/100")
    col2.metric("Language", f"{scores['Language']}/100")
    col3.metric("Coherence", f"{scores['Coherence']}/100")
    col4.metric("Reasoning", f"{scores['Reasoning']}/100")

    st.markdown("---")

    tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs([
        "Visualizations",
        "Section Summaries",
        "Issues",
        "Suggestions",
        "Detailed Metrics",
        "Sentiment",
        "Abstract Quality"
    ])

  
    with tab1:
        categories = ['Language','Coherence','Reasoning','Sophistication','Readability']
        values = [scores[c] for c in categories]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values,theta=categories,fill='toself'))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True,range=[0,100])),
            showlegend=False
        )
        st.plotly_chart(fig,use_container_width=True)

  
    with tab2:
        for title,content in res["sections"].items():
            with st.expander(f" {title}"):
                st.write(content[:1000])

    with tab3:
        if res["issues"]:
            for s in res["issues"]:
                st.warning(s)
        else:
            st.success("No long sentences detected!")

 
    with tab4:
        suggestions_map = {
            "very":"extremely",
            "bad":"adverse",
            "good":"beneficial",
            "show":"demonstrate",
            "big":"substantial"
        }
        text_lower = res["blob"].raw.lower()
        found=False
        for s,c in suggestions_map.items():
            if s in text_lower:
                st.info(f"Replace **{s}** with **{c}**")
                found=True
        if not found:
            st.success("Great vocabulary!")

 
    with tab5:
        st.write(f"**Words:** {stats['word_count']}")
        st.write(f"**Sentences:** {stats['sentence_count']}")
        st.write(f"**Avg Sentence Length:** {stats['avg_sentence_len']}")
        st.write(f"**Avg Word Length:** {stats['avg_word_len']}")


    with tab6:
        st.metric("Sentiment Score", res["sentiment"])
        if res["sentiment"] > 0:
            st.success("Positive Tone")
        else:
            st.warning("Neutral / Negative Tone")

    with tab7:
        st.subheader("Abstract Quality Evaluation")
        abstract_data = res["abstract_analysis"]

        if "error" in abstract_data:
            st.error(abstract_data["error"])
        else:
            st.write(f"**Word Count:** {abstract_data['word_count']}")
            st.write(f"**Length Status:** {abstract_data['length_status']}")
            st.write("### Structure Checks")
            st.write("Problem Statement:", "Found" if abstract_data["problem_present"] else "Not Found")
            st.write("Method Mentioned:", "Found" if abstract_data["method_present"] else "Not Found")
            st.write("Results Mentioned:", "Found" if abstract_data["result_present"] else "Not Found")
            st.write("Conclusion Mentioned:", "Found" if abstract_data["conclusion_present"] else "Not Found")
