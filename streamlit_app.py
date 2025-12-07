import streamlit as st
import google.generativeai as genai
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
import re
import time
from io import BytesIO

# ==========================================
# 1. CONSTANTS & COPYRIGHT SETUP
# ==========================================
COPYRIGHT_HTML = """
<div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666;">
    <p>
        <a href="https://www.carepathiq.org" target="_blank" style="text-decoration:none; color:#4a4a4a; font-weight:bold;">CarePathIQ</a> 
        © 2024 by 
        <a href="https://www.tehreemrehman.com" target="_blank" style="text-decoration:none; color:#4a4a4a; font-weight:bold;">Tehreem Rehman</a> 
        is licensed under 
        <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" style="text-decoration:none; color:#4a4a4a;">CC BY-SA 4.0</a>
    </p>
</div>
"""

COPYRIGHT_MD = """
---
**© 2024 CarePathIQ by Tehreem Rehman.** Licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
"""

HEURISTIC_DEFS = {
    "H1": "Visibility of system status: The design should always keep users informed about what is going on.",
    "H2": "Match between system and real world: Speak the users' language, avoiding jargon.",
    "H3": "User control and freedom: Provide clearly marked 'emergency exits' to leave unwanted states.",
    "H4": "Consistency and standards: Users shouldn't have to wonder if different words mean the same thing.",
    "H5": "Error prevention: Good error messages are important, but preventing problems is better.",
    "H6": "Recognition rather than recall: Minimize memory load; making elements and options visible.",
    "H7": "Flexibility and efficiency of use: Accelerators for experts while remaining usable for novices.",
    "H8": "Aesthetic and minimalist design: Interfaces should not contain irrelevant information.",
    "H9": "Help users recognize, diagnose, and recover from errors: Error messages in plain language.",
    "H10": "Help and documentation: Provide concise, concrete documentation focused on user tasks."
}

# ==========================================
# 2. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="CarePathIQ AI Agent",
    page_icon="🏥",
    layout="wide"
)

st.markdown("""
<style>
/* === DARK BROWN PRIMARY BUTTONS === */
div.stButton > button[kind="primary"],
div.stDownloadButton > button {
    background-color: #5D4037 !important;
    color: white !important;
    border: none !important;
}
div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button:hover {
    background-color: #3E2723 !important;
    color: white !important;
}

/* === DARK BROWN RADIO BUTTONS === */
div[data-baseweb="radio"] > label > div:first-child {
    background-color: #5D4037 !important;
}
div[data-baseweb="radio"] > label > div:first-child > div {
    background-color: white !important;
}

/* === STREAMLIT DEFAULT BUTTON STYLING === */
div.stButton > button[kind="secondary"] {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #D3D3D3;
}
div.stButton > button[kind="secondary"]:hover {
    background-color: #F0F0F0;
    color: #000000;
    border-color: #A9A9A9;
}

/* === TYPOGRAPHY === */
h1, h2, h3 {
    color: #333;
}

/* === CONTAINERS === */
div[data-testid="stExpander"] {
    border: 1px solid #ddd;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. SIDEBAR (API Key + Email Tracking)
# ==========================================
with st.sidebar:
    st.title("🏥 CarePathIQ")
    st.markdown("**AI Agent for Clinical Pathway Development**")
    st.markdown("---")
    
    api_key = st.text_input("🔑 Enter Gemini API Key:", type="password", key="api_key_input")
    if api_key:
        genai.configure(api_key=api_key)
        st.success("✅ API Key Set")
    else:
        st.warning("⚠️ Please enter your API key to proceed.")
    
    st.markdown("---")
    st.markdown("### 📧 Email for Download Access")
    user_email = st.text_input("Email:", key="user_email", placeholder="you@example.com")
    if user_email:
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; text-align:center;">
            ✅ Email Saved: {user_email}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Enter your email above to unlock downloads.")
    
    st.markdown("---")
    st.markdown("""
    **How to Use:**
    1. Enter API key & email
    2. Choose your clinical condition
    3. The AI will automatically:
       - Suggest condition details
       - Retrieve and grade literature
       - Generate clinical logic
       - Analyze usability heuristics
       - Create deliverables
    """)

# ==========================================
# 4. SESSION STATE INITIALIZATION
# ==========================================
if "condition" not in st.session_state:
    st.session_state.condition = ""
if "condition_details" not in st.session_state:
    st.session_state.condition_details = ""
if "pubmed_results" not in st.session_state:
    st.session_state.pubmed_results = []
if "grade_table" not in st.session_state:
    st.session_state.grade_table = []
if "logic_draft" not in st.session_state:
    st.session_state.logic_draft = ""
if "heuristic_analysis" not in st.session_state:
    st.session_state.heuristic_analysis = ""
if "user_guide" not in st.session_state:
    st.session_state.user_guide = ""
if "slide_deck" not in st.session_state:
    st.session_state.slide_deck = ""
if "tech_specs" not in st.session_state:
    st.session_state.tech_specs = ""

# Auto-run flags
if "auto_run" not in st.session_state:
    st.session_state.auto_run = {
        "p2_grade": False,
        "p3_logic": False,
        "p4_heuristics": False,
        "p5_all": False
    }

# ==========================================
# 5. HELPER FUNCTIONS
# ==========================================
def export_widget(label, content, file_prefix, file_ext="txt"):
    """Display download button only if user_email is provided."""
    email = st.session_state.get("user_email", "").strip()
    if not email:
        st.warning("⚠️ Enter your email in the sidebar to download.")
        return
    
    if not content or not content.strip():
        st.info(f"ℹ️ No {label} content to download yet.")
        return
    
    filename = f"{file_prefix}.{file_ext}"
    st.download_button(
        label=f"📥 Download {label}",
        data=content,
        file_name=filename,
        mime="text/plain" if file_ext == "txt" else "text/markdown"
    )

def get_gemini_response(prompt, model_name="gemini-1.5-flash"):
    """Call Gemini API with rate limiting."""
    time.sleep(1)
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def search_pubmed(query, max_results=10):
    """Search PubMed using E-utilities API."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax={max_results}&retmode=json"
    try:
        with urllib.request.urlopen(search_url) as response:
            data = json.loads(response.read().decode())
            pmids = data.get("esearchresult", {}).get("idlist", [])
        
        if not pmids:
            return []
        
        fetch_url = f"{base_url}esummary.fcgi?db=pubmed&id={','.join(pmids)}&retmode=json"
        with urllib.request.urlopen(fetch_url) as response:
            fetch_data = json.loads(response.read().decode())
            articles = []
            for pmid in pmids:
                article = fetch_data.get("result", {}).get(pmid, {})
                title = article.get("title", "No title")
                authors = article.get("authors", [])
                author_names = ", ".join([a.get("name", "") for a in authors[:3]])
                pub_date = article.get("pubdate", "Unknown date")
                articles.append({
                    "PMID": pmid,
                    "Title": title,
                    "Authors": author_names,
                    "Date": pub_date
                })
            return articles
    except Exception as e:
        st.error(f"PubMed search error: {e}")
        return []

# ==========================================
# 6. WELCOME / LANDING PAGE
# ==========================================
if not st.session_state.condition:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #5D4037 0%, #3E2723 100%); 
                color: white; padding: 40px; border-radius: 10px; text-align: center;">
        <h1 style="color: white; margin-bottom: 20px;">🏥 CarePathIQ AI Agent</h1>
        <p style="font-size: 1.2em; margin-bottom: 30px;">
            Automated Clinical Pathway Development with AI-Powered Evidence Synthesis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### ✨ What This Agent Does")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **📚 Evidence Synthesis**
        - Auto-searches PubMed
        - GRADE quality scoring
        - Evidence tables
        """)
    with col2:
        st.markdown("""
        **🧠 Logic Generation**
        - Clinical decision trees
        - Rule-based pathways
        - Graphviz diagrams
        """)
    with col3:
        st.markdown("""
        **📋 Deliverables**
        - User guides
        - Slide decks
        - Technical specs
        """)
    
    st.markdown("---")
    st.markdown("### 🚀 Get Started")
    st.markdown("**Choose your clinical condition below to begin the automated workflow.**")

# ==========================================
# 7. PHASE 1: Condition Selection & Auto-Suggestions
# ==========================================
st.header("Phase 1: Clinical Condition")

condition_input = st.text_input(
    "Enter Clinical Condition:",
    value=st.session_state.condition,
    placeholder="e.g., Type 2 Diabetes, Hypertension, COPD",
    key="condition_input"
)

if st.button("Set Condition", type="primary"):
    if condition_input.strip():
        st.session_state.condition = condition_input.strip()
        st.session_state.condition_details = ""
        st.session_state.pubmed_results = []
        st.session_state.grade_table = []
        st.session_state.logic_draft = ""
        st.session_state.heuristic_analysis = ""
        st.session_state.user_guide = ""
        st.session_state.slide_deck = ""
        st.session_state.tech_specs = ""
        st.session_state.auto_run = {
            "p2_grade": False,
            "p3_logic": False,
            "p4_heuristics": False,
            "p5_all": False
        }
        st.rerun()
    else:
        st.warning("Please enter a condition name.")

if st.session_state.condition:
    st.success(f"**Selected:** {st.session_state.condition}")
    
    if not st.session_state.condition_details and st.session_state.get("api_key_input"):
        with st.spinner("🤖 AI Agent generating condition suggestions..."):
            prompt = f"""You are a clinical informatics expert. For the condition '{st.session_state.condition}', provide:
1. A brief clinical description (2-3 sentences)
2. Key diagnostic criteria (3-5 bullet points)
3. Common treatment approaches (3-5 bullet points)
4. Important clinical considerations (2-3 bullet points)

Format as clear, professional markdown."""
            st.session_state.condition_details = get_gemini_response(prompt, "gemini-1.5-flash")
    
    if st.session_state.condition_details:
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; margin-bottom:10px;">
            ✅ AI Agent Output: Condition Details
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.condition_details)
        export_widget("Condition Details", st.session_state.condition_details, "condition_details", "md")

# ==========================================
# 8. PHASE 2: Literature Search & Auto-GRADE
# ==========================================
if st.session_state.condition:
    st.markdown("---")
    st.header("Phase 2: Literature Review")
    
    search_query = st.text_input(
        "PubMed Search Query:",
        value=f"{st.session_state.condition} clinical pathway",
        key="pubmed_query"
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔍 Search PubMed", type="primary"):
            with st.spinner("Searching PubMed..."):
                results = search_pubmed(search_query, max_results=10)
                st.session_state.pubmed_results = results
                st.session_state.auto_run["p2_grade"] = False
    
    with col2:
        if st.session_state.grade_table and st.button("🗑️ Clear Grades"):
            st.session_state.grade_table = []
            st.session_state.auto_run["p2_grade"] = False
            st.rerun()
    
    if st.session_state.pubmed_results:
        st.success(f"Found {len(st.session_state.pubmed_results)} articles")
        df = pd.DataFrame(st.session_state.pubmed_results)
        st.dataframe(df, use_container_width=True)
        
        if not st.session_state.auto_run["p2_grade"] and st.session_state.get("api_key_input"):
            with st.spinner("🤖 AI Agent performing GRADE analysis..."):
                titles = "\n".join([f"{i+1}. {a['Title']}" for i, a in enumerate(st.session_state.pubmed_results)])
                prompt = f"""As a clinical evidence expert, assign GRADE quality ratings (High/Moderate/Low/Very Low) to these articles:

{titles}

For each article, provide:
- Study design (RCT, observational, review, etc.)
- GRADE rating with brief justification
- Key limitation (if any)

Format as a structured table with columns: Article#, Study Design, GRADE Rating, Justification, Limitations"""
                grade_response = get_gemini_response(prompt, "gemini-1.5-pro")
                st.session_state.grade_table = grade_response
                st.session_state.auto_run["p2_grade"] = True
        
        if st.session_state.grade_table:
            st.markdown(f"""
            <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; margin-bottom:10px;">
                ✅ AI Agent Output: GRADE Analysis
            </div>
            """, unsafe_allow_html=True)
            st.markdown(st.session_state.grade_table)
            export_widget("GRADE Analysis", st.session_state.grade_table, "grade_analysis", "md")

# ==========================================
# 9. PHASE 3: Logic Generation (Auto-Run)
# ==========================================
if st.session_state.condition:
    st.markdown("---")
    st.header("Phase 3: Clinical Logic")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**The AI will automatically generate clinical decision logic for your pathway.**")
    with col2:
        if st.session_state.logic_draft and st.button("🗑️ Clear Logic"):
            st.session_state.logic_draft = ""
            st.session_state.auto_run["p3_logic"] = False
            st.rerun()
    
    if not st.session_state.auto_run["p3_logic"] and st.session_state.get("api_key_input"):
        with st.spinner("🤖 AI Agent generating clinical logic..."):
            prompt = f"""Create a detailed clinical decision logic for {st.session_state.condition} pathway.

Include:
1. Initial Assessment (symptoms, vitals, labs)
2. Decision Points (if-then rules)
3. Treatment Pathways (step-by-step)
4. Follow-up Protocols

Format as clear, structured markdown with decision trees where applicable."""
            st.session_state.logic_draft = get_gemini_response(prompt, "gemini-1.5-pro")
            st.session_state.auto_run["p3_logic"] = True
    
    if st.session_state.logic_draft:
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; margin-bottom:10px;">
            ✅ AI Agent Output: Clinical Logic
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.logic_draft)
        export_widget("Clinical Logic", st.session_state.logic_draft, "clinical_logic", "md")
        
        st.subheader("📊 Graphviz Diagram")
        dot_code = st.text_area(
            "Edit DOT code (Graphviz):",
            value="""digraph clinical_pathway {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    Start [label="Patient Presentation", shape=ellipse, style=filled, fillcolor=lightblue];
    Assess [label="Initial Assessment"];
    Decision [label="Diagnostic Criteria Met?", shape=diamond, style=filled, fillcolor=lightyellow];
    Treat [label="Initiate Treatment"];
    Monitor [label="Monitor & Follow-up"];
    End [label="Pathway Complete", shape=ellipse, style=filled, fillcolor=lightgreen];
    
    Start -> Assess;
    Assess -> Decision;
    Decision -> Treat [label="Yes"];
    Decision -> End [label="No"];
    Treat -> Monitor;
    Monitor -> End;
}""",
            height=200,
            key="dot_editor"
        )
        
        try:
            graph = graphviz.Source(dot_code)
            st.graphviz_chart(graph)
            
            email = st.session_state.get("user_email", "").strip()
            if email:
                st.download_button(
                    label="📥 Download DOT File",
                    data=dot_code,
                    file_name="pathway_diagram.dot",
                    mime="text/plain"
                )
                try:
                    png_data = graph.pipe(format='png')
                    st.download_button(
                        label="📥 Download PNG",
                        data=png_data,
                        file_name="pathway_diagram.png",
                        mime="image/png"
                    )
                except Exception:
                    st.info("ℹ️ PNG generation unavailable. Download DOT file instead.")
            else:
                st.warning("⚠️ Enter email in sidebar to download diagram.")
        except Exception as e:
            st.error(f"Graphviz error: {e}")

# ==========================================
# 10. PHASE 4: Heuristic Analysis (Auto-Run)
# ==========================================
if st.session_state.condition:
    st.markdown("---")
    st.header("Phase 4: Usability Heuristics")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**AI will analyze pathway usability using Nielsen's 10 heuristics.**")
    with col2:
        if st.session_state.heuristic_analysis and st.button("🔄 Run New Analysis"):
            st.session_state.heuristic_analysis = ""
            st.session_state.auto_run["p4_heuristics"] = False
            st.rerun()
    
    with st.expander("📖 View Heuristic Definitions"):
        for h_id, h_def in HEURISTIC_DEFS.items():
            st.markdown(f"**{h_id}:** {h_def}")
    
    if not st.session_state.auto_run["p4_heuristics"] and st.session_state.get("api_key_input"):
        with st.spinner("🤖 AI Agent analyzing heuristics..."):
            heuristics_text = "\n".join([f"{k}: {v}" for k, v in HEURISTIC_DEFS.items()])
            prompt = f"""Analyze the clinical pathway for {st.session_state.condition} using these Nielsen heuristics:

{heuristics_text}

For each heuristic:
1. Score: Rate 1-5 (1=poor, 5=excellent)
2. Assessment: How well does the pathway address this?
3. Recommendations: Specific improvements

Format as a structured analysis with clear sections."""
            st.session_state.heuristic_analysis = get_gemini_response(prompt, "gemini-1.5-pro")
            st.session_state.auto_run["p4_heuristics"] = True
    
    if st.session_state.heuristic_analysis:
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; margin-bottom:10px;">
            ✅ AI Agent Output: Heuristic Analysis
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.heuristic_analysis)
        export_widget("Heuristic Analysis", st.session_state.heuristic_analysis, "heuristic_analysis", "md")

# ==========================================
# 11. PHASE 5: Final Deliverables (Auto-Run All)
# ==========================================
if st.session_state.condition:
    st.markdown("---")
    st.header("Phase 5: Final Deliverables")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**AI will generate all final deliverables automatically.**")
    with col2:
        if st.session_state.user_guide and st.button("🔄 Regenerate All"):
            st.session_state.user_guide = ""
            st.session_state.slide_deck = ""
            st.session_state.tech_specs = ""
            st.session_state.auto_run["p5_all"] = False
            st.rerun()
    
    if not st.session_state.auto_run["p5_all"] and st.session_state.get("api_key_input"):
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; margin-bottom:10px;">
            🤖 AI Agent generating all deliverables...
        </div>
        """, unsafe_allow_html=True)
        
        with st.spinner("Generating User Guide..."):
            prompt = f"""Create a comprehensive user guide for the {st.session_state.condition} clinical pathway.

Include:
1. Introduction & Purpose
2. Step-by-Step Usage Instructions
3. Clinical Decision Support
4. Common Scenarios & Examples
5. Troubleshooting & FAQs

Format as a professional, easy-to-follow document."""
            st.session_state.user_guide = get_gemini_response(prompt, "gemini-1.5-pro")
        
        with st.spinner("Generating Slide Deck..."):
            prompt = f"""Create a 10-slide presentation outline for the {st.session_state.condition} pathway.

Each slide should have:
- Title
- 3-5 bullet points
- Speaker notes (optional)

Cover: Overview, Evidence Base, Clinical Logic, Implementation, Outcomes"""
            st.session_state.slide_deck = get_gemini_response(prompt, "gemini-1.5-flash")
        
        with st.spinner("Generating Technical Specs..."):
            prompt = f"""Create technical implementation specifications for the {st.session_state.condition} pathway system.

Include:
1. System Architecture
2. Data Models & Schema
3. API Endpoints
4. Integration Requirements
5. Security & Compliance
6. Testing Strategy

Format as detailed technical documentation."""
            st.session_state.tech_specs = get_gemini_response(prompt, "gemini-1.5-pro")
        
        st.session_state.auto_run["p5_all"] = True
        st.rerun()
    
    if st.session_state.user_guide:
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:10px; border-radius:5px; margin-bottom:10px;">
            ✅ AI Agent Output: All Deliverables Generated
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📖 User Guide", "📊 Slide Deck", "⚙️ Technical Specs"])
        
        with tab1:
            st.markdown(st.session_state.user_guide)
            export_widget("User Guide", st.session_state.user_guide, "user_guide", "md")
        
        with tab2:
            st.markdown(st.session_state.slide_deck)
            export_widget("Slide Deck", st.session_state.slide_deck, "slide_deck", "md")
        
        with tab3:
            st.markdown(st.session_state.tech_specs)
            export_widget("Technical Specs", st.session_state.tech_specs, "tech_specs", "md")

# ==========================================
# 12. FOOTER
# ==========================================
st.markdown("---")
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
