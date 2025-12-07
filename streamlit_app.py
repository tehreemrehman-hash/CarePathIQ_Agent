import streamlit as st
import google.generativeai as genai
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
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

# Nielsen's Heuristics Definitions for Tooltips
HEURISTIC_DEFS = {
    "H1": "Visibility of system status: The design should always keep users informed about what is going on, through appropriate feedback within a reasonable amount of time.",
    "H2": "Match between system and the real world: The design should speak the users' language. Use words, phrases, and concepts familiar to the user, rather than internal jargon.",
    "H3": "User control and freedom: Users often perform actions by mistake. They need a clearly marked 'emergency exit' to leave the unwanted action without having to go through an extended process.",
    "H4": "Consistency and standards: Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions.",
    "H5": "Error prevention: Good error messages are important, but the best designs carefully prevent problems from occurring in the first place.",
    "H6": "Recognition rather than recall: Minimize the user's memory load by making elements, actions, and options visible. The user should not have to remember information from one part of the interface to another.",
    "H7": "Flexibility and efficiency of use: Shortcuts — hidden from novice users — may speed up the interaction for the expert user such that the design can cater to both inexperienced and experienced users.",
    "H8": "Aesthetic and minimalist design: Interfaces should not contain information which is irrelevant or rarely needed. Every extra unit of information in an interface competes with the relevant units of information.",
    "H9": "Help users recognize, diagnose, and recover from errors: Error messages should be expressed in plain language (no error codes), precisely indicate the problem, and constructively suggest a solution.",
    "H10": "Help and documentation: It's best if the system doesn't need any additional explanation. However, it may be necessary to provide documentation to help users understand how to complete their tasks."
}

# ==========================================
# 2. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="CarePathIQ AI Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR MINT & BROWN THEME ---
st.markdown("""
<style>
    /* 1. DEFAULT BUTTONS (Mint Green) */
    div.stButton > button {
        background-color: #4DB6AC; 
        color: white;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #26A69A;
        color: white;
    }

    /* 2. PRIMARY BUTTONS (Dark Brown) */
    div.stButton > button[kind="primary"] {
        background-color: #5D4037 !important;
        color: white !important;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #3E2723 !important;
    }

    /* 3. Phase Selection Radio Buttons (Mint Highlight) */
    div[role="radiogroup"] > label > div:first-child {
        background-color: #E0F2F1;
    }
    
    /* Tooltip Hover Style for Heuristics */
    .heuristic-title {
        cursor: help;
        font-weight: bold;
        color: #00695C;
        text-decoration: underline dotted;
        font-size: 1.05em;
    }

    /* Headers */
    h1, h2, h3 { color: #00695C; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONFIG & EMAIL TRACKING ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
    st.title("AI Agent")
    st.divider()
    
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Use Google AI Studio Key")
    model_choice = st.selectbox("AI Model", ["gemini-2.5-pro", "gemini-2.5-flash"], index=0)
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success(f"✅ Connected: {model_choice}")
    else:
        st.warning("⚠️ Enter API Key to activate.")
        
    st.divider()
    
    # --- EMAIL TRACKING ---
    st.markdown("### 📧 User Tracking")
    st.caption("Enter email to unlock downloads.")
    user_email = st.text_input("Your Email Address", placeholder="clinician@hospital.org")
    
    if user_email and "@" in user_email:
        st.session_state['user_email'] = user_email
        st.success("✅ Access Granted")
    else:
        st.session_state['user_email'] = None
        st.warning("🔒 Downloads Locked")

    st.divider()
    
    # --- MINT "CURRENT PHASE" BOX ---
    current_phase = st.session_state.get('current_phase_label', 'Start')
    st.markdown(f"""
    <div style="
        background-color: #E0F2F1; 
        color: #00695C; 
        padding: 10px; 
        border-radius: 5px; 
        border-left: 5px solid #4DB6AC;
        font-weight: bold;
        font-size: 0.9em;">
        Current Phase: <br>
        <span style="font-size: 1.1em; color: #004D40;">{current_phase}</span>
    </div>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "", "population": "", "setting": "", "problem": "", "objectives": ""},
        "phase2": {"evidence": [], "pico_p": "", "pico_i": "", "pico_c": "", "pico_o": "", "mesh_query": ""},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}}, 
        "phase5": {"beta_email": "", "beta_content": "", "slides": "", "epic_csv": ""} 
    }

if "suggestions" not in st.session_state:
    st.session_state.suggestions = {}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def export_widget(content, filename, mime_type="text/plain", label="Download"):
    """
    Standardized export widget that handles Copyright + Email Gating
    """
    # 1. Append Copyright
    final_content = content
    if "text" in mime_type or "csv" in mime_type:
        if isinstance(content, str):
            final_content = content + "\n\n" + COPYRIGHT_MD
    
    # 2. Check Email Gate
    if not st.session_state.get('user_email'):
        st.info(f"🔒 Enter email in sidebar to download {filename}")
        return

    # 3. Download Button Only
    st.download_button(f"📥 {label}", final_content, filename, mime_type)

def get_gemini_response(prompt, json_mode=False):
    if not gemini_api_key: return None
    try:
        model = genai.GenerativeModel(model_choice)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(prompt, safety_settings=safety_settings)
        text = response.text
        
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            try:
                start_list = text.find('[')
                end_list = text.rfind(']') + 1
                start_obj = text.find('{')
                end_obj = text.rfind('}') + 1
                
                if start_list != -1 and (start_obj == -1 or start_list < start_obj):
                    text = text[start_list:end_list]
                elif start_obj != -1:
                    text = text[start_obj:end_obj]
                return json.loads(text)
            except json.JSONDecodeError:
                return [] if '[' in text else {}
        return text
    except Exception as e:
        st.error(f"AI Error ({model_choice}): {e}")
        return None


def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        search_params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': 5}
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            id_list = data.get('esearchresult', {}).get('idlist', [])
        if not id_list: return []
        
        summary_params = {'db': 'pubmed', 'id': ','.join(id_list), 'retmode': 'json'}
        url = base_url + "esummary.fcgi?" + urllib.parse.urlencode(summary_params)
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode()).get('result', {})
        
        citations = []
        for uid in id_list:
            if uid in result:
                item = result[uid]
                citations.append({
                    "title": item.get('title', 'No Title'),
                    "author": item.get('authors', [{'name': 'Unknown'}])[0]['name'],
                    "source": item.get('source', 'Journal'),
                    "date": item.get('pubdate', 'No Date')[:4],
                    "id": uid,
                    "grade": "Un-graded"
                })
        return citations
    except Exception as e:
        st.error(f"PubMed Error: {e}")
        return []

# ==========================================
# 4. MAIN UI
# ==========================================
st.title("CarePathIQ AI Agent")
st.markdown(f"### Intelligent Clinical Pathway Development")

if not gemini_api_key:
    st.info("👋 Welcome. Please enter your Gemini API Key in the sidebar.")
    st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
    st.stop()

phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", 
                  "Phase 2: Evidence & Mesh", 
                  "Phase 3: Logic Construction",
                  "Phase 4: Visualization & Testing",
                  "Phase 5: Operationalize"], 
                 horizontal=True)

st.session_state.current_phase_label = phase
st.divider()

# ------------------------------------------
# PHASE 1: SCOPING
# ------------------------------------------
if "Phase 1" in phase:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Project Parameters")
        cond_input = st.text_input("Target Condition", value=st.session_state.data['phase1']['condition'], placeholder="e.g. Sepsis")
        
        if cond_input and cond_input != st.session_state.suggestions.get('condition_ref'):
            st.session_state.data['phase1']['condition'] = cond_input
            with st.spinner(f"🤖 Auto-populating suggestions for '{cond_input}'..."):
                prompt = f"""
                Act as a Chief Medical Officer. User is building a pathway for: '{cond_input}'.
                Return JSON with realistic clinical suggestions:
                - population: (String)
                - setting: (String)
                - problem: (String)
                - objectives: (List of 3 strings, SMART goals)
                """
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    st.session_state.suggestions = data
                    st.session_state.suggestions['condition_ref'] = cond_input
                    st.session_state.data['phase1']['population'] = f"e.g. {data.get('population', '')}"
                    st.session_state.data['phase1']['setting'] = f"e.g. {data.get('setting', '')}"
                    st.session_state.data['phase1']['problem'] = f"e.g. {data.get('problem', '')}"
                    goals = data.get('objectives', [])
                    formatted_goals = "\n".join([f"- {g}" for g in goals])
                    st.session_state.data['phase1']['objectives'] = f"e.g. Suggested Objectives:\n{formatted_goals}"
                    st.rerun()

        pop = st.text_input("Target Population", value=st.session_state.data['phase1']['population'])
        setting = st.text_input("Care Setting", value=st.session_state.data['phase1']['setting'])
        prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'])

        st.session_state.data['phase1'].update({"population": pop, "setting": setting, "problem": prob, "condition": cond_input})

    with col2:
        st.subheader("Objectives")
        obj = st.text_area("Define Project Objectives", value=st.session_state.data['phase1']['objectives'], height=200)
        st.session_state.data['phase1']['objectives'] = obj
        
        st.divider()
        if st.button("Generate Project Charter", type="primary"):
            prompt = f"Create a formal Project Charter (Markdown).\nCondition: {cond_input}\nPopulation: {pop}\nSetting: {setting}\nProblem: {prob}\nObjectives: {obj}"
            response = get_gemini_response(prompt)
            if response:
                export_widget(response, "charter.md", label="Download Charter")

# ------------------------------------------
# PHASE 2: EVIDENCE
# ------------------------------------------
elif "Phase 2" in phase:
    st.subheader("Dynamic Evidence Synthesis")
    col1, col2 = st.columns([1, 2])
    p1_cond = st.session_state.data['phase1']['condition']
    
    with col1:
        st.markdown("#### PICO Framework")
        p = st.text_input("P (Population)", value=st.session_state.data['phase1']['population'])
        i = st.text_input("I (Intervention)", value="Standardized Pathway")
        c = st.text_input("C (Comparison)", value="Current Variation")
        o = st.text_input("O (Outcome)", value="Reduced Mortality / LOS")
        st.session_state.data['phase2'].update({"pico_p": p, "pico_i": i, "pico_c": c, "pico_o": o})

        st.divider()
        if st.button("Generate MeSH Query", type="primary"):
            if not p1_cond:
                 st.error("Please define a condition in Phase 1.")
            else:
                with st.spinner("Building query..."):
                    prompt = f"Create a PubMed search query using MeSH terms.\nCondition: {p1_cond}, P: {p}, I: {i}, O: {o}.\nOutput ONLY the raw query string."
                    query = get_gemini_response(prompt)
                    st.session_state.data['phase2']['mesh_query'] = query
                    st.rerun()

    with col2:
        st.markdown("#### Literature Search")
        current_query = st.session_state.data['phase2'].get('mesh_query', '')
        search_q = st.text_area("Search Query", value=current_query, height=100)
        
        col_search, col_ai_grade = st.columns([1, 1.5])
        with col_search:
            if st.button("Search PubMed"):
                if search_q:
                    with st.spinner("Searching..."):
                        results = search_pubmed(search_q)
                        existing = {e['id'] for e in st.session_state.data['phase2']['evidence']}
                        for r in results:
                            if r['id'] not in existing:
                                st.session_state.data['phase2']['evidence'].append(r)
        
        with col_ai_grade:
            if st.button("✨ AI-Analyze GRADE Scores", type="primary"):
                 evidence_list = st.session_state.data['phase2']['evidence']
                 if not evidence_list:
                     st.warning("No evidence to analyze.")
                 else:
                     with st.spinner("AI evaluating strength of evidence..."):
                         titles = [f"ID {e['id']}: {e['title']}" for e in evidence_list]
                         prompt = f"Analyze citations. Assign GRADE score (High, Moderate, Low, Very Low).\nCitations: {json.dumps(titles)}\nReturn JSON object {{ID: Score}}."
                         grade_map = get_gemini_response(prompt, json_mode=True)
                         if isinstance(grade_map, dict):
                             for e in st.session_state.data['phase2']['evidence']:
                                 if e['id'] in grade_map: e['grade'] = grade_map[e['id']]
                             st.rerun()

        if st.session_state.data['phase2']['evidence']:
            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            grade_help = "High (A): High confidence.\nModerate (B): Moderate confidence.\nLow (C): Limited confidence.\nVery Low (D): Very little confidence."
            edited_df = st.data_editor(df, column_config={
                "grade": st.column_config.SelectboxColumn("Strength of Evidence", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], help=grade_help, required=True, width="medium"),
                "title": st.column_config.TextColumn("Title", width="large", disabled=True),
                "id": st.column_config.TextColumn("PubMed ID", disabled=True),
            }, hide_index=True, key="evidence_editor", num_rows="dynamic")
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            
            if not df.empty:
                csv = edited_df.to_csv(index=False)
                export_widget(csv, "evidence_table.csv", "text/csv", label="Download CSV")

# ------------------------------------------
# PHASE 3: LOGIC
# ------------------------------------------
elif "Phase 3" in phase:
    st.subheader("Pathway Logic")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        <div style="background-color: #E0F2F1; border-left: 5px solid #4DB6AC; padding: 10px; border-radius: 5px; color: #00695C; margin-bottom: 20px;">
            <strong>ℹ️ Instructions:</strong> Define the clinical steps of your pathway below.
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Auto-Draft Logic", type="primary"):
            cond = st.session_state.data['phase1']['condition']
            evidence_list = st.session_state.data['phase2']['evidence']
            
            if not cond:
                st.error("Missing Phase 1 data.")
            else:
                with st.spinner("Synthesizing logic..."):
                    ev_context = "\n".join([f"- ID {e['id']}: {e['title']}" for e in evidence_list[:5]])
                    prompt = f"""
                    Create a clinical logic flow for {cond}.
                    Available Evidence:
                    {ev_context}
                    Return a JSON List of objects: [{{"type": "Start", "label": "Triage", "evidence": "ID 12345"}}]
                    - "type": Start, Decision, Process, End.
                    - "label": Short step description.
                    - "evidence": Select ID from Available Evidence if relevant, or "N/A".
                    """
                    nodes = get_gemini_response(prompt, json_mode=True)
                    if isinstance(nodes, list):
                        st.session_state.data['phase3']['nodes'] = nodes
                        st.rerun()

    with col2:
        evidence_ids = ["N/A"] + [f"ID {e['id']}" for e in st.session_state.data['phase2']['evidence']]
        if not st.session_state.data['phase3']['nodes']:
             st.session_state.data['phase3']['nodes'] = [{"type":"Start", "label":"", "evidence":"N/A"}]
        
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        edited_nodes = st.data_editor(df_nodes, column_config={
            "type": st.column_config.SelectboxColumn("Type", options=["Start", "Decision", "Process", "Note", "End"], required=True),
            "label": st.column_config.TextColumn("Content", default=""), 
            "evidence": st.column_config.SelectboxColumn("Evidence", options=evidence_ids, width="medium")
        }, num_rows="dynamic", hide_index=True, use_container_width=True)
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# ------------------------------------------
# PHASE 4: VISUALIZATION
# ------------------------------------------
elif "Phase 4" in phase:
    st.subheader("Visual Flowchart")
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
                
                if st.session_state.get('user_email'):
                    c_dl1, c_dl2 = st.columns(2)
                    with c_dl1:
                         try:
                             png_data = graph.pipe(format='png')
                             st.download_button("🖼️ High-Res PNG", png_data, "pathway.png", "image/png", type="primary")
                         except: st.warning("PNG unavailable.")
                    with c_dl2:
                         try:
                             svg_data = graph.pipe(format='svg')
                             st.download_button("✏️ Visio-Ready SVG", svg_data, "pathway.svg", "image/svg+xml")
                         except: 
                             st.download_button("📜 Download DOT", graph.source, "pathway.dot", "text/plain")
                else:
                    st.warning("🔒 Enter email to download diagram.")
                    
            except Exception as e:
                st.error(f"Graph Error: {e}")

    with col2:
        st.markdown("#### Heuristic Evaluation")
        if st.button("Start AI Analysis", type="primary"):
            with st.spinner("Analyzing against Nielsen's 10 Heuristics..."):
                prompt = f"""
                Analyze logic: {json.dumps(nodes)}
                Evaluate against Nielsen's 10 Usability Heuristics.
                Return JSON {{H1: "e.g. [Insight]", ... H10: "e.g. [Insight]"}}.
                Important: Start every insight with "e.g.".
                """
                risks = get_gemini_response(prompt, json_mode=True)
                if isinstance(risks, dict): st.session_state.data['phase4']['heuristics_data'] = risks
        
        risks = st.session_state.data['phase4'].get('heuristics_data', {})
        for k, v in risks.items():
            # Tooltip logic: display definition via HTML title attribute on the header
            def_text = HEURISTIC_DEFS.get(k, "No definition available.")
            st.markdown(f"""
            <div style="margin-bottom: 5px;">
                <span class="heuristic-title" title="{def_text}">{k} Insight (Hover for Def)</span>
            </div>
            """, unsafe_allow_html=True)
            st.info(v) # Display the AI insight (which now starts with e.g.)

# ------------------------------------------
# PHASE 5: OPERATIONALIZE
# ------------------------------------------
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    c1, c2, c3 = st.columns(3)
    
    # 1. Beta Testing (Updated Prompt)
    with c1:
        st.markdown("#### 🌐 1. Beta Testing")
        
        if st.button("Generate Interact Guide"):
            user_mail = st.session_state.get('user_email', 'USER_EMAIL')
            with st.spinner("Drafting Interactive Guide..."):
                prompt = f"""
                Create a 'Beta Testing Interactive Guide' (HTML/Markdown) for {st.session_state.data['phase1']['condition']}.
                
                CRITICAL REQUIREMENT:
                - Include a "Feedback Module" section.
                - Create a feedback link or form action that directs mail to: {user_mail}
                - Make it clear to the beta tester that clicking "Send Feedback" will email the pathway author.
                
                Content:
                1. Intro to pathway.
                2. Instructions for beta testers.
                3. Feedback Form (Subject: Beta Feedback - {st.session_state.data['phase1']['condition']}).
                """
                content = get_gemini_response(prompt)
                st.session_state.data['phase5']['beta_content'] = content
        
        if st.session_state.data['phase5']['beta_content']:
             st.info(f"ℹ️ Generated guide directs feedback to: {st.session_state.get('user_email', 'your email')}")
             export_widget(st.session_state.data['phase5']['beta_content'], "beta_guide.html", "text/html", label="Download Guide")

    # 2. Education
    with c2:
        st.markdown("#### 📊 2. Frontline Education")
        if st.button("Generate Slide Deck"):
            with st.spinner("Drafting Slides..."):
                prompt = f"Create content for 5 educational slides (Markdown) about {st.session_state.data['phase1']['condition']} pathway."
                slides = get_gemini_response(prompt)
                st.session_state.data['phase5']['slides'] = slides
        
        if st.session_state.data['phase5']['slides']:
             export_widget(st.session_state.data['phase5']['slides'], "slides.md", label="Download Slides")

    # 3. EHR Integration
    with c3:
        st.markdown("#### 🏥 3. EHR Integration")
        if st.button("Generate OPS/Epic Specs"):
            with st.spinner("Mapping to OPS..."):
                nodes_json = json.dumps(st.session_state.data['phase3']['nodes'])
                prompt = f"""
                Map these nodes to Epic/HR tools.
                Nodes: {nodes_json}
                Use 'OPS' (Practice Advisory) instead of BPA.
                Return CSV string with headers: Phase, Logic_Node, OPS_Action, Decision_Tree_Element.
                """
                csv = get_gemini_response(prompt)
                st.session_state.data['phase5']['epic_csv'] = csv
        
        if st.session_state.data['phase5']['epic_csv']:
            export_widget(st.session_state.data['phase5']['epic_csv'], "ops_specs.csv", "text/csv", label="Download CSV")

# ==========================================
# FOOTER
# ==========================================
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
