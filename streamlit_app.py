import streamlit as st
# Version info sidebar caption (admin-only)
import streamlit.components.v1 as components
import os
import json
import pandas as pd
import altair as alt
import urllib.request
import urllib.parse
import re
import time
import base64
from io import BytesIO
import datetime
from datetime import date, timedelta
import copy
import xml.etree.ElementTree as ET
from contextlib import contextmanager
import requests
import hashlib
import textwrap
from google import genai

def _get_query_param(name: str):
    try:
        # Streamlit >= 1.33
        if hasattr(st, "query_params"):
            val = st.query_params.get(name)
        else:
            val = st.experimental_get_query_params().get(name)
        if isinstance(val, list):
            return val[0] if val else None
        return val
    except Exception:
        return None

def is_admin():
    # Env flag still enables admin mode for server-side checks
    if os.environ.get("CPQ_SHOW_VERSION", "").lower() in ("1", "true", "yes", "y"):
        return True
    # Optional shared code via env or secrets + query param `?admin=CODE`
    code = os.environ.get("CPQ_ADMIN_CODE", "")
    try:
        code = code or st.secrets.get("ADMIN_CODE", "")
    except Exception:
        pass
    if code:
        return (_get_query_param("admin") == code)
    return False

def is_debug():
    # Enable with env `CPQ_DEBUG` or query param `?debug=1`
    if os.environ.get("CPQ_DEBUG", "").lower() in ("1", "true", "yes", "y"):
        return True
    val = _get_query_param("debug")
    return str(val).lower() in ("1", "true", "yes", "y")

def debug_log(msg: str):
    try:
        if is_debug():
            st.sidebar.caption(str(msg))
    except Exception:
        pass


# --- GOOGLE GENAI CLIENT HELPER ---
# Using official google-genai SDK per https://ai.google.dev/gemini-api/docs/quickstart
def get_genai_client():
    return st.session_state.get("genai_client")

# Column helper that prefers top alignment but gracefully falls back
def columns_top(spec, **kwargs):
    try:
        # Streamlit >= 1.30 supports vertical_alignment
        return st.columns(spec, vertical_alignment="top", **kwargs)
    except TypeError:
        # Older Streamlit versions without vertical_alignment
        return st.columns(spec, **kwargs)

# Unified status UI for AI tasks
@contextmanager
def ai_activity(label="Working with the AI agent…"):
    with st.status(label, expanded=False) as status:
        try:
            yield status
            status.update(label="Ready!", state="complete")
        except Exception:
            status.update(label="There was a problem completing this step.", state="error")
            st.error("Please try again or adjust your input.")
            return

def regenerate_nodes_with_refinement(nodes, refine_text, heuristics_data=None):
    """Regenerate Phase 3 nodes based on user refinement notes and optional heuristics context."""
    refine_text = (refine_text or "").strip()
    if not refine_text:
        return None

    cond = st.session_state.data['phase1'].get('condition') or "Pathway"
    setting = st.session_state.data['phase1'].get('setting') or "care setting"
    evidence_list = st.session_state.data['phase2'].get('evidence', [])

    ev_context = "\n".join([
        f"- PMID {e['id']}: {e['title']} | Abstract: {e.get('abstract', 'N/A')[:200]}"
        for e in evidence_list[:20]
    ])

    heuristics_summary = ""
    if heuristics_data:
        bullet_lines = []
        for key, val in heuristics_data.items():
            try:
                label = val.get('label', key)
                recs = val.get('recommendations', [])
                if recs:
                    bullet_lines.append(f"- {label}: {recs[0]}")
            except Exception:
                continue
        if bullet_lines:
            heuristics_summary = "\nHeuristics guidance (PRESERVE clinical complexity while applying):\n" + "\n".join(bullet_lines[:5])

    prompt = f"""
    Act as a CLINICAL DECISION SCIENTIST. Refine the EXISTING pathway based on the user's request.

    CRITICAL: Apply refinements while PRESERVING and potentially ENHANCING clinical complexity.
    
    Current pathway for {cond} in {setting}:
    {json.dumps(nodes, indent=2)}

    Available Evidence:
    {ev_context}

    User's refinement request: "{refine_text}"
    {heuristics_summary}

    MANDATORY PRESERVATION RULES:
    
    1. MAINTAIN DECISION SCIENCE FRAMEWORK:
       - Keep CGT/Ad/it principles and Medical Decision Analysis structure intact
       - Preserve or enhance benefit/harm trade-offs at decision points
       - Maintain evidence-based reasoning (cite PMIDs)
    
    2. PRESERVE DECISION DIVERGENCE:
       - Do NOT collapse multiple branches into linear sequences
       - Keep distinct pathways separate until final disposition
       - If refining convergence points, make them explicit with new Decision nodes
    
    3. PRESERVE CLINICAL COVERAGE:
       - All 4 stages must remain: Initial Evaluation, Diagnosis/Treatment, Re-evaluation, Final Disposition
       - Do NOT remove edge cases or special population considerations
       - If refining, EXPAND specificity (e.g., "treat infection" → "vancomycin 15-20 mg/kg IV q8-12h")
    
    4. ENHANCE DEPTH, NOT REDUCE:
       - When applying refinements, consider adding detail (more nodes, more branches)
       - If user asks to "simplify," interpret as "make more understandable" (clearer labels, better organization)
       - NOT "remove clinical branches"
       - Prefer 30+ well-organized nodes over 10 oversimplified ones
    
    5. MAINTAIN DAG STRUCTURE:
       - No cycles, backward loops, or reconvergent branches
       - Escalation moves forward (ED → ICU, not back)
       - All paths must terminate in explicit End nodes
    
    OUTPUT: Complete revised JSON array of nodes with fields: type, label, evidence, (optional) detail
    Rules:
    - type: "Start" | "Decision" | "Process" | "End"
    - First node: type "Start", label "patient present to {setting} with {cond}"
    - NO artificial node count limit—maintain complexity needed for clinical accuracy
    - End nodes must be TERMINAL single outcomes (no "or" phrasing)
    - Consecutive Decision nodes are allowed and encouraged for true clinical branching
    - Include benefit/harm trade-offs in Decision node labels or detail fields
    - Evidence citations (PMIDs) on clinically important steps
    """

    return get_gemini_response(prompt, json_mode=True)

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
    /* Style secondary (non-active) buttons as brown. Avoid overriding primary. */
    button[kind="secondary"],
    div.stButton > button:not([kind="primary"]),
    div[data-testid="stButton"] > button:not([kind="primary"]) {
        background-color: #5D4037 !important; 
        color: white !important;
        border: 1px solid #5D4037 !important;
        border-radius: 5px !important;
        font-weight: 600 !important;
    }
    button[kind="secondary"]:hover,
    div.stButton > button:not([kind="primary"]):hover,
    div[data-testid="stButton"] > button:not([kind="primary"]):hover {
        background-color: #3E2723 !important; 
        border-color: #3E2723 !important;
        color: white !important;
    }

    /* FORM SUBMIT BUTTONS (e.g., "Regenerate" inside forms) */
    /* Streamlit renders these differently from st.button; target explicitly */
    div[data-testid="stFormSubmitButton"] > button,
    form[data-testid="stForm"] button[type="submit"] {
        background-color: #5D4037 !important; 
        color: white !important;
        border: 1px solid #5D4037 !important;
        border-radius: 5px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover,
    form[data-testid="stForm"] button[type="submit"]:hover {
        background-color: #3E2723 !important; 
        border-color: #3E2723 !important;
        color: white !important;
    }
    
    /* PRIMARY BUTTONS (Current Phase) */
    div.stButton > button[kind="primary"],
    button[kind="primary"] {
        background-color: #FFB0C9 !important; 
        color: black !important;
        border: 1px solid black !important;
        border-radius: 5px !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="primary"]:hover,
    button[kind="primary"]:hover {
        background-color: #FF9BB8 !important; 
        border-color: black !important;
        color: black !important;
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
        background-color: #FFB0C9 !important;
        border: 2px solid black !important;
        box-shadow: 0 2px 4px rgba(255,176,201,0.35);
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

    /* Sidebar chat expander matches landing banner */
    section[data-testid="stSidebar"] div[data-testid="stExpander"]:first-of-type details summary {
        background-color: #FFB0C9 !important;
        color: black !important;
        border: 1px solid black !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"]:first-of-type details summary:hover {
        background-color: #FF9BB8 !important;
        color: #3E2723 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"]:first-of-type details summary svg {
        color: black !important;
    }

    /* HEADERS */
    h1, h2, h3 { color: #00695C; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* TOOLTIPS */
    div[data-testid="stTooltipContent"] {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
    }
    /* Help icon spacing right after labels (e.g., GRADE) */
    [data-testid="stTooltipIcon"] {
        margin-left: 4px !important;
        display: inline-block !important;
        vertical-align: middle !important;
    }
    /* Heuristic title tooltips */
    .heuristic-title {
        cursor: help;
        font-weight: bold;
        color: #00695C;
        text-decoration: underline dotted;
        font-size: 1.05em;
    }
    /* Inline info icon for section headers */
    .tooltip-info {
        display: inline-block;
        margin-left: 6px;
        color: #5D4037;
        background: #A9EED1;
        border: 1px solid #5D4037;
        border-radius: 50%;
        width: 18px;
        height: 18px;
        line-height: 16px;
        text-align: center;
        font-size: 12px;
        cursor: help;
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

    /* IMPROVE BUTTON AND TEXT VERTICAL ALIGNMENT */
    /* Top-align items in columns to keep headers aligned horizontally */
    div[data-testid="stColumn"] {
        display: flex !important;
        align-items: flex-start !important;
    }

    /* For horizontal button rows (e.g., bottom navigation), center-align contents */
    [data-testid="stHorizontalBlock"] div[data-testid="stColumn"] {
        align-items: center !important;
    }
    /* Ensure the inner vertical block centers content within horizontal rows */
    [data-testid="stHorizontalBlock"] div[data-testid="stColumn"] > div > div[data-testid="stVerticalBlock"] {
        justify-content: center !important;
        align-items: center !important;
    }
    
    button, input, select, textarea, label {
        vertical-align: middle !important;
    }
    
    /* PHASE 2 EXPORT SECTION ALIGNMENT */
    div[data-testid="stColumn"] > div > div[data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
    }
    
    /* SUBHEADER AND SELECTBOX ALIGNMENT */
    div[data-testid="stColumn"] h3 {
        margin-bottom: 0 !important;
        line-height: 1.2 !important;
    }
    /* Ensure Streamlit subheaders (h2) sit close to content for alignment */
    div[data-testid="stColumn"] h2 {
        margin-bottom: 0.35rem !important;
        line-height: 1.2 !important;
    }
    
    div[data-testid="stColumn"] div[data-baseweb="select"] {
        margin-top: 0 !important;
    }
    
    /* RADIO BUTTON LABEL ALIGNMENT */
    div[role="radiogroup"] {
        display: flex !important;
        align-items: center !important;
        gap: 1.5rem !important;
        width: 50% !important;
    }
    
    div[role="radiogroup"] label {
        display: flex !important;
        align-items: center !important;
        margin-bottom: 0 !important;
        margin-right: 0 !important;
        line-height: 1 !important;
        white-space: nowrap !important;
        gap: 0.5rem !important;
    }
    
    div[role="radiogroup"] label > span {
        vertical-align: middle !important;
    }
    
    div[role="radiogroup"] label > div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* DOWNLOAD BUTTON CONSISTENT HEIGHT */
    div.stDownloadButton > button,
    div.stButton > button {
        min-height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Global link-button styling to match Streamlit buttons */
    .cpq-link-button {
        display: flex; align-items: center; justify-content: center;
        width: 100%; padding: 10px 14px; border-radius: 5px;
        background-color: #5D4037; color: #fff; text-decoration: none;
        border: 1px solid #5D4037; font-weight: 600; height: 42px;
    }
    .cpq-link-button:hover { background-color: #3E2723; border-color: #3E2723; color: #fff; }

    /* FILE UPLOADER & TEXTAREA — compact spacing */
    div[data-testid="stFileUploader"] section {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    div[data-testid="stFileUploaderDropzone"] {
        padding: 12px !important;
        border-radius: 8px !important;
    }
    textarea {
        line-height: 1.35 !important;
    }

    /* PHASE 2 — highlight rows marked as new via the first checkbox column */
    div[data-testid="stDataFrame"] tbody tr:has(input[type="checkbox"]:checked) td,
    div[data-testid="stTable"] tbody tr:has(input[type="checkbox"]:checked) td {
        background-color: #FFB0C9 !important;
    }

    /* DATA TABLES — enable text wrapping for easier scanning */
    div[data-testid="stDataFrame"] table,
    div[data-testid="stTable"] table {
        table-layout: fixed !important;
    }
    div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th,
    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        white-space: normal !important;
        word-break: break-word !important;
    }
    
    /* BOTTOM NAVIGATION */
    /* Hide only Streamlit's default footer, not custom navigation */
    footer[data-testid="stBottom"] {
        visibility: hidden;
    }
    
    /* ENHANCED PHASE NAVIGATION */
    .phase-nav-container {
        background: linear-gradient(to right, #FFB0C9 0%, #A9EED1 100%);
        padding: 10px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .phase-progress-bar {
        height: 6px;
        background: #e0e0e0;
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 15px;
    }
    
    .phase-progress-fill {
        height: 100%;
        background: linear-gradient(to right, #5D4037, #00695C);
        transition: width 0.5s ease;
    }
    
    .phase-nav-label {
        font-size: 0.8rem;
        color: #5D4037;
        font-weight: 600;
        text-align: center;
        margin-bottom: 5px;
    }
    
    /* Make navigation buttons more compact */
    [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] button {
        font-size: 0.9rem !important;
        padding: 10px 8px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        line-height: 1.3 !important;
        min-height: 42px !important;
        max-height: 42px !important;
        height: 42px !important;
    }
    
    /* Ensure all button text stays horizontal */
    [data-testid="stHorizontalBlock"] button div,
    [data-testid="stHorizontalBlock"] button p,
    [data-testid="stHorizontalBlock"] button span {
        writing-mode: horizontal-tb !important;
        text-orientation: mixed !important;
        transform: none !important;
        display: inline !important;
    }

    /* Responsive: stack columns and make paired controls full-width on narrow screens */
    @media (max-width: 560px) {
        /* Stack all Streamlit columns */
        div[data-testid="stColumn"] {
            width: 100% !important;
            flex: 0 0 100% !important;
        }
        /* Make link-button and download button fill width */
        .cpq-link-button { width: 100% !important; }
        div.stDownloadButton > button { width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# Integrating phase 5 helper functions into the Streamlit app

# Importing necessary functions from phase5_helpers
from phase5_helpers import CAREPATHIQ_COLORS, CAREPATHIQ_FOOTER, SHARED_CSS, ensure_carepathiq_branding

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

# Heuristics categorized by applicability to clinical pathways
HEURISTIC_CATEGORIES = {
    "pathway_actionable": {
        "H2": "Language clarity (replace medical jargon with patient-friendly terms where appropriate)",
        "H4": "Consistency (standardize terminology and node types across pathway)",
        "H5": "Error prevention (add critical alerts, validation rules, and edge case handling)",
        "H9": "Error recovery (surface critical checks earlier; add recovery steps in the flow)"
    },
    "ui_design_only": {
        "H1": "Status visibility (implement progress indicators and highlighting in the interface)",
        "H3": "User control (add escape routes and undo/skip options in UI)",
        "H6": "Recognition not recall (use visual icons and clear labels instead of hidden menus)",
        "H7": "Efficiency accelerators (add keyboard shortcuts and quick actions for power users)",
        "H8": "Minimalist design (remove clutter and non-essential information from interface)",
        "H10": "Help & docs (provide in-app tooltips, FAQs, and guided walkthroughs)"
    }
}

ROLE_COLORS = {
    "Physician": "#E3F2FD",
    "Doctor": "#E3F2FD",
    "MD": "#E3F2FD",
    "Nurse": "#E8F5E9",
    "RN": "#E8F5E9",
    "Pharmacist": "#F3E5F5",
    "PharmD": "#F3E5F5",
    "Patient": "#FFF3E0",
    "Care Coordinator": "#FFF8E1",
    "Process": "#FFFDE7",
}
PHASES = [
    "Define Scope & Charter",
    "Appraise Evidence",
    "Build Decision Tree",
    "Design User Interface",
    "Operationalize & Deploy"
]

PROVIDER_OPTIONS = {
    "google": "Google Forms (user account)",
    "html": "HTML Preview (no submission)",
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

import secrets
import urllib.parse

# --- NAVIGATION CONTROLLER ---
def change_phase(new_phase):
    st.session_state.current_phase_label = new_phase
    st.session_state.top_nav_radio = new_phase  # Sync radio button value

def render_bottom_navigation():
    """Renders Previous/Next buttons at the bottom of the page with phase indicators."""
    if "current_phase_label" in st.session_state and st.session_state.current_phase_label in PHASES:
        current_idx = PHASES.index(st.session_state.current_phase_label)
        st.divider()
        # Add a small spacer to keep bottom nav comfortably separated from content above
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        
        try:
            # Try Streamlit >= 1.30 with vertical_alignment
            col_prev, col_middle, col_next = st.columns([1, 1, 1], vertical_alignment="center")
        except TypeError:
            # Fallback for older Streamlit versions
            col_prev, col_middle, col_next = st.columns([1, 1, 1])
        
        if current_idx > 0:
            prev_phase = PHASES[current_idx - 1]
            with col_prev:
                if st.button(f"← {prev_phase}", key=f"bottom_prev_{current_idx}", type="secondary", use_container_width=True):
                    st.session_state.current_phase_label = prev_phase
                    st.rerun()
        else:
            with col_prev:
                st.write("")  # Empty space for alignment
        
        with col_middle:
            # Simple phase counter
            st.markdown(
                f"<div style='text-align: center; padding: 10px; color: #5D4037; font-weight: bold;'>Phase {current_idx + 1} of {len(PHASES)}</div>",
                unsafe_allow_html=True
            )
        
        if current_idx < len(PHASES) - 1:
            next_phase = PHASES[current_idx + 1]
            with col_next:
                if st.button(f"{next_phase} →", key=f"bottom_next_{current_idx}", type="primary", use_container_width=True):
                    st.session_state.current_phase_label = next_phase
                    st.rerun()
        # Always render brand/licensing footer before any phase stop()
        try:
            st.markdown(COPYRIGHT_HTML_FOOTER, unsafe_allow_html=True)
        except Exception:
            pass

def calculate_granular_progress():
    """
    Calculate progress across all 5 phases with balanced weighting.
    Each phase = 20% of total progress (fair distribution).
    Within each phase, fields are weighted equally.
    Returns: float between 0.0 and 1.0
    """
    if 'data' not in st.session_state:
        return 0.0
    
    data = st.session_state.data
    phase_progress = {}
    
    # --- PHASE 1: 20% (6 fields, each 1/6 of phase 1) ---
    p1 = data.get('phase1', {})
    p1_fields = ['condition', 'setting', 'inclusion', 'exclusion', 'problem', 'objectives']
    p1_completed = sum(1 for k in p1_fields if p1.get(k))
    phase_progress['p1'] = p1_completed / len(p1_fields)
    
    # --- PHASE 2: 20% (2 fields, each 1/2 of phase 2) ---
    p2 = data.get('phase2', {})
    p2_fields = ['mesh_query', 'evidence']
    p2_completed = sum(1 for k in p2_fields if p2.get(k))
    phase_progress['p2'] = p2_completed / len(p2_fields)
    
    # --- PHASE 3: 20% (1 field, worth full phase 3) ---
    p3 = data.get('phase3', {})
    phase_progress['p3'] = 1.0 if p3.get('nodes') else 0.0
    
    # --- PHASE 4: 20% (1 field, worth full phase 4) ---
    p4 = data.get('phase4', {})
    phase_progress['p4'] = 1.0 if p4.get('heuristics_data') else 0.0
    
    # --- PHASE 5: 20% (3 fields, each 1/3 of phase 5) ---
    p5 = data.get('phase5', {})
    p5_fields = ['beta_html', 'expert_html', 'edu_html']
    p5_completed = sum(1 for k in p5_fields if p5.get(k))
    phase_progress['p5'] = p5_completed / len(p5_fields)
    
    # Each phase worth 20% of total
    overall_progress = sum(phase_progress.values()) / 5
    return min(1.0, overall_progress)

def styled_info(text):
    formatted_text = text.replace("Tip:", "<b>Tip:</b>")
    st.markdown(f"""
    <div style="background-color: #FFB0C9; color: black; padding: 10px; border-radius: 5px; border: 1px solid black; margin-bottom: 10px;">
        {formatted_text}
    </div>""", unsafe_allow_html=True)

def upload_and_review_file(uploaded_file, phase_key: str, context: str = ""):
    """
    Upload a file to Gemini, auto-review it, and return markdown summary + file URI.
    Args:
        uploaded_file: Streamlit UploadedFile object
        phase_key: Unique key for session state (e.g., 'p1_refine')
        context: Optional context about what the file is for (e.g., 'clinical pathway')
    Returns:
        dict with 'review' (markdown), 'file_uri', and 'filename'
    """
    if not uploaded_file:
        return None

    client = get_genai_client()
    if not client:
        st.error("API connection error. Cannot upload file.")
        return None

    try:
        # Read file bytes
        file_bytes = uploaded_file.read()

        # Build MIME type
        mime_type = uploaded_file.type or "application/octet-stream"
        if uploaded_file.name.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif uploaded_file.name.endswith('.txt'):
            mime_type = 'text/plain'
        elif uploaded_file.name.endswith('.md'):
            mime_type = 'text/markdown'

        # Upload to Gemini Files API
        from io import BytesIO
        file_obj = BytesIO(file_bytes)
        uploaded = client.files.upload(
            file=file_obj,
            mime_type=mime_type,
            display_name=uploaded_file.name,
        )

        review_text = review_document(uploaded.uri, context)
        st.session_state[f"file_{phase_key}"] = f"File: {uploaded.display_name} ({uploaded.uri})"
        return {
            "review": review_text,
            "file_uri": uploaded.uri,
            "filename": uploaded.display_name,
        }
    except Exception as e:
        st.error(f"File upload failed: {e}")
        return None


def review_document(file_uri: str, context: str = "") -> str:
    """
    Review an uploaded file using Gemini API and return a markdown summary.
    
    Args:
        file_uri: URI of the file uploaded to Gemini Files API
        context: Optional context about what the file is for (e.g., 'clinical pathway')
    
    Returns:
        str: Markdown-formatted review summary
    """
    client = get_genai_client()
    if not client:
        return "⚠️ API connection unavailable. Could not review file."
    
    try:
        context_phrase = f" for {context}" if context else ""
        prompt = f"""Review this document{context_phrase}. Provide a concise summary in markdown format including:
        
- **Purpose**: Main topic and intent
- **Key Points**: 3-5 most important takeaways
- **Relevance**: How this relates to clinical pathway development{context_phrase}

Keep the summary brief (3-5 sentences per section)."""
        
        # Use the file URI in the content
        contents = [
            {
                "parts": [
                    {"text": prompt},
                    {"file_data": {"file_uri": file_uri}}
                ]
            }
        ]
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )
        
        return response.text if response and response.text else "✓ File uploaded successfully. Content available for AI analysis."
    
    except Exception as e:
        return f"✓ File uploaded. *(Auto-review unavailable: {str(e)})*"


def create_formsubmit_html(form_html: str) -> str:
    """
    Ensure FormSubmit.co compatibility in generated HTML.
    Adds dynamic form action based on recipient email field.
    
    Args:
        form_html: Generated HTML form content
        
    Returns:
        str: HTML with FormSubmit integration and dynamic submission
    """
    # Add JavaScript to handle dynamic form submission
    formsubmit_script = r'''
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const form = document.querySelector('form');
        if (form) {
            // Add recipient email field at the top if it doesn't exist
            const hasRecipientField = form.querySelector('input[name="recipient_email"]');
            if (!hasRecipientField) {
                const fieldHTML = `
                    <div style="margin-bottom: 20px; padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
                        <label for="recipient_email" style="font-weight: bold; display: block; margin-bottom: 5px;">
                            Where should this form submission be sent? *
                        </label>
                        <input type="email" id="recipient_email" name="recipient_email" required 
                               placeholder="your-email@hospital.org"
                               style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;">
                        <small style="display: block; margin-top: 5px; color: #666;">
                            Form responses will be sent to this email address via FormSubmit.co
                        </small>
                    </div>
                `;
                form.insertAdjacentHTML('afterbegin', fieldHTML);
            }
            
            // Handle form submission
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                st.divider()

                # Determine current phase selection from navigation
                # Use the authoritative `current_phase_label` to avoid desync loops
                const recipientEmail = form.querySelector('input[name="recipient_email"]').value;
                if (recipientEmail) {
                    form.action = `https://formsubmit.co/${recipientEmail}`;
                    form.method = 'POST';
                    // Add FormSubmit configuration fields
                    if (!form.querySelector('input[name="_subject"]')) {
                        const subjectInput = document.createElement('input');
                        subjectInput.type = 'hidden';
                        subjectInput.name = '_subject';
                        subjectInput.value = document.title || 'Form Submission';
                        form.appendChild(subjectInput);
                    }
                    if (!form.querySelector('input[name="_template"]')) {
                        const templateInput = document.createElement('input');
                        templateInput.type = 'hidden';
                        templateInput.name = '_template';
                        templateInput.value = 'box';
                        form.appendChild(templateInput);
                    }
                    if (!form.querySelector('input[name="_captcha"]')) {
                        const captchaInput = document.createElement('input');
                        captchaInput.type = 'hidden';
                        captchaInput.name = '_captcha';
                        captchaInput.value = 'false';
                        form.appendChild(captchaInput);
                    }
                    form.submit();
                } else {
                    alert('Please provide a recipient email address.');
                }
            });
        }
    });
    </script>
    '''
    
    # Insert script before closing body tag
    if '</body>' in form_html:
        form_html = form_html.replace('</body>', formsubmit_script + '</body>')
    else:
        form_html += formsubmit_script
    
    # Add honeypot field if not present
    if '_honey' not in form_html and 'bot-field' not in form_html:
        honeypot = '<input type="text" name="_honey" style="display:none">'
        if '<form' in form_html:
            form_html = form_html.replace('<form', f'<form>{honeypot}', 1)
    
    return form_html


def make_preview_only(form_html: str) -> str:
    """Convert a generated form to preview-only by hiding email/submit fields and blocking submission."""
    try:
        if not form_html:
            return form_html
        banner = (
            '<div style="background:#FFF3CD;border:1px solid #F0AD4E;color:#8A6D3B;'
            'padding:12px;border-radius:6px;margin:12px 0;">\n'
            '  Preview only — responses are not collected here. Use Google Forms to collect submissions.\n'
            '</div>\n'
        )
        style_js = (
            '<style id="cpq-preview-only">\n'
            'form input[type="email"],\n'
            'form input[type="submit"],\n'
            'form button[type="submit"],\n'
            'form button.submit,\n'
            'form .submit,\n'
            'form .cpq-submit { display: none !important; }\n'
            '</style>\n'
            '<script>\n'
            "document.addEventListener('DOMContentLoaded', function() {\n"
            "  document.querySelectorAll('form').forEach(function(f) {\n"
            "    f.addEventListener('submit', function(e) {\n"
            "      e.preventDefault();\n"
            "      alert('Preview only — responses are not collected here.');\n"
            "    });\n"
            "  });\n"
            "});\n"
            '</script>\n'
        )
        injection = style_js + banner
        if "</body>" in form_html:
            return form_html.replace("</body>", injection + "</body>")
        return injection + form_html
    except Exception:
        return form_html


def mark_provider_connected(provider: str):
    if "oauth" not in st.session_state:
        st.session_state["oauth"] = {}
    st.session_state["oauth"][provider] = True


def render_provider_card(name: str, provider_key: str, description: str, configured: bool, bullets: list, button_key: str):
    """Render a provider card with status and a mock connect CTA (placeholder until real OAuth)."""
    connected = configured or ("oauth" in st.session_state and st.session_state["oauth"].get(provider_key))
    status_color = "#2e7d32" if connected else "#9e9e9e"
    status_text = "Connected" if connected else "Not connected"
    st.markdown(f"<div style='border:1px solid #ddd;border-radius:8px;padding:14px;margin-bottom:8px;'>\n"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<strong>{name}</strong>"
                f"<span style='padding:4px 10px;border-radius:12px;background:{status_color};color:#fff;font-size:12px;'>{status_text}</span>"
                f"</div>\n"
                f"<div style='color:#444;margin:6px 0;'>{description}</div>\n"
                + "".join([f"<div style='color:#555;font-size:13px;'>• {b}</div>" for b in bullets]) +
                "</div>", unsafe_allow_html=True)
    if st.button(f"Connect {name.split()[0]}", width="stretch", key=button_key):
        mark_provider_connected(provider_key)
        st.success(f"{name} connected for this session (placeholder; add OAuth to persist).")


def is_configured(keys) -> bool:
    """Return True if any of the given keys exist in env or Streamlit secrets."""
    try:
        for k in keys:
            if os.getenv(k):
                return True
            if hasattr(st, "secrets") and k in st.secrets:
                return True
    except Exception:
        return False
    return False


def is_google_forms_configured() -> bool:
    # Minimal heuristic: presence of OAuth creds or service account JSON
    keys = [
        "GOOGLE_FORMS_CLIENT_ID",
        "GOOGLE_FORMS_CLIENT_SECRET",
        "GOOGLE_FORMS_REFRESH_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ]
    has_env = is_configured(keys)
    has_session = "oauth" in st.session_state and st.session_state["oauth"].get("google")
    return bool(has_env or has_session)


def _get_secret(key: str, default: str | None = None) -> str | None:
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


def build_google_auth_url() -> str | None:
    client_id = _get_secret("GOOGLE_FORMS_CLIENT_ID")
    redirect_uri = _get_secret("GOOGLE_REDIRECT_URI", _get_secret("OAUTH_REDIRECT_URI", "http://localhost:8501/"))
    scopes = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.body.readonly",
    ]
    if not client_id or not redirect_uri:
        return None
    state = secrets.token_urlsafe(16)
    if "oauth" not in st.session_state:
        st.session_state["oauth"] = {}
    st.session_state["oauth"]["google_state"] = state
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def complete_google_oauth(params: dict) -> bool:
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    expected = st.session_state.get("oauth", {}).get("google_state")
    if not code or not state or state != expected:
        return False
    client_id = _get_secret("GOOGLE_FORMS_CLIENT_ID")
    client_secret = _get_secret("GOOGLE_FORMS_CLIENT_SECRET")
    redirect_uri = _get_secret("GOOGLE_REDIRECT_URI", _get_secret("OAUTH_REDIRECT_URI", "http://localhost:8501/"))
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        import requests
        resp = requests.post(token_url, data=data, timeout=10)
        if resp.status_code == 200:
            token = resp.json()
            st.session_state.setdefault("oauth_tokens", {})["google"] = token
            st.session_state["oauth"]["google"] = True
            return True
    except Exception:
        return False
    return False


def render_connect_link(provider_key: str):
    if provider_key != "google":
        return
    url = build_google_auth_url()
    if url:
        st.link_button("Open consent window", url, width="stretch")
    else:
        st.warning("Missing client configuration. Please set client ID/redirect URI in secrets or env.")


def ensure_carepathiq_footer(html: str) -> str:
    """Append a CarePathIQ-branded footer with inline logo if missing."""
    try:
        if not html or "carepathiq-brand-footer" in html:
            return html
        footer_html = """
<div class=\"carepathiq-brand-footer\" style=\"text-align:center;margin-top:32px;padding-top:16px;border-top:1px solid #ddd;color:#444;\">
  <div style=\"font-weight:600;\">CarePathIQ</div>
  <svg viewBox=\"0 0 300 60\" xmlns=\"http://www.w3.org/2000/svg\" role=\"img\" aria-label=\"CarePathIQ logo\" style=\"width:160px;height:auto;display:block;margin:8px auto;\">
    <rect x=\"0\" y=\"0\" width=\"300\" height=\"60\" fill=\"transparent\"/>
    <text x=\"60\" y=\"38\" font-family=\"Segoe UI, Tahoma, Verdana, sans-serif\" font-size=\"28\" fill=\"#3E2723\">Care</text>
    <text x=\"130\" y=\"38\" font-family=\"Segoe UI, Tahoma, Verdana, sans-serif\" font-size=\"28\" fill=\"#5D4037\">Path</text>
    <text x=\"210\" y=\"38\" font-family=\"Segoe UI, Tahoma, Verdana, sans-serif\" font-size=\"28\" fill=\"#00695C\">IQ</text>
    <circle cx=\"25\" cy=\"30\" r=\"10\" fill=\"#A9EED1\" stroke=\"#3E2723\" stroke-width=\"2\"/>
  </svg>
  <div style=\"font-size:12px;color:#666;\">© CarePathIQ</div>
</div>
"""
        if "</body>" in html:
            return html.replace("</body>", footer_html + "</body>")
        return html + footer_html
    except Exception:
        return html

def fix_edu_certificate_html(html: str) -> str:
    """Ensure the education module's certificate uses landscape layout, brand colors,
    updated approval text, and includes a CarePathIQ logo at the bottom.
    Safe to call multiple times; idempotent-ish.
    """
    try:
        if not html:
            return html
        updated = html.replace("Verified Education Credit", "Approved by CarePathIQ")
        style = """
<style id="cpq-certificate-style">
@page { size: landscape; margin: 1in; }
:root { --cpq-brown:#5D4037; --cpq-brown-dark:#3E2723; --cpq-teal:#A9EED1; }
.cpq-certificate {
  width: 100%;
  max-width: 1100px;
  margin: 20px auto;
  background: #fff;
  border: 6px solid var(--cpq-brown);
  padding: 32px 40px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.cpq-cert-header { text-align:center; color: var(--cpq-brown-dark); border-bottom: 3px solid var(--cpq-teal); padding-bottom: 8px; margin-bottom: 16px; }
.cpq-cert-badge { display:inline-block; background: var(--cpq-teal); color: var(--cpq-brown-dark); font-weight:700; padding: 4px 10px; border-radius: 4px; margin-top: 6px; }
.cpq-cert-body { color: #333; line-height: 1.5; }
.cpq-cert-footer { text-align:center; margin-top: 24px; color: #444; }
.cpq-cert-logo { display:block; margin: 12px auto 0 auto; width: 160px; height: auto; }
</style>
"""
        if "cpq-certificate-style" not in updated:
            if "</head>" in updated:
                updated = updated.replace("</head>", style + "</head>")
            else:
                updated = style + updated

        # Append a real logo image (base64) footer if available; fallback to inline SVG
        if "cpq-cert-logo" not in updated and "Approved by CarePathIQ" in updated:
            logo_html = ""
            try:
                logo_path = os.path.join(os.getcwd(), "CarePathIQ_Logo.png")
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as f:
                        logo_b64 = base64.b64encode(f.read()).decode("utf-8")
                    logo_html = f"""
<div class=\"cpq-cert-footer\">\n  <div>Approved by CarePathIQ</div>\n  <img class=\"cpq-cert-logo\" alt=\"CarePathIQ logo\" src=\"data:image/png;base64,{logo_b64}\" />\n  <div style=\"font-size:12px;color:#666;\">© CarePathIQ</div>\n</div>\n"""
            except Exception:
                logo_html = ""
            if not logo_html:
                logo_html = """
<div class=\"cpq-cert-footer\">\n  <div>Approved by CarePathIQ</div>\n  <svg class=\"cpq-cert-logo\" viewBox=\"0 0 300 60\" xmlns=\"http://www.w3.org/2000/svg\" role=\"img\" aria-label=\"CarePathIQ logo\">\n    <rect x=\"0\" y=\"0\" width=\"300\" height=\"60\" fill=\"transparent\"/>\n    <text x=\"60\" y=\"38\" font-family=\"Segoe UI, Tahoma, Verdana, sans-serif\" font-size=\"28\" fill=\"#3E2723\">Care</text>\n    <text x=\"130\" y=\"38\" font-family=\"Segoe UI, Tahoma, Verdana, sans-serif\" font-size=\"28\" fill=\"#5D4037\">Path</text>\n    <text x=\"210\" y=\"38\" font-family=\"Segoe UI, Tahoma, Verdana, sans-serif\" font-size=\"28\" fill=\"#00695C\">IQ</text>\n    <circle cx=\"25\" cy=\"30\" r=\"10\" fill=\"#A9EED1\" stroke=\"#3E2723\" stroke-width=\"2\"/>\n  </svg>\n  <div style=\"font-size:12px;color:#666;\">© CarePathIQ</div>\n</div>\n"""
            if "</body>" in updated:
                updated = updated.replace("</body>", logo_html + "</body>")
            else:
                updated = updated + logo_html

        return updated
    except Exception:
        return html

def render_refine_suggestions(target_key: str, suggestions: list[str]):
    """Render clickable suggestion buttons that pre-populate a refine text area.
    Clicking a suggestion sets st.session_state[target_key] and reruns.
    """
    if not suggestions:
        return
    st.caption("Quick suggestions:")
    # Render in rows of 3 buttons
    for i in range(0, len(suggestions), 3):
        row = suggestions[i:i+3]
        cols = st.columns(len(row))
        for idx, s in enumerate(row):
            with cols[idx]:
                if st.button(s, key=f"{target_key}_sugg_{i+idx}", width="stretch"):
                    st.session_state[target_key] = s
                    st.rerun()

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
        for m in ihi.get('outcome_measures', []): doc.add_paragraph(m, style='List Bullet')
        
        doc.add_heading('Process Measure(s)', level=2)
        for m in ihi.get('process_measures', []): doc.add_paragraph(m, style='List Bullet')
        
        doc.add_heading('Balancing Measure(s)', level=2)
        for m in ihi.get('balancing_measures', []): doc.add_paragraph(m, style='List Bullet')

        doc.add_heading('What changes can we make?', level=1)
        doc.add_heading('Initial Activities', level=2)
        doc.add_paragraph(ihi.get('initial_activities', ''))
        
        doc.add_heading('Change Ideas', level=2)
        for c in ihi.get('change_ideas', []): doc.add_paragraph(c, style='List Bullet')
        
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

def generate_p1_charter():
    """
    Auto-generate Phase 1 Project Charter using IHI Model for Improvement.
    Updates st.session_state.data['phase1']['ihi_content'] and triggers download.
    """
    d = st.session_state.data['phase1']
    if not d.get('condition') or not d.get('problem'):
        st.warning("Please fill in Condition and Problem before generating charter.")
        return
    
    with st.status("Generating Project Charter...", expanded=True) as status:
        st.write("Building project charter based on IHI Quality Improvement framework...")
        
        p_ihi = f"""You are a Quality Improvement Advisor using IHI's Model for Improvement.

Build a project charter for managing "{d['condition']}" in "{d.get('setting', '') or 'care setting'}".

**Phase 1 Context:**
Problem: {d['problem']}
Inclusion: {d.get('inclusion', '')}
Exclusion: {d.get('exclusion', '')}
Objectives: {d.get('objectives', '')}

Return JSON with keys:
- project_description (string)
- rationale (string)
- expected_outcomes (string)
- aim_statement (string)
- outcome_measures (string)
- process_measures (string)
- balancing_measures (string)
- initial_activities (string)
- change_ideas (array of strings)
- stakeholders (string)
- barriers (string)
- boundaries: object with in_scope (string) and out_of_scope (string)

Return clean JSON ONLY. No markdown, no explanation."""
        
        res = get_gemini_response(p_ihi, json_mode=True)
        if res:
            st.session_state.data['phase1']['ihi_content'] = res
            doc = create_word_docx(st.session_state.data['phase1'])
            if doc:
                status.update(label="Ready!", state="complete")
                st.download_button(
                    "Download Project Charter (.docx)",
                    doc,
                    f"Project_Charter_{d['condition']}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                status.update(label="Word export unavailable. Please ensure python-docx is installed.", state="error")
        else:
            status.update(label="Failed to generate charter.", state="error")

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

def auto_grade_evidence_list(evidence_list: list):
    """
    Auto-grade a list of evidence items using GRADE criteria via Gemini API.
    Updates each item in the list with 'grade' and 'rationale' fields.
    
    Args:
        evidence_list: List of evidence dictionaries with at least 'id' and 'title' keys
    """
    if not evidence_list:
        return
    
    try:
        prompt = (
            "Assign GRADE quality of evidence (use EXACTLY one of: 'High (A)', 'Moderate (B)', 'Low (C)', or 'Very Low (D)') "
            "and provide a brief Rationale (1-2 sentences) for each article. "
            f"{json.dumps([{k:v for k,v in e.items() if k in ['id','title']} for e in evidence_list])}. "
            "Return ONLY valid JSON object where keys are PMID strings and values are objects with 'grade' and 'rationale' fields. "
            '{"12345678": {"grade": "High (A)", "rationale": "text here"}}'
        )
        
        grades = get_gemini_response(prompt, json_mode=True)
        
        if grades and isinstance(grades, dict):
            for e in evidence_list:
                pmid_str = str(e.get('id', ''))
                if pmid_str in grades:
                    grade_data = grades[pmid_str]
                    if isinstance(grade_data, dict):
                        e['grade'] = grade_data.get('grade', 'Un-graded')
                        e['rationale'] = grade_data.get('rationale', 'Not provided.')
                    else:
                        e['grade'] = 'Un-graded'
                        e['rationale'] = 'Not provided.'
                else:
                    e.setdefault('grade', 'Un-graded')
                    e.setdefault('rationale', 'Not yet evaluated.')
        else:
            # If API call fails, set defaults
            for e in evidence_list:
                e.setdefault('grade', 'Un-graded')
                e.setdefault('rationale', 'Auto-grading unavailable.')
    
    except Exception as ex:
        # On error, set defaults and log
        for e in evidence_list:
            e.setdefault('grade', 'Un-graded')
            e.setdefault('rationale', f'Auto-grading error: {str(ex)}')

def format_citation_line(entry, style="APA"):
    """Lightweight formatter for citation strings based on available PubMed fields.
    Supports preset styles (APA, MLA, Vancouver) and custom style names."""
    authors = (entry.get("authors") or "Unknown").rstrip(".")
    title = (entry.get("title") or "Untitled").rstrip(".")
    journal = (entry.get("journal") or "Journal").rstrip(".")
    year = entry.get("year") or "n.d."
    pmid = entry.get("id") or ""
    if style == "MLA":
        return f"{authors}. \"{title}.\" {journal}, {year}. PMID {pmid}."
    if style == "Vancouver":
        return f"{authors}. {title}. {journal}. {year}. PMID:{pmid}."
    # Default APA (also used for custom style names)
    return f"{authors} ({year}). {title}. {journal}. PMID: {pmid}."

def apply_pathway_heuristic_improvements(nodes, heuristics_data, extra_ui_insights=None):
    """
    Intelligently apply feasible heuristics (H1-H10) to pathway nodes.
    CRITICAL: Preserves and enhances clinical complexity, does NOT reduce it.
    The AI evaluates each heuristic and applies only those that improve without compromising decision science.
    Returns: (updated_nodes, applied_heuristics_list, summary_text) or (None, [], "")
    """
    if not heuristics_data:
        return None, [], ""

    # Include all heuristics in the analysis
    insights_text = "\n".join([f"{k}: {v}" for k, v in sorted(heuristics_data.items())])

    guardrails = """Safety rules (MANDATORY):
1) PRESERVE all clinical complexity and decision branches—never simplify away clinical logic
2) Do NOT reduce decision divergence or collapse distinct pathways
3) Do NOT remove edge cases or special population considerations
4) Preserve all node IDs, branching structure, and evidence citations
5) Add detail and specificity—do NOT generalize clinical steps
6) Only modify text clarity, add safety annotations, or improve organization
7) Add new nodes ONLY if critical for safety or decision clarity
8) For each heuristic applied, explain how it enhances (not reduces) the pathway"""

    prompt = f"""You are a CLINICAL DECISION SCIENTIST with expertise in Medical Decision Analysis and Nielsen's Usability Heuristics.

TASK: Apply feasible heuristics to improve this clinical decision pathway while PRESERVING AND ENHANCING decision-science integrity.

CRITICAL PRINCIPLE: This is NOT about simplification. Improvements should make the pathway MORE usable, more complete, and more clinically rigorous—not less complex.

Current pathway ({len(nodes)} nodes):
{json.dumps(nodes)}

Heuristic Assessment:
{insights_text}

APPLICATION STRATEGY:
- H1 (Status visibility): ADD checkpoint descriptions and alarm thresholds (enhances clinical specificity)
- H2 (Language clarity): Clarify terminology WITHOUT removing medical precision needed for safety
- H3 (User control): ADD escape routes/alternative pathways (increases decision options)
- H4 (Consistency): Standardize decision structures AND expand them uniformly
- H5 (Error prevention): ADD validation rules and edge case handling (increases complexity beneficially)
- H6 (Recognition not recall): Improve labeling clarity while preserving all decision detail
- H7 (Efficiency): Remove ONLY redundant steps; keep clinical content and decision branches
- H8 (Minimalist): Consolidate presentation, NOT clinical content; respect DAG and decision divergence
- H9 (Error recovery): Move critical checks EARLIER and ADD recovery pathways (increases safety)
- H10 (Help & docs): ADD evidence citations and rationale annotations to decision nodes

{guardrails}

BEFORE/AFTER RULE:
- Evaluate: Does this improvement ADD clinical value, clarity, or safety?
- If yes: Apply it and include in applied_heuristics list
- If no: Skip it
- NEVER: Reduce complexity, remove branches, generalize clinical steps, or simplify decision trees

Return ONLY valid JSON:
{{
  "updated_nodes": [array of modified node objects with enhanced detail and annotations],
  "applied_heuristics": ["H2", "H4", "H5", ...list of heuristics that genuinely improved the pathway],
  "applied_summary": "Detailed explanation of improvements made and how each enhances clinical decision-making"
}}

VALIDATION CHECKLIST BEFORE RETURNING:
- Node count maintained or INCREASED (not decreased)
- All Decision node branches still present and distinct
- Evidence citations preserved on all applicable nodes
- No "or" statements in End nodes
- DAG structure maintained (no cycles)
- All 4 clinical stages still represented: Initial Evaluation, Diagnosis/Treatment, Re-evaluation, Final Disposition
- Clinical depth enhanced, not reduced"""

    response = get_gemini_response(prompt, json_mode=True)
    
    if response and isinstance(response, dict):
        updated_nodes = response.get("updated_nodes")
        applied = response.get("applied_heuristics", [])
        summary = response.get("applied_summary", "")
        
        if updated_nodes and isinstance(updated_nodes, list) and isinstance(applied, list):
            # Optionally validate the returned nodes meet our standards
            validation = validate_decision_science_pathway(updated_nodes)
            if validation['complexity']['complexity_level'] != 'comprehensive':
                # If heuristics reduced complexity, log warning but still return
                st.warning(f"⚠️ Heuristic application reduced pathway complexity. Original: {len(nodes)} nodes, Updated: {len(updated_nodes)} nodes. Review the changes.")
            return updated_nodes, applied, summary
    
    return None, [], ""


def apply_actionable_heuristics_incremental(nodes, heuristics_data):
    """
    Intelligently apply all feasible heuristics to the pathway.
    The AI evaluates all H1-H10 and applies only those that work for pathway nodes.
    Returns: (updated_nodes, applied_heuristics_list, summary_text)
    """
    updated_nodes, applied_list, summary = apply_pathway_heuristic_improvements(nodes, heuristics_data, {})
    return updated_nodes, applied_list, summary

def create_references_docx(citations, style="APA"):
    """Create Word document with citations. Supports preset styles and custom style names."""
    if Document is None or not citations:
        return None
    doc = Document()
    # Use the style name (preset or custom) in the heading
    heading_text = f"References ({style})" if style else "References"
    doc.add_heading(heading_text, 0)
    for idx, entry in enumerate(citations, start=1):
        line = format_citation_line(entry, style)
        doc.add_paragraph(f"{idx}. {line}")
    # Add licensing/footer similar to other DOCX exports
    try:
        section = doc.sections[0]
        footer = section.footer
        p = footer.paragraphs[0]
        p.text = "CarePathIQ © 2024 by Tehreem Rehman is licensed under CC BY-SA 4.0"
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception:
        pass
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def harden_nodes(nodes_list):
    """Validate and fix node structure, ensuring Decision nodes have proper branches."""
    if not isinstance(nodes_list, list): return []
    validated = []
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict): continue
        # Ensure required fields
        if 'id' not in node or not node['id']: 
            node['id'] = f"{node.get('type', 'P')[0].upper()}{i+1}"
        if 'type' not in node: 
            node['type'] = 'Process'
        if 'label' not in node or not node.get('label'):
            node['label'] = f"Step {i+1}"
        
        # Validate Decision nodes have branches
        if node['type'] == 'Decision':
            if 'branches' not in node or not isinstance(node['branches'], list) or len(node['branches']) == 0:
                # Create default branches pointing to next nodes if they exist
                next_idx = i + 1
                alt_idx = i + 2 if i + 2 < len(nodes_list) else i + 1
                node['branches'] = [
                    {'label': 'Yes', 'target': next_idx}, 
                    {'label': 'No', 'target': alt_idx}
                ]
            # Ensure branches have valid structure and targets are within bounds
            for branch in node['branches']:
                if 'label' not in branch:
                    branch['label'] = 'Option'
                if 'target' not in branch or not isinstance(branch.get('target'), (int, float)):
                    branch['target'] = min(i + 1, len(nodes_list) - 1)
                else:
                    # Clamp target to valid range
                    target = int(branch['target'])
                    branch['target'] = max(0, min(target, len(nodes_list) - 1))
        
        validated.append(node)
    return validated

def validate_pathway_flow(nodes_list):
    """
    Validate pathway for common flow issues:
    - Unreachable nodes (orphaned)
    - Invalid branch targets
    - Missing End nodes
    - Cycles (if DAG-only enforcement needed)
    Returns: (is_valid, issues_list)
    """
    if not isinstance(nodes_list, list) or len(nodes_list) == 0:
        return False, ["Empty pathway"]
    
    issues = []
    n = len(nodes_list)
    reachable = set([0])  # Start node is always index 0
    
    # Build reachability graph
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict):
            issues.append(f"Node {i}: Invalid node structure")
            continue
        
        node_type = node.get('type', 'Process')
        
        if node_type == 'Decision':
            branches = node.get('branches', [])
            if not branches:
                issues.append(f"Node {i} ({node.get('label', 'N/A')}): Decision node has no branches")
            for branch in branches:
                target = branch.get('target')
                if not isinstance(target, (int, float)):
                    issues.append(f"Node {i}: Branch '{branch.get('label', 'N/A')}' has invalid target: {target}")
                elif not (0 <= int(target) < n):
                    issues.append(f"Node {i}: Branch '{branch.get('label', 'N/A')}' points to out-of-bounds index: {target}")
                else:
                    reachable.add(int(target))
        elif i + 1 < n:
            # Non-decision nodes implicitly connect to next node
            reachable.add(i + 1)
    
    # Check for unreachable nodes (except End nodes which are terminal)
    unreachable = []
    for i, node in enumerate(nodes_list):
        if i not in reachable and node.get('type') != 'End':
            unreachable.append(f"Node {i} ({node.get('label', 'N/A')})")
    
    if unreachable:
        issues.append(f"Unreachable nodes: {', '.join(unreachable)}")
    
    # Check for at least one End node
    has_end = any(node.get('type') == 'End' for node in nodes_list)
    if not has_end:
        issues.append("Pathway has no End nodes")
    
    # Check for Start node
    if nodes_list[0].get('type') != 'Start':
        issues.append(f"First node should be Start, found: {nodes_list[0].get('type')}")
    
    return len(issues) == 0, issues

def fix_decision_flow_issues(nodes_list):
    """
    Fix common AI generation issues:
    1. Remove any nodes that appear after End nodes (End nodes must be terminal)
    2. Validate Decision node branches point to valid indices
    3. Detect if Decision branches artificially reconverge (both point to same next node) and keep them separate
    """
    if not isinstance(nodes_list, list) or len(nodes_list) == 0:
        return nodes_list
    
    # Find first End node - everything after it should be removed
    first_end_idx = None
    for i, node in enumerate(nodes_list):
        if isinstance(node, dict) and node.get('type') == 'End':
            first_end_idx = i
            break
    
    # If there's an End node followed by more nodes, truncate
    if first_end_idx is not None and first_end_idx < len(nodes_list) - 1:
        nodes_list = nodes_list[:first_end_idx + 1]
    
    # Validate Decision node branches
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict):
            continue
        if node.get('type') == 'Decision' and 'branches' in node:
            valid_branches = []
            for branch in node.get('branches', []):
                target = branch.get('target')
                if isinstance(target, (int, float)) and 0 <= int(target) < len(nodes_list):
                    valid_branches.append(branch)
            if valid_branches:
                node['branches'] = valid_branches
    
    return nodes_list

def normalize_or_logic(nodes_list):
    """
    Automatically detect and convert OR logic in End nodes to proper Decision nodes with branches.
    This runs silently as backend auto-normalization with no user notification.
    
    Example: "Discharge or Admit to Cardiology" (End node)
    Becomes: "Disposition decision?" (Decision) with branches to "Discharge" and "Admit to Cardiology" (End nodes)
    """
    if not isinstance(nodes_list, list) or len(nodes_list) == 0:
        return nodes_list
    
    normalized = []
    added_nodes = []
    
    for idx, node in enumerate(nodes_list):
        if not isinstance(node, dict):
            normalized.append(node)
            continue
        
        # Check if this is an End node with OR logic
        label = node.get('label', '').lower()
        if node.get('type') == 'End' and ' or ' in label:
            # Extract the original label for clarity
            original_label = node.get('label', '')
            
            # Split by ' or ' to get individual outcomes
            outcomes = [o.strip() for o in original_label.split(' or ')]
            
            if len(outcomes) > 1:
                # Convert this End node to a Decision node
                decision_label = f"{outcomes[0].split()[0]} vs {outcomes[1].split()[0] if len(outcomes[1].split()) > 0 else 'other'}?"
                decision_node = {
                    'type': 'Decision',
                    'label': decision_label,
                    'evidence': node.get('evidence', 'N/A'),
                    'branches': []
                }
                
                # Create End nodes for each outcome
                end_node_targets = []
                for outcome_idx, outcome in enumerate(outcomes):
                    end_node = {
                        'type': 'End',
                        'label': outcome,
                        'evidence': 'N/A'
                    }
                    added_nodes.append(end_node)
                    # Calculate target index: current position + branches + previously added nodes
                    target_idx = len(normalized) + 1 + outcome_idx
                    end_node_targets.append(target_idx)
                    
                    # Add branch to decision node
                    decision_node['branches'].append({
                        'label': outcome.split()[0],  # First word of outcome as branch label
                        'target': target_idx
                    })
                
                normalized.append(decision_node)
            else:
                # No actual OR split possible, keep as-is
                normalized.append(node)
        else:
            normalized.append(node)
    
    # Append all newly created End nodes at the end
    result = normalized + added_nodes
    
    # Update all target indices to account for insertions
    # Rebuild with proper sequential indexing
    final_result = []
    for node in result:
        final_node = dict(node)
        if final_node.get('type') == 'Decision' and 'branches' in final_node:
            # Branches already set correctly during creation
            pass
        final_result.append(final_node)
    
    return final_result

def assess_clinical_complexity(nodes_list):
    """
    Assess whether a pathway has appropriate clinical complexity per decision science standards.
    
    Returns: dict with complexity metrics
    {
        'node_count': int,
        'complexity_level': 'minimal' | 'moderate' | 'comprehensive',
        'decision_count': int,
        'decision_divergence_ratio': float (how much branches stay separate),
        'evidence_coverage': float (% nodes with PMIDs),
        'clinical_stage_coverage': dict (which 4 stages are represented),
        'recommendations': [str]
    }
    """
    if not isinstance(nodes_list, list) or len(nodes_list) == 0:
        return {'complexity_level': 'minimal', 'recommendations': ['Pathway is empty']}
    
    metrics = {
        'node_count': len(nodes_list),
        'decision_count': 0,
        'process_count': 0,
        'end_count': 0,
        'decision_divergence_ratio': 0.0,
        'evidence_coverage': 0.0,
        'clinical_stage_coverage': {},
        'recommendations': []
    }
    
    # Count node types and stage coverage
    stages = {
        'initial_evaluation': False,
        'diagnosis_treatment': False,
        're_evaluation': False,
        'final_disposition': False
    }
    
    stage_keywords = {
        'initial_evaluation': ['initial', 'assess', 'vital', 'exam', 'presentation', 'triage'],
        'diagnosis_treatment': ['diagnos', 'treat', 'interven', 'medic', 'workup', 'order'],
        're_evaluation': ['recheck', 'monitor', 'response', 'follow', 'escalat', 're-evaluat'],
        'final_disposition': ['discharg', 'admit', 'transfer', 'disposition', 'prescri', 'referral']
    }
    
    pmid_nodes = 0
    for node in nodes_list:
        if not isinstance(node, dict):
            continue
        
        ntype = node.get('type', 'Process')
        if ntype == 'Decision':
            metrics['decision_count'] += 1
        elif ntype == 'Process':
            metrics['process_count'] += 1
        elif ntype == 'End':
            metrics['end_count'] += 1
        
        # Check stage coverage
        label_lower = (node.get('label', '') or '').lower()
        for stage, keywords in stage_keywords.items():
            if any(kw in label_lower for kw in keywords):
                stages[stage] = True
        
        # Check evidence coverage
        if node.get('evidence') and node.get('evidence') != 'N/A':
            pmid_nodes += 1
    
    metrics['clinical_stage_coverage'] = stages
    metrics['evidence_coverage'] = pmid_nodes / len(nodes_list) if nodes_list else 0.0
    
    # Assess divergence: check if Decision nodes lead to distinct downstream paths
    divergent_decisions = 0
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict) or node.get('type') != 'Decision':
            continue
        branches = node.get('branches', [])
        if len(branches) >= 2:
            # Check if branches lead to truly different sequences (not immediate reconvergence)
            branch_targets = [b.get('target') for b in branches if isinstance(b.get('target'), (int, float))]
            if len(set(branch_targets)) == len(branch_targets):  # All unique targets
                divergent_decisions += 1
    
    metrics['decision_divergence_ratio'] = divergent_decisions / max(1, metrics['decision_count'])
    
    # Determine complexity level
    if metrics['node_count'] < 12:
        metrics['complexity_level'] = 'minimal'
        metrics['recommendations'].append('⚠️ Pathway may be oversimplified. Consider adding more decision branches and edge cases.')
    elif metrics['node_count'] < 20:
        metrics['complexity_level'] = 'moderate'
        metrics['recommendations'].append('Pathway has moderate complexity. Consider adding edge cases or special populations.')
    else:
        metrics['complexity_level'] = 'comprehensive'
        metrics['recommendations'].append('✓ Pathway has appropriate complexity for evidence-based decision science.')
    
    # Check stage coverage
    stages_covered = sum(1 for v in stages.values() if v)
    if stages_covered < 4:
        metrics['recommendations'].append(f'⚠️ Missing clinical stages: {", ".join([k.replace("_", " ").title() for k, v in stages.items() if not v])}')
    
    # Check evidence coverage
    if metrics['evidence_coverage'] < 0.3:
        metrics['recommendations'].append(f'⚠️ Low evidence coverage ({metrics["evidence_coverage"]:.0%}). Add PMID citations to key clinical steps.')
    
    # Check decision divergence
    if metrics['decision_divergence_ratio'] < 0.5:
        metrics['recommendations'].append('⚠️ Many Decision nodes reconverge quickly. Consider keeping branches more distinct.')
    
    if metrics['end_count'] < 2:
        metrics['recommendations'].append('⚠️ Pathway has few distinct end points. Clinical reality typically has multiple outcomes.')
    
    return metrics

def assess_decision_science_integrity(nodes_list):
    """
    Assess whether pathway follows decision science best practices per Medical Decision Analysis framework.
    
    Returns: dict with integrity metrics and violations
    {
        'is_dag': bool (directed acyclic graph - no cycles),
        'terminal_end_nodes': bool (all End nodes are terminal),
        'no_or_logic': bool (no "or" statements in End nodes),
        'benefit_harm_annotated': bool (Decision nodes mention trade-offs),
        'evidence_cited': bool (key steps have PMIDs),
        'violations': [str]
    }
    """
    if not isinstance(nodes_list, list) or len(nodes_list) == 0:
        return {'violations': ['Empty pathway']}
    
    integrity = {
        'is_dag': True,
        'terminal_end_nodes': True,
        'no_or_logic': True,
        'benefit_harm_annotated': False,
        'evidence_cited': False,
        'violations': []
    }
    
    # Check for cycles (simple reachability check)
    visited = set()
    def has_cycle(node_idx, path):
        if node_idx in path:
            return True
        if node_idx in visited:
            return False
        visited.add(node_idx)
        path.add(node_idx)
        
        node = nodes_list[node_idx] if 0 <= node_idx < len(nodes_list) else None
        if not node or not isinstance(node, dict):
            return False
        
        if node.get('type') == 'Decision':
            for branch in node.get('branches', []):
                target = branch.get('target')
                if isinstance(target, (int, float)) and has_cycle(int(target), path.copy()):
                    return True
        elif node_idx + 1 < len(nodes_list):
            if has_cycle(node_idx + 1, path.copy()):
                return True
        
        return False
    
    if has_cycle(0, set()):
        integrity['is_dag'] = False
        integrity['violations'].append('🔄 Cycle detected: pathway has backward loops')
    
    # Check End nodes are terminal (nothing after them)
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict):
            continue
        if node.get('type') == 'End' and i + 1 < len(nodes_list):
            next_node = nodes_list[i + 1]
            if isinstance(next_node, dict) and next_node.get('type') not in ('End', None):
                integrity['terminal_end_nodes'] = False
                integrity['violations'].append(f"Node {i} is End but followed by {next_node.get('type')} at index {i+1}")
    
    # Check for OR logic in End nodes
    for i, node in enumerate(nodes_list):
        if not isinstance(node, dict):
            continue
        if node.get('type') == 'End':
            label = (node.get('label') or '').lower()
            if ' or ' in label:
                integrity['no_or_logic'] = False
                integrity['violations'].append(f"Node {i} (End): Contains 'or' logic: '{node.get('label')}'. Split into Decision branches.")
    
    # Check for benefit/harm trade-off annotations
    benefit_harm_keywords = ['trade', 'vs', 'benefit', 'risk', 'harm', 'weigh', 'consider']
    harm_annotated_count = 0
    for node in nodes_list:
        if not isinstance(node, dict) or node.get('type') != 'Decision':
            continue
        label = (node.get('label', '') or '').lower()
        detail = (node.get('detail', '') or '').lower()
        full_text = label + ' ' + detail
        if any(kw in full_text for kw in benefit_harm_keywords):
            harm_annotated_count += 1
    
    if harm_annotated_count >= max(1, nodes_list.__len__() // 5):
        integrity['benefit_harm_annotated'] = True
    else:
        integrity['violations'].append(f"⚠️ Few Decision nodes annotate benefit/harm trade-offs ({harm_annotated_count}). Consider adding rationale.")
    
    # Check evidence coverage
    pmid_count = sum(1 for n in nodes_list if isinstance(n, dict) and n.get('evidence') and n.get('evidence') != 'N/A')
    if pmid_count >= len(nodes_list) * 0.3:
        integrity['evidence_cited'] = True
    else:
        integrity['violations'].append(f"⚠️ Low PMID coverage ({pmid_count}/{len(nodes_list)}). Cite evidence for key clinical steps.")
    
    return integrity

def validate_decision_science_pathway(nodes_list):
    """
    Comprehensive validation: combines complexity assessment and integrity check.
    Returns: dict with detailed diagnostic info
    """
    complexity = assess_clinical_complexity(nodes_list)
    integrity = assess_decision_science_integrity(nodes_list)
    flow_valid, flow_issues = validate_pathway_flow(nodes_list)
    
    return {
        'complexity': complexity,
        'integrity': integrity,
        'flow_valid': flow_valid,
        'flow_issues': flow_issues,
        'overall_quality': sum([
            complexity['complexity_level'] == 'comprehensive',
            integrity['is_dag'],
            integrity['terminal_end_nodes'],
            integrity['no_or_logic'],
            integrity['evidence_cited'],
            flow_valid
        ]) / 6
    }

def generate_mermaid_code(nodes, orientation="TD"):
    """Legacy function - now redirects to DOT format for compatibility."""
    return dot_from_nodes(nodes, orientation)

# --- GRAPH EXPORT HELPERS (Graphviz/DOT) ---
def _escape_label(text: str) -> str:
    if text is None:
        return ""
    # Escape quotes and backslashes for DOT labels
    return str(text).replace("\\", "\\\\").replace("\"", "'").replace("\n", "\\n")

def _wrap_label(text: str, width: int = 22) -> str:
    if not text:
        return ""
    wrapped = textwrap.wrap(str(text), width=width)
    return "\\n".join(wrapped) if wrapped else str(text)

def _role_fill(role: str, default_fill: str) -> str:
    if not role:
        return default_fill
    return ROLE_COLORS.get(role, ROLE_COLORS.get(str(role).title(), default_fill))

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
            label = _escape_label(_wrap_label(n.get('label', 'Step')))
            detail = _escape_label(_wrap_label(n.get('detail', '')))
            meds = _escape_label(n.get('medications', ''))
            if meds:
                detail = f"{detail}\\nMeds: {meds}" if detail else f"Meds: {meds}"
            full_label = f"{label}\\n{detail}" if detail else label
            ntype = n.get('type', 'Process')
            if ntype == 'Decision': shape, fill = 'diamond', '#F8CECC'
            elif ntype in ('Start', 'End'): shape, fill = 'oval', '#D5E8D4'
            elif ntype == 'Reevaluation': shape, fill = 'box', '#FFCC80'
            else: shape, fill = 'box', '#FFF2CC'
            fill = _role_fill(n.get('role', ''), fill)
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
        # Skip creating swimlane entries for nodes without a role - they'll be added to default process group
        role = n.get('role', '')
        if not role or role == 'Unassigned':
            role = 'Process'  # Default role instead of 'Unassigned'
        swimlanes[role].append((i, n))
    rankdir = 'TB' if orientation == 'TD' else 'LR'
    g = graphviz.Digraph(format='svg')
    g.attr(rankdir=rankdir)
    g.attr('node', fontname='Helvetica')
    g.attr('edge', fontname='Helvetica')
    node_id_map = {}
    for role, n_list in swimlanes.items():
        with g.subgraph(name=f"cluster_{re.sub(r'[^A-Za-z0-9_]', '_', str(role) or 'Process')}") as c:
            c.attr(label=str(role))
            c.attr(style='filled', color='lightgrey')
            for i, n in n_list:
                nid = f"N{i}"; node_id_map[i] = nid
                label = _escape_label(_wrap_label(n.get('label', 'Step')))
                detail = _escape_label(_wrap_label(n.get('detail', '')))
                meds = _escape_label(n.get('medications', ''))
                if meds:
                    detail = f"{detail}\\nMeds: {meds}" if detail else f"Meds: {meds}"
                full_label = f"{label}\\n{detail}" if detail else label
                ntype = n.get('type', 'Process')
                if ntype == 'Decision': shape, fill = 'diamond', '#F8CECC'
                elif ntype in ('Start', 'End'): shape, fill = 'oval', '#D5E8D4'
                elif ntype == 'Reevaluation': shape, fill = 'box', '#FFCC80'
                else: shape, fill = 'box', '#FFF2CC'
                fill = _role_fill(n.get('role', ''), fill)
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

def get_smart_model_cascade(requires_vision=False, requires_json=False):
    """Return prioritized list of models for Auto mode based on task requirements.
    
    Model names per official docs: https://ai.google.dev/gemini-api/docs/models
    - gemini-2.5-flash: Fast, multimodal, 1M token context (most sophisticated)
    - gemini-3-flash: Newest model with improved performance
    - gemini-2.5-flash-lite: Lightweight variant
    - gemini-2.5-flash-tts: Multimodal with text-to-speech
    
    Strategy: Try models from most to least sophisticated. Auto mode cascades through
    available models until quota is found. User-selected models fall back to alternatives.
    """
    if model_choice == "Auto":
        # Cascade from most to least sophisticated (broader quota coverage)
        if requires_vision:
            return [
                "gemini-2.5-flash",           # Most sophisticated for vision
                "gemini-3-flash",              # Newest alternative
                "gemini-2.5-flash-lite",       # Lighter weight fallback
                "gemini-2.5-flash-tts",        # Text-to-speech variant
            ]
        else:
            return [
                "gemini-2.5-flash",           # Most sophisticated general model
                "gemini-3-flash",              # Newest alternative
                "gemini-2.5-flash-lite",       # Lighter weight fallback
                "gemini-2.5-flash-tts",        # Alternative multimodal option
            ]
    else:
        # Use user-selected model with intelligent fallback
        return [model_choice, "gemini-2.5-flash", "gemini-3-flash", "gemini-2.5-flash-lite"]

def get_gemini_response(prompt, json_mode=False, stream_container=None, image_data=None, timeout=30):
    """
    Send a prompt (with optional image) to Gemini and get a response.
    Per official API: https://ai.google.dev/gemini-api/docs/api-key
    
    Args:
        prompt: Text prompt string
        json_mode: If True, extract JSON from response
        stream_container: Deprecated (v1 API)
        image_data: Optional dict with 'mime_type' and 'data' (base64 bytes) for image
        timeout: Seconds to wait per model before moving to next
    """
    client = get_genai_client()
    if not client:
        st.error("AI Error. Please check API Key.")
        return None

    # Smart cascade: if image provided, prioritize vision models
    candidates = get_smart_model_cascade(requires_vision=bool(image_data), requires_json=json_mode)

    # Build contents array per official API structure
    # https://ai.google.dev/gemini-api/docs/api-overview#request-body
    if image_data:
        # Multimodal: text + image
        contents = [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": image_data.get('mime_type', 'image/jpeg'),
                            "data": image_data['data']
                        }
                    }
                ]
            }
        ]
    else:
        # Text-only: wrap in proper structure
        contents = [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]

    response = None
    last_error = None
    skipped_models = []
    
    for model_name in candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
            )
            # Check if response has valid text
            if response and hasattr(response, 'text'):
                break
        except Exception as e:
            error_str = str(e)
            last_error = error_str

            # Check if error is quota exhaustion (429 RESOURCE_EXHAUSTED)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                skipped_models.append(f"{model_name} (quota)")
            else:
                skipped_models.append(f"{model_name} (unavailable)")

            # Continue to next candidate
            time.sleep(0.3)
            continue

    if not response:
        tried_info = " → ".join(skipped_models) if skipped_models else ", ".join(candidates)
        summary = "AI rate limit or model unavailable. Try again later or pick another model."
        details = f"Details: {last_error}" if last_error else f"Tried: {tried_info}"
        with st.expander(summary, expanded=False):
            st.code(details)
        st.error(summary)
        return None

    try:
        # Access response.text per official API
        text = response.text if hasattr(response, 'text') else ""
        
        if not text:
            return None

        if json_mode:
            # Clean markdown code blocks
            text = text.replace('```json', '').replace('```', '').strip()
            # Extract JSON object or array
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
            if match:
                text = match.group(0)
            try:
                return json.loads(text)
            except Exception:
                return None
        return text
    except Exception:
        st.error("AI response parsing error. Please retry.")
        return None

@st.cache_data(ttl=3600)
def get_available_models(api_key):
    """Fetch list of available models from Gemini API.
    Uses client.models.list() per official SDK.
    https://ai.google.dev/gemini-api/docs/models
    """
    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        model_names = []
        for m in models:
            # Extract model name
            name = getattr(m, 'name', '')
            if name:
                # Model names come as 'models/gemini-2.5-flash' format
                # Extract just the model ID
                if 'models/' in name:
                    model_id = name.split('models/')[-1]
                    model_names.append(model_id)
                else:
                    model_names.append(name)
        return sorted(list(set(model_names))) if model_names else None
    except Exception as e:
        # Silently fail for caching purposes
        return None

def validate_ai_connection() -> bool:
    """Attempt a minimal generate_content call to verify the API key/model works.
    Returns True if a response is obtained, else False.
    Per official API: https://ai.google.dev/gemini-api/docs/quickstart
    """
    client = get_genai_client()
    if not client:
        return False
    try:
        # Use proper content structure per official API
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"parts": [{"text": "ping"}]}]
        )
        return bool(resp and hasattr(resp, 'text') and resp.text)
    except Exception as e:
        # Store concise summary instead of verbose raw error
        err = str(e)
        if "RESOURCE_EXHAUSTED" in err or "429" in err or "quota" in err:
            st.session_state["ai_error"] = "Rate limit exceeded. Please try again later."
        elif "UNAUTHENTICATED" in err or "invalid" in err:
            st.session_state["ai_error"] = "Invalid API key. Check and retry."
        elif "PERMISSION_DENIED" in err:
            st.session_state["ai_error"] = "Permission denied for model. Try another model."
        else:
            st.session_state["ai_error"] = "AI service error. Please try again."
        return False

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

def fetch_single_pmid(pmid):
    """Fetch metadata for a single PMID from PubMed. Returns evidence dict with default grade."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        # With rate limiting: respect NCBI 3 requests/second limit
        time.sleep(0.4)
        
        fetch_params = {'db': 'pubmed', 'id': pmid, 'retmode': 'xml'}
        with urllib.request.urlopen(base_url + "efetch.fcgi?" + urllib.parse.urlencode(fetch_params)) as response:
            root = ET.fromstring(response.read().decode())
        
        article = root.find('.//PubmedArticle')
        if article is None:
            return None
        
        medline = article.find('MedlineCitation')
        if medline is None:
            return None
        
        pmid_elem = medline.find('PMID')
        title_elem = medline.find('Article/ArticleTitle')
        
        if pmid_elem is None or title_elem is None:
            return None
        
        # Authors
        author_list = article.findall('.//Author')
        authors_str = "Unknown"
        if author_list:
            authors = []
            for auth in author_list[:3]:
                lname = auth.find('LastName')
                init = auth.find('Initials')
                if lname is not None and init is not None:
                    authors.append(f"{lname.text} {init.text}")
            authors_str = ", ".join(authors)
            if len(author_list) > 3:
                authors_str += ", et al."
        
        # Year
        year_node = article.find('.//PubDate/Year')
        year = year_node.text if year_node is not None else "N/A"
        
        # Journal
        journal = medline.find('Article/Journal/Title').text if medline.find('Article/Journal/Title') is not None else "N/A"
        
        # Abstract
        abs_node = medline.find('Article/Abstract')
        abstract_text = " ".join([e.text for e in abs_node.findall('AbstractText') if e.text]) if abs_node is not None else "No abstract."
        
        return {
            "id": pmid_elem.text,
            "title": title_elem.text,
            "authors": authors_str,
            "year": year,
            "journal": journal,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_elem.text}/",
            "abstract": abstract_text,
            "grade": "Un-graded",
            "rationale": "Auto-added; pending review",
            "source": "enriched_from_phase3"
        }
    except Exception as e:
        return None

def extract_pmids_from_nodes(nodes):
    """Extract all unique PMIDs from pathway nodes that are not 'N/A'."""
    pmids = set()
    for node in nodes:
        pmid = node.get('evidence', 'N/A')
        if pmid and pmid not in ['N/A', '', None]:
            pmids.add(str(pmid).strip())
    return pmids

def enrich_phase2_with_new_pmids(new_pmids, existing_pmids):
    """
    Compare Phase 3 PMIDs with Phase 2 PMIDs.
    Fetch and add any new PMIDs to Phase 2 evidence.
    Returns list of newly added evidence entries.
    """
    pmids_to_add = new_pmids - existing_pmids
    if not pmids_to_add:
        return []
    
    new_evidence = []
    for pmid in sorted(pmids_to_add):
        evidence_entry = fetch_single_pmid(pmid)
        if evidence_entry:
            new_evidence.append(evidence_entry)
    
    return new_evidence

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
# 3A. CHAT & FEEDBACK HELPER FUNCTIONS
# ==========================================

def initialize_chat_state():
    """Initialize chat messages in session state if not exists."""
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    if "chat_expanded" not in st.session_state:
        # Auto-open if query param ?chat=1 is present
        qp = _get_query_param("chat")
        st.session_state["chat_expanded"] = str(qp).lower() in ("1", "true", "yes", "y")


def save_feedback_response(rating: int, feedback_text: str, phase: str = ""):
    """Save feedback response as JSON to data/feedback/ folder."""
    import datetime
    os.makedirs("data/feedback", exist_ok=True)
    
    # Safely get pathway condition from session state
    pathway_condition = ""
    if hasattr(st.session_state, 'data') and isinstance(st.session_state.data, dict):
        pathway_condition = st.session_state.data.get("phase1", {}).get("condition", "")
    
    feedback_data = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "rating": rating,
        "feedback_text": feedback_text,
        "phase": phase,
        "pathway_condition": pathway_condition
    }
    
    timestamp_ms = int(datetime.datetime.utcnow().timestamp() * 1000)
    filename = f"data/feedback/feedback_{timestamp_ms}.json"
    with open(filename, "w") as f:
        json.dump(feedback_data, f, indent=2)


def get_carepathiq_scoped_response(user_question: str) -> str:
    """
    Get a response from Gemini scoped strictly to CarePathIQ app questions.
    Enhanced with comprehensive knowledge of app structure, files, and capabilities.
    """
    # Try local FAQ first (lightweight, always works)
    response = get_local_faq_answer(user_question)
    if response:
        return response
    
    # Only try AI if client is available
    client = get_genai_client()
    if not client:
        return "Please enter your Gemini API key in the sidebar to enable AI-powered answers."
    
    scope_constraint = """You are the CarePathIQ AI Agent - an expert assistant with complete knowledge of the CarePathIQ clinical pathway development application.

**The 5 Phases in Detail:**

1. **Phase 1: Define Scope & Charter** — Input clinical condition and care setting. AI auto-drafts inclusion/exclusion criteria, problem statement, objectives, and population.
   
2. **Phase 2: Appraise Evidence** — PubMed/MESH query integration with evidence table, PMID, abstract, and GRADE quality assessment. PICO framework support.
   
3. **Phase 3: Build Decision Tree** — Node-based pathway (decision, action, outcome nodes) with Graphviz rendering and AI-powered regeneration with user refinement.
   
4. **Phase 4: Design Interface** — Nielsen's 10 Usability Heuristics analysis with AI recommendations and visual preview of improvements.
   
5. **Phase 5: Operationalize** — Expert Panel Form, Beta Testing Form, Interactive Education (quizzes + certificates), Executive Summary. All standalone HTML/DOCX.

**Key Features:** Gemini API integration, admin mode (?admin=CODE), feedback system, CSV/DOCX/HTML/PNG/SVG exports, responsive pink/brown/teal design.

**Your Capabilities:** Explain phases/features, guide workflow, troubleshoot (API, models, exports), clarify inputs/outputs, explain Phase 5 deliverables.

**Response Style:** Concise 2-4 sentences, reference specific phases/features, conversational expert tone.

**User Question:** {user_question}"""

    response = get_gemini_response(scope_constraint)
    if not response:
        response = get_local_faq_answer(user_question)
    return response or "I'm not sure how to help with that. Please ask me about features in the CarePathIQ app!"


def get_local_faq_answer(user_question: str) -> str:
    """Provide lightweight built-in answers when AI is unavailable."""
    q = (user_question or "").strip().lower()
    if "5 phases" in q or "five phases" in q or "phases" in q:
        return (
            "CarePathIQ has 5 phases: 1) **Define Scope** — clarify condition, context, and goals. "
            "2) **Appraise Evidence** — gather and grade studies with structured PICO/MESH support. "
            "3) **Build Decision Tree** — design pathway logic and branches. "
            "4) **Design Interface** — preview and optimize using Nielsen's usability heuristics. "
            "5) **Operationalize** — export expert forms, beta testing, education modules, and executive summary."
        )
    if "decision tree" in q or "phase 3" in q or "nodes" in q or "pathway" in q:
        return (
            "In Phase 3, add nodes (decisions, actions, outcomes), connect them to form branches, "
            "and iterate using evidence and heuristics. Use the refinement box to request changes, "
            "then regenerate to update the pathway structure. The AI uses Phase 1 & 2 context to build logical flows."
        )
    if "evidence" in q or "phase 2" in q or "pubmed" in q or "mesh" in q:
        return (
            "Phase 2 enables PubMed searches with MESH term suggestions. Include study PMID, title, abstract, "
            "GRADE quality assessment, and relevance notes. Structured PICO framework helps organize evidence systematically. "
            "Export to CSV for documentation."
        )
    if "phase 5" in q or "operationalize" in q or "export" in q or "expert" in q or "beta" in q:
        return (
            "Phase 5 generates 4 deliverables: Expert Panel Feedback Form (HTML), Beta Testing Form (HTML), "
            "Interactive Education Module (HTML with quizzes & certificates), and Executive Summary (Word doc). "
            "All are standalone files with no backend—users download, share, and collect responses via CSV."
        )
    if "heuristics" in q or "phase 4" in q or "usability" in q or "nielsen" in q:
        return (
            "Phase 4 applies Nielsen's 10 Usability Heuristics to your pathway. The AI analyzes each heuristic "
            "(visibility, error prevention, consistency, etc.) and suggests improvements. You can apply or reject "
            "each recommendation to optimize the user experience."
        )
    if "api" in q or "key" in q or "gemini" in q or "model" in q:
        return (
            "CarePathIQ uses Google Gemini API (get free key at https://aistudio.google.com/app/apikey). "
            "Supports gemini-2.5-flash, gemini-2.5-flash-lite, and gemini-3-flash models. Enter your API key "
            "in the sidebar to activate all AI features."
        )
    if "files" in q or "structure" in q or "code" in q:
        return (
            "Main files: streamlit_app.py (4200+ lines, 5-phase workflow), phase5_helpers.py (HTML generators), "
            "education_template.py (quiz system). Documentation: PHASE5_GUIDE.md, API_ALIGNMENT.md, README.md. "
            "Uses Streamlit, google-genai, Graphviz, python-docx."
        )
    return (
        "I can help with: the 5 phases workflow, building decision trees, evidence appraisal, "
        "usability heuristics, Phase 5 exports, API setup, or technical structure. What would you like to know?"
    )


def render_satisfaction_survey():
    """Render satisfaction survey with rating slider and feedback textarea."""
    with st.expander("📋 Feedback & Satisfaction Survey", expanded=False):
        st.markdown("### How satisfied are you with this app?")
        
        rating = st.slider(
            "Rating (10=Very Satisfied, 0=Not Satisfied)",
            min_value=0,
            max_value=10,
            value=5,
            step=1
        )
        
        feedback_text = st.text_area(
            "Additional feedback (optional)",
            placeholder="Tell us what you think...",
            height=100
        )
        
        if st.button("Submit Feedback"):
            phase = "Phase 3"
            save_feedback_response(rating, feedback_text, phase)
            st.success("✅ Thank you for your feedback!")


def load_admin_feedback_dashboard():
    """Admin-only dashboard to view and export feedback responses."""
    if not is_admin():
        return
    
    with st.expander("🔧 Admin: Feedback Dashboard", expanded=False):
        feedback_dir = "data/feedback"
        
        if not os.path.exists(feedback_dir):
            st.info("No feedback collected yet.")
            return
        
        feedback_files = [f for f in os.listdir(feedback_dir) if f.endswith(".json")]
        
        if not feedback_files:
            st.info("No feedback collected yet.")
            return
        
        st.markdown(f"**Total Responses:** {len(feedback_files)}")
        
        all_ratings = []
        for filename in feedback_files:
            try:
                with open(os.path.join(feedback_dir, filename)) as f:
                    data = json.load(f)
                    all_ratings.append(data.get("rating", 0))
            except Exception:
                continue
        
        if all_ratings:
            avg_rating = sum(all_ratings) / len(all_ratings)
            st.metric("Average Rating", f"{avg_rating:.1f}/10")
        
        st.markdown("### Feedback Responses")
        
        selected_file = st.selectbox(
            "View feedback:",
            feedback_files,
            format_func=lambda x: x.replace("feedback_", "").replace(".json", "")
        )
        
        if selected_file:
            try:
                with open(os.path.join(feedback_dir, selected_file)) as f:
                    feedback = json.load(f)
                    st.json(feedback)
            except Exception as e:
                st.error(f"Error loading feedback: {e}")
        
        if st.button("Export All Feedback as CSV"):
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "rating", "feedback", "phase", "pathway_condition"])
            
            for filename in feedback_files:
                try:
                    with open(os.path.join(feedback_dir, filename)) as f:
                        data = json.load(f)
                        writer.writerow([
                            data.get("timestamp", ""),
                            data.get("rating", ""),
                            data.get("feedback_text", ""),
                            data.get("phase", ""),
                            data.get("pathway_condition", "")
                        ])
                except Exception:
                    continue
            
            csv_data = output.getvalue()
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="feedback_export.csv",
                mime="text/csv"
            )

# ==========================================
# 3B. SIDEBAR & SESSION INITIALIZATION
# ==========================================
with st.sidebar:
    try:
        if "CarePathIQ_Logo.png" in os.listdir():
            with open("CarePathIQ_Logo.png", "rb") as f:
                logo_data = base64.b64encode(f.read()).decode()
            st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><a href="https://carepathiq.org/" target="_blank"><img src="data:image/png;base64,{logo_data}" width="200" style="max-width: 100%;"></a></div>""", unsafe_allow_html=True)
    except Exception: pass

    st.divider()
    
    # API Key and Model - at top for easy access
    # Do not prefill from secrets so landing shows on first load
    gemini_api_key = st.text_input("Gemini API Key", value="", type="password", key="gemini_key")
    
    # Dynamically fetch available models from API
    available_models = []
    if gemini_api_key:
        available_models = get_available_models(gemini_api_key)
    
    model_options = ["Auto"] + (available_models if available_models else ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash"])
    model_choice = st.selectbox("Model", model_options, index=0)
    
    st.divider()
    
    # Chat expander - plain text, no icon
    initialize_chat_state()
    with st.expander("Question about CarePathIQ?", expanded=False):
        # Initialize welcome message if this is the first load
        if not st.session_state.get("chat_initialized", False):
            st.session_state["chat_messages"] = [
                {
                    "role": "assistant",
                    "content": "Hi! Ask me anything about using CarePathIQ — the 5 phases, building pathways, using evidence, designing interfaces, or deploying your pathway."
                }
            ]
            st.session_state["chat_initialized"] = True
        
        # Display chat messages
        for message in st.session_state.get("chat_messages", []):
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Show suggested questions buttons (only if chat just started)
        if len(st.session_state.get("chat_messages", [])) <= 1:
            st.markdown("---")
            suggested_questions = [
                "What are the 5 phases?",
                "How do I add evidence in Phase 2?",
                "How do I create a decision tree in Phase 3?",
            ]
            
            for i, question in enumerate(suggested_questions):
                if st.button(question, key=f"suggested_q_{i}"):
                    # Append suggested question as user message
                    st.session_state["chat_messages"].append({
                        "role": "user",
                        "content": question
                    })
                    # Generate response
                    response = get_carepathiq_scoped_response(question)
                    st.session_state["chat_messages"].append({
                        "role": "assistant",
                        "content": response
                    })
                    st.rerun()
        
        st.markdown("---")
        
        # Chat input for user questions
        if user_input := st.chat_input("Ask about CarePathIQ..."):
            st.session_state["chat_messages"].append({
                "role": "user",
                "content": user_input
            })
            
            # Generate scoped response
            response = get_carepathiq_scoped_response(user_input)
            st.session_state["chat_messages"].append({
                "role": "assistant",
                "content": response
            })
            
            st.rerun()
    
    # Help us improve - plain text, no icon
    with st.expander("Help us improve!", expanded=False):
        st.markdown("How satisfied are you with this app?")
        
        rating = st.slider(
            "Rating",
            min_value=0,
            max_value=10,
            value=5,
            step=1,
            help="0=Not Satisfied, 10=Very Satisfied",
            key="sidebar_feedback_rating"
        )
        
        feedback_text = st.text_area(
            "Additional feedback (optional)",
            placeholder="Tell us what you think...",
            height=80,
            key="sidebar_feedback_text"
        )
        
        if st.button("Submit Feedback", key="sidebar_submit_feedback"):
            if rating or feedback_text.strip():
                save_feedback_response(rating, feedback_text, "sidebar")
                st.success("✅ Thank you for your feedback!")
            else:
                st.info("Please provide a rating or feedback")
    
    load_admin_feedback_dashboard()

    if gemini_api_key:
        try:
            st.session_state["genai_client"] = genai.Client(api_key=gemini_api_key)
            should_validate = st.session_state.get("last_tested_key") != gemini_api_key
            if should_validate:
                st.session_state["last_tested_key"] = gemini_api_key
                ok = validate_ai_connection()
                if ok:
                    st.success("AI Connected")
                    st.session_state["ai_valid"] = True
                    st.session_state.pop("ai_error", None)
                else:
                    # Show concise message only
                    err = st.session_state.get("ai_error")
                    short_msg = err or "API key invalid or model unavailable."
                    st.error(short_msg)
                    st.session_state["ai_valid"] = False
            else:
                # Preserve prior validation result
                if st.session_state.get("ai_valid"):
                    st.success("AI Connected")
                else:
                    st.info("Key entered — awaiting first AI call")
        except Exception as e:
            st.error(f"Failed to initialize Gemini client: {str(e)[:120]}")
            st.stop()

# LANDING PAGE LOGIC — SHOW WELCOME INSTEAD OF BLANK STOP
if not gemini_api_key:
    st.markdown(
        "<h2 style='color:#5D4037;font-style:italic;'>Intelligently Build & Deploy Care Pathways</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="
            background-color: #FFB0C9;
            border-left: 5px solid #5D4037;
            padding: 16px;
            border-radius: 6px;
            color: #3E2723;
            margin-bottom: 20px;">
            <strong>Welcome!</strong> Enter your <strong>Gemini API token</strong> on the left to activate the AI Agent. If you don't have one, you can get one for free <a href="https://aistudio.google.com/app/apikey" target="_blank"><strong>here</strong></a>.
        </div>
        """,
        unsafe_allow_html=True,
    )

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

# ==========================================
# 4. MAIN WORKFLOW LOGIC
# ==========================================
# Display tagline at top (always visible when logged in)
st.markdown(
    "<h2 style='color:#5D4037;font-style:italic;'>Intelligently Build & Deploy Care Pathways</h2>",
    unsafe_allow_html=True,
)

## --- PHASE NAVIGATION ---

# Calculate progress for visual indicator
try:
    progress_value = calculate_granular_progress()
    progress_pct = int(progress_value * 100)
except:
    progress_value = 0.0
    progress_pct = 0

# Display progress bar
st.markdown(
    f"""
    <div class="phase-nav-container">
        <div class="phase-nav-label">Pathway Development Progress: {progress_pct}% Complete</div>
        <div class="phase-progress-bar">
            <div class="phase-progress-fill" style="width: {progress_pct}%;"></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Create horizontal navigation with phase numbers
phase = st.session_state.get("current_phase_label", PHASES[0])
current_phase_index = PHASES.index(phase) if phase in PHASES else 0

# Calculate completion status for each phase
data = st.session_state.get('data', {})
phase_completion = []

# Phase 1: Check if main fields are filled
p1 = data.get('phase1', {})
p1_complete = bool(p1.get('condition') and p1.get('setting') and p1.get('inclusion') and p1.get('exclusion'))
phase_completion.append(p1_complete)

# Phase 2: Check if evidence is collected
p2 = data.get('phase2', {})
p2_complete = bool(p2.get('evidence') and len(p2.get('evidence', [])) > 0)
phase_completion.append(p2_complete)

# Phase 3: Check if nodes exist
p3 = data.get('phase3', {})
p3_complete = bool(p3.get('nodes') and len(p3.get('nodes', [])) > 0)
phase_completion.append(p3_complete)

# Phase 4: Check if heuristics analyzed
p4 = data.get('phase4', {})
p4_complete = bool(p4.get('heuristics_data'))
phase_completion.append(p4_complete)

# Phase 5: Check if any deliverable generated
p5 = data.get('phase5', {})
p5_complete = bool(p5.get('beta_html') or p5.get('expert_html') or p5.get('edu_html'))
phase_completion.append(p5_complete)

# Compact navigation with numbered phases and status indicators
st.caption("**Phase**")

# Use ultra-short labels for navigation buttons
phase_short_labels = [
    "Scope",
    "Evidence",
    "Logic",
    "Design",
    "Deploy"
]

# Sidebar quick navigation mirroring the short labels
with st.sidebar:
    st.markdown("### Quick Navigation")
    for i, p in enumerate(PHASES):
        is_active = (i == current_phase_index)
        short_label = phase_short_labels[i]
        button_label = f"{i + 1}. {short_label}"
        button_type = "primary" if is_active else "secondary"
        if st.button(button_label, key=f"side_nav_{p.replace(' ', '_').replace('&', 'and')}", type=button_type):
            st.session_state.current_phase_label = p
            st.rerun()

# Create columns with arrows between buttons for forward flow visualization
# Pattern: [button] → [button] → [button] → [button] → [button]
num_buttons = len(PHASES)
num_arrows = num_buttons - 1
# Create columns: button, arrow, button, arrow, ..., button
col_specs = []
for i in range(num_buttons):
    col_specs.append(3)  # Button column (wider)
    if i < num_arrows:
        col_specs.append(0.5)  # Arrow column (narrow)

nav_cols = st.columns(col_specs)

col_idx = 0
for i, p in enumerate(PHASES):
    is_active = (i == current_phase_index)
    is_complete = phase_completion[i] if i < len(phase_completion) else False
    button_type = "primary" if is_active else "secondary"
    
    # Create button label with phase number using shorter label
    phase_num = i + 1
    short_label = phase_short_labels[i]
    button_label = f"{phase_num}. {short_label}"
    
    with nav_cols[col_idx]:
        if st.button(button_label, key=f"nav_{p.replace(' ', '_').replace('&', 'and')}", type=button_type, use_container_width=True):
            st.session_state.current_phase_label = p
            st.rerun()
    
    col_idx += 1
    
    # Add arrow between buttons (except after the last button)
    if i < num_arrows:
        with nav_cols[col_idx]:
            st.markdown("<div style='text-align: center; padding-top: 4px; font-size: 20px; color: #666;'>→</div>", unsafe_allow_html=True)
        col_idx += 1

st.markdown("---")

# --- PHASE 1 ---
if "Scope" in phase:
    # 1) Draft helper
    def trigger_p1_draft():
        c = st.session_state.get('p1_cond_input', '').strip()
        s = st.session_state.get('p1_setting', '').strip()
        if not (c and s):
            return
        prompt = f"""
        Act as a Chief Medical Officer creating a clinical care pathway. For "{c}" in "{s}", return a JSON object with exactly these keys: inclusion, exclusion, problem, objectives.
        
        CRITICAL REQUIREMENTS:
        - inclusion: ONLY 3-5 brief patient characteristics that INCLUDE them in the pathway (e.g., age range, presentation type, risk factors). Concise phrases, not detailed descriptions.
        - exclusion: ONLY 3-5 brief characteristics that EXCLUDE patients (e.g., contraindications, alternative diagnoses, comorbidities). Concise phrases, not detailed descriptions.
        - problem: One brief clinical problem statement (1-2 sentences). Describe the gap or challenge, not educational content.
        - objectives: ONLY 3-4 brief clinical objectives for the pathway (e.g., "Reduce time to diagnosis", "Standardize treatment decisions"). Short statements, not detailed goals.
        
        Format each list as a simple newline-separated text, NOT as a JSON array. Do not use markdown formatting (no asterisks, dashes for bullets). Use plain text only.
        """
        with ai_activity("Generating pathway scope…"):
            data = get_gemini_response(prompt, json_mode=True)
        if data and isinstance(data, dict):
            st.session_state.data['phase1']['inclusion'] = format_as_numbered_list(data.get('inclusion', ''))
            st.session_state.data['phase1']['exclusion'] = format_as_numbered_list(data.get('exclusion', ''))
            st.session_state.data['phase1']['problem'] = str(data.get('problem', ''))
            st.session_state.data['phase1']['objectives'] = format_as_numbered_list(data.get('objectives', ''))

    # 2) Sync helpers
    def sync_p1_widgets():
        st.session_state.data['phase1']['condition'] = st.session_state.get('p1_cond_input', '')
        st.session_state.data['phase1']['setting'] = st.session_state.get('p1_setting', '')
        st.session_state.data['phase1']['inclusion'] = st.session_state.get('p1_inc', '')
        st.session_state.data['phase1']['exclusion'] = st.session_state.get('p1_exc', '')
        st.session_state.data['phase1']['problem'] = st.session_state.get('p1_prob', '')
        st.session_state.data['phase1']['objectives'] = st.session_state.get('p1_obj', '')

    def sync_and_draft():
        # First sync widget values to session state; Streamlit will rerun
        # automatically after this callback. On the next run, we perform the
        # AI draft, keeping the callback snappy and avoiding rerun warnings.
        sync_p1_widgets()
        st.session_state['p1_should_draft'] = True

    # 3) Seed widget values
    p1 = st.session_state.data['phase1']
    st.session_state.setdefault('p1_cond_input', p1.get('condition', ''))
    st.session_state.setdefault('p1_setting',    p1.get('setting', ''))
    st.session_state.setdefault('p1_inc',        p1.get('inclusion', ''))
    st.session_state.setdefault('p1_exc',        p1.get('exclusion', ''))
    st.session_state.setdefault('p1_prob',       p1.get('problem', ''))
    st.session_state.setdefault('p1_obj',        p1.get('objectives', ''))

    # If a widget change requested an auto-draft, run it now on the main pass
    # (after the immediate UI refresh) and then clear the flag.
    if st.session_state.get('p1_should_draft'):
        st.session_state['p1_should_draft'] = False
        trigger_p1_draft()
        # Copy AI-generated values to widget keys so they display immediately
        p1 = st.session_state.data['phase1']
        st.session_state['p1_inc'] = p1.get('inclusion', '')
        st.session_state['p1_exc'] = p1.get('exclusion', '')
        st.session_state['p1_prob'] = p1.get('problem', '')
        st.session_state['p1_obj'] = p1.get('objectives', '')
        st.rerun()

    # 4) UI: Inputs
    st.header(f"Phase 1. {PHASES[0]}")
    styled_info("<b>Tip:</b> Enter Clinical Condition and Care Setting; the agent generates the rest automatically.")

    col1, col2 = columns_top(2)
    with col1:
        st.subheader("1. Clinical Focus")
        st.text_input("Clinical Condition", placeholder="e.g., Chest Pain", key="p1_cond_input", on_change=sync_p1_widgets)
        st.text_input("Care Setting", placeholder="e.g., Emergency Department", key="p1_setting", on_change=sync_and_draft)

        st.subheader("2. Target Population")
        st.text_area("Inclusion Criteria", key="p1_inc", height=compute_textarea_height(st.session_state.get('p1_inc',''), 14), on_change=sync_p1_widgets)
        st.text_area("Exclusion Criteria", key="p1_exc", height=compute_textarea_height(st.session_state.get('p1_exc',''), 14), on_change=sync_p1_widgets)

    with col2:
        st.subheader("3. Clinical Gap / Problem Statement")
        st.text_area("Problem Statement / Clinical Gap", key="p1_prob", height=compute_textarea_height(st.session_state.get('p1_prob',''), 12), on_change=sync_p1_widgets, label_visibility="collapsed")

        st.subheader("4. Goals")
        st.text_area("Project Goals", key="p1_obj", height=compute_textarea_height(st.session_state.get('p1_obj',''), 14), on_change=sync_p1_widgets, label_visibility="collapsed")

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
            # Define consistent color scheme for all owners
            owner_colors = {
                'PM': '#5f9ea0',           # Cadet blue
                'Clinical Lead': '#4169e1',  # Royal blue
                'Expert Panel': '#b0c4de',   # Light steel blue
                'IT': '#dc143c',             # Crimson
                'Ops': '#ffb6c1',            # Light pink
                'Quality': '#5D4037'         # Brown (consistent with brand)
            }
            
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Start', title='Date'),
                x2='End',
                y=alt.Y('Stage', sort=None),
                color=alt.Color('Owner', 
                    scale=alt.Scale(
                        domain=list(owner_colors.keys()),
                        range=list(owner_colors.values())
                    ),
                    legend=alt.Legend(title='Owner')
                ),
                tooltip=['Stage', 'Start', 'End', 'Owner']
            ).properties(height=300).interactive()
            st.altair_chart(chart, width="stretch")
    else:
        st.info("Add timeline entries to see the Gantt chart.")

    st.divider()
    
    # Download Project Charter - generates on-the-fly when clicked
    sync_p1_widgets()
    d = st.session_state.data['phase1']
    
    if d.get('condition') and d.get('problem'):
        if st.button("Download Project Charter (.docx)", type="secondary"):
            with st.status("Generating Project Charter...", expanded=True) as status:
                st.write("Building project charter based on IHI Quality Improvement framework...")
                p_ihi = f"""You are a Quality Improvement Advisor using IHI's Model for Improvement.

Build a project charter for managing "{d['condition']}" in "{d.get('setting', '') or 'care setting'}".

**Phase 1 Context:**
Problem: {d['problem']}
Inclusion: {d['inclusion']}
Exclusion: {d['exclusion']}
Objectives: {d.get('objectives', '')}

**Required JSON Output** (clean, no nested objects, all values as strings or string arrays):
Return ONLY a JSON object with these exact keys:
- problem: narrative (string, 1–2 paragraphs, use Phase 1 problem statement)
- project_description: scope statement (string, 1 paragraph: 1 sentence scope + 1 sentence approach)
- rationale: evidence basis (string, 1 paragraph, use Phase 1 context)
- expected_outcomes: list of strings (5–8 outcomes, one string per item)
- aim_statement: SMART goal (string, 1 line)
- outcome_measures: list of strings (safety/efficiency metrics, 4–6 items)
- process_measures: list of strings (protocol adherence, 4–6 items)
- balancing_measures: list of strings (staff impact, 3–4 items)
- initial_activities: narrative (string, 1 paragraph)
- change_ideas: list of strings (4–6 PDSA-ready interventions)
- stakeholders: comma-separated string
- barriers: list of strings (3–5 barriers)
- boundaries: object with in_scope (string) and out_of_scope (string)

Return clean JSON ONLY. No markdown, no explanation."""
                res = get_gemini_response(p_ihi, json_mode=True)
                if res:
                    st.session_state.data['phase1']['ihi_content'] = res
                    doc = create_word_docx(st.session_state.data['phase1'])
                    if doc:
                        status.update(label="Ready!", state="complete")
                        st.download_button("Download Project Charter (.docx)", doc, f"Project_Charter_{d['condition']}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    else:
                        status.update(label="Word export unavailable. Please ensure python-docx is installed.", state="error")
                else:
                    status.update(label="Failed to generate charter.", state="error")
    else:
        st.info("Complete Clinical Condition and Problem Statement to download the Project Charter.")

    # Refine & Regenerate (placed below charter so edits can be made, then re-generate)
    st.divider()
    submitted = False
    with st.expander("Refine & Regenerate", expanded=False):
        st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update all Phase 1 content and downloads")
        with st.form("p1_refine_form"):
            col_text, col_file = columns_top([2, 1])
            with col_text:
                st.text_area(
                    "Refinement Notes",
                    key="p1_refine_input",
                    placeholder="Clarify inclusion criteria; tighten scope; align objectives",
                    height=90,
                    help="Describe what to change. After applying, click Generate Project Charter above again."
                )

            with col_file:
                st.caption("Supporting Documents (optional)")
                p1_uploaded = st.file_uploader(
                    "Drag & drop or browse",
                    key="p1_file_upload",
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    help="Attach PDFs/DOCX files; the agent auto-summarizes them for context."
                )
                if p1_uploaded:
                    for uploaded_file in p1_uploaded:
                        file_result = upload_and_review_file(uploaded_file, f"p1_refine_{uploaded_file.name}", "clinical scope and charter")
                        if file_result:
                            with st.expander(f"Review: {file_result['filename']}", expanded=False):
                                st.markdown(file_result["review"])

            col1, col2 = st.columns([3, 1])
            with col2:
                submitted = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)

    if submitted:
        refinement_text = st.session_state.get('p1_refine_input', '').strip()
        if refinement_text:
            # Collect all uploaded document reviews
            doc_reviews = []
            for key in st.session_state.keys():
                if key.startswith("file_p1_refine_") and key != "file_p1_refine":
                    doc_reviews.append(st.session_state.get(key, ''))
            
            if doc_reviews:
                refinement_text += f"\n\nSupporting Documents:\n" + "\n\n".join(doc_reviews)
            
            current = st.session_state.data['phase1']
            prompt = f"""
            Update the following sections based on this user feedback: "{refinement_text}"
            Current Data JSON: {json.dumps({k: current[k] for k in ['inclusion','exclusion','problem','objectives']})}
            Return JSON with keys inclusion, exclusion, problem, objectives (use numbered lists where applicable).
            Do not use markdown formatting (no asterisks for bold). Use plain text only.
            """
            with ai_activity("Applying refinements and auto-generating charter…"):
                data = get_gemini_response(prompt, json_mode=True)
            if data and isinstance(data, dict):
                st.session_state.data['phase1']['inclusion'] = format_as_numbered_list(data.get('inclusion', ''))
                st.session_state.data['phase1']['exclusion'] = format_as_numbered_list(data.get('exclusion', ''))
                st.session_state.data['phase1']['problem'] = str(data.get('problem', ''))
                st.session_state.data['phase1']['objectives'] = format_as_numbered_list(data.get('objectives', ''))
                # Auto-generate charter
                generate_p1_charter()
                st.success("Refinements applied and Project Charter auto-generated!")
            else:
                st.error("Failed to apply refinements. Please try again.")
    render_bottom_navigation()
    st.stop()

# --- PHASE 2 ---
elif "Evidence" in phase or "Appraise" in phase:
    st.header(f"Phase 2. {PHASES[1]}")

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
                    "Return ONLY valid JSON object where keys are PMID strings and values are objects with 'grade' and 'rationale' fields. "
                    "Example: {\"12345678\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}"
                )
                grades = get_gemini_response(prompt, json_mode=True)
                if grades and isinstance(grades, dict):
                    for e in st.session_state.data['phase2']['evidence']:
                        pmid_str = str(e['id'])
                        if pmid_str in grades:
                            grade_data = grades[pmid_str]
                            e['grade'] = grade_data.get('grade', 'Un-graded') if isinstance(grade_data, dict) else 'Un-graded'
                            e['rationale'] = grade_data.get('rationale', 'Not provided.') if isinstance(grade_data, dict) else 'Not provided.'
        st.session_state['p2_last_autorun_query'] = st.session_state.data['phase2']['mesh_query']

    # Summary banner for newly enriched evidence from Phase 3
    try:
        ev_list = st.session_state.data.get('phase2', {}).get('evidence', [])
        new_count = sum(1 for e in ev_list if bool(e.get('is_new')) or e.get('source') == 'enriched_from_phase3')
    except Exception:
        new_count = 0
    if new_count > 0:
        styled_info(f"<b>New evidence added from Phase 3:</b> {new_count} item(s) auto‑graded and added below. Use 'Show only new evidence' to focus review.")

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
            # Use secondary to render in app's brown style
            if st.button("Regenerate Evidence Table", type="secondary", key="p2_search_run"):
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
                                "Return ONLY valid JSON object where keys are PMID strings and values are objects with 'grade' and 'rationale' fields. "
                                "Example: {\"12345678\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}"
                            )
                            grades = get_gemini_response(prompt, json_mode=True)
                            if grades and isinstance(grades, dict):
                                for e in st.session_state.data['phase2']['evidence']:
                                    pmid_str = str(e['id'])
                                    if pmid_str in grades:
                                        grade_data = grades[pmid_str]
                                        e['grade'] = grade_data.get('grade', 'Un-graded') if isinstance(grade_data, dict) else 'Un-graded'
                                        e['rationale'] = grade_data.get('rationale', 'Not provided.') if isinstance(grade_data, dict) else 'Not provided.'
                        # Ensure defaults if AI response missing
                        for e in st.session_state.data['phase2']['evidence']:
                            e.setdefault('grade', 'Un-graded')
                            e.setdefault('rationale', 'Not yet evaluated.')
                    st.session_state['p2_last_autorun_query'] = search_term
                    st.rerun()
        with col_open:
            # Show PubMed link using the best-available query (user input, current saved, or default)
            effective_q = q_clean or current_q_full or default_q or ""
            if effective_q:
                full_q = ensure_time_filter(effective_q)
                st.link_button(
                    "Open in PubMed ↗",
                    f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(full_q)}",
                    type="secondary",
                )
            else:
                st.link_button("Open in PubMed ↗", "https://pubmed.ncbi.nlm.nih.gov", disabled=True, type="secondary")

    if st.session_state.data['phase2']['evidence']:
        grade_help = (
            "GRADE Criteria\n"
            "- High (A): Further research is very unlikely to change our confidence in the estimate of effect.\n"
            "- Moderate (B): Further research is likely to have an important impact on our confidence in the estimate of effect and may change the estimate.\n"
            "- Low (C): Further research is very likely to have an important impact on our confidence in the estimate of effect and is likely to change the estimate.\n"
            "- Very Low (D): We are very uncertain about the estimate."
        )

        # Use native Streamlit subheader with help parameter for consistent alignment
        st.subheader("Filter by GRADE", help=grade_help)

        # Default filters set to show all grades initially + 'new only' toggle
        col_g1, col_g2 = st.columns([3, 2])
        with col_g1:
            selected_grades = st.multiselect(
                "",
                ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
                default=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
                key="grade_filter_multiselect"
            )
        with col_g2:
            st.checkbox("Show only new evidence", value=False, key="p2_show_new_only")
        
        # Sort Logic: High to Low
        grade_order = {"High (A)": 0, "Moderate (B)": 1, "Low (C)": 2, "Very Low (D)": 3, "Un-graded": 4}
        
        evidence_data = st.session_state.data['phase2']['evidence']
        # Apply Sorting
        evidence_data.sort(key=lambda x: grade_order.get(x.get('grade', 'Un-graded'), 4))
        
        # Filter for Display
        display_data = [e for e in evidence_data if e.get('grade', 'Un-graded') in selected_grades]
        if st.session_state.get('p2_show_new_only'):
            display_data = [e for e in display_data if bool(e.get('is_new')) or e.get('source') == 'enriched_from_phase3']
        df_ev = pd.DataFrame(display_data)
        
        if not df_ev.empty:
            # Ensure all required columns exist in DataFrame
            required_cols = ["id", "title", "grade", "rationale", "url", "authors", "abstract", "year", "journal", "source"]
            for col in required_cols:
                if col not in df_ev.columns:
                    df_ev[col] = ""
            
            # Add visual indicator for newly auto-added entries without emojis or Phase mentions
            df_ev["source"] = df_ev.get("source", "").fillna("")
            # Prefer explicit boolean column for styling & export persistence
            if "is_new" not in df_ev.columns:
                df_ev["is_new"] = df_ev["source"].apply(lambda x: True if x == "enriched_from_phase3" else False)
            else:
                df_ev["is_new"] = df_ev["is_new"].fillna(False)
            # Insert a visible, disabled checkbox for "New" highlighting
            df_ev.insert(0, "new", df_ev["is_new"].astype(bool))

            # Neutral tip without Phase 3 reference
            styled_info("<b>Tip:</b> New evidence is marked with a checked box in the first table column. Review the auto-generated GRADE and rationale. Hover over the top right of the table for more options including CSV download.")

            edited_ev = st.data_editor(
                df_ev[["new", "id", "title", "grade", "rationale", "url"]], 
                column_config={
                    "new": st.column_config.CheckboxColumn("New", disabled=True, help="Auto-added and auto-graded from Phase 3."),
                    "id": st.column_config.TextColumn("PMID", disabled=True, width="small"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], width="small"),
                    "rationale": st.column_config.TextColumn("GRADE Rationale", width="large"),
                    "url": st.column_config.LinkColumn("URL", width="small"),
                }, 
                hide_index=True, width="stretch", key="ev_editor"
            )

            # Persist edits back to session so downloads reflect the latest table
            try:
                edited_records = edited_ev.to_dict("records")
                by_id = {str(r.get("id", "")): r for r in edited_records}
                for e in st.session_state.data['phase2']['evidence']:
                    eid = str(e.get('id', ''))
                    if eid in by_id:
                        row = by_id[eid]
                        e["title"] = row.get("title", e.get("title", ""))
                        e["grade"] = row.get("grade", e.get("grade", "Un-graded"))
                        e["rationale"] = row.get("rationale", e.get("rationale", "Not yet evaluated."))
                        # carry forward markers for styling/exports
                        e["is_new"] = bool(row.get("new", e.get("is_new", False)))
                        if e.get("is_new"):
                            e["source"] = e.get("source", "auto_enriched")
            except Exception:
                pass
            
            # EXPORT OPTIONS SECTION
            st.divider()

            full_df = pd.DataFrame(evidence_data)
            c1, c2 = st.columns([1, 1])

            show_table = True
            show_citations = True

            with c1:
                if show_table:
                    st.subheader("Detailed Evidence Table", help="Includes journal, year, authors, and abstract for all results.")
                    full_export_df = full_df[["id", "title", "grade", "rationale", "url", "journal", "year", "authors", "abstract"]].copy()
                    full_export_df.columns = ["PMID", "Title", "GRADE", "GRADE Rationale", "URL", "Journal", "Year", "Authors", "Abstract"]
                    csv_data_full = full_export_df.to_csv(index=False).encode('utf-8')
                    # Centered download button beneath the section
                    dl_l, dl_c, dl_r = st.columns([1,2,1])
                    with dl_c:
                        st.download_button("Download (.csv)", csv_data_full, file_name="evidence_table.csv", mime="text/csv")

            with c2:
                if show_citations:
                    st.subheader("Formatted Citations", help="Generate Word citations in your preferred style. Pick a preset or type your own below.")
                    style_col, custom_col = columns_top([1, 2])
                    with style_col:
                        citation_style = st.selectbox(
                            "Citation style",
                            ["APA", "MLA", "Vancouver"],
                            key="p2_citation_style"
                        )
                        st.caption("Pick a preset or type your own below.")
                    with custom_col:
                        custom_style = st.text_input(
                            "Or enter custom style name",
                            value="",
                            placeholder="Harvard, Chicago",
                            max_chars=30,
                            key="p2_custom_citation_style"
                        )
                        st.caption("Leave blank to use the preset above.")

                    # Use custom style if provided, otherwise use selected preset
                    final_citation_style = custom_style if custom_style.strip() else citation_style
                    references_source = display_data if display_data else evidence_data
                    citations = references_source or []
                    lines = [format_citation_line(entry, final_citation_style) for entry in citations]
                    docx_bytes = create_references_docx(citations, style=final_citation_style)

                    no_citations = len(citations) == 0
                    dl2_l, dl2_c, dl2_r = st.columns([1,2,1])
                    with dl2_c:
                        if docx_bytes:
                            st.download_button(
                                "Download (.docx)",
                                docx_bytes,
                                file_name="citations.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                disabled=no_citations
                            )
                        else:
                            st.info("Word export unavailable (python-docx not installed)")
                        if no_citations:
                            st.info("Add evidence to enable download.")

    else:
        # If nothing to show, provide a helpful prompt
        styled_info("No results yet. Refine the search or ensure Phase 1 has a condition and setting.")
    render_bottom_navigation()
    st.stop()

# --- PHASE 3 ---
elif "Decision" in phase or "Tree" in phase:
    st.header(f"Phase 3. {PHASES[2]}")
    styled_info("<b>Tip:</b> The AI agent generated an evidence-based decision tree. You can manually update text, add/remove nodes, or refine using natural language below.")
    
    st.divider()
    
    # Reset enrichment flag each time Phase 3 is loaded (allows re-enrichment if new PMIDs added)
    # This is a safety mechanism to detect changes from previous session
    if 'p3_last_nodes_state' not in st.session_state:
        st.session_state['p3_last_nodes_state'] = None
    
    current_nodes_state = str(st.session_state.data.get('phase3', {}).get('nodes', []))
    if current_nodes_state != st.session_state['p3_last_nodes_state']:
        # Nodes have changed (new entry or edit); reset enrichment to allow re-detection
        st.session_state['p3_enrichment_performed'] = False
        st.session_state['p3_last_nodes_state'] = current_nodes_state
    
    # Auto-generate table on first entry to Phase 3
    cond = st.session_state.data['phase1']['condition']
    setting = st.session_state.data['phase1']['setting'] or "care setting"
    evidence_list = st.session_state.data['phase2']['evidence']
    
    if not st.session_state.data['phase3']['nodes'] and cond:
        ev_context = "\n".join([f"- PMID {e['id']}: {e['title']} | Abstract: {e.get('abstract', 'N/A')[:200]}" for e in evidence_list[:20]])
        prompt = f"""
        Act as a CLINICAL DECISION SCIENTIST with expertise in Medical Decision Analysis and evidence-based medicine.
        
        TASK: Build a SOPHISTICATED, COMPREHENSIVE decision-science pathway for managing {cond} in {setting}.
        
        FOUNDATIONAL FRAMEWORK (MANDATORY - Preserve All Principles):
        - CGT/Ad/it principles: Explicit decision structure, separate content from form
        - Users' Guide to Medical Decision Analysis (Dobler et al., Mayo Clin Proc 2021):
          * Make decision/chance/terminal flows EXPLICIT through DAG structure
          * Trade off BENEFITS vs HARMS at every decision point with evidence-backed rationales
          * Use evidence-based probabilities and utilities to guide branching
        - Ensure pathway reflects real clinical uncertainty and decision complexity

        Available Evidence Base:
        {ev_context}
        
        REQUIRED CLINICAL COVERAGE (4 Mandatory Stages - Each MUST Have Complexity):
        1. Initial Evaluation:
           - Chief complaint and symptom characterization
           - Vital signs assessment (with abnormality thresholds)
           - Physical examination findings and risk stratification
           - Early diagnostic workup (labs, imaging, monitoring)
        
        2. Diagnosis and Treatment:
           - Differential diagnosis decision trees (what tests rule in/out?)
           - Therapeutic interventions (medications with dose/route, procedures, supportive care)
           - Risk-benefit analysis for major therapeutic choices
           - Edge cases and special populations (pregnant, elderly, immunocompromised, etc.)
        
        3. Re-evaluation:
           - Monitoring criteria and frequency (vital signs, labs, imaging follow-ups)
           - Response to treatment assessment (improving vs. unchanged vs. deteriorating)
           - Escalation triggers and de-escalation pathways
           - When to repeat diagnostic testing or change therapy
        
        4. Final Disposition:
           - Specific discharge instructions (medications with dose/route/duration, activity restrictions, dietary changes)
           - Outpatient follow-up (which specialist, timing, what triggers urgent return)
           - Admit/observation criteria with clear thresholds
           - Transfer to higher level of care (ICU, specialty unit) triggers
        
        OUTPUT FORMAT: JSON array of nodes with THESE EXACT FIELDS:
        - "type": "Start" | "Decision" | "Process" | "End" (no other types)
        - "label": Concise, specific clinical step using medical abbreviations (e.g., "ECG, troponin x2 at 0h/3h, IV access")
        - "evidence": PMID citation OR "N/A"
        - "detail": (optional) Extended description of rationale or threshold (e.g., "escalate if SBP <90 or altered mental status")
        
        CRITICAL CONSTRAINTS (PRESERVE DECISION SCIENCE INTEGRITY):
        
        1. DECISION DIVERGENCE - Every Decision creates DISTINCT branches:
           - "Is patient hemodynamically stable?" YES→Observation pathway | NO→ICU-level resuscitation
           - "Does EKG show STEMI?" YES→Cath lab pathway | NO→Serial troponin pathway
           - Branches MUST lead to different clinical sequences (never reconverge)
           - If branches must eventually converge, make it explicit with another Decision point
        
        2. TERMINAL END NODES - Each pathway branch ends ONLY with End nodes:
           - No content after an End node
           - End nodes represent final disposition: "Discharged on aspirin/metoprolol x90 days with PCP follow-up"
           - Each clinical outcome gets its own End node; DO NOT use "or" (e.g., BAD: "Admit or ICU")
           - Even similar outcomes get separate End nodes if they represent distinct pathways
        
        3. BENEFIT/HARM TRADE-OFFS (Decision-point rationales):
           - At every Decision node, annotate the label or detail with trade-off thinking:
             "Stress test vs. CT angiography? (test sensitivity vs. radiation dose vs. time to diagnosis)"
           - Include thresholds: "If troponin >99th percentile → activate cath lab (high MI risk outweighs procedural risk)"
           - Cite PMIDs when evidence supports the decision
        
        4. EVIDENCE-BACKED STEPS:
           - Every Process and Decision node should have a PMID when available (from evidence list above)
           - If multiple PMIDs support a step, use one representative citation
           - Do NOT hallucinate PMIDs—use "N/A" if no supporting evidence in list
        
        5. COMPLEXITY AND SPECIFICITY:
           - Build 20-40+ nodes (more nodes = more explicit decision logic)
           - Include edge cases: pregnancy, renal failure, drug allergies, age extremes
           - Specific medications with doses/routes, not vague "treat symptomatically"
           - Examples:
             ✓ "Order vancomycin 15-20 mg/kg q8-12h IV (adjust for renal function) + meropenem"
             ✗ "Treat with antibiotics"
           - Include monitoring intervals: "Recheck troponin q3h x 2, then daily troponin x 2 if negative"
        
        6. DAG STRUCTURE (No cycles):
           - Pathway is a directed acyclic graph (DAG)—never loop back
           - Escalation only moves forward (ICU-bound patients don't move back to ED)
           - De-escalation is explicit: "Stable x 24h→Transfer to med/surg bed from ICU"
        
        7. ACTIONABILITY AND CLINICAL REALISM:
           - Every node represents an action or decision a clinician takes in real time
           - Include realistic clinical decision points: "Vitals stable x 2h" or "Troponin rising vs. falling?"
           - Timestamps and criteria matter: "Admit if BP <90 persistently AFTER 2L fluid bolus"
        
        Rules for Node Structure:
        - First node: type "Start", label "Patient present to {setting} with {cond}"
        - Last nodes: All type "End" (no Process/Decision after End)
        - Consecutive Decision nodes are OK (do NOT force Process nodes between them)
        - Use compound labels for clarity: "Assess troponin, CXR, EKG—any abnormality?" (Decision)
        - Detail field can explain thresholds or rationale (e.g., detail: "escalate if HR>110 or RR>22")
        
        Node Count Guidance:
        - MINIMUM 15 nodes (simple pathway structure)
        - TYPICAL 25-35 nodes (comprehensive with main branches)
        - MAXIMUM 50+ nodes (complex with edge cases, special populations, escalation/de-escalation)
        - Aim for depth over breadth: prefer explicit decision trees over oversimplification
        
        Generate a pathway that respects real clinical complexity and decision uncertainty. This is NOT a linear checklist—it's a decision tree that branches and evolves based on patient presentation and test results.
        
        CRITICAL: Each Decision branch must lead to a unique sequence ending in its own End node. Do NOT make branches reconverge.
        """
        with ai_activity("Auto-generating decision tree from Phase 1 & 2 data..."):
            nodes = get_gemini_response(prompt, json_mode=True)
        if isinstance(nodes, list) and len(nodes) > 0:
            # Clean up common AI generation issues
            nodes = normalize_or_logic(nodes)  # Fix OR statements in End nodes
            nodes = fix_decision_flow_issues(nodes)  # Fix reconverging branches and non-terminal End nodes
            st.session_state.data['phase3']['nodes'] = nodes
            st.rerun()
        elif not isinstance(nodes, list):
            st.warning(f"❌ Could not parse decision tree. The AI returned: {type(nodes).__name__}. Please manually add nodes in the table below, or try again.")
    
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
        width="stretch",
        key="p3_editor"
    )
    # Auto-save on edit
    st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')
    
    # QUALITY ENFORCEMENT: Validate decision science integrity
    current_nodes = st.session_state.data['phase3']['nodes']
    if current_nodes and len(current_nodes) > 1:  # Skip validation for empty/minimal setup
        validation = validate_decision_science_pathway(current_nodes)
        complexity = validation['complexity']
        
        # Auto-enforce quality standards
        if complexity['complexity_level'] == 'minimal' and len(current_nodes) >= 5:
            st.error("⚠️ **Oversimplified Pathway Detected**")
            st.markdown(f"""
            This pathway has **only {len(current_nodes)} nodes**, which is insufficient for clinical decision science:
            - **Required**: 20-35+ nodes for comprehensive care pathways
            - **Missing**: {', '.join([k.replace('_', ' ').title() for k, v in complexity['clinical_stage_coverage'].items() if not v])}
            - **Evidence Coverage**: {complexity['evidence_coverage']:.0%} (target: 30%+)
            """)
            
            if st.button("🔧 Auto-Enhance Pathway", type="primary", key="p3_auto_enhance"):
                with ai_activity("Enhancing pathway to meet decision science standards..."):
                    ev_context = "\n".join([f"- PMID {e['id']}: {e['title']}" for e in evidence_list[:20]])
                    enhance_prompt = f"""
                    The current pathway for {cond} in {setting} is oversimplified ({len(current_nodes)} nodes).
                    
                    Current pathway: {json.dumps(current_nodes, indent=2)}
                    
                    Evidence: {ev_context}
                    
                    EXPAND this into a comprehensive clinical decision pathway (25-35+ nodes) that covers:
                    1. Initial Evaluation (vitals, exam, initial workup)
                    2. Diagnosis/Treatment (diagnostic tests, medications with doses, interventions)
                    3. Re-evaluation (monitoring, response assessment, escalation criteria)
                    4. Final Disposition (discharge instructions, admit criteria, transfer criteria)
                    
                    Add decision branches, edge cases, and specific clinical details. DO NOT simplify—EXPAND.
                    """
                    enhanced_nodes = get_gemini_response(enhance_prompt, json_mode=True)
                    if isinstance(enhanced_nodes, list) and len(enhanced_nodes) > len(current_nodes):
                        st.session_state.data['phase3']['nodes'] = normalize_or_logic(fix_decision_flow_issues(enhanced_nodes))
                        st.success(f"✓ Pathway enhanced: {len(current_nodes)} → {len(enhanced_nodes)} nodes")
                        st.rerun()
    
    st.divider()
    
    # Display pathway metrics with evidence enrichment
    node_count = len(st.session_state.data['phase3']['nodes'])

    # Extract all PMIDs from Phase 3 nodes
    phase3_pmids = extract_pmids_from_nodes(st.session_state.data['phase3']['nodes'])
    
    # De-duplicate Phase 2 evidence first (in case there are existing duplicates)
    seen_pmids = set()
    deduplicated_evidence = []
    for e in evidence_list:
        pmid = e.get('id')
        if pmid not in seen_pmids:
            seen_pmids.add(pmid)
            deduplicated_evidence.append(e)
    
    # Update Phase 2 evidence list with deduplicated version
    st.session_state.data['phase2']['evidence'] = deduplicated_evidence
    evidence_list = deduplicated_evidence
    
    phase2_pmids = seen_pmids
    
    # Identify new PMIDs in Phase 3 not yet in Phase 2
    new_pmids_in_phase3 = phase3_pmids - phase2_pmids
    
    # Count evidence-backed nodes (nodes with non-'N/A' evidence field)
    evidence_backed_nodes = [n for n in st.session_state.data['phase3']['nodes'] 
                            if n.get('evidence', 'N/A') not in ['N/A', '', None]]
    evidence_backed_count = len(evidence_backed_nodes)
    
    # Track enrichment state: re-enrich only when new PMIDs appear that haven't been processed
    if 'p3_last_enriched_pmids' not in st.session_state:
        st.session_state['p3_last_enriched_pmids'] = set()
    
    enriched_count = 0
    pmids_to_enrich_now = new_pmids_in_phase3 - st.session_state['p3_last_enriched_pmids']
    
    # Auto-enrich Phase 2 with truly NEW PMIDs (not previously enriched)
    if pmids_to_enrich_now:
        with ai_activity("Enriching evidence and auto‑grading new PMIDs…"):
            new_evidence_list = enrich_phase2_with_new_pmids(pmids_to_enrich_now, phase2_pmids)
            if new_evidence_list:
                # Auto‑grade the newly added items
                auto_grade_evidence_list(new_evidence_list)
                # Mark as new for visual highlight and add to Phase 2
                for e in new_evidence_list:
                    e["is_new"] = True
                    if not e.get("source"):
                        e["source"] = "enriched_from_phase3"
                st.session_state.data['phase2']['evidence'].extend(new_evidence_list)
                enriched_count = len(new_evidence_list)
        # Update tracking to prevent re-enrichment of same PMIDs
        st.session_state['p3_last_enriched_pmids'] = new_pmids_in_phase3.copy()
    
    # Create metrics display
    if evidence_backed_count == 0:
        evidence_status = "No evidence citations"
    else:
        evidence_status = f"{evidence_backed_count} evidence-based nodes"
        if len(new_pmids_in_phase3) > 0:
            evidence_status += f" | {len(new_pmids_in_phase3)} new evidence in Phase 2"
    
    st.markdown(f"**Pathway Metrics:** {node_count} total nodes | {evidence_status}")
    
    # Show tip if new PMIDs detected (whether just enriched or already enriched)
    if new_pmids_in_phase3:
        styled_info(
            f"<b>New evidence identified:</b> {len(new_pmids_in_phase3)} PMID(s) from Phase 3 auto-graded and added to Phase 2 (marked with checked box in first column). "
            f"<b>Visit Phase 2</b> to review and finalize."
        )

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
            - If >20 nodes, organize into sections or sub-pathways
            - Prefer evidence-backed steps; cite PMIDs where available
            - Highlight benefit/harm trade-offs at decision points
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
        
        # Determine button type and label
        reco_button_type = "primary" if applied_flag else "secondary"
        reco_button_label = "Applied" if applied_flag else "Apply Recommendations"
        
        if st.button(reco_button_label, type=reco_button_type, key="p3_apply_reco_btn"):
            if not applied_flag:
                apply_large_pathway_recommendations()

    st.divider()

    # Refine & Regenerate (placed below the table)
    st.divider()
    submitted = False
    with st.expander("Refine & Regenerate", expanded=False):
        st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update all Phase 3 content and downloads")
        with st.form("p3_refine_form"):
            col_text, col_file = columns_top([2, 1])
            with col_text:
                st.text_area(
                    "Refinement Notes",
                    key="p3_refine_input",
                    placeholder="Add branch for renal impairment; include discharge meds for heart failure; clarify follow‑up",
                    height=90,
                    help="Describe what to change. After applying, the pathway will regenerate above."
                )

            with col_file:
                st.caption("Supporting Documents (optional)")
                p3_uploaded = st.file_uploader(
                    "Drag & drop or browse",
                    key="p3_file_upload",
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    help="Attach PDFs/DOCX files; the agent auto-summarizes them for context."
                )
                if p3_uploaded:
                    for uploaded_file in p3_uploaded:
                        file_result = upload_and_review_file(uploaded_file, f"p3_refine_{uploaded_file.name}", "decision tree pathway")
                        if file_result:
                            with st.expander(f"Review: {file_result['filename']}", expanded=False):
                                st.markdown(file_result["review"])

            col1, col2 = st.columns([3, 1])
            with col2:
                submitted = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)

    if submitted:
        refinement_request = st.session_state.get('p3_refine_input', '').strip()
        if refinement_request:
            # Collect all uploaded document reviews
            doc_reviews = []
            for key in st.session_state.keys():
                if key.startswith("file_p3_refine_") and key != "file_p3_refine":
                    doc_reviews.append(st.session_state.get(key, ''))
            
            if doc_reviews:
                refinement_request += f"\n\nSupporting Documents:\n" + "\n\n".join(doc_reviews)
            
            if st.session_state.data['phase3']['nodes']:
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
                        # Clean up common AI generation issues
                        nodes = normalize_or_logic(nodes)
                        nodes = fix_decision_flow_issues(nodes)
                        st.session_state.data['phase3']['nodes'] = nodes
                        # Clear Phase 4 visualization cache so regenerated views/downloads reflect updates
                        st.session_state.data.setdefault('phase4', {}).pop('viz_cache', None)
                        st.success("Refinements applied and pathway regenerated!")
                    else:
                        st.error("Failed to regenerate pathway. Please try again.")
                    st.rerun()
    
    render_bottom_navigation()
    st.stop()

# --- PHASE 4 ---
elif "Interface" in phase or "UI" in phase:
    st.header(f"Phase 4. {PHASES[3]}")
    styled_info("<b>Tip:</b> Heuristic recommendations are auto-generated. Review, then apply or undo per criterion.")
    
    nodes = st.session_state.data['phase3']['nodes']
    p4_state = st.session_state.data.setdefault('phase4', {})

    # GUARD: If no nodes, continue rendering Phase 4 with guidance
    if not nodes:
        st.warning("No pathway nodes found. You can still review heuristics and apply custom refinements below.")

    # Initialize Phase 4 state defaults
    p4_state.setdefault('nodes_history', [])
    p4_state.setdefault('heuristics_data', {})
    p4_state.setdefault('auto_heuristics_done', False)
    p4_state.setdefault('ui_apply_flags', {})
    p4_state.setdefault('applied_status', False)
    p4_state.setdefault('applied_summary', "")
    p4_state.setdefault('applying_heuristics', False)  # Flag to prevent re-analysis during apply

    # Detect pathway changes and allow heuristics to re-run
    # BUT: Don't clear heuristics if we're currently applying them
    try:
        nodes_hash = hashlib.md5(json.dumps(nodes, sort_keys=True).encode('utf-8')).hexdigest()
    except Exception:
        nodes_hash = str(len(nodes))
    
    if p4_state.get('last_nodes_hash') != nodes_hash and not p4_state.get('applying_heuristics'):
        p4_state['last_nodes_hash'] = nodes_hash
        # Clear prior heuristics to refresh recommendations only if nodes changed externally (not from applying heuristics)
        p4_state['heuristics_data'] = {}
        p4_state['auto_heuristics_done'] = False
        p4_state['applied_status'] = False
        p4_state['applied_summary'] = ""
    elif p4_state.get('applying_heuristics'):
        # We just applied heuristics, update hash but keep heuristics data
        p4_state['last_nodes_hash'] = nodes_hash
        p4_state['applying_heuristics'] = False  # Reset flag

    # If heuristics never populated but auto-run flagged as done, allow rerun
    if not p4_state['heuristics_data'] and p4_state.get('auto_heuristics_done'):
        p4_state['auto_heuristics_done'] = False

    # Auto-run heuristics once if pathway data exists
    if nodes and not p4_state['heuristics_data'] and not p4_state['auto_heuristics_done']:
        with ai_activity("Analyzing usability heuristics…"):
            # Limit nodes in prompt to avoid token overflow
            nodes_sample = nodes[:10] if len(nodes) > 10 else nodes
            prompt = f"""
            Analyze the following clinical decision pathway for Nielsen's 10 Usability Heuristics.
            For each heuristic (H1-H10), provide a specific, actionable critique and suggestion in 2-3 sentences.
            
            Pathway nodes: {json.dumps(nodes_sample)}
            
            Return ONLY valid JSON with exactly these keys: H1, H2, H3, H4, H5, H6, H7, H8, H9, H10
            Each value should be a string with the recommendation.
            
            Example format: {{"H1": "The pathway lacks clear status indicators...", "H2": "Medical jargon should be..."}}
            """
            res = get_gemini_response(prompt, json_mode=True)
            if res and isinstance(res, dict) and len(res) >= 10:
                p4_state['heuristics_data'] = res
                p4_state['auto_heuristics_done'] = True
                st.rerun()  # Rerun to display heuristics immediately
            else:
                # Don't mark as done so it retries on next interaction
                st.warning(f"Heuristics generation incomplete. Received {len(res) if res else 0} of 10. Please try again or navigate away and back.")
    elif not nodes:
        # Debug: show why heuristics aren't generating
        st.info("Waiting for pathway nodes from Phase 3...")
    elif p4_state.get('auto_heuristics_done') and not p4_state.get('heuristics_data'):
        # Debug: generation was attempted but failed
        st.warning("Heuristics generation failed. Retrying...")
        p4_state['auto_heuristics_done'] = False
        st.rerun()

    # Prepare nodes for visualization with a lightweight cache
    nodes_for_viz = nodes if nodes else [
        {"label": "Start", "type": "Start"},
        {"label": "Add nodes in Phase 3", "type": "Process"},
        {"label": "End", "type": "End"},
    ]
    cache = p4_state.setdefault('viz_cache', {})
    sig = hashlib.md5(json.dumps(nodes_for_viz, sort_keys=True).encode('utf-8')).hexdigest()

    # FULLSCREEN-ONLY VISUALIZATION + RIGHT-SIDE HEURISTICS LAYOUT
    # Build or retrieve SVG for visualization (no inline preview)
    svg_bytes = cache.get(sig, {}).get("svg")
    if svg_bytes is None:
        g = build_graphviz_from_nodes(nodes_for_viz, "TD")
        if g:
            new_svg = render_graphviz_bytes(g, "svg")
            cache[sig] = {"svg": new_svg}
            svg_bytes = new_svg
        else:
            debug_log(f"build_graphviz_from_nodes returned None. graphviz module: {graphviz}")
    p4_state['viz_cache'] = {sig: cache.get(sig, {})}

    import base64
    svg_b64 = base64.b64encode(svg_bytes or b"").decode('utf-8') if svg_bytes else ""
    
    # Also decode SVG to string for direct embedding
    svg_str = svg_bytes.decode('utf-8') if svg_bytes else ""

    # Always prepare DOT source as a client-side fallback via Viz.js
    dot_src = dot_from_nodes(nodes_for_viz, "TD")

    # DEBUG: Log SVG generation status
    debug_log(f"SVG generation - graphviz: {graphviz is not None}, svg_bytes: {svg_bytes is not None}, svg_b64 len: {len(svg_b64)}, svg_str len: {len(svg_str)}")

    col_left, col_right = st.columns([3, 2])

    # LEFT: Fullscreen open + manual edit + refine/regenerate
    with col_left:
        st.subheader("Pathway Visualization")
        if svg_bytes:
            c1, c2 = columns_top([1, 1])
            with c1:
                st.download_button("Download (SVG)", svg_bytes, file_name="pathway.svg", mime="image/svg+xml")
            with c2:
                st.caption("Re‑download the SVG after each edit to see updates.")
        else:
            st.warning("SVG unavailable. Install Graphviz on the server and retry.")

        st.divider()

        # EDIT PATHWAY DATA SECTION (immediately below visualization controls)
        st.subheader("Edit Pathway Manually")
        with st.expander("Edit Pathway Data", expanded=False):
            df_p4 = pd.DataFrame(nodes)
            if 'node_id' not in df_p4.columns:
                df_p4.insert(0, 'node_id', range(1, len(df_p4) + 1))
            else:
                df_p4['node_id'] = range(1, len(df_p4) + 1)
            edited_p4 = st.data_editor(df_p4, num_rows="dynamic", key="p4_editor")
            manual_changed = not df_p4.equals(edited_p4)
            if manual_changed:
                if 'node_id' in edited_p4.columns:
                    edited_p4 = edited_p4.drop('node_id', axis=1)
                st.session_state.data['phase3']['nodes'] = edited_p4.to_dict('records')
                p4_state['viz_cache'] = {}
                st.info("Nodes updated. Click 'Regenerate Visualization & Downloads' to refresh.")

            regen_disabled = not manual_changed and not st.session_state.data['phase3'].get('nodes')
            if st.button("Regenerate Visualization & Downloads", key="p4_manual_regen", disabled=regen_disabled):
                p4_state['viz_cache'] = {}
                st.success("Visualization regenerated with latest edits. Open fullscreen or download updated SVG.")
                st.rerun()

        st.divider()

        # LIVE DOT EDITOR SECTION (NEW)
        st.subheader("Advanced: Live DOT Editor")
        with st.expander("Edit DOT Source & Live Preview", expanded=False):
            col_editor, col_preview = st.columns([1, 1])
            
            with col_editor:
                st.markdown("**DOT Source** (expert mode)")
                current_dot = dot_from_nodes(nodes_for_viz, "TD")
                
                edited_dot = st.text_area(
                    "Edit pathway DOT syntax",
                    value=current_dot,
                    height=400,
                    key="dot_editor",
                    help="Modify colors, labels, shapes. Changes preview in real-time."
                )
            
            with col_preview:
                st.markdown("**Live Preview** (via Viz.js)")
                
                # Check if DOT changed from current
                dot_changed = edited_dot != current_dot
                
                if dot_changed:
                    st.info("📝 Editing DOT source...")
                    
                    # Embed Viz.js + render live
                    viz_html = f"""
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"></script>
                    <div id="graph" style="border: 1px solid #ddd; padding: 10px; background: white; border-radius: 4px;"></div>
                    <script>
                        const dotSrc = `{edited_dot}`;
                        try {{
                            const viz = new Viz();
                            viz.renderSVGElement(dotSrc).then(element => {{
                                document.getElementById('graph').appendChild(element);
                            }}).catch(err => {{
                                document.getElementById('graph').innerHTML = 
                                    '<p style="color:red; font-family: monospace;">❌ DOT Syntax Error:<br/>' + err.message + '</p>';
                            }});
                        }} catch(e) {{
                            document.getElementById('graph').innerHTML = 
                                '<p style="color:red; font-family: monospace;">❌ ' + e.message + '</p>';
                        }}
                    </script>
                    """
                    st.components.v1.html(viz_html, height=500, scrolling=True)
                else:
                    st.success("✓ Current pathway DOT")
                    viz_html_current = f"""
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"></script>
                    <div id="graph" style="border: 1px solid #ddd; padding: 10px; background: white; border-radius: 4px;"></div>
                    <script>
                        const viz = new Viz();
                        viz.renderSVGElement(`{current_dot}`).then(element => {{
                            document.getElementById('graph').appendChild(element);
                        }}).catch(err => {{
                            document.getElementById('graph').innerHTML = '<p style="color:red;">Error rendering: ' + err.message + '</p>';
                        }});
                    </script>
                    """
                    st.components.v1.html(viz_html_current, height=500, scrolling=True)
            
            # Action buttons
            st.divider()
            col_save, col_download, col_reset = st.columns(3)
            
            with col_save:
                if st.button("💾 Apply DOT Changes", key="apply_dot_changes", type="primary", use_container_width=True):
                    st.success("✅ DOT applied! Download SVG to save visual changes.")
                    st.session_state['dot_editor_applied'] = True
            
            with col_download:
                if st.button("⬇️ Download Custom DOT", key="download_custom_dot", use_container_width=True):
                    st.download_button(
                        "📄 pathway-custom.dot",
                        edited_dot,
                        file_name="pathway-custom.dot",
                        mime="text/plain",
                        key="download_dot_button"
                    )
            
            with col_reset:
                if st.button("🔄 Reset to Original", key="reset_dot_editor", use_container_width=True):
                    st.session_state.dot_editor = current_dot
                    st.rerun()
            
            # Color legend
            st.markdown("""
            **Color Legend:**
            - 🟩 Green: Start/End nodes (`#D5E8D4`)
            - 🟥 Red: Decision nodes (`#F8CECC`)
            - 🟨 Yellow: Process nodes (`#FFF2CC`)
            - 🟧 Orange: Reevaluation (`#FFCC80`)
            
            **Tip:** Export to [Graphviz Online](https://dreampuf.github.io/GraphvizOnline/) or [draw.io](https://draw.io) for advanced editing.
            """)

        st.divider()

        # REFINE AND REGENERATE SECTION (collapsed for cleaner UI)
        h_data = p4_state.get('heuristics_data', {})
        with st.expander("Refine & Regenerate", expanded=False):
            st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update Phase 4 content and downloads.")
            with st.form("p4_refine_form"):
                col_text, col_file = columns_top([2, 1])
                with col_text:
                    refine_notes = st.text_area(
                        "Refinement Notes",
                        placeholder="Consolidate redundant steps; add alerts for critical values; use patient-friendly terms",
                        key="p4_refine_notes",
                        height=90,
                        label_visibility="visible"
                    )

                with col_file:
                    st.caption("Supporting Documents (optional)")
                    uploaded = st.file_uploader(
                        "Drag and drop file here",
                        key="p4_upload",
                        accept_multiple_files=False,
                        label_visibility="collapsed",
                        help="Limit 200MB per file"
                    )
                    if uploaded:
                        file_result = upload_and_review_file(uploaded, "p4_refine_file", "pathway")
                        if file_result:
                            with st.expander("File Review", expanded=False):
                                st.markdown(file_result["review"])

                col_form_gap, col_form_btn = st.columns([3, 1])
                with col_form_btn:
                    submitted = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)

            if submitted:
                refine_with_file = st.session_state.get('p4_refine_notes', '').strip()
                if refine_with_file:
                    if st.session_state.get("file_p4_refine_file"):
                        refine_with_file += f"\n\n**Supporting Document:**\n{st.session_state.get('file_p4_refine_file')}"
                    with st.spinner("Applying refinements..."):
                        refined = regenerate_nodes_with_refinement(nodes, refine_with_file, h_data) if 'regenerate_nodes_with_refinement' in globals() else None
                        if refined:
                            st.session_state.data['phase3']['nodes'] = refined
                            p4_state['viz_cache'] = {}
                            st.success("Refinements applied. Regenerated nodes below.")
                            st.rerun()
                        else:
                            st.warning("Could not apply refinements. Please try different notes or regenerate.")

    # RIGHT: Nielsen's heuristics panel
    with col_right:
        st.subheader("Nielsen's Heuristics Evaluation")
        h_data = p4_state.get('heuristics_data', {})

        if not h_data:
            styled_info("Heuristics are generated automatically. They will appear here shortly.")
            # Add manual retry button if auto-generation hasn't completed
            if nodes and st.button("Generate Heuristics Now", key="p4_manual_heuristics", type="secondary"):
                p4_state['auto_heuristics_done'] = False
                st.rerun()
        else:
            # Display ALL heuristics H1-H10 without pre-filtering
            # AI will intelligently evaluate each and apply only those that improve the pathway
            ordered_keys = sorted(h_data.keys(), key=lambda k: int(k[1:]) if k[1:].isdigit() else k)
            st.markdown("### Heuristics (H1–H10)")
            st.caption("Review each heuristic. AI will evaluate all and apply those that improve pathway structure. Results will show what was applied and what was skipped.")

            for heuristic_key in ordered_keys:
                insight = h_data.get(heuristic_key, "")
                # Get label from HEURISTIC_DEFS
                label_stub = HEURISTIC_DEFS.get(heuristic_key, "Heuristic").split(' (')[0].split(':')[0]

                with st.expander(f"**{heuristic_key}** - {label_stub}", expanded=False):
                    st.markdown(f"**Full Heuristic:** {HEURISTIC_DEFS.get(heuristic_key, 'N/A')}")
                    st.divider()
                    st.markdown("**AI Assessment for Your Pathway:**")
                    st.markdown(
                        f"<div style='background-color: white; color: black; padding: 12px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 10px; border-left: 4px solid #5D4037;'>{insight}</div>",
                        unsafe_allow_html=True
                    )
                    st.caption("AI will determine if this can be meaningfully applied to pathway nodes.")

            # APPLY + UNDO BUTTONS
            has_heuristics = bool(h_data)
            if has_heuristics:
                st.markdown("### Apply Heuristics")
                st.caption("AI will evaluate ALL H1-H10 heuristics and apply those that meaningfully improve your pathway structure. AI determines applicability intelligently.")
                
                if p4_state.get('applied_status') and p4_state.get('applied_summary_detail'):
                    st.success("✓ Heuristics applied successfully")
                    with st.expander("View detailed changes", expanded=False):
                        if p4_state.get('applied_heuristics'):
                            applied_list = p4_state['applied_heuristics']
                            st.markdown(f"**✅ Applied:** {', '.join(applied_list)}")
                            
                            # Show skipped heuristics
                            all_h = set([f"H{i}" for i in range(1, 11)])
                            skipped = sorted(list(all_h - set(applied_list)), key=lambda x: int(x[1:]))
                            if skipped:
                                st.markdown(f"**⊘ Skipped:** {', '.join(skipped)} (not applicable to pathway structure)")
                        st.divider()
                        st.markdown("**Changes Summary:**")
                        st.markdown(p4_state['applied_summary_detail'])
                
                col_apply, col_undo = st.columns([1, 1])
                with col_apply:
                    btn_applied = p4_state.get('applied_status', False)
                    btn_label = "Applied ✓" if btn_applied else "Apply All Heuristics"
                    btn_type = "primary" if btn_applied else "secondary"
                    if st.button(btn_label, key="p4_apply_all_actionable", type=btn_type, disabled=btn_applied):
                        # Initialize history if needed
                        if 'nodes_history' not in p4_state:
                            p4_state['nodes_history'] = []
                        
                        # Save current state to history BEFORE applying
                        p4_state['nodes_history'].append(copy.deepcopy(nodes))
                        p4_state['applying_heuristics'] = True  # Set flag to prevent re-analysis
                        
                        with ai_activity("AI evaluating ALL H1-H10 heuristics and applying those that improve pathway…"):
                            improved_nodes, applied_heuristics, apply_summary = apply_actionable_heuristics_incremental(nodes, h_data)
                            if improved_nodes and len(improved_nodes) > 0:
                                st.session_state.data['phase3']['nodes'] = harden_nodes(improved_nodes)
                                p4_state['viz_cache'] = {}
                                p4_state['applied_status'] = True
                                p4_state['applied_heuristics'] = applied_heuristics
                                p4_state['applied_summary_detail'] = apply_summary
                                st.rerun()
                            else:
                                # Remove from history if apply failed
                                if p4_state.get('nodes_history'):
                                    p4_state['nodes_history'].pop()
                                st.error("Could not process recommendations. AI returned no valid nodes. Please try again.")

                with col_undo:
                    history_count = len(p4_state.get('nodes_history', []))
                    undo_disabled = history_count == 0
                    if st.button("Undo Last Changes", key="p4_undo_all", type="secondary", disabled=undo_disabled):
                        if p4_state.get('nodes_history') and len(p4_state['nodes_history']) > 0:
                            prev_nodes = p4_state['nodes_history'].pop()
                            st.session_state.data['phase3']['nodes'] = prev_nodes
                            p4_state['viz_cache'] = {}
                            p4_state['applied_status'] = False
                            p4_state['applied_summary_detail'] = ""
                            p4_state['applied_heuristics'] = []
                            st.success(f"✓ Reverted to previous version ({len(prev_nodes)} nodes)")
                            st.rerun()
                        else:
                            st.info("No changes to undo")
                    if history_count > 0:
                        st.caption(f"{history_count} version(s) in history")

    render_bottom_navigation()
    st.stop()

# --- PHASE 5 ---
elif "Operationalize" in phase or "Deploy" in phase:
    st.header(f"Phase 5. {PHASES[4]}")
    
    # Import Phase 5 helpers
    try:
        from phase5_helpers import (
            generate_expert_form_html,
            generate_beta_form_html,
            create_phase5_executive_summary_docx,
            ensure_carepathiq_branding,
            get_role_depth_mapping,
            generate_role_specific_module_header,
            generate_role_specific_learning_objectives,
            generate_role_specific_quiz_scenario,
            filter_nodes_by_role
        )
        from education_template import create_education_module_template
    except ImportError:
        st.error("Phase 5 helpers not found. Please ensure phase5_helpers.py and education_template.py are in the workspace.")
        st.stop()
    
    # Single info box at top
    styled_info("<b>Tip:</b> Enter a target audience below, and each deliverable will be auto-generated immediately. Download the HTML file to share—it opens in any browser and allows feedback export as CSV.")
    
    cond = st.session_state.data['phase1']['condition'] or "Pathway"
    setting = st.session_state.data['phase1'].get('setting', '') or ""
    nodes = st.session_state.data['phase3']['nodes'] or []
    
    # Initialize session state for each deliverable
    deliverables = {
        "expert": "Expert Panel Feedback",
        "beta": "Beta Testing Guide",
        "education": "Education Module",
        "executive": "Executive Summary"
    }
    
    for key in deliverables:
        if f"p5_aud_{key}" not in st.session_state:
            st.session_state[f"p5_aud_{key}"] = ""
    
    # 2x2 GRID LAYOUT
    col1, col2 = st.columns(2)

    # ========== TOP LEFT: EXPERT PANEL FEEDBACK ==========
    with col1:
        st.markdown(f"<h3>{deliverables['expert']}</h3>", unsafe_allow_html=True)

        aud_expert = st.text_input(
            "Target Audience",
            value=st.session_state.get("p5_aud_expert", ""),
            placeholder="e.g., Clinical Leaders, Quality & Safety",
            key="p5_aud_expert_input"
        )

        # Auto-generate on input change
        if aud_expert and aud_expert != st.session_state.get("p5_aud_expert_prev", ""):
            st.session_state["p5_aud_expert"] = aud_expert
            st.session_state["p5_aud_expert_prev"] = aud_expert
            with st.spinner("Generating expert feedback form..."):
                # Generate SVG for pathway visualization in downloaded form
                g = build_graphviz_from_nodes(nodes, "TD")
                svg_bytes = render_graphviz_bytes(g, "svg") if g else None
                svg_b64 = base64.b64encode(svg_bytes).decode('utf-8') if svg_bytes else None
                
                expert_html = generate_expert_form_html(
                    condition=cond,
                    nodes=nodes,
                    audience=aud_expert,
                    organization=cond,
                    care_setting=setting,
                    pathway_svg_b64=svg_b64,
                    genai_client=get_genai_client()
                )
                st.session_state.data['phase5']['expert_html'] = ensure_carepathiq_branding(expert_html)

                if st.session_state.data['phase5'].get('expert_html'):
                        exp_html = st.session_state.data['phase5']['expert_html']
                        dl_l, dl_c, dl_r = st.columns([1, 2, 1])
                        with dl_c:
                                st.download_button(
                                        "Download (.html)",
                                        exp_html,
                                        f"ExpertFeedback_{cond.replace(' ', '_')}.html",
                                        "text/html",
                                        
                                )

                        # Inline pathway preview (similar to Phase 4) for expert panel context
                        nodes_for_viz = nodes if nodes else [
                                {"label": "Start", "type": "Start"},
                                {"label": "Add nodes in Phase 3", "type": "Process"},
                                {"label": "End", "type": "End"},
                        ]
        # Refine section (collapsible, notes on the left for natural flow)
        with st.expander("Refine & Regenerate", expanded=False):
            st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update Phase 5 content and downloads")
            with st.form("p5_refine_expert_form"):
                col_text, col_file = columns_top([2, 1])
                with col_text:
                    refine_expert = st.text_area(
                        "Refinement Notes",
                        placeholder="Add usability metrics; clarify scenarios; shorten steps",
                        key="p5_refine_expert",
                        height=90,
                        label_visibility="visible"
                    )
                with col_file:
                    st.caption("Supporting Documents (optional)")
                    p5e_uploaded = st.file_uploader(
                        "Drag & drop or browse",
                        key="p5_expert_upload",
                        accept_multiple_files=False,
                        label_visibility="collapsed"
                    )
                    if p5e_uploaded:
                        file_result = upload_and_review_file(p5e_uploaded, "p5_expert", "expert panel feedback form")
                        if file_result:
                            with st.expander("File Review", expanded=True):
                                st.markdown(file_result["review"])
                
                col_form_gap, col_form_btn = st.columns([3, 1])
                with col_form_btn:
                    submitted_expert = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)
            
            if submitted_expert:
                with st.spinner("Refining..."):
                    refine_with_file = refine_expert
                    if st.session_state.get("file_p5_expert_review"):
                        refine_with_file += f"\n\n**Supporting Document:**\n{st.session_state.get('file_p5_expert_review')}"
                    
                    refined_html = generate_expert_form_html(
                        condition=cond,
                        nodes=nodes,
                        audience=st.session_state.get("p5_aud_expert", ""),
                        organization=cond,
                        care_setting=setting,
                        genai_client=get_genai_client()
                    )
                    st.session_state.data['phase5']['expert_html'] = ensure_carepathiq_branding(refined_html)
                    st.success("Refined!")

# ========== TOP RIGHT: BETA TESTING GUIDE ==========
    with col2:
        st.markdown(f"<h3>{deliverables['beta']}</h3>", unsafe_allow_html=True)
        
        aud_beta = st.text_input(
            "Target Audience",
            value=st.session_state.get("p5_aud_beta", ""),
            placeholder="e.g., ED Clinicians (Physicians, RNs), APPs",
            key="p5_aud_beta_input"
        )
        
        # Auto-generate on input change
        if aud_beta and aud_beta != st.session_state.get("p5_aud_beta_prev", ""):
            st.session_state["p5_aud_beta"] = aud_beta
            st.session_state["p5_aud_beta_prev"] = aud_beta
            with st.spinner("Generating guide..."):
                beta_html = generate_beta_form_html(
                    condition=cond,
                    nodes=nodes,
                    audience=aud_beta,
                    organization=cond,
                    care_setting=setting,
                    genai_client=get_genai_client()
                )
                st.session_state.data['phase5']['beta_html'] = ensure_carepathiq_branding(beta_html)
        
        # Download centered
        if st.session_state.data['phase5'].get('beta_html'):
            beta_html = st.session_state.data['phase5']['beta_html']
            dl_l, dl_c, dl_r = st.columns([1,2,1])
            with dl_c:
                st.download_button(
                    "Download (.html)",
                    beta_html,
                    f"BetaTestingGuide_{cond.replace(' ', '_')}.html",
                    "text/html",
                    
                )

        # Refine & Regenerate section (matching Expert Panel pattern)
        with st.expander("Refine & Regenerate", expanded=False):
            st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update Phase 5 content and downloads")
            with st.form("p5_refine_beta_form"):
                col_text, col_file = columns_top([2, 1])
                with col_text:
                    refine_beta = st.text_area(
                        "Refinement Notes",
                        placeholder="Add usability metrics; clarify scenarios; shorten steps",
                        key="p5_refine_beta",
                        height=90,
                        label_visibility="visible"
                    )
                with col_file:
                    st.caption("Supporting Documents (optional)")
                    p5b_uploaded = st.file_uploader(
                        "Drag & drop or browse",
                        key="p5_beta_upload",
                        accept_multiple_files=False,
                        label_visibility="collapsed"
                    )
                    if p5b_uploaded:
                        file_result = upload_and_review_file(p5b_uploaded, "p5_beta", "beta testing guide")
                        if file_result:
                            with st.expander("File Review", expanded=True):
                                st.markdown(file_result["review"])
                
                col_form_gap, col_form_btn = st.columns([3, 1])
                with col_form_btn:
                    submitted_beta = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)
            
            if submitted_beta:
                with st.spinner("Refining..."):
                    refine_with_file = refine_beta
                    if st.session_state.get("file_p5_beta_review"):
                        refine_with_file += f"\n\n**Supporting Document:**\n{st.session_state.get('file_p5_beta_review')}"
                    
                    refined_html = generate_beta_form_html(
                        condition=cond,
                        nodes=nodes,
                        audience=st.session_state.get("p5_aud_beta", ""),
                        organization=cond,
                        care_setting=setting,
                        genai_client=get_genai_client()
                    )
                    st.session_state.data['phase5']['beta_html'] = ensure_carepathiq_branding(refined_html)
                    st.success("Refined!")
    
    st.divider()
    
    col3, col4 = columns_top(2)
    
    # ========== BOTTOM LEFT: EDUCATION MODULE ==========
    with col3:
        st.markdown(f"<h3>{deliverables['education']}</h3>", unsafe_allow_html=True)
        
        aud_edu = st.text_input(
            "Target Audience",
            value=st.session_state.get("p5_aud_edu", ""),
            placeholder="e.g., Clinical Team (Residents, RNs, APPs)",
            key="p5_aud_edu_input"
        )
        
        # Auto-generate on input change
        if aud_edu and aud_edu != st.session_state.get("p5_aud_edu_prev", ""):
            st.session_state["p5_aud_edu"] = aud_edu
            st.session_state["p5_aud_edu_prev"] = aud_edu
            with st.spinner("Generating module..."):
                # Extract learning objectives from Phase 1 charter
                charter = st.session_state.data['phase1'].get('charter', '')
                overall_objectives = []
                if charter:
                    if 'goals' in charter.lower() or 'objectives' in charter.lower():
                        lines = charter.split('\n')
                        for i, line in enumerate(lines):
                            if any(word in line.lower() for word in ['goal', 'objective', 'aim']):
                                for j in range(i+1, min(i+5, len(lines))):
                                    if lines[j].strip().startswith(('-', '•', '*', '1.', '2.', '3.')):
                                        obj_text = lines[j].strip().lstrip('-•*123456789. ')
                                        if len(obj_text) > 10:
                                            overall_objectives.append(obj_text)

                if not overall_objectives:
                    overall_objectives = [
                        f"Understand the clinical approach to {cond}",
                        f"Apply evidence-based decision-making in {setting or 'clinical practice'}",
                        "Recognize key decision points in the care pathway",
                        "Implement standardized protocols effectively"
                    ]

                # Get role-specific configuration
                role_mapping = get_role_depth_mapping(aud_edu)
                role_type = role_mapping.get('role_type', 'Clinical Team Member')
                depth_level = role_mapping.get('depth_level', 'moderate')
                role_statement = role_mapping.get('role_statement', '')
                
                # Filter nodes by role
                filtered_nodes = filter_nodes_by_role(nodes, aud_edu)
                
                # Get evidence citations from Phase 2 for quiz explanations
                evidence_data = st.session_state.data['phase2'].get('evidence', [])
                
                # Create educational modules from filtered pathway nodes
                edu_topics = []
                if filtered_nodes and len(filtered_nodes) > 1:
                    decision_nodes = [n for n in nodes if n.get('type') in ['Decision', 'Process', 'Action'] and n.get('label', '').strip()]
                    nodes_per_module = max(1, len(decision_nodes) // 3)
                    module_groups = [decision_nodes[i:i + nodes_per_module] for i in range(0, len(decision_nodes), nodes_per_module)][:4]

                    for mod_idx, module_nodes in enumerate(module_groups):
                        if not module_nodes:
                            continue

                        # Generate role-specific module header
                        module_title = generate_role_specific_module_header(
                            target_audience=aud_edu,
                            condition=cond,
                            care_setting=setting,
                            node=module_nodes[0] if module_nodes else None
                        )
                        
                        if len(module_title) > 100:
                            module_title = module_title[:100] + '...'

                        content_html = f"<h4>Your Role in This Section</h4><p>{role_statement}</p><h4>Pathway Steps</h4>"
                        quiz_questions = []

                        for node in module_nodes:
                            node_label = node.get('label', 'Decision point')
                            node_type = node.get('type', 'Process')
                            node_evidence = node.get('evidence', 'N/A')

                            content_html += f"<div style='margin: 15px 0; padding: 10px; background: #f8f9fa; border-left: 3px solid #6c757d;'>"
                            content_html += f"<strong>{node_type}:</strong> {node_label}"
                            if node_evidence and node_evidence != 'N/A':
                                content_html += f"<br><small style='color: #666;'>Evidence: {node_evidence}</small>"
                            content_html += "</div>"

                            if node_type == 'Decision' and len(quiz_questions) < 3:
                                # Generate role-specific scenario for this node
                                scenario = generate_role_specific_quiz_scenario(
                                    question_idx=len(quiz_questions),
                                    node=node,
                                    target_audience=aud_edu,
                                    evidence_citations=evidence_data
                                )
                                quiz_questions.append(scenario)

                        content_html += "<h4>Key Clinical Pearls</h4><ul>"
                        content_html += f"<li>Early recognition and assessment improves outcomes</li>"
                        content_html += f"<li>Evidence-based pathways reduce variation in care</li>"
                        content_html += f"<li>Clear documentation supports care coordination</li>"
                        content_html += "</ul>"

                        if not quiz_questions:
                            quiz_questions.append({
                                "question": f"What is a key principle in {role_type} management of this pathway?",
                                "options": [
                                    "Follow evidence-based protocols",
                                    "Skip documentation steps",
                                    "Delay patient care",
                                    "Avoid clinical guidelines"
                                ],
                                "correct": 0,
                                "explanation": "Evidence-based protocols improve patient outcomes and standardize care."
                            })

                        # Generate role-specific learning objectives
                        module_objectives = generate_role_specific_learning_objectives(
                            target_audience=aud_edu,
                            condition=cond,
                            nodes=module_nodes,
                            module_idx=mod_idx
                        )

                        edu_topics.append({
                            "title": f"Module {mod_idx + 1}: {module_title}",
                            "content": content_html,
                            "learning_objectives": module_objectives,
                            "quiz": quiz_questions,
                            "time_minutes": 5
                        })

                if not edu_topics:
                    edu_topics = [
                        {
                            "title": f"Module 1: {cond} Pathway Overview",
                            "content": f"""
                                <h4>Introduction</h4>
                                <p>This module introduces the evidence-based clinical pathway for {cond} in {setting or 'clinical practice'}.</p>
                                
                                <h4>Core Principles</h4>
                                <ul>
                                    <li>Standardized assessment and triage</li>
                                    <li>Evidence-based decision making</li>
                                    <li>Coordinated multidisciplinary care</li>
                                    <li>Clear documentation and communication</li>
                                </ul>
                                
                                <h4>Key Takeaways</h4>
                                <p>Following standardized pathways improves patient safety, reduces variation, and enhances outcomes.</p>
                            """,
                            "learning_objectives": overall_objectives[:3],
                            "quiz": [{
                                "question": "What is the primary benefit of using clinical pathways?",
                                "options": [
                                    "Standardize care and improve patient safety",
                                    "Increase documentation burden",
                                    "Slow down clinical decision-making",
                                    "Eliminate clinical judgment"
                                ],
                                "correct": 0,
                                "explanation": "Clinical pathways standardize high-quality care while preserving clinical judgment, leading to better outcomes."
                            }],
                            "time_minutes": 5
                        }
                    ]

                edu_html = create_education_module_template(
                    condition=cond,
                    topics=edu_topics,
                    target_audience=aud_edu,
                    organization=cond,
                    care_setting=setting,
                    require_100_percent=True,
                    learning_objectives=overall_objectives[:4],
                    role_context=role_mapping,
                    role_statement=role_statement,
                    genai_client=get_genai_client()
                )
                st.session_state.data['phase5']['edu_html'] = ensure_carepathiq_branding(edu_html)
        
        # Download centered
        if st.session_state.data['phase5'].get('edu_html'):
            edu_html = st.session_state.data['phase5']['edu_html']
            dl_l, dl_c, dl_r = st.columns([1,2,1])
            with dl_c:
                st.download_button(
                    "Download (.html)",
                    edu_html,
                    f"EducationModule_{cond.replace(' ', '_')}.html",
                    "text/html",
                    
                )

        # Refine & Regenerate section (matching Expert Panel pattern)
        with st.expander("Refine & Regenerate", expanded=False):
            st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update Phase 5 content and downloads")
            with st.form("p5_refine_edu_form"):
                col_text, col_file = columns_top([2, 1])
                with col_text:
                    refine_edu = st.text_area(
                        "Refinement Notes",
                        placeholder="Add case studies; include quick checks; simplify objectives",
                        key="p5_refine_edu",
                        height=90,
                        label_visibility="visible"
                    )
                with col_file:
                    st.caption("Supporting Documents (optional)")
                    p5ed_uploaded = st.file_uploader(
                        "Drag & drop or browse",
                        key="p5_edu_upload",
                        accept_multiple_files=False,
                        label_visibility="collapsed"
                    )
                    if p5ed_uploaded:
                        file_result = upload_and_review_file(p5ed_uploaded, "p5_edu", "education module")
                        if file_result:
                            with st.expander("File Review", expanded=False):
                                st.markdown(file_result["review"])
                
                col_form_gap, col_form_btn = st.columns([3, 1])
                with col_form_btn:
                    submitted_edu = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)
            
            if submitted_edu:
                with st.spinner("Refining..."):
                    # Include file context
                    refine_with_file = refine_edu
                    if st.session_state.get("file_p5_edu_review"):
                        refine_with_file += f"\n\n**Supporting Document:**\n{st.session_state.get('file_p5_edu_review')}"
                    
                    # Get existing modules and add refinement notes
                    existing_html = st.session_state.data['phase5'].get('edu_html', '')
                    if existing_html:
                        # Append refinement notes to existing content
                        edu_topics = []
                        charter = st.session_state.data['phase1'].get('charter', '')
                        overall_objectives = []
                    
                        # Extract objectives (same as initial generation)
                        if charter:
                            lines = charter.split('\n')
                            for i, line in enumerate(lines):
                                if any(word in line.lower() for word in ['goal', 'objective', 'aim']):
                                    for j in range(i+1, min(i+5, len(lines))):
                                        if lines[j].strip().startswith(('-', '•', '*', '1.', '2.', '3.')):
                                            obj_text = lines[j].strip().lstrip('-•*123456789. ')
                                            if len(obj_text) > 10:
                                                overall_objectives.append(obj_text)
                    
                        if not overall_objectives:
                            overall_objectives = [
                                f"Understand the clinical approach to {cond}",
                                f"Apply evidence-based decision-making in {setting or 'clinical practice'}",
                                "Recognize key decision points in the care pathway",
                                "Implement standardized protocols effectively"
                            ]
                    
                        # Rebuild modules with refinement
                        if nodes and len(nodes) > 1:
                            decision_nodes = [n for n in nodes if n.get('type') in ['Decision', 'Process', 'Action'] and n.get('label', '').strip()]
                            nodes_per_module = max(1, len(decision_nodes) // 3)
                            module_groups = [decision_nodes[i:i + nodes_per_module] for i in range(0, len(decision_nodes), nodes_per_module)][:4]
                        
                            for mod_idx, module_nodes in enumerate(module_groups):
                                if not module_nodes:
                                    continue
                            
                                module_title = module_nodes[0].get('label', f'Module {mod_idx + 1}')
                                if len(module_title) > 60:
                                    module_title = module_title[:60] + '...'
                            
                                content_html = f"<h4>Pathway Steps</h4>"
                                quiz_questions = []
                            
                                for node in module_nodes:
                                    node_label = node.get('label', 'Decision point')
                                    node_type = node.get('type', 'Process')
                                    node_evidence = node.get('evidence', 'N/A')
                                
                                    content_html += f"<div style='margin: 15px 0; padding: 10px; background: #f8f9fa; border-left: 3px solid #6c757d;'>"
                                    content_html += f"<strong>{node_type}:</strong> {node_label}"
                                    if node_evidence and node_evidence != 'N/A':
                                        content_html += f"<br><small style='color: #666;'>Evidence: {node_evidence}</small>"
                                    content_html += "</div>"
                                
                                    if node_type == 'Decision' and len(quiz_questions) < 3:
                                        quiz_questions.append({
                                            "question": f"What is the recommended approach when: {node_label[:80]}?",
                                            "options": [
                                                "Follow the evidence-based pathway protocol",
                                                "Skip assessment and proceed to treatment",
                                                "Wait for additional consultation before acting",
                                                "Defer decision-making to ancillary services"
                                            ],
                                            "correct": 0,
                                            "explanation": f"The pathway recommends following evidence-based protocols. {node_evidence if node_evidence != 'N/A' else ''}"
                                        })
                            
                                # Add refinement notes section
                                content_html += "<h4>Key Clinical Pearls</h4><ul>"
                                content_html += f"<li>Early recognition and assessment improves outcomes</li>"
                                content_html += f"<li>Evidence-based pathways reduce variation in care</li>"
                                content_html += f"<li>Clear documentation supports care coordination</li>"
                                content_html += "</ul>"
                                content_html += f"<div style='margin-top: 20px; padding: 15px; background: #fff3cd; border-left: 3px solid #ffc107;'>"
                                content_html += f"<strong>Additional Guidance:</strong><br>{refine_with_file}</div>"
                            
                                if not quiz_questions:
                                    quiz_questions.append({
                                        "question": f"What is a key principle in this module?",
                                        "options": [
                                            "Follow evidence-based protocols",
                                            "Skip documentation steps",
                                            "Delay patient care",
                                            "Avoid clinical guidelines"
                                        ],
                                        "correct": 0,
                                        "explanation": "Evidence-based protocols improve patient outcomes and standardize care."
                                    })
                            
                                edu_topics.append({
                                    "title": f"Module {mod_idx + 1}: {module_title}",
                                    "content": content_html,
                                    "learning_objectives": [
                                        f"Understand decision points in {module_title.lower()}",
                                        "Apply evidence-based clinical reasoning",
                                        "Recognize appropriate care pathway steps"
                                    ],
                                    "quiz": quiz_questions,
                                    "time_minutes": 5
                                })
                    
                        if not edu_topics:
                            edu_topics = [{
                                "title": f"Module 1: {cond} Pathway Overview",
                                "content": f"""
                                    <h4>Introduction</h4>
                                    <p>This module introduces the evidence-based clinical pathway for {cond} in {setting or 'clinical practice'}.</p>
                                    <h4>Core Principles</h4>
                                    <ul>
                                        <li>Standardized assessment and triage</li>
                                        <li>Evidence-based decision making</li>
                                        <li>Coordinated multidisciplinary care</li>
                                        <li>Clear documentation and communication</li>
                                    </ul>
                                    <div style='margin-top: 20px; padding: 15px; background: #fff3cd; border-left: 3px solid #ffc107;'>
                                        <strong>Additional Guidance:</strong><br>{refine_with_file}
                                    </div>
                                """,
                                "learning_objectives": overall_objectives[:3],
                                "quiz": [{
                                    "question": "What is the primary benefit of using clinical pathways?",
                                    "options": [
                                        "Standardize care and improve patient safety",
                                        "Increase documentation burden",
                                        "Slow down clinical decision-making",
                                        "Eliminate clinical judgment"
                                    ],
                                    "correct": 0,
                                    "explanation": "Clinical pathways standardize high-quality care while preserving clinical judgment."
                                }],
                                "time_minutes": 5
                            }]
                    
                        refined_html = create_education_module_template(
                            condition=cond,
                            topics=edu_topics,
                            target_audience=st.session_state.get("p5_aud_edu", ""),
                            organization=cond,
                            care_setting=setting,
                            require_100_percent=True,
                            learning_objectives=overall_objectives[:4],
                            genai_client=get_genai_client()
                        )
                        st.session_state.data['phase5']['edu_html'] = ensure_carepathiq_branding(refined_html)
                    else:
                        st.warning("Please generate the education module first before refining.")
            st.success("Refined!")
    
    # ========== BOTTOM RIGHT: EXECUTIVE SUMMARY ==========
    with col4:
        st.markdown(f"<h3>{deliverables['executive']}</h3>", unsafe_allow_html=True)
        
        aud_exec = st.text_input(
            "Target Audience",
            value=st.session_state.get("p5_aud_exec", ""),
            placeholder="e.g., Hospital Leadership, Board Members",
            key="p5_aud_exec_input"
        )
        
        # Auto-generate on input change
        if aud_exec and aud_exec != st.session_state.get("p5_aud_exec_prev", ""):
            st.session_state["p5_aud_exec"] = aud_exec
            st.session_state["p5_aud_exec_prev"] = aud_exec
            with st.spinner("Generating summary..."):
                exec_summary = f"Executive Summary for {cond} - Prepared for {aud_exec}"
                st.session_state.data['phase5']['exec_summary'] = exec_summary
        
        # Download centered
        if st.session_state.data['phase5'].get('exec_summary'):
            # Pass session data, condition, and target audience per function signature
            docx_bytes = create_phase5_executive_summary_docx(
                data=st.session_state.data,
                condition=cond,
                target_audience=aud_exec,
                genai_client=get_genai_client()
            )
            dl_l, dl_c, dl_r = st.columns([1,2,1])
            with dl_c:
                st.download_button(
                    "Download (.docx)",
                    docx_bytes,
                    f"ExecutiveSummary_{cond.replace(' ', '_')}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    
                )
        
        # Refine & Regenerate section for Executive Summary
        with st.expander("Refine & Regenerate", expanded=False):
            st.markdown("**Tip:** Describe any desired modifications and optionally attach supporting documents. Click \"Regenerate\" to automatically update Phase 5 content and downloads")
            with st.form("p5_refine_exec_form"):
                col_text, col_file = columns_top([2, 1])
                with col_text:
                    st.text_area(
                        "Refinement Notes",
                        placeholder="Emphasize ROI and cost-benefit; highlight key metrics and outcomes; focus on strategic alignment",
                        key="p5_refine_exec",
                        height=90,
                        label_visibility="visible"
                    )
                with col_file:
                    st.caption("Supporting Documents (optional)")
                    p5ex_uploaded = st.file_uploader(
                        "Drag & drop or browse",
                        key="p5_exec_upload",
                        accept_multiple_files=False,
                        label_visibility="collapsed"
                    )
                    if p5ex_uploaded:
                        file_result = upload_and_review_file(p5ex_uploaded, "p5_exec", "executive summary")
                        if file_result:
                            with st.expander("File Review", expanded=False):
                                st.markdown(file_result["review"])
                
                col_form_gap, col_form_btn = st.columns([3, 1])
                with col_form_btn:
                    submitted_exec = st.form_submit_button("Regenerate", type="secondary", use_container_width=True)
            if submitted_exec:
                refine_exec = st.session_state.get('p5_refine_exec', '').strip()
                if refine_exec or st.session_state.get("file_p5_exec_review"):
                    with ai_activity("Refining Executive Summary…"):
                        refine_with_file = refine_exec
                        if st.session_state.get("file_p5_exec_review"):
                            refine_with_file += f"\n\n**Strategic Context:**\n{st.session_state.get('file_p5_exec_review')}"
                        refined_summary = f"Executive Summary for {cond} - Prepared for {st.session_state.get('p5_aud_exec', '')}. Strategic Updates: {refine_with_file}"
                        st.session_state.data['phase5']['exec_summary'] = refined_summary
                    st.success("Executive Summary auto-regenerated!")
                    st.rerun()
                else:
                    st.warning("Please enter refinement notes or attach supporting documents.")
    
    render_bottom_navigation()
    st.stop()

# Footer is now rendered within each phase via render_bottom_navigation()