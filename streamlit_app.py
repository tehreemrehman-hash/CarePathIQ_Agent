import streamlit as st
import google.generativeai as genai
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
import re
import time
import base64
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

# Nielsen's Definitions for Tooltips
HEURISTIC_DEFS = {
    "H1": "Visibility of system status: The design should always keep users informed about what is going on, through appropriate feedback within a reasonable amount of time.",
    "H2": "Match between system and real world: The design should speak the users' language. Use words, phrases, and concepts familiar to the user, rather than internal jargon.",
    "H3": "User control and freedom: Users often perform actions by mistake. They need a clearly marked 'emergency exit' to leave the unwanted action without having to go through an extended process.",
    "H4": "Consistency and standards: Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions.",
    "H5": "Error prevention: Good error messages are important, but the best designs carefully prevent problems from occurring in the first place.",
    "H6": "Recognition rather than recall: Minimize the user's memory load by making elements, actions, and options visible. The user should not have to remember information from one part of the interface to another.",
    "H7": "Flexibility and efficiency of use: Shortcuts — hidden from novice users — may speed up the interaction for the expert user such that the design can cater to both inexperienced and experienced users.",
    "H8": "Aesthetic and minimalist design: Interfaces should not contain information which is irrelevant or rarely needed. Every extra unit of information in an interface competes with the relevant units of information.",
    "H9": "Help users recognize, diagnose, and recover from errors: Error messages should be expressed in plain language (no error codes), precisely indicate the problem, and constructively suggest a solution.",
    "H10": "Help and documentation: It’s best if the system doesn’t need any additional explanation. However, it may be necessary to provide documentation to help users understand how to complete their tasks."
}

# ==========================================
# 2. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="CarePathIQ AI Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS: GLOBAL DARK BROWN THEME ---
st.markdown("""
<style>
    /* 1. ALL BUTTONS -> Dark Brown (#5D4037) */
    div.stButton > button {
        background-color: #5D4037 !important; 
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
    }
    div.stButton > button:hover {
        background-color: #3E2723 !important; /* Darker brown on hover */
        color: white !important;
    }
    div.stButton > button:active {
        background-color: #3E2723 !important;
        color: white !important;
    }

    /* 2. RADIO BUTTONS (The Little Circles) */
    /* Unchecked border */
    div[role="radiogroup"] label > div:first-child {
        border-color: #5D4037 !important;
    }
    /* Checked background - Target the inner circle */
    div[role="radiogroup"] label > div:first-child > div {
        background-color: #5D4037 !important;
    }
    /* Checked border */
    div[role="radiogroup"] label[data-checked="true"] > div:first-child {
        border-color: #5D4037 !important;
        background-color: #5D4037 !important;
    }

    /* 3. TOOLTIPS HOVER STYLE */
    .heuristic-title {
        cursor: help;
        font-weight: bold;
        color: #00695C; /* Keeping Teal for Text Contrast */
        text-decoration: underline dotted;
        font-size: 1.05em;
    }

    /* Headers */
    h1, h2, h3 { color: #00695C; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONFIG ---
with st.sidebar:
    st.title("AI Agent")
    st.divider()
    
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Use Google AI Studio Key")
    # Default to Flash for speed and stability
    model_choice = st.selectbox("AI Agent Model", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success(f"Connected: {model_choice}")
        
    st.divider()
    
    # --- DARK BROWN STATUS BOX ---
    current_phase = st.session_state.get('current_phase_label', 'Start')
    st.markdown(f"""
    <div style="
        background-color: #5D4037; 
        color: white; 
        padding: 10px; 
        border-radius: 5px; 
        text-align: center;
        font-weight: bold;
        font-size: 0.9em;">
        Current Phase: <br>
        <span style="font-size: 1.1em;">{current_phase}</span>
    </div>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "", "inclusion": "", "exclusion": "", "setting": "", "problem": "", "objectives": ""},
        "phase2": {"evidence": [], "pico_p": "", "pico_i": "", "pico_c": "", "pico_o": "", "mesh_query": ""},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}}, 
        "phase5": {"beta_email": "", "beta_content": "", "slides": "", "epic_csv": ""} 
    }

if "suggestions" not in st.session_state:
    st.session_state.suggestions = {}

if "current_phase_label" not in st.session_state:
    st.session_state.current_phase_label = "Phase 1: Scoping & Charter"
    
# Flags to control "Auto-Run" logic once per phase update
if "auto_run" not in st.session_state:
    st.session_state.auto_run = {
        "p2_pico": False,
        "p2_grade": False,
        "p3_logic": False,
        "p4_heuristics": False,
        "p5_all": False
    }

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def create_pdf_view_link(html_content, label="Open Charter in New Window"):
    """Generates a link to open HTML in new tab, simulating PDF."""
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" target="_blank" style="text-decoration:none; color:white; background-color:#5D4037; padding:10px 20px; border-radius:5px; font-weight:bold; display:inline-block;">{label}</a>'

def export_widget(content, filename, mime_type="text/plain", label="Download"):
    """Universal download widget with copyright."""
    final_content = content
    if "text" in mime_type or "csv" in mime_type:
        if isinstance(content, str):
            final_content = content + "\n\n" + COPYRIGHT_MD
    st.download_button(f"{label}", final_content, filename, mime_type)

def get_gemini_response(prompt, json_mode=False):
    """Robust AI caller with JSON cleaner."""
    if not gemini_api_key: return None
    try:
        model = genai.GenerativeModel(model_choice)
        # Relaxed safety for medical terms
        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
        time.sleep(1) # Prevent 429 errors
        response = model.generate_content(prompt, safety_settings=safety)
        text = response.text
        
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            # Robust JSON extraction via regex
            match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if match:
                text = match.group()
            return json.loads(text)
        return text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def search_pubmed(query):
    """Real PubMed API Search."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        search_params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': 5}
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            id_list = json.loads(response.read().decode()).get('esearchresult', {}).get('idlist', [])
        if not id_list: return []
        
        summary_params = {'db': 'pubmed', 'id': ','.join(id_list), 'retmode': 'json'}
        url = base_url + "esummary.fcgi?" + urllib.parse.urlencode(summary_params)
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode()).get('result', {})
        
        citations = []
        for uid in id_list:
            if uid in result:
                item = result[uid]
                title = item.get('title', 'No Title')
                author = item.get('authors', [{'name': 'Unknown'}])[0]['name']
                source = item.get('source', 'Journal')
                date = item.get('pubdate', 'No Date')[:4]
                citations.append({
                    "title": title,
                    "id": uid,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                    "citation": f"{title} by {author} ({source}, {date})",
                    "grade": "Un-graded" # Placeholder for AI
                })
        return citations
    except: return []

# ==========================================
# 4. MAIN UI
# ==========================================
st.title("CarePathIQ AI Agent")
st.markdown(f"### Intelligent Clinical Pathway Development")

if not gemini_api_key:
    # DARK BROWN SOLID WELCOME BOX
    st.markdown("""
    <div style="
        background-color: #5D4037; 
        padding: 15px; 
        border-radius: 5px; 
        color: white;
        margin-bottom: 20px;">
        <strong>Welcome.</strong> Please enter your <strong>Gemini API Key</strong> in the sidebar to activate the AI Agent.
    </div>
    """, unsafe_allow_html=True)
    st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
    st.stop()

phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", 
                  "Phase 2: Rapid Evidence Appraisal", 
                  "Phase 3: Decision Science", 
                  "Phase 4: Heuristic Evaluation", 
                  "Phase 5: Operationalize"], 
                 horizontal=True,
                 key="current_phase_label")

st.divider()

# ------------------------------------------
# PHASE 1: SCOPING
# ------------------------------------------
if "Phase 1" in phase:
    col1, col2 = st.columns([1, 2])
    with col1:
        # 1. CLINICAL CONDITION
        st.subheader("Clinical Condition")
        cond_input = st.text_input("Clinical Condition", value=st.session_state.data['phase1']['condition'], placeholder="e.g. Sepsis", label_visibility="collapsed")
        
        # 2. AUTO-POPULATE LOGIC
        if cond_input and cond_input != st.session_state.suggestions.get('condition_ref'):
            st.session_state.data['phase1']['condition'] = cond_input
            with st.spinner(f"AI Agent auto-populating suggestions..."):
                prompt = f"""
                Act as a Chief Medical Officer. User is building a pathway for: '{cond_input}'.
                Return a valid JSON object with these exact keys:
                - "inclusion": string
                - "exclusion": string
                - "setting": string
                - "problem": string
                - "objectives": list of strings
                """
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    st.session_state.suggestions = data
                    st.session_state.suggestions['condition_ref'] = cond_input
                    st.session_state.data['phase1']['inclusion'] = f"e.g. {data.get('inclusion', '')}"
                    st.session_state.data['phase1']['exclusion'] = f"e.g. {data.get('exclusion', '')}"
                    st.session_state.data['phase1']['setting'] = f"e.g. {data.get('setting', '')}"
                    st.session_state.data['phase1']['problem'] = f"e.g. {data.get('problem', '')}"
                    
                    # Handle objectives safely
                    objs = data.get('objectives', [])
                    if isinstance(objs, list):
                        obj_text = "\n".join([f"- {g}" for g in objs])
                    else:
                        obj_text = str(objs)
                        
                    st.session_state.data['phase1']['objectives'] = f"e.g. Suggested Objectives:\n{obj_text}"
                    st.rerun()
                else:
                    st.warning("AI Agent could not generate suggestions. Please try again or enter manually.")

        # 3. TARGET POPULATION
        st.subheader("Target Population")
        inc = st.text_area("Inclusion Criteria", value=st.session_state.data['phase1'].get('inclusion', ''), height=100)
        exc = st.text_area("Exclusion Criteria", value=st.session_state.data['phase1'].get('exclusion', ''), height=100)
        
        # 4. CARE SETTING
        st.subheader("Care Setting")
        setting = st.text_input("Care Setting", value=st.session_state.data['phase1']['setting'], label_visibility="collapsed")
        
        # 5. CLINICAL GAP
        st.subheader("Clinical Gap / Problem")
        prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'], label_visibility="collapsed")
        
        st.session_state.data['phase1'].update({"inclusion": inc, "exclusion": exc, "setting": setting, "problem": prob})

    with col2:
        st.subheader("Objectives")
        obj = st.text_area("Define Project Objectives", value=st.session_state.data['phase1']['objectives'], height=200, label_visibility="collapsed")
        st.session_state.data['phase1']['objectives'] = obj
        st.divider()
        
        if st.button("Generate Project Charter", type="primary"):
            if not cond_input:
                st.warning("Please enter a Clinical Condition first.")
            else:
                with st.spinner("AI Agent generating Charter..."):
                    prompt = f"Create a formal Project Charter (HTML). Condition: {cond_input}. Inclusion: {inc}. Exclusion: {exc}. Problem: {prob}. Objectives: {obj}. Return HTML."
                    charter_content = get_gemini_response(prompt)
                    
                    # Wrap for PDF-like view
                    full_html = f"""
                    <html>
                    <head>
                        <style>
                            body {{ font-family: 'Times New Roman', serif; padding: 40px; background-color: #525659; }}
                            .page {{ background: white; padding: 50px; width: 210mm; min-height: 297mm; margin: auto; box-shadow: 0 0 10px rgba(0,0,0,0.5); }}
                            h1 {{ color: #00695C; text-align: center; }}
                            h2 {{ color: #2E7D32; border-bottom: 2px solid #2E7D32; }}
                        </style>
                    </head>
                    <body>
                        <div class="page">
                            {charter_content}
                            <div style="margin-top: 50px; font-size: 0.8em; color: gray; text-align: center; border-top: 1px solid #ddd; padding-top: 10px;">
                                CarePathIQ © 2024 by Tehreem Rehman. Licensed under CC BY-SA 4.0.
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    st.markdown(create_pdf_view_link(full_html), unsafe_allow_html=True)

# ------------------------------------------
# PHASE 2: EVIDENCE
# ------------------------------------------
elif "Phase 2" in phase:
    st.subheader("Rapid Evidence Appraisal")
    
    # AUTO-RUN: PICO & MESH GENERATION
    p1_cond = st.session_state.data['phase1']['condition']
    if p1_cond and not st.session_state.auto_run.get("p2_pico", False):
        with st.spinner("AI Agent drafting PICO framework & Search Query..."):
            # 1. Generate PICO
            prompt_pico = f"""
            Act as a Medical Librarian. Define PICO for: '{p1_cond}'.
            Context: {st.session_state.data['phase1'].get('problem', '')}
            Return JSON: {{ "P": "...", "I": "...", "C": "...", "O": "..." }}
            """
            pico_data = get_gemini_response(prompt_pico, json_mode=True)
            if pico_data:
                st.session_state.data['phase2']['pico_p'] = pico_data.get("P", "")
                st.session_state.data['phase2']['pico_i'] = pico_data.get("I", "")
                st.session_state.data['phase2']['pico_c'] = pico_data.get("C", "")
                st.session_state.data['phase2']['pico_o'] = pico_data.get("O", "")
            
            # 2. Generate MeSH Query
            p = st.session_state.data['phase2']['pico_p']
            i = st.session_state.data['phase2']['pico_i']
            o = st.session_state.data['phase2']['pico_o']
            
            prompt_mesh = f"Create a PubMed search query using MeSH terms.\nCondition: {p1_cond}, P: {p}, I: {i}, O: {o}.\nOutput ONLY the raw query string."
            query = get_gemini_response(prompt_mesh)
            st.session_state.data['phase2']['mesh_query'] = query
            
            st.session_state.auto_run["p2_pico"] = True
            st.rerun()

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### PICO Framework")
        # Use session state values as defaults (populated by AI)
        p = st.text_input("P (Population)", value=st.session_state.data['phase2']['pico_p'])
        i = st.text_input("I (Intervention)", value=st.session_state.data['phase2']['pico_i'])
        c = st.text_input("C (Comparison)", value=st.session_state.data['phase2']['pico_c'])
        o = st.text_input("O (Outcome)", value=st.session_state.data['phase2']['pico_o'])
        st.session_state.data['phase2'].update({"pico_p": p, "pico_i": i, "pico_c": c, "pico_o": o})

        st.divider()
        if st.button("Regenerate MeSH Query", type="primary"):
            if not p1_cond:
                 st.error("Please define a condition in Phase 1.")
            else:
                with st.spinner("AI Agent building query..."):
                    prompt = f"Create a PubMed search query using MeSH terms.\nCondition: {p1_cond}, P: {p}, I: {i}, O: {o}.\nOutput ONLY the raw query string."
                    query = get_gemini_response(prompt)
                    st.session_state.data['phase2']['mesh_query'] = query
                    st.rerun()

    with col2:
        st.markdown("#### Literature Search")
        current_query = st.session_state.data['phase2'].get('mesh_query', '')
        search_q = st.text_area("Search Query", value=current_query, height=100)
        
        if st.button("Search PubMed"):
            if search_q:
                with st.spinner("Searching..."):
                    results = search_pubmed(search_q)
                    existing = {e['id'] for e in st.session_state.data['phase2']['evidence']}
                    for r in results:
                        if r['id'] not in existing:
                            st.session_state.data['phase2']['evidence'].append(r)
                            # New evidence added? Reset grading flag to trigger auto-analysis
                            st.session_state.auto_run["p2_grade"] = False 
        
        # AUTO-RUN: GRADE ANALYSIS (Dynamic)
        evidence_list = st.session_state.data['phase2']['evidence']
        if evidence_list and not st.session_state.auto_run["p2_grade"]:
             with st.spinner("AI Agent automatically analyzing GRADE scores..."):
                 titles = [f"ID {e['id']}: {e['title']}" for e in evidence_list]
                 prompt = f"Analyze citations. Assign GRADE score (High, Moderate, Low, Very Low).\nCitations: {json.dumps(titles)}\nReturn JSON object {{ID: Score}}."
                 grade_map = get_gemini_response(prompt, json_mode=True)
                 if isinstance(grade_map, dict):
                     for e in st.session_state.data['phase2']['evidence']:
                         if e['id'] in grade_map: e['grade'] = grade_map[e['id']]
                     st.session_state.auto_run["p2_grade"] = True
                     st.rerun()

        if evidence_list:
            # KEEP/MODIFY CONTROL
            st.markdown("""
            <div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">
                <strong>AI Agent Output:</strong> GRADE scores auto-populated. <br>
                <strong>Keep/Modify</strong> below, or click 'Clear Grades' for manual entry.
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Clear Grades for Manual Entry", type="primary"):
                for e in st.session_state.data['phase2']['evidence']: e['grade'] = "Un-graded"
                st.session_state.auto_run["p2_grade"] = True # Don't re-run immediately
                st.rerun()

            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            
            # GRADE TOOLTIP
            grade_help = """
            High (A): True effect lies close to estimate.
            Moderate (B): True effect likely close to estimate.
            Low (C): True effect may be substantially different.
            Very Low (D): True effect is likely substantially different.
            """
            
            # CONFIGURE 4 COLUMNS + GRADE
            edited_df = st.data_editor(df, column_config={
                "title": st.column_config.TextColumn("Title", width="large", disabled=True),
                "id": st.column_config.TextColumn("PubMed ID", disabled=True),
                "url": st.column_config.LinkColumn("URL", disabled=True),
                "citation": st.column_config.TextColumn("Citation", disabled=True),
                "grade": st.column_config.SelectboxColumn("Strength of Evidence", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], help=grade_help, required=True, width="medium")
            }, column_order=["title", "id", "url", "citation", "grade"], hide_index=True)
            
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            
            if not df.empty:
                csv = edited_df.to_csv(index=False)
                export_widget(csv, "evidence_table.csv", "text/csv", label="Download CSV")

# ------------------------------------------
# PHASE 3: LOGIC
# ------------------------------------------
elif "Phase 3" in phase:
    st.subheader("Decision Science")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # DARK BROWN INSTRUCTIONS
        st.markdown("""
        <div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 20px;">
            <strong>Instructions:</strong> Define the clinical steps of your pathway below.
        </div>
        """, unsafe_allow_html=True)
        
        # AUTO-RUN: LOGIC DRAFT
        cond = st.session_state.data['phase1']['condition']
        evidence_list = st.session_state.data['phase2']['evidence']
        nodes_exist = len(st.session_state.data['phase3']['nodes']) > 0
        
        if cond and not nodes_exist and not st.session_state.auto_run["p3_logic"]:
             with st.spinner("AI Agent drafting logic flow based on Phase 2 evidence..."):
                 ev_context = "\n".join([f"- ID {e['id']}: {e['title']}" for e in evidence_list[:5]])
                 prompt = f"""
                 Create a clinical logic flow for {cond}.
                 Available Evidence: {ev_context}
                 Return a JSON List of objects: [{{"type": "Start", "label": "Triage", "evidence": "ID 12345"}}]
                 - "type": Start, Decision, Process, End.
                 - "label": Short step description.
                 - "evidence": Select ID from Available Evidence if relevant, or "".
                 """
                 nodes = get_gemini_response(prompt, json_mode=True)
                 if isinstance(nodes, list):
                     st.session_state.data['phase3']['nodes'] = nodes
                     st.session_state.auto_run["p3_logic"] = True
                     st.rerun()

    with col2:
        if st.session_state.auto_run["p3_logic"]:
             st.markdown("""
            <div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">
                <strong>AI Agent Output:</strong> Logic draft generated. <br>
                <strong>Keep/Modify</strong> rows below, or click 'Clear Logic' to start fresh.
            </div>
            """, unsafe_allow_html=True)
             if st.button("Clear Logic for Manual Entry", type="primary"):
                 st.session_state.data['phase3']['nodes'] = []
                 st.session_state.auto_run["p3_logic"] = True
                 st.rerun()

        # DYNAMIC EVIDENCE DROPDOWN
        evidence_ids = [""] + [f"ID {e['id']}" for e in st.session_state.data['phase2']['evidence']]
        if not st.session_state.data['phase3']['nodes']:
             st.session_state.data['phase3']['nodes'] = [{"type":"Start", "label":"", "evidence":""}]
        
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        
        edited_nodes = st.data_editor(df_nodes, column_config={
            "type": st.column_config.SelectboxColumn("Type", options=["Start", "Decision", "Process", "Note", "End"], required=True),
            "label": st.column_config.TextColumn("Content", default=""), # Renamed "Content"
            "evidence": st.column_config.SelectboxColumn("Evidence", options=evidence_ids, width="medium")
        }, num_rows="dynamic", hide_index=True, use_container_width=True)
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# ------------------------------------------
# PHASE 4: VISUALIZATION
# ------------------------------------------
elif "Phase 4" in phase:
    st.subheader("Heuristic Evaluation")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        nodes = st.session_state.data['phase3']['nodes']
        if nodes:
            try:
                graph = graphviz.Digraph()
                graph.attr(rankdir='TB')
                for i, n in enumerate(nodes):
                    color = {'Start':'#D5E8D4', 'Decision':'#F8CECC', 'Process':'#FFF2CC', 'End':'#D5E8D4'}.get(n.get('type'), '#E0F2F1')
                    shape = {'Decision':'diamond', 'Start':'oval', 'End':'oval'}.get(n.get('type'), 'box')
                    graph.node(str(i), n.get('label', '?'), shape=shape, style='filled', fillcolor=color)
                    if i > 0: graph.edge(str(i-1), str(i))
                st.graphviz_chart(graph)
                
                # UNLOCKED DOWNLOADS
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                     try:
                         png_data = graph.pipe(format='png')
                         st.download_button("High-Res PNG", png_data, "pathway.png", "image/png", type="primary")
                     except: 
                         st.download_button("Download DOT (Fallback)", graph.source, "pathway.dot", "text/plain")
                with c_dl2:
                     try:
                         svg_data = graph.pipe(format='svg')
                         st.download_button("Visio-Ready SVG", svg_data, "pathway.svg", "image/svg+xml")
                     except: pass
            except Exception as e:
                st.error(f"Graph Error: {e}")

    with col2:
        st.markdown("#### Heuristic Evaluation")
        
        nodes = st.session_state.data['phase3']['nodes']
        if not nodes:
            st.info("Please define the pathway logic in Phase 3 (Decision Science) to enable Heuristic Evaluation.")
        
        # AUTO-RUN: HEURISTICS
        nodes_json = json.dumps(nodes)
        if nodes and not st.session_state.auto_run["p4_heuristics"]:
             with st.spinner("AI Agent analyzing against Nielsen's 10 Heuristics..."):
                 prompt = f"""
                 Analyze logic: {nodes_json}
                 Evaluate against Nielsen's 10 Usability Heuristics.
                 Return JSON {{H1: "e.g. [Insight]", ... H10: "e.g. [Insight]"}}.
                 Important: Start every insight with "e.g.".
                 """
                 risks = get_gemini_response(prompt, json_mode=True)
                 if isinstance(risks, dict): 
                     st.session_state.data['phase4']['heuristics_data'] = risks
                     st.session_state.auto_run["p4_heuristics"] = True
                     st.rerun()

        risks = st.session_state.data['phase4'].get('heuristics_data', {})
        if risks:
            st.markdown("""
            <div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">
                <strong>AI Agent Output:</strong> Analysis complete.
            </div>
            """, unsafe_allow_html=True)
            
            for k, v in risks.items():
                # TOOLTIP LOGIC
                def_text = HEURISTIC_DEFS.get(k, "No definition available.")
                st.markdown(f"""
                <div style="margin-bottom: 5px;">
                    <span class="heuristic-title" title="{def_text}">{k} Insight (Hover for Def)</span>
                </div>
                """, unsafe_allow_html=True)
                st.info(v)
            
            if st.button("Run New Analysis (Modify)", type="primary"):
                 st.session_state.auto_run["p4_heuristics"] = False
                 st.rerun()

# ------------------------------------------
# PHASE 5: OPERATIONALIZE
# ------------------------------------------
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    
    # AUTO-RUN ALL PHASE 5 CONTENT IF MISSING
    if not st.session_state.auto_run["p5_all"]:
        with st.spinner("AI Agent generating Guide, Slides, and EHR Specs (One-Time Setup)..."):
            cond = st.session_state.data['phase1']['condition']
            prob = st.session_state.data['phase1']['problem']
            goals = st.session_state.data['phase1']['objectives']
            # Default placeholder logic since email is no longer global
            nodes_json = json.dumps(st.session_state.data['phase3']['nodes'])
            
            if not st.session_state.data['phase5']['beta_content']:
                p_guide = f"Create a 'Beta Testing Interactive Guide' (HTML) for {cond}. Context: {prob}. Leave feedback link placeholder."
                st.session_state.data['phase5']['beta_content'] = get_gemini_response(p_guide)
            
            if not st.session_state.data['phase5']['slides']:
                p_slides = f"Create 5 educational slides (Markdown) for {cond}. Gap: {prob}. Goals: {goals}."
                st.session_state.data['phase5']['slides'] = get_gemini_response(p_slides)
            
            if not st.session_state.data['phase5']['epic_csv']:
                p_specs = f"Map nodes {nodes_json} to Epic/OPS tools. Return CSV string."
                st.session_state.data['phase5']['epic_csv'] = get_gemini_response(p_specs)
            
            st.session_state.auto_run["p5_all"] = True
            st.rerun()

    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("Beta Testing")
        beta_email_input = st.text_input("Enter email to receive beta feedback:")
        
        # CORRECTED BUTTON TEXT
        if st.button("Generate Interactive Guide"):
             with st.spinner("Updating guide..."):
                 cond = st.session_state.data['phase1']['condition']
                 prob = st.session_state.data['phase1']['problem']
                 st.session_state.data['phase5']['beta_content'] = get_gemini_response(f"Create Beta Guide (HTML) for {cond}. Context: {prob}. Create mailto link for {beta_email_input}.")
                 st.rerun()
        
        if st.session_state.data['phase5']['beta_content']:
             st.success(f"AI Agent Guide Generated.")
             export_widget(st.session_state.data['phase5']['beta_content'], "beta_guide.html", "text/html", label="Download Guide")

    with c2:
        st.subheader("Frontline Education")
        if st.session_state.data['phase5']['slides']:
             st.success(f"AI Agent Slides Generated.")
             export_widget(st.session_state.data['phase5']['slides'], "slides.md", label="Download Slides")

    with c3:
        st.subheader("EHR Integration")
        if st.session_state.data['phase5']['epic_csv']:
            st.success(f"AI Agent Specs Generated.")
            export_widget(st.session_state.data['phase5']['epic_csv'], "ops_specs.csv", "text/csv", label="Download CSV")
            
    if st.button("Regenerate All Phase 5 Outputs", type="primary"):
        st.session_state.auto_run["p5_all"] = False
        st.session_state.data['phase5'] = {"beta_email": "", "beta_content": "", "slides": "", "epic_csv": ""}
        st.rerun()

# ==========================================
# FOOTER
# ==========================================
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
