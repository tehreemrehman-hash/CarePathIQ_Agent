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
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS: DARK BROWN THEME ---
st.markdown("""
<style>
    /* 1. ALL BUTTONS -> Dark Brown */
    div.stButton > button {
        background-color: #5D4037 !important; 
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
    }
    div.stButton > button:hover {
        background-color: #3E2723 !important;
        color: white !important;
    }

    /* 2. RADIO BUTTONS (Phase Circles) */
    /* Border of the circle */
    div[role="radiogroup"] label > div:first-child {
        border-color: #5D4037 !important;
    }
    /* Background when selected */
    div[role="radiogroup"] label > div:first-child[data-checked="true"] {
        background-color: #5D4037 !important;
        border-color: #5D4037 !important;
    }
    /* The inner dot */
    div[role="radiogroup"] label > div:first-child[data-checked="true"] > div {
        background-color: white !important;
    }

    /* 3. TOOLTIPS */
    .heuristic-title {
        cursor: help;
        font-weight: bold;
        color: #00695C;
        text-decoration: underline dotted;
        font-size: 1.05em;
    }

    h1, h2, h3 { color: #00695C; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
    st.title("AI Agent")
    st.divider()
    
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Use Google AI Studio Key")
    model_choice = st.selectbox("AI Agent Model", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success(f"✅ Connected: {model_choice}")
        
    st.divider()
    
    # --- DARK BROWN STATUS BOX ---
    current_phase = st.session_state.get('current_phase_label', 'Start')
    st.markdown(f"""
    <div style="background-color: #5D4037; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
        Current Phase: <br><span style="font-size: 1.1em;">{current_phase}</span>
    </div>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
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
    
if "auto_run" not in st.session_state:
    st.session_state.auto_run = {"p2_grade": False, "p3_logic": False, "p4_heuristics": False, "p5_all": False}

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def create_pdf_view_link(html_content, label="📄 Open Charter in New Window"):
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" target="_blank" style="text-decoration:none; color:white; background-color:#5D4037; padding:10px 20px; border-radius:5px; font-weight:bold; display:inline-block;">{label}</a>'

def export_widget(content, filename, mime_type="text/plain", label="Download"):
    final_content = content
    if "text" in mime_type or "csv" in mime_type:
        if isinstance(content, str): final_content = content + "\n\n" + COPYRIGHT_MD
    st.download_button(f"📥 {label}", final_content, filename, mime_type)

def get_gemini_response(prompt, json_mode=False):
    if not gemini_api_key: return None
    try:
        model = genai.GenerativeModel(model_choice)
        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
        time.sleep(1) 
        response = model.generate_content(prompt, safety_settings=safety)
        text = response.text
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            try:
                # Robust Regex JSON extraction
                match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
                if match: return json.loads(match.group())
                return json.loads(text)
            except: return {}
        return text
    except: return None

def search_pubmed(query):
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
                    "grade": "Un-graded"
                })
        return citations
    except: return []

# ==========================================
# 4. MAIN UI
# ==========================================
st.title("CarePathIQ AI Agent")
st.markdown(f"### Intelligent Clinical Pathway Development")

if not gemini_api_key:
    st.markdown("""<div style="background-color: #5D4037; padding: 15px; border-radius: 5px; color: white; margin-bottom: 20px;"><strong>👋 Welcome.</strong> Please enter your <strong>Gemini API Key</strong> in the sidebar to activate the AI Agent.</div>""", unsafe_allow_html=True)
    st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
    st.stop()

phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", "Phase 2: Evidence & Mesh", "Phase 3: Logic Construction", "Phase 4: Visualization & Testing", "Phase 5: Operationalize"], 
                 horizontal=True)
st.session_state.current_phase_label = phase
st.divider()

# PHASE 1
if "Phase 1" in phase:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Project Parameters")
        cond_input = st.text_input("Clinical Condition", value=st.session_state.data['phase1']['condition'], placeholder="e.g. Sepsis")
        
        if cond_input and cond_input != st.session_state.suggestions.get('condition_ref'):
            st.session_state.data['phase1']['condition'] = cond_input
            with st.spinner(f"🤖 AI Agent auto-populating suggestions..."):
                prompt = f"Act as CMO. Building pathway for: '{cond_input}'. Return JSON: inclusion, exclusion, setting, problem, objectives (list)."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    st.session_state.suggestions = data
                    st.session_state.suggestions['condition_ref'] = cond_input
                    st.session_state.data['phase1']['inclusion'] = f"e.g. {data.get('inclusion', '')}"
                    st.session_state.data['phase1']['exclusion'] = f"e.g. {data.get('exclusion', '')}"
                    st.session_state.data['phase1']['setting'] = f"e.g. {data.get('setting', '')}"
                    st.session_state.data['phase1']['problem'] = f"e.g. {data.get('problem', '')}"
                    st.session_state.data['phase1']['objectives'] = f"e.g. Suggested Objectives:\n" + "\n".join([f"- {g}" for g in data.get('objectives', [])])
                    st.rerun()

        st.markdown("#### Target Population")
        inc = st.text_area("Inclusion Criteria", value=st.session_state.data['phase1'].get('inclusion', ''))
        exc = st.text_area("Exclusion Criteria", value=st.session_state.data['phase1'].get('exclusion', ''))
        setting = st.text_input("Care Setting", value=st.session_state.data['phase1']['setting'])
        prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'])
        st.session_state.data['phase1'].update({"inclusion": inc, "exclusion": exc, "setting": setting, "problem": prob})

    with col2:
        st.subheader("Objectives")
        obj = st.text_area("Define Project Objectives", value=st.session_state.data['phase1']['objectives'], height=200)
        st.session_state.data['phase1']['objectives'] = obj
        st.divider()
        if st.button("Generate Project Charter", type="primary"):
            with st.spinner("AI Agent generating Charter..."):
                prompt = f"Create a formal Project Charter (HTML). Condition: {cond_input}. Inclusion: {inc}. Exclusion: {exc}. Problem: {prob}. Objectives: {obj}. Return HTML."
                charter_content = get_gemini_response(prompt)
                full_html = f"<html><body style='font-family:serif; padding:40px;'>{charter_content}<div style='text-align:center; color:gray; margin-top:50px;'>CarePathIQ © 2024</div></body></html>"
                st.markdown(create_pdf_view_link(full_html), unsafe_allow_html=True)

# PHASE 2
elif "Phase 2" in phase:
    st.subheader("Dynamic Evidence Synthesis")
    col1, col2 = st.columns([1, 2])
    p1_cond = st.session_state.data['phase1']['condition']
    
    with col1:
        st.markdown("#### PICO Framework")
        p = st.text_input("P (Population)", value=st.session_state.data['phase1']['inclusion'])
        i = st.text_input("I (Intervention)", value="Standardized Pathway")
        c = st.text_input("C (Comparison)", value="Current Variation")
        o = st.text_input("O (Outcome)", value="Reduced Mortality / LOS")
        if st.button("Generate MeSH Query", type="primary"):
            with st.spinner("AI Agent building query..."):
                prompt = f"Create MeSH query for {p1_cond}. P:{p} I:{i} O:{o}. Output query string only."
                st.session_state.data['phase2']['mesh_query'] = get_gemini_response(prompt)
                st.rerun()

    with col2:
        st.markdown("#### Literature Search")
        search_q = st.text_area("Search Query", value=st.session_state.data['phase2'].get('mesh_query', ''), height=100)
        
        if st.button("Search PubMed"):
            if search_q:
                with st.spinner("Searching..."):
                    results = search_pubmed(search_q)
                    existing = {e['id'] for e in st.session_state.data['phase2']['evidence']}
                    for r in results:
                        if r['id'] not in existing:
                            st.session_state.data['phase2']['evidence'].append(r)
                            st.session_state.auto_run["p2_grade"] = False
        
        evidence_list = st.session_state.data['phase2']['evidence']
        if evidence_list and not st.session_state.auto_run["p2_grade"]:
             with st.spinner("AI Agent automatically analyzing GRADE scores..."):
                 titles = [f"ID {e['id']}: {e['title']}" for e in evidence_list]
                 prompt = f"Analyze citations. Assign GRADE score (High, Moderate, Low, Very Low). Citations: {json.dumps(titles)}. Return JSON {{ID: Score}}."
                 grade_map = get_gemini_response(prompt, json_mode=True)
                 if isinstance(grade_map, dict):
                     for e in st.session_state.data['phase2']['evidence']:
                         if e['id'] in grade_map: e['grade'] = grade_map[e['id']]
                     st.session_state.auto_run["p2_grade"] = True
                     st.rerun()

        if evidence_list:
            st.markdown("""<div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">✅ <strong>AI Agent Output:</strong> GRADE scores auto-populated. <strong>Keep/Modify</strong> below, or click 'Clear Grades' for manual entry.</div>""", unsafe_allow_html=True)
            if st.button("Clear Grades for Manual Entry", type="primary"):
                for e in st.session_state.data['phase2']['evidence']: e['grade'] = "Un-graded"
                st.session_state.auto_run["p2_grade"] = True 
                st.rerun()

            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            # 4 SPECIFIC COLUMNS + GRADE with TOOLTIP
            edited_df = st.data_editor(df, column_config={
                "title": st.column_config.TextColumn("Title", width="large", disabled=True),
                "id": st.column_config.TextColumn("PubMed ID", disabled=True),
                "url": st.column_config.LinkColumn("URL", disabled=True),
                "citation": st.column_config.TextColumn("Citation", disabled=True),
                "grade": st.column_config.SelectboxColumn("Strength of Evidence", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], required=True, help="High (A): High confidence.\nModerate (B): Moderate confidence.\nLow (C): Limited confidence.\nVery Low (D): Very little confidence.")
            }, hide_index=True)
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            if not df.empty: export_widget(edited_df.to_csv(index=False), "evidence.csv", "text/csv", label="Download CSV")

# PHASE 3
elif "Phase 3" in phase:
    st.subheader("Pathway Logic")
    col1, col2 = st.columns([1, 2])
    with col1:
        # INSTRUCTIONS DARK BROWN
        st.markdown("""<div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 20px;">ℹ️ <strong>Instructions:</strong> Define the clinical steps of your pathway below.</div>""", unsafe_allow_html=True)
        cond = st.session_state.data['phase1']['condition']
        
        if cond and not st.session_state.data['phase3']['nodes'] and not st.session_state.auto_run["p3_logic"]:
             with st.spinner("AI Agent drafting logic flow..."):
                 prompt = f"Create clinical logic for {cond}. Return JSON List: [{{'type': 'Start', 'label': 'Triage', 'evidence': ''}}]. Keys: type, label, evidence."
                 nodes = get_gemini_response(prompt, json_mode=True)
                 if isinstance(nodes, list):
                     st.session_state.data['phase3']['nodes'] = nodes
                     st.session_state.auto_run["p3_logic"] = True
                     st.rerun()

    with col2:
        if st.session_state.auto_run["p3_logic"]:
             st.markdown("""<div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">✅ <strong>AI Agent Output:</strong> Logic draft generated. <strong>Keep/Modify</strong> rows below, or click 'Clear Logic' to start fresh.</div>""", unsafe_allow_html=True)
             if st.button("Clear Logic for Manual Entry", type="primary"):
                 st.session_state.data['phase3']['nodes'] = []
                 st.session_state.auto_run["p3_logic"] = True
                 st.rerun()

        # BLANK DEFAULT
        evidence_ids = [""] + [f"ID {e['id']}" for e in st.session_state.data['phase2']['evidence']]
        if not st.session_state.data['phase3']['nodes']: st.session_state.data['phase3']['nodes'] = [{"type":"Start", "label":"", "evidence":""}]
        
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        # COLUMN NAMED "Content"
        edited_nodes = st.data_editor(df_nodes, column_config={
            "type": st.column_config.SelectboxColumn("Type", options=["Start", "Decision", "Process", "End"]),
            "label": st.column_config.TextColumn("Content", default=""), 
            "evidence": st.column_config.SelectboxColumn("Evidence", options=evidence_ids)
        }, num_rows="dynamic", hide_index=True, use_container_width=True)
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# PHASE 4
elif "Phase 4" in phase:
    st.subheader("Visual Flowchart")
    col1, col2 = st.columns([2, 1])
    with col1:
        nodes = st.session_state.data['phase3']['nodes']
        if nodes:
            graph = graphviz.Digraph()
            graph.attr(rankdir='TB')
            for i, n in enumerate(nodes):
                color = {'Start':'#D5E8D4', 'Decision':'#F8CECC', 'Process':'#FFF2CC', 'End':'#D5E8D4'}.get(n.get('type'), '#E0F2F1')
                shape = {'Decision':'diamond', 'Start':'oval', 'End':'oval'}.get(n.get('type'), 'box')
                graph.node(str(i), n.get('label', '?'), shape=shape, style='filled', fillcolor=color)
                if i > 0: graph.edge(str(i-1), str(i))
            st.graphviz_chart(graph)
            
            # DOWNLOADS ALWAYS VISIBLE
            c1, c2 = st.columns(2)
            with c1:
                try: st.download_button("🖼️ High-Res PNG", graph.pipe(format='png'), "flow.png", "image/png", type="primary")
                except: st.warning("PNG unavailable.")
            with c2:
                try: st.download_button("✏️ Visio SVG", graph.pipe(format='svg'), "flow.svg", "image/svg+xml")
                except: pass

    with col2:
        st.markdown("#### Heuristic Evaluation")
        nodes_json = json.dumps(nodes)
        
        # AUTO-RUN HEURISTICS - NO BUTTON
        if nodes and not st.session_state.auto_run["p4_heuristics"]:
             with st.spinner("AI Agent analyzing against Nielsen's 10 Heuristics..."):
                 prompt = f"Analyze logic: {nodes_json}. Evaluate against Nielsen's 10 Usability Heuristics. Return JSON {{H1: 'e.g. ...', ... H10: 'e.g. ...'}}."
                 risks = get_gemini_response(prompt, json_mode=True)
                 if isinstance(risks, dict): 
                     st.session_state.data['phase4']['heuristics_data'] = risks
                     st.session_state.auto_run["p4_heuristics"] = True
                     st.rerun()

        risks = st.session_state.data['phase4'].get('heuristics_data', {})
        if risks:
            st.markdown("""<div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">✅ <strong>AI Agent Output:</strong> Analysis complete.</div>""", unsafe_allow_html=True)
            for k, v in risks.items():
                def_text = HEURISTIC_DEFS.get(k, "No definition.")
                st.markdown(f"<div style='margin-bottom:5px;'><span class='heuristic-title' title='{def_text}'>{k} Insight (Hover)</span></div>", unsafe_allow_html=True)
                st.info(v)

# PHASE 5
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    if not st.session_state.auto_run["p5_all"]:
        with st.spinner("AI Agent generating Guide, Slides, and EHR Specs..."):
            cond = st.session_state.data['phase1']['condition']
            prob = st.session_state.data['phase1']['problem']
            goals = st.session_state.data['phase1']['objectives']
            nodes = json.dumps(st.session_state.data['phase3']['nodes'])
            
            if not st.session_state.data['phase5']['beta_content']:
                st.session_state.data['phase5']['beta_content'] = get_gemini_response(f"Create Beta Guide (HTML) for {cond}. Context: {prob}. Placeholder feedback link.")
            if not st.session_state.data['phase5']['slides']:
                st.session_state.data['phase5']['slides'] = get_gemini_response(f"Create 5 slides (Markdown) for {cond}. Gap: {prob}. Goals: {goals}.")
            if not st.session_state.data['phase5']['epic_csv']:
                st.session_state.data['phase5']['epic_csv'] = get_gemini_response(f"Map {nodes} to Epic/OPS tools. Return CSV string.")
            
            st.session_state.auto_run["p5_all"] = True
            st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 🌐 1. Beta Testing")
        beta_email = st.text_input("Enter email to receive feedback:")
        if st.button("Generate Interactive Guide"):
             with st.spinner("Updating guide..."):
                 cond = st.session_state.data['phase1']['condition']
                 prob = st.session_state.data['phase1']['problem']
                 st.session_state.data['phase5']['beta_content'] = get_gemini_response(f"Create Beta Guide (HTML) for {cond}. Context: {prob}. Feedback link to {beta_email}.")
                 st.rerun()
        
        if st.session_state.data['phase5']['beta_content']:
             st.success("✅ Guide Generated.")
             export_widget(st.session_state.data['phase5']['beta_content'], "beta_guide.html", "text/html", label="Download Guide")
    with c2:
        st.markdown("#### 📊 2. Frontline Education")
        if st.session_state.data['phase5']['slides']:
             st.success("✅ Slides Generated.")
             export_widget(st.session_state.data['phase5']['slides'], "slides.md", label="Download Slides")
    with c3:
        st.markdown("#### 🏥 3. EHR Integration")
        if st.session_state.data['phase5']['epic_csv']:
            st.success("✅ Specs Generated.")
            export_widget(st.session_state.data['phase5']['epic_csv'], "ops_specs.csv", "text/csv", label="Download CSV")

st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
