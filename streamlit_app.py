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
    
    /* DISABLE BUTTONS (Standard Streamlit Disable Grey) */
    div.stButton > button:disabled {
        background-color: #eee !important;
        color: #999 !important;
        border: 1px solid #ccc !important;
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
    
    /* 2c. COLLAPSIBLE BUTTONS (Expanders) -> Dark Brown Background, White Text */
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
        "phase5": {"beta_email": "", "beta_content": "", "slides": "", "epic_csv": "", "exec_summary": ""} 
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
def styled_info(text):
    """Custom info box with Pink background and Black text."""
    # Convert markdown bold to HTML bold for correct rendering inside div
    # Ensure 'Tip:' is always bolded, even if not already in markdown bold
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    formatted_text = re.sub(r'(?<!<b>)\bTip:', r'<b>Tip:</b>', formatted_text)
    st.markdown(f"""
    <div style="background-color: #FFB0C9; color: black; padding: 10px; border-radius: 5px; border: 1px solid black; margin-bottom: 10px;">
        {formatted_text}
    </div>
    """, unsafe_allow_html=True)

def create_pdf_view_link(html_content, label="Open Charter in New Window"):
    """Generates a link to open HTML in new tab, simulating PDF."""
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" target="_blank" style="text-decoration:none; color:white; background-color:#5D4037; padding:10px 20px; border-radius:5px; font-weight:bold; display:inline-block;">{label}</a>'

def export_widget(content, filename, mime_type="text/plain", label="Download"):
    # The function html_to_pdf_bytes is now defined outside of export_widget
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

    doc.add_heading('Clinical Pathway: Beta Testing Guide', 0)
    
    # Simple markdown-to-docx parser
    for line in content_text.split('\n'):
        line = line.strip()
        # Remove Markdown symbols to preserve clean formatting
        line = line.replace('*', '').replace('#', '').strip()
        
        if not line: continue
        
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

def get_interactive_education_html(cond, points):
    """Generates an Interactive HTML Staff Education Module with Quiz."""
    logo_src = ""
    # Try to embed logo if available
    try:
        with open("CarePathIQ_Logo.png", "rb") as f:
            b64_logo = base64.b64encode(f.read()).decode()
            logo_src = f'<img src="data:image/png;base64,{b64_logo}" style="height:50px; margin-bottom:20px;">'
    except: pass

    # For demo, use static quiz content. In production, generate quiz dynamically from pathway data.
    html = f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>CarePathIQ Staff Education</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f9f9f9; color: #333; padding: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #5D4037; border-bottom: 2px solid #A9EED1; padding-bottom: 10px; }}
            .btn {{ background-color: #5D4037; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 20px; }}
            .btn:hover {{ background-color: #3E2723; }}
            .quiz-section {{ display: none; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
            .question {{ margin-bottom: 20px; }}
            .result {{ font-weight: bold; margin-top: 20px; padding: 10px; border-radius: 5px; }}
            .correct {{ background-color: #d4edda; color: #155724; }}
            .incorrect {{ background-color: #f8d7da; color: #721c24; }}
        </style>
        <script>
            function startQuiz() {{
                document.getElementById('intro').style.display = 'none';
                document.getElementById('quiz').style.display = 'block';
            }}
            function checkAnswer(btn, isCorrect) {{
                let resDiv = document.getElementById('result');
                if(isCorrect) {{
                    resDiv.innerHTML = "Correct!";
                    resDiv.className = "result correct";
                }} else {{
                    resDiv.innerHTML = "Incorrect. Please review the key points above.";
                    resDiv.className = "result incorrect";
                }}
            }}
        </script>
    </head>
    <body>
        <div class='container'>
            {logo_src}
            <h1>Clinical Pathway: {cond}</h1>
            <div id='intro'>
                <h3>Key Clinical Points & Goals</h3>
                <p>{points.replace(chr(10), '<br>')}</p>
                <h3>Scope</h3>
                <p>This pathway covers the defined patient population and care setting. Please review inclusion and exclusion criteria and goals below.</p>
                <ul>
                    <li><b>Scope:</b> [Insert scope from pathway data]</li>
                    <li><b>Inclusion Criteria:</b> [Insert inclusion criteria]</li>
                    <li><b>Exclusion Criteria:</b> [Insert exclusion criteria]</li>
                    <li><b>Goals:</b> [Insert goals]</li>
                    <li><b>Your Role:</b> [Insert role-based content for target audience]</li>
                </ul>
                <button class='btn' onclick='startQuiz()'>Take Knowledge Check</button>
            </div>
            <div id='quiz' class='quiz-section'>
                <h3>Knowledge Check</h3>
                <div class='question'>
                    <p><strong>1. What is the scope of this pathway?</strong></p>
                    <button class='btn' onclick='checkAnswer(this, true)'>[Correct scope answer]</button><br>
                    <button class='btn' style='background-color:#ccc; color:#333; margin-top:10px;' onclick='checkAnswer(this, false)'>[Incorrect answer]</button>
                </div>
                <div class='question'>
                    <p><strong>2. Which of the following is an inclusion criterion?</strong></p>
                    <button class='btn' onclick='checkAnswer(this, true)'>[Correct inclusion]</button><br>
                    <button class='btn' style='background-color:#ccc; color:#333; margin-top:10px;' onclick='checkAnswer(this, false)'>[Incorrect inclusion]</button>
                </div>
                <div class='question'>
                    <p><strong>3. Which of the following is an exclusion criterion?</strong></p>
                    <button class='btn' onclick='checkAnswer(this, true)'>[Correct exclusion]</button><br>
                    <button class='btn' style='background-color:#ccc; color:#333; margin-top:10px;' onclick='checkAnswer(this, false)'>[Incorrect exclusion]</button>
                </div>
                <div class='question'>
                    <p><strong>4. What is your role in this pathway?</strong></p>
                    <button class='btn' onclick='checkAnswer(this, true)'>[Correct role-based answer]</button><br>
                    <button class='btn' style='background-color:#ccc; color:#333; margin-top:10px;' onclick='checkAnswer(this, false)'>[Incorrect role-based answer]</button>
                </div>
                <div id='result'></div>
                <br>
                <p><em>This module confirms your understanding of the new {cond} protocol.</em></p>
            </div>
            <div style='margin-top: 40px; font-size: 0.8em; color: #777; text-align: center;'>
                Generated by CarePathIQ AI Agent
            </div>
        </div>
    </body>
    </html>
    """
    return html

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
    if model_choice == "Auto":
        candidates = [
            "gemini-2.5-flash", 
            "gemini-2.5-flash-lite",
            "gemini-1.5-flash", 
            "gemini-robotics-er-1.5-preview",
            "gemini-2.5-flash-tts"
        ]
    else:
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
            
            # Minimal sleep on retries
            if i > 0: time.sleep(0.1) 
            
            is_stream = stream_container is not None
            response = model.generate_content(prompt, safety_settings=safety, stream=is_stream)
            
            if response:
                if model_choice != "Auto" and model_name != model_choice:
                    st.toast(f"Switched to {model_name} (auto-fallback)")
                break 
        except Exception as e:
            e_str = str(e)
            if "429" in e_str:
                last_error = e
            elif last_error is None or "429" not in str(last_error):
                last_error = e
            continue

    if not response:
        error_msg = str(last_error)
        if "429" in error_msg:
            st.error("**Quota Exceeded (Rate Limit)**: You have hit the free tier limit for Gemini API.")
            styled_info("<b>IMPORTANT:</b> Google enforces strict rate limits and quotas on all Gemini API keys, even new ones. If you see this message, you must wait before trying again, or use a different API key. <br><br><b>Each user must use their own Gemini API key.</b> If you continue to see this error with a new key, it is likely that Google's quota for your account or region has been reached. <br><br>For more information, see <a href='https://aistudio.google.com/app/apikey' target='_blank'>Google AI Studio</a>.")
        elif "404" in error_msg:
            st.error("**Model Not Found**: The selected AI model is not available in your region or API version.")
        elif "API_KEY_INVALID" in error_msg or "400" in error_msg:
            st.error("API Key Error: The provided Google Gemini API Key is invalid.")
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
            stream_container.markdown(text) 
        else:
            text = response.text
            
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if match:
                text = match.group()
            
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                try:
                    # Fix escapes
                    cleaned_text = text.replace('\\', '\\\\') 
                    import ast
                    return ast.literal_eval(text)
                except:
                    pass
                raise 
        return text
    except Exception as e:
        st.error(f"Parsing Error: {e}")
        return None

def search_pubmed(query):
    """Real PubMed API Search with Abstracts."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        # 1. ESearch
        search_params = {
            'db': 'pubmed', 
            'term': f"{query} AND (\"last 5 years\"[dp])", 
            'retmode': 'json', 
            'retmax': 50, # Updated to 50
            'sort': 'relevance' # Explicitly Best Match
        }
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            id_list = data.get('esearchresult', {}).get('idlist', [])
        if not id_list:
            st.warning(f"PubMed returned no results for query: {query}")
            return []
        # 2. EFetch
        ids_str = ','.join(id_list)
        fetch_params = {'db': 'pubmed', 'id': ids_str, 'retmode': 'xml'}
        url = base_url + "efetch.fcgi?" + urllib.parse.urlencode(fetch_params)
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode()
        # 3. Parse XML
        root = ET.fromstring(xml_data)
        citations = []
        pmc_map = {} 
        for article in root.findall('.//PubmedArticle'):
            # Robustly extract fields, do not skip articles for missing data
            medline = article.find('MedlineCitation')
            article_data = medline.find('Article') if medline is not None else None
            pmid = medline.find('PMID').text if medline is not None and medline.find('PMID') is not None else "No PMID"
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
            title = article_data.find('ArticleTitle').text if article_data is not None and article_data.find('ArticleTitle') is not None else "No Title"
            abstract_text = "No abstract available."
            if article_data is not None:
                abstract = article_data.find('Abstract')
                if abstract is not None:
                    abstract_texts = [elem.text for elem in abstract.findall('AbstractText') if elem.text]
                    if abstract_texts:
                        abstract_text = " ".join(abstract_texts)
            author_list = article_data.find('AuthorList') if article_data is not None else None
            first_author = "Unknown"
            if author_list is not None and len(author_list) > 0:
                last_name = author_list[0].find('LastName')
                if last_name is not None:
                    first_author = last_name.text
            journal = article_data.find('Journal') if article_data is not None else None
            source = "Journal"
            if journal is not None:
                title_elem = journal.find('Title')
                if title_elem is not None:
                    source = title_elem.text
            year = "No Date"
            pubdate = journal.find('JournalIssue').find('PubDate') if journal is not None and journal.find('JournalIssue') is not None else None
            if pubdate is not None:
                year_elem = pubdate.find('Year')
                if year_elem is not None:
                    year = year_elem.text
                else:
                    medline_date = pubdate.find('MedlineDate')
                    if medline_date is not None:
                        year = medline_date.text[:4]
            citation_obj = {
                "title": title,
                "id": pmid,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "citation": f"{title} by {first_author} ({source}, {year})",
                "abstract": abstract_text,
                "full_text": None,
                "grade": "Un-graded",
                "year": year,
                "first_author": first_author
            }
            citations.append(citation_obj)
            if pmc_id:
                pmc_map[pmc_id] = len(citations) - 1
        # 4. Fetch Full Text
        if pmc_map:
            try:
                pmc_ids_clean = [pid.replace('PMC', '') for pid in pmc_map.keys()]
                pmc_ids_str = ','.join(pmc_ids_clean)
                pmc_url = base_url + "efetch.fcgi?" + urllib.parse.urlencode({'db': 'pmc', 'id': pmc_ids_str, 'retmode': 'xml'})
                with urllib.request.urlopen(pmc_url) as response:
                    pmc_xml = response.read().decode()
                pmc_root = ET.fromstring(pmc_xml)
                for article in pmc_root.findall('.//article'):
                    current_pmc_id = None
                    for aid in article.findall('.//article-id'):
                        if aid.get('pub-id-type') == 'pmc':
                            current_pmc_id = "PMC" + aid.text 
                            break
                    if current_pmc_id and current_pmc_id in pmc_map:
                        body = article.find('body')
                        if body is not None:
                            full_text = "".join(body.itertext())
                            if len(full_text) > 50000:
                                full_text = full_text[:50000] + "... [Truncated]"
                            citations[pmc_map[current_pmc_id]]['full_text'] = full_text
            except Exception as e:
                st.warning(f"PubMed Full Text fetch error: {e}")
        if not citations:
            st.warning(f"PubMed returned no parseable citations for query: {query}")
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

# --- NAVIGATION HANDLER ---
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
    
    def sync_p1_widgets():
        st.session_state.data['phase1']['condition'] = st.session_state.get('p1_cond_input', '')
        st.session_state.data['phase1']['inclusion'] = st.session_state.get('p1_inc', '')
        st.session_state.data['phase1']['exclusion'] = st.session_state.get('p1_exc', '')
        st.session_state.data['phase1']['setting'] = st.session_state.get('p1_setting', '')
        st.session_state.data['phase1']['problem'] = st.session_state.get('p1_prob', '')
        st.session_state.data['phase1']['objectives'] = st.session_state.get('p1_obj', '')
        st.session_state.auto_run["p2_pico"] = False
        st.session_state.auto_run["p2_query"] = False

    if 'p1_cond_input' not in st.session_state: st.session_state['p1_cond_input'] = st.session_state.data['phase1'].get('condition', '')
    if 'p1_inc' not in st.session_state: st.session_state['p1_inc'] = st.session_state.data['phase1'].get('inclusion', '')
    if 'p1_exc' not in st.session_state: st.session_state['p1_exc'] = st.session_state.data['phase1'].get('exclusion', '')
    if 'p1_setting' not in st.session_state: st.session_state['p1_setting'] = st.session_state.data['phase1'].get('setting', '')
    if 'p1_prob' not in st.session_state: st.session_state['p1_prob'] = st.session_state.data['phase1'].get('problem', '')
    if 'p1_obj' not in st.session_state: st.session_state['p1_obj'] = st.session_state.data['phase1'].get('objectives', '')
    
    styled_info("Tip: This form is interactive. The AI agent will auto-draft sections (Criteria, Problem, Goals) as you type. You can **manually edit** any text area to refine the content, and the AI agent will use your edits to generate the next section and the final Project Charter.")

    with col1:
        st.subheader("1. Clinical Focus")
        cond_input = st.text_input("Clinical Condition", placeholder="e.g. Sepsis", key="p1_cond_input", on_change=sync_p1_widgets)
        setting_input = st.text_input("Care Setting", placeholder="e.g. Emergency Department", key="p1_setting", on_change=sync_p1_widgets)
        
        st.subheader("2. Target Population")
        curr_key = f"{cond_input}|{setting_input}"
        last_key = st.session_state.get('last_criteria_key', '')
        
        if cond_input and setting_input and curr_key != last_key:
            with st.spinner("Auto-generating inclusion/exclusion criteria..."):
                prompt = f"""
                Act as a Chief Medical Officer. For the clinical pathway on '{cond_input}' in the setting '{setting_input}', suggest precise 'inclusion' and 'exclusion' criteria for clinical workflow (NOT for research studies).

                CRITICAL INSTRUCTIONS:
                - Do NOT use research or study language (e.g., 'study protocol', 'enrollment', 'informed consent', 'randomization', 'investigator').
                - Focus on real-world clinical criteria for patient selection and pathway entry/exit (e.g., 'Adults age 18+', 'Presenting with flank pain', 'No known allergy to contrast', 'Pregnant patients excluded').
                - Do NOT automatically exclude patients who are critically ill or have red flag signs; these patients should be included in the pathway with appropriate steps for escalation, stabilization, or urgent management.
                - Use concise, clinically relevant language that would make sense to a practicing clinician.
                - Return a JSON object with keys: 'inclusion', 'exclusion'.
                """
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
        st.subheader("3. Clinical Gap / Problem Statement")
        curr_inc = st.session_state.get('p1_inc', '')
        curr_exc = st.session_state.get('p1_exc', '')
        curr_cond = st.session_state.get('p1_cond_input', '')
        curr_setting = st.session_state.get('p1_setting', '')
        
        curr_prob_key = f"{curr_inc}|{curr_exc}|{curr_cond}"
        last_prob_key = st.session_state.get('last_prob_key', '')
        
        if curr_inc and curr_exc and curr_cond and curr_prob_key != last_prob_key:
             with st.spinner("Auto-generating problem statement..."):
                prompt = f"Act as a CMO. For condition '{curr_cond}' in setting '{curr_setting}', suggest a 'problem' statement (clinical gap). The statement MUST explicitly reference variation in current management and the need for care standardization. Return JSON with key: 'problem'."
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    problem_text = str(data.get('problem', ''))
                    st.session_state.data['phase1']['problem'] = problem_text
                    st.session_state['p1_prob'] = problem_text
                    st.session_state['last_prob_key'] = curr_prob_key
                    st.rerun()

        st.text_area("Problem Statement / Clinical Gap", height=100, key="p1_prob", on_change=sync_p1_widgets, label_visibility="collapsed")
        
        st.subheader("4. Goals")
        curr_prob = st.session_state.get('p1_prob', '')
        curr_obj_key = f"{curr_prob}|{curr_cond}"
        last_obj_key = st.session_state.get('last_obj_key', '')
        
        if curr_prob and curr_cond and curr_obj_key != last_obj_key:
             with st.spinner("Auto-generating SMART objectives..."):
                prompt = f"""
                Act as a **Chief Medical Officer** in a hospital. 
                For condition '{curr_cond}' in the '{curr_setting}' setting, addressing problem '{curr_prob}', suggest 3 SMART 'objectives'.
                
                CRITICAL INSTRUCTIONS:
                - Focus ONLY on clinical and operational outcomes (e.g., Length of Stay, Mortality, Readmission Rate, Door-to-Needle time, Patient Safety, Compliance with Guidelines).
                - Do NOT use business or marketing metrics (e.g., no 'leads', 'brand equity', 'sales', 'conversion rates').
                - **Do NOT use LaTeX formatting (e.g. avoid $\le$). Use standard text characters (e.g. <=, <, >) for inequalities.**
                - Return JSON with key 'objectives' (list of strings).
                """
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

    st.subheader("5. Project Schedule (Gantt Chart)")
    if 'schedule' not in st.session_state.data['phase1'] or not st.session_state.data['phase1']['schedule']:
        today = date.today()
        def add_weeks(start_d, w): return start_d + timedelta(weeks=w)
        
        # 1) Project Charter (2 wks)
        d1_end = add_weeks(today, 2)
        # 2) Pathway Draft (4 wks)
        d2_end = add_weeks(d1_end, 4)
        # 3) Expert Panel Feedback (2 wks)
        d3_end = add_weeks(d2_end, 2)
        # 4) Iterative Design (2 wks)
        d4_end = add_weeks(d3_end, 2)
        # 5) Informatics Build (4 wks)
        d5_end = add_weeks(d4_end, 4)
        # 6) Beta Testing (4 wks)
        d6_end = add_weeks(d5_end, 4)
        # 7) Go-Live (2 wks)
        d7_end = add_weeks(d6_end, 2)
        # 8) Optimization (4 wks)
        d8_end = add_weeks(d7_end, 4)
        # 9) Monitoring (Ongoing 12+ wks)
        d9_end = add_weeks(d8_end, 12)
        
        st.session_state.data['phase1']['schedule'] = [
            {"Phase": "1. Project Charter", "Owner": "Project Manager", "Start": today, "End": d1_end},
            {"Phase": "2. Pathway Draft", "Owner": "Clinical Lead", "Start": d1_end, "End": d2_end},
            {"Phase": "3. Expert Panel Feedback", "Owner": "Expert Panel", "Start": d2_end, "End": d3_end},
            {"Phase": "4. Iterative Design", "Owner": "Clinical Lead", "Start": d3_end, "End": d4_end},
            {"Phase": "5. Informatics Build & EHR Integration", "Owner": "Informatics Team", "Start": d4_end, "End": d5_end},
            {"Phase": "6. Beta Testing", "Owner": "Quality Improvement", "Start": d5_end, "End": d6_end},
            {"Phase": "7. Go-Live and Staff Education", "Owner": "Operations", "Start": d6_end, "End": d7_end},
            {"Phase": "8. Post Go-Live Optimizations", "Owner": "Clinical Lead", "Start": d7_end, "End": d8_end},
            {"Phase": "9. Monitoring and Evaluation", "Owner": "Quality Dept", "Start": d8_end, "End": d9_end},
        ]

    if st.button("Reset Schedule to Defaults", key="reset_schedule"):
        st.session_state.data['phase1']['schedule'] = []
        st.rerun()

    df_schedule = pd.DataFrame(st.session_state.data['phase1']['schedule'])
    df_schedule['Start'] = pd.to_datetime(df_schedule['Start']).dt.date
    df_schedule['End'] = pd.to_datetime(df_schedule['End']).dt.date

    styled_info("**Tip:** You can edit the **Start Date**, **End Date**, and **Owner** directly in the table below.")

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
    
    st.session_state.data['phase1']['schedule'] = edited_schedule.to_dict('records')

    if not edited_schedule.empty:
        chart_data = edited_schedule.copy()
        chart_data['Start'] = pd.to_datetime(chart_data['Start'])
        chart_data['End'] = pd.to_datetime(chart_data['End'])
        
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Start', title='Date'),
            x2='End',
            y=alt.Y('Phase', sort=None, title=None),
            color=alt.Color('Owner', legend=alt.Legend(title="Owner")),
            tooltip=['Phase', 'Start', 'End', 'Owner']
        ).properties(title="Project Timeline", height=300).interactive()
        
        st.altair_chart(chart, use_container_width=True)

    st.divider()

    if st.button("Generate Project Charter", type="primary", use_container_width=True):
        st.session_state.data['phase1']['condition'] = st.session_state.p1_cond_input
        st.session_state.data['phase1']['inclusion'] = st.session_state.p1_inc
        st.session_state.data['phase1']['exclusion'] = st.session_state.p1_exc
        st.session_state.data['phase1']['setting'] = st.session_state.p1_setting
        st.session_state.data['phase1']['problem'] = st.session_state.p1_prob
        st.session_state.data['phase1']['objectives'] = st.session_state.p1_obj

        d = st.session_state.data['phase1']
        
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
                today_str = date.today().strftime("%B %d, %Y")
                
                schedule_list = st.session_state.data['phase1']['schedule']
                schedule_str = ""
                for item in schedule_list:
                    s_date = str(item['Start'])
                    e_date = str(item['End'])
                    schedule_str += f"- {item['Phase']} (Start: {s_date}, End: {e_date}, Owner: {item['Owner']})\n"

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
                **Structure:** Use the following best-practice Clinical Pathway Project Charter template as your guide. 
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
                - **Do NOT use LaTeX formatting (no $\le$). Use standard text characters.**
                - **Do NOT write 'None' for missing fields like Sponsor. Leave them blank so the user can fill them in.**
                - DO NOT use markdown code blocks (```). Just return the HTML.
                """
                
                st.write("Generating content sections...")
                charter_content = get_gemini_response(prompt)
                charter_content = charter_content.replace('```html', '').replace('```', '').strip()
                
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
                st.session_state['charter_doc'] = word_html
    
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
    
    # Auto-populate PubMed search query using Phase 1 content
    if 'p1_cond_input' in st.session_state:
        st.session_state.data['phase1']['condition'] = st.session_state.p1_cond_input
    p1_cond = st.session_state.data['phase1'].get('condition', '').strip()
    p1_setting = st.session_state.data['phase1'].get('setting', '').strip()

    # Build the query: managing patients with [clinical condition] in [care setting] (last 5 years)
    auto_query = ""
    if p1_cond and p1_setting:
        auto_query = f"managing patients with {p1_cond} in {p1_setting}"
        st.session_state.data['phase2']['mesh_query'] = auto_query

    search_q = st.session_state.data['phase2'].get('mesh_query', '')
    if search_q and not st.session_state.data['phase2']['evidence'] and not st.session_state.auto_run.get("p2_search_done", False):
        with st.spinner("Fetching PubMed results..."):
            results = search_pubmed(search_q)
            if results:
                st.session_state.data['phase2']['evidence'].extend(results)
                st.session_state.auto_run["p2_grade"] = False 
                st.session_state.auto_run["p2_search_done"] = True
                st.rerun()
            else:
                st.warning("No results found.")
                st.session_state.auto_run["p2_search_done"] = True 

    # Only show PubMed query and link if a search has been performed (not on landing)
    if search_q and (st.session_state.data['phase2']['evidence'] or st.session_state.auto_run.get("p2_search_done", False)):
        # Add last 5 years filter to the query for PubMed
        pubmed_query = f"{search_q} AND (\"last 5 years\"[dp])"
        encoded_query = urllib.parse.quote(pubmed_query.strip())
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={encoded_query}"
        st.link_button("Open in PubMed ↗", pubmed_url, type="primary")

    evidence_list = st.session_state.data['phase2']['evidence']
    
    if evidence_list and not st.session_state.auto_run["p2_grade"]:
        with st.status("AI Agent Evaluating Evidence...", expanded=True) as status:
            st.write("Preparing citations for analysis...")
            titles = [f"ID {e['id']}: {e['title']}" for e in evidence_list]
            prompt = f"""
            Act as a Clinical Methodologist applying GRADE.
            For each citation: {json.dumps(titles)}
            Assign a Grade: \"High (A)\", \"Moderate (B)\", \"Low (C)\", \"Very Low (D)\".
            Return JSON object: {{ \"ID\": {{ \"grade\": \"...\", \"rationale\": \"...\" }} }}
            """
            grade_data = get_gemini_response(prompt, json_mode=True)
            error_flag = False
            if not isinstance(grade_data, dict) or not grade_data:
                st.warning("AI could not assign GRADE or rationale. Please review and assign manually.")
                error_flag = True
            else:
                # Map grades/rationales to evidence by ID, robustly
                for e in st.session_state.data['phase2']['evidence']:
                    entry = grade_data.get(str(e['id'])) or grade_data.get(e['id'])
                    if entry:
                        e['grade'] = entry.get('grade', 'Un-graded')
                        e['rationale'] = entry.get('rationale', 'AI generated.')
                    else:
                        e['grade'] = 'Un-graded'
                        e['rationale'] = 'No rationale provided.'
            st.session_state.auto_run["p2_grade"] = True
            if not error_flag:
                status.update(label="Evaluation Complete!", state="complete", expanded=False)
            st.rerun()

    if evidence_list:
        st.markdown("### Evidence Table")
        col_filter, col_clear, col_regrade = st.columns([3, 1, 2])
        with col_filter:
            selected_grades = st.multiselect("Filter by GRADE:", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], default=["High (A)", "Moderate (B)", "Low (C)", "Un-graded"])
        with col_clear:
            if st.button("Clear Evidence List", key="clear_ev"):
                st.session_state.data['phase2']['evidence'] = []
                st.session_state.auto_run["p2_grade"] = False
                st.rerun()
        with col_regrade:
            if st.button("Regrade All Evidence", key="regrade_ev"):
                st.session_state.auto_run["p2_grade"] = False
                st.rerun()

        # Ensure all evidence has grade and rationale fields
        for e in st.session_state.data['phase2']['evidence']:
            if 'grade' not in e:
                e['grade'] = 'Un-graded'
            if 'rationale' not in e:
                e['rationale'] = 'No rationale provided.'

        df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
        # Debug output removed
        if 'rationale' not in df.columns: df['rationale'] = "No rationale provided."
        if 'grade' not in df.columns: df['grade'] = "Un-graded"

        # Sort by Grade (High to Low)
        grade_order = ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"]
        df['grade'] = pd.Categorical(df['grade'], categories=grade_order, ordered=True)
        df = df.sort_values('grade')

        df_filtered = df[df['grade'].isin(selected_grades)]

        # Add missing columns if not present
        for col in ["abstract", "citation"]:
            if col not in df.columns:
                df[col] = ""
        # Optionally add year/author if present in evidence
        if any("year" in e for e in st.session_state.data['phase2']['evidence']):
            if "year" not in df.columns:
                df["year"] = ""
        if any("first_author" in e for e in st.session_state.data['phase2']['evidence']):
            if "first_author" not in df.columns:
                df["first_author"] = ""

        column_config = {
            "title": st.column_config.TextColumn("Title", width="medium", disabled=True),
            "id": st.column_config.TextColumn("PMID", width="small", disabled=True),
            "url": st.column_config.LinkColumn("Link", disabled=True),
            "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)", "Un-graded"], width="small", required=True),
            "rationale": st.column_config.TextColumn("GRADE Rationale", width="large"),
            "citation": st.column_config.TextColumn("Citation", width="large", disabled=True),
        }
        column_order = ["id", "title", "grade", "rationale", "citation", "url"]
        if "year" in df.columns:
            column_config["year"] = st.column_config.TextColumn("Year", width="small", disabled=True)
            column_order.insert(2, "year")
        if "first_author" in df.columns:
            column_config["first_author"] = st.column_config.TextColumn("First Author", width="small", disabled=True)
            column_order.insert(3, "first_author")

        edited_df = st.data_editor(df_filtered, column_config=column_config, column_order=column_order, hide_index=True, key="ev_editor")

        edited_map = {str(row['id']): row for row in edited_df.to_dict('records')}
        updated_evidence = []
        for row in st.session_state.data['phase2']['evidence']:
            rid = str(row['id'])
            if rid in edited_map: updated_evidence.append(edited_map[rid])
            else: updated_evidence.append(row)

        st.session_state.data['phase2']['evidence'] = updated_evidence

        csv = edited_df.to_csv(index=False)
        export_widget(csv, "evidence_table.csv", "text/csv", label="Download Evidence Table (CSV)")

    render_bottom_navigation()

# ------------------------------------------
# PHASE 3: DECISION SCIENCE
# ------------------------------------------
elif "Phase 3" in phase:
    
    cond = st.session_state.data['phase1']['condition']
    evidence_list = st.session_state.data['phase2']['evidence']
    nodes_exist = len(st.session_state.data['phase3']['nodes']) > 0
    
    if cond and not nodes_exist and not st.session_state.auto_run["p3_logic"]:
        with st.status("AI Agent drafting decision tree...", expanded=True) as status:
            titles = [e['title'] for e in evidence_list]
            prompt = f"""
            Act as a Clinical Decision Scientist. Build a Clinical Pathway for: {cond}.
            Evidence Titles: {json.dumps(titles)}

            CRITICAL LOGIC REQUIREMENT (Adhere to this specific flow):
            1. **Start Node:** Patient presentation.
            2. **Immediate Triage Sub-pathway Check:** Check for specific populations (e.g. Pregnancy, Hemodynamic Instability). If Yes -> Go to Sub-pathway. If No -> Continue.
            3. **Risk Stratification:** Use validated scores. Branch into Low/Moderate/High or specific score ranges (e.g. HEART <3, 4-5, >5). For each Decision node, include a 'branches' field: a list of objects with 'label' (e.g. 'Low Risk', 'Medium Risk', 'High Risk', '<3', '4-5', '>5') and 'target' (index of the next node for that branch).
            4. **Process Steps:** - **Diagnostics:** Use standard medical acronyms (e.g. BMP, UA, CBC, CT Abdomen and Pelvis).
               - **Medications:** Specify exact names (e.g. Flomax, Tamsulosin, NSAIDs, Ceftriaxone) and dosages.
               - **Consults:** Specify triggers (e.g. "If MRI pos for cauda equina -> STAT Neurosurgery consult").
               - **Discharge:** specific instructions (e.g. "Discharge with Amb Ref to Urology and prescribe NSAIDs").
            5. **Disposition:** Detailed discharge instructions.
            6. **Thresholds:** Ensure decision nodes have discrete, specific thresholds (e.g. "Creatinine > 2.0" rather than "High Kidney Function"). Reduce ambiguity.

            For each node, include:
            - type (Start, Decision, Process, Note, End)
            - label (short title)
            - detail (action-oriented, specific, e.g. labs, imaging, consults, discharge, etc.)
            - role (owner: nurse, physician, social worker, etc.)
            - evidence_id (PMID or evidence reference)
            - labs (if applicable)
            - imaging (if applicable)
            - medications (if applicable)
            - dosage (if applicable)
            - branches (for Decision nodes: list of {{label, target}} for multi-branch logic)
            - id (unique node id)

            Return JSON List of objects, in order:
            [{{ "type": "...", "label": "...", "detail": "...", "role": "...", "evidence_id": "...", "labs": "...", "imaging": "...", "medications": "...", "dosage": "...", "branches": [{{"label": "...", "target": ...}}], "id": "..." }}]
            """
            nodes = get_gemini_response(prompt, json_mode=True)
            if not isinstance(nodes, list):
                st.error("AI Agent could not generate a valid decision tree. Please try again or simplify your request.")
                status.update(label="Error: Invalid AI response.", state="error", expanded=True)
            # Auto-assign IDs if missing (D1, P1, S1 etc.)
            counts = {"Decision": 0, "Process": 0, "Start": 0, "End": 0, "Note": 0}
            for i, n in enumerate(nodes):
                if 'id' not in n:
                    ntype = n.get('type', 'Process')
                    counts[ntype] = counts.get(ntype, 0) + 1
                    prefix = ntype[0].upper()
                    n['id'] = f"{prefix}{counts[ntype]}"
            st.session_state.data['phase3']['nodes'] = nodes
            st.session_state.auto_run["p3_logic"] = True
            status.update(label="Decision Tree Drafted!", state="complete", expanded=False)
            st.rerun()

    if st.session_state.auto_run["p3_logic"]:
         if st.button("Add Manual Step"):
             st.session_state.data['phase3']['nodes'].append({"type": "Process", "label": "New Step", "detail": ""})
             st.rerun()

    if not st.session_state.data['phase3']['nodes']:
         st.session_state.data['phase3']['nodes'] = [{"type":"Start", "label":"Triage", "detail":""}]
    
    df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
    if "detail" not in df_nodes.columns: df_nodes["detail"] = ""
    if "role" not in df_nodes.columns: df_nodes["role"] = "Unassigned"
    if "evidence" not in df_nodes.columns: df_nodes["evidence"] = None
    if "id" not in df_nodes.columns: df_nodes["id"] = ""

    # Prepare Evidence Options (PMID Only)
    evidence_options = []
    pmid_list = []
    if st.session_state.data['phase2']['evidence']:
        pmid_list = [str(e['id']) for e in st.session_state.data['phase2']['evidence']]
        evidence_options = [f"PMID: {pmid}" for pmid in pmid_list]

    # Auto-populate Supporting Evidence with the most relevant PMID using AI
    if pmid_list and st.session_state.data['phase2']['evidence']:
        evidence_map = {str(e['id']): e for e in st.session_state.data['phase2']['evidence']}
        for idx, row in df_nodes.iterrows():
            if not row.get('evidence'):
                # Use AI to select the most relevant PMID for this node
                node_label = row.get('label', '')
                node_detail = row.get('detail', '')
                titles = [f"PMID: {e['id']} - {e['title']}" for e in st.session_state.data['phase2']['evidence']]
                prompt = f"""
                Given the following clinical pathway node:
                Label: {node_label}
                Detail: {node_detail}
                And these evidence options:
                {json.dumps(titles)}
                Select the single most relevant PMID (just the number) that best supports this node. If none are relevant, return an empty string.
                """
                best_pmid = get_gemini_response(prompt, json_mode=False)
                best_pmid = str(best_pmid).strip()
                if best_pmid and best_pmid in pmid_list:
                    df_nodes.at[idx, 'evidence'] = f"PMID: {best_pmid}"
                    df_nodes.at[idx, 'evidence_id'] = best_pmid
                else:
                    df_nodes.at[idx, 'evidence'] = None
                    df_nodes.at[idx, 'evidence_id'] = None
            elif row.get('evidence'):
                df_nodes.at[idx, 'evidence_id'] = str(row['evidence']).replace("PMID: ", "")

    edited_nodes = st.data_editor(df_nodes, column_config={
        "id": st.column_config.TextColumn("ID", width="small", disabled=True),
        "type": st.column_config.SelectboxColumn("Node Type", options=["Start", "Decision", "Process", "Note", "End"], required=True, width="medium"),
        "label": st.column_config.TextColumn("Label", width="medium"),
        "role": st.column_config.TextColumn("Role / Owner", width="small"),
        "detail": st.column_config.TextColumn("Clinical Detail", width="large"),
        "evidence": st.column_config.SelectboxColumn("Supporting Evidence", options=evidence_options, width="medium")
    }, num_rows="dynamic", hide_index=True, use_container_width=True, key="p3_editor")

    # Ensure IDs persist if added manually & sync evidence ID, and all required fields exist
    updated_nodes = []
    counts = {"Decision": 0, "Process": 0, "Start": 0, "End": 0, "Note": 0}
    required_fields = ["id", "type", "label", "detail", "role", "evidence", "evidence_id", "branches"]
    for n in edited_nodes.to_dict('records'):
        ntype = n.get('type', 'Process')
        counts[ntype] = counts.get(ntype, 0) + 1
        if not n.get('id'):
            prefix = ntype[0].upper()
            n['id'] = f"{prefix}{counts[ntype]}"
        # Evidence Logic
        if n.get('evidence'):
            try:
                n['evidence_id'] = str(n['evidence']).replace("PMID: ", "")
            except:
                n['evidence_id'] = None
        else:
            n['evidence_id'] = None
        # Ensure branches is always a list for Decision nodes
        if ntype.lower() == 'decision':
            if not isinstance(n.get('branches'), list):
                n['branches'] = []
        else:
            n['branches'] = []
        # Ensure all required fields exist
        for field in required_fields:
            if field not in n:
                if field == 'branches':
                    n[field] = []
                else:
                    n[field] = "" if field != 'evidence' and field != 'evidence_id' else None
        updated_nodes.append(n)
    st.session_state.data['phase3']['nodes'] = updated_nodes

    # After editing nodes in Phase 3, check for explicit branch labels
    for n in updated_nodes:
        if n.get('type', '').lower() == 'decision' and 'branches' in n and n['branches']:
            for branch in n['branches']:
                if isinstance(branch, dict):
                    label = branch.get('label', '').strip().lower()
                    # List of generic terms to flag
                    generic_terms = ["yes", "no", "high", "low", "medium", "positive", "negative", "present", "absent"]
                    if label in generic_terms or len(label) < 6:
                        st.warning(f"Branch label '{branch.get('label','')}' in node '{n.get('label','')}' is too generic. Please use explicit, action-oriented labels (e.g., 'Order BMP and UA').")
                else:
                    continue  # Skip non-dict branches

    render_bottom_navigation()

# ------------------------------------------
# PHASE 4: USER INTERFACE DESIGN
# ------------------------------------------
elif "Phase 4" in phase:
    col1, col2 = st.columns([2, 1])

    def generate_mermaid_code(nodes, orientation="TD"):
        # Validate nodes for required fields and types
        if not isinstance(nodes, list) or not nodes:
            return "flowchart TD\n%% No nodes to display"
        for n in nodes:
            if not isinstance(n, dict):
                return "flowchart TD\n%% Invalid node structure"
            for field in ["id", "type", "label", "detail", "role", "branches"]:
                if field not in n:
                    return "flowchart TD\n%% Missing required node fields"
            if n.get('type', '').lower() == 'decision' and not isinstance(n.get('branches'), list):
                return "flowchart TD\n%% Invalid branches structure"
        # Group nodes by owner/role for swimlanes
        from collections import defaultdict
        swimlanes = defaultdict(list)
        for i, n in enumerate(nodes):
            role = n.get('role', 'Unassigned')
            swimlanes[role].append((i, n))

        code = f"flowchart {orientation}\n"
        code += "    %% Swimlanes by Owner/Role\n"
        node_id_map = {}
        for role, node_list in swimlanes.items():
            code += f"    subgraph {role}\n"
            for i, n in node_list:
                nid = f"N{i}"
                node_id_map[i] = nid
                display_id = n.get('id', nid)
                safe_label = n.get('label', 'Step').replace('"', "'").strip()
                # Add action details for process steps
                details = n.get('detail', '').strip()
                if details:
                    safe_label += f"\\n{details}"
                # Add owner/role to label
                safe_label += f"\\n({role})"
                # Add labs, imaging, meds, dosages if present
                for key in ['labs', 'imaging', 'medications', 'dosage']:
                    val = n.get(key)
                    if val:
                        safe_label += f"\\n{key.capitalize()}: {val}"
                ntype = n.get('type', 'Process')
                if ntype == 'Start':
                    shape_open, shape_close = '([', '])'
                    style = f'style {nid} fill:#D5E8D4,stroke:#82B366,stroke-width:2px,color:#000'
                elif ntype == 'End':
                    shape_open, shape_close = '([', '])'
                    style = f'style {nid} fill:#D5E8D4,stroke:#82B366,stroke-width:2px,color:#000'
                elif ntype == 'Decision':
                    shape_open, shape_close = '{', '}'
                    style = f'style {nid} fill:#F8CECC,stroke:#B85450,stroke-width:2px,color:#000'
                elif ntype == 'Note':
                    shape_open, shape_close = '>', ']' 
                    style = f'style {nid} fill:#DAE8FC,stroke:#6C8EBF,stroke-width:1px,color:#000,stroke-dasharray: 5 5'
                else: 
                    shape_open, shape_close = '[', ']'
                    style = f'style {nid} fill:#FFF2CC,stroke:#D6B656,stroke-width:1px,color:#000'
                code += f'        {nid}{shape_open}"{display_id}: {safe_label}"{shape_close}\n'
                code += f'        {style}\n'
            code += "    end\n"

        code += "\n    %% Logic Flow\n"
        for i, n in enumerate(nodes):
            curr = node_id_map[i]
            ntype = n.get('type')
            # Multi-branch logic for risk/score-based decisions
            if ntype == 'Decision':
                # Check for custom branches (e.g., risk, score)
                branches = n.get('branches')
                if branches and isinstance(branches, list):
                    for b in branches:
                        label = b.get('label', 'Option')
                        target = b.get('target')
                        if target is not None and 0 <= target < len(nodes):
                            code += f'    {curr} --|{label}| {node_id_map[target]}\n'
                else:
                    # Default binary
                    if i+1 < len(nodes):
                        code += f'    {curr} --|Yes| {node_id_map[i+1]}\n'
                    if i+2 < len(nodes):
                        code += f'    {curr} --|No| {node_id_map[i+2]}\n'
            elif ntype == 'Note':
                if i > 0:
                    prev = node_id_map[i-1]
                    code += f'    {curr} -.- {prev}\n'
            elif i+1 < len(nodes) and nodes[i+1].get('type') != 'Note':
                code += f'    {curr} --> {node_id_map[i+1]}\n'
        return code

    with col1:
        st.subheader("Clinical Pathway Visualizer")
        # Removed non-functional Zoom In/High-Res Image radio/button
        with st.expander("Edit Pathway Data", expanded=False):
            df_p4 = pd.DataFrame(st.session_state.data['phase3']['nodes'])
            if "role" not in df_p4.columns: df_p4["role"] = "Unassigned"
            edited_p4 = st.data_editor(df_p4, num_rows="dynamic", key="p4_editor", use_container_width=True,
                column_config={"type": st.column_config.SelectboxColumn("Type", options=["Start", "Decision", "Process", "Note", "End"], width="small"),
                               "label": st.column_config.TextColumn("Label", width="medium"),
                               "detail": st.column_config.TextColumn("Details", width="large")})
            if not df_p4.equals(edited_p4):
                st.session_state.data['phase3']['nodes'] = edited_p4.to_dict('records')
                st.rerun()

        nodes = st.session_state.data['phase3']['nodes']

        if nodes:
            try:
                c_view1, c_view2 = st.columns([1, 2])
                with c_view1:
                    orientation = st.selectbox("Orientation", ["Vertical (TD)", "Horizontal (LR)"], index=0)
                    mermaid_orient = "TD" if "Vertical" in orientation else "LR"
                
                mermaid_code = generate_mermaid_code(nodes, mermaid_orient)
                mermaid_base64 = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
                image_url = f"https://mermaid.ink/img/{mermaid_base64}?bgColor=FFFFFF"
                
                with c_view2:
                    st.write("")
                    # Removed non-functional Zoom In / High-Res Image radio/button

                # Local Render using HTML/JS (Fixes "Error opening..." issues)
                html_code = f"""
                <div class="mermaid">
                {mermaid_code}
                </div>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                <script>mermaid.initialize({{startOnLoad:true}});</script>
                """
                components.html(html_code, height=600, scrolling=True)
                
                with st.expander("View Mermaid Syntax"):
                    st.code(mermaid_code, language='mermaid')

            except Exception as e:
                st.error(f"Visualization Error: {e}")
        else:
            st.info("No nodes defined. Please go back to Phase 3 or add nodes above.")

    with col2:
        st.subheader("Nielsen's Heuristics Analysis")
        nodes_json = json.dumps(nodes)
        if nodes and not st.session_state.auto_run["p4_heuristics"]:
            with st.spinner("AI Agent analyzing User Interface Design risks..."):
                prompt = f"""
                Act as a UX Researcher. Analyze this clinical pathway logic: {nodes_json}
                Evaluate it against **Jakob Nielsen's 10 Usability Heuristics**.
                For each heuristic, provide:
                1. A specific critique.
                2. A boolean 'actionable' flag.
                Return JSON: {{ "H1": {{ "insight": "...", "actionable": true }}, ... }}
                """
                risks = get_gemini_response(prompt, json_mode=True)
                if isinstance(risks, dict):
                    st.session_state.data['phase4']['heuristics_data'] = risks
                    st.session_state.auto_run["p4_heuristics"] = True
                    st.rerun()
                else:
                    st.warning("AI returned invalid or incomplete JSON for heuristics analysis. Please try again or edit the pathway for clarity. You may also manually enter critiques if needed.")
                    st.session_state.data['phase4']['heuristics_data'] = {}
                    st.session_state.auto_run["p4_heuristics"] = False

        risks = st.session_state.data['phase4'].get('heuristics_data', {})
        if risks:
            for k, v in risks.items():
                if isinstance(v, dict):
                    insight = v.get('insight', 'No insight.')
                    is_actionable = v.get('actionable', False)
                else:
                    insight = str(v)
                    is_actionable = True
                
                def_name = HEURISTIC_DEFS.get(k, "Heuristic").split(":")[0]
                full_def = HEURISTIC_DEFS.get(k, "No definition.")
                
                # Use Help parameter to show definition on hover
                label = f"{k}: {def_name}"
                
                with st.expander(label, expanded=False):
                    st.markdown(f"**Definition:** *{full_def}*")
                    st.markdown(f"""<div style="background-color: #FDF2F5; color: #5D4037; padding: 10px; border-radius: 4px; border-left: 4px solid #9E4244;"><strong>Critique:</strong> {insight}</div>""", unsafe_allow_html=True)
                    
                    if is_actionable:
                        applied_key = f"heuristic_applied_{k}"
                        if applied_key not in st.session_state: st.session_state[applied_key] = False
                        
                        if not st.session_state[applied_key]:
                            if st.button("Apply Recommendations", key=f"btn_fix_{k}", use_container_width=True):
                                with st.spinner("Applying fix..."):
                                    if 'node_history' not in st.session_state: st.session_state.node_history = []
                                    st.session_state.node_history.append(copy.deepcopy(st.session_state.data['phase3']['nodes']))
                                    prompt_fix = f"""
                                    Act as a Clinical Decision Scientist.
                                    Update this pathway JSON to address the critique: "{insight}"
                                    Current JSON: {json.dumps(st.session_state.data['phase3']['nodes'])}
                                    Return ONLY valid JSON.
                                    """
                                    new_nodes = get_gemini_response(prompt_fix, json_mode=True)
                                    if new_nodes and isinstance(new_nodes, list):
                                        st.session_state.data['phase3']['nodes'] = new_nodes
                                        st.session_state[applied_key] = True
                                        st.rerun()
                        else:
                            st.button("Recommendations Applied", disabled=True, key=f"btn_applied_{k}")

            st.divider()
            c_undo, c_rerun = st.columns(2)
            with c_undo:
                if 'node_history' in st.session_state and st.session_state.node_history:
                    if st.button("Undo Last Change", type="secondary", use_container_width=True):
                        st.session_state.data['phase3']['nodes'] = st.session_state.node_history.pop()
                        st.rerun()
            with c_rerun:
                if st.button("Rerun Heuristics Analysis", type="secondary", use_container_width=True):
                    st.session_state.auto_run["p4_heuristics"] = False
                    st.rerun()

            st.divider()
            
            custom_edit = st.text_area("Custom Refinement", placeholder="E.g., 'Add a blood pressure check after triage'", label_visibility="collapsed")
            if 'custom_edit_applied' not in st.session_state:
                st.session_state['custom_edit_applied'] = False

            btn_label = "Changes Applied" if st.session_state['custom_edit_applied'] else "Apply Changes"
            btn_disabled = st.session_state['custom_edit_applied']
            if st.button(btn_label, type="primary", use_container_width=True, disabled=btn_disabled):
                if custom_edit and not st.session_state['custom_edit_applied']:
                    with st.spinner("Applying edit..."):
                        if 'node_history' not in st.session_state: st.session_state.node_history = []
                        st.session_state.node_history.append(copy.deepcopy(st.session_state.data['phase3']['nodes']))
                        prompt_custom = f"""
                        Update this pathway JSON based on user request: "{custom_edit}"
                        Current JSON: {json.dumps(st.session_state.data['phase3']['nodes'])}
                        Return ONLY valid JSON.
                        """
                        new_nodes = get_gemini_response(prompt_custom, json_mode=True)
                        if new_nodes and isinstance(new_nodes, list):
                            st.session_state.data['phase3']['nodes'] = new_nodes
                            st.session_state['custom_edit_applied'] = True
                            st.rerun()
            if not custom_edit:
                st.session_state['custom_edit_applied'] = False

    render_bottom_navigation()

# ------------------------------------------
# PHASE 5: OPERATIONALIZE
# ------------------------------------------
elif "Phase 5" in phase:
    st.markdown("### Operational Toolkit & Deployment")
    
    # 1. Target Audience
    st.subheader("Target Audience")
    if 'target_audience' not in st.session_state: st.session_state.target_audience = "Multidisciplinary Team"
    new_audience = st.text_input("Define Primary Audience:", value=st.session_state.target_audience)
    if new_audience != st.session_state.target_audience:
        st.session_state.target_audience = new_audience
        st.session_state.auto_run["p5_assets"] = False
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
    if b3.button("Informaticists", use_container_width=True): 
        st.session_state.target_audience = "Informaticists"
        st.session_state.auto_run["p5_assets"] = False
        st.rerun()

    st.divider()

    # 2. Asset Generation Options (no format radio, always generate all)
    if "p5_files" not in st.session_state:
        st.session_state.p5_files = {"pptx": None, "csv": None, "html": None, "interactive_html": None, "beta_html": None, "feedback_pdf_html": None, "beta_pdf_html": None}

    if not st.session_state.auto_run.get("p5_assets", False):
        with st.status(f"Generating Assets...", expanded=True) as status:
            cond = st.session_state.data['phase1']['condition']
            audience = st.session_state.target_audience

            # HTML FEEDBACK FORM (with italicized instructions)
            instr = "<br><i>If so, please list their numbers below and the recommended modifications with either an evidence-based or resource requirement justification for the change.</i>"
            q1 = f"1. Do you recommend any modifications to the start or end nodes of the pathway?{instr}"
            q2 = f"2. Do you recommend any modifications to the decision nodes?{instr}"
            q3 = f"3. Do you recommend any modifications to the process steps?{instr}"
            q_html = f"<p><b>{q1}</b><br><textarea style='width:100%; height:80px;'></textarea></p>"
            q_html += f"<p><b>{q2}</b><br><textarea style='width:100%; height:80px;'></textarea></p>"
            q_html += f"<p><b>{q3}</b><br><textarea style='width:100%; height:80px;'></textarea></p>"
            feedback_html = f"<html><body><h2>Feedback: {cond}</h2>{q_html}<br><button onclick=\"navigator.clipboard.writeText(document.body.innerText);alert('Copied!')\">Copy All to Clipboard</button></body></html>"
            feedback_pdf_html = f"<html><body><h2>Feedback: {cond}</h2>{q_html}</body></html>"
            st.session_state.p5_files["html"] = feedback_html
            st.session_state.p5_files["feedback_pdf_html"] = feedback_pdf_html

            # BETA TESTING GUIDE (HTML, not docx)
            prompt_guide = f"""
            Create a Beta Testing Guide for '{cond}' pathway. Target User: {audience}.
            Structure: Title, Checklist, Questions, Feedback Instructions. 
            Output as clean HTML, not Word or markdown.
            """
            guide_html = get_gemini_response(prompt_guide)
            if guide_html:
                st.session_state.p5_files["beta_html"] = guide_html
                st.session_state.p5_files["beta_pdf_html"] = guide_html

            # SLIDE DECK (PPTX)
            prompt_slides = f"""
            Act as a Senior Graphic Designer. Create a visually appealing slide deck structure for '{cond}'. Audience: {audience}.
            Content should be sophisticated.
            Return JSON: {{ "title": "...", "slides": [ {{ "title": "...", "content": "..." }} ] }}
            CRITICAL: Do NOT use markdown symbols in the content strings. Plain text only.
            """
            slides_json = get_gemini_response(prompt_slides, json_mode=True)
            if isinstance(slides_json, dict): st.session_state.p5_files["pptx"] = create_ppt_presentation(slides_json)

            # STAFF EDUCATION MODULE WITH QUIZ
            prompt_staff_edu = f"""
            Create a Staff Education Module for '{cond}'.
            Include:
            1. 3-5 key clinical points (bulleted).
            2. A 3-question multiple choice quiz (with answers and explanations).
            Output as clean HTML with a copy-to-clipboard button for the whole module.
            """
            staff_edu_html = get_gemini_response(prompt_staff_edu)
            if staff_edu_html:
                st.session_state.p5_files["staff_edu_html"] = staff_edu_html

            st.session_state.auto_run["p5_assets"] = True
            status.update(label="Assets Generated!", state="complete", expanded=False)
            st.rerun()

    # 3. HTML Deliverables
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Expert Panel Feedback Form")
        if st.session_state.p5_files.get("html"):
            st.download_button("Download Form (HTML)", st.session_state.p5_files["html"], "Expert_Panel_Feedback.html", "text/html", type="primary")
    with c2:
        st.subheader("Beta Testing Guide")
        if st.session_state.p5_files.get("beta_html"):
            st.download_button("Download Guide (HTML)", st.session_state.p5_files["beta_html"], "Beta_Guide.html", "text/html", type="primary")
    with c3:
        st.subheader("Staff Education Module")
        if st.session_state.p5_files.get("staff_edu_html"):
            st.download_button("Download Module (HTML)", st.session_state.p5_files["staff_edu_html"], "Staff_Education_Module.html", "text/html", type="primary")

    st.divider()
    
    if st.button("Regenerate Assets"):
        st.session_state.auto_run["p5_assets"] = False
        st.rerun()
    
    # 4. Executive Summary
    if st.button("Generate Executive Summary", use_container_width=True):
        with st.spinner("Compiling Executive Summary..."):
            p1 = st.session_state.data['phase1']
            
            # Calculate metrics
            num_citations = len(st.session_state.data['phase2']['evidence'])
            num_nodes = len(st.session_state.data['phase3']['nodes'])
            
            prompt = f"""
            Create an Executive Summary for '{p1['condition']}'. 
            Target Audience: Hospital Executives (C-Suite).
            
            Include:
            1. Problem Statement
            2. Objectives
            3. Evidence Overview (Mention {num_citations} high-quality citations integrated).
            4. Logic Overview (Mention a robust decision tree with {num_nodes} clinical nodes).
            5. Strategic Value (ROI, Quality, Safety).
            
            Format: Markdown.
            """
            summary = get_gemini_response(prompt)
            st.session_state.data['phase5']['exec_summary'] = summary
            
    if st.session_state.data['phase5'].get('exec_summary'):
        st.markdown("### Executive Summary")
        st.markdown(st.session_state.data['phase5']['exec_summary'])
        export_widget(st.session_state.data['phase5']['exec_summary'], "executive_summary.md", label="Download Summary")

    render_bottom_navigation()

st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)