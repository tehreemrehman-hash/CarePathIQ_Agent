import streamlit as st
import streamlit.components.v1 as components
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

# --- NEW IMPORTS FOR PHASE 5 ---
try:
    from docx import Document
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:
    st.error("⚠️ Missing Libraries: Please run `pip install python-docx python-pptx` to use the new Phase 5 features.")

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

    /* 1b. DOWNLOAD BUTTONS -> Dark Brown (#5D4037) */
    div.stDownloadButton > button {
        background-color: #5D4037 !important; 
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #3E2723 !important;
        color: white !important;
    }
    div.stDownloadButton > button:active {
        background-color: #3E2723 !important;
        color: white !important;
    }

    /* 1c. PRIMARY BUTTONS (Navigation) -> Mint Green (#00897B) */
    /* This targets buttons with type="primary" */
    div.stButton > button[kind="primary"] {
        background-color: #00897B !important;
        border-color: #00897B !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #00695C !important;
        border-color: #00695C !important;
    }
    div.stButton > button[kind="primary"]:active {
        background-color: #00695C !important;
        border-color: #00695C !important;
    }

    /* 1d. LINK BUTTONS (Open in PubMed) -> Dark Brown (#5D4037) */
    a[kind="primary"] {
        background-color: #5D4037 !important;
        border-color: #5D4037 !important;
        color: white !important;
    }
    a[kind="primary"]:hover {
        background-color: #3E2723 !important;
        border-color: #3E2723 !important;
    }
    
    /* 2. RADIO BUTTONS (The Little Circles) */
    /* Unchecked: White background, Brown border */
    div[role="radiogroup"] label > div:first-child {
        background-color: white !important;
        border-color: #5D4037 !important;
    }
    
    /* Checked: Brown background, Brown border */
    div[role="radiogroup"] label[data-checked="true"] > div:first-child {
        background-color: #5D4037 !important;
        border-color: #5D4037 !important;
    }
    
    /* Checked: Inner dot - make it white for contrast */
    div[role="radiogroup"] label[data-checked="true"] > div:first-child > div {
        background-color: white !important;
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
    
    # Try to load from secrets, otherwise empty
    default_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            default_key = st.secrets["GEMINI_API_KEY"]
    except FileNotFoundError:
        pass

    gemini_api_key = st.text_input("Gemini API Key", value=default_key, type="password", help="Use Google AI Studio Key")
    
    # Default to gemini-2.5-flash as requested, but include fallbacks
    model_choice = st.selectbox("AI Agent Model", ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"], index=0)
    
    if gemini_api_key:
        gemini_api_key = gemini_api_key.strip() # Remove any leading/trailing whitespace
        genai.configure(api_key=gemini_api_key)
        st.success(f"Connected: {model_choice}")
        
    st.divider()
    
    # --- NAVIGATION & PROGRESS ---
    PHASES = [
        "Phase 1: Scoping & Charter", 
        "Phase 2: Rapid Evidence Appraisal", 
        "Phase 3: Decision Science", 
        "Phase 4: Heuristic Evaluation", 
        "Phase 5: Operationalize"
    ]
    
    # Determine current index
    current_label = st.session_state.get('current_phase_label', PHASES[0])
    try:
        curr_idx = PHASES.index(current_label)
    except ValueError:
        curr_idx = 0
        
    # Previous Button (Dark Brown)
    if curr_idx > 0:
        if st.button(f"Previous: {PHASES[curr_idx-1].split(':')[0]}", type="primary", use_container_width=True):
            st.session_state.current_phase_label = PHASES[curr_idx-1]
            st.rerun()
            
    # --- CURRENT PHASE STATUS BOX (Dark Brown) ---
    st.markdown(f"""
    <div style="
        background-color: #5D4037; 
        color: white; 
        padding: 10px; 
        border-radius: 5px; 
        text-align: center;
        font-weight: bold;
        font-size: 0.9em;
        margin-top: 5px;
        margin-bottom: 5px;">
        Current Phase: <br>
        <span style="font-size: 1.1em;">{current_label}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Next Button (Dark Brown)
    if curr_idx < len(PHASES) - 1:
        if st.button(f"Next: {PHASES[curr_idx+1].split(':')[0]}", type="primary", use_container_width=True):
            st.session_state.current_phase_label = PHASES[curr_idx+1]
            st.rerun()

    # Progress Bar
    progress = curr_idx / len(PHASES)
    st.caption(f"Progress Complete: {int(progress*100)}%")
    st.progress(progress)

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
    """Robust AI caller with JSON cleaner and multi-model fallback."""
    if not gemini_api_key: return None
    
    # Define fallback hierarchy
    # We include 'gemini-pro' and other variants because API model names can vary by region/version
    candidates = [
        model_choice,
        "gemini-2.5-flash",
        "gemini-1.5-pro", 
        "gemini-1.5-flash", 
        "gemini-1.0-pro", 
        "gemini-pro", 
        "gemini-1.0-pro-latest",
        "gemini-1.0-pro-001"
    ]
    # Deduplicate preserving order
    candidates = list(dict.fromkeys(candidates))
    
    response = None
    last_error = None

    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            # Relaxed safety for medical terms
            safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
            time.sleep(1) # Prevent 429 errors
            response = model.generate_content(prompt, safety_settings=safety)
            
            if response:
                if model_name != model_choice:
                    st.toast(f"Switched to {model_name} (auto-fallback)", icon="🔄")
                break # Success
        except Exception as e:
            last_error = e
            continue # Try next model

    if not response:
        # Final Hail Mary: Try to dynamically find ANY available Gemini model
        try:
            st.toast("Attempting dynamic model discovery...", icon="🔎")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                    try:
                        model = genai.GenerativeModel(m.name)
                        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
                        response = model.generate_content(prompt, safety_settings=safety)
                        if response:
                            st.toast(f"Found working model: {m.name}", icon="✅")
                            break
                    except: continue
        except Exception as e:
            last_error = f"{last_error} | Dynamic discovery failed: {e}"

    if not response:
        error_msg = str(last_error)
        if "API_KEY_INVALID" in error_msg or "400" in error_msg:
            st.error("🚨 API Key Error: The provided Google Gemini API Key is invalid. Please check for typos or extra spaces, or generate a new key at Google AI Studio.")
        else:
            st.error(f"AI Error: All models failed. Last error: {last_error}")
        return None

    try:
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
        st.error(f"Parsing Error: {e}")
        return None

def search_pubmed(query):
    """Real PubMed API Search."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        # Increased retmax to 20 to get more results
        search_params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': 20}
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
                 key="current_phase_label",
                 label_visibility="collapsed")

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
                - "objectives": list of strings (Must be SMART goals: Specific, Measurable, Achievable, Relevant, Time-bound)
                """
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    st.session_state.suggestions = data
                    st.session_state.suggestions['condition_ref'] = cond_input
                    st.session_state.data['phase1']['inclusion'] = data.get('inclusion', '')
                    st.session_state.data['phase1']['exclusion'] = data.get('exclusion', '')
                    st.session_state.data['phase1']['setting'] = data.get('setting', '')
                    st.session_state.data['phase1']['problem'] = data.get('problem', '')
                    
                    # Handle objectives safely
                    objs = data.get('objectives', [])
                    if isinstance(objs, list):
                        obj_text = "\n".join([f"- {g}" for g in objs])
                    else:
                        obj_text = str(objs)
                        
                    st.session_state.data['phase1']['objectives'] = obj_text
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
                with st.spinner("AI Agent Generating Project Charter..."):
                    prompt = f"Create a formal Project Charter (HTML). Condition: {cond_input}. Inclusion: {inc}. Exclusion: {exc}. Setting: {setting}. Problem: {prob}. Objectives: {obj}. Return HTML body content only. Do not include ```html or ``` markers."
                    charter_content = get_gemini_response(prompt)
                    
                    # Clean up any potential markdown markers if the model ignores instructions
                    charter_content = charter_content.replace('```html', '').replace('```', '').strip()
                    
                    # Wrap for Word Doc
                    word_html = f"""
                    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body {{ font-family: 'Times New Roman', serif; }}
                            h1 {{ color: #00695C; text-align: center; }}
                            h2 {{ color: #2E7D32; border-bottom: 2px solid #2E7D32; }}
                            table {{ border-collapse: collapse; width: 100%; }}
                            td, th {{ border: 1px solid #ddd; padding: 8px; }}
                            /* Remove any unwanted grid lines from main layout if present */
                            .no-border {{ border: none !important; }}
                        </style>
                    </head>
                    <body>
                        {charter_content}
                        <div style="margin-top: 50px; font-size: 0.8em; color: gray; text-align: center; border-top: 1px solid #ddd; padding-top: 10px;">
                            CarePathIQ © 2024 by Tehreem Rehman. Licensed under CC BY-SA 4.0.
                        </div>
                    </body>
                    </html>
                    """
                    st.session_state['charter_doc'] = word_html
        
        if 'charter_doc' in st.session_state:
            st.success("Charter generated successfully!")
            st.download_button(
                label="Download Project Charter (.doc)",
                data=st.session_state['charter_doc'],
                file_name="Project_Charter.doc",
                mime="application/msword"
            )

# ------------------------------------------
# PHASE 2: EVIDENCE
# ------------------------------------------
elif "Phase 2" in phase:
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
            
            # Retrieve Phase 1 context for better specificity
            inc = st.session_state.data['phase1'].get('inclusion', '')
            exc = st.session_state.data['phase1'].get('exclusion', '')
            setting = st.session_state.data['phase1'].get('setting', '')
            problem = st.session_state.data['phase1'].get('problem', '')

            prompt_mesh = f"""
            Act as an expert Medical Librarian. Construct a highly specific and sophisticated PubMed search query using MeSH terms and keywords.
            Base the query on the following clinical context:
            - Condition: {p1_cond}
            - Population/Inclusion: {inc}
            - Exclusion: {exc}
            - Setting: {setting}
            - Clinical Problem: {problem}
            - PICO P: {p}
            - PICO I: {i}
            - PICO O: {o}

            Requirements:
            1. Use correct MeSH terminology (e.g., "Term"[Mesh]).
            2. Use boolean operators (AND, OR, NOT) effectively.
            3. Include relevant keywords for broader coverage where MeSH might be too narrow.
            4. IMPORTANT: Do not make the query too restrictive. Use OR to combine synonyms and MeSH terms for the same concept.
            5. Output ONLY the raw query string, ready to be pasted into PubMed. No explanations.
            """
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
                with st.spinner("AI Agent building sophisticated query..."):
                    # Retrieve Phase 1 context
                    inc = st.session_state.data['phase1'].get('inclusion', '')
                    exc = st.session_state.data['phase1'].get('exclusion', '')
                    setting = st.session_state.data['phase1'].get('setting', '')
                    problem = st.session_state.data['phase1'].get('problem', '')
                    
                    prompt = f"""
                    Act as an expert Medical Librarian. Construct a highly specific and sophisticated PubMed search query using MeSH terms and keywords.
                    Base the query on the following clinical context:
                    - Condition: {p1_cond}
                    - Population/Inclusion: {inc}
                    - Exclusion: {exc}
                    - Setting: {setting}
                    - Clinical Problem: {problem}
                    - PICO P: {p}
                    - PICO I: {i}
                    - PICO O: {o}

                    Requirements:
                    1. Use correct MeSH terminology (e.g., "Term"[Mesh]).
                    2. Use boolean operators (AND, OR, NOT) effectively.
                    3. Include relevant keywords for broader coverage where MeSH might be too narrow.
                    4. IMPORTANT: Do not make the query too restrictive. Use OR to combine synonyms and MeSH terms for the same concept.
                    5. Output ONLY the raw query string, ready to be pasted into PubMed. No explanations.
                    """
                    query = get_gemini_response(prompt)
                    st.session_state.data['phase2']['mesh_query'] = query
                    st.rerun()

    with col2:
        st.markdown("#### Literature Search")
        current_query = st.session_state.data['phase2'].get('mesh_query', '')
        search_q = st.text_area("Search Query", value=current_query, height=100)
        
        col_search, col_open = st.columns([1, 1])
        with col_search:
            grade_tooltip = """
            GRADE (Grading of Recommendations Assessment, Development and Evaluation) is a framework for rating the quality of evidence.
            
            High (A): We are very confident that the true effect lies close to that of the estimate of the effect.
            Moderate (B): We are moderately confident in the effect estimate: The true effect is likely to be close to the estimate of the effect, but there is a possibility that it is substantially different.
            Low (C): Our confidence in the effect estimate is limited: The true effect may be substantially different from the estimate of the effect.
            Very Low (D): We have very little confidence in the effect estimate: The true effect is likely to be substantially different from the estimate of effect.
            """
            if st.button("GRADE Evidence", help=grade_tooltip):
                if search_q:
                    with st.spinner("Searching PubMed & Grading Evidence..."):
                        results = search_pubmed(search_q)
                        if not results:
                            st.warning("No results found via API. Try refining the query or opening directly in PubMed.")
                        else:
                            existing = {e['id'] for e in st.session_state.data['phase2']['evidence']}
                            count_new = 0
                            for r in results:
                                if r['id'] not in existing:
                                    st.session_state.data['phase2']['evidence'].append(r)
                                    count_new += 1
                            
                            if count_new > 0:
                                st.success(f"Imported {count_new} new citations.")
                                # New evidence added? Reset grading flag to trigger auto-analysis
                                st.session_state.auto_run["p2_grade"] = False 
                            else:
                                st.info("No new citations found (duplicates skipped).")

        with col_open:
            if search_q:
                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(search_q)}"
                st.link_button("Open in PubMed ↗", pubmed_url) 
        
        # AUTO-RUN: GRADE ANALYSIS (Dynamic with Prasad 2024 Schema)
        evidence_list = st.session_state.data['phase2']['evidence']
        
        if evidence_list and not st.session_state.auto_run["p2_grade"]:
             with st.spinner("AI Agent analyzing Evidence Certainty (Prasad 2024 Framework)..."):
                 titles = [f"ID {e['id']}: {e['title']}" for e in evidence_list]
                 
                 # ENHANCED PROMPT BASED ON PRASAD 2024
                 prompt = f"""
                 Act as a Clinical Methodologist applying the GRADE framework (Prasad 2024).
                 Analyze the following citations.
                 
                 For each citation, assign a Grade: High, Moderate, Low, or Very Low.
                 CRITICAL: You must determine the grade based on these specific factors:
                 1. Downgrade for: Risk of Bias, Inconsistency, Indirectness, Imprecision, Publication Bias.
                 2. Upgrade (if observational) for: Large Effect, Dose-Response, Plausible Bias direction.
                 
                 Citations to analyze: {json.dumps(titles)}
                 
                 Return a JSON object where keys are the PubMed IDs and values are objects containing 'grade' and 'rationale'.
                 Example format:
                 {{
                    "12345": {{
                        "grade": "Moderate (B)",
                        "rationale": "Downgraded for imprecision (small sample); Upgraded for large effect size."
                    }}
                 }}
                 """
                 
                 grade_data = get_gemini_response(prompt, json_mode=True)
                 
                 if isinstance(grade_data, dict):
                     for e in st.session_state.data['phase2']['evidence']:
                         if e['id'] in grade_data:
                             # robust handling if AI returns string vs dict
                             entry = grade_data[e['id']]
                             if isinstance(entry, dict):
                                 e['grade'] = entry.get('grade', 'Un-graded')
                                 e['rationale'] = entry.get('rationale', 'No rationale provided.')
                             else:
                                 e['grade'] = str(entry)
                                 e['rationale'] = " AI generated simple score."
                     
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

            # Update the Data Editor to show the Rationale
            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            
            # Ensure rationale column exists
            if 'rationale' not in df.columns:
                df['rationale'] = ""

            grade_help = """
            High (A): High confidence in effect estimate.
            Moderate (B): Moderate confidence; true effect likely close.
            Low (C): Limited confidence; true effect may differ.
            Very Low (D): Very little confidence.
            """
            
            edited_df = st.data_editor(df, column_config={
                "title": st.column_config.TextColumn("Title", width="medium", disabled=True),
                "id": st.column_config.TextColumn("ID", disabled=True),
                "url": st.column_config.LinkColumn("Link", disabled=True),
                "grade": st.column_config.SelectboxColumn(
                    "GRADE", 
                    options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
                    help=grade_help, 
                    width="small",
                    required=True
                ),
                "rationale": st.column_config.TextColumn(
                    "GRADE Rationale (Prasad Criteria)",
                    help="Factors: Risk of Bias, Inconsistency, Indirectness, Imprecision",
                    width="large"
                ),
                "citation": st.column_config.TextColumn("Citation", disabled=True),
            }, column_order=["title", "grade", "rationale", "url"], hide_index=True)
            
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            
            if not df.empty:
                csv = edited_df.to_csv(index=False)
                export_widget(csv, "evidence_table.csv", "text/csv", label="Download CSV")

# ------------------------------------------
# PHASE 3: LOGIC
# ------------------------------------------
elif "Phase 3" in phase:
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
             with st.spinner("AI Agent drafting decision model (AHRQ/Philips Framework)..."):
                 
                 # Prepare Evidence Context
                 ev_context = "\n".join([f"- {e.get('title','')} (GRADE: {e.get('grade','Un-graded')})" for e in evidence_list[:5]])
                 
                 # ENHANCED PROMPT BASED ON AHRQ METHODOLOGY (NBK127482)
                 prompt = f"""
                 Act as a Decision Scientist building a Clinical Pathway Model for: {cond}.
                 Adhere to the 'Best Practices for Decision Modeling' (Philips et al., AHRQ).
                 
                 Context:
                 - Evidence Available: {ev_context}
                 
                 INSTRUCTIONS:
                 1. **Define the Pathway Type**: Is this Prevention, Screening, Diagnostic, or Treatment? Structure accordingly.
                 2. **Natural History**: Ensure the flow reflects the biological progression or clinical workflow logic.
                 3. **Node Types**:
                    - 'Start': Entry point (Patient presentation).
                    - 'Decision': A branching point (Test Result / Risk Stratification).
                    - 'Process': An intervention or action (Administer Meds / Surgery).
                    - 'Note': Crucial for **Assumptions** or **Uncertainty** (e.g., "If high bleeding risk, consider X").
                    - 'End': Clinical Outcome (Discharge / Admit / Palliative).
                 
                 4. **Handling Uncertainty**: If evidence is Low GRADE, use a 'Note' node to highlight the assumption being made.
                 
                 Return a JSON List of objects: [{{"type": "Start", "label": "Acute Onset", "evidence": "ID..."}}]
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
                <strong>AI Agent Output:</strong> Decision tree generated. <br>
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
# PHASE 4: USER INTERFACE DESIGN
# ------------------------------------------
elif "Phase 4" in phase:
    st.markdown("### User Interface Design & Heuristics")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Clinical Pathway Visualizer")
        
        nodes = st.session_state.data['phase3']['nodes']
        if nodes:
            try:
                # --- ENHANCED GRAPHVIZ LOGIC FOR YES/NO BRANCHING ---
                graph = graphviz.Digraph()
                graph.attr(rankdir='TB', splines='ortho') # Orthogonal lines for professional look
                graph.attr('node', fontname='Helvetica', fontsize='10')
                
                # 1. Define Nodes with specific shapes/colors matching your template
                for i, n in enumerate(nodes):
                    node_id = str(i)
                    label = n.get('label', '?')
                    node_type = n.get('type', 'Process')
                    
                    if node_type == 'Start':
                        graph.node(node_id, label, shape='oval', style='filled', fillcolor='#D5E8D4', color='#82B366')
                    elif node_type == 'End':
                        graph.node(node_id, label, shape='oval', style='filled', fillcolor='#D5E8D4', color='#82B366')
                    elif node_type == 'Decision':
                        graph.node(node_id, label, shape='diamond', style='filled', fillcolor='#F8CECC', color='#B85450')
                    elif node_type == 'Note':
                        # Note shape (folder-like or note)
                        graph.node(node_id, label, shape='note', style='filled', fillcolor='#DAE8FC', color='#6C8EBF')
                    else: # Process
                        graph.node(node_id, label, shape='box', style='filled', fillcolor='#FFF2CC', color='#D6B656')

                # 2. Define Edges with Logic
                # This simple logic assumes a linear list where:
                # - 'Decision' nodes branch: 
                #     - 'Yes' goes to the immediate next node (i+1)
                #     - 'No' attempts to skip to a logical end or later step (simulated here as i+2 or End)
                # - 'Note' nodes connect to their parent with a dotted line
                
                for i, n in enumerate(nodes):
                    if i < len(nodes) - 1:
                        curr_id = str(i)
                        next_id = str(i + 1)
                        curr_type = n.get('type')
                        
                        if curr_type == 'Decision':
                            # YES Path (Green)
                            graph.edge(curr_id, next_id, label="Yes", color="green", fontcolor="green")
                            
                            # NO Path (Red) - Logic to find a jump or End
                            # For this auto-draft, we connect 'No' to the node AFTER next, or End if none exists
                            if i + 2 < len(nodes):
                                no_target_id = str(i + 2)
                            else:
                                # Create a generic End if needed or link to last
                                no_target_id = str(len(nodes) - 1) 
                            
                            # Avoid self-loops if logic is tight
                            if no_target_id != next_id:
                                graph.edge(curr_id, no_target_id, label="No", color="red", fontcolor="red")
                                
                        elif curr_type == 'Note':
                            # Dotted line to the previous Process/Decision it modifies
                            # Assuming Note comes AFTER the step it describes in your list
                            if i > 0:
                                prev_id = str(i - 1)
                                # Notes are usually attached TO the main flow, so we reverse edge or make it distinct
                                graph.edge(curr_id, prev_id, style="dotted", arrowtail="none", dir="back", constraint="false")
                                # Notes usually don't continue the flow themselves, the flow bypasses them
                                # So we connect i-1 to i+1 directly if i is a Note? 
                                # For simplicity in this linear list view, we just link Note back to parent.
                                # To keep flow continuity:
                                graph.edge(prev_id, next_id) 
                        
                        elif nodes[i+1].get('type') == 'Note':
                            # If next is a note, skip logic handled above
                            pass
                        
                        else:
                            # Standard flow
                            graph.edge(curr_id, next_id)

                st.graphviz_chart(graph)
                
                # --- DOWNLOADS ---
                st.markdown("##### Export Flowchart")
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                     try:
                         png_data = graph.pipe(format='png')
                         st.download_button(
                             label="Download High-Res PNG",
                             data=png_data,
                             file_name="clinical_pathway.png",
                             mime="image/png",
                             type="primary",
                             use_container_width=True
                         )
                     except Exception as e: 
                         st.error(f"PNG Error: {e}")
                with c_dl2:
                     try:
                         svg_data = graph.pipe(format='svg')
                         st.download_button(
                             label="Download SVG (Visio Ready)",
                             data=svg_data,
                             file_name="clinical_pathway.svg",
                             mime="image/svg+xml",
                             type="primary",
                             use_container_width=True
                         )
                     except Exception as e:
                         st.error(f"SVG Error: {e}")
                         
            except Exception as e:
                st.error(f"Graph Visualization Error: {e}")
                st.info("Tip: Ensure your Phase 3 Logic list is populated.")

    with col2:
        st.subheader("Nielsen's Heuristic Analysis")
        
        nodes = st.session_state.data['phase3']['nodes']
        if not nodes:
            st.warning("No pathway logic defined in Phase 3.")
        
        # AUTO-RUN: HEURISTICS
        nodes_json = json.dumps(nodes)
        if nodes and not st.session_state.auto_run["p4_heuristics"]:
             with st.spinner("AI Agent analyzing User Interface Design risks..."):
                 
                 prompt = f"""
                 Act as a UX Researcher specializing in Clinical Decision Support. 
                 Analyze this clinical pathway logic: {nodes_json}
                 
                 Evaluate it against **Jakob Nielsen's 10 Usability Heuristics** (nngroup.com).
                 For each heuristic, provide a specific critique or suggestion for the pathway design.
                 
                 Focus on:
                 - **Match between system and real world**: Do the terms (e.g., '{nodes[0].get('label')}') match clinical mental models?
                 - **Error Prevention**: Are there 'Decision' nodes lacking clear 'No' paths?
                 - **Recognition rather than recall**: Is critical info (dosage, criteria) visible in 'Note' nodes?
                 
                 Return a JSON object: {{ "H1": "insight...", "H2": "insight...", ... "H10": "insight..." }}
                 """
                 
                 risks = get_gemini_response(prompt, json_mode=True)
                 
                 if isinstance(risks, dict): 
                     st.session_state.data['phase4']['heuristics_data'] = risks
                     st.session_state.auto_run["p4_heuristics"] = True
                     st.rerun()

        risks = st.session_state.data['phase4'].get('heuristics_data', {})
        if risks:
            st.markdown("""
            <div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 15px;">
                <strong>AI Design Critique:</strong> Review these insights to improve your pathway's usability.
            </div>
            """, unsafe_allow_html=True)
            
            for k, v in risks.items():
                def_text = HEURISTIC_DEFS.get(k, "Nielsen's Usability Heuristic")
                with st.expander(f"{k}: {v[:50]}...", expanded=False):
                    st.markdown(f"**Principle:** *{def_text}*")
                    st.divider()
                    st.info(v)
            
            if st.button("Refresh Analysis (After Edits)", type="primary", use_container_width=True):
                 st.session_state.auto_run["p4_heuristics"] = False
                 st.rerun()

# ------------------------------------------
# PHASE 5: OPERATIONALIZE
# ------------------------------------------
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("#### Beta Testing")
        
        if st.button("Generate Beta Guide", key="btn_guide"):
             with st.spinner("Generating Guide..."):
                 cond = st.session_state.data['phase1']['condition']
                 prob = st.session_state.data['phase1']['problem']
                 st.session_state.data['phase5']['beta_content'] = get_gemini_response(f"Create Beta Guide (HTML) for {cond}. Context: {prob}.")
        
        if st.session_state.data['phase5']['beta_content']:
             export_widget(st.session_state.data['phase5']['beta_content'], "beta_guide.html", "text/html", label="Download Guide")

    with c2:
        st.markdown("#### Frontline Education")
        
        if st.button("Generate Educational Slides", key="btn_slides"):
            with st.spinner("Generating Slides..."):
                cond = st.session_state.data['phase1']['condition']
                prob = st.session_state.data['phase1']['problem']
                goals = st.session_state.data['phase1']['objectives']
                st.session_state.data['phase5']['slides'] = get_gemini_response(f"Create 5 educational slides (Markdown) for {cond}. Gap: {prob}. Goals: {goals}.")

        if st.session_state.data['phase5']['slides']:
             export_widget(st.session_state.data['phase5']['slides'], "slides.md", label="Download Slides")

    with c3:
        st.markdown("#### EHR Integration")
        
        if st.button("Generate EHR Specs", key="btn_specs"):
            with st.spinner("Generating Specs..."):
                nodes_json = json.dumps(st.session_state.data['phase3']['nodes'])
                st.session_state.data['phase5']['epic_csv'] = get_gemini_response(f"Map nodes {nodes_json} to Epic/OPS tools. Return CSV string.")

        if st.session_state.data['phase5']['epic_csv']:
            export_widget(st.session_state.data['phase5']['epic_csv'], "ops_specs.csv", "text/csv", label="Download CSV")
            
    st.divider()
    
    # EXECUTIVE SUMMARY
    if st.button("Generate Executive Summary", use_container_width=True):
        with st.spinner("Compiling Executive Summary..."):
            # Gather Context
            p1 = st.session_state.data['phase1']
            p2_count = len(st.session_state.data['phase2']['evidence'])
            p3_nodes = len(st.session_state.data['phase3']['nodes'])
            
            prompt = f"""
            Create a C-Suite Executive Summary for the Clinical Pathway: {p1['condition']}.
            
            Sections:
            1. Problem Statement: {p1['problem']}
            2. Objectives: {p1['objectives']}
            3. Evidence Base: {p2_count} citations reviewed.
            4. Pathway Logic: {p3_nodes} steps defined.
            5. Implementation Plan: Beta testing and EHR integration ready.
            
            Format as a professional briefing document.
            """
            summary = get_gemini_response(prompt)
            st.session_state.data['phase5']['exec_summary'] = summary
            
    if st.session_state.data['phase5'].get('exec_summary'):
        st.markdown("### Executive Summary")
        st.markdown(st.session_state.data['phase5']['exec_summary'])
        export_widget(st.session_state.data['phase5']['exec_summary'], "executive_summary.md", label="Download Summary")

# ==========================================
# FOOTER
# ==========================================
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
