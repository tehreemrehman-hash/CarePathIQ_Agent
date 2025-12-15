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
import datetime
from datetime import date, timedelta
import os
import copy
import xml.etree.ElementTree as ET
import altair as alt

# --- GRAPHVIZ PATH FIX ---
# Ensure the system path includes the location of the 'dot' executable
os.environ["PATH"] += os.pathsep + '/usr/bin'

# --- NEW IMPORTS FOR PHASE 5 ---
try:
    from docx import Document
    from docx.shared import Inches as DocxInches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
except ImportError:
    st.error("Missing Libraries: Please run `pip install python-docx python-pptx` to use the new Phase 5 features.")

def calculate_granular_progress():
    """Calculates progress based on completed fields across all phases."""
    if 'data' not in st.session_state: return 0.0
    
    data = st.session_state.data
    total_points = 0
    earned_points = 0
    
    # Phase 1: 6 points (Inputs)
    p1 = data.get('phase1', {})
    for k in ['condition', 'setting', 'inclusion', 'exclusion', 'problem', 'objectives']:
        total_points += 1
        if p1.get(k): earned_points += 1
        
    # Phase 2: 2 points (Query + Evidence)
    p2 = data.get('phase2', {})
    total_points += 1
    if p2.get('mesh_query'): earned_points += 1
    total_points += 1
    if p2.get('evidence'): earned_points += 1
    
    # Phase 3: 3 points (Pathway Nodes - Weighted)
    p3 = data.get('phase3', {})
    total_points += 3
    if p3.get('nodes'): earned_points += 3
    
    # Phase 4: 2 points (Heuristics Analysis)
    p4 = data.get('phase4', {})
    total_points += 2
    if p4.get('heuristics_data'): earned_points += 2
    
    # Phase 5: 3 points (Assets Generated)
    p5 = data.get('phase5', {})
    for k in ['beta_content', 'slides', 'epic_csv']:
        total_points += 1
        if p5.get(k): earned_points += 1
        
    if total_points == 0: return 0.0
    return min(1.0, earned_points / total_points)

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
    /* 1. ALL STANDARD BUTTONS (Primary & Secondary) -> Dark Brown (#5D4037) */
    div.stButton > button, 
    div[data-testid="stButton"] > button,
    button[kind="primary"],
    button[kind="secondary"] {
        background-color: #5D4037 !important; 
        color: white !important;
        border: 1px solid #5D4037 !important;
        border-radius: 5px !important;
    }
    div.stButton > button:hover, 
    div[data-testid="stButton"] > button:hover,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover {
        background-color: #3E2723 !important; 
        border-color: #3E2723 !important;
        color: white !important;
    }
    div.stButton > button:active, 
    div[data-testid="stButton"] > button:active,
    button[kind="primary"]:active,
    button[kind="secondary"]:active {
        background-color: #3E2723 !important;
        border-color: #3E2723 !important;
        color: white !important;
    }

    /* 1b. DOWNLOAD BUTTONS -> Dark Brown (#5D4037) */
    div.stDownloadButton > button {
        background-color: #5D4037 !important; 
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
    }

    /* TOOLTIP STYLING */
    div[data-testid="stTooltipContent"] {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ccc !important;
        font-family: 'Arial', sans-serif !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #3E2723 !important;
        color: white !important;
    }
    div.stDownloadButton > button:active {
        background-color: #3E2723 !important;
        color: white !important;
    }

    /* 1d. LINK BUTTONS (Open in PubMed) -> Dark Brown (#5D4037) */
    a[kind="secondary"] {
        background-color: #5D4037 !important;
        border-color: #5D4037 !important;
        color: white !important;
    }
    a[kind="secondary"]:hover {
        background-color: #3E2723 !important;
        border-color: #3E2723 !important;
    }

    /* 1e. SIDEBAR BUTTONS (Previous/Next) -> Mint Green (#A9EED1) */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #A9EED1 !important;
        color: #5D4037 !important; /* Dark Brown text */
        border: none !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #8FD9BC !important;
        color: #3E2723 !important;
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

    /* 2b. SPINNER (Loading Circle) -> Dark Brown */
    .stSpinner > div {
        border-top-color: #5D4037 !important;
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

    /* Tooltip Background - Force White */
    div[data-testid="stTooltipContent"] {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
    }

    /* Hide the anchor link icons on hover for headers */
    [data-testid="stHeaderAction"] { display: none !important; visibility: hidden !important; opacity: 0 !important; }
    .st-emotion-cache-1629p8f a, h1 a, h2 a, h3 a { display: none !important; pointer-events: none; color: transparent !important; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONFIG ---
with st.sidebar:
    # Clickable Logo (Custom HTML for larger size)
    try:
        with open("CarePathIQ_Logo.png", "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 10px;">
                <a href="https://carepathiq.org/" target="_blank">
                    <img src="data:image/png;base64,{logo_data}" width="220" style="max-width: 100%;">
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.warning("Logo not found.")
    
    st.title("AI Agent")
    st.divider()
    
    # Try to load from secrets, otherwise empty
    default_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            default_key = st.secrets["GEMINI_API_KEY"]
    except FileNotFoundError:
        pass

    gemini_api_key = st.text_input("Gemini API Key", value=default_key, type="password", help="Paste your key from Google AI Studio")
    
    # Default to Auto for best performance
    # User specified models: gemini 2.5 flash, gemini 2.5 flash lite, gemini-2.5-flash-tts, gemini-robotics-er-1.5-preview
    model_options = ["Auto", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash-tts", "gemini-robotics-er-1.5-preview"]
    model_choice = st.selectbox("AI Agent Model", model_options, index=0)
    
    if gemini_api_key:
        gemini_api_key = gemini_api_key.strip() # Remove any leading/trailing whitespace
        genai.configure(api_key=gemini_api_key)
        # Show last 4 chars for verification
        key_suffix = gemini_api_key[-4:] if len(gemini_api_key) > 4 else "****"
        st.success(f"Connected: {model_choice} (Key: ...{key_suffix})")
        
    st.divider()
    
    # --- NAVIGATION & PROGRESS ---
    PHASES = [
        "Phase 1: Scoping & Charter", 
        "Phase 2: Rapid Evidence Appraisal", 
        "Phase 3: Decision Science", 
        "Phase 4: User Interface Design", 
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
        margin-top: 15px;
        margin-bottom: 15px;">
        Current Phase: <br>
        <span style="font-size: 1.1em;">{current_label}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Next Button (Dark Brown)
    if curr_idx < len(PHASES) - 1:
        if st.button(f"Next: {PHASES[curr_idx+1].split(':')[0]}", type="primary", use_container_width=True):
            st.session_state.current_phase_label = PHASES[curr_idx+1]
            st.rerun()

    # Progress Bar (Granular)
    progress = calculate_granular_progress()
    st.caption(f"Overall Completion: {int(progress*100)}%")
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
        "p2_query": False,
        "p2_grade": False,
        "p3_logic": False,
        "p4_heuristics": False,
        "p5_all": False
    }

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def styled_info(text):
    """Custom info box with Pink background and Dark Red text."""
    # Convert markdown bold to HTML bold for correct rendering inside div
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    st.markdown(f"""
    <div style="background-color: #FFE6EE; color: #9E4244; padding: 10px; border-radius: 5px; border: 1px solid #9E4244; margin-bottom: 10px;">
        {formatted_text}
    </div>
    """, unsafe_allow_html=True)

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

def create_word_docx(content_text):
    """Generates a Word Document from text content."""
    try:
        doc = Document()
    except NameError:
        return None # Library not loaded

    # Logo removed per user request
    # if os.path.exists("CarePathIQ_Logo.png"):
    #     try:
    #         doc.add_picture("CarePathIQ_Logo.png", width=DocxInches(2.0))
    #         last_paragraph = doc.paragraphs[-1] 
    #         last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    #     except Exception:
    #         pass

    doc.add_heading('Clinical Pathway: Beta Testing Guide', 0)
    
    # Simple markdown-to-docx parser
    for line in content_text.split('\n'):
        line = line.strip()
        if line.startswith('###'):
            doc.add_heading(line.replace('#', '').strip(), level=2)
        elif line.startswith('##'):
            doc.add_heading(line.replace('#', '').strip(), level=1)
        elif line.startswith('-') or line.startswith('*'):
            doc.add_paragraph(line.replace('-', '').replace('*', '').strip(), style='List Bullet')
        else:
            if line:
                doc.add_paragraph(line)
            
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_ppt_presentation(slides_data, flowchart_img=None):
    """Generates a Professional PowerPoint with branding."""
    try:
        prs = Presentation()
        # Brand Colors
        BROWN = RGBColor(93, 64, 55)   # #5D4037
        TEAL = RGBColor(0, 105, 92)    # #00695C
        GREY = RGBColor(80, 80, 80)
        WHITE = RGBColor(255, 255, 255)
        LIGHT_BG = RGBColor(245, 245, 245)
    except NameError:
        return None
    
    # Helper: Add Footer
    def add_footer(slide, text_color=GREY):
        left = Inches(0.5)
        top = Inches(7.1)
        width = Inches(9)
        height = Inches(0.3)
        
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = "CarePathIQ © 2024 | Confidential Internal Document"
        p.font.size = Pt(9)
        p.font.color.rgb = text_color
        p.font.name = 'Arial'
        p.alignment = PP_ALIGN.CENTER

    # 1. Title Slide (Custom Layout)
    slide = prs.slides.add_slide(prs.slide_layouts[6]) # Blank Layout
    
    # Background Color (Dark Brown)
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BROWN
    
    # Title Text
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(2))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = slides_data.get('title', 'Clinical Pathway Launch')
    p.font.size = Pt(44)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.font.name = 'Arial'
    p.alignment = PP_ALIGN.CENTER
    
    # Subtitle Text
    sub_box = slide.shapes.add_textbox(Inches(1), Inches(4.5), Inches(8), Inches(1))
    tf_sub = sub_box.text_frame
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = f"Target Audience: {slides_data.get('audience', 'General')}\nGenerated by CarePathIQ AI Agent"
    p_sub.font.size = Pt(18)
    p_sub.font.color.rgb = RGBColor(220, 220, 220) # Off-white
    p_sub.font.name = 'Arial'
    p_sub.alignment = PP_ALIGN.CENTER
    
    add_footer(slide, text_color=RGBColor(200, 200, 200))

    # 2. Content Slides
    for slide_info in slides_data.get('slides', []):
        slide = prs.slides.add_slide(prs.slide_layouts[6]) # Blank Layout
        
        # Header Strip
        shape = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(1.2)) # MSO_SHAPE.RECTANGLE = 1
        shape.fill.solid()
        shape.fill.fore_color.rgb = BROWN
        shape.line.fill.background() # No border
        
        # Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = slide_info.get('title', 'Untitled')
        p.font.size = Pt(32)
        p.font.color.rgb = WHITE
        p.font.bold = True
        p.font.name = 'Arial'
        
        # Content Area
        is_flowchart = "Format" in slide_info.get('title', '') and flowchart_img
        
        if is_flowchart:
            if flowchart_img:
                try:
                    flowchart_img.seek(0)
                    # Add Image
                    pic = slide.shapes.add_picture(flowchart_img, Inches(0.5), Inches(1.5), width=Inches(9))
                    
                    # Adjust height if too tall, keeping aspect ratio
                    if pic.height > Inches(5.5):
                        ratio = pic.width / pic.height
                        pic.height = Inches(5.5)
                        pic.width = Inches(5.5 * ratio)
                        # Center horizontally
                        pic.left = Inches((10 - (5.5 * ratio)) / 2)
                        
                except Exception as e:
                    print(f"Image Error: {e}")
        else:
            # Text Content
            content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5.5))
            tf = content_box.text_frame
            tf.word_wrap = True
            
            content_text = str(slide_info.get('content', ''))
            lines = content_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # STRIP MARKDOWN ARTIFACTS
                clean_line = line.replace('**', '').replace('##', '').replace('__', '').replace('`', '')
                
                p = tf.add_paragraph()
                p.text = clean_line
                p.font.name = 'Arial'
                p.font.size = Pt(18)
                p.font.color.rgb = GREY
                p.space_after = Pt(10)
                
                # Simple Bullet Detection
                if clean_line.startswith('- ') or clean_line.startswith('* '):
                    p.text = clean_line[2:]
                    p.level = 1
                elif clean_line[0].isdigit() and clean_line[1] == '.':
                    p.level = 0 # Numbered lists handled as top level for now
                else:
                    p.level = 0

        add_footer(slide)

    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer

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
    try:
        curr_idx = PHASES.index(current_label)
    except ValueError:
        curr_idx = 0
        
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # Callback to update phase safely
    def set_phase(new_phase):
        st.session_state.target_phase = new_phase

    with col1:
        if curr_idx > 0:
            st.button(
                f"← Previous: {PHASES[curr_idx-1].split(':')[0]}", 
                key=f"bottom_prev_{curr_idx}", 
                use_container_width=True,
                on_click=set_phase,
                args=(PHASES[curr_idx-1],)
            )
                
    with col3:
        if curr_idx < len(PHASES) - 1:
            st.button(
                f"Next: {PHASES[curr_idx+1].split(':')[0]} →", 
                key=f"bottom_next_{curr_idx}", 
                type="primary", 
                use_container_width=True,
                on_click=set_phase,
                args=(PHASES[curr_idx+1],)
            )

def get_gemini_response(prompt, json_mode=False, stream_container=None):
    """Robust AI caller with JSON cleaner, multi-model fallback, and streaming."""
    if not gemini_api_key: return None
    
    # Define fallback hierarchy
    # If Auto is selected, prioritize Flash models for speed
    if model_choice == "Auto":
        candidates = [
            "gemini-2.5-flash", 
            "gemini-2.5-flash-lite",
            "gemini-1.5-flash", # Added for speed/stability
            "gemini-robotics-er-1.5-preview",
            "gemini-2.5-flash-tts"
        ]
    else:
        # User selected specific model, try that first, then fallbacks
        candidates = [
            model_choice,
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-2.5-flash-lite"
        ]
    
    # Deduplicate preserving order
    candidates = list(dict.fromkeys(candidates))
    
    response = None
    last_error = None

    for i, model_name in enumerate(candidates):
        try:
            model = genai.GenerativeModel(model_name)
            # Relaxed safety for medical terms
            safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
            
            # Minimal sleep on retries to keep momentum
            if i > 0: time.sleep(0.1) 
            
            # Enable streaming if container provided
            is_stream = stream_container is not None
            response = model.generate_content(prompt, safety_settings=safety, stream=is_stream)
            
            if response:
                if model_choice == "Auto" and i > 0:
                    # Optional: Log which model was actually used in Auto mode if not the first
                    pass 
                elif model_choice != "Auto" and model_name != model_choice:
                    st.toast(f"Switched to {model_name} (auto-fallback)")
                break # Success
        except Exception as e:
            # Prioritize keeping 429 errors (Quota Exceeded) over 404s (Not Found)
            e_str = str(e)
            if "429" in e_str:
                last_error = e
            elif last_error is None or "429" not in str(last_error):
                last_error = e
            continue # Try next model

    if not response:
        # Final Hail Mary: Try standard 1.5 Flash directly instead of slow list_models()
        try:
            fallback_model = "gemini-1.5-flash"
            if fallback_model not in candidates:
                model = genai.GenerativeModel(fallback_model)
                safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
                is_stream = stream_container is not None
                response = model.generate_content(prompt, safety_settings=safety, stream=is_stream)
                if response:
                    st.toast(f"Recovered with: {fallback_model}")
        except Exception as e:
            last_error = f"{last_error} | Final fallback failed: {e}"

    if not response:
        error_msg = str(last_error)
        if "429" in error_msg:
            st.error("**Quota Exceeded (Rate Limit)**: You have hit the free tier limit for Gemini API.")
            styled_info("Please wait a minute before trying again, or use a different API key.")
        elif "404" in error_msg:
            st.error("**Model Not Found**: The selected AI model is not available in your region or API version.")
        elif "API_KEY_INVALID" in error_msg or "400" in error_msg:
            st.error("API Key Error: The provided Google Gemini API Key is invalid. Please check for typos or extra spaces, or generate a new key at Google AI Studio.")
        else:
            st.error(f"AI Error: All models failed. Last error: {error_msg}")
        return None

    try:
        if stream_container:
            text = ""
            for chunk in response:
                if chunk.text:
                    text += chunk.text
                    stream_container.markdown(text + "▌")
            stream_container.markdown(text) # Final render without cursor
        else:
            text = response.text
            
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            # Robust JSON extraction via regex
            match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if match:
                text = match.group()
            
            # Attempt to fix common JSON errors (like invalid escapes)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Fallback: Escape backslashes that aren't already escaped
                # This is a simple heuristic to fix things like "C:\Path" -> "C:\\Path"
                # But we must be careful not to double escape valid escapes like \n or \"
                try:
                    # Regex to find backslashes that are NOT followed by valid escape chars
                    # Valid JSON escapes: ", \, /, b, f, n, r, t, uXXXX
                    # We want to escape \ that is NOT one of these.
                    # This is complex, so a simpler approach is often to just use a permissive parser or try to strip bad chars.
                    # Let's try a simple replace of single backslash with double, but this breaks valid escapes.
                    
                    # Better approach: Use a raw string cleanup or just try to ignore strictness if possible (not in std lib).
                    # Let's try to just strip invalid escapes if they are causing issues, or use a library if available (we don't have one).
                    
                    # Specific fix for the error "Invalid \escape":
                    # Often caused by LaTeX like \frac or file paths.
                    # Let's try to escape backslashes that look like they are part of text.
                    cleaned_text = text.replace('\\', '\\\\') 
                    # But wait, this breaks \n -> \\n which is not a newline anymore.
                    
                    # Let's try a different strategy: If standard load fails, try `eval` (dangerous but effective for Python-like dicts)
                    # ONLY if it looks safe-ish.
                    import ast
                    return ast.literal_eval(text)
                except:
                    pass
                raise # Re-raise original error if fallback fails
        return text
    except Exception as e:
        st.error(f"Parsing Error: {e}")
        return None

def search_pubmed(query):
    """Real PubMed API Search with Abstracts."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        # 1. ESearch to get IDs
        # Increased retmax to 30 to get more results, sorted by relevance
        # Added date filter for last 5 years
        search_params = {
            'db': 'pubmed', 
            'term': f"{query} AND (\"last 5 years\"[dp])", 
            'retmode': 'json', 
            'retmax': 30, 
            'sort': 'relevance'
        }
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            id_list = data.get('esearchresult', {}).get('idlist', [])
        
        if not id_list: return []
        
        # 2. EFetch to get details (XML)
        ids_str = ','.join(id_list)
        fetch_params = {'db': 'pubmed', 'id': ids_str, 'retmode': 'xml'}
        url = base_url + "efetch.fcgi?" + urllib.parse.urlencode(fetch_params)
        
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode()
            
        # 3. Parse XML
        root = ET.fromstring(xml_data)
        citations = []
        pmc_map = {} # Map PMC ID to citation index
        
        for article in root.findall('.//PubmedArticle'):
            try:
                medline = article.find('MedlineCitation')
                article_data = medline.find('Article')
                
                # ID
                pmid = medline.find('PMID').text
                
                # Check for PMC ID
                pmc_id = None
                pubmed_data = article.find('PubmedData')
                if pubmed_data is not None:
                    article_id_list = pubmed_data.find('ArticleIdList')
                    if article_id_list is not None:
                        for aid in article_id_list.findall('ArticleId'):
                            if aid.get('IdType') == 'pmc':
                                pmc_id = aid.text
                                break
                
                # Title
                title = article_data.find('ArticleTitle').text
                
                # Abstract
                abstract_text = "No abstract available."
                abstract = article_data.find('Abstract')
                if abstract is not None:
                    abstract_texts = [elem.text for elem in abstract.findall('AbstractText') if elem.text]
                    if abstract_texts:
                        abstract_text = " ".join(abstract_texts)
                
                # Authors
                author_list = article_data.find('AuthorList')
                first_author = "Unknown"
                if author_list is not None and len(author_list) > 0:
                    last_name = author_list[0].find('LastName')
                    if last_name is not None:
                        first_author = last_name.text
                
                # Journal/Source
                journal = article_data.find('Journal')
                source = "Journal"
                if journal is not None:
                    title_elem = journal.find('Title')
                    if title_elem is not None:
                        source = title_elem.text
                
                # Date
                pubdate = journal.find('JournalIssue').find('PubDate')
                year = "No Date"
                if pubdate is not None:
                    year_elem = pubdate.find('Year')
                    if year_elem is not None:
                        year = year_elem.text
                    else:
                        # Try MedlineDate
                        medline_date = pubdate.find('MedlineDate')
                        if medline_date is not None:
                            year = medline_date.text[:4]

                citation_obj = {
                    "title": title,
                    "id": pmid,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "citation": f"{title} by {first_author} ({source}, {year})",
                    "abstract": abstract_text,
                    "full_text": None, # Placeholder
                    "grade": "Un-graded" # Placeholder for AI
                }
                
                citations.append(citation_obj)
                if pmc_id:
                    pmc_map[pmc_id] = len(citations) - 1
                    
            except Exception as e:
                continue
        
        # 4. Fetch Full Text from PMC if available
        if pmc_map:
            try:
                # Extract numeric IDs for PMC fetch (remove 'PMC' prefix if present)
                pmc_ids_clean = [pid.replace('PMC', '') for pid in pmc_map.keys()]
                pmc_ids_str = ','.join(pmc_ids_clean)
                
                pmc_url = base_url + "efetch.fcgi?" + urllib.parse.urlencode({'db': 'pmc', 'id': pmc_ids_str, 'retmode': 'xml'})
                
                with urllib.request.urlopen(pmc_url) as response:
                    pmc_xml = response.read().decode()
                
                pmc_root = ET.fromstring(pmc_xml)
                
                for article in pmc_root.findall('.//article'):
                    # Find the PMC ID in this article to match back
                    current_pmc_id = None
                    for aid in article.findall('.//article-id'):
                        if aid.get('pub-id-type') == 'pmc':
                            current_pmc_id = "PMC" + aid.text # Standardize to PMC prefix
                            break
                    
                    if current_pmc_id and current_pmc_id in pmc_map:
                        # Extract Body Text
                        body = article.find('body')
                        if body is not None:
                            # Naive text extraction: get all text from body
                            # itertext() is useful here
                            full_text = "".join(body.itertext())
                            # Truncate if excessively long to prevent memory issues (e.g. 50k chars)
                            if len(full_text) > 50000:
                                full_text = full_text[:50000] + "... [Truncated]"
                            
                            citations[pmc_map[current_pmc_id]]['full_text'] = full_text
                            
            except Exception as e:
                # Fail silently on full text fetch, keep abstracts
                print(f"PMC Fetch Error: {e}")
                pass
                
        return citations
                
        return citations
    except Exception as e:
        st.error(f"PubMed Search Error: {e}")
        return []

# ==========================================
# 4. MAIN UI
# ==========================================
st.title("CarePathIQ AI Agent")
st.markdown(f"### Intelligently Build and Deploy Clinical Pathways")

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
        Get a free API key <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #A9EED1; text-decoration: underline;">here</a>.
    </div>
    """, unsafe_allow_html=True)
    st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
    st.stop()

# --- NAVIGATION HANDLER (Must be before st.radio) ---
if 'target_phase' in st.session_state and st.session_state.target_phase:
    st.session_state.current_phase_label = st.session_state.target_phase
    st.session_state.target_phase = None

phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", 
                  "Phase 2: Rapid Evidence Appraisal", 
                  "Phase 3: Decision Science", 
                  "Phase 4: User Interface Design", 
                  "Phase 5: Operationalize"], 
                 horizontal=True,
                 key="current_phase_label",
                 label_visibility="collapsed")

st.divider()

# ------------------------------------------
# PHASE 1: SCOPING & CHARTER
# ------------------------------------------
if "Phase 1" in phase:
    
    col1, col2 = st.columns([1, 1])
    
    # --- 1. INITIALIZE WIDGET STATE ---
    # Helper to sync widget state to data store
    def sync_p1_widgets():
        st.session_state.data['phase1']['condition'] = st.session_state.get('p1_cond_input', '')
        st.session_state.data['phase1']['inclusion'] = st.session_state.get('p1_inc', '')
        st.session_state.data['phase1']['exclusion'] = st.session_state.get('p1_exc', '')
        st.session_state.data['phase1']['setting'] = st.session_state.get('p1_setting', '')
        st.session_state.data['phase1']['problem'] = st.session_state.get('p1_prob', '')
        st.session_state.data['phase1']['objectives'] = st.session_state.get('p1_obj', '')
        
        # Invalidate Phase 2 so it regenerates based on new Phase 1 data
        st.session_state.auto_run["p2_pico"] = False
        st.session_state.auto_run["p2_query"] = False

    # Initialize keys if missing
    if 'p1_cond_input' not in st.session_state: st.session_state['p1_cond_input'] = st.session_state.data['phase1'].get('condition', '')
    if 'p1_inc' not in st.session_state: st.session_state['p1_inc'] = st.session_state.data['phase1'].get('inclusion', '')
    if 'p1_exc' not in st.session_state: st.session_state['p1_exc'] = st.session_state.data['phase1'].get('exclusion', '')
    if 'p1_setting' not in st.session_state: st.session_state['p1_setting'] = st.session_state.data['phase1'].get('setting', '')
    if 'p1_prob' not in st.session_state: st.session_state['p1_prob'] = st.session_state.data['phase1'].get('problem', '')
    if 'p1_obj' not in st.session_state: st.session_state['p1_obj'] = st.session_state.data['phase1'].get('objectives', '')
    
    # INSTRUCTIONAL BANNER
    styled_info("**Workflow Tip:** This form is interactive. The AI agent will auto-draft sections (Criteria, Problem, Goals) as you type. You can **manually edit** any text area to refine the content, and the AI agent will use your edits to generate the next section and the final Project Charter.")

    with col1:
        # CLINICAL CONDITION
        st.subheader("1. Clinical Focus")
        cond_input = st.text_input(
            "Clinical Condition", 
            placeholder="e.g. Sepsis", 
            key="p1_cond_input",
            on_change=sync_p1_widgets
        )
        
        # CARE SETTING (Moved Up)
        setting_input = st.text_input(
            "Care Setting", 
            placeholder="e.g. Emergency Department",
            key="p1_setting", 
            on_change=sync_p1_widgets
        )
        
        # TARGET POPULATION
        st.subheader("2. Target Population")
        
        # AUTO-GENERATE CRITERIA (Replaces Button)
        # Trigger only if both inputs are present and we haven't run for this combo yet
        curr_key = f"{cond_input}|{setting_input}"
        last_key = st.session_state.get('last_criteria_key', '')
        
        if cond_input and setting_input and curr_key != last_key:
             with st.spinner("Auto-generating inclusion/exclusion criteria..."):
                prompt = f"Act as a CMO. For clinical condition '{cond_input}' in setting '{setting_input}', suggest precise 'inclusion' and 'exclusion' criteria. Return a JSON object with keys: 'inclusion', 'exclusion'."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    inc_raw = data.get('inclusion') or data.get('Inclusion') or ''
                    exc_raw = data.get('exclusion') or data.get('Exclusion') or ''
                    
                    def fmt_item(x):
                        if isinstance(x, dict): return ": ".join([str(v) for v in x.values() if v])
                        return str(x)

                    inc_text = "\n".join([f"- {fmt_item(x)}" for x in inc_raw]) if isinstance(inc_raw, list) else str(inc_raw)
                    exc_text = "\n".join([f"- {fmt_item(x)}" for x in exc_raw]) if isinstance(exc_raw, list) else str(exc_raw)
                    
                    st.session_state.data['phase1']['inclusion'] = inc_text
                    st.session_state.data['phase1']['exclusion'] = exc_text
                    st.session_state['p1_inc'] = inc_text
                    st.session_state['p1_exc'] = exc_text
                    
                    st.session_state['last_criteria_key'] = curr_key
                    st.rerun()

        st.text_area("Inclusion Criteria", height=100, key="p1_inc", on_change=sync_p1_widgets)
        st.text_area("Exclusion Criteria", height=100, key="p1_exc", on_change=sync_p1_widgets)
        
    with col2:
        # CONTEXT
        st.subheader("3. Clinical Gap / Problem Statement")
        
        # AUTO-GENERATE PROBLEM (Replaces Button)
        # Trigger if Inclusion/Exclusion are present and we haven't run for this combo
        curr_inc = st.session_state.get('p1_inc', '')
        curr_exc = st.session_state.get('p1_exc', '')
        curr_cond = st.session_state.get('p1_cond_input', '')
        curr_setting = st.session_state.get('p1_setting', '')
        
        curr_prob_key = f"{curr_inc}|{curr_exc}|{curr_cond}"
        last_prob_key = st.session_state.get('last_prob_key', '')
        
        if curr_inc and curr_exc and curr_cond and curr_prob_key != last_prob_key:
             with st.spinner("Auto-generating problem statement..."):
                prompt = f"Act as a CMO. For condition '{curr_cond}' in setting '{curr_setting}' with inclusion '{curr_inc}', suggest a 'problem' statement (clinical gap). The statement MUST explicitly reference variation in current management and the need for care standardization. Return JSON with key: 'problem'."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    problem_raw = data.get('problem') or data.get('Problem') or ''
                    problem_text = str(problem_raw)
                    
                    st.session_state.data['phase1']['problem'] = problem_text
                    st.session_state['p1_prob'] = problem_text
                    st.session_state['last_prob_key'] = curr_prob_key
                    st.rerun()

        st.text_area("Problem Statement / Clinical Gap", height=100, key="p1_prob", on_change=sync_p1_widgets, label_visibility="collapsed")
        
        # OBJECTIVES
        st.subheader("4. Goals")
        
        # AUTO-GENERATE OBJECTIVES (Replaces Button)
        # Trigger if Problem is present and we haven't run for this combo
        curr_prob = st.session_state.get('p1_prob', '')
        
        curr_obj_key = f"{curr_prob}|{curr_cond}"
        last_obj_key = st.session_state.get('last_obj_key', '')
        
        if curr_prob and curr_cond and curr_obj_key != last_obj_key:
             with st.spinner("Auto-generating SMART objectives..."):
                prompt = f"Act as a CMO. For condition '{curr_cond}' in the '{curr_setting}' setting, addressing problem '{curr_prob}', suggest 3 SMART 'objectives'. Return JSON with key 'objectives' (list of strings)."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    objs = data.get('objectives', [])
                    obj_text = "\n".join([f"- {g}" for g in objs]) if isinstance(objs, list) else str(objs)
                    
                    st.session_state.data['phase1']['objectives'] = obj_text
                    st.session_state['p1_obj'] = obj_text
                    st.session_state['last_obj_key'] = curr_obj_key
                    st.rerun()

        st.text_area("Project Goals", height=150, key="p1_obj", on_change=sync_p1_widgets, label_visibility="collapsed")

    st.divider()

    # --- 5. PROJECT SCHEDULE (GANTT CHART) ---
    st.subheader("5. Project Schedule (Gantt Chart)")
    
    # Initialize Default Schedule if missing
    if 'schedule' not in st.session_state.data['phase1'] or not st.session_state.data['phase1']['schedule']:
        today = date.today()
        
        # Helper for date math
        def add_weeks(start_d, w):
            return start_d + timedelta(weeks=w)
            
        # Realistic Timeline Calculation
        # Phase 1: 2 weeks
        d1_end = add_weeks(today, 2)
        # Phase 2: 4 weeks
        d2_end = add_weeks(d1_end, 4)
        # Phase 3: 12 weeks (3 months) - Analysis/Design
        d3_end = add_weeks(d2_end, 12)
        # Phase 4: 8 weeks - Improvement/Pilot
        d4_end = add_weeks(d3_end, 8)
        # Phase 5: 4 weeks - Control
        d5_end = add_weeks(d4_end, 4)
        # Phase 6: 2 weeks - Close
        d6_end = add_weeks(d5_end, 2)
        
        st.session_state.data['phase1']['schedule'] = [
            {"Phase": "Form Project Team & Charter", "Owner": "Project Manager", "Start": today, "End": d1_end},
            {"Phase": "Definition & Measurement", "Owner": "Project Lead", "Start": d1_end, "End": d2_end},
            {"Phase": "Analysis (Root Cause & Design)", "Owner": "Clinical Lead", "Start": d2_end, "End": d3_end},
            {"Phase": "Improvement (Pilot)", "Owner": "Implementation Team", "Start": d3_end, "End": d4_end},
            {"Phase": "Control Phase", "Owner": "Quality Dept", "Start": d4_end, "End": d5_end},
            {"Phase": "Close Out & Summary", "Owner": "Project Sponsor", "Start": d5_end, "End": d6_end},
        ]

    # Reset Button
    if st.button("Reset Schedule to Defaults", key="reset_schedule"):
        st.session_state.data['phase1']['schedule'] = [] # Clear to trigger re-init
        st.rerun()

    # Editable Dataframe
    df_schedule = pd.DataFrame(st.session_state.data['phase1']['schedule'])
    
    # Ensure date columns are datetime objects for the editor
    df_schedule['Start'] = pd.to_datetime(df_schedule['Start']).dt.date
    df_schedule['End'] = pd.to_datetime(df_schedule['End']).dt.date

    styled_info("**Tip:** You can edit the **Start Date**, **End Date**, and **Owner** directly in the table below. The Gantt chart visualization will update automatically to reflect your changes.")

    edited_schedule = st.data_editor(
        df_schedule,
        column_config={
            "Phase": st.column_config.TextColumn("Phase", width="medium", disabled=True),
            "Owner": st.column_config.TextColumn("Owner", width="small"),
            "Start": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
            "End": st.column_config.DateColumn("End Date", format="YYYY-MM-DD"),
        },
        hide_index=True,
        use_container_width=True,
        key="gantt_editor"
    )
    
    # Save edits back to session state
    st.session_state.data['phase1']['schedule'] = edited_schedule.to_dict('records')

    # Interactive Gantt Chart (Altair)
    if not edited_schedule.empty:
        # Convert back to datetime for Altair
        chart_data = edited_schedule.copy()
        chart_data['Start'] = pd.to_datetime(chart_data['Start'])
        chart_data['End'] = pd.to_datetime(chart_data['End'])
        
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Start', title='Date'),
            x2='End',
            y=alt.Y('Phase', sort=None, title=None),
            color=alt.Color('Owner', legend=alt.Legend(title="Owner")),
            tooltip=['Phase', 'Start', 'End', 'Owner']
        ).properties(
            title="Project Timeline",
            height=300
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

    st.divider()

    # --- GENERATE CHARTER ---
    if st.button("Generate Project Charter", type="primary", use_container_width=True):
        
        # 1. CRITICAL: SYNC WIDGET VALUES TO DATA STORE
        # This forces the app to look at what you *just typed* (the widget state keys)
        # rather than the old dictionary values.
        st.session_state.data['phase1']['condition'] = st.session_state.p1_cond_input
        st.session_state.data['phase1']['inclusion'] = st.session_state.p1_inc
        st.session_state.data['phase1']['exclusion'] = st.session_state.p1_exc
        st.session_state.data['phase1']['setting'] = st.session_state.p1_setting
        st.session_state.data['phase1']['problem'] = st.session_state.p1_prob
        st.session_state.data['phase1']['objectives'] = st.session_state.p1_obj

        # Retrieve fresh values
        d = st.session_state.data['phase1']
        
        # Prepare prompt values (handle empty strings to prevent hallucination)
        p_cond = d['condition'] if d['condition'] else "Not specified"
        p_prob = d['problem'] if d['problem'] else "Not specified"
        p_set = d['setting'] if d['setting'] else "Not specified"
        p_inc = d['inclusion'] if d['inclusion'] and d['inclusion'].strip() else "None"
        p_exc = d['exclusion'] if d['exclusion'] and d['exclusion'].strip() else "None"
        p_obj = d['objectives'] if d['objectives'] and d['objectives'].strip() else "None"
        
        if not d['condition'] or not d['problem']:
            st.error("Please fill in at least the 'Condition' and 'Problem Statement' to generate a charter.")
        else:
            with st.status("AI Agent drafting Project Charter...", expanded=True) as status:
                st.write("Initializing PMP Agent...")
                
                # Get Today's Date for the Prompt
                today = date.today()
                today_str = today.strftime("%B %d, %Y")
                
                # Format Schedule for Prompt
                schedule_list = st.session_state.data['phase1']['schedule']
                schedule_str = ""
                for item in schedule_list:
                    s_date = item['Start'].strftime("%B %d, %Y") if isinstance(item['Start'], date) else str(item['Start'])
                    e_date = item['End'].strftime("%B %d, %Y") if isinstance(item['End'], date) else str(item['End'])
                    schedule_str += f"- {item['Phase']} (Start: {s_date}, End: {e_date}, Owner: {item['Owner']})\n"

                # Professional Prompt
                prompt = f"""
                Act as a certified Project Management Professional (PMP) in Healthcare. 
                Create a formal **Project Charter** for a Clinical Pathway initiative.
                
                **Use strictly this data (do not hallucinate criteria I deleted). If a field is 'None', state 'None' or leave blank in the charter:**
                - **Initiative:** {p_cond}
                - **Clinical Gap:** {p_prob}
                - **Care Setting:** {p_set}
                - **In Scope (Inclusion):** {p_inc}
                - **Out of Scope (Exclusion):** {p_exc}
                - **Objectives:** {p_obj}
                - **Date Created:** {today_str}
                
                **Output Format:** HTML Body Only.
                **Structure:** 
                Use the following best-practice Clinical Pathway Project Charter template as your guide. 
                Organize the content into a clean, professional HTML layout (using tables for the header, financials, and schedule):

                1. **Project Header**: Project Name, Project Manager, Project Sponsor.
                2. **Financials & Dates**: Estimated Costs, Expected Savings, Start Date, Completion Date.
                3. **Project Overview**: 
                   - Problem or Issue
                   - Purpose of Project
                   - Business Case
                   - Goals / Metrics
                   - Expected Deliverables
                4. **Project Scope**: Within Scope vs Outside Scope.
                5. **Tentative Schedule (Gantt Chart)**: A table representing a Gantt Chart with columns [Key Milestone | Owner | Start Date | End Date | Duration]. You MUST use these specific dates provided by the user:
                     {schedule_str}
                6. **Key Performance Indicators (KPIs)**: A table with columns [Metric | Definition | Target | Data Source | Owner]. Include relevant clinical, operational, and financial metrics.
                
                **Style Guide:**
                - Use <h2> headers for sections.
                - Ensure the tone is professional, concise, and persuasive.
                - DO NOT use markdown code blocks (```). Just return the HTML.
                """
                
                st.write("Generating content sections...")
                charter_content = get_gemini_response(prompt)
                
                st.write("Formatting document...")
                charter_content = charter_content.replace('```html', '').replace('```', '').strip()
                
                # Logo removed per user request
                logo_html = ""
                # if os.path.exists("CarePathIQ_Logo.png"):
                #     with open("CarePathIQ_Logo.png", "rb") as img_file:
                #         b64_logo = base64.b64encode(img_file.read()).decode()
                #         logo_html = f'<img src="data:image/png;base64,{b64_logo}" style="width:150px; display:block; margin-bottom:20px;">'

                # Professional HTML Wrapper with BLACK FONT enforcement
                word_html = f"""
                <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='[http://www.w3.org/TR/REC-html40](http://www.w3.org/TR/REC-html40)'>
                <head>
                    <meta charset="utf-8">
                    <style>
                        /* Force Black Text for everything */
                        body {{ font-family: 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; color: #000000 !important; }}
                        h1 {{ color: #000000 !important; font-size: 24pt; border-bottom: 2px solid #000000; padding-bottom: 10px; margin-bottom: 20px; }}
                        h2 {{ color: #000000 !important; font-size: 14pt; margin-top: 25px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }}
                        p, li, td, th {{ color: #000000 !important; }}
                        
                        /* Layout */
                        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                        td, th {{ border: 1px solid #000000; padding: 8px; vertical-align: top; }}
                        th {{ background-color: #f2f2f2; font-weight: bold; text-align: left; }}
                        .footer {{ margin-top: 50px; font-size: 9pt; color: #000000; text-align: center; border-top: 1px solid #000000; padding-top: 10px; }}
                    </style>
                </head>
                <body>
                    {logo_html}
                    <h1>Project Charter: {d['condition']} Pathway</h1>
                    <p><strong>Date Generated:</strong> {today_str}</p>
                    {charter_content}
                    <div class="footer">
                        Generated by CarePathIQ AI Agent | Confidential Internal Document
                    </div>
                </body>
                </html>
                """
                status.update(label="Charter Generated Successfully!", state="complete", expanded=False)
                status.update(label="Charter Generated Successfully!", state="complete", expanded=False)
                
                st.session_state['charter_doc'] = word_html
    
    # DOWNLOAD BUTTON
    if 'charter_doc' in st.session_state:
        st.success("Charter Generated Successfully.")
        st.download_button(
            label="Download Project Charter (.doc)",
            data=st.session_state['charter_doc'],
            file_name=f"Project_Charter_{st.session_state.data['phase1']['condition'].replace(' ', '_')}.doc",
            mime="application/msword",
            type="primary"
        )

    render_bottom_navigation()

# ------------------------------------------
# PHASE 2: RAPID EVIDENCE APPRAISAL
# ------------------------------------------
elif "Phase 2" in phase:
    
    # --- A. AUTO-RUN: PICO & SEARCH GENERATION ---
    # 1. SYNC PHASE 1 DATA (Fix for manual edits not propagating)
    # We check if the widget keys exist in session_state (meaning user visited Phase 1)
    # and update the data dictionary before proceeding.
    if 'p1_cond_input' in st.session_state: st.session_state.data['phase1']['condition'] = st.session_state.p1_cond_input
    if 'p1_inc' in st.session_state: st.session_state.data['phase1']['inclusion'] = st.session_state.p1_inc
    if 'p1_exc' in st.session_state: st.session_state.data['phase1']['exclusion'] = st.session_state.p1_exc
    if 'p1_setting' in st.session_state: st.session_state.data['phase1']['setting'] = st.session_state.p1_setting
    if 'p1_prob' in st.session_state: st.session_state.data['phase1']['problem'] = st.session_state.p1_prob
    if 'p1_obj' in st.session_state: st.session_state.data['phase1']['objectives'] = st.session_state.p1_obj

    p1_cond = st.session_state.data['phase1']['condition']
    
    # Only run if condition exists and we haven't run PICO yet
    # --- A. AUTO-RUN: SEARCH STRATEGY ---
    # Trigger only if we have a condition and haven't run yet
    p1_cond = st.session_state.data['phase1'].get('condition', '')
    
    # QUERY GENERATION & AUTO-SEARCH (Directly from Phase 1)
    if p1_cond:
        # 1. Generate Query if missing
        if not st.session_state.data['phase2'].get('mesh_query'):
            with st.spinner("AI Agent drafting Search Query..."):
                # Retrieve Phase 1 context
                setting = st.session_state.data['phase1'].get('setting', '')

                prompt_mesh = f"""
                Construct a PubMed search query.
                
                The query MUST strictly follow this format:
                "guidelines for managing patients with [Condition] in [Setting]"
                
                Use these values:
                - Condition: {p1_cond}
                - Setting: {setting}
                
                Example: "guidelines for managing patients with Sepsis in Emergency Department"
                
                OUTPUT FORMAT:
                - Return ONLY the raw query string.
                - Do NOT use markdown blocks.
                """
                raw_query = get_gemini_response(prompt_mesh)
                
                # Clean the query string to prevent broken links
                if raw_query:
                    clean_query = raw_query.replace('```', '').replace('\n', ' ').strip()
                    st.session_state.data['phase2']['mesh_query'] = clean_query
                    st.rerun()

        search_q = st.session_state.data['phase2'].get('mesh_query', '')

        # 2. Auto-Search if evidence is empty and we have a query
        # We use a flag 'p2_search_done' to prevent infinite loops if no results are found
        if search_q and not st.session_state.data['phase2']['evidence'] and not st.session_state.auto_run.get("p2_search_done", False):
             with st.spinner("Fetching PubMed results..."):
                results = search_pubmed(search_q)
                if results:
                    st.session_state.data['phase2']['evidence'].extend(results)
                    st.session_state.auto_run["p2_grade"] = False # Trigger grade
                    st.session_state.auto_run["p2_search_done"] = True
                    st.rerun()
                else:
                    st.warning("No results found.")
                    st.session_state.auto_run["p2_search_done"] = True # Prevent loop

    # --- UI: TOP BAR ---
    search_q = st.session_state.data['phase2'].get('mesh_query', '')
    if search_q:
        # PubMed Link Button (Safe Logic)
        encoded_query = urllib.parse.quote(search_q.strip())
        
        # Add "Last 5 Years" filter
        today = date.today()
        five_years_ago = today - timedelta(days=5*365)
        start_str = five_years_ago.strftime('%Y/%m/%d')
        end_str = today.strftime('%Y/%m/%d')
        filter_val = f"dates.{start_str}-{end_str}"
        encoded_filter = urllib.parse.quote(filter_val)
        
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={encoded_query}&filter={encoded_filter}"
        st.link_button("Open in PubMed ↗", pubmed_url, type="primary")

    # --- D. AUTO-RUN: GRADE ANALYSIS ---
    evidence_list = st.session_state.data['phase2']['evidence']
    
    if evidence_list and not st.session_state.auto_run["p2_grade"]:
        with st.status("AI Agent Evaluating Evidence...", expanded=True) as status:
            st.write("Preparing citations for analysis...")
            titles = [f"ID {e['id']}: {e['title']}" for e in evidence_list]
            
            # ENHANCED PROMPT BASED ON GRADE
            prompt = f"""
            Act as a Clinical Methodologist applying the GRADE framework.
            Analyze the following citations.
            
            For each citation, assign a Grade from these EXACT options: 
            - "High (A)"
            - "Moderate (B)"
            - "Low (C)"
            - "Very Low (D)"
            
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
            
            st.write("Connecting to Gemini AI...")
            grade_data = get_gemini_response(prompt, json_mode=True)
            
            st.write("Processing results...")
            if isinstance(grade_data, dict):
                for e in st.session_state.data['phase2']['evidence']:
                    if e['id'] in grade_data:
                        entry = grade_data[e['id']]
                        if isinstance(entry, dict):
                            e['grade'] = entry.get('grade', 'Un-graded')
                            e['rationale'] = entry.get('rationale', 'No rationale provided.')
                        else:
                            e['grade'] = str(entry)
                            e['rationale'] = "AI generated score."
                
                st.session_state.auto_run["p2_grade"] = True
                status.update(label="Evaluation Complete!", state="complete", expanded=False)
                st.rerun()

    # --- E. EVIDENCE TABLE ---
    if evidence_list:
        st.markdown("### Evidence Table")
        
        # Filter & Clear
        all_grades = ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"]
        default_grades = ["High (A)", "Moderate (B)", "Low (C)", "Un-graded"]
        
        col_filter, col_clear = st.columns([3, 1])
        with col_filter:
            selected_grades = st.multiselect("Filter by GRADE:", options=all_grades, default=default_grades)
        with col_clear:
            if st.button("Clear Evidence List", key="clear_ev"):
                st.session_state.data['phase2']['evidence'] = []
                st.session_state.auto_run["p2_grade"] = False
                st.rerun()

        df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
        
        # Ensure columns exist
        if 'rationale' not in df.columns: df['rationale'] = ""
        if 'grade' not in df.columns: df['grade'] = "Un-graded"
        
        # Remove "Supporting Evidence" column from Phase 2 display
        if 'Supporting Evidence' in df.columns:
            df = df.drop(columns=['Supporting Evidence'])
            
        # Apply Filter
        df_filtered = df[df['grade'].isin(selected_grades)]

        grade_help = """
        High (A): High confidence in effect estimate.
        Moderate (B): Moderate confidence; true effect likely close.
        Low (C): Limited confidence; true effect may differ.
        Very Low (D): Very little confidence.
        """
        
        edited_df = st.data_editor(df_filtered, column_config={
            "title": st.column_config.TextColumn("Title", width="medium", disabled=True),
            "id": st.column_config.TextColumn("PMID", width="small", disabled=True),
            "url": st.column_config.LinkColumn("Link", disabled=True),
            "grade": st.column_config.SelectboxColumn(
                "GRADE", 
                options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"],
                help=grade_help, 
                width="small",
                required=True
            ),
            "rationale": st.column_config.TextColumn(
                "GRADE Rationale",
                help="Factors: Risk of Bias, Inconsistency, Indirectness, Imprecision",
                width="large"
            ),
            "citation": st.column_config.TextColumn("Citation", disabled=True),
        }, column_order=["id", "title", "grade", "rationale", "url"], hide_index=True, key="ev_editor")
        
        # Save manual edits back to state (Merge Logic)
        # We must merge edited rows back into the full dataset to avoid losing hidden rows
        edited_map = {str(row['id']): row for row in edited_df.to_dict('records')}
        
        updated_evidence = []
        for row in st.session_state.data['phase2']['evidence']:
            rid = str(row['id'])
            if rid in edited_map:
                updated_evidence.append(edited_map[rid])
            else:
                updated_evidence.append(row)
        
        st.session_state.data['phase2']['evidence'] = updated_evidence
        
        # CSV Download
        csv = edited_df.to_csv(index=False)
        export_widget(csv, "evidence_table.csv", "text/csv", label="Download Evidence Table (CSV)")

    render_bottom_navigation()

# ------------------------------------------
# PHASE 3: DECISION SCIENCE
# ------------------------------------------
elif "Phase 3" in phase:
    
    # AUTO-RUN: LOGIC DRAFT
    cond = st.session_state.data['phase1']['condition']
    evidence_list = st.session_state.data['phase2']['evidence']
    nodes_exist = len(st.session_state.data['phase3']['nodes']) > 0
    
    if cond and not nodes_exist and not st.session_state.auto_run["p3_logic"]:
         with st.status("AI Agent drafting decision tree...", expanded=True) as status:
             
             # Prepare Evidence Context
             st.write("Analyzing Phase 2 Evidence...")
             
             def format_evidence_item(e):
                 base = f"- ID {e['id']}: {e.get('title','')} (GRADE: {e.get('grade','Un-graded')})"
                 content = ""
                 if e.get('full_text'):
                     content = f"\n  FULL TEXT (Truncated): {e['full_text'][:10000]}...\n"
                 else:
                     content = f"\n  ABSTRACT: {e.get('abstract', 'No abstract available.')}\n"
                 return base + content

             ev_context = "\n".join([format_evidence_item(e) for e in evidence_list])
             
             # ENHANCED PROMPT: BROADENED DEFINITIONS
             st.write("Structuring Clinical Logic...")
             prompt = f"""
             Act as a Clinical Decision Scientist. Build a Clinical Pathway for: {cond}.
             
             CRITICAL INSTRUCTION: Thoroughly read and analyze the evidence provided below. 
             Where FULL TEXT is available, prioritize it for deep clinical nuance. Otherwise, use the ABSTRACT.
             Ensure the decision tree is truly evidence-based and informed by the specific findings, recommendations, and guidelines presented in these texts.
             
             STRICT TEMPLATE RULES (Match the user's Visual Logic Language):
             1. **Start**: Entry point (e.g., "Patient presents to ED").
             2. **Decisions (Red Diamonds)**: Logic checkpoints. Can be Binary (Yes/No) OR Risk Stratification (Low/Moderate/High) based on validated scores (e.g., Wells Score, HEART Score).
             3. **Process (Yellow Box)**: High-Yield Clinical Actions. 
                - **Concise but Detailed**: Use specific parameters but keep it brief.
                - **Bad**: "Order Imaging", "Give Meds".
                - **Good**: "CT KUB (Low Dose)", "Tamsulosin 0.4mg daily", "IV Fluids (2L NS)".
                - **Constraint**: Max 6-8 words per label.
             4. **Notes (Blue Wave)**: Use these for **Red Flags** (exclusion criteria/safety checks) OR **Clarifications** (clinical context/dosage info).
             5. **End (Green Oval)**: The logical conclusion of a branch. This is often a final disposition (Discharge, Admit), but can be any terminal step appropriate for the logic.
             
             **Multidisciplinary Roles:**
             - Assign a **SINGLE primary "role"** to each step (e.g., "Triage Nurse", "ED Physician", "Specialist", "Pharmacist", "Admin").
             - Avoid multiple owners for a single step to ensure clear accountability.

             **Logic Structure Strategy (CRITICAL):**
             - **Decisions**: Must have clear branches. For Binary: 'Yes'/'No'. For Risk: 'Low'/'Moderate'/'High' (or similar categories). Ensure process steps follow each specific branch.
             - **Red Flags**: Should be represented as 'Notes' (Blue Wave) attached to relevant steps, OR as 'Decisions' (e.g., "Red flags present?") leading to different outcomes.
             - **Flow**: Ensure a logical progression from Start to End.
             
             **Evidence Mapping:**
             - For each step, if a specific piece of evidence from the list below supports it, include the "evidence_id" (e.g., "12345").
             
             Context Evidence:
             {ev_context}
             
             Return a JSON List of objects: 
             [{{
                 "type": "Start" | "Decision" | "Process" | "Note" | "End", 
                 "label": "Specific Action (e.g. 'CT KUB (Low Dose)')", 
                 "detail": "Longer clinical detail/criteria",
                 "role": "Role/Owner of this step",
                 "evidence_id": "Optional PubMed ID string matching the provided list"
             }}]
             """
             
             st.write("Mapping Evidence to Steps...")
             nodes = get_gemini_response(prompt, json_mode=True)
             
             if isinstance(nodes, list):
                 # Post-process to format evidence string for dropdown
                 for n in nodes:
                     eid = n.get('evidence_id')
                     if eid:
                         # Find matching evidence object
                         match = next((e for e in evidence_list if str(e['id']) == str(eid)), None)
                         if match:
                             n['evidence'] = f"PMID: {match['id']}"
                         else:
                             n['evidence'] = None
                     else:
                         n['evidence'] = None

                 st.session_state.data['phase3']['nodes'] = nodes
                 st.session_state.auto_run["p3_logic"] = True
                 status.update(label="Decision Tree Drafted!", state="complete", expanded=False)
                 st.rerun()

    if st.session_state.auto_run["p3_logic"]:
         if st.button("Add Manual Step"):
             st.session_state.data['phase3']['nodes'].append({"type": "Process", "label": "New Step", "detail": ""})
             st.rerun()

    # DYNAMIC EVIDENCE DROPDOWN & EDITOR
    if not st.session_state.data['phase3']['nodes']:
         st.session_state.data['phase3']['nodes'] = [{"type":"Start", "label":"Triage", "detail":""}]
    
    df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
    
    # Ensure columns exist
    if "detail" not in df_nodes.columns: df_nodes["detail"] = ""
    if "role" not in df_nodes.columns: df_nodes["role"] = "Unassigned"
    if "evidence" not in df_nodes.columns: df_nodes["evidence"] = None

    # Prepare Evidence Options
    evidence_options = []
    if st.session_state.data['phase2']['evidence']:
        evidence_options = [f"PMID: {e['id']}" for e in st.session_state.data['phase2']['evidence']]
    
    # COLOR-CODED TYPE DROPDOWN
    type_options = ["Start", "Decision", "Process", "Note", "End"]
    
    edited_nodes = st.data_editor(df_nodes, column_config={
        "type": st.column_config.SelectboxColumn(
            "Node Type", 
            options=type_options, 
            required=True,
            help="Decision=Red Diamond, Process=Yellow Box, Note=Blue Wave, End=Green Oval",
            width="medium"
        ),
        "label": st.column_config.TextColumn(
            "Label (Flowchart)", 
            help="Short text shown inside the shape",
            width="medium"
        ),
        "role": st.column_config.TextColumn(
            "Role / Owner", 
            help="Who performs this step? (e.g. Nurse, MD, Admin)",
            width="small"
        ),
        "detail": st.column_config.TextColumn(
            "Clinical Detail / Criteria", 
            help="Specifics (e.g. 'Serum Cr > 2.0', 'Failed PO trial')",
            width="large"
        ),
        "evidence": st.column_config.SelectboxColumn(
            "Supporting Evidence",
            options=evidence_options,
            help="Link to Phase 2 Evidence",
            width="small"
        ),
        "evidence_id": None # Hide the raw ID column
    }, num_rows="dynamic", hide_index=True, use_container_width=True, key="p3_editor")
    
    # Sync evidence_id with evidence selection to maintain data integrity
    updated_nodes = edited_nodes.to_dict('records')
    for n in updated_nodes:
        if n.get('evidence'):
            # Extract ID from "PMID: 12345"
            try:
                n['evidence_id'] = str(n['evidence']).replace("PMID: ", "")
            except:
                pass
        else:
            n['evidence_id'] = None

    st.session_state.data['phase3']['nodes'] = updated_nodes

    render_bottom_navigation()

# ------------------------------------------
# PHASE 4: USER INTERFACE DESIGN
# ------------------------------------------
elif "Phase 4" in phase:
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Clinical Pathway Visualizer")
        
        # --- DIRECT EDITING (EXPANDER) ---
        with st.expander("✏️ Edit Pathway Data (Nodes & Roles)", expanded=False):
            styled_info("Edit the table below to update the flowchart. **Gold Standard:** Keep labels concise (6-8 words) but clinically specific (e.g., 'CT KUB (Low Dose)' instead of 'CT Scan').")
            
            # Re-use the editor logic from Phase 3 (simplified)
            df_p4 = pd.DataFrame(st.session_state.data['phase3']['nodes'])
            if "role" not in df_p4.columns: df_p4["role"] = "Unassigned"
            
            edited_p4 = st.data_editor(df_p4, num_rows="dynamic", key="p4_editor", use_container_width=True)
            st.session_state.data['phase3']['nodes'] = edited_p4.to_dict('records')
            nodes = st.session_state.data['phase3']['nodes'] # Refresh local var
        
        if nodes:
            try:
                # --- LAYOUT CONTROLS ---
                c_view1, c_view2 = st.columns([1, 3])
                with c_view1:
                    orientation = st.radio(
                        "Layout Orientation",
                        ["Landscape (Horizontal)", "Portrait (Vertical)"],
                        index=0,
                        help="Switch between horizontal (Left-to-Right) and vertical (Top-to-Bottom) swimlanes."
                    )
                
                rank_dir = 'LR' if "Landscape" in orientation else 'TB'

                # --- ENHANCED GRAPHVIZ LOGIC WITH SWIMLANES ---
                graph = graphviz.Digraph()
                graph.attr(rankdir=rank_dir, splines='ortho') 
                graph.attr('node', fontname='Helvetica', fontsize='10')
                
                # Helper to style nodes
                def add_styled_node(g, idx, n):
                    node_id = str(idx)
                    label = n.get('label', '?')
                    node_type = n.get('type', 'Process')
                    
                    if node_type == 'Start':
                        g.node(node_id, label, shape='oval', style='filled', fillcolor='#D5E8D4', color='#82B366')
                    elif node_type == 'End':
                        g.node(node_id, label, shape='oval', style='filled', fillcolor='#D5E8D4', color='#82B366')
                    elif node_type == 'Decision':
                        g.node(node_id, label, shape='diamond', style='filled', fillcolor='#F8CECC', color='#B85450')
                    elif node_type == 'Note':
                        g.node(node_id, label, shape='note', style='filled', fillcolor='#DAE8FC', color='#6C8EBF')
                    else: # Process
                        g.node(node_id, label, shape='box', style='filled', fillcolor='#FFF2CC', color='#D6B656')

                # Group nodes by Role for Swimlanes
                roles = sorted(list(set([n.get('role', 'Unassigned') for n in nodes])))
                
                # Create Swimlanes (Subgraphs) if multiple roles exist
                # Note: Graphviz clusters require 'cluster_' prefix
                if len(roles) > 1:
                    for r in roles:
                        # Clean role name for graphviz ID (alphanumeric only)
                        safe_role = "".join(c for c in r if c.isalnum())
                        if not safe_role: safe_role = "default"
                        
                        with graph.subgraph(name=f'cluster_{safe_role}') as c:
                            c.attr(label=r, style='filled', color='#f8f9fa')
                            for i, n in enumerate(nodes):
                                if n.get('role', 'Unassigned') == r:
                                    add_styled_node(c, i, n)
                else:
                    # No swimlanes needed
                    for i, n in enumerate(nodes):
                        add_styled_node(graph, i, n)

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

                st.graphviz_chart(graph, use_container_width=True)
                
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
                styled_info("Tip: Ensure your Phase 3 Logic list is populated.")

    with col2:
        st.subheader("Nielsen's Heuristics Analysis")
        
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
                 For each heuristic, provide:
                 1. A specific critique or suggestion.
                 2. A boolean flag 'actionable' indicating if this suggestion requires a direct change to the node structure (e.g. changing labels, adding nodes, reordering).
                 
                 Return a JSON object where keys are H1-H10 and values are objects: 
                 {{ "H1": {{ "insight": "...", "actionable": true }}, ... }}
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
                Review these insights to improve your pathway's usability.
            </div>
            """, unsafe_allow_html=True)
            
            for k, v in risks.items():
                def_text = HEURISTIC_DEFS.get(k, "Nielsen's Usability Heuristic")
                
                # Handle both old (string) and new (dict) formats for backward compatibility
                if isinstance(v, dict):
                    insight = v.get('insight', 'No insight provided.')
                    is_actionable = v.get('actionable', False)
                else:
                    insight = str(v)
                    is_actionable = True # Default to showing button if format is old
                
                with st.expander(f"{k}: {insight[:50]}...", expanded=False):
                    st.markdown(f"**Principle:** *{def_text}*")
                    st.divider()
                    # Custom styling: White background, Dark Brown font
                    st.markdown(f"""
                    <div style="background-color: white; color: #5D4037; padding: 10px; border-radius: 5px; border: 1px solid #5D4037;">
                        {insight}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # APPLY RECOMMENDATION BUTTON (Only if actionable)
                    if is_actionable:
                        if st.button(f"Apply Recommendations ({k})", key=f"btn_fix_{k}"):
                            with st.spinner("AI Agent applying recommendations..."):
                                # Initialize history if needed
                                if 'node_history' not in st.session_state:
                                    st.session_state.node_history = []
                                
                                # Save current state to history
                                st.session_state.node_history.append(copy.deepcopy(st.session_state.data['phase3']['nodes']))
                                
                                # AI Call to modify nodes
                                curr_nodes = st.session_state.data['phase3']['nodes']
                                prompt_fix = f"""
                                Act as a Clinical Decision Scientist.
                                Current Clinical Pathway (JSON): {json.dumps(curr_nodes)}
                                
                                Usability Critique to Address: "{insight}"
                                
                                Task: Update the pathway JSON to fulfill the critique recommendations.
                                - You MUST make VISIBLE changes to the 'label' or 'detail' fields, or add/remove nodes.
                                - Do not just change internal IDs unless necessary.
                                - Maintain the existing structure and keys.
                                - Return ONLY the valid JSON list of nodes.
                                """
                                new_nodes = get_gemini_response(prompt_fix, json_mode=True)
                                
                                if new_nodes and isinstance(new_nodes, list):
                                    if new_nodes != curr_nodes:
                                        st.session_state.data['phase3']['nodes'] = new_nodes
                                        st.toast("Pathway updated successfully! Refreshing...", icon="✅")
                                        time.sleep(1.5) # Give user time to see the toast
                                        st.rerun()
                                    else:
                                        st.warning("AI suggested no changes for this critique.")
                                else:
                                    st.error("Failed to apply changes. Please try again.")

            # UNDO BUTTON
            if 'node_history' in st.session_state and st.session_state.node_history:
                if st.button("Undo Last Change", type="secondary", use_container_width=True):
                    st.session_state.data['phase3']['nodes'] = st.session_state.node_history.pop()
                    st.rerun()

            st.divider()
            
            # MANUAL REFINEMENT
            st.markdown("#### Custom Refinement")
            custom_edit = st.text_area("Describe any other changes you want to make:", 
                                     placeholder="e.g., 'Add a step to check blood pressure after triage'",
                                     key="p4_custom_edit")
            
            if st.button("Preview Changes", type="primary", use_container_width=True):
                if custom_edit:
                    with st.spinner("AI Agent analyzing request..."):
                        curr_nodes = st.session_state.data['phase3']['nodes']
                        prompt_custom = f"""
                        Act as a Clinical Decision Scientist.
                        Current Clinical Pathway (JSON): {json.dumps(curr_nodes)}
                        
                        User Request: "{custom_edit}"
                        
                        Task: 
                        1. Analyze the request and describe the specific changes needed (e.g. "Adding a Process node 'Check BP' after node 2").
                        2. Generate the updated pathway JSON.
                        
                        Return a JSON object with keys:
                        - "description": string (The explanation of changes)
                        - "nodes": list (The new full list of nodes)
                        """
                        result = get_gemini_response(prompt_custom, json_mode=True)
                        
                        if result and isinstance(result, dict) and 'nodes' in result:
                            st.session_state['p4_pending_custom'] = result
                            st.rerun()

            # Display Pending Changes
            if 'p4_pending_custom' in st.session_state:
                pending = st.session_state['p4_pending_custom']
                
                st.markdown(f"""
                <div style="background-color: #E3F2FD; padding: 10px; border-radius: 5px; border: 1px solid #2196F3; margin-bottom: 10px;">
                    <strong>Proposed Updates:</strong><br>
                    {pending.get('description', 'Updates generated.')}
                </div>
                """, unsafe_allow_html=True)
                
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("Apply Changes", type="primary", use_container_width=True, key="btn_apply_custom"):
                         # Initialize history if needed
                        if 'node_history' not in st.session_state:
                            st.session_state.node_history = []
                        
                        # Save current state
                        st.session_state.node_history.append(copy.deepcopy(st.session_state.data['phase3']['nodes']))
                        
                        # Apply
                        st.session_state.data['phase3']['nodes'] = pending['nodes']
                        del st.session_state['p4_pending_custom']
                        st.success("Custom changes applied!")
                        time.sleep(1)
                        st.rerun()
                
                with c_no:
                    if st.button("Cancel", use_container_width=True, key="btn_cancel_custom"):
                        del st.session_state['p4_pending_custom']
                        st.rerun()
            
            if st.button("Rerun Analysis (After Edits)", type="secondary", use_container_width=True):
                 st.session_state.auto_run["p4_heuristics"] = False
                 st.rerun()

    render_bottom_navigation()

# ------------------------------------------
# PHASE 5: OPERATIONALIZE
# ------------------------------------------
elif "Phase 5" in phase:
    st.markdown("### Operational Toolkit & Deployment")
    
    # --- 1. TARGET AUDIENCE SELECTOR ---
    st.subheader("Target Audience")
    
    if 'target_audience' not in st.session_state:
        st.session_state.target_audience = "Multidisciplinary Team"

    # If user changes this, we only invalidate the ASSETS (Docs/Slides), not the EHR
    new_audience = st.text_input("Define Primary Audience for Beta Testing and Education:", 
                                   value=st.session_state.target_audience)
    if new_audience != st.session_state.target_audience:
        st.session_state.target_audience = new_audience
        st.session_state.auto_run["p5_assets"] = False # Invalidate assets
        st.rerun()

    st.write("Quick Select:")
    b1, b2, b3 = st.columns([1, 1, 1])
    if b1.button("Physicians", use_container_width=True): 
        st.session_state.target_audience = "Physicians"
        st.session_state.auto_run["p5_assets"] = False
        st.rerun()
    if b2.button("Nurses", use_container_width=True): 
        st.session_state.target_audience = "Nurses"
        st.session_state.auto_run["p5_assets"] = False
        st.rerun()
    if b3.button("IT Analysts", use_container_width=True): 
        st.session_state.target_audience = "IT Analysts"
        st.session_state.auto_run["p5_assets"] = False
        st.rerun()

    st.divider()

    # --- 2. GENERATION LOGIC ---
    if "p5_files" not in st.session_state:
        st.session_state.p5_files = {"docx": None, "pptx": None, "csv": None, "html": None}

    # A. ASSETS GENERATION (Dependent on Audience)
    if not st.session_state.auto_run.get("p5_assets", False):
        with st.status(f"Generating Assets for {st.session_state.target_audience}...", expanded=True) as status:
            st.write("Initializing asset generation...")
            cond = st.session_state.data['phase1']['condition']
            prob = st.session_state.data['phase1']['problem']
            goals = st.session_state.data['phase1']['objectives']
            audience = st.session_state.target_audience
            nodes = st.session_state.data['phase3']['nodes']
            
            # --- GENERATE FLOWCHART IMAGE FOR PPT ---
            st.write("Rendering Flowchart...")
            flowchart_stream = None
            if nodes:
                try:
                    graph = graphviz.Digraph()
                    graph.attr(rankdir='TB', splines='ortho')
                    for i, n in enumerate(nodes):
                        node_id = str(i)
                        label = n.get('label', '?')
                        node_type = n.get('type', 'Process')
                        if node_type == 'Start':
                            graph.node(node_id, label, shape='oval', style='filled', fillcolor='#D5E8D4')
                        elif node_type == 'Decision':
                            graph.node(node_id, label, shape='diamond', style='filled', fillcolor='#F8CECC')
                        elif node_type == 'Note':
                            graph.node(node_id, label, shape='note', style='filled', fillcolor='#DAE8FC')
                        else:
                            graph.node(node_id, label, shape='box', style='filled', fillcolor='#FFF2CC')
                    
                    # Edges
                    for i, n in enumerate(nodes):
                        if i < len(nodes) - 1:
                            if n.get('type') == 'Decision':
                                graph.edge(str(i), str(i+1), label="Yes", color="green")
                                if i+2 < len(nodes): graph.edge(str(i), str(i+2), label="No", color="red")
                            elif n.get('type') == 'Note':
                                if i > 0: graph.edge(str(i), str(i-1), style="dotted", dir="back")
                                graph.edge(str(i-1), str(i+1))
                            elif nodes[i+1].get('type') == 'Note': pass
                            else: graph.edge(str(i), str(i+1))
                    
                    flowchart_stream = BytesIO(graph.pipe(format='png'))
                except Exception as e:
                    print(f"Flowchart generation failed for PPT: {e}")

            # --- WORD DOC (BETA GUIDE) ---
            st.write("Drafting Beta Testing Guide (Word)...")
            prompt_guide = f"""
            Act as a Clinical Operations Manager. Create a Beta Testing Guide for the '{cond}' pathway.
            Target User: {audience}.
            
            CRITICAL FORMATTING INSTRUCTION:
            - Do NOT use markdown code blocks (like ```markdown).
            - Do NOT use markdown headers (like # or ##).
            - Provide the content as a clean, guided series of checklists and plain text questions.
            - Use bullet points (-) for lists.
            
            Structure:
            1. Title: Beta Testing Instructions
            2. Pre-Test Checklist (Bullet points)
            3. Questions for the End User (Usability, Clarity, Workflow Fit)
            4. Feedback Submission Instructions
            """
            guide_text = get_gemini_response(prompt_guide)
            if guide_text:
                # Clean up any residual markdown artifacts just in case
                clean_text = guide_text.replace("```markdown", "").replace("```", "").strip()
                st.session_state.p5_files["docx"] = create_word_docx(clean_text)

            # --- HTML FORM (INTERACTIVE FEEDBACK) ---
            st.write("Designing Feedback Form (HTML)...")
            prompt_form = f"""
            Act as a UX Researcher. Create 5 specific feedback questions for beta testers of the '{cond}' pathway.
            Target Audience: {audience}.
            
            CRITICAL INSTRUCTION: Refer to the group as 'Team' instead of 'MDT' or 'Multidisciplinary Team' in the questions.
            
            Return a JSON Object with a single key "questions" containing a list of strings.
            Example: {{ "questions": ["Question 1?", "Question 2?"] }}
            """
            response_json = get_gemini_response(prompt_form, json_mode=True)
            
            questions = []
            if isinstance(response_json, list):
                questions = response_json
            elif isinstance(response_json, dict) and "questions" in response_json:
                questions = response_json["questions"]
            
            if questions:
                q_html = ""
                for i, q in enumerate(questions):
                    q_html += f'<div style="margin-bottom: 15px;"><label style="font-weight:bold; display:block; margin-bottom:5px;">{i+1}. {q}</label><textarea style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px;" rows="3"></textarea></div>'
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>CarePathIQ Beta Testing Feedback</title>
                    <style>
                        body {{ font-family: 'Arial', sans-serif; background-color: #f4f4f9; color: #333; padding: 20px; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .header {{ text-align: center; border-bottom: 2px solid #5D4037; padding-bottom: 20px; margin-bottom: 20px; }}
                        .logo {{ font-size: 24px; font-weight: bold; color: #5D4037; text-decoration: none; }}
                        .btn {{ background-color: #5D4037; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }}
                        .btn:hover {{ background-color: #3E2723; }}
                        .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #eee; padding-top: 15px; }}
                    </style>
                    <script>
                        function getFeedbackBody() {{
                            var body = "BETA TESTING FEEDBACK RESULTS:\\n\\n";
                            var textareas = document.getElementsByTagName('textarea');
                            var labels = document.getElementsByTagName('label');
                            
                            for (var i = 0; i < textareas.length; i++) {{
                                if (labels[i]) {{
                                    body += labels[i].innerText + "\\n" + textareas[i].value + "\\n\\n";
                                }}
                            }}
                            return body;
                        }}
                        
                        function copyToClipboard() {{
                            var body = getFeedbackBody();
                            navigator.clipboard.writeText(body).then(function() {{
                                alert('Feedback copied to clipboard!');
                            }}, function(err) {{
                                alert('Could not copy text. Please manually copy the answers.');
                            }});
                        }}

                        function downloadWord() {{
                            var header = "<html xmlns:o='urn:schemas-microsoft-com:office:office' " +
                                         "xmlns:w='urn:schemas-microsoft-com:office:word' " +
                                         "xmlns='http://www.w3.org/TR/REC-html40'>" +
                                         "<head><meta charset='utf-8'><title>Feedback</title></head><body>";
                            var footer = "</body></html>";
                            var body = "<h1>Beta Testing Feedback: {cond}</h1>";
                            body += "<p><strong>Audience:</strong> {audience}</p><hr>";
                            
                            var textareas = document.getElementsByTagName('textarea');
                            var labels = document.getElementsByTagName('label');
                            
                            for (var i = 0; i < textareas.length; i++) {{
                                if (labels[i]) {{
                                    body += "<h3>" + labels[i].innerText + "</h3>";
                                    body += "<p>" + (textareas[i].value || "(No answer)") + "</p>";
                                }}
                            }}
                            
                            var sourceHTML = header + body + footer;
                            var source = 'data:application/vnd.ms-word;charset=utf-8,' + encodeURIComponent(sourceHTML);
                            var fileDownload = document.createElement("a");
                            document.body.appendChild(fileDownload);
                            fileDownload.href = source;
                            fileDownload.download = 'feedback_responses.doc';
                            fileDownload.click();
                            document.body.removeChild(fileDownload);
                        }}
                    </script>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">CarePathIQ</div>
                            <p>Clinical Pathway Beta Testing Feedback Form</p>
                        </div>
                        
                        <p><strong>Pathway:</strong> {cond}</p>
                        <p><strong>Audience:</strong> {audience}</p>
                        <hr>
                        
                        <form onsubmit="event.preventDefault();">
                            {q_html}
                            
                            <div style="display: flex; gap: 10px; flex-direction: column;">
                                <button type="button" onclick="copyToClipboard()" class="btn" style="background-color: #795548;">Copy Responses to Clipboard</button>
                                <button type="button" onclick="downloadWord()" class="btn">Download Responses (Word Doc)</button>
                            </div>
                        </form>
                        
                        <div class="footer">
                            &copy; 2024 CarePathIQ by Tehreem Rehman. All Rights Reserved.<br>
                            Confidential Internal Document.
                        </div>
                    </div>
                </body>
                </html>
                """
                st.session_state.p5_files["html"] = html_content

            # --- POWERPOINT (SLIDE DECK) ---
            st.write("Compiling Slide Deck (PowerPoint)...")
            prompt_slides = f"""
            Act as a Healthcare Executive. Create content for a PowerPoint slide deck for the '{cond}' pathway.
            Target Audience: {audience}.
            Context: {prob}
            
            CRITICAL FORMATTING:
            - Provide PLAIN TEXT content only.
            - Do NOT use markdown (no **, ##, etc.).
            
            Return a JSON Object with this structure:
            {{
                "title": "Main Presentation Title",
                "audience": "{audience}",
                "slides": [
                    {{"title": "Clinical Gap", "content": "Describe the gap: {prob}"}},
                    {{"title": "Scope", "content": "..."}},
                    {{"title": "Objectives", "content": "Goals: {goals}"}},
                    {{"title": "Pathway", "content": "Please insert the clinical pathway flowchart here."}},
                    {{"title": "Content Overview", "content": "..."}},
                    {{"title": "Anticipated Impact", "content": "Focus on: \n1. Value of Advancing Care Standardization.\n2. Improving Health Equity."}}
                ]
            }}
            """
            slides_json = get_gemini_response(prompt_slides, json_mode=True)
            if isinstance(slides_json, dict):
                st.session_state.p5_files["pptx"] = create_ppt_presentation(slides_json, flowchart_stream)

            st.session_state.auto_run["p5_assets"] = True
            status.update(label="All Assets Generated!", state="complete", expanded=False)
            st.rerun()

    # --- 3. DISPLAY DOWNLOADS ---
    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("Beta Testing Guide")
        if st.session_state.p5_files["docx"]:
            st.download_button(
                label="Download Guide (.docx)",
                data=st.session_state.p5_files["docx"],
                file_name="Beta_Testing_Guide.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )

    with c2:
        st.subheader("Clinical Pathway Beta Testing Feedback Form")
        if st.session_state.p5_files.get("html"):
            st.download_button(
                label="Download Form (.html)",
                data=st.session_state.p5_files["html"],
                file_name="Beta_Testing_Feedback_Form.html",
                mime="text/html",
                type="primary"
            )

    with c3:
        st.subheader("Education Deck")
        if st.session_state.p5_files["pptx"]:
            st.download_button(
                label="Download Slides (.pptx)",
                data=st.session_state.p5_files["pptx"],
                file_name=f"Launch_Deck_{st.session_state.target_audience}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary"
            )

    st.divider()
    
    if st.button("Regenerate Education Assets (Refresh Audience)", type="primary"):
        st.session_state.auto_run["p5_assets"] = False
        st.rerun()
    
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
            3. Evidence Base: {p2_count} citations reviewed and graded.
            4. Pathway Logic: {p3_nodes} decision nodes and process steps defined.
            5. Value Proposition: Summarize the rigorous process undertaken (evidence appraisal, logic design, heuristic analysis) to justify the standardization of care and the readiness for pilot testing.
            
            Format as a professional briefing document.
            """
            summary = get_gemini_response(prompt)
            st.session_state.data['phase5']['exec_summary'] = summary
            
    if st.session_state.data['phase5'].get('exec_summary'):
        st.markdown("### Executive Summary")
        st.markdown(st.session_state.data['phase5']['exec_summary'])
        export_widget(st.session_state.data['phase5']['exec_summary'], "executive_summary.md", label="Download Summary")

    render_bottom_navigation()

# ==========================================
# FOOTER
# ==========================================
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
