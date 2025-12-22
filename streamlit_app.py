import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import pandas as pd
import urllib.request
import urllib.parse
import json
import re
import time
import base64
from io import BytesIO
import datetime
from datetime import date, timedelta
import os
import copy
import xml.etree.ElementTree as ET
import altair as alt

# --- GRAPHVIZ PATH FIX ---
os.environ["PATH"] += os.pathsep + '/usr/bin'

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="CarePathIQ AI Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* BUTTONS */
    div.stButton > button, 
    div[data-testid="stButton"] > button,
    button[kind="primary"],
    button[kind="secondary"] {
        background-color: #5D4037 !important; 
        color: white !important;
        border: 1px solid #5D4037 !important;
        border-radius: 5px !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover, 
    div[data-testid="stButton"] > button:hover {
        background-color: #3E2723 !important; 
        border-color: #3E2723 !important;
        color: white !important;
    }
    div.stButton > button:disabled {
        background-color: #eee !important;
        color: #999 !important;
        border: 1px solid #ccc !important;
    }

    /* DOWNLOAD BUTTONS */
    div.stDownloadButton > button {
        background-color: #5D4037 !important; 
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #3E2723 !important;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #A9EED1 !important; 
        color: #5D4037 !important;
        border: none !important;
        font-weight: bold;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #8FD9BC !important; 
        color: #3E2723 !important;
    }
    
    /* PROGRESS & SPINNER */
    div[data-testid="stProgress"] > div > div > div { background-color: #A9EED1 !important; }
    .stSpinner > div { border-top-color: #5D4037 !important; }
    
    /* HEADERS */
    h1, h2, h3 { color: #00695C; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* TOOLTIPS */
    div[data-testid="stTooltipContent"] {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
COPYRIGHT_MD = "\n\n---\n**© 2024 CarePathIQ by Tehreem Rehman.** Licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)."
HEURISTIC_DEFS = {
    "H1": "Visibility of system status", "H2": "Match between system and real world",
    "H3": "User control and freedom", "H4": "Consistency and standards",
    "H5": "Error prevention", "H6": "Recognition rather than recall",
    "H7": "Flexibility and efficiency of use", "H8": "Aesthetic and minimalist design",
    "H9": "Help users recognize, diagnose, and recover from errors", "H10": "Help and documentation"
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def calculate_granular_progress():
    if 'data' not in st.session_state: return 0.0
    data = st.session_state.data
    total_points = 0
    earned_points = 0
    
    # Phase 1
    p1 = data.get('phase1', {})
    for k in ['condition', 'setting', 'inclusion', 'exclusion', 'problem', 'objectives']:
        total_points += 1
        if p1.get(k): earned_points += 1
    # Phase 2
    p2 = data.get('phase2', {})
    total_points += 2
    if p2.get('mesh_query'): earned_points += 1
    if p2.get('evidence'): earned_points += 1
    # Phase 3
    p3 = data.get('phase3', {})
    total_points += 3
    if p3.get('nodes'): earned_points += 3
    # Phase 4
    p4 = data.get('phase4', {})
    total_points += 2
    if p4.get('heuristics_data'): earned_points += 2
    # Phase 5
    p5 = data.get('phase5', {})
    for k in ['beta_html', 'expert_html', 'edu_html']:
        total_points += 1
        if p5.get(k): earned_points += 1
        
    if total_points == 0: return 0.0
    return min(1.0, earned_points / total_points)

def styled_info(text):
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    st.markdown(f"""
    <div style="background-color: #FFB0C9; color: black; padding: 10px; border-radius: 5px; border: 1px solid black; margin-bottom: 10px;">
        {formatted_text}
    </div>""", unsafe_allow_html=True)

def export_widget(content, filename, mime_type="text/plain", label="Download"):
    final_content = content
    if "text" in mime_type or "csv" in mime_type or "markdown" in mime_type:
        if isinstance(content, str):
            final_content = content + COPYRIGHT_MD
    st.download_button(label, final_content, filename, mime_type)

def harden_nodes(nodes_list):
    """Validates and repairs the Decision Tree logic."""
    if not isinstance(nodes_list, list): return []
    validated = []
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict): continue
        if 'id' not in node or not node['id']:
            prefix = node.get('type', 'P')[0].upper()
            node['id'] = f"{prefix}{i+1}"
        if 'type' not in node: node['type'] = 'Process'
        if node['type'] == 'Decision':
            if 'branches' not in node or not isinstance(node['branches'], list):
                node['branches'] = [
                    {'label': 'Yes', 'target': i+1 if i+1 < len(nodes_list) else None},
                    {'label': 'No', 'target': i+2 if i+2 < len(nodes_list) else None}
                ]
            else:
                for b in node['branches']:
                    if 'label' not in b: b['label'] = 'Option'
                    if 'target' not in b: b['target'] = None
        validated.append(node)
    return validated

def generate_mermaid_code(nodes, orientation="TD"):
    if not nodes: return "flowchart TD\n%% No nodes"
    valid_nodes = harden_nodes(nodes)
    from collections import defaultdict
    swimlanes = defaultdict(list)
    for i, n in enumerate(valid_nodes):
        role = n.get('role', 'Unassigned')
        swimlanes[role].append((i, n))
    code = f"flowchart {orientation}\n"
    node_id_map = {}
    for role, n_list in swimlanes.items():
        code += f"    subgraph {role}\n"
        for i, n in n_list:
            nid = f"N{i}"
            node_id_map[i] = nid
            label = n.get('label', 'Step').replace('"', "'")
            # RESTORED: Clinical details in visualizer
            detail = n.get('detail', '').replace('"', "'")
            meds = n.get('medications', '')
            if meds: detail += f"\\nMeds: {meds}"
            
            full_label = f"{label}\\n{detail}" if detail else label
            ntype = n.get('type', 'Process')
            
            if ntype == 'Start':
                shape_s, shape_e = '([', '])'
                style = f'style {nid} fill:#D5E8D4,stroke:#82B366,stroke-width:2px'
            elif ntype == 'Decision':
                shape_s, shape_e = '{', '}'
                style = f'style {nid} fill:#F8CECC,stroke:#B85450,stroke-width:2px'
            elif ntype == 'End':
                shape_s, shape_e = '([', '])'
                style = f'style {nid} fill:#D5E8D4,stroke:#82B366,stroke-width:2px'
            else:
                shape_s, shape_e = '[', ']'
                style = f'style {nid} fill:#FFF2CC,stroke:#D6B656,stroke-width:1px'
            code += f'        {nid}{shape_s}"{full_label}"{shape_e}\n'
            code += f'        {style}\n'
        code += "    end\n"
    for i, n in enumerate(valid_nodes):
        nid = node_id_map[i]
        ntype = n.get('type')
        if ntype == 'Decision' and 'branches' in n:
            for b in n.get('branches', []):
                t_idx = b.get('target')
                lbl = b.get('label', 'Yes')
                if isinstance(t_idx, (int, float)) and 0 <= t_idx < len(valid_nodes):
                     code += f"    {nid} --|{lbl}| {node_id_map[int(t_idx)]}\n"
        else:
            if i + 1 < len(valid_nodes):
                code += f"    {nid} --> {node_id_map[i+1]}\n"
    return code

def get_gemini_response(prompt, json_mode=False, stream_container=None):
    if not gemini_api_key: return None
    candidates = ["gemini-1.5-flash", "gemini-1.5-pro"]
    if model_choice != "Auto" and model_choice in candidates:
        candidates.insert(0, model_choice)
    response = None
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            is_stream = stream_container is not None
            response = model.generate_content(prompt, stream=is_stream)
            if response: break 
        except Exception:
            time.sleep(0.5)
            continue
    if not response:
        st.error("AI Error. Please check API Key.")
        return None
    try:
        if stream_container:
            text = ""
            for chunk in response:
                if chunk.text:
                    text += chunk.text
                    stream_container.markdown(text + "▌")
            stream_container.markdown(text) 
        else:
            text = response.text
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if match: text = match.group()
            try: return json.loads(text)
            except: return None
        return text
    except Exception: return None

def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        search_params = {'db': 'pubmed', 'term': f"{query} AND (\"last 5 years\"[dp])", 'retmode': 'json', 'retmax': 20, 'sort': 'relevance'}
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            id_list = data.get('esearchresult', {}).get('idlist', [])
        if not id_list: return []
        ids_str = ','.join(id_list)
        fetch_params = {'db': 'pubmed', 'id': ids_str, 'retmode': 'xml'}
        url = base_url + "efetch.fcgi?" + urllib.parse.urlencode(fetch_params)
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode()
        root = ET.fromstring(xml_data)
        citations = []
        for article in root.findall('.//PubmedArticle'):
            medline = article.find('MedlineCitation')
            pmid = medline.find('PMID').text
            title = medline.find('Article/ArticleTitle').text
            abstract_text = "No abstract available."
            abs_node = medline.find('Article/Abstract')
            if abs_node is not None:
                texts = [elem.text for elem in abs_node.findall('AbstractText') if elem.text]
                if texts: abstract_text = " ".join(texts)
            citations.append({"id": pmid, "title": title, "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "abstract": abstract_text, "grade": "Un-graded", "rationale": "Not yet evaluated."})
        return citations
    except Exception as e:
        st.error(f"PubMed Search Error: {e}")
        return []

def render_bottom_navigation(phases, current_label):
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    try: curr_idx = phases.index(current_label)
    except: curr_idx = 0
    with col1:
        if curr_idx > 0:
            if st.button(f"← Previous", use_container_width=True):
                st.session_state.current_phase_label = phases[curr_idx-1]
                st.rerun()
    with col3:
        if curr_idx < len(phases) - 1:
            if st.button(f"Next →", type="primary", use_container_width=True):
                st.session_state.current_phase_label = phases[curr_idx+1]
                st.rerun()

# ==========================================
# 3. SIDEBAR & SESSION INITIALIZATION
# ==========================================
with st.sidebar:
    try:
        if "CarePathIQ_Logo.png" in os.listdir():
            st.image("CarePathIQ_Logo.png", width=220)
    except: pass
    st.title("AI Agent")
    st.caption("Clinical Pathway Architect")
    st.divider()
    
    default_key = st.secrets.get("GEMINI_API_KEY", "")
    gemini_api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    model_choice = st.selectbox("Model", ["Auto", "gemini-1.5-flash", "gemini-1.5-pro"])
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success("AI Connected")
    st.divider()
    
    PHASES = ["Phase 1: Scoping & Charter", "Phase 2: Rapid Evidence Appraisal", "Phase 3: Decision Science", "Phase 4: User Interface Design", "Phase 5: Operationalize"]
    if "current_phase_label" not in st.session_state: st.session_state.current_phase_label = PHASES[0]
    
    for p in PHASES:
        is_active = (p == st.session_state.current_phase_label)
        if st.button(p, key=f"nav_{p}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state.current_phase_label = p
            st.rerun()
    st.divider()
    st.progress(calculate_granular_progress())

if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "", "setting": "", "inclusion": "", "exclusion": "", "problem": "", "objectives": "", "schedule": []},
        "phase2": {"evidence": [], "mesh_query": ""},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}},
        "phase5": {"exec_summary": "", "beta_html": "", "expert_html": "", "edu_html": ""}
    }

# ==========================================
# 4. MAIN WORKFLOW LOGIC
# ==========================================
phase = st.session_state.current_phase_label
st.markdown(f"""<div style="background-color: #5D4037; color: white; padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 25px;"><h3 style="color: white; margin:0;">{phase}</h3></div>""", unsafe_allow_html=True)

# --- PHASE 1 ---
if "Phase 1" in phase:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.data['phase1']['condition'] = st.text_input("Clinical Condition", value=st.session_state.data['phase1'].get('condition',''))
        st.session_state.data['phase1']['setting'] = st.text_input("Care Setting", value=st.session_state.data['phase1'].get('setting',''))
        st.session_state.data['phase1']['inclusion'] = st.text_area("Inclusion Criteria", value=st.session_state.data['phase1'].get('inclusion',''), height=100)
        st.session_state.data['phase1']['exclusion'] = st.text_area("Exclusion Criteria", value=st.session_state.data['phase1'].get('exclusion',''), height=100)
    with col2:
        st.session_state.data['phase1']['problem'] = st.text_area("Problem Statement", value=st.session_state.data['phase1'].get('problem',''), height=100)
        st.session_state.data['phase1']['objectives'] = st.text_area("SMART Objectives", value=st.session_state.data['phase1'].get('objectives',''), height=100)
        if st.button("Auto-Draft Content (AI)", type="primary"):
            cond = st.session_state.data['phase1']['condition']
            if cond:
                with st.spinner("Drafting..."):
                    prompt = f"Act as CMO. For {cond}: Define 3 inclusion/exclusion criteria, a problem statement, and 3 SMART objectives. Return JSON."
                    res = get_gemini_response(prompt, json_mode=True)
                    if res:
                        st.session_state.data['phase1'].update(res)
                        st.rerun()
    st.divider()
    st.subheader("Project Schedule")
    
    # RESTORED: The specific 9-step schedule you originally requested
    if not st.session_state.data['phase1']['schedule']:
        today = date.today()
        def add_weeks(start, w): return start + timedelta(weeks=w)
        d1 = add_weeks(today, 2); d2 = add_weeks(d1, 4); d3 = add_weeks(d2, 2); d4 = add_weeks(d3, 2)
        d5 = add_weeks(d4, 4); d6 = add_weeks(d5, 4); d7 = add_weeks(d6, 2); d8 = add_weeks(d7, 4)
        
        st.session_state.data['phase1']['schedule'] = [
            {"Phase": "1. Project Charter", "Owner": "PM", "Start": today, "End": d1},
            {"Phase": "2. Pathway Draft", "Owner": "Clinical Lead", "Start": d1, "End": d2},
            {"Phase": "3. Expert Panel", "Owner": "Expert Panel", "Start": d2, "End": d3},
            {"Phase": "4. Iterative Design", "Owner": "Clinical Lead", "Start": d3, "End": d4},
            {"Phase": "5. Informatics Build", "Owner": "IT", "Start": d4, "End": d5},
            {"Phase": "6. Beta Testing", "Owner": "Quality", "Start": d5, "End": d6},
            {"Phase": "7. Go-Live", "Owner": "Ops", "Start": d6, "End": d7},
            {"Phase": "8. Optimization", "Owner": "Clinical Lead", "Start": d7, "End": d8},
            {"Phase": "9. Monitoring", "Owner": "Quality", "Start": d8, "End": add_weeks(d8, 12)}
        ]
        
    df_sched = pd.DataFrame(st.session_state.data['phase1']['schedule'])
    edited_sched = st.data_editor(df_sched, num_rows="dynamic", use_container_width=True, key="sched_editor")
    if not edited_sched.empty:
        st.session_state.data['phase1']['schedule'] = edited_sched.to_dict('records')
        chart_data = edited_sched.copy()
        chart_data['Start'] = pd.to_datetime(chart_data['Start'])
        chart_data['End'] = pd.to_datetime(chart_data['End'])
        chart = alt.Chart(chart_data).mark_bar().encode(x='Start', x2='End', y='Phase', color='Owner').interactive()
        st.altair_chart(chart, use_container_width=True)
    render_bottom_navigation(PHASES, phase)

# ------------------------------------------
# PHASE 2: RAPID EVIDENCE APPRAISAL (FIXED)
# ------------------------------------------
elif "Phase 2" in phase:
    col_q, col_btn = st.columns([3, 1])
    with col_q:
        default_q = st.session_state.data['phase2'].get('mesh_query', '')
        if not default_q and st.session_state.data['phase1']['condition']:
            default_q = f"guidelines for {st.session_state.data['phase1']['condition']}"
        q = st.text_input("PubMed Search Query", value=default_q)
        
    with col_btn:
        st.write("")
        st.write("")
        if st.button("Search PubMed", type="primary", use_container_width=True):
            st.session_state.data['phase2']['mesh_query'] = q
            with st.spinner("Querying PubMed Database..."):
                res = search_pubmed(q)
                st.session_state.data['phase2']['evidence'] = res
                st.rerun()

    if st.session_state.data['phase2']['evidence']:
        st.markdown("### Evidence Table")
        
        # Batch Grade Button
        if st.button("AI-Grade All Evidence (GRADE Method)"):
            with st.status("AI Agent reading abstracts...", expanded=True) as status:
                ev_list = st.session_state.data['phase2']['evidence']
                # Process in batches of 5 to avoid token limits
                batch_size = 5
                for i in range(0, len(ev_list), batch_size):
                    batch = ev_list[i:i+batch_size]
                    prompt = f"""
                    Act as a Clinical Methodologist.
                    For these articles (ID, Title, Abstract provided), assign a GRADE (High, Moderate, Low, Very Low) and a brief Rationale.
                    Data: {json.dumps([{k:v for k,v in e.items() if k in ['id','title','abstract']} for e in batch])}
                    Return JSON mapping ID to {{ "grade": "...", "rationale": "..." }}
                    """
                    status.write(f"Grading batch {i//batch_size + 1}...")
                    res = get_gemini_response(prompt, json_mode=True)
                    if res:
                        for e in batch:
                            if e['id'] in res:
                                e['grade'] = res[e['id']].get('grade', 'Un-graded')
                                e['rationale'] = res[e['id']].get('rationale', '')
                status.update(label="Grading Complete", state="complete")
                st.rerun()

        # --- FIX STARTS HERE ---
        # 1. Create DataFrame
        df_ev = pd.DataFrame(st.session_state.data['phase2']['evidence'])
        
        # 2. Force 'id' to be string to prevent mismatch errors
        if not df_ev.empty and 'id' in df_ev.columns:
            df_ev['id'] = df_ev['id'].astype(str)

        # 3. Editor Configuration
        edited_ev = st.data_editor(
            df_ev,
            column_config={
                "id": st.column_config.TextColumn("PMID", disabled=True), # Force Text display
                "title": st.column_config.TextColumn("Title", width="medium"),
                "url": st.column_config.LinkColumn("Link"),
                "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], required=True),
                "rationale": st.column_config.TextColumn("Rationale", width="large"),
                "abstract": None # Hide abstract from grid
            },
            hide_index=True,
            use_container_width=True,
            key="ev_editor"
        )
        
        # 4. Direct Save (Simpler & More Robust than mapping)
        st.session_state.data['phase2']['evidence'] = edited_ev.to_dict('records')
        # --- FIX ENDS HERE ---
        
        csv = edited_ev.to_csv(index=False).encode('utf-8')
        export_widget(csv, "evidence_table.csv", "text/csv")
        
    render_bottom_navigation(PHASES, phase)

# --- PHASE 3 ---
elif "Phase 3" in phase:
    col_tools, col_editor = st.columns([1, 3])
    with col_tools:
        if st.button("Auto-Draft Logic (AI)", type="primary", use_container_width=True):
            cond = st.session_state.data['phase1']['condition']
            with st.spinner("Drafting..."):
                # RESTORED: Specific Prompt requesting clinical details (labs, meds)
                prompt = f"""
                Act as Clinical Decision Scientist. Create pathway for {cond}.
                Return JSON LIST. Each node: 
                {{
                    "id": "P1", "type": "Start|Decision|Process|End", "label": "...", "role": "Physician",
                    "detail": "Action...", 
                    "labs": "...", "imaging": "...", "medications": "...", "dosage": "...", 
                    "branches": [{{ "label": "Yes", "target": null }}] (Only for Decision nodes)
                }}
                """
                nodes = get_gemini_response(prompt, json_mode=True)
                if nodes:
                    st.session_state.data['phase3']['nodes'] = harden_nodes(nodes)
                    st.rerun()
        if st.button("Clear All", use_container_width=True):
            st.session_state.data['phase3']['nodes'] = []
            st.rerun()

    with col_editor:
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        # RESTORED: Expanded column config for clinical details
        edited_nodes = st.data_editor(
            df_nodes, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="p3_editor",
            column_config={
                "type": st.column_config.SelectboxColumn("Type", options=["Start", "Decision", "Process", "End"]),
                "labs": st.column_config.TextColumn("Labs"),
                "medications": st.column_config.TextColumn("Meds"),
                "dosage": st.column_config.TextColumn("Dosage"),
                "detail": st.column_config.TextColumn("Details", width="medium")
            }
        )
        if st.button("Save Logic"):
            st.session_state.data['phase3']['nodes'] = harden_nodes(edited_nodes.to_dict('records'))
            st.success("Saved.")
            st.rerun()
            
    render_bottom_navigation(PHASES, phase)

# --- PHASE 4 ---
elif "Phase 4" in phase:
    nodes = st.session_state.data['phase3']['nodes']
    col_vis, col_heuristics = st.columns([2, 1])
    with col_vis:
        st.subheader("Pathway Visualization")
        mermaid_code = generate_mermaid_code(nodes)
        components.html(f'<div class="mermaid">{mermaid_code}</div><script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script><script>mermaid.initialize({{startOnLoad:true}});</script>', height=600, scrolling=True)
    with col_heuristics:
        st.subheader("Heuristics")
        if st.button("Analyze Risks"):
            prompt = f"Analyze logic {json.dumps(nodes)} for Nielsen's Heuristics. Return JSON {{H1: critique...}}"
            res = get_gemini_response(prompt, json_mode=True)
            if res:
                st.session_state.data['phase4']['heuristics_data'] = res
                st.rerun()
        h_data = st.session_state.data['phase4'].get('heuristics_data', {})
        for k, v in h_data.items():
            with st.expander(k): 
                st.write(v)
                # RESTORED: Apply Fix Button Logic
                if st.button(f"Apply Fix ({k})", key=f"fix_{k}"):
                    with st.spinner("Applying AI Fix..."):
                        p_fix = f"Update this JSON to fix {k} ({v}): {json.dumps(nodes)}. Return JSON."
                        new_nodes = get_gemini_response(p_fix, json_mode=True)
                        if new_nodes:
                            st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                            st.rerun()

    render_bottom_navigation(PHASES, phase)

# --- PHASE 5 ---
elif "Phase 5" in phase:
    st.markdown("### Operational Toolkit: Interactive HTML Assets")
    styled_info("These tools generate **standalone HTML files** that you can send to users. Submissions from these forms will be sent directly to the email you provide below.")
    
    cond = st.session_state.data['phase1']['condition'] or "Pathway"
    
    with st.expander("Deployment Configuration", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            audience = st.text_input("Target Audience", value="Multidisciplinary Team")
        with col_c2:
            email_target = st.text_input("Receive Submissions at Email:", placeholder="you@hospital.org")
    
    st.divider()
    
    if st.button("Generate Interactive HTML Assets (AI)", type="primary", use_container_width=True):
        if not email_target:
            st.error("Please provide an email address to receive form submissions.")
        else:
            with st.status("Generating Assets...", expanded=True) as status:
                
                # 1. Expert Panel Form (RESTORED CUSTOM LOGIC)
                status.write("Creating Expert Panel Feedback Form...")
                prompt_expert = f"""
                Create a standalone HTML5 Form for Expert Panel Feedback on a '{cond}' clinical pathway.
                Target Audience: {audience}.
                
                CRITICAL LOGIC:
                The form MUST contain distinct sections to identify feedback by Node Type.
                1. Section: Start/End Nodes.
                2. Section: Decision Nodes.
                3. Section: Process Nodes.
                
                For EACH section, include a dropdown or radio button asking:
                "Justification for Change:" -> Options: ["Evidence-Based", "Resource-Based", "Other"].
                
                Backend: Form Action = 'https://formsubmit.co/{email_target}'.
                Styling: Professional, clean CSS.
                Return ONLY valid HTML code.
                """
                expert_html = get_gemini_response(prompt_expert)
                st.session_state.data['phase5']['expert_html'] = expert_html
                
                # 2. Beta Tester Form
                status.write("Creating Beta Tester Feedback Form...")
                prompt_beta = f"""
                Create a standalone HTML5 Form for Beta Testers of the '{cond}' pathway.
                Target Audience: {audience}.
                Form Action: 'https://formsubmit.co/{email_target}'.
                Questions: Usability, clarity, bugs.
                Return ONLY valid HTML code.
                """
                beta_html = get_gemini_response(prompt_beta)
                st.session_state.data['phase5']['beta_html'] = beta_html

                # 3. Education Module (RESTORED LOGIC)
                status.write("Creating Interactive Education & Certificate Module...")
                prompt_edu = f"""
                Create a standalone HTML/JS file for '{cond}' Staff Education.
                
                1. Content: 3 Key Clinical Takeaways.
                2. Quiz: 5 Multiple Choice Questions related to {cond}. 
                   - JS Validation: Show "Correct" or "Incorrect" immediately.
                3. Gating: 
                   - IF score == 100%: Reveal Hidden Certificate Form.
                   - ELSE: Show "Please review and try again".
                4. Certificate Form:
                   - Input: "Full Name".
                   - Action: 'https://formsubmit.co/{email_target}'.
                   - Submit Button: "Submit for Certificate".
                
                Return ONLY valid HTML code.
                """
                edu_html = get_gemini_response(prompt_edu)
                st.session_state.data['phase5']['edu_html'] = edu_html
                
                status.update(label="Assets Generated Successfully!", state="complete")

    st.subheader("Asset Downloads")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.session_state.data['phase5'].get('expert_html'):
            st.download_button("📥 Expert Panel Form (.html)", st.session_state.data['phase5']['expert_html'], f"{cond}_ExpertForm.html", "text/html", use_container_width=True)
        else:
            st.button("Expert Form Missing", disabled=True, use_container_width=True)
            
    with c2:
        if st.session_state.data['phase5'].get('beta_html'):
            st.download_button("📥 Beta Tester Form (.html)", st.session_state.data['phase5']['beta_html'], f"{cond}_BetaForm.html", "text/html", use_container_width=True)
        else:
            st.button("Beta Form Missing", disabled=True, use_container_width=True)
            
    with c3:
        if st.session_state.data['phase5'].get('edu_html'):
            st.download_button("📥 Education Module (.html)", st.session_state.data['phase5']['edu_html'], f"{cond}_EduModule.html", "text/html", use_container_width=True)
        else:
            st.button("Education Module Missing", disabled=True, use_container_width=True)

    render_bottom_navigation(PHASES, phase)

st.markdown(COPYRIGHT_MD, unsafe_allow_html=True)