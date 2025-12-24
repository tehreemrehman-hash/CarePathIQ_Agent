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
    import graphviz  # for diagram exports (SVG/PNG/DOT)
except ImportError:
    # Safe fallback to prevent crash if libraries are missing
    Document = None
    plt = None
    mdates = None
    graphviz = None

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
    /* HIDE HEADER DEPLOYMENT LINKS BUT KEEP CONTENT ANCHOR LINKS */
    [data-testid="stHeaderAction"] { display: none !important; visibility: hidden !important; opacity: 0 !important; }
    
    /* Make anchor links visible for content headings */
    .stMarkdown h1 a.anchor-link, 
    .stMarkdown h2 a.anchor-link, 
    .stMarkdown h3 a.anchor-link { 
        display: inline-block !important; 
        opacity: 1 !important;
        visibility: visible !important;
        height: auto !important; 
        width: auto !important; 
        margin-left: 0.5rem !important;
    }
    h1 > a.anchor-link, h2 > a.anchor-link, h3 > a.anchor-link { 
        display: inline-block !important; 
        opacity: 1 !important;
        visibility: visible !important;
    }
    
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
    
    /* GRADE FILTER MULTISELECT */
    div[data-testid="stMultiSelect"] label:has(+ div[data-baseweb="select"]) {
        background-color: #FFB0C9 !important;
        color: black !important;
        padding: 8px 12px !important;
        border-radius: 5px !important;
        border: 1px solid black !important;
        display: inline-block !important;
        margin-bottom: 8px !important;
        font-weight: 500 !important;
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
        col_prev, _, col_next = st.columns([1, 2, 1])
        if current_idx > 0:
            prev_phase = PHASES[current_idx - 1]
            with col_prev:
                st.button(f"{prev_phase.split(':')[0]}", key="bottom_prev", use_container_width=True, on_click=change_phase, args=(prev_phase,))
        if current_idx < len(PHASES) - 1:
            next_phase = PHASES[current_idx + 1]
            with col_next:
                st.button(f"{next_phase.split(':')[0]}", key="bottom_next", use_container_width=True, type="primary", on_click=change_phase, args=(next_phase,))

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
        ax.barh(y_pos, df['Duration'], left=mdates.date2num(df['Start']), align='center', color='#5D4037', alpha=0.8)
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
    try:
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
    except Exception as e:
        st.error(f"Error generating document: {str(e)}")
        return None

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

def format_citation_line(entry, style="APA"):
    """Lightweight formatter for citation strings based on available PubMed fields."""
    authors = (entry.get("authors") or "Unknown").rstrip(".")
    title = (entry.get("title") or "Untitled").rstrip(".")
    journal = (entry.get("journal") or "Journal").rstrip(".")
    year = entry.get("year") or "n.d."
    pmid = entry.get("id") or ""
    if style == "MLA":
        return f"{authors}. \"{title}.\" {journal}, {year}. PMID {pmid}."
    if style == "Vancouver":
        return f"{authors}. {title}. {journal}. {year}. PMID:{pmid}."
    # Default APA
    return f"{authors} ({year}). {title}. {journal}. PMID: {pmid}."

def create_references_docx(citations, style="APA"):
    if Document is None or not citations:
        return None
    doc = Document()
    doc.add_heading(f"References ({style})", 0)
    for idx, entry in enumerate(citations, start=1):
        line = format_citation_line(entry, style)
        doc.add_paragraph(f"{idx}. {line}")
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
        safe_role = re.sub(r'[^A-Za-z0-9_]', '_', str(role or 'Unassigned'))
        escaped_role = str(role or '').replace('"', "'").replace('\n', ' ')
        code += f"    subgraph {safe_role}[\"{escaped_role}\"]\n"
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

# --- GRAPH EXPORT HELPERS (Graphviz/DOT) ---
def _escape_label(text: str) -> str:
    if text is None:
        return ""
    # Escape quotes and backslashes for DOT labels
    return str(text).replace("\\", "\\\\").replace("\"", "'").replace("\n", "\\n")

def dot_from_nodes(nodes, orientation="TD") -> str:
    """Generate Graphviz DOT source from pathway nodes. Does not require graphviz package."""
    if not nodes:
        return "digraph G {\n  // No nodes\n}"
    valid_nodes = harden_nodes(nodes)
    from collections import defaultdict
    swimlanes = defaultdict(list)
    for i, n in enumerate(valid_nodes):
        swimlanes[n.get('role', 'Unassigned')].append((i, n))
    rankdir = 'TB' if orientation == 'TD' else 'LR'
    lines = ["digraph G {", f"  rankdir={rankdir};", "  node [fontname=Helvetica];", "  edge [fontname=Helvetica];"]
    node_id_map = {}
    # Clusters by role
    for role, n_list in swimlanes.items():
        cluster_name = re.sub(r"[^A-Za-z0-9_]", "_", str(role) or "Unassigned")
        lines.append(f"  subgraph cluster_{cluster_name} {{")
        lines.append(f"    label=\"{_escape_label(role)}\";")
        lines.append("    style=filled; color=lightgrey;")
        for i, n in n_list:
            nid = f"N{i}"; node_id_map[i] = nid
            label = _escape_label(n.get('label', 'Step'))
            detail = _escape_label(n.get('detail', ''))
            meds = _escape_label(n.get('medications', ''))
            if meds:
                detail = f"{detail}\\nMeds: {meds}" if detail else f"Meds: {meds}"
            full_label = f"{label}\\n{detail}" if detail else label
            ntype = n.get('type', 'Process')
            if ntype == 'Decision': shape, fill = 'diamond', '#F8CECC'
            elif ntype in ('Start', 'End'): shape, fill = 'oval', '#D5E8D4'
            else: shape, fill = 'box', '#FFF2CC'
            lines.append(f"    {nid} [label=\"{full_label}\", shape={shape}, style=filled, fillcolor=\"{fill}\"];")
        lines.append("  }")
    # Edges
    for i, n in enumerate(valid_nodes):
        src = node_id_map.get(i)
        if not src:
            continue
        if n.get('type') == 'Decision' and 'branches' in n:
            for b in n.get('branches', []):
                t = b.get('target')
                lbl = _escape_label(b.get('label', 'Yes'))
                if isinstance(t, (int, float)) and 0 <= int(t) < len(valid_nodes):
                    dst = node_id_map.get(int(t))
                    if dst:
                        lines.append(f"  {src} -> {dst} [label=\"{lbl}\"];")
        elif i + 1 < len(valid_nodes):
            dst = node_id_map.get(i + 1)
            if dst:
                lines.append(f"  {src} -> {dst};")
    lines.append("}")
    return "\n".join(lines)

def build_graphviz_from_nodes(nodes, orientation="TD"):
    """Build a graphviz.Digraph from nodes if graphviz is available; otherwise return None."""
    if graphviz is None:
        return None
    valid_nodes = harden_nodes(nodes or [])
    from collections import defaultdict
    swimlanes = defaultdict(list)
    for i, n in enumerate(valid_nodes):
        swimlanes[n.get('role', 'Unassigned')].append((i, n))
    rankdir = 'TB' if orientation == 'TD' else 'LR'
    g = graphviz.Digraph(format='svg')
    g.attr(rankdir=rankdir)
    g.attr('node', fontname='Helvetica')
    g.attr('edge', fontname='Helvetica')
    node_id_map = {}
    for role, n_list in swimlanes.items():
        with g.subgraph(name=f"cluster_{re.sub(r'[^A-Za-z0-9_]', '_', str(role) or 'Unassigned')}") as c:
            c.attr(label=str(role))
            c.attr(style='filled', color='lightgrey')
            for i, n in n_list:
                nid = f"N{i}"; node_id_map[i] = nid
                label = _escape_label(n.get('label', 'Step'))
                detail = _escape_label(n.get('detail', ''))
                meds = _escape_label(n.get('medications', ''))
                if meds:
                    detail = f"{detail}\\nMeds: {meds}" if detail else f"Meds: {meds}"
                full_label = f"{label}\\n{detail}" if detail else label
                ntype = n.get('type', 'Process')
                if ntype == 'Decision': shape, fill = 'diamond', '#F8CECC'
                elif ntype in ('Start', 'End'): shape, fill = 'oval', '#D5E8D4'
                else: shape, fill = 'box', '#FFF2CC'
                c.node(nid, full_label, shape=shape, style='filled', fillcolor=fill)
    for i, n in enumerate(valid_nodes):
        src = node_id_map.get(i)
        if not src:
            continue
        if n.get('type') == 'Decision' and 'branches' in n:
            for b in n.get('branches', []):
                t = b.get('target'); lbl = _escape_label(b.get('label', 'Yes'))
                if isinstance(t, (int, float)) and 0 <= int(t) < len(valid_nodes):
                    dst = node_id_map.get(int(t))
                    if dst:
                        g.edge(src, dst, label=lbl)
        elif i + 1 < len(valid_nodes):
            dst = node_id_map.get(i + 1)
            if dst:
                g.edge(src, dst)
    return g

def render_graphviz_bytes(graph, fmt="svg"):
    """Render a graphviz.Digraph to bytes if possible, else return None."""
    if graphviz is None or graph is None:
        return None
    try:
        return graph.pipe(format=fmt)
    except Exception:
        return None

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
    st.markdown('<p style="font-size: 1.2em; color: #5D4037; margin-top: -10px; margin-bottom: 20px;"><strong><em>Intelligently build and deploy clinical pathways</em></strong></p>', unsafe_allow_html=True)
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

# Prominent phase header
st.markdown(
    "<div style='font-weight: 800; font-size: 1.1rem;'>AI Agent Phase</div>",
    unsafe_allow_html=True,
)

# Avoid passing a default index when the session already has a value for this widget
if "top_nav_radio" in st.session_state and st.session_state.top_nav_radio in PHASES:
    phase = st.radio(
        "AI Agent Phase",
        PHASES,
        horizontal=True,
        label_visibility="collapsed",
        key="top_nav_radio",
        on_change=sync_radio_to_phase,
    )
else:
    phase = st.radio(
        "AI Agent Phase",
        PHASES,
        index=radio_index,
        horizontal=True,
        label_visibility="collapsed",
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
            with ai_activity("Drafting Phase 1 content…"):
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
            else:
                st.error("Failed to generate content. Please check your API key and try again.")

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
            else:
                st.error("Failed to apply refinements. Please try again.")

    # 2. SYNC FUNCTION (General)
    def sync_p1_widgets():
        st.session_state.data['phase1']['condition'] = st.session_state.get('p1_cond_input', '')
        st.session_state.data['phase1']['inclusion'] = st.session_state.get('p1_inc', '')
        st.session_state.data['phase1']['exclusion'] = st.session_state.get('p1_exc', '')
        st.session_state.data['phase1']['setting'] = st.session_state.get('p1_setting', '')
        st.session_state.data['phase1']['problem'] = st.session_state.get('p1_prob', '')
        st.session_state.data['phase1']['objectives'] = st.session_state.get('p1_obj', '')

    def sync_and_draft():
        """Persist current inputs, then trigger draft generation."""
        sync_p1_widgets()
        trigger_p1_draft()

    # Always sync widget keys with saved data when entering Phase 1
    st.session_state['p1_cond_input'] = st.session_state.data['phase1'].get('condition', '')
    st.session_state['p1_inc'] = st.session_state.data['phase1'].get('inclusion', '')
    st.session_state['p1_exc'] = st.session_state.data['phase1'].get('exclusion', '')
    st.session_state['p1_setting'] = st.session_state.data['phase1'].get('setting', '')
    st.session_state['p1_prob'] = st.session_state.data['phase1'].get('problem', '')
    st.session_state['p1_obj'] = st.session_state.data['phase1'].get('objectives', '')

    st.title("Phase 1: Scoping & Charter")
    styled_info("<b>Tip:</b> The AI agent will auto-draft sections <b>after you enter both the Clinical Condition and Care Setting</b>. You can then manually edit any generated text to refine the content.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. Clinical Focus")
        # SPECIFIC TRIGGER ON CARE SETTING CHANGE via on_change
        cond_input = st.text_input("Clinical Condition", placeholder="e.g. Chest Pain", key="p1_cond_input", on_change=sync_p1_widgets)
        setting_input = st.text_input("Care Setting", placeholder="e.g. Emergency Department", key="p1_setting", on_change=sync_and_draft)
        
        st.subheader("2. Target Population")
        st.text_area(
            "Inclusion Criteria",
            height=compute_textarea_height(st.session_state.get('p1_inc', ''), min_rows=14),
            key="p1_inc",
            on_change=sync_p1_widgets,
        )
        st.text_area(
            "Exclusion Criteria",
            height=compute_textarea_height(st.session_state.get('p1_exc', ''), min_rows=14),
            key="p1_exc",
            on_change=sync_p1_widgets,
        )
        
    with col2:
        st.subheader("3. Clinical Gap / Problem Statement")
        st.text_area(
            "Problem Statement / Clinical Gap",
            height=compute_textarea_height(st.session_state.get('p1_prob', ''), min_rows=12),
            key="p1_prob",
            on_change=sync_p1_widgets,
            label_visibility="collapsed",
        )
        
        st.subheader("4. Goals")
        st.text_area(
            "Project Goals",
            height=compute_textarea_height(st.session_state.get('p1_obj', ''), min_rows=14),
            key="p1_obj",
            on_change=sync_p1_widgets,
            label_visibility="collapsed",
        )

    # Manual Trigger Button using Callback
    if st.button("Regenerate Draft", key="regen_draft"):
        trigger_p1_draft()

    st.divider()
    
    # Natural Language Refinement Section
    st.subheader("Refine Content")
    st.text_area("", placeholder="E.g., 'Make the inclusion criteria strictly for patients over 65'...", key="p1_refine_input")
    if st.button("Apply Refinements", type="primary"):
        apply_refinements()
        st.success("Refinements applied!")

    st.divider()
    st.subheader("5. Project Timeline (Gantt Chart)")
    styled_info("<b>Tip:</b> Hover over the top right of the chart to download the image or table. You can also directly edit the timeline table below to adjust start/end dates and task owners.")
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
        sync_p1_widgets()
        d = st.session_state.data['phase1']
        if not d['condition'] or not d['problem']: st.error("Please fill in Condition and Problem.")
        else:
            with st.status("Generating Project Charter...", expanded=True) as status:
                st.write("Building project charter based on IHI Quality Improvement framework...")
                p_ihi = f"Act as QI Advisor (IHI Model). Draft Charter for {d['condition']}. Problem: {d['problem']}. Scope: {d['inclusion']}. Return JSON: project_description, rationale, expected_outcomes, aim_statement, outcome_measures, process_measures, balancing_measures, initial_activities, change_ideas, stakeholders, barriers, boundaries (return as dict: in_scope, out_of_scope)."
                res = get_gemini_response(p_ihi, json_mode=True)
                if res:
                    st.session_state.data['phase1']['ihi_content'] = res
                    doc = create_word_docx(st.session_state.data['phase1'])
                    if doc:
                        status.update(label="Ready!", state="complete")
                        st.download_button("Download Project Charter (.docx)", doc, f"Project_Charter_{d['condition']}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    else:
                        status.update(label="Word export unavailable. Please ensure python-docx is installed.", state="error")
    render_bottom_navigation()

# --- PHASE 2 ---
elif "Phase 2" in phase:
    st.title("Phase 2: Rapid Evidence Appraisal")

    # Build robust default query from Phase 1 if none saved
    # Format: "managing patients with [clinical condition] in [care setting]" using PubMed syntax
    default_q = st.session_state.data['phase2'].get('mesh_query', '')
    if not default_q and st.session_state.data['phase1']['condition']:
        c = st.session_state.data['phase1']['condition']
        s = st.session_state.data['phase1']['setting']
        # Build proper PubMed query with MeSH terms
        cond_q = f'("{c}"[MeSH Terms] OR "{c}"[Title/Abstract])'
        if s:
            # Include care setting in the query
            set_q = f'("{s}"[Title/Abstract] OR "{s}"[All Fields])'
            default_q = f'({cond_q} AND {set_q}) AND (pathway OR guideline OR policy) AND english[lang]'
        else:
            default_q = f'{cond_q} AND (pathway OR guideline OR policy) AND english[lang]'

    # Auto-run search once per distinct default query when evidence is empty
    if (
        not st.session_state.data['phase2']['evidence']
        and default_q
        and st.session_state.get('p2_last_autorun_query') != default_q
    ):
        st.session_state.data['phase2']['mesh_query'] = f"{default_q} AND (\"last 5 years\"[dp])"
        full_query = st.session_state.data['phase2']['mesh_query']
        with ai_activity("Searching PubMed and auto‑grading…"):
            results = search_pubmed(full_query)
            st.session_state.data['phase2']['evidence'] = results
            if results:
                prompt = (
                    "Assign GRADE quality of evidence (use EXACTLY one of: 'High (A)', 'Moderate (B)', 'Low (C)', or 'Very Low (D)') "
                    "and provide a brief Rationale (1-2 sentences) for each article. "
                    f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in results])}. "
                    "Return ONLY valid JSON: {\"PMID_NUMBER\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}. "
                    "Use exactly these grade formats: 'High (A)', 'Moderate (B)', 'Low (C)', 'Very Low (D)'."
                )
                grades = get_gemini_response(prompt, json_mode=True)
                if grades:
                    for e in st.session_state.data['phase2']['evidence']:
                        if e['id'] in grades:
                            grade_data = grades[e['id']]
                            e['grade'] = grade_data.get('grade', e.get('grade', 'Un-graded'))
                            e['rationale'] = grade_data.get('rationale', e.get('rationale', 'Not provided.'))
                for e in st.session_state.data['phase2']['evidence']:
                    e.setdefault('grade', 'Un-graded')
                    e.setdefault('rationale', 'Not yet evaluated.')
        st.session_state['p2_last_autorun_query'] = st.session_state.data['phase2']['mesh_query']

    # Refinement with the current query prefilled
    with st.expander("Refine search", expanded=False):
        current_q = st.session_state.data['phase2'].get('mesh_query', default_q)
        current_q_full = current_q or ""
        if current_q_full and '"last 5 years"[dp]' not in current_q_full:
            current_q_full = f"{current_q_full} AND (\"last 5 years\"[dp])"
        q = st.text_input(
            "PubMed Search Query (editable full query)",
            value=current_q_full,
            placeholder="Enter a custom query (include filters as needed)",
            key="p2_query_input",
        )
        q_clean = (q or "").strip()

        def ensure_time_filter(term: str) -> str:
            return term if '"last 5 years"[dp]' in term else f"{term} AND (\"last 5 years\"[dp])"

        col_run, col_open = st.columns([1, 1])
        with col_run:
            if st.button("Regenerate Evidence Table", type="primary", key="p2_search_run"):
                search_term = q_clean or current_q_full or default_q or ""
                if not search_term:
                    st.warning("Please enter a PubMed search query first.")
                else:
                    search_term = ensure_time_filter(search_term)
                    st.session_state.data['phase2']['mesh_query'] = search_term
                    with ai_activity("Searching PubMed and auto‑grading…"):
                        results = search_pubmed(search_term)
                        st.session_state.data['phase2']['evidence'] = results
                        if results:
                            prompt = (
                                "Assign GRADE quality of evidence (use EXACTLY one of: 'High (A)', 'Moderate (B)', 'Low (C)', or 'Very Low (D)') "
                                "and provide a brief Rationale (1-2 sentences) for each article. "
                                f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in results])}. "
                                "Return ONLY valid JSON: {\"PMID_NUMBER\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}. "
                                "Use exactly these grade formats: 'High (A)', 'Moderate (B)', 'Low (C)', 'Very Low (D)'."
                            )
                            grades = get_gemini_response(prompt, json_mode=True)
                            if grades:
                                for e in st.session_state.data['phase2']['evidence']:
                                    if e['id'] in grades:
                                        grade_data = grades[e['id']]
                                        e['grade'] = grade_data.get('grade', e.get('grade', 'Un-graded'))
                                        e['rationale'] = grade_data.get('rationale', e.get('rationale', 'Not provided.'))
                        # Ensure defaults if AI response missing
                        for e in st.session_state.data['phase2']['evidence']:
                            e.setdefault('grade', 'Un-graded')
                            e.setdefault('rationale', 'Not yet evaluated.')
                    st.session_state['p2_last_autorun_query'] = search_term
                    st.rerun()
        with col_open:
            if q_clean:
                full_q = ensure_time_filter(q_clean)
                st.link_button("Open in PubMed ↗", f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(full_q)}", type="secondary")

    if st.session_state.data['phase2']['evidence']:
        grade_help = (
            "GRADE Criteria\n"
            "- High (A): Further research is very unlikely to change our confidence in the estimate of effect.\n"
            "- Moderate (B): Further research is likely to have an important impact on our confidence in the estimate of effect and may change the estimate.\n"
            "- Low (C): Further research is very likely to have an important impact on our confidence in the estimate of effect and is likely to change the estimate.\n"
            "- Very Low (D): We are very uncertain about the estimate."
        )

        # Default filters set to show all grades initially
        selected_grades = st.multiselect(
            "Filter by GRADE:",
            ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
            default=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
            help=grade_help,
            key="grade_filter_multiselect"
        )
        
        # Sort Logic: High to Low
        grade_order = {"High (A)": 0, "Moderate (B)": 1, "Low (C)": 2, "Very Low (D)": 3, "Un-graded": 4}
        
        evidence_data = st.session_state.data['phase2']['evidence']
        # Apply Sorting
        evidence_data.sort(key=lambda x: grade_order.get(x.get('grade', 'Un-graded'), 4))
        
        # Filter for Display
        display_data = [e for e in evidence_data if e.get('grade', 'Un-graded') in selected_grades]
        df_ev = pd.DataFrame(display_data)
        
        if not df_ev.empty:
            # Ensure all required columns exist in DataFrame
            required_cols = ["id", "title", "grade", "rationale", "url", "authors", "abstract", "year", "journal"]
            for col in required_cols:
                if col not in df_ev.columns:
                    df_ev[col] = ""

            styled_info("<b>Tip:</b> Hover over the top right of the table to download the CSV. You can edit GRADE and Rationale directly in the table.")

            edited_ev = st.data_editor(
                df_ev[["id", "title", "grade", "rationale", "url"]], 
                column_config={
                    "id": st.column_config.TextColumn("PMID", disabled=True, width="small"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], width="small"),
                    "rationale": st.column_config.TextColumn("GRADE Rationale", width="large"),
                    "url": st.column_config.LinkColumn("URL", width="small"),
                }, 
                hide_index=True, width="stretch", key="ev_editor"
            )
            
            # EXPORT OPTIONS SECTION
            st.divider()

            full_df = pd.DataFrame(evidence_data)
            c1, c2 = st.columns([1, 1])

            with c1:
                st.subheader("Detailed Evidence Table", help="Includes journal, year, authors, and abstract for all results.")
                full_export_df = full_df[["id", "title", "grade", "rationale", "url", "journal", "year", "authors", "abstract"]].copy()
                full_export_df.columns = ["PMID", "Title", "GRADE", "GRADE Rationale", "URL", "Journal", "Year", "Authors", "Abstract"]
                csv_data_full = full_export_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download", csv_data_full, "detailed_evidence_summary.csv", "text/csv", key="dl_csv_full", use_container_width=True)

            with c2:
                col_cit_header = st.columns([1, 2])
                with col_cit_header[0]:
                    st.subheader("Formatted Citations", help="Generate Word citations in your preferred style.")
                with col_cit_header[1]:
                    citation_style = st.selectbox("Citation style", ["APA", "MLA", "Vancouver"], key="p2_citation_style", label_visibility="collapsed")
                
                references_source = display_data if display_data else evidence_data
                if not references_source:
                    st.info("Add or unfilter evidence to generate references.")
                else:
                    references_doc = create_references_docx(references_source, citation_style)
                    if references_doc:
                        st.download_button(
                            "Download",
                            references_doc,
                            f"references_{citation_style.lower()}.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="dl_refs_docx",
                            use_container_width=True
                        )
                    else:
                        st.warning("python-docx is not available; install it to enable Word downloads.")

    else:
        # If nothing to show, provide a helpful prompt and the PubMed link if available
        st.info("No results yet. Refine the search or ensure Phase 1 has a condition and setting.")
        # Offer quick broaden options
        c = st.session_state.data['phase1'].get('condition', '')
        s = st.session_state.data['phase1'].get('setting', '')
        col_b1, col_b2 = st.columns([1, 1])
        with col_b1:
            if c and st.button("Broaden: drop setting", key="p2_broaden_drop_setting"):
                cond_q = f'("{c}"[MeSH Terms] OR "{c}"[Title/Abstract])'
                q = f'{cond_q} AND english[lang]'
                st.session_state.data['phase2']['mesh_query'] = q
                full_query = f"{q} AND (\"last 5 years\"[dp])"
                with ai_activity("Searching PubMed and auto‑grading…"):
                    results = search_pubmed(full_query)
                    st.session_state.data['phase2']['evidence'] = results
                    if results:
                        prompt = (
                            "Assign GRADE quality of evidence (use EXACTLY one of: 'High (A)', 'Moderate (B)', 'Low (C)', or 'Very Low (D)') "
                            "and provide a brief Rationale (1-2 sentences) for each article. "
                            f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in results])}. "
                            "Return ONLY valid JSON: {\"PMID_NUMBER\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}. "
                            "Use exactly these grade formats: 'High (A)', 'Moderate (B)', 'Low (C)', 'Very Low (D)'."
                        )
                        grades = get_gemini_response(prompt, json_mode=True)
                        if grades:
                            for e in st.session_state.data['phase2']['evidence']:
                                if e['id'] in grades:
                                    grade_data = grades[e['id']]
                                    e['grade'] = grade_data.get('grade', e.get('grade', 'Un-graded'))
                                    e['rationale'] = grade_data.get('rationale', e.get('rationale', 'Not provided.'))
                        for e in st.session_state.data['phase2']['evidence']:
                            e.setdefault('grade', 'Un-graded')
                            e.setdefault('rationale', 'Not yet evaluated.')
                st.session_state['p2_last_autorun_query'] = q
                st.rerun()
        with col_b2:
            if st.button("Broaden: drop time filter", key="p2_broaden_drop_time"):
                q_current = st.session_state.data['phase2'].get('mesh_query', '') or default_q
                # If still empty, rebuild robust query from Phase 1
                if not q_current and c:
                    cond_q = f'("{c}"[MeSH Terms] OR "{c}"[Title/Abstract])'
                    if s:
                        set_q = f'("{s}"[Title/Abstract] OR "{s}"[All Fields])'
                        q_current = f'({cond_q} AND {set_q}) AND english[lang]'
                    else:
                        q_current = f'{cond_q} AND english[lang]'
                st.session_state.data['phase2']['mesh_query'] = q_current
                # Run without last 5 years filter
                with ai_activity("Searching PubMed and auto‑grading…"):
                    results = search_pubmed(q_current)
                    st.session_state.data['phase2']['evidence'] = results
                    if results:
                        prompt = (
                            "Assign GRADE quality of evidence (use EXACTLY one of: 'High (A)', 'Moderate (B)', 'Low (C)', or 'Very Low (D)') "
                            "and provide a brief Rationale (1-2 sentences) for each article. "
                            f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in results])}. "
                            "Return ONLY valid JSON: {\"PMID_NUMBER\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}. "
                            "Use exactly these grade formats: 'High (A)', 'Moderate (B)', 'Low (C)', 'Very Low (D)'."
                        )
                        grades = get_gemini_response(prompt, json_mode=True)
                        if grades:
                            for e in st.session_state.data['phase2']['evidence']:
                                if e['id'] in grades:
                                    grade_data = grades[e['id']]
                                    e['grade'] = grade_data.get('grade', e.get('grade', 'Un-graded'))
                                    e['rationale'] = grade_data.get('rationale', e.get('rationale', 'Not provided.'))
                        for e in st.session_state.data['phase2']['evidence']:
                            e.setdefault('grade', 'Un-graded')
                            e.setdefault('rationale', 'Not yet evaluated.')
                st.session_state['p2_last_autorun_query'] = q_current
                st.rerun()
        if st.session_state.data['phase2'].get('mesh_query'):
            search_q = st.session_state.data['phase2']['mesh_query']
            full_q = search_q if '"last 5 years"[dp]' in search_q else f"{search_q} AND (\"last 5 years\"[dp])"
            st.link_button("Open in PubMed ↗", f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(full_q)}", type="secondary")
    render_bottom_navigation()

# --- PHASE 3 ---
elif "Phase 3" in phase:
    st.title("Phase 3: Decision Science")
    styled_info("<b>Tip:</b> The AI agent generated an evidence-based decision tree. You can manually update text, add/remove nodes, or refine using natural language below.")
    
    # Auto-generate table on first entry to Phase 3
    cond = st.session_state.data['phase1']['condition']
    setting = st.session_state.data['phase1']['setting'] or "care setting"
    evidence_list = st.session_state.data['phase2']['evidence']
    
    if not st.session_state.data['phase3']['nodes'] and cond:
        with ai_activity("Auto-generating decision science table based on Phase 1 & 2..."):
            ev_context = "\n".join([f"- PMID {e['id']}: {e['title']} | Abstract: {e.get('abstract', 'N/A')[:200]}" for e in evidence_list[:20]])
            prompt = f"""
            Act as a Clinical Decision Scientist. Build a comprehensive decision-science pathway for managing patients with {cond} in {setting}.
            
            Ground the design in CGT/Ad/it principles and the Users' Guide to Medical Decision Analysis (Dobler et al., Mayo Clin Proc 2021): separate structure from content, make decision/chance/terminal flows explicit, trade off benefits vs harms, and rely on evidence-based probabilities and utilities.

            Available Evidence:
            {ev_context}
            
            The pathway MUST cover these clinical stages:
            1. Initial Evaluation (presenting symptoms, vital signs, initial assessment)
            2. Diagnosis and Treatment (diagnostic workup, interventions, medications)
            3. Re-evaluation (response to treatment, monitoring criteria)
            4. Final Disposition (discharge with prescriptions/referrals, observe, admit, transfer to higher level of care)
            
            Output: JSON array of nodes. Each object must have:
            - "type": one of "Start", "Decision", "Process", "End"
            - "label": concise, actionable clinical step using medical acronyms where appropriate (e.g., BP, HR, CBC, CXR, IV, PO, etc.)
            - "evidence": PMID from evidence list when step is evidence-backed; otherwise "N/A"
            
            Rules:
            - First node: type "Start", label "patient present to {setting} with {cond}"
            - Focus on ACTION and SPECIFICITY (e.g., "Order CBC, BMP, troponin" not "Order labs")
            - Use BREVITY with standard medical abbreviations
            - Include discharge details: specific prescriptions (drug, dose, route) and outpatient referrals when applicable
            - NO arbitrary node count limit - build as many nodes as needed for complete clinical flow
            - If pathway exceeds 20 nodes, organize into logical sections or create sub-pathways for special populations
            - Prefer evidence-backed steps; cite PMIDs where available
            - Highlight benefit/harm trade-offs at decision points
            """
            nodes = get_gemini_response(prompt, json_mode=True)
            if isinstance(nodes, list) and len(nodes) > 0:
                st.session_state.data['phase3']['nodes'] = nodes
                st.rerun()
    
    st.divider()
    st.markdown("### Decision Tree")
    
    # Build evidence options from Phase 2
    evidence_ids = ["N/A"] + [e['id'] for e in evidence_list]
    
    # Initialize with empty row if no nodes
    if not st.session_state.data['phase3']['nodes']:
        st.session_state.data['phase3']['nodes'] = [{"type": "Start", "label": "", "evidence": "N/A"}]
    
    df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
    edited_nodes = st.data_editor(
        df_nodes,
        column_config={
            "type": st.column_config.SelectboxColumn(
                "Type",
                options=["Start", "Decision", "Process", "End"],
                required=True,
                width="small"
            ),
            "label": st.column_config.TextColumn(
                "Clinical Step",
                width="large",
                required=True
            ),
            "evidence": st.column_config.TextColumn(
                "Supporting Evidence (PMID)",
                width="medium",
                help="Enter PMID or 'N/A'"
            )
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="p3_editor"
    )
    # Auto-save on edit
    st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')
    
    # Display pathway metrics
    node_count = len(st.session_state.data['phase3']['nodes'])
    evidence_backed = len([n for n in st.session_state.data['phase3']['nodes'] if n.get('evidence') not in ['N/A', '', None]])
    st.caption(f"Pathway contains {node_count} nodes | {evidence_backed} evidence-backed steps")

    def apply_large_pathway_recommendations():
        current_nodes = st.session_state.data['phase3']['nodes']
        ev_context = "\n".join([f"- PMID {e['id']}: {e['title']} | Abstract: {e.get('abstract', 'N/A')[:200]}" for e in evidence_list[:20]])
        with ai_activity("Applying pathway recommendations…"):
            prompt = f"""
            The current decision tree for {cond} in {setting} is long. Re-organize it into a clearer, multi-section pathway.

            Current pathway (JSON):
            {json.dumps(current_nodes, indent=2)}

            Available Evidence:
            {ev_context}

            Requirements:
            - Keep fields: type, label, evidence.
            - Preserve evidence citations when present; use "N/A" if none.
            - Group logically into segments (e.g., Initial Evaluation, Diagnosis/Treatment, Re-evaluation, Final Disposition) and streamline redundant steps.
            - Maintain actionable, concise clinical labels with standard abbreviations.
            - Ensure a complete flow with Start and End nodes; no node count limit but prioritize clarity.
            """
            new_nodes = get_gemini_response(prompt, json_mode=True)
        if isinstance(new_nodes, list) and new_nodes:
            st.session_state.data['phase3']['nodes'] = new_nodes
            st.session_state.data['phase3']['large_rec_applied'] = True
            st.success("Recommendations applied to the decision tree.")
            st.rerun()

    applied_flag = st.session_state.data['phase3'].get('large_rec_applied', False)
    if node_count > 20:
        styled_info("<b>Note:</b> Large pathway detected. Recommend organizing into multiple decision trees (e.g., Initial Evaluation, Diagnosis/Treatment, Re-evaluation) for clarity.")
        if not applied_flag:
            if st.button("Apply Recommendations", type="primary", key="p3_apply_reco_btn"):
                apply_large_pathway_recommendations()
        else:
            st.markdown("""
                <div style="background-color: #FFB0C9; color: black; padding: 10px 20px; border-radius: 5px; border: 1px solid black; text-align: center; font-weight: 600; margin-bottom: 10px;">
                    Recommendations Applied
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Natural Language Refinement Interface (placed below the table)
    st.text_area(
        "Refine Decision Tree",
        placeholder="E.g., 'Add a branch for patients with renal impairment', 'Include specific discharge medications for heart failure'...",
        key="p3_refine_input",
        height=80
    )
    if st.button("Apply Refinements", type="primary"):
        refinement_request = st.session_state.get('p3_refine_input', '').strip()
        if refinement_request and st.session_state.data['phase3']['nodes']:
            with ai_activity("Applying refinements to decision tree..."):
                current_nodes = st.session_state.data['phase3']['nodes']
                ev_context = "\n".join([f"- PMID {e['id']}: {e['title']} | Abstract: {e.get('abstract', 'N/A')[:200]}" for e in evidence_list[:20]])
                prompt = f"""
                Act as a Clinical Decision Scientist. Refine the existing pathway based on the user's request.

                Current pathway for {cond} in {setting}:
                {json.dumps(current_nodes, indent=2)}

                Available Evidence:
                {ev_context}

                User's refinement request: "{refinement_request}"

                Apply the requested changes while maintaining:
                - CGT/Ad/it principles and Medical Decision Analysis best practices
                - Coverage of: Initial Evaluation, Diagnosis/Treatment, Re-evaluation, Final Disposition
                - Actionable steps with medical acronyms for brevity
                - Specific discharge details (prescriptions with dose/route, referrals)
                - Evidence citations (PMIDs where applicable)

                Output: Complete revised JSON array of nodes with fields: type, label, evidence.
                Rules:
                - type in [Start, Decision, Process, End]
                - First node: type "Start", label "patient present to {setting} with {cond}"
                - NO node count limit - build complete clinical flow
                - If >20 nodes, organize into sections or sub-pathways
                """
                nodes = get_gemini_response(prompt, json_mode=True)
                if isinstance(nodes, list) and len(nodes) > 0:
                    st.session_state.data['phase3']['nodes'] = nodes
                    st.success("Refinements applied")
                    st.rerun()
    
    render_bottom_navigation()

# --- PHASE 4 ---
elif "Phase 4" in phase:
    st.title("Phase 4: User Interface Design")
    styled_info("<b>Tip:</b> Evaluate your pathway against Nielsen's 10 Usability Heuristics. The AI agent can provide suggestions for each criterion.")
    
    nodes = st.session_state.data['phase3']['nodes']
    
    # Initialize Phase 4 data structure
    if 'nodes_history' not in st.session_state.data['phase4']:
        st.session_state.data['phase4']['nodes_history'] = []
    if 'heuristics_data' not in st.session_state.data['phase4']:
        st.session_state.data['phase4']['heuristics_data'] = {}
    
    col_vis, col_heuristics = st.columns([2, 1])
    
    # LEFT COLUMN: Visualization + Downloads
    with col_vis:
        st.subheader("Pathway Visualization")
        
        # Visualization style selector
        vis_style = st.radio(
            "Visualization Style",
            ["Mermaid (Web)", "Graphviz (Diagram)"],
            horizontal=True,
            index=0
        )
        
        c_view1, c_view2 = st.columns([1, 2])
        with c_view1:
            orientation = st.selectbox("Orientation", ["Vertical (TD)", "Horizontal (LR)"], index=0)
            mermaid_orient = "TD" if "Vertical" in orientation else "LR"
        
        # Display visualization based on selected style
        if vis_style == "Mermaid (Web)":
            mermaid_code = generate_mermaid_code(nodes, mermaid_orient)
            components.html(f'<div class="mermaid">{mermaid_code}</div><script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script><script>mermaid.initialize({{startOnLoad:true}});</script>', height=600, scrolling=True)
        else:  # Graphviz
            g = build_graphviz_from_nodes(nodes, mermaid_orient)
            if g:
                svg_bytes = render_graphviz_bytes(g, "svg")
                if svg_bytes:
                    components.html(svg_bytes.decode('utf-8'), height=600, scrolling=True)
                else:
                    st.info("Graphviz rendering not available. Try Mermaid style instead.")
            else:
                st.info("Graphviz rendering not available. Try Mermaid style instead.")
        
        # Download buttons (always available)
        with st.container(border=False):
            c_dl_svg, c_dl_png, c_dl_dot = st.columns([1, 1, 1])
            
            # DOT file (always available)
            dot_text = dot_from_nodes(nodes, mermaid_orient)
            with c_dl_dot:
                st.download_button("Download DOT", dot_text, file_name="pathway.dot", mime="text/vnd.graphviz")
            
            # SVG/PNG via Graphviz if available
            g = build_graphviz_from_nodes(nodes, mermaid_orient)
            svg_bytes = render_graphviz_bytes(g, "svg") if g else None
            png_bytes = render_graphviz_bytes(g, "png") if g else None
            with c_dl_svg:
                if svg_bytes:
                    st.download_button("Download SVG", svg_bytes, file_name="pathway.svg", mime="image/svg+xml")
                else:
                    st.caption("SVG unavailable (Graphviz not installed)")
            with c_dl_png:
                if png_bytes:
                    st.download_button("Download PNG", png_bytes, file_name="pathway.png", mime="image/png")
                else:
                    st.caption("PNG unavailable (Graphviz not installed)")
        
        # Edit pathway data
        with st.expander("Edit Pathway Data", expanded=False):
            df_p4 = pd.DataFrame(nodes)
            edited_p4 = st.data_editor(df_p4, num_rows="dynamic", key="p4_editor", width="stretch")
            if not df_p4.equals(edited_p4):
                st.session_state.data['phase3']['nodes'] = edited_p4.to_dict('records')
                st.rerun()

    # RIGHT COLUMN: Heuristics Analysis
    with col_heuristics:
        st.subheader("Heuristics Analysis")
        
        # Analyze Heuristics button
        if st.button("Analyze Heuristics", key="p4_analyze_btn"):
            with ai_activity("Analyzing usability heuristics…"):
                prompt = f"""
                Analyze the following clinical decision pathway for Nielsen's 10 Usability Heuristics.
                For each heuristic (H1-H10), provide a specific, actionable critique and suggestion.
                
                Pathway nodes: {json.dumps(nodes)}
                
                Return ONLY a JSON object with this exact structure:
                {{
                    "H1": "specific insight and fix",
                    "H2": "specific insight and fix",
                    "H3": "specific insight and fix",
                    "H4": "specific insight and fix",
                    "H5": "specific insight and fix",
                    "H6": "specific insight and fix",
                    "H7": "specific insight and fix",
                    "H8": "specific insight and fix",
                    "H9": "specific insight and fix",
                    "H10": "specific insight and fix"
                }}
                """
                res = get_gemini_response(prompt, json_mode=True)
                if res:
                    st.session_state.data['phase4']['heuristics_data'] = res
                    st.rerun()
        
        # Display heuristics with expanders
        h_data = st.session_state.data['phase4'].get('heuristics_data', {})
        if h_data:
            for heuristic_key in sorted(h_data.keys()):
                insight = h_data[heuristic_key]
                # Extract first 40 chars for preview
                preview = insight[:40] + "..." if len(insight) > 40 else insight
                definition = HEURISTIC_DEFS.get(heuristic_key, "")
                
                with st.expander(f"{heuristic_key}: {preview}"):
                    st.write(f"**Insight:** {insight}")
                    if definition:
                        st.caption(definition)
                    
                    # Apply Fix button
                    if st.button(f"Apply Fix", key=f"p4_fix_{heuristic_key}"):
                        # Save current nodes to history for undo
                        st.session_state.data['phase4']['nodes_history'] = [copy.deepcopy(nodes)]
                        
                        with ai_activity(f"Applying fix for {heuristic_key}…"):
                            p_fix = f"""
                            Update this clinical pathway JSON to address this heuristic issue:
                            {heuristic_key}: {insight}
                            
                            Current pathway: {json.dumps(nodes)}
                            
                            Return ONLY the updated JSON array.
                            """
                            new_nodes = get_gemini_response(p_fix, json_mode=True)
                            if new_nodes and isinstance(new_nodes, list):
                                st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                                st.rerun()
        else:
            st.info("Click 'Analyze Heuristics' to begin evaluation.")
    
    st.divider()
    
    # APPLY CHANGES section
    st.subheader("Apply Changes?")
    apply_choice = st.radio(
        "Commit changes to the pathway?",
        ["Skip", "Apply"],
        horizontal=True,
        index=0,
        key="p4_apply_choice"
    )
    
    if apply_choice == "Apply":
        st.success("Changes applied")
        if st.session_state.data['phase4'].get('nodes_history'):
            if st.button("Undo last change", key="p4_undo_btn"):
                if st.session_state.data['phase4']['nodes_history']:
                    old_nodes = st.session_state.data['phase4']['nodes_history'].pop(0)
                    st.session_state.data['phase3']['nodes'] = old_nodes
                    st.success("Change undone")
                    st.rerun()
    else:
        st.info("Changes discarded")
    
    # Re-run analysis button
    if st.button("Re-run Heuristics Analysis", key="p4_rerun_analysis"):
        st.session_state.data['phase4']['heuristics_data'] = {}
        st.rerun()
    
    st.divider()
    
    # CUSTOM REFINEMENT section
    st.subheader("Heuristic-Targeted Refinement")
    
    # Prefill suggestion based on selected heuristic
    selected_h = st.selectbox(
        "Focus refinement on a heuristic (optional)",
        ["None"] + list(st.session_state.data['phase4'].get('heuristics_data', {}).keys()),
        key="p4_selected_h"
    )
    
    if selected_h != "None":
        h_text = st.session_state.data['phase4']['heuristics_data'].get(selected_h, "")
        placeholder = f"Refine {selected_h}: {h_text[:70]}..."
    else:
        placeholder = "Describe your refinement..."
    
    custom_ref = st.text_area(
        "Refinement Details",
        placeholder=placeholder,
        key="p4_custom_ref",
        height=100
    )
    
    if st.button("Apply Refinements", type="primary", key="p4_apply_ref"):
        if custom_ref.strip():
            st.session_state.data['phase4']['nodes_history'] = [copy.deepcopy(nodes)]
            
            with ai_activity("Applying refinements…"):
                p_custom = f"""
                Update this clinical pathway based on user feedback:
                {custom_ref}
                
                Current pathway: {json.dumps(nodes)}
                
                Return ONLY updated JSON array.
                """
                new_nodes = get_gemini_response(p_custom, json_mode=True)
                if new_nodes and isinstance(new_nodes, list):
                    st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                    st.success("Refinements applied!")
                    st.rerun()
        else:
            st.warning("Enter refinement details")
    
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