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
import requests
import hashlib
import textwrap

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
    div[data-testid="stColumn"] {
        display: flex !important;
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

    /* PHASE 2 — highlight rows marked as new via the first checkbox column */
    div[data-testid="stDataFrame"] tbody tr:has(input[type="checkbox"]:checked) td,
    div[data-testid="stTable"] tbody tr:has(input[type="checkbox"]:checked) td {
        background-color: #FFB0C9 !important;
    }
    
    /* BOTTOM NAVIGATION */
    footer {
        visibility: hidden;
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
PHASES = ["Phase 1: Scoping & Charter", "Phase 2: Rapid Evidence Appraisal", "Phase 3: Decision Science", "Phase 4: User Interface Design", "Phase 5: Operationalize"]

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
    """Renders Previous/Next buttons at the bottom of the page."""
    if "current_phase_label" in st.session_state and st.session_state.current_phase_label in PHASES:
        current_idx = PHASES.index(st.session_state.current_phase_label)
        st.divider()
        col_prev, _, col_next = st.columns([1, 2, 1])
        if current_idx > 0:
            prev_phase = PHASES[current_idx - 1]
            with col_prev:
                st.button(f"{prev_phase.split(':')[0]}", key="bottom_prev", width="stretch", on_click=change_phase, args=(prev_phase,))
        if current_idx < len(PHASES) - 1:
            next_phase = PHASES[current_idx + 1]
            with col_next:
                st.button(f"{next_phase.split(':')[0]}", key="bottom_next", use_container_width=True, type="secondary", on_click=change_phase, args=(next_phase,))

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

def auto_grade_evidence_list(evidence_list):
    """Assign GRADE and rationale for a list of evidence items in-place using the existing AI helper.
    Falls back to safe defaults when the AI response is missing or malformed.
    """
    try:
        payload = [
            {k: v for k, v in e.items() if k in ["id", "title"]}
            for e in evidence_list if e.get("id") and e.get("title")
        ]
        if not payload:
            for e in evidence_list:
                e.setdefault("grade", "Un-graded")
                e.setdefault("rationale", "Not yet evaluated.")
            return
        prompt = (
            "Assign GRADE quality of evidence (use EXACTLY one of: 'High (A)', 'Moderate (B)', 'Low (C)', 'Very Low (D)') "
            "and provide a brief Rationale (1-2 sentences) for each article. "
            f"{json.dumps(payload)}. "
            "Return ONLY valid JSON object where keys are PMID strings and values are objects with 'grade' and 'rationale' fields. "
            "Example: {\"12345678\": {\"grade\": \"High (A)\", \"rationale\": \"text here\"}}"
        )
        grades = get_gemini_response(prompt, json_mode=True)
        if isinstance(grades, dict):
            for e in evidence_list:
                pmid_str = str(e.get("id", ""))
                g = grades.get(pmid_str)
                if isinstance(g, dict):
                    e["grade"] = g.get("grade", e.get("grade", "Un-graded"))
                    e["rationale"] = g.get("rationale", e.get("rationale", "Not provided."))
        # ensure defaults
        for e in evidence_list:
            e.setdefault("grade", "Un-graded")
            e.setdefault("rationale", "Not yet evaluated.")
    except Exception:
        for e in evidence_list:
            e.setdefault("grade", "Un-graded")
            e.setdefault("rationale", "Not yet evaluated.")

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
    formsubmit_script = """
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
                const recipientEmail = form.querySelector('input[name="recipient_email"]').value;
                if (recipientEmail) {
                    form.action = \`https://formsubmit.co/\${recipientEmail}\`;
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
    """
    
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

# Create custom horizontal phase selector using columns
cols = st.columns(len(PHASES))
phase = st.session_state.get("top_nav_radio", PHASES[0])

for idx, phase_name in enumerate(PHASES):
    with cols[idx]:
        is_current = phase_name == phase
        button_type = "primary" if is_current else "secondary"
        if st.button(
            phase_name.split(":")[0],
            key=f"phase_btn_{idx}",
            width="stretch",
            type=button_type
        ):
            st.session_state.top_nav_radio = phase_name
            st.session_state.current_phase_label = phase_name
            phase = phase_name
            st.rerun()

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
            with ai_activity("Applying refinements to Phase 1 content…"):
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    st.session_state.data['phase1']['inclusion'] = format_as_numbered_list(data.get('inclusion', ''))
                    st.session_state.data['phase1']['exclusion'] = format_as_numbered_list(data.get('exclusion', ''))
                    st.session_state.data['phase1']['problem'] = str(data.get('problem', ''))
                    st.session_state.data['phase1']['objectives'] = format_as_numbered_list(data.get('objectives', ''))
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

    # Always sync widget keys from saved data to show AI-generated content
    st.session_state['p1_cond_input'] = st.session_state.data['phase1'].get('condition', '')
    st.session_state['p1_setting'] = st.session_state.data['phase1'].get('setting', '')
    st.session_state['p1_inc'] = st.session_state.data['phase1'].get('inclusion', '')
    st.session_state['p1_exc'] = st.session_state.data['phase1'].get('exclusion', '')
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
    
    # Reset refinement applied flag if text area content changes
    if 'p1_last_refine_input' not in st.session_state:
        st.session_state['p1_last_refine_input'] = ""
    
    current_p1_refine = st.session_state.get('p1_refine_input', '').strip()
    if current_p1_refine != st.session_state['p1_last_refine_input']:
        st.session_state['p1_refinement_applied'] = False
        st.session_state['p1_last_refine_input'] = current_p1_refine
    
    # Check if refinements were just applied
    p1_refinement_applied = st.session_state.get('p1_refinement_applied', False)
    
    # Determine button type and label
    p1_refine_button_type = "primary" if p1_refinement_applied else "secondary"
    p1_refine_button_label = "Applied" if p1_refinement_applied else "Apply Refinements"
    
    if st.button(p1_refine_button_label, type=p1_refine_button_type, key="p1_apply_refine_btn"):
        if not p1_refinement_applied:
            apply_refinements()
            st.session_state['p1_refinement_applied'] = True
            st.success("Phase 1 refinements applied successfully!")

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
            st.altair_chart(chart, width="stretch")
    
    if st.button("Generate Project Charter", type="secondary", use_container_width=True):
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
    st.stop()

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

        # Use native Streamlit subheader with help parameter for consistent alignment
        st.subheader("Filter by GRADE", help=grade_help)

        # Default filters set to show all grades initially
        selected_grades = st.multiselect(
            "",
            ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
            default=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
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
            styled_info("<b>Tip:</b> Review the auto-graded GRADE and rationale. Hover over the top right of the table for more options including CSV download.")

            edited_ev = st.data_editor(
                df_ev[["new", "id", "title", "grade", "rationale", "url"]], 
                column_config={
                    "new": st.column_config.CheckboxColumn("New", disabled=True, help="Auto-added and auto-graded; highlighted in pink."),
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

            with c2:
                if show_citations:
                    st.subheader("Formatted Citations", help="Generate Word citations in your preferred style.")
                    citation_style = st.selectbox("Citation style", ["APA", "MLA", "Vancouver"], key="p2_citation_style", label_visibility="collapsed")
                    references_source = display_data if display_data else evidence_data

            # Align download buttons horizontally in a new row
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if show_table:
                    _, btn_col1, _ = st.columns([1, 1, 1])
                    with btn_col1:
                        st.download_button("Download", csv_data_full, "detailed_evidence_summary.csv", "text/csv", key="dl_csv_full", use_container_width=True)
            
            with btn_c2:
                if show_citations:
                    if not references_source:
                        styled_info("Add or unfilter evidence to generate references.")
                    else:
                        references_doc = create_references_docx(references_source, citation_style)
                        if references_doc:
                            _, btn_col2, _ = st.columns([1, 1, 1])
                            with btn_col2:
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
        styled_info("No results yet. Refine the search or ensure Phase 1 has a condition and setting.")
        # Offer quick broaden options
        c = st.session_state.data['phase1'].get('condition', '')
        s = st.session_state.data['phase1'].get('setting', '')
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
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
    st.stop()

# --- PHASE 3 ---
elif "Phase 3" in phase:
    st.title("Phase 3: Decision Science")
    styled_info("<b>Tip:</b> The AI agent generated an evidence-based decision tree. You can manually update text, add/remove nodes, or refine using natural language below.")
    
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
        with ai_activity("Auto-generating decision tree from Phase 1 & 2 data..."):
            nodes = get_gemini_response(prompt, json_mode=True)
        if isinstance(nodes, list) and len(nodes) > 0:
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
    
    # Display pathway metrics with evidence enrichment
    node_count = len(st.session_state.data['phase3']['nodes'])
    
    # Extract all PMIDs from Phase 3 nodes
    phase3_pmids = extract_pmids_from_nodes(st.session_state.data['phase3']['nodes'])
    phase2_pmids = set([e['id'] for e in evidence_list])
    
    # Identify new PMIDs in Phase 3 not yet in Phase 2
    new_pmids_in_phase3 = phase3_pmids - phase2_pmids
    
    # Count evidence-backed nodes (nodes with non-'N/A' evidence field)
    evidence_backed_nodes = [n for n in st.session_state.data['phase3']['nodes'] 
                            if n.get('evidence', 'N/A') not in ['N/A', '', None]]
    evidence_backed_count = len(evidence_backed_nodes)
    
    # Check if auto-enrichment has been performed in this session
    if 'p3_enrichment_performed' not in st.session_state:
        st.session_state['p3_enrichment_performed'] = False
    
    # Auto-enrich Phase 2 with new PMIDs if not yet done this session
    enriched_count = 0
    if new_pmids_in_phase3 and not st.session_state['p3_enrichment_performed']:
        with ai_activity("Enriching evidence and auto‑grading new PMIDs…"):
            new_evidence_list = enrich_phase2_with_new_pmids(new_pmids_in_phase3, phase2_pmids)
            if new_evidence_list:
                # Auto‑grade the newly added items
                auto_grade_evidence_list(new_evidence_list)
                # Mark as new for visual highlight, set neutral source
                for e in new_evidence_list:
                    e["is_new"] = True
                    if not e.get("source"):
                        e["source"] = "enriched_from_phase3"
                # Add to Phase 2 repository
                st.session_state.data['phase2']['evidence'].extend(new_evidence_list)
                enriched_count = len(new_evidence_list)
                st.session_state['p3_enrichment_performed'] = True
                st.session_state['p3_new_pmids_enriched'] = enriched_count
    else:
        enriched_count = st.session_state.get('p3_new_pmids_enriched', 0)
    
    # Create metrics display similar to total nodes and evidence-based nodes pattern
    if evidence_backed_count == 0:
        evidence_status = "No evidence citations"
    else:
        evidence_status = f"{evidence_backed_count} evidence-based nodes"
        if enriched_count > 0:
            evidence_status += f" | new evidence auto-graded: {enriched_count}"
    
    st.markdown(f"**Pathway Metrics:** {node_count} total nodes | {evidence_status}")
    
    # Show tip if new PMIDs were enriched
    if enriched_count > 0:
        styled_info(
            f"<b>Evidence updated:</b> {enriched_count} new PMID(s) auto-graded and added to Phase 2 (pink-highlighted). "
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

    # Natural Language Refinement Interface (placed below the table)
    st.text_area(
        "Refine Decision Tree",
        placeholder="E.g., 'Add a branch for patients with renal impairment', 'Include specific discharge medications for heart failure'...",
        key="p3_refine_input",
        height=80
    )
    
    # Reset refinement applied flag if text area content changes
    if 'p3_last_refine_input' not in st.session_state:
        st.session_state['p3_last_refine_input'] = ""
    
    current_refine_input = st.session_state.get('p3_refine_input', '').strip()
    if current_refine_input != st.session_state['p3_last_refine_input']:
        st.session_state['p3_refinement_applied'] = False
        st.session_state['p3_last_refine_input'] = current_refine_input
    
    # Check if refinements were just applied
    p3_refinement_applied = st.session_state.get('p3_refinement_applied', False)
    
    # Determine button type and label
    refine_button_type = "primary" if p3_refinement_applied else "secondary"
    refine_button_label = "Applied" if p3_refinement_applied else "Apply Refinements"
    
    if st.button(refine_button_label, type=refine_button_type, key="p3_apply_refine_btn"):
        if not p3_refinement_applied:
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
                        st.session_state['p3_refinement_applied'] = True
                        st.success("Refinements applied")
                        st.rerun()
    
    render_bottom_navigation()
    st.stop()

# --- PHASE 4 ---
elif "Phase 4" in phase:
    st.title("Phase 4: User Interface Design")
    styled_info("<b>Tip:</b> Evaluate your pathway against Nielsen's 10 Usability Heuristics. The AI agent can provide suggestions for each criterion.")
    
    nodes = st.session_state.data['phase3']['nodes']
    p4_state = st.session_state.data.setdefault('phase4', {})

    # GUARD: If no nodes, continue rendering Phase 4 with guidance
    if not nodes:
        st.warning("No pathway nodes found. You can still review heuristics and apply custom refinements below.")

    # Initialize Phase 4 state defaults
    p4_state.setdefault('nodes_history', [])
    p4_state.setdefault('heuristics_data', {})
    p4_state.setdefault('auto_heuristics_done', False)
    p4_state.setdefault('viz_height', 400)

    # If heuristics never populated but auto-run flagged as done, allow rerun
    if not p4_state['heuristics_data'] and p4_state.get('auto_heuristics_done'):
        p4_state['auto_heuristics_done'] = False

    # Auto-run heuristics once if pathway data exists
    if nodes and not p4_state['heuristics_data'] and not p4_state['auto_heuristics_done']:
        with ai_activity("Analyzing usability heuristics…"):
            prompt = f"""
            Analyze the following clinical decision pathway for Nielsen's 10 Usability Heuristics.
            For each heuristic (H1-H10), provide a specific, actionable critique and suggestion.
            Pathway nodes: {json.dumps(nodes)}
            Return ONLY a JSON object with keys H1-H10.
            """
            res = get_gemini_response(prompt, json_mode=True)
            if res:
                p4_state['heuristics_data'] = res
                p4_state['auto_heuristics_done'] = True

    # Prepare nodes for visualization with a lightweight cache
    nodes_for_viz = nodes if nodes else [
        {"label": "Start", "type": "Start"},
        {"label": "Add nodes in Phase 3", "type": "Process"},
        {"label": "End", "type": "End"},
    ]
    cache = p4_state.setdefault('viz_cache', {})
    sig = hashlib.md5(json.dumps(nodes_for_viz, sort_keys=True).encode('utf-8')).hexdigest()

    # TWO-COLUMN LAYOUT: Visualization (Left) + Heuristics (Right)
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("Pathway Visualization")
        
        # Visualization height control and refresh
        viz_col1, viz_col2, viz_col3 = st.columns([1, 1, 1])
        with viz_col1:
            viz_height = st.slider("Height (px)", 300, 800, p4_state['viz_height'], step=50, key="p4_viz_height")
            p4_state['viz_height'] = viz_height
        with viz_col2:
            if st.button("Refresh", use_container_width=True, key="p4_refresh_btn"):
                p4_state['viz_cache'] = {}  # Clear cache to force re-render
                st.rerun()
        with viz_col3:
            st.empty()  # Placeholder for balanced layout

        # Render graphviz visualization
        svg_bytes = cache.get(sig, {}).get("svg")

        if svg_bytes is None:
            g = build_graphviz_from_nodes(nodes_for_viz, "TD")
            if g:
                new_svg = render_graphviz_bytes(g, "svg")
                cache[sig] = {"svg": new_svg}
                svg_bytes = new_svg
        # Keep cache bounded to the latest signature only
        p4_state['viz_cache'] = {sig: cache.get(sig, {})}

        # Fullscreen button - opens SVG in new window
        if svg_bytes:
            import base64
            svg_encoded = base64.b64encode(svg_bytes).decode('utf-8')
            svg_data_for_popup = f"data:image/svg+xml;base64,{svg_encoded}"

            popup_js = f"""
            <script>
            function openFullscreen() {{
                var w = window.open('', '_blank', 'width=1200,height=900,resizable=yes,scrollbars=yes');
                if (w) {{
                    w.document.write('<html><head><title>Pathway Visualization - Fullscreen</title>');
                    w.document.write('<style>body{{margin:0;padding:20px;background:#e8f5e9;text-align:center;}}img{{max-width:100%;height:auto;display:block;margin:0 auto;border:2px solid #5D4037;border-radius:8px;}}</style>');
                    w.document.write('</head><body>');
                    w.document.write('<h2 style="color:#5D4037;">Clinical Pathway Visualization</h2>');
                    w.document.write('<img src="{svg_data_for_popup}" alt="Pathway Visualization" />');
                    w.document.write('</body></html>');
                    w.document.close();
                }} else {{
                    alert('Popup blocked! Please allow popups for this site to use Fullscreen mode.');
                }}
            }}
            </script>
            """
            components.html(popup_js, height=0)
            if st.button("Fullscreen ↗", use_container_width=True, key="p4_fullscreen_btn"):
                components.html(popup_js + '<script>openFullscreen();</script>', height=0)
        else:
            st.button("Fullscreen ↗", use_container_width=True, disabled=True, key="p4_fullscreen_btn_disabled")

        # Validate and render SVG with proper width parameter
        if svg_bytes and isinstance(svg_bytes, bytes) and len(svg_bytes) > 0:
            try:
                st.image(svg_bytes, width=None)
            except Exception as e:
                st.warning(f"Unable to render SVG image. {str(e)[:100]}")
        else:
            st.warning("Unable to render pathway visualization. Check node data or try Fullscreen.")
        
        # Download buttons (DOT and SVG formats)
        st.markdown("**Export Formats:**")
        col_dl_dot, col_dl_svg = st.columns(2)
        dot_text = dot_from_nodes(nodes_for_viz, "TD")
        with col_dl_dot:
            st.download_button("DOT", dot_text, file_name="pathway.dot", mime="text/vnd.graphviz", width="stretch")

        with col_dl_svg:
            if svg_bytes and isinstance(svg_bytes, bytes) and len(svg_bytes) > 0:
                st.download_button("SVG (Editable)", svg_bytes, file_name="pathway.svg", mime="image/svg+xml", width="stretch")
            else:
                st.caption("SVG unavailable")
        
        # Edit pathway data with Node ID column - changes auto-invalidate visualization cache
        with st.expander("Edit Pathway Data", expanded=False):
            df_p4 = pd.DataFrame(nodes)
            # Add node ID column if not present
            if 'node_id' not in df_p4.columns:
                df_p4.insert(0, 'node_id', range(1, len(df_p4) + 1))
            else:
                df_p4['node_id'] = range(1, len(df_p4) + 1)
            
            edited_p4 = st.data_editor(df_p4, num_rows="dynamic", key="p4_editor", width="stretch")
            if not df_p4.equals(edited_p4):
                # Remove node_id before saving (it's display-only)
                if 'node_id' in edited_p4.columns:
                    edited_p4 = edited_p4.drop('node_id', axis=1)
                st.session_state.data['phase3']['nodes'] = edited_p4.to_dict('records')
                p4_state['viz_cache'] = {}  # Clear visualization cache to force re-render with new node data
                st.success("Nodes updated. Flowchart will refresh automatically.")
                st.rerun()
    
    with col_right:
        st.subheader("Nielsen's Heuristics")
        
        # Display all heuristics with definitions
        st.markdown("**Evaluation Criteria:**")
        for heuristic_key in sorted(HEURISTIC_DEFS.keys()):
            definition = HEURISTIC_DEFS[heuristic_key]
            st.caption(f"**{heuristic_key}:** {definition}")
        
        st.divider()

        # Manual trigger to generate or retry heuristics
        h_data = p4_state.get('heuristics_data', {})
        auto_done = p4_state.get('auto_heuristics_done', False)
        btn_label = "Run heuristics" if not auto_done else "Retry heuristics"

        if st.button(btn_label, use_container_width=True, key="p4_run_heuristics_btn"):
            with ai_activity("Analyzing usability heuristics…"):
                prompt = f"""
                Analyze the following clinical decision pathway for Nielsen's 10 Usability Heuristics.
                For each heuristic (H1-H10), provide a specific, actionable critique and suggestion.
                Pathway nodes: {json.dumps(nodes)}
                Return ONLY a JSON object with keys H1-H10.
                """
                res = get_gemini_response(prompt, json_mode=True)
                if res:
                    p4_state['heuristics_data'] = res
                    h_data = res
                p4_state['auto_heuristics_done'] = True

        if not h_data:
            styled_info("No heuristics yet. Click 'Run heuristics' to analyze this pathway.")
        else:
            # Batch Apply All Heuristics
            if st.button("Apply All Heuristics", use_container_width=True, key="p4_apply_all_heuristics_btn"):
                # Snapshot current state for undo
                p4_state.setdefault('nodes_history', []).append(copy.deepcopy(nodes))
                
                with ai_activity("Applying all 10 heuristics…"):
                    # Aggregate all H1-H10 recommendations into a single prompt
                    all_recommendations = "\n".join([
                        f"{hkey}: {h_data[hkey]}" 
                        for hkey in sorted(h_data.keys())
                    ])
                    
                    prompt_apply_all = f"""
                    Update the clinical pathway by applying ALL of these usability recommendations together.
                    Consider how they interact and create a cohesive, improved pathway.
                    
                    All heuristic recommendations:
                    {all_recommendations}
                    
                    Current pathway: {json.dumps(nodes)}
                    
                    Return ONLY the updated JSON array of nodes incorporating all recommendations.
                    """
                    
                    new_nodes = get_gemini_response(prompt_apply_all, json_mode=True)
                    if new_nodes and isinstance(new_nodes, list):
                        st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                        # Reset flag to allow heuristics refresh after batch apply
                        p4_state['auto_heuristics_done'] = False
                        st.success("Applied all heuristics")
                        st.rerun()

        st.divider()

        # Display heuristics with per-item actions (collapsible expanders)
        if h_data:
            st.markdown("**AI Recommendations** (click to expand):")
            for heuristic_key in sorted(h_data.keys()):
                insight = h_data[heuristic_key]
                definition = HEURISTIC_DEFS.get(heuristic_key, "No definition available.")

                # Collapsible expander with heuristic title
                with st.expander(f"{heuristic_key}", expanded=False):
                    # Display definition with CarePathIQ styling (light teal background)
                    st.markdown(f"""
                    <div style="padding: 10px; background-color: #A9EED1; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #5D4037;">
                        <strong style="color: #5D4037;">Definition:</strong><br/>
                        <span style="color: #333; font-size: 0.95em;">{definition}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # AI Recommendation in info box
                    st.info(insight)

                    # Refine note (optional)
                    refine_note = st.text_area(
                        f"Custom note for {heuristic_key}",
                        value="",
                        key=f"p4_refine_note_{heuristic_key}",
                        placeholder="Optional: Add specific context or changes",
                        height=80
                    )

                    # Action buttons for this heuristic (side by side)
                    act_left, act_right = st.columns([1, 1])
                    
                    with act_left:
                        if st.button(f"Apply {heuristic_key}", key=f"p4_apply_{heuristic_key}", use_container_width=True):
                            # Snapshot current nodes for undo
                            p4_state.setdefault('nodes_history', []).append(copy.deepcopy(nodes))
                            with ai_activity(f"Applying {heuristic_key}…"):
                                prompt_apply = f"""
                                Update the clinical pathway by applying this specific usability recommendation.
                                Heuristic {heuristic_key} recommendation: {insight}
                                Current pathway: {json.dumps(nodes)}
                                Return ONLY the updated JSON array of nodes.
                                """
                                new_nodes = get_gemini_response(prompt_apply, json_mode=True)
                                if new_nodes and isinstance(new_nodes, list):
                                    st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                                    st.success(f"Applied {heuristic_key}")
                                    st.rerun()
                    
                    with act_right:
                        if st.button(f"Refine {heuristic_key}", key=f"p4_refine_{heuristic_key}", use_container_width=True):
                            # Snapshot for undo
                            p4_state.setdefault('nodes_history', []).append(copy.deepcopy(nodes))
                            user_note = refine_note.strip()
                            with ai_activity(f"Refining via {heuristic_key}…"):
                                prompt_refine = f"""
                                Refine the clinical pathway using this heuristic and user note.
                                Heuristic {heuristic_key} recommendation: {insight}
                                User note: {user_note if user_note else '(none)'}
                                Current pathway: {json.dumps(nodes)}
                                Return ONLY the updated JSON array of nodes.
                                """
                                new_nodes = get_gemini_response(prompt_refine, json_mode=True)
                                if new_nodes and isinstance(new_nodes, list):
                                    st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                                    st.success(f"Refined via {heuristic_key}")
                                    st.rerun()
    
    st.divider()
    
    # CUSTOM REFINEMENT SECTION
    st.subheader("Custom Refinement")
    custom_ref = st.text_area(
        "Describe your refinement",
        placeholder="E.g., 'Add more specific diagnostic thresholds' or 'Simplify decision tree paths'...",
        key="p4_custom_ref",
        height=80
    )
    
    # Reset the refinement applied flag if text area content changes
    if 'p4_last_custom_ref' not in st.session_state:
        st.session_state['p4_last_custom_ref'] = ""
    
    if custom_ref != st.session_state['p4_last_custom_ref']:
        st.session_state['p4_refinement_applied'] = False
        st.session_state['p4_last_custom_ref'] = custom_ref
    
    col_refine, col_undo = st.columns([1, 1])
    with col_refine:
        # Check if refinements were just applied in this session
        refinement_applied = st.session_state.get('p4_refinement_applied', False)
        
        # Determine button type and label
        button_type = "primary" if refinement_applied else "secondary"
        button_label = "Applied" if refinement_applied else "Apply Refinements"
        
        if st.button(button_label, type=button_type, use_container_width=True, key="p4_apply_ref"):
            if not refinement_applied:  # Only apply if not already applied
                if custom_ref.strip():
                    if 'nodes_history' not in st.session_state.data['phase4']:
                        st.session_state.data['phase4']['nodes_history'] = []
                    st.session_state.data['phase4']['nodes_history'].append(copy.deepcopy(nodes))
                    
                    with ai_activity("Applying refinements…"):
                        p_custom = f"""
                        Update this clinical pathway based on user feedback:
                        {custom_ref}
                        
                        Current pathway: {json.dumps(nodes)}
                        
                        Return ONLY the updated JSON array.
                        """
                        new_nodes = get_gemini_response(p_custom, json_mode=True)
                        if new_nodes and isinstance(new_nodes, list):
                            st.session_state.data['phase3']['nodes'] = harden_nodes(new_nodes)
                            st.session_state['p4_refinement_applied'] = True
                            st.success("Refinements applied")
                            st.rerun()
                else:
                    st.warning("Please describe your refinement first.")
    
    with col_undo:
        if p4_state.get('nodes_history'):
            if st.button("Undo Last Change", width="stretch", key="p4_undo_btn"):
                old_nodes = p4_state['nodes_history'].pop()
                st.session_state.data['phase3']['nodes'] = old_nodes
                st.success("Change undone")
                st.rerun()
    
    render_bottom_navigation()
    st.stop()

# --- PHASE 5 ---
elif "Phase 5" in phase:
    # Import Phase 5 helpers
    try:
        from phase5_helpers import (
            generate_expert_form_html,
            generate_beta_form_html,
            create_phase5_executive_summary_docx,
            ensure_carepathiq_branding
        )
        from education_template import create_education_module_template
    except ImportError:
        st.error("Phase 5 helpers not found. Please ensure phase5_helpers.py and education_template.py are in the workspace.")
        st.stop()
    
    st.title("Phase 5: Operationalize")
    st.markdown("""
    ### Download Shareable Files
    
    Generate standalone HTML files and Word documents that users can download and share directly.
    **No hosting required** — files work offline in any browser.
    """)
    
    cond = st.session_state.data['phase1']['condition'] or "Pathway"
    nodes = st.session_state.data['phase3']['nodes'] or []
    
    st.divider()
    
    # Configuration
    st.subheader("Configuration")
    col_aud, col_org = st.columns([1, 1])
    with col_aud:
        audience = st.text_input(
            "Target Audience",
            value=st.session_state.get("p5_audience", "Clinical Team"),
            placeholder="e.g., Physicians, Nurses, Pharmacists",
            key="p5_audience"
        )
    with col_org:
        organization = st.text_input(
            "Organization Name",
            value=st.session_state.get("p5_organization", "CarePathIQ"),
            placeholder="Your Hospital/Institution",
            key="p5_organization"
        )

    # Quick audience examples per deliverable to speed setup
    with st.expander("Target Audience Examples", expanded=False):
        st.caption("Click to auto-fill the audience field above.")
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            if st.button("Expert Panel", key="aud_expert", use_container_width=True):
                st.session_state.p5_audience = "Clinical Experts (EM, Cardiology, Pharmacy)"
                st.rerun()
        with e2:
            if st.button("Beta Testing", key="aud_beta", use_container_width=True):
                st.session_state.p5_audience = "ED Clinicians (Physicians, RNs), APPs, Pharmacists"
                st.rerun()
        with e3:
            if st.button("Education Module", key="aud_edu", use_container_width=True):
                st.session_state.p5_audience = "Clinical Team (Residents, RNs, APPs)"
                st.rerun()
        with e4:
            if st.button("Exec Summary", key="aud_exec", use_container_width=True):
                st.session_state.p5_audience = "Hospital & Service-Line Leadership"
                st.rerun()
    
    st.divider()

    
    st.divider()
    
    # ============================================================
    # 1. EXPERT PANEL FEEDBACK FORM
    # ============================================================
    st.subheader("1. Expert Panel Feedback Form")
    st.caption("Share with clinical experts for pathway review")
    
    col_exp1, col_exp2 = st.columns([2, 1])
    with col_exp1:
        st.markdown("Collects structured feedback on each pathway node. Reviewers download responses as CSV and email back.")
        # Quick audience presets for this deliverable
        exp_c1, exp_c2, exp_c3 = st.columns(3)
        with exp_c1:
            if st.button("Clinician Experts", key="exp_aud1", use_container_width=True):
                st.session_state.p5_audience = "Clinical Experts (EM, Cardiology, Pharmacy)"; st.rerun()
        with exp_c2:
            if st.button("Governance Committee", key="exp_aud2", use_container_width=True):
                st.session_state.p5_audience = "Pathway Governance Committee"; st.rerun()
        with exp_c3:
            if st.button("Quality & Safety", key="exp_aud3", use_container_width=True):
                st.session_state.p5_audience = "Quality & Patient Safety Leaders"; st.rerun()
    with col_exp2:
        if st.button("Generate (5-10 sec)", key="gen_expert", use_container_width=True):
            with ai_activity("Generating expert feedback form..."):
                expert_html = generate_expert_form_html(
                    condition=cond,
                    nodes=nodes,
                    audience=audience,
                    organization=organization
                )
                st.session_state.data['phase5']['expert_html'] = expert_html
                st.success("Form generated!")
    
    if st.session_state.data['phase5'].get('expert_html'):
        col_view, col_dl = st.columns([1, 1])
        with col_view:
            expert_preview_active = st.session_state.get('show_expert_preview', False)
            preview_btn_label = "Hide Preview" if expert_preview_active else "Preview"
            preview_btn_type = "primary" if expert_preview_active else "secondary"
            if st.button(preview_btn_label, key="view_expert_form", type=preview_btn_type, use_container_width=True):
                st.session_state['show_expert_preview'] = not expert_preview_active
                st.rerun()
        
        with col_dl:
            st.download_button(
                "Download HTML",
                st.session_state.data['phase5']['expert_html'],
                f"ExpertPanelFeedback_{cond.replace(' ', '_')}.html",
                "text/html",
                use_container_width=True
            )
        
        if st.session_state.get('show_expert_preview'):
            with st.expander("Form Preview", expanded=True):
                components.html(
                    st.session_state.data['phase5']['expert_html'],
                    height=600,
                    scrolling=True
                )
    
    st.divider()
    
    # ============================================================
    # 2. BETA TESTING FEEDBACK FORM
    # ============================================================
    st.subheader("2. Beta Testing Feedback Form")
    st.caption("Share with users testing the pathway in real-world settings")
    
    col_beta1, col_beta2 = st.columns([2, 1])
    with col_beta1:
        st.markdown("Usability testing form focused on clarity, workflow fit, and implementation barriers. Download responses as CSV.")
        beta_c1, beta_c2, beta_c3 = st.columns(3)
        with beta_c1:
            if st.button("ED Team", key="beta_aud1", use_container_width=True):
                st.session_state.p5_audience = "ED Clinicians (Physicians, RNs), APPs, Pharmacists"; st.rerun()
        with beta_c2:
            if st.button("Inpatient Nursing", key="beta_aud2", use_container_width=True):
                st.session_state.p5_audience = "Inpatient Nursing Staff"; st.rerun()
        with beta_c3:
            if st.button("Primary Care", key="beta_aud3", use_container_width=True):
                st.session_state.p5_audience = "Primary Care Team"; st.rerun()
    with col_beta2:
        if st.button("Generate (5-10 sec)", key="gen_beta", use_container_width=True):
            with ai_activity("Generating beta testing form..."):
                beta_html = generate_beta_form_html(
                    condition=cond,
                    nodes=nodes,
                    audience=audience,
                    organization=organization
                )
                st.session_state.data['phase5']['beta_html'] = beta_html
                st.success("Form generated!")
    
    if st.session_state.data['phase5'].get('beta_html'):
        col_view, col_dl = st.columns([1, 1])
        with col_view:
            beta_preview_active = st.session_state.get('show_beta_preview', False)
            preview_btn_label = "Hide Preview" if beta_preview_active else "Preview"
            preview_btn_type = "primary" if beta_preview_active else "secondary"
            if st.button(preview_btn_label, key="view_beta_form", type=preview_btn_type, use_container_width=True):
                st.session_state['show_beta_preview'] = not beta_preview_active
                st.rerun()
        
        with col_dl:
            st.download_button(
                "Download HTML",
                st.session_state.data['phase5']['beta_html'],
                f"BetaTestingFeedback_{cond.replace(' ', '_')}.html",
                "text/html",
                use_container_width=True
            )
        
        if st.session_state.get('show_beta_preview'):
            with st.expander("Form Preview", expanded=True):
                components.html(
                    st.session_state.data['phase5']['beta_html'],
                    height=600,
                    scrolling=True
                )
    
    st.divider()
    
    # ============================================================
    # 3. EDUCATION MODULE
    # ============================================================
    st.subheader("3. Interactive Education Module")
    st.caption("Share with clinical team for training. Users complete quizzes and download certificate.")
    
    col_edu1, col_edu2 = st.columns([2, 1])
    with col_edu1:
        st.markdown("Self-contained learning module with interactive quizzes and certificate of completion. Works offline in any browser.")
        edu_c1, edu_c2, edu_c3 = st.columns(3)
        with edu_c1:
            if st.button("Residents & Fellows", key="edu_aud1", use_container_width=True):
                st.session_state.p5_audience = "Residents and Fellows"; st.rerun()
        with edu_c2:
            if st.button("Nursing Staff", key="edu_aud2", use_container_width=True):
                st.session_state.p5_audience = "Nursing Staff"; st.rerun()
        with edu_c3:
            if st.button("APPs", key="edu_aud3", use_container_width=True):
                st.session_state.p5_audience = "Advanced Practice Providers (NP/PA)"; st.rerun()
    with col_edu2:
        if st.button("Generate (10-15 sec)", key="gen_edu", use_container_width=True):
            with ai_activity("Generating education module..."):
                # Create default modules if none exist
                edu_modules = [
                    {
                        "title": f"Module 1: {cond} Overview",
                        "content": f"<p>This module introduces the clinical presentation and epidemiology of {cond}.</p><p><strong>Key Topics:</strong></p><ul><li>Definition and prevalence</li><li>Risk factors and pathophysiology</li><li>Clinical presentation</li><li>Initial assessment approach</li></ul>",
                        "learning_objectives": [
                            f"Define {cond} and describe its clinical relevance",
                            "Identify key risk factors and pathophysiologic mechanisms",
                            "Recognize presenting symptoms and clinical findings"
                        ],
                        "quiz": [
                            {
                                "question": f"Which of the following is a primary characteristic of {cond}?",
                                "options": ["Clinical finding A", "Clinical finding B", "Clinical finding C", "Clinical finding D"],
                                "correct": 0
                            }
                        ]
                    },
                    {
                        "title": "Module 2: Diagnostic Approach",
                        "content": "<p>Evidence-based diagnostic workup and interpretation.</p><p><strong>Diagnostic Strategy:</strong></p><ul><li>Initial testing</li><li>Advanced investigations</li><li>Diagnostic accuracy</li><li>When to treat vs. observe</li></ul>",
                        "learning_objectives": [
                            "Select appropriate diagnostic tests based on clinical presentation",
                            "Interpret test results and understand their limitations",
                            "Apply diagnostic criteria for confirmation"
                        ],
                        "quiz": [
                            {
                                "question": "Which diagnostic test has the highest sensitivity?",
                                "options": ["Test A", "Test B", "Test C", "Test D"],
                                "correct": 1
                            }
                        ]
                    },
                    {
                        "title": "Module 3: Treatment & Management",
                        "content": "<p>Evidence-based treatment strategies and clinical decision-making.</p><p><strong>Management Approach:</strong></p><ul><li>First-line treatments</li><li>Escalation protocols</li><li>Monitoring parameters</li><li>Adverse effect management</li></ul>",
                        "learning_objectives": [
                            "Apply evidence-based treatment recommendations",
                            "Manage treatment-related complications",
                            "Monitor therapeutic response"
                        ],
                        "quiz": [
                            {
                                "question": "What is the first-line intervention?",
                                "options": ["Option A", "Option B", "Option C", "Option D"],
                                "correct": 2
                            }
                        ]
                    }
                ]
                
                edu_html = create_education_module_template(
                    condition=cond,
                    topics=edu_modules,
                    organization=organization,
                    learning_objectives=[
                        f"Understand the clinical presentation and epidemiology of {cond}",
                        "Apply evidence-based diagnostic and treatment strategies",
                        f"Recognize complications and implement safety measures for {cond}",
                        "Communicate effectively with the interdisciplinary team"
                    ]
                )
                st.session_state.data['phase5']['edu_html'] = edu_html
                st.success("Module generated!")
    
    if st.session_state.data['phase5'].get('edu_html'):
        col_view, col_dl = st.columns([1, 1])
        with col_view:
            edu_preview_active = st.session_state.get('show_edu_preview', False)
            preview_btn_label = "Hide Preview" if edu_preview_active else "Preview"
            preview_btn_type = "primary" if edu_preview_active else "secondary"
            if st.button(preview_btn_label, key="view_edu_form", type=preview_btn_type, use_container_width=True):
                st.session_state['show_edu_preview'] = not edu_preview_active
                st.rerun()
        
        with col_dl:
            st.download_button(
                "Download HTML",
                st.session_state.data['phase5']['edu_html'],
                f"EducationModule_{cond.replace(' ', '_')}.html",
                "text/html",
                use_container_width=True
            )
        
        if st.session_state.get('show_edu_preview'):
            with st.expander("Module Preview", expanded=True):
                components.html(
                    st.session_state.data['phase5']['edu_html'],
                    height=700,
                    scrolling=True
                )
    
    st.divider()
    
    # ============================================================
    # 4. EXECUTIVE SUMMARY
    # ============================================================
    st.subheader("4. Executive Summary Document")
    st.caption("Share with hospital leadership")
    
    col_exec1, col_exec2 = st.columns([2, 1])
    with col_exec1:
        st.markdown("Word document with project overview, evidence summary, pathway design, and implementation roadmap.")
    with col_exec2:
        if st.button("Generate (8-12 sec)", key="gen_exec", use_container_width=True):
            with ai_activity("Generating executive summary..."):
                doc = create_phase5_executive_summary_docx(
                    st.session_state.data,
                    cond
                )
                if doc:
                    st.session_state.data['phase5']['exec_doc'] = doc
                    st.success("Summary generated!")
                else:
                    st.error("python-docx not installed. Please install with: pip install python-docx")
    
    if st.session_state.data['phase5'].get('exec_doc'):
        st.download_button(
            "Download Word Document",
            st.session_state.data['phase5']['exec_doc'],
            f"ExecutiveSummary_{cond.replace(' ', '_')}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
    
    st.divider()
    
    # ============================================================
    # SHARING TIP & BULK DOWNLOAD
    # ============================================================
    styled_info("<b>Sharing Tip:</b> All HTML files can be shared as email attachments. End users can download their form responses as CSV files or certificates as PDF files directly from their browser — no server required.")
    
    # Bulk download option
    if (st.session_state.data['phase5'].get('expert_html') and 
        st.session_state.data['phase5'].get('beta_html') and 
        st.session_state.data['phase5'].get('edu_html') and 
        st.session_state.data['phase5'].get('exec_doc')):
        
        st.divider()
        st.subheader("Bulk Download")
        
        if st.button("Download All Deliverables as ZIP", use_container_width=True, type="primary"):
            import zipfile
            from io import BytesIO
            
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add HTML files
                zip_file.writestr(
                    f"ExpertPanelFeedback_{cond.replace(' ', '_')}.html",
                    st.session_state.data['phase5']['expert_html']
                )
                zip_file.writestr(
                    f"BetaTestingFeedback_{cond.replace(' ', '_')}.html",
                    st.session_state.data['phase5']['beta_html']
                )
                zip_file.writestr(
                    f"EducationModule_{cond.replace(' ', '_')}.html",
                    st.session_state.data['phase5']['edu_html']
                )
                # Add Word doc
                zip_file.writestr(
                    f"ExecutiveSummary_{cond.replace(' ', '_')}.docx",
                    st.session_state.data['phase5']['exec_doc']
                )
            
            zip_buffer.seek(0)
            st.download_button(
                "Click to Download ZIP",
                zip_buffer,
                f"CarePathIQ_Deliverables_{cond.replace(' ', '_')}.zip",
                "application/zip",
                use_container_width=True
            )
    
    st.divider()
    
    # ============================================================
    # SHARING INSTRUCTIONS
    # ============================================================
    st.subheader("How to Share & Collect Feedback")
    
    with st.expander("Expert Panel Workflow", expanded=False):
        st.markdown("""
        1. **Download** ExpertPanelFeedback.html file
        2. **Share** the file (email, shared folder, LMS, etc.)
        3. **Expert** opens in any browser and provides feedback
        4. **Expert clicks** "Download Responses (CSV)"
        5. **Expert emails** CSV file back to you
        6. **You import** CSV into your analysis tool
        """)
    
    with st.expander("Beta Testing Workflow", expanded=False):
        st.markdown("""
        1. **Download** BetaTestingFeedback.html file
        2. **Share** with real users testing the pathway
        3. **Users** open in browser and complete form
        4. **Users click** "Download Responses (CSV)"
        5. **Users email** CSV back to you
        6. **Aggregate** feedback to identify usability issues
        """)
    
    with st.expander("Education Module Workflow", expanded=False):
        st.markdown("""
        1. **Download** EducationModule.html file
        2. **Host** on your institution's server or LMS
        3. **Share** link with clinical staff
        4. **Staff** complete interactive modules
        5. **Staff** take quizzes (must score 100%)
        6. **Staff** download/print certificate of completion
        7. **No email submission needed** — certificates are self-contained
        """)
    
    with st.expander("Executive Summary Workflow", expanded=False):
        st.markdown("""
        1. **Download** ExecutiveSummary.docx
        2. **Edit** in Microsoft Word to customize
        3. **Share** directly with hospital leadership
        4. **Use for** funding approval, policy alignment, go-live planning
        """)
    
    render_bottom_navigation()
    st.stop()

st.markdown(COPYRIGHT_HTML_FOOTER, unsafe_allow_html=True)