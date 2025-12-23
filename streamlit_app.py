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
from contextlib import contextmanager

# --- GRAPHVIZ PATH FIX ---
os.environ["PATH"] += os.pathsep + '/usr/bin'

# --- LIBRARY HANDLING ---
try:
    from docx import Document
    from docx.shared import Inches as DocxInches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:
    # Safe fallback to prevent crash if libraries are missing
    Document = None
    plt = None
    mdates = None

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="CarePathIQ AI Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide detailed Python tracebacks from end users
try:
    st.set_option('client.showErrorDetails', False)
except Exception:
    pass

# --- CUSTOM CSS ---
# Force-clear Streamlit caches once per user session to avoid stale views
if "cleared_cache_once" not in st.session_state:
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    st.session_state.cleared_cache_once = True

st.markdown("""
<style>
    /* AGGRESSIVELY HIDE HEADER LINKS & ANCHORS */
    [data-testid="stHeaderAction"] { display: none !important; visibility: hidden !important; opacity: 0 !important; }
    a.anchor-link { display: none !important; height: 0px !important; width: 0px !important; }
    .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a { display: none !important; pointer-events: none; cursor: default; text-decoration: none; color: transparent !important; }
    h1 > a, h2 > a, h3 > a { display: none !important; }
    
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

    /* LINK BUTTONS */
    a[kind="secondary"] {
        background-color: #5D4037 !important;
        border-color: #5D4037 !important;
        color: white !important;
        text-decoration: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
    }
    a[kind="secondary"]:hover {
        background-color: #3E2723 !important;
        border-color: #3E2723 !important;
        color: white !important;
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
        border: 2px solid #5D4037 !important;
        border-radius: 50% !important;
        width: 20px !important;
        height: 20px !important;
        margin-right: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div[role="radiogroup"] label[data-checked="true"] > div:first-child {
        background-color: #5D4037 !important;
        border: 2px solid #5D4037 !important;
        box-shadow: 0 2px 4px rgba(93,64,55,0.15);
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
COPYRIGHT_MD = "\n\n---\n**© 2024 CarePathIQ by Tehreem Rehman.** Licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)."
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
HEURISTIC_DEFS = {
    "H1": "Visibility of system status", "H2": "Match between system and real world",
    "H3": "User control and freedom", "H4": "Consistency and standards",
    "H5": "Error prevention", "H6": "Recognition rather than recall",
    "H7": "Flexibility and efficiency of use", "H8": "Aesthetic and minimalist design",
    "H9": "Help users recognize, diagnose, and recover from errors", "H10": "Help and documentation"
}
PHASES = ["Phase 1: Scoping & Charter", "Phase 2: Rapid Evidence Appraisal", "Phase 3: Decision Science", "Phase 4: User Interface Design", "Phase 5: Operationalize"]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

# --- NAVIGATION CONTROLLER ---
def change_phase(new_phase):
    st.session_state.current_phase_label = new_phase
    st.session_state.top_nav_radio = new_phase  # Sync radio button value

def render_bottom_navigation():
    """Renders Previous/Next buttons at the bottom of the page."""
    if "current_phase_label" in st.session_state and st.session_state.current_phase_label in PHASES:
        current_idx = PHASES.index(st.session_state.current_phase_label)
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if current_idx > 0:
                prev_phase = PHASES[current_idx - 1]
                st.button(f"← {prev_phase.split(':')[0]}", key="bottom_prev", use_container_width=True, on_click=change_phase, args=(prev_phase,))
                    
        with col3:
            if current_idx < len(PHASES) - 1:
                next_phase = PHASES[current_idx + 1]
                st.button(f"{next_phase.split(':')[0]} →", key="bottom_next", use_container_width=True, type="primary", on_click=change_phase, args=(next_phase,))

def calculate_granular_progress():
    if 'data' not in st.session_state: return 0.0
    data = st.session_state.data
    total_points = 0
    earned_points = 0
    p1 = data.get('phase1', {})
    for k in ['condition', 'setting', 'inclusion', 'exclusion', 'problem', 'objectives']:
        total_points += 1
        if p1.get(k): earned_points += 1
    p2 = data.get('phase2', {})
    total_points += 2
    if p2.get('mesh_query'): earned_points += 1
    if p2.get('evidence'): earned_points += 1
    p3 = data.get('phase3', {})
    total_points += 3
    if p3.get('nodes'): earned_points += 3
    p4 = data.get('phase4', {})
    total_points += 2
    if p4.get('heuristics_data'): earned_points += 2
    p5 = data.get('phase5', {})
    for k in ['beta_html', 'expert_html', 'edu_html']:
        total_points += 1
        if p5.get(k): earned_points += 1
    if total_points == 0: return 0.0
    return min(1.0, earned_points / total_points)

def styled_info(text):
    formatted_text = text.replace("Tip:", "<b>Tip:</b>")
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

@contextmanager
def ai_activity(label="Working with the AI agent…"):
    """Unified, clean status UI for AI tasks; suppresses tracebacks."""
    with st.status(label, expanded=False) as status:
        try:
            yield status
            status.update(label="Ready!", state="complete")
        except Exception:
            status.update(label="There was a problem completing this step.", state="error")
            st.error("Please try again or adjust your input.")
            # Swallow exception to avoid exposing internals
            return

@st.cache_data(ttl=3600)
def generate_gantt_image(schedule):
    if not schedule: return None
    # Safety check if matplotlib is not installed/imported
    if 'plt' not in globals() or 'mdates' not in globals() or plt is None: return None
    try:
        df = pd.DataFrame(schedule)
        df['Start'] = pd.to_datetime(df['Start'])
        df['End'] = pd.to_datetime(df['End'])
        df['Duration'] = (df['End'] - df['Start']).dt.days
        fig, ax = plt.subplots(figsize=(8, 4))
        y_pos = range(len(df))
        ax.barh(y_pos, df['Duration'], left=mdates.date2num(df['Start']), align='center', color='#00695C', alpha=0.8)
        ax.set_yticks(y_pos)
        # Use 'Stage' column for labels if available
        labels = df['Stage'].tolist() if 'Stage' in df.columns else df['Phase'].tolist()
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.set_xlabel('Timeline')
        ax.set_title('Project Schedule', fontsize=12, fontweight='bold', color='#5D4037')
        plt.tight_layout()
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150)
        plt.close(fig)
        img_buffer.seek(0)
        return img_buffer
    except Exception as e:
        return None

def create_word_docx(data):
    if Document is None: return None
    doc = Document()
    doc.add_heading(f"Project Charter: {data.get('condition', 'Untitled')}", 0)
    ihi = data.get('ihi_content', {})
    
    doc.add_heading('What are we trying to accomplish?', level=1)
    doc.add_heading('Problem', level=2)
    doc.add_paragraph(ihi.get('problem', data.get('problem', '')))
    
    doc.add_heading('Project Description', level=2)
    doc.add_paragraph(ihi.get('project_description', ''))
    
    doc.add_heading('Rationale', level=2)
    doc.add_paragraph(ihi.get('rationale', ''))
    
    doc.add_heading('Expected Outcomes', level=2)
    doc.add_paragraph(ihi.get('expected_outcomes', ''))
    
    doc.add_heading('Aim Statement', level=2)
    doc.add_paragraph(ihi.get('aim_statement', data.get('objectives', '')))

    doc.add_heading('How will we know that a change is an improvement?', level=1)
    doc.add_heading('Outcome Measure(s)', level=2)
    for m in ihi.get('outcome_measures', []): doc.add_paragraph(f"- {m}", style='List Bullet')
    
    doc.add_heading('Process Measure(s)', level=2)
    for m in ihi.get('process_measures', []): doc.add_paragraph(f"- {m}", style='List Bullet')
    
    doc.add_heading('Balancing Measure(s)', level=2)
    for m in ihi.get('balancing_measures', []): doc.add_paragraph(f"- {m}", style='List Bullet')

    doc.add_heading('What changes can we make?', level=1)
    doc.add_heading('Initial Activities', level=2)
    doc.add_paragraph(ihi.get('initial_activities', ''))
    
    doc.add_heading('Change Ideas', level=2)
    for c in ihi.get('change_ideas', []): doc.add_paragraph(f"- {c}", style='List Bullet')
    
    doc.add_heading('Key Stakeholders', level=2)
    doc.add_paragraph(ihi.get('stakeholders', ''))
    
    doc.add_heading('Barriers', level=2)
    doc.add_paragraph(ihi.get('barriers', ''))
    
    doc.add_heading('Boundaries', level=2)
    # Check both cases for boundaries key
    boundaries = ihi.get('boundaries', ihi.get('Boundaries', ''))
    if isinstance(boundaries, dict):
        # Format dictionary nicely (In Scope / Out of Scope)
        in_scope = boundaries.get('in_scope', boundaries.get('In Scope', ''))
        out_scope = boundaries.get('out_of_scope', boundaries.get('Out of Scope', ''))
        
        if in_scope:
            p = doc.add_paragraph()
            run = p.add_run("In Scope: ")
            run.bold = True
            p.add_run(str(in_scope))
            
        if out_scope:
            p = doc.add_paragraph()
            run = p.add_run("Out of Scope: ")
            run.bold = True
            p.add_run(str(out_scope))
    else:
        doc.add_paragraph(str(boundaries))
    
    doc.add_heading('Project Timeline', level=1)
    schedule = data.get('schedule', [])
    if schedule:
        gantt_img = generate_gantt_image(schedule)
        if gantt_img:
            doc.add_picture(gantt_img, width=DocxInches(6))
            doc.add_paragraph("")
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Stage'; hdr_cells[1].text = 'Owner'; hdr_cells[2].text = 'Start Date'; hdr_cells[3].text = 'End Date'
        for item in schedule:
            row_cells = table.add_row().cells
            row_cells[0].text = str(item.get('Stage', ''))
            row_cells[1].text = str(item.get('Owner', ''))
            row_cells[2].text = str(item.get('Start', ''))
            row_cells[3].text = str(item.get('End', ''))
    section = doc.sections[0]; footer = section.footer; p = footer.paragraphs[0]
    p.text = "Adapted from IHI QI Project Charter: https://www.ihi.org/library/tools/qi-project-charter\nCarePathIQ © 2024 by Tehreem Rehman is licensed under CC BY-SA 4.0"; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def create_exec_summary_docx(summary_text, condition):
    if Document is None: return None
    doc = Document()
    doc.add_heading(f"Executive Summary: {condition}", 0)
    for line in summary_text.split('\n'):
        if line.strip():
            if line.startswith('###'): doc.add_heading(line.replace('###', '').strip(), level=3)
            elif line.startswith('##'): doc.add_heading(line.replace('##', '').strip(), level=2)
            elif line.startswith('#'): doc.add_heading(line.replace('#', '').strip(), level=1)
            else: doc.add_paragraph(line.strip().replace('**', ''))
    section = doc.sections[0]; footer = section.footer; p = footer.paragraphs[0]
    p.text = "CarePathIQ © 2024 by Tehreem Rehman is licensed under CC BY-SA 4.0"; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def harden_nodes(nodes_list):
    if not isinstance(nodes_list, list): return []
    validated = []
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict): continue
        if 'id' not in node or not node['id']: node['id'] = f"{node.get('type', 'P')[0].upper()}{i+1}"
        if 'type' not in node: node['type'] = 'Process'
        if node['type'] == 'Decision':
            if 'branches' not in node or not isinstance(node['branches'], list):
                node['branches'] = [{'label': 'Yes', 'target': i+1}, {'label': 'No', 'target': i+2}]
        validated.append(node)
    return validated

def generate_mermaid_code(nodes, orientation="TD"):
    if not nodes: return "flowchart TD\n%% No nodes"
    valid_nodes = harden_nodes(nodes)
    from collections import defaultdict
    swimlanes = defaultdict(list)
    for i, n in enumerate(valid_nodes): swimlanes[n.get('role', 'Unassigned')].append((i, n))
    code = f"flowchart {orientation}\n"
    node_id_map = {}
    for role, n_list in swimlanes.items():
        code += f"    subgraph {role}\n"
        for i, n in n_list:
            nid = f"N{i}"; node_id_map[i] = nid
            label = n.get('label', 'Step').replace('"', "'")
            detail = n.get('detail', '').replace('"', "'")
            meds = n.get('medications', '')
            if meds: detail += f"\\nMeds: {meds}"
            full_label = f"{label}\\n{detail}" if detail else label
            ntype = n.get('type', 'Process')
            if ntype == 'Start': shape = '([', '])'; style = 'fill:#D5E8D4,stroke:#82B366,stroke-width:2px,color:black'
            elif ntype == 'Decision': shape = '{', '}'; style = 'fill:#F8CECC,stroke:#B85450,stroke-width:2px,color:black'
            elif ntype == 'End': shape = '([', '])'; style = 'fill:#D5E8D4,stroke:#82B366,stroke-width:2px,color:black'
            else: shape = '[', ']'; style = 'fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:black'
            code += f'        {nid}{shape[0]}"{full_label}"{shape[1]}\n        style {nid} {style}\n'
        code += "    end\n"
    for i, n in enumerate(valid_nodes):
        nid = node_id_map[i]
        if n.get('type') == 'Decision' and 'branches' in n:
            for b in n.get('branches', []):
                t = b.get('target')
                if isinstance(t, (int, float)) and 0 <= t < len(valid_nodes): code += f"    {nid} --|{b.get('label', 'Yes')}| {node_id_map[int(t)]}\n"
        elif i + 1 < len(valid_nodes): code += f"    {nid} --> {node_id_map[i+1]}\n"
    return code

@st.cache_data(ttl=3600)
def get_gemini_response(prompt, json_mode=False, stream_container=None):
    if not gemini_api_key: return None
    candidates = ["gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"] if model_choice == "Auto" else [model_choice, "gemini-1.5-flash"]
    response = None
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            is_stream = stream_container is not None
            response = model.generate_content(prompt, stream=is_stream)
            if response: break 
        except Exception: time.sleep(0.5); continue
    if not response: st.error("AI Error. Please check API Key."); return None
    try:
        if stream_container:
            text = ""
            for chunk in response:
                if chunk.text: text += chunk.text; stream_container.markdown(text + "▌")
            stream_container.markdown(text) 
        else: text = response.text
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
            if match: text = match.group(0)
            try: return json.loads(text)
            except: return None
        return text
    except Exception: return None

@st.cache_data(ttl=3600)
def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        search_params = {'db': 'pubmed', 'term': f"{query}", 'retmode': 'json', 'retmax': 50, 'sort': 'relevance'}
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response: id_list = json.loads(response.read().decode()).get('esearchresult', {}).get('idlist', [])
        if not id_list: return []
        fetch_params = {'db': 'pubmed', 'id': ','.join(id_list), 'retmode': 'xml'}
        with urllib.request.urlopen(base_url + "efetch.fcgi?" + urllib.parse.urlencode(fetch_params)) as response: root = ET.fromstring(response.read().decode())
        citations = []
        for article in root.findall('.//PubmedArticle'):
            medline = article.find('MedlineCitation')
            pmid = medline.find('PMID').text
            title = medline.find('Article/ArticleTitle').text
            # Authors
            author_list = article.findall('.//Author')
            authors_str = "Unknown"
            if author_list:
                authors = []
                for auth in author_list[:3]:
                    lname = auth.find('LastName')
                    init = auth.find('Initials')
                    if lname is not None and init is not None: authors.append(f"{lname.text} {init.text}")
                authors_str = ", ".join(authors)
                if len(author_list) > 3: authors_str += ", et al."
            # Year
            year_node = article.find('.//PubDate/Year')
            year = year_node.text if year_node is not None else "N/A"
            # Journal
            journal = medline.find('Article/Journal/Title').text if medline.find('Article/Journal/Title') is not None else "N/A"
            # Abstract
            abs_node = medline.find('Article/Abstract')
            abstract_text = " ".join([e.text for e in abs_node.findall('AbstractText') if e.text]) if abs_node is not None else "No abstract."
            citations.append({
                "id": pmid, "title": title, "authors": authors_str, "year": year, "journal": journal,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "abstract": abstract_text,
                "grade": "Un-graded", "rationale": "Not yet evaluated."
            })
        return citations
    except Exception as e: st.error(f"PubMed Search Error: {e}"); return []

def format_as_numbered_list(items):
    """Ensure numbered list formatting with a blank line between items.
    - Accepts list or string; outputs a string with "1. ..." and blank lines.
    """
    # If already a list, normalize and build with spacing
    if isinstance(items, list):
        clean_items = [re.sub(r'^\s*[\d\.\-\*]+\s*', '', str(item)).strip() for item in items if str(item).strip()]
        return "\n\n".join([f"{i+1}. {item}" for i, item in enumerate(clean_items)])

    # If it's a string, try to detect existing items and rebuild
    text = str(items or "").strip()
    if not text:
        return ""

    lines = [ln.rstrip() for ln in text.split("\n")]
    # Extract lines that look like items (start with number. or bullet)
    item_lines = []
    for ln in lines:
        m = re.match(r"^\s*(\d+\.|[-\*])\s+(.*)$", ln)
        if m:
            item_lines.append(m.group(2).strip())
        elif ln.strip():
            item_lines.append(ln.strip())
    # If we collected multiple logical items, rebuild with numbering + spacing
    if len(item_lines) >= 2:
        return "\n\n".join([f"{i+1}. {it}" for i, it in enumerate(item_lines)])

    # Otherwise, ensure at least single paragraph return
    # Also insert blank lines before any subsequent "N." occurrences
    text = re.sub(r"\n(?=(\d+\.)\s)", "\n\n", text)
    return text

def compute_textarea_height(text: str, min_rows: int = 10, max_rows: int = 100, line_px: int = 22, padding_px: int = 18, chars_per_line: int = 70) -> int:
    """
    Estimate a textarea height in pixels based on current text content.
    Streamlit doesn't auto-resize text_areas, so we approximate by rows.
    """
    if text is None:
        text = ""
    # Estimate visual lines including wrapping
    # Split on explicit newlines, then estimate wrapped rows per line
    est_lines = 0
    for block in text.split("\n\n"):
        for ln in block.split("\n"):
            length = len(ln.strip()) or 1
            est_lines += max(1, (length + chars_per_line - 1) // chars_per_line)
        # add one extra line between paragraphs for spacing
        est_lines += 1
    lines = max(min_rows, min(max_rows, est_lines or min_rows))
    return lines * line_px + padding_px

# ==========================================
# 3. SIDEBAR & SESSION INITIALIZATION
# ==========================================
with st.sidebar:
    try:
        if "CarePathIQ_Logo.png" in os.listdir():
            with open("CarePathIQ_Logo.png", "rb") as f:
                logo_data = base64.b64encode(f.read()).decode()
            st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><a href="https://carepathiq.org/" target="_blank"><img src="data:image/png;base64,{logo_data}" width="200" style="max-width: 100%;"></a></div>""", unsafe_allow_html=True)
    except Exception: pass

    st.title("AI Agent")
    st.divider()
    try:
        default_key = st.secrets.get("GEMINI_API_KEY", "")
    except:
        default_key = ""
    gemini_api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    model_options = ["Auto", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"]
    model_choice = st.selectbox("Model", model_options, index=0)
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success("AI Connected")
        st.divider()

        # Navigation Logic for sidebar buttons (only when activated)
        for p in PHASES:
            st.button(
                p,
                key=f"nav_{p}",
                width="stretch",
                type="primary" if st.session_state.get('current_phase_label') == p else "secondary",
                on_click=change_phase,
                args=(p,)
            )

        st.markdown(
            f"""
            <div style="background-color: #5D4037; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin: 15px 0;">
                Current Phase: <br><span style="font-size: 1.1em;">{st.session_state.get('current_phase_label', PHASES[0])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.progress(calculate_granular_progress())

# LANDING PAGE LOGIC
if not gemini_api_key:
    st.title("CarePathIQ AI Agent")
    st.markdown('<p style="font-size: 1.2em; color: #00695C; margin-top: -10px; margin-bottom: 20px;"><strong><em>Intelligently build and deploy clinical pathways</em></strong></p>', unsafe_allow_html=True)
    st.markdown("""<div style="background-color: #5D4037; padding: 15px; border-radius: 5px; color: white; margin-bottom: 20px;"><strong>Welcome.</strong> Please enter your <strong>Gemini API Key</strong> in the sidebar to activate the AI Agent. <br><a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #A9EED1; font-weight: bold; text-decoration: underline;">Get a free API key here</a>.</div>""", unsafe_allow_html=True)
    st.markdown(COPYRIGHT_HTML_FOOTER, unsafe_allow_html=True)
    st.stop()

if "current_phase_label" not in st.session_state:
    st.session_state.current_phase_label = PHASES[0]

if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "", "setting": "", "inclusion": "", "exclusion": "", "problem": "", "objectives": "", "schedule": [], "population": ""},
        "phase2": {"evidence": [], "mesh_query": ""},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}},
        "phase5": {"exec_summary": "", "beta_html": "", "expert_html": "", "edu_html": ""}
    }
if "suggestions" not in st.session_state:
    st.session_state.suggestions = {}
# --- FORCE MIGRATION FOR OLD DATA ---
if "pico_p" in st.session_state.data.get("phase2", {}):
    # Old PICO structure detected; clear Phase 2 data to force new layout
    st.session_state.data["phase2"] = {"evidence": [], "mesh_query": ""}
    # Optional: trigger a rerun if you want immediate effect, usually not needed if logic below is safe

# ==========================================
# 4. MAIN WORKFLOW LOGIC
# ==========================================
## --- PHASE NAVIGATION ---
try:
    radio_index = PHASES.index(st.session_state.current_phase_label)
except ValueError:
    radio_index = 0

# Use a callback to sync radio selection to current_phase_label
def sync_radio_to_phase():
    st.session_state.current_phase_label = st.session_state.top_nav_radio

# Avoid passing a default index when the session already has a value for this widget
if "top_nav_radio" in st.session_state and st.session_state.top_nav_radio in PHASES:
    phase = st.radio(
        "Workflow Phase",
        PHASES,
        horizontal=True,
        label_visibility="visible",
        key="top_nav_radio",
        on_change=sync_radio_to_phase,
    )
else:
    phase = st.radio(
        "Workflow Phase",
        PHASES,
        index=radio_index,
        horizontal=True,
        label_visibility="visible",
        key="top_nav_radio",
        on_change=sync_radio_to_phase,
    )
st.divider()

# --- PHASE 1 ---
if "Phase 1" in phase:
    # 1. TRIGGER FUNCTIONS (Callbacks)
    def trigger_p1_draft():
        # Only trigger if both fields have text
        c = st.session_state.p1_cond_input
        s = st.session_state.p1_setting
        if c and s:
            prompt = f"""
            Act as a Chief Medical Officer. For '{c}' in '{s}', generate a single JSON object with these 4 keys:
            1. "inclusion": Detailed inclusion criteria (formatted as a numbered list).
            2. "exclusion": Detailed exclusion criteria (formatted as a numbered list).
            3. "problem": A problem statement referencing care variation.
            4. "objectives": 3 SMART objectives (formatted as a numbered list).
            """
            data = get_gemini_response(prompt, json_mode=True)
            if data:
                # Use the helper to enforce numbered lists formatting
                st.session_state.data['phase1']['inclusion'] = format_as_numbered_list(data.get('inclusion', ''))
                st.session_state.data['phase1']['exclusion'] = format_as_numbered_list(data.get('exclusion', ''))
                st.session_state.data['phase1']['problem'] = str(data.get('problem', ''))
                st.session_state.data['phase1']['objectives'] = format_as_numbered_list(data.get('objectives', ''))
                
                # Force update keys used by widgets
                st.session_state['p1_inc'] = st.session_state.data['phase1']['inclusion']
                st.session_state['p1_exc'] = st.session_state.data['phase1']['exclusion']
                st.session_state['p1_prob'] = st.session_state.data['phase1']['problem']
                st.session_state['p1_obj'] = st.session_state.data['phase1']['objectives']

    def apply_refinements():
        refinement_text = st.session_state.p1_refine_input
        if refinement_text:
            current_data = st.session_state.data['phase1']
            prompt = f"""
            Update the following clinical pathway sections based on this specific user feedback: "{refinement_text}"
            
            Current Data:
            - Inclusion: {current_data['inclusion']}
            - Exclusion: {current_data['exclusion']}
            - Problem: {current_data['problem']}
            - Objectives: {current_data['objectives']}
            
            Return a JSON object with the updated keys: "inclusion", "exclusion", "problem", "objectives".
            """
            data = get_gemini_response(prompt, json_mode=True)
            if data:
                st.session_state.data['phase1']['inclusion'] = format_as_numbered_list(data.get('inclusion', ''))
                st.session_state.data['phase1']['exclusion'] = format_as_numbered_list(data.get('exclusion', ''))
                st.session_state.data['phase1']['problem'] = str(data.get('problem', ''))
                st.session_state.data['phase1']['objectives'] = format_as_numbered_list(data.get('objectives', ''))
                
                st.session_state['p1_inc'] = st.session_state.data['phase1']['inclusion']
                st.session_state['p1_exc'] = st.session_state.data['phase1']['exclusion']
                st.session_state['p1_prob'] = st.session_state.data['phase1']['problem']
                st.session_state['p1_obj'] = st.session_state.data['phase1']['objectives']

    # 2. SYNC FUNCTION (General)
    def sync_p1_widgets():
        st.session_state.data['phase1']['condition'] = st.session_state.get('p1_cond_input', '')
        st.session_state.data['phase1']['inclusion'] = st.session_state.get('p1_inc', '')
        st.session_state.data['phase1']['exclusion'] = st.session_state.get('p1_exc', '')
        st.session_state.data['phase1']['setting'] = st.session_state.get('p1_setting', '')
        st.session_state.data['phase1']['problem'] = st.session_state.get('p1_prob', '')
        st.session_state.data['phase1']['objectives'] = st.session_state.get('p1_obj', '')

    # Initialize State Keys if missing
    if 'p1_cond_input' not in st.session_state: st.session_state['p1_cond_input'] = st.session_state.data['phase1'].get('condition', '')
    if 'p1_inc' not in st.session_state: st.session_state['p1_inc'] = st.session_state.data['phase1'].get('inclusion', '')
    if 'p1_exc' not in st.session_state: st.session_state['p1_exc'] = st.session_state.data['phase1'].get('exclusion', '')
    if 'p1_setting' not in st.session_state: st.session_state['p1_setting'] = st.session_state.data['phase1'].get('setting', '')
    if 'p1_prob' not in st.session_state: st.session_state['p1_prob'] = st.session_state.data['phase1'].get('problem', '')
    if 'p1_obj' not in st.session_state: st.session_state['p1_obj'] = st.session_state.data['phase1'].get('objectives', '')

    st.title("Phase 1: Scoping & Charter")
    styled_info("<b>Tip:</b> The AI agent will auto-draft sections <b>after you enter both the Clinical Condition and Care Setting</b>. You can then manually edit any generated text to refine the content.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. Clinical Focus")
        # SPECIFIC TRIGGER ON CARE SETTING CHANGE via on_change
        cond_input = st.text_input("Clinical Condition", placeholder="e.g. Chest Pain", key="p1_cond_input", on_change=sync_p1_widgets)
        setting_input = st.text_input("Care Setting", placeholder="e.g. Emergency Department", key="p1_setting", on_change=trigger_p1_draft)
        
        st.subheader("2. Target Population")
        st.text_area(
            "Inclusion Criteria",
            height=compute_textarea_height(st.session_state.get('p1_inc', ''), min_rows=14),
            key="p1_inc",
            on_change=sync_p1_widgets,
        )
        with st.expander("View full", expanded=False):
            st.markdown(st.session_state.get('p1_inc', '') or "_Empty_")
        st.text_area(
            "Exclusion Criteria",
            height=compute_textarea_height(st.session_state.get('p1_exc', ''), min_rows=14),
            key="p1_exc",
            on_change=sync_p1_widgets,
        )
        with st.expander("View full", expanded=False):
            st.markdown(st.session_state.get('p1_exc', '') or "_Empty_")
        
    with col2:
        st.subheader("3. Clinical Gap / Problem Statement")
        st.text_area(
            "Problem Statement / Clinical Gap",
            height=compute_textarea_height(st.session_state.get('p1_prob', ''), min_rows=12),
            key="p1_prob",
            on_change=sync_p1_widgets,
            label_visibility="collapsed",
        )
        with st.expander("View full", expanded=False):
            st.markdown(st.session_state.get('p1_prob', '') or "_Empty_")
        
        st.subheader("4. Goals")
        st.text_area(
            "Project Goals",
            height=compute_textarea_height(st.session_state.get('p1_obj', ''), min_rows=14),
            key="p1_obj",
            on_change=sync_p1_widgets,
            label_visibility="collapsed",
        )
        with st.expander("View full", expanded=False):
            st.markdown(st.session_state.get('p1_obj', '') or "_Empty_")

    # Manual Trigger Button using Callback
    if st.button("Regenerate Draft", on_click=trigger_p1_draft):
         pass

    st.divider()
    
    # Natural Language Refinement Section
    st.subheader("Refine Content")
    st.text_area("Custom Refinement", placeholder="E.g., 'Make the inclusion criteria strictly for patients over 65'...", key="p1_refine_input")
    if st.button("Apply Refinements", type="primary", on_click=apply_refinements):
        st.success("Refinements applied!")

    st.divider()
    st.subheader("5. Project Timeline (Gantt Chart)")
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
    edited_sched = st.data_editor(df_sched, num_rows="dynamic", width="stretch", key="sched_editor", column_config={"Stage": st.column_config.TextColumn("Stage", width="medium")})
    if not edited_sched.empty:
        st.session_state.data['phase1']['schedule'] = edited_sched.to_dict('records')
        chart_data = edited_sched.copy()
        chart_data.dropna(subset=['Start', 'End', 'Stage'], inplace=True)
        chart_data['Start'] = pd.to_datetime(chart_data['Start'])
        chart_data['End'] = pd.to_datetime(chart_data['End'])
        if not chart_data.empty:
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Start', title='Date'), x2='End', y=alt.Y('Stage', sort=None), color='Owner', tooltip=['Stage', 'Start', 'End', 'Owner']
            ).properties(height=300).interactive()
            st.altair_chart(chart, use_container_width=True)
    
    if st.button("Generate Project Charter", type="primary", use_container_width=True):
        d = st.session_state.data['phase1']
        if not d['condition'] or not d['problem']: st.error("Please fill in Condition and Problem.")
        else:
            with st.status("Generating Project Charter...", expanded=True) as status:
                p_ihi = f"Act as QI Advisor (IHI Model). Draft Charter for {d['condition']}. Problem: {d['problem']}. Scope: {d['inclusion']}. Return JSON: project_description, rationale, expected_outcomes, aim_statement, outcome_measures, process_measures, balancing_measures, initial_activities, change_ideas, stakeholders, barriers, boundaries (return as dict: in_scope, out_of_scope)."
                res = get_gemini_response(p_ihi, json_mode=True)
                if res:
                    st.session_state.data['phase1']['ihi_content'] = res
                    doc = create_word_docx(st.session_state.data['phase1'])
                    if doc:
                        status.update(label="Ready!", state="complete")
                        st.download_button("Download Project Charter (.docx)", doc, f"Project_Charter_{d['condition']}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    render_bottom_navigation()

# --- PHASE 2 ---
elif "Phase 2" in phase:
    st.title("Phase 2: Rapid Evidence Appraisal")

    # Build default query from Phase 1 if none saved
    default_q = st.session_state.data['phase2'].get('mesh_query', '')
    if not default_q and st.session_state.data['phase1']['condition']:
        c = st.session_state.data['phase1']['condition']
        s = st.session_state.data['phase1']['setting']
        default_q = f"managing patients with {c} in {s}"

    # Auto-run search once per distinct default query when evidence is empty
    if (
        not st.session_state.data['phase2']['evidence']
        and default_q
        and st.session_state.get('p2_last_autorun_query') != default_q
    ):
        st.session_state.data['phase2']['mesh_query'] = default_q
        full_query = f"{default_q} AND (\"last 5 years\"[dp])"
        with ai_activity("Searching PubMed and auto‑grading…"):
            results = search_pubmed(full_query)
            st.session_state.data['phase2']['evidence'] = results
            if results:
                prompt = (
                    "Assign GRADE (High/Mod/Low/Very Low) and short Rationale for: "
                    f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in results])}. "
                    "Return JSON {ID: {grade, rationale}}"
                )
                grades = get_gemini_response(prompt, json_mode=True)
                if grades:
                    for e in st.session_state.data['phase2']['evidence']:
                        if e['id'] in grades:
                            e.update(grades[e['id']])
        st.session_state['p2_last_autorun_query'] = default_q

    # Refinement with the current query prefilled
    with st.expander("Refine search", expanded=False):
        current_q = st.session_state.data['phase2'].get('mesh_query', default_q)
        q = st.text_input(
            "PubMed Search Query",
            value=current_q or "",
            placeholder="Enter a custom query (optional)",
            key="p2_query_input",
        )
        col_run, col_open = st.columns([1, 1])
        with col_run:
            if st.button("Run Search", type="primary", key="p2_search_run"):
                full_query = f"{q} AND (\"last 5 years\"[dp])"
                st.session_state.data['phase2']['mesh_query'] = q
                with ai_activity("Searching PubMed and auto‑grading…"):
                    results = search_pubmed(full_query)
                    st.session_state.data['phase2']['evidence'] = results
                    if results:
                        prompt = (
                            "Assign GRADE (High/Mod/Low/Very Low) and short Rationale for: "
                            f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in results])}. "
                            "Return JSON {ID: {grade, rationale}}"
                        )
                        grades = get_gemini_response(prompt, json_mode=True)
                        if grades:
                            for e in st.session_state.data['phase2']['evidence']:
                                if e['id'] in grades:
                                    e.update(grades[e['id']])
                st.session_state['p2_last_autorun_query'] = q
        with col_open:
            if q:
                full_q = f"{q} AND (\"last 5 years\"[dp])"
                st.link_button("Open in PubMed ↗", f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(full_q)}", type="secondary")

    if st.session_state.data['phase2']['evidence']:
        st.markdown("### Evidence Table")
        # Always provide an 'Open in PubMed' action with current query
        if st.session_state.data['phase2'].get('mesh_query'):
            search_q = st.session_state.data['phase2']['mesh_query']
            full_q = f"{search_q} AND (\"last 5 years\"[dp])"
            st.link_button("Open in PubMed ↗", f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(full_q)}", type="secondary")
        
        # TOP TIP: GRADE DEFINITIONS
        styled_info("""<b>Tip: GRADE Criteria Guide</b><br>
        - <b>High (A):</b> Further research is very unlikely to change our confidence in the estimate of effect.<br>
        - <b>Moderate (B):</b> Further research is likely to have an important impact on our confidence in the estimate of effect and may change the estimate.<br>
        - <b>Low (C):</b> Further research is very likely to have an important impact on our confidence in the estimate of effect and is likely to change the estimate.<br>
        - <b>Very Low (D):</b> We are very uncertain about the estimate.""")

        col_filter, col_clear, col_regrade = st.columns([3, 1, 2])
        with col_filter:
            # Default filters set to High, Moderate, Low
            selected_grades = st.multiselect("Filter by GRADE:", ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], default=["High (A)", "Moderate (B)", "Low (C)"])
        with col_clear:
            if st.button("Clear List"):
                st.session_state.data['phase2']['evidence'] = []
                st.rerun()
        
        # Sort Logic: High to Low
        grade_order = {"High (A)": 0, "Moderate (B)": 1, "Low (C)": 2, "Very Low (D)": 3, "Un-graded": 4}
        
        evidence_data = st.session_state.data['phase2']['evidence']
        # Apply Sorting
        evidence_data.sort(key=lambda x: grade_order.get(x.get('grade', 'Un-graded'), 4))
        
        # Filter for Display
        display_data = [e for e in evidence_data if e.get('grade', 'Un-graded') in selected_grades]
        df_ev = pd.DataFrame(display_data)
        
        if not df_ev.empty:

            edited_ev = st.data_editor(
                df_ev, 
                column_config={
                    "id": st.column_config.TextColumn("PMID", disabled=True, width="small"),
                    "title": st.column_config.TextColumn("Title", width="medium"),
                    "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], width="small"),
                    "rationale": st.column_config.TextColumn("Rationale", width="large"),
                    # Hide other columns from view but keep in data
                    "year": None, "journal": None, "authors": None, "abstract": None, "url": None
                }, 
                column_order=["id", "title", "grade", "rationale"],
                hide_index=True, width="stretch", key="ev_editor"
            )
            
            # BOTTOM TIP
            styled_info("<b>Tip:</b> The table above shows key details. Download the CSV below to see the <b>full abstract, authors, journal, and year</b>.")
            
            # Export Full Data (Not just visible)
            full_df = pd.DataFrame(evidence_data)
            export_widget(full_df.to_csv(index=False).encode('utf-8'), "evidence_table.csv", "text/csv", label="Download Evidence Table (CSV)")
    else:
        # If nothing to show, provide a helpful prompt and the PubMed link if available
        st.info("No results yet. Refine the search or ensure Phase 1 has a condition and setting.")
        if st.session_state.data['phase2'].get('mesh_query'):
            search_q = st.session_state.data['phase2']['mesh_query']
            full_q = f"{search_q} AND (\"last 5 years\"[dp])"
            st.link_button("Open in PubMed ↗", f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(full_q)}", type="secondary")
    render_bottom_navigation()

# --- PHASE 3 ---
elif "Phase 3" in phase:
    st.title("Phase 3: Decision Science")
    styled_info("<b>Tip:</b> Build your clinical pathway logic. Use the AI agent to auto-draft nodes or manually edit the table.")
    
    col_tools, col_editor = st.columns([1, 3])
    with col_tools:
        if st.button("Auto-Draft Logic (AI)", type="primary", width="stretch"):
            cond = st.session_state.data['phase1']['condition']
            with ai_activity("Drafting pathway with the AI agent…"):
                prompt = f"Act as Clinical Decision Scientist. Create pathway for {cond}. Return JSON LIST. Objects: id, type (Start|Decision|Process|End), label, detail, labs, imaging, medications, dosage, branches."
                nodes = get_gemini_response(prompt, json_mode=True)
                if nodes:
                    st.session_state.data['phase3']['nodes'] = harden_nodes(nodes)
                    st.rerun()
        if st.button("Clear All", width="stretch"):
            st.session_state.data['phase3']['nodes'] = []
            st.rerun()
        st.write("")
        if st.button("Auto-Populate Evidence", width="stretch"):
             with ai_activity("Matching pathway steps to evidence…"):
                 ev_titles = [f"{e['id']}: {e['title']}" for e in st.session_state.data['phase2']['evidence']]
                 for node in st.session_state.data['phase3']['nodes']:
                     if not node.get('evidence'):
                         p_match = f"Match step '{node['label']}' to best evidence ID from: {ev_titles}. Return ID."
                         res = get_gemini_response(p_match)
                         if res: node['evidence'] = res.strip()
                 st.rerun()

    with col_editor:
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        edited_nodes = st.data_editor(
            df_nodes, 
            num_rows="dynamic", 
            width="stretch", 
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
    render_bottom_navigation()

# --- PHASE 4 ---
elif "Phase 4" in phase:
    st.title("Phase 4: User Interface Design")
    styled_info("<b>Tip:</b> Evaluate your pathway against Nielsen's 10 Usability Heuristics. The AI agent can provide suggestions for each criterion.")
    
    nodes = st.session_state.data['phase3']['nodes']
    col_vis, col_heuristics = st.columns([2, 1])
    with col_vis:
        st.subheader("Pathway Visualization")
        c_view1, c_view2 = st.columns([1, 2])
        with c_view1:
            orientation = st.selectbox("Orientation", ["Vertical (TD)", "Horizontal (LR)"], index=0)
            mermaid_orient = "TD" if "Vertical" in orientation else "LR"
        mermaid_code = generate_mermaid_code(nodes, mermaid_orient)
        components.html(f'<div class="mermaid">{mermaid_code}</div><script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script><script>mermaid.initialize({{startOnLoad:true}});</script>', height=600, scrolling=True)
        with st.expander("Edit Pathway Data", expanded=False):
            df_p4 = pd.DataFrame(nodes)
            edited_p4 = st.data_editor(df_p4, num_rows="dynamic", key="p4_editor", width="stretch")
            if not df_p4.equals(edited_p4):
                st.session_state.data['phase3']['nodes'] = edited_p4.to_dict('records')
                st.rerun()

    with col_heuristics:
        st.subheader("Heuristics")
        if st.button("Analyze Risks"):
            with ai_activity("Analyzing usability heuristics…"):
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
                    with ai_activity("Applying AI‑recommended fix…"):
                        p_fix = f"Update this JSON to fix {k} ({v}): {json.dumps(nodes)}. Return JSON."
                        new_nodes = get_gemini_response(p_fix, json_mode=True)
                        if new_nodes:
                            st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                            st.rerun()
    st.divider()
    custom_edit = st.text_area("Custom Refinement", placeholder="E.g., 'Add a blood pressure check after triage'", label_visibility="collapsed")
    if st.button("Apply Changes", type="primary"):
         with ai_activity("Applying your changes…"):
             p_cust = f"Update logic based on: {custom_edit}. Current: {json.dumps(nodes)}. Return JSON."
             new_nodes = get_gemini_response(p_cust, json_mode=True)
             if new_nodes:
                 st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                 st.rerun()
    render_bottom_navigation()

# --- PHASE 5 ---
elif "Phase 5" in phase:
    st.title("Phase 5: Operationalize")
    styled_info("<b>Tip:</b> Generate deployment materials for different audiences. The AI agent creates executive summaries, expert guides, and education plans.")
    
    st.markdown("### Operational Toolkit")
    cond = st.session_state.data['phase1']['condition'] or "Pathway"
    
    # Configuration Row
    col_a, col_e = st.columns(2)
    with col_a:
        st.write("Target Audience")
        audience_options = ["Multidisciplinary Team", "Physicians", "Nurses", "Informaticists"]
        audience_sel = st.selectbox("Select or type custom audience", [""] + audience_options, index=0, label_visibility="collapsed")
        if audience_sel:
            audience = st.text_input("Audience (edit if needed)", value=audience_sel, label_visibility="collapsed")
        else:
            audience = st.text_input("Enter custom audience", placeholder="e.g., Nurse Practitioners", label_visibility="collapsed")
    with col_e:
        email_target = st.text_input("Recipient Email (for forms and certificates)", placeholder="you@hospital.org")

    st.divider()
    
    # 3-COLUMN HORIZONTAL LAYOUT
    c1, c2, c3 = st.columns(3)
    
    # 1. Expert Panel Feedback Form
    with c1:
        st.markdown("#### 1. Expert Panel Feedback Form")
        if st.button("Generate Form", type="primary", use_container_width=True, key="btn_expert_gen"):
            with ai_activity("Generating expert feedback form…"):
                nodes = st.session_state.data['phase3']['nodes']
                s_e_nodes = [n for n in nodes if n.get('type') in ['Start', 'End']]
                p_nodes = [n for n in nodes if n.get('type') == 'Process']
                d_nodes = [n for n in nodes if n.get('type') == 'Decision']
                s_e_str = "\n".join([f"- {n.get('label')}" for n in s_e_nodes])
                p_str = "\n".join([f"- {n.get('label')}" for n in p_nodes])
                d_str = "\n".join([f"- {n.get('label')}" for n in d_nodes])

                prompt = f"""
                Create HTML5 Form for Expert Panel Feedback. Audience: {audience}.
                Intro: "Thank you for serving on the expert panel for {cond}."
                Logic:
                Iterate through these nodes:
                Start/End: {s_e_str}
                Decisions: {d_str}
                Process: {p_str}
                For EACH node, create a Checkbox. If checked, show:
                1. "Proposed Change" (Textarea)
                2. "Justification" (Select: Peer-Reviewed Literature, National Guideline, Institutional Policy, Resource Limitations, None)
                3. "Justification Detail" (Textarea)
                Form Action: 'https://formsubmit.co/{email_target}'
                Add hidden input: <input type="hidden" name="_subject" value="Expert Panel Feedback - {cond}">
                """
                st.session_state.data['phase5']['expert_html'] = get_gemini_response(prompt)
                if st.session_state.data['phase5']['expert_html']: 
                    st.session_state.data['phase5']['expert_html'] += COPYRIGHT_HTML_FOOTER
        
        if st.session_state.data['phase5'].get('expert_html'):
            st.download_button("Download Form (.html)", st.session_state.data['phase5']['expert_html'], "ExpertPanelForm.html", use_container_width=True)
            st.info("📧 Form submissions will be sent to the email address provided above.")
            with st.expander("Refine Form"):
                refine_expert = st.text_area("Edit request", height=70, key="ref_expert", label_visibility="collapsed")
                if st.button("Update Form", use_container_width=True, key="update_expert"):
                    with ai_activity("Updating expert feedback form…"):
                        new_html = get_gemini_response(f"Update this HTML: {st.session_state.data['phase5']['expert_html']} Request: {refine_expert}")
                    if new_html: st.session_state.data['phase5']['expert_html'] = new_html + COPYRIGHT_HTML_FOOTER; st.rerun()
    
    # 2. Beta Testing Form
    with c2:
        st.markdown("#### 2. Beta Testing Form")
        if st.button("Generate Form", type="primary", use_container_width=True, key="btn_beta_gen"):
            with ai_activity("Generating beta testing form…"):
                prompt = f"""
                Create HTML5 Form. Title: 'Beta Testing Feedback for {cond}'. Audience: {audience}. 
                Form Action: 'https://formsubmit.co/{email_target}'.
                Questions: 
                1. Usability Rating (1-5 scale)
                2. Bugs/Issues Encountered (Textarea)
                3. Workflow Integration (Select: Excellent, Good, Fair, Poor)
                4. Additional Feedback (Textarea)
                Add hidden input: <input type="hidden" name="_subject" value="Beta Testing Feedback - {cond}">
                """
                st.session_state.data['phase5']['beta_html'] = get_gemini_response(prompt)
                if st.session_state.data['phase5']['beta_html']: 
                    st.session_state.data['phase5']['beta_html'] += COPYRIGHT_HTML_FOOTER
        
        if st.session_state.data['phase5'].get('beta_html'):
            st.download_button("Download Form (.html)", st.session_state.data['phase5']['beta_html'], "BetaTestingForm.html", use_container_width=True)
            st.info("📧 Form submissions will be sent to the email address provided above.")
            with st.expander("Refine Form"):
                refine_beta = st.text_area("Edit request", height=70, key="ref_beta", label_visibility="collapsed")
                if st.button("Update Form", use_container_width=True, key="update_beta"):
                    with ai_activity("Updating beta testing form…"):
                        new_html = get_gemini_response(f"Update HTML: {st.session_state.data['phase5']['beta_html']} Request: {refine_beta}")
                    if new_html: st.session_state.data['phase5']['beta_html'] = new_html + COPYRIGHT_HTML_FOOTER; st.rerun()
    
    # 3. Staff Education Module
    with c3:
        st.markdown("#### 3. Staff Education Module")
        if st.button("Generate Module", type="primary", use_container_width=True, key="btn_edu_gen"):
            with ai_activity("Generating education module…"):
                prompt = f"""
                Create HTML Education Module for {cond}. Audience: {audience}.
                1. Key Clinical Points (summary section)
                2. Interactive 5 Question Quiz with immediate feedback (correct/incorrect with explanations)
                3. Certificate of Completion: 
                   - User enters Name and Email
                   - On completion, display printable certificate
                   - Submit form to: 'https://formsubmit.co/{email_target}' to send certificate copy to admin
                   - Add hidden input: <input type="hidden" name="_subject" value="Education Certificate - {cond}">
                """
                st.session_state.data['phase5']['edu_html'] = get_gemini_response(prompt)
                if st.session_state.data['phase5']['edu_html']: 
                    st.session_state.data['phase5']['edu_html'] += COPYRIGHT_HTML_FOOTER
        
        if st.session_state.data['phase5'].get('edu_html'):
            st.download_button("Download Module (.html)", st.session_state.data['phase5']['edu_html'], "EducationModule.html", use_container_width=True)
            st.info("🎓 Certificates will be emailed to both the learner and the address provided above.")
            with st.expander("Refine Module"):
                refine_edu = st.text_area("Edit request", height=70, key="ref_edu", label_visibility="collapsed")
                if st.button("Update Module", use_container_width=True, key="update_edu"):
                    with ai_activity("Updating education module…"):
                        new_html = get_gemini_response(f"Update HTML: {st.session_state.data['phase5']['edu_html']} Request: {refine_edu}")
                    if new_html: st.session_state.data['phase5']['edu_html'] = new_html + COPYRIGHT_HTML_FOOTER; st.rerun()
    
    st.divider()
    
    # 4. Executive Summary (Full Width)
    st.subheader("4. Executive Summary")
    col_gen, col_space = st.columns([1, 3])
    with col_gen:
        if st.button("Draft Executive Summary", type="primary", use_container_width=True):
            with ai_activity("Drafting executive summary…"):
                st.session_state.data['phase5']['exec_summary'] = get_gemini_response(f"Write executive summary for {cond} pathway. Audience: Hospital Leadership.")

    if st.session_state.data['phase5'].get('exec_summary'):
        st.markdown(st.session_state.data['phase5']['exec_summary'])
        doc = create_exec_summary_docx(st.session_state.data['phase5']['exec_summary'], cond)
        if doc: st.download_button("Download Executive Summary (.docx)", doc, "ExecSummary.docx")
        with st.expander("Refine Summary"):
            refine_exec = st.text_area("Edit request", height=70, key="ref_exec", label_visibility="collapsed")
            if st.button("Update Summary"):
                with ai_activity("Updating executive summary…"):
                    new_sum = get_gemini_response(f"Update text: {st.session_state.data['phase5']['exec_summary']} Request: {refine_exec}")
                if new_sum: st.session_state.data['phase5']['exec_summary'] = new_sum; st.rerun()

    render_bottom_navigation()

st.markdown(COPYRIGHT_HTML_FOOTER, unsafe_allow_html=True)