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

# --- LIBRARY HANDLING ---
try:
    from docx import Document
    from docx.shared import Inches as DocxInches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    st.error("Missing Libraries: Please run `pip install python-docx`")
    Document = None

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
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

    /* SIDEBAR BUTTONS */
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
    
    /* RADIO BUTTONS */
    div[role="radiogroup"] label > div:first-child {
        background-color: white !important;
        border-color: #5D4037 !important;
    }
    div[role="radiogroup"] label[data-checked="true"] > div:first-child {
        background-color: #5D4037 !important;
        border-color: #5D4037 !important;
    }
    
    /* SPINNER */
    .stSpinner > div {
        border-top-color: #5D4037 !important;
    }
    
    /* EXPANDERS */
    div[data-testid="stExpander"] details summary {
        background-color: #5D4037 !important;
        color: white !important;
        border-radius: 5px;
        margin-bottom: 5px;
    }
    div[data-testid="stExpander"] details summary:hover {
        color: #A9EED1 !important;
    }
    div[data-testid="stExpander"] details summary svg {
        color: white !important;
    }

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
COPYRIGHT_HTML_FOOTER = """
<div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666;">
    <p>
        <a href="https://www.carepathiq.org" target="_blank" style="text-decoration:none; color:#4a4a4a; font-weight:bold;">CarePathIQ</a> 
        © 2024 by 
        <a href="https://www.tehreemrehman.com" target="_blank" style="text-decoration:none; color:#4a4a4a; font-weight:bold;">Tehreem Rehman</a> 
        is licensed under 
        <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" style="text-decoration:none; color:#4a4a4a;">CC BY-SA 4.0</a>
        <img src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;">
        <img src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;">
        <img src="https://mirrors.creativecommons.org/presskit/icons/sa.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;">
    </p>
</div>
"""
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
    formatted_text = re.sub(r'(?<!<b>)\bTip:', r'<b>Tip:</b>', formatted_text)
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

def create_word_docx(data):
    """Generates a Word Document Project Charter from Phase 1 data."""
    if Document is None: return None
    doc = Document()
    doc.add_heading(f"Project Charter: {data.get('condition', 'Untitled')}", 0)
    
    doc.add_heading('1. Project Overview', level=1)
    doc.add_paragraph(f"Care Setting: {data.get('setting', 'N/A')}")
    doc.add_heading('Problem Statement', level=2)
    doc.add_paragraph(data.get('problem', 'N/A'))
    
    doc.add_heading('2. Scope', level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Inclusion Criteria'
    hdr_cells[1].text = 'Exclusion Criteria'
    row_cells = table.add_row().cells
    row_cells[0].text = data.get('inclusion', '')
    row_cells[1].text = data.get('exclusion', '')
    
    doc.add_heading('3. SMART Objectives', level=1)
    doc.add_paragraph(data.get('objectives', 'N/A'))
    
    doc.add_heading('4. Project Timeline', level=1)
    schedule = data.get('schedule', [])
    if schedule:
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Stage'
        hdr_cells[1].text = 'Owner'
        hdr_cells[2].text = 'Start Date'
        hdr_cells[3].text = 'End Date'
        
        for item in schedule:
            row_cells = table.add_row().cells
            row_cells[0].text = str(item.get('Stage', ''))
            row_cells[1].text = str(item.get('Owner', ''))
            row_cells[2].text = str(item.get('Start', ''))
            row_cells[3].text = str(item.get('End', ''))
    
    # Copyright Footer
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = "CarePathIQ © 2024 by Tehreem Rehman is licensed under CC BY-SA 4.0"
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_exec_summary_docx(summary_text, condition):
    """Generates a Word Document for the Executive Summary."""
    if Document is None: return None
    doc = Document()
    doc.add_heading(f"Executive Summary: {condition}", 0)
    
    for line in summary_text.split('\n'):
        if line.strip():
            if line.startswith('###'):
                doc.add_heading(line.replace('###', '').strip(), level=3)
            elif line.startswith('##'):
                doc.add_heading(line.replace('##', '').strip(), level=2)
            elif line.startswith('#'):
                doc.add_heading(line.replace('#', '').strip(), level=1)
            else:
                doc.add_paragraph(line.strip().replace('**', ''))

    # Copyright Footer
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = "CarePathIQ © 2024 by Tehreem Rehman is licensed under CC BY-SA 4.0"
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

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
            # Clinical details in visualizer
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

def render_bottom_navigation():
    """Renders Previous/Next buttons at the bottom of the page."""
    st.divider()
    PHASES = [
        "Phase 1: Scoping & Charter", 
        "Phase 2: Rapid Evidence Appraisal", 
        "Phase 3: Decision Science", 
        "Phase 4: User Interface Design", 
        "Phase 5: Operationalize"
    ]
    current_label = st.session_state.get('current_phase_label', PHASES[0])
    try: curr_idx = PHASES.index(current_label)
    except: curr_idx = 0
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # Callback to update phase safely
    def set_phase(new_phase):
        st.session_state.target_phase = new_phase

    with col1:
        if curr_idx > 0:
            st.button(f"← Previous: {PHASES[curr_idx-1].split(':')[0]}", key=f"btm_prev_{curr_idx}", use_container_width=True, on_click=set_phase, args=(PHASES[curr_idx-1],))
    with col3:
        if curr_idx < len(PHASES) - 1:
            st.button(f"Next: {PHASES[curr_idx+1].split(':')[0]} →", key=f"btm_next_{curr_idx}", type="primary", use_container_width=True, on_click=set_phase, args=(PHASES[curr_idx+1],))

# ==========================================
# 3. SIDEBAR & SESSION INITIALIZATION
# ==========================================
with st.sidebar:
    # Clickable Logo
    try:
        if "CarePathIQ_Logo.png" in os.listdir():
            with open("CarePathIQ_Logo.png", "rb") as f:
                logo_data = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 20px;">
                    <a href="https://carepathiq.org/" target="_blank">
                        <img src="data:image/png;base64,{logo_data}" width="200" style="max-width: 100%;">
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )
    except Exception: pass

    st.title("AI Agent")
    st.divider()
    
    default_key = st.secrets.get("GEMINI_API_KEY", "")
    gemini_api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    model_choice = st.selectbox("Model", ["Auto", "gemini-1.5-flash", "gemini-1.5-pro"])
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success("AI Connected")
    st.divider()
    
    # Navigation Buttons (Mint Green)
    PHASES = ["Phase 1: Scoping & Charter", "Phase 2: Rapid Evidence Appraisal", "Phase 3: Decision Science", "Phase 4: User Interface Design", "Phase 5: Operationalize"]
    if "current_phase_label" not in st.session_state: st.session_state.current_phase_label = PHASES[0]
    
    # Determine current index
    current_label = st.session_state.get('current_phase_label', PHASES[0])
    try: curr_idx = PHASES.index(current_label)
    except: curr_idx = 0
    
    # Previous Button
    if curr_idx > 0:
        if st.button(f"Previous: {PHASES[curr_idx-1].split(':')[0]}", type="primary", use_container_width=True):
            st.session_state.current_phase_label = PHASES[curr_idx-1]
            st.rerun()
            
    # Phase Status Box
    st.markdown(f"""
    <div style="background-color: #5D4037; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin: 15px 0;">
        Current Phase: <br><span style="font-size: 1.1em;">{current_label}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Next Button
    if curr_idx < len(PHASES) - 1:
        if st.button(f"Next: {PHASES[curr_idx+1].split(':')[0]}", type="primary", use_container_width=True):
            st.session_state.current_phase_label = PHASES[curr_idx+1]
            st.rerun()

    st.divider()
    st.progress(calculate_granular_progress())

# LANDING PAGE LOGIC: BLOCK ACCESS WITHOUT KEY
if not gemini_api_key:
    st.title("CarePathIQ AI Agent")
    st.markdown("""
    <div style="background-color: #5D4037; padding: 15px; border-radius: 5px; color: white; margin-bottom: 20px;">
        <strong>Welcome.</strong> Please enter your <strong>Gemini API Key</strong> in the sidebar to activate the AI Agent. 
        Get a free API key <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #A9EED1; text-decoration: underline;">here</a>.
    </div>
    """, unsafe_allow_html=True)
    st.markdown(COPYRIGHT_HTML_FOOTER, unsafe_allow_html=True)
    st.stop()

if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "", "setting": "", "inclusion": "", "exclusion": "", "problem": "", "objectives": "", "schedule": []},
        "phase2": {"evidence": [], "mesh_query": ""},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}},
        "phase5": {"exec_summary": "", "beta_html": "", "expert_html": "", "edu_html": ""}
    }

# Handle Navigation State
if 'target_phase' in st.session_state and st.session_state.target_phase:
    st.session_state.current_phase_label = st.session_state.target_phase
    st.session_state.target_phase = None

# ==========================================
# 4. MAIN WORKFLOW LOGIC
# ==========================================
# Top Navigation
phase = st.radio("Workflow Phase", PHASES, index=curr_idx, horizontal=True, label_visibility="collapsed", key="top_nav_radio")
if phase != st.session_state.current_phase_label:
    st.session_state.current_phase_label = phase
    st.rerun()

st.divider()

# --- PHASE 1 ---
if "Phase 1" in phase:
    # 1. Helper to Sync Widgets to Data Store
    def sync_p1_widgets():
        st.session_state.data['phase1']['condition'] = st.session_state.get('p1_cond_input', '')
        st.session_state.data['phase1']['inclusion'] = st.session_state.get('p1_inc', '')
        st.session_state.data['phase1']['exclusion'] = st.session_state.get('p1_exc', '')
        st.session_state.data['phase1']['setting'] = st.session_state.get('p1_setting', '')
        st.session_state.data['phase1']['problem'] = st.session_state.get('p1_prob', '')
        st.session_state.data['phase1']['objectives'] = st.session_state.get('p1_obj', '')

    # 2. Initialize Session State Keys if missing
    if 'p1_cond_input' not in st.session_state: st.session_state['p1_cond_input'] = st.session_state.data['phase1'].get('condition', '')
    if 'p1_inc' not in st.session_state: st.session_state['p1_inc'] = st.session_state.data['phase1'].get('inclusion', '')
    if 'p1_exc' not in st.session_state: st.session_state['p1_exc'] = st.session_state.data['phase1'].get('exclusion', '')
    if 'p1_setting' not in st.session_state: st.session_state['p1_setting'] = st.session_state.data['phase1'].get('setting', '')
    if 'p1_prob' not in st.session_state: st.session_state['p1_prob'] = st.session_state.data['phase1'].get('problem', '')
    if 'p1_obj' not in st.session_state: st.session_state['p1_obj'] = st.session_state.data['phase1'].get('objectives', '')

    styled_info("Tip: This form is <b>interactive</b>. The AI agent will auto-draft sections (Criteria, Problem, Goals) <b>as you type</b>. You can manually edit any text area to refine the content.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Clinical Focus")
        # Interactive Inputs with Callbacks
        cond_input = st.text_input("Clinical Condition", placeholder="e.g. Sepsis", key="p1_cond_input", on_change=sync_p1_widgets)
        setting_input = st.text_input("Care Setting", placeholder="e.g. Emergency Department", key="p1_setting", on_change=sync_p1_widgets)
        
        st.subheader("2. Target Population")
        # Logic: Auto-Generate Criteria if Condition/Setting change
        curr_key = f"{cond_input}|{setting_input}"
        last_key = st.session_state.get('last_criteria_key', '')
        
        if cond_input and setting_input and curr_key != last_key:
            with st.spinner("Auto-generating inclusion/exclusion criteria..."):
                prompt = f"""
                Act as a Chief Medical Officer. For '{cond_input}' in '{setting_input}', suggest precise 'inclusion' and 'exclusion' criteria.
                Return JSON object with keys: 'inclusion', 'exclusion'.
                """
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    inc_text = str(data.get('inclusion', ''))
                    exc_text = str(data.get('exclusion', ''))
                    # Update State
                    st.session_state.data['phase1']['inclusion'] = inc_text
                    st.session_state.data['phase1']['exclusion'] = exc_text
                    st.session_state['p1_inc'] = inc_text
                    st.session_state['p1_exc'] = exc_text
                    st.session_state['last_criteria_key'] = curr_key
                    st.rerun()

        st.text_area("Inclusion Criteria", height=100, key="p1_inc", on_change=sync_p1_widgets)
        st.text_area("Exclusion Criteria", height=100, key="p1_exc", on_change=sync_p1_widgets)
        
    with col2:
        st.subheader("3. Clinical Gap / Problem Statement")
        # Logic: Auto-Generate Problem if Criteria exist
        curr_inc = st.session_state.get('p1_inc', '')
        curr_cond = st.session_state.get('p1_cond_input', '')
        curr_prob_key = f"{curr_inc}|{curr_cond}"
        last_prob_key = st.session_state.get('last_prob_key', '')
        
        if curr_inc and curr_cond and curr_prob_key != last_prob_key:
             with st.spinner("Auto-generating problem statement..."):
                prompt = f"Act as a CMO. For condition '{curr_cond}', suggest a 'problem' statement referencing care variation. Return JSON with key: 'problem'."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    p_text = str(data.get('problem', ''))
                    st.session_state.data['phase1']['problem'] = p_text
                    st.session_state['p1_prob'] = p_text
                    st.session_state['last_prob_key'] = curr_prob_key
                    st.rerun()

        st.text_area("Problem Statement / Clinical Gap", height=100, key="p1_prob", on_change=sync_p1_widgets, label_visibility="collapsed")
        
        st.subheader("4. Goals")
        # Logic: Auto-Generate Goals if Problem exists
        curr_prob = st.session_state.get('p1_prob', '')
        curr_obj_key = f"{curr_prob}|{curr_cond}"
        last_obj_key = st.session_state.get('last_obj_key', '')
        
        if curr_prob and curr_cond and curr_obj_key != last_obj_key:
             with st.spinner("Auto-generating SMART objectives..."):
                prompt = f"Act as a CMO. For condition '{curr_cond}' addressing problem '{curr_prob}', suggest 3 SMART 'objectives'. Return JSON with key 'objectives'."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    o_text = str(data.get('objectives', ''))
                    st.session_state.data['phase1']['objectives'] = o_text
                    st.session_state['p1_obj'] = o_text
                    st.session_state['last_obj_key'] = curr_obj_key
                    st.rerun()

        st.text_area("Project Goals", height=150, key="p1_obj", on_change=sync_p1_widgets, label_visibility="collapsed")

    st.divider()
    st.subheader("5. Project Timeline (Gantt Chart)")
    
    # 9-Step Schedule Logic (Fixed Date Math & Terminology)
    if not st.session_state.data['phase1']['schedule']:
        today = date.today()
        def add_weeks(start, w): return start + timedelta(weeks=w)
        d1 = add_weeks(today, 2); d2 = add_weeks(d1, 4); d3 = add_weeks(d2, 2); d4 = add_weeks(d3, 2)
        d5 = add_weeks(d4, 4); d6 = add_weeks(d5, 4); d7 = add_weeks(d6, 2); d8 = add_weeks(d7, 4)
        
        st.session_state.data['phase1']['schedule'] = [
            {"Stage": "1. Project Charter", "Owner": "PM", "Start": today, "End": d1},
            {"Stage": "2. Pathway Draft", "Owner": "Clinical Lead", "Start": d1, "End": d2},
            {"Stage": "3. Expert Panel", "Owner": "Expert Panel", "Start": d2, "End": d3},
            {"Stage": "4. Iterative Design", "Owner": "Clinical Lead", "Start": d3, "End": d4},
            {"Stage": "5. Informatics Build", "Owner": "IT", "Start": d4, "End": d5},
            {"Stage": "6. Beta Testing", "Owner": "Quality", "Start": d5, "End": d6},
            {"Stage": "7. Go-Live", "Owner": "Ops", "Start": d6, "End": d7},
            {"Stage": "8. Optimization", "Owner": "Clinical Lead", "Start": d7, "End": d8},
            {"Stage": "9. Monitoring", "Owner": "Quality", "Start": d8, "End": add_weeks(d8, 12)}
        ]
        
    df_sched = pd.DataFrame(st.session_state.data['phase1']['schedule'])
    # Column config with 'Stage' instead of 'Phase'
    edited_sched = st.data_editor(
        df_sched, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="sched_editor",
        column_config={
            "Stage": st.column_config.TextColumn("Stage", width="medium"),
            "Owner": st.column_config.TextColumn("Owner"),
            "Start": st.column_config.DateColumn("Start"),
            "End": st.column_config.DateColumn("End")
        }
    )
    if not edited_sched.empty:
        st.session_state.data['phase1']['schedule'] = edited_sched.to_dict('records')
        
        # ALTAIR FIX: Drop invalid data and force datetime conversion
        chart_data = edited_sched.copy()
        chart_data.dropna(subset=['Start', 'End', 'Stage'], inplace=True)
        chart_data['Start'] = pd.to_datetime(chart_data['Start'])
        chart_data['End'] = pd.to_datetime(chart_data['End'])
        
        if not chart_data.empty:
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Start', title='Date'), 
                x2='End', 
                y=alt.Y('Stage', sort=None, title='Stage'), 
                color=alt.Color('Owner', legend=alt.Legend(title="Owner")),
                tooltip=['Stage', 'Start', 'End', 'Owner']
            ).properties(height=300).interactive()
            st.altair_chart(chart, use_container_width=True)
    
    if st.button("Generate Project Charter", type="primary", use_container_width=True):
        # Sync final values before generation
        sync_p1_widgets()
        d = st.session_state.data['phase1']
        
        # Check inputs
        if not d['condition'] or not d['problem']:
            st.error("Please ensure Condition and Problem Statement are filled.")
        else:
            with st.status("Generating Charter Document...", expanded=True) as status:
                charter_buffer = create_word_docx(d)
                if charter_buffer:
                    status.update(label="Charter Ready!", state="complete")
                    st.download_button(
                        label="Download Project Charter (.docx)",
                        data=charter_buffer,
                        file_name=f"Project_Charter_{d['condition']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    status.update(label="Error generating Word Doc.", state="error")

    render_bottom_navigation()

# --- PHASE 2 ---
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
        
        col_filter, col_clear, col_regrade = st.columns([3, 1, 2])
        with col_filter:
            selected_grades = st.multiselect("Filter by GRADE:", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], default=["High (A)", "Moderate (B)", "Low (C)", "Un-graded"])
        with col_clear:
            if st.button("Clear Evidence List", key="clear_ev"):
                st.session_state.data['phase2']['evidence'] = []
                st.rerun()
        with col_regrade:
            if st.button("AI-Grade All Evidence"):
                with st.status("Grading...", expanded=True):
                    ev_list = st.session_state.data['phase2']['evidence']
                    for i in range(0, len(ev_list), 5):
                        batch = ev_list[i:i+5]
                        prompt = f"Assign GRADE (High/Mod/Low) and Rationale for: {json.dumps([{k:v for k,v in e.items() if k in ['id','title','abstract']} for e in batch])}. Return JSON {{ID: {{grade, rationale}}}}"
                        res = get_gemini_response(prompt, json_mode=True)
                        if res:
                            for e in batch:
                                if e['id'] in res: e.update(res[e['id']])
                    st.rerun()
        
        df_ev = pd.DataFrame(st.session_state.data['phase2']['evidence'])
        if not df_ev.empty:
            if 'id' in df_ev.columns: df_ev['id'] = df_ev['id'].astype(str)
            if 'grade' not in df_ev.columns: df_ev['grade'] = 'Un-graded'
            df_ev = df_ev[df_ev['grade'].isin(selected_grades)]
        
        edited_ev = st.data_editor(
            df_ev, 
            column_config={
                "id": st.column_config.TextColumn("PMID", disabled=True),
                "url": st.column_config.LinkColumn("Link"), 
                "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"]),
                "rationale": st.column_config.TextColumn("Rationale", width="large"),
                "abstract": None 
            }, 
            hide_index=True, use_container_width=True, key="ev_editor"
        )
        
        csv = edited_ev.to_csv(index=False).encode('utf-8')
        export_widget(csv, "evidence_table.csv", "text/csv", label="Download Evidence Table (CSV)")
        
    render_bottom_navigation()

# --- PHASE 3 ---
elif "Phase 3" in phase:
    col_tools, col_editor = st.columns([1, 3])
    with col_tools:
        if st.button("Auto-Draft Logic (AI)", type="primary", use_container_width=True):
            cond = st.session_state.data['phase1']['condition']
            with st.spinner("Drafting..."):
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
    
    if st.button("Auto-Populate Supporting Evidence (AI)"):
         with st.spinner("Matching nodes to evidence..."):
             ev_titles = [f"{e['id']}: {e['title']}" for e in st.session_state.data['phase2']['evidence']]
             for node in st.session_state.data['phase3']['nodes']:
                 if not node.get('evidence'):
                     p_match = f"Match this clinical step: '{node['label']}' to best evidence ID: {ev_titles}. Return just ID."
                     res = get_gemini_response(p_match)
                     if res: node['evidence'] = res.strip()
             st.rerun()
            
    render_bottom_navigation()

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
                if st.button(f"Apply Fix ({k})", key=f"fix_{k}"):
                    with st.spinner("Applying AI Fix..."):
                        p_fix = f"Update this JSON to fix {k} ({v}): {json.dumps(nodes)}. Return JSON."
                        new_nodes = get_gemini_response(p_fix, json_mode=True)
                        if new_nodes:
                            st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                            st.rerun()
    
    st.divider()
    custom_edit = st.text_area("Custom Refinement", placeholder="E.g., 'Add a blood pressure check after triage'", label_visibility="collapsed")
    if st.button("Apply Changes", type="primary"):
         with st.spinner("Applying..."):
             p_cust = f"Update logic based on: {custom_edit}. Current: {json.dumps(nodes)}. Return JSON."
             new_nodes = get_gemini_response(p_cust, json_mode=True)
             if new_nodes:
                 st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                 st.rerun()

    render_bottom_navigation()

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
                # Append footer
                if expert_html:
                     expert_html = expert_html.replace('</body>', f'{COPYRIGHT_HTML_FOOTER}</body>')
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
                # Append footer
                if beta_html:
                    beta_html = beta_html.replace('</body>', f'{COPYRIGHT_HTML_FOOTER}</body>')
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
                # Append footer
                if edu_html:
                    edu_html = edu_html.replace('</body>', f'{COPYRIGHT_HTML_FOOTER}</body>')
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
    
    st.divider()
    st.subheader("Executive Summary")
    if st.button("Draft Executive Summary (AI)"):
        with st.spinner("Drafting..."):
            p_sum = f"Write a professional executive summary for the {cond} pathway project."
            summary = get_gemini_response(p_sum)
            st.session_state.data['phase5']['exec_summary'] = summary
            st.rerun()
            
    if st.session_state.data['phase5'].get('exec_summary'):
        st.markdown(st.session_state.data['phase5']['exec_summary'])
        # Create Word Doc for Summary
        summary_buffer = create_exec_summary_docx(st.session_state.data['phase5']['exec_summary'], cond)
        if summary_buffer:
            st.download_button(
                label="Download Executive Summary (.docx)",
                data=summary_buffer,
                file_name=f"Executive_Summary_{cond}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    render_bottom_navigation()

st.markdown(COPYRIGHT_HTML_FOOTER, unsafe_allow_html=True)