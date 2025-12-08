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
from datetime import date
import os
import copy

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
        "p2_query": False,
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
        GREY = RGBColor(100, 100, 100)
    except NameError:
        return None
    
    # Helper: Add Footer & Logo
    def add_branding(slide):
        # Footer Text Box at bottom center
        left = Inches(0.5)
        top = Inches(7.1)
        width = Inches(9)
        height = Inches(0.3)
        
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = "CarePathIQ © 2024 by Tehreem Rehman | Confidential Internal Document"
        p.font.size = Pt(10)
        p.font.color.rgb = GREY
        p.alignment = PP_ALIGN.CENTER

        # Logo removed per user request
        # if os.path.exists("CarePathIQ_Logo.png"):
        #     try:
        #         slide.shapes.add_picture("CarePathIQ_Logo.png", Inches(8.5), Inches(0.2), width=Inches(1.2))
        #     except Exception:
        #         pass

    # 1. Title Slide
    slide = prs.slides.add_slide(prs.slide_layouts[0]) # Title Slide Layout
    
    # Title
    title = slide.shapes.title
    title.text = slides_data.get('title', 'Clinical Pathway Launch')
    title.text_frame.paragraphs[0].font.color.rgb = BROWN
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.size = Pt(44)
    
    # Subtitle
    if len(slide.placeholders) > 1:
        subtitle = slide.placeholders[1]
        subtitle.text = f"Target Audience: {slides_data.get('audience', 'General')}\nGenerated by CarePathIQ AI Agent"
        subtitle.text_frame.paragraphs[0].font.color.rgb = TEAL
        subtitle.text_frame.paragraphs[0].font.size = Pt(24)
    
    add_branding(slide)

    # 2. Content Slides
    for slide_info in slides_data.get('slides', []):
        # Determine Layout
        # Layout 1 = Title + Content (Bullets)
        # Layout 5 = Title Only (Best for Images)
        layout_idx = 1
        if "Format" in slide_info.get('title', '') and flowchart_img:
            layout_idx = 5 
            
        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
        
        # Set Title
        if slide.shapes.title:
            title_shape = slide.shapes.title
            title_shape.text = slide_info.get('title', 'Untitled')
            title_shape.text_frame.paragraphs[0].font.color.rgb = BROWN
            title_shape.text_frame.paragraphs[0].font.size = Pt(32)
            title_shape.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        
        # Set Content
        if layout_idx == 1:
            # Standard Bulleted List
            if len(slide.placeholders) > 1:
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                # Ensure content is a string and not None
                content_text = slide_info.get('content', '')
                if content_text is None: content_text = ""
                tf.text = str(content_text)
                
                # Style paragraphs
                for p in tf.paragraphs:
                    p.font.size = Pt(20)
                    p.space_after = Pt(12)
                    
        elif layout_idx == 5:
            # Flowchart Slide
            if flowchart_img:
                try:
                    flowchart_img.seek(0)
                    # Center the image: Slide width ~10", Height ~7.5"
                    # We place it below title (approx 1.5" down)
                    slide.shapes.add_picture(flowchart_img, Inches(0.5), Inches(1.5), width=Inches(9), height=Inches(5.0))
                except Exception as e:
                    print(f"Image Error: {e}")
        
        add_branding(slide)

    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer

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
            st.info("Please wait a minute before trying again, or use a different API key.")
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
                prompt = f"Act as a CMO. For condition '{curr_cond}' in setting '{curr_setting}' with inclusion '{curr_inc}', suggest a 'problem' statement (clinical gap). Return JSON with key: 'problem'."
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
                today_str = date.today().strftime("%B %d, %Y")

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
                5. **Tentative Schedule**: A table with columns [Key Milestone | Start | Finish] including these standard phases:
                     - Form Project Team and Conduct Preliminary Review
                     - Finalize Project Plan and Project Charter
                     - Conduct Definition Phase
                     - Conduct Measurement Phase
                     - Conduct Analysis Phase
                     - Conduct Improvement Phase
                     - Conduct Control Phase
                     - Close Out Project and Write Summary Report
                
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
    # --- A. AUTO-RUN: PICO & SEARCH STRATEGY ---
    # Trigger only if we have a condition and haven't run yet
    p1_cond = st.session_state.data['phase1'].get('condition', '')
    
    # 1. PICO GENERATION (From Phase 1)
    if p1_cond and not st.session_state.auto_run.get("p2_pico", False):
        with st.spinner("AI Agent drafting PICO framework..."):
            
            # Generate PICO
            problem_context = st.session_state.data['phase1'].get('problem', '')
            setting_context = st.session_state.data['phase1'].get('setting', '')
            prompt_pico = f"""
            Act as a Medical Librarian. Define the PICO framework for: '{p1_cond}'.
            Context: {problem_context}
            Setting: {setting_context}
            Return a valid JSON object with these keys: {{ "P": "...", "I": "...", "C": "...", "O": "..." }}
            """
            pico_data = get_gemini_response(prompt_pico, json_mode=True)
            
            if pico_data:
                # Ensure strings for all PICO fields
                st.session_state.data['phase2']['pico_p'] = str(pico_data.get("P", "") or "")
                st.session_state.data['phase2']['pico_i'] = str(pico_data.get("I", "") or "")
                st.session_state.data['phase2']['pico_c'] = str(pico_data.get("C", "") or "")
                st.session_state.data['phase2']['pico_o'] = str(pico_data.get("O", "") or "")
            
            st.session_state.auto_run["p2_pico"] = True
            # Force query update since PICO changed
            st.session_state.auto_run["p2_query"] = False

    # 2. QUERY GENERATION (From PICO)
    # Run if query is stale (p2_query=False) AND we have PICO data
    has_pico = any(st.session_state.data['phase2'].get(k) for k in ['pico_p', 'pico_i', 'pico_c', 'pico_o'])
    
    if has_pico and not st.session_state.auto_run.get("p2_query", False):
        with st.spinner("AI Agent drafting Search Query..."):
            # Retrieve PICO
            p = st.session_state.data['phase2']['pico_p']
            i = st.session_state.data['phase2']['pico_i']
            o = st.session_state.data['phase2']['pico_o']
            
            # Retrieve Phase 1 context
            inc = st.session_state.data['phase1'].get('inclusion', '')
            setting = st.session_state.data['phase1'].get('setting', '')

            prompt_mesh = f"""
            Construct a PubMed search query for: {p1_cond}.
            
            The query MUST start with the exact phrase: "clinical pathway or evidence based guideline for"
            
            Followed by the KEY TERMS extracted from the PICO elements:
            - Population: {p}
            - Intervention: {i}
            - Outcome: {o}
            
            Example: "clinical pathway or evidence based guideline for Sepsis Antibiotics Mortality"
            
            OUTPUT FORMAT:
            - Return ONLY the raw query string.
            - Do NOT use markdown blocks.
            """
            raw_query = get_gemini_response(prompt_mesh)
            
            # Clean the query string to prevent broken links
            if raw_query:
                clean_query = raw_query.replace('```', '').replace('\n', ' ').strip()
                st.session_state.data['phase2']['mesh_query'] = clean_query
            
            st.session_state.auto_run["p2_query"] = True
            st.rerun()

    # --- B. UI: PICO INPUTS ---
    col1, col2 = st.columns([1, 2])
    
    # Helper to sync Phase 2 widgets
    def sync_p2_widgets():
        st.session_state.data['phase2']['pico_p'] = st.session_state.get('p2_p', '')
        st.session_state.data['phase2']['pico_i'] = st.session_state.get('p2_i', '')
        st.session_state.data['phase2']['pico_c'] = st.session_state.get('p2_c', '')
        st.session_state.data['phase2']['pico_o'] = st.session_state.get('p2_o', '')
        st.session_state.data['phase2']['mesh_query'] = st.session_state.get('p2_query_box', '')

    # Initialize keys if missing
    if 'p2_p' not in st.session_state: st.session_state['p2_p'] = st.session_state.data['phase2'].get('pico_p', '')
    if 'p2_i' not in st.session_state: st.session_state['p2_i'] = st.session_state.data['phase2'].get('pico_i', '')
    if 'p2_c' not in st.session_state: st.session_state['p2_c'] = st.session_state.data['phase2'].get('pico_c', '')
    if 'p2_o' not in st.session_state: st.session_state['p2_o'] = st.session_state.data['phase2'].get('pico_o', '')
    if 'p2_query_box' not in st.session_state: st.session_state['p2_query_box'] = st.session_state.data['phase2'].get('mesh_query', '')

    with col1:
        st.markdown("#### PICO Framework")
        
        st.text_input("P (Population)", key="p2_p", on_change=sync_p2_widgets)
        st.text_input("I (Intervention)", key="p2_i", on_change=sync_p2_widgets)
        st.text_input("C (Comparison)", key="p2_c", on_change=sync_p2_widgets)
        st.text_input("O (Outcome)", key="p2_o", on_change=sync_p2_widgets)
        
        st.divider()
        
        if st.button("Regenerate Query from PICO", type="secondary", use_container_width=True):
            st.session_state.auto_run["p2_query"] = False # Force re-run QUERY logic only
            st.rerun()

    # --- C. UI: SEARCH & GRADE ---
    with col2:
        st.markdown("#### Literature Search Strategy")
        
        # Search Query Text Area
        st.text_area("PubMed Search Query", height=150, key="p2_query_box", on_change=sync_p2_widgets)
        
        # Define search_q from widget state to fix NameError
        search_q = st.session_state.p2_query_box

        # Action Buttons Row
        c_act1, c_act2 = st.columns([1, 1])
        
        with c_act1:
            # GRADE Button
            grade_help = "The GRADE framework (Grading of Recommendations Assessment, Development and Evaluation) is a transparent approach to grading the quality of evidence (High, Moderate, Low, Very Low) and the strength of recommendations."
            if st.button("Search & GRADE Evidence", help=grade_help, type="primary", use_container_width=True):
                if not search_q.strip():
                    st.error("Query is empty.")
                else:
                    with st.spinner("Fetching PubMed results..."):
                        results = search_pubmed(search_q)
                        if not results:
                            st.warning("No results found. Try simplifying the query.")
                        else:
                            # Add new results to session state, avoiding duplicates
                            existing_ids = {e['id'] for e in st.session_state.data['phase2']['evidence']}
                            new_items = [r for r in results if r['id'] not in existing_ids]
                            st.session_state.data['phase2']['evidence'].extend(new_items)
                            
                            if new_items:
                                st.toast(f"Added {len(new_items)} new papers.", icon="📚")
                                # Reset grade flag to trigger analysis on next pass
                                st.session_state.auto_run["p2_grade"] = False 
                                st.rerun()
                            else:
                                st.info("No new papers found (duplicates skipped).")

        with c_act2:
            # PubMed Link Button (Safe Logic)
            if search_q.strip():
                # Encode the query safely for URL
                encoded_query = urllib.parse.quote(search_q.strip())
                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={encoded_query}"
                st.link_button("Open in PubMed ↗", pubmed_url, type="primary", use_container_width=True)
            else:
                st.button("Open in PubMed ↗", disabled=True, use_container_width=True)

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
            
            # Clear Button
            if st.button("Clear Evidence List", key="clear_ev"):
                st.session_state.data['phase2']['evidence'] = []
                st.session_state.auto_run["p2_grade"] = False
                st.rerun()

            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            
            # Ensure columns exist
            if 'rationale' not in df.columns: df['rationale'] = ""
            if 'grade' not in df.columns: df['grade'] = "Un-graded"

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
                    "GRADE Rationale",
                    help="Factors: Risk of Bias, Inconsistency, Indirectness, Imprecision",
                    width="large"
                ),
                "citation": st.column_config.TextColumn("Citation", disabled=True),
            }, column_order=["title", "grade", "rationale", "url"], hide_index=True, key="ev_editor")
            
            # Save manual edits back to state
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            
            # CSV Download
            csv = edited_df.to_csv(index=False)
            export_widget(csv, "evidence_table.csv", "text/csv", label="Download Evidence Table (CSV)")

# ------------------------------------------
# PHASE 3: DECISION SCIENCE
# ------------------------------------------
elif "Phase 3" in phase:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # DARK GREEN INSTRUCTIONS
        st.markdown("""
        <div style="background-color: #2E7D32; padding: 15px; border-radius: 5px; color: white; margin-bottom: 20px;">
            <strong>Decision Design Instructions:</strong><br>
            Define the clinical logic flow. This data powers the visual flowchart in Phase 4.<br><br>
            <strong>Standard Node Types:</strong>
            <ul>
                <li><span style="color:#ffcccc; font-weight:bold; color:black; padding:0 4px;">Red Diamond</span>: Decision (Binary Yes/No)</li>
                <li><span style="color:#fff2cc; font-weight:bold; color:black; padding:0 4px;">Yellow Box</span>: Process Step (Action/Order)</li>
                <li><span style="color:#dae8fc; font-weight:bold; color:black; padding:0 4px;">Blue Wave</span>: Note (Red Flags OR Clarifications)</li>
                <li><span style="color:#d5e8d4; font-weight:bold; color:black; padding:0 4px;">Green Oval</span>: Start / End</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # AUTO-RUN: LOGIC DRAFT
        cond = st.session_state.data['phase1']['condition']
        evidence_list = st.session_state.data['phase2']['evidence']
        nodes_exist = len(st.session_state.data['phase3']['nodes']) > 0
        
        if cond and not nodes_exist and not st.session_state.auto_run["p3_logic"]:
             with st.status("AI Agent drafting decision tree...", expanded=True) as status:
                 
                 # Prepare Evidence Context
                 st.write("Analyzing Phase 2 Evidence...")
                 ev_context = "\n".join([f"- ID {e['id']}: {e.get('title','')} (GRADE: {e.get('grade','Un-graded')})" for e in evidence_list])
                 
                 # ENHANCED PROMPT: BROADENED DEFINITIONS
                 st.write("Structuring Clinical Logic...")
                 prompt = f"""
                 Act as a Clinical Decision Scientist. Build a Clinical Pathway for: {cond}.
                 
                 STRICT TEMPLATE RULES (Match the user's Visual Logic Language):
                 1. **Start**: Entry point (e.g., "Patient presents to ED").
                 2. **Decisions (Red Diamonds)**: Binary checkpoints (e.g., "Is patient pregnant?", "Stone < 5mm?").
                 3. **Process (Yellow Box)**: Clinical actions (e.g., "Order CT Abdomen", "Consult Urology").
                 4. **Notes (Blue Wave)**: Use these for **Red Flags** (exclusion criteria/safety checks) OR **Clarifications** (clinical context/dosage info).
                 5. **End (Green Oval)**: The logical conclusion of a branch. This is often a final disposition (Discharge, Admit), but can be any terminal step appropriate for the logic.
                 
                 **Logic Structure Strategy (CRITICAL):**
                 - **Decisions**: Must ALWAYS have a 'Yes' and 'No' path.
                 - **Red Flags**: Should be represented as 'Notes' (Blue Wave) attached to relevant steps, OR as 'Decisions' (e.g., "Red flags present?") leading to different outcomes.
                 - **Flow**: Ensure a logical progression from Start to End.
                 
                 **Evidence Mapping:**
                 - For each step, if a specific piece of evidence from the list below supports it, include the "evidence_id" (e.g., "12345").
                 
                 Context Evidence:
                 {ev_context}
                 
                 Return a JSON List of objects: 
                 [{{
                     "type": "Start" | "Decision" | "Process" | "Note" | "End", 
                     "label": "Short Text (Max 6 words)", 
                     "detail": "Longer clinical detail/criteria",
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
                                 n['evidence'] = f"ID {match['id']}: {match['title'][:30]}... ({match.get('grade','?')})"
                             else:
                                 n['evidence'] = None
                         else:
                             n['evidence'] = None

                     st.session_state.data['phase3']['nodes'] = nodes
                     st.session_state.auto_run["p3_logic"] = True
                     status.update(label="Decision Tree Drafted!", state="complete", expanded=False)
                     st.rerun()

    with col2:
        if st.session_state.auto_run["p3_logic"]:
             st.markdown("""
            <div style="background-color: #5D4037; padding: 10px; border-radius: 5px; color: white; margin-bottom: 10px;">
                <strong>AI Agent Output:</strong> Logic generated. <br>
                <strong>Review Below:</strong> Ensure 'Decisions' are followed by their 'Yes' path.
            </div>
            """, unsafe_allow_html=True)
             
             c_btn1, c_btn2 = st.columns([1,1])
             with c_btn1:
                 if st.button("Clear Logic to Restart", type="primary"):
                     st.session_state.data['phase3']['nodes'] = []
                     st.session_state.auto_run["p3_logic"] = True # Prevent immediate auto-run
                     st.rerun()
             with c_btn2:
                 if st.button("Add Manual Step"):
                     st.session_state.data['phase3']['nodes'].append({"type": "Process", "label": "New Step", "detail": ""})
                     st.rerun()

        # DYNAMIC EVIDENCE DROPDOWN & EDITOR
        if not st.session_state.data['phase3']['nodes']:
             st.session_state.data['phase3']['nodes'] = [{"type":"Start", "label":"Triage", "detail":""}]
        
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        
        # Ensure columns exist
        if "detail" not in df_nodes.columns: df_nodes["detail"] = ""
        if "evidence" not in df_nodes.columns: df_nodes["evidence"] = None

        # Prepare Evidence Options
        evidence_options = []
        if st.session_state.data['phase2']['evidence']:
            evidence_options = [f"ID {e['id']}: {e['title'][:30]}... ({e.get('grade','?')})" for e in st.session_state.data['phase2']['evidence']]
        
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
            "detail": st.column_config.TextColumn(
                "Clinical Detail / Criteria", 
                help="Specifics (e.g. 'Serum Cr > 2.0', 'Failed PO trial')",
                width="large"
            ),
            "evidence": st.column_config.SelectboxColumn(
                "Supporting Evidence",
                options=evidence_options,
                help="Link to Phase 2 Evidence",
                width="large"
            )
        }, num_rows="dynamic", hide_index=True, use_container_width=True, key="p3_editor")
        
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# ------------------------------------------
# PHASE 4: USER INTERFACE DESIGN
# ------------------------------------------
elif "Phase 4" in phase:
    
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
                <strong>AI Design Critique:</strong> Review these insights to improve your pathway's usability.
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
                                - Maintain the existing structure and keys.
                                - Only make necessary changes.
                                - Return ONLY the valid JSON list of nodes.
                                """
                                new_nodes = get_gemini_response(prompt_fix, json_mode=True)
                                
                                if new_nodes and isinstance(new_nodes, list):
                                    st.session_state.data['phase3']['nodes'] = new_nodes
                                    st.success("Pathway updated!")
                                    time.sleep(1)
                                    st.rerun()
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
            
            if st.button("Refresh Analysis (After Edits)", type="secondary", use_container_width=True):
                 st.session_state.auto_run["p4_heuristics"] = False
                 st.rerun()

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
            Format: Markdown (to be converted to Word).
            
            Include:
            1. Title: Beta Testing Instructions.
            2. Section: Pre-Test Checklist.
            3. Section: "Questions for the End User" (Usability, Clarity, Workflow Fit).
            4. Section: Feedback Submission Instructions.
            """
            guide_text = get_gemini_response(prompt_guide)
            if guide_text:
                st.session_state.p5_files["docx"] = create_word_docx(guide_text)

            # --- HTML FORM (INTERACTIVE FEEDBACK) ---
            st.write("Designing Feedback Form (HTML)...")
            prompt_form = f"""
            Act as a UX Researcher. Create 5 specific feedback questions for beta testers of the '{cond}' pathway.
            Target Audience: {audience}.
            Return a JSON list of strings (the questions).
            """
            questions = get_gemini_response(prompt_form, json_mode=True)
            if isinstance(questions, list):
                q_html = ""
                for i, q in enumerate(questions):
                    q_html += f'<div style="margin-bottom: 15px;"><label style="font-weight:bold; display:block; margin-bottom:5px;">{i+1}. {q}</label><textarea style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px;" rows="3"></textarea></div>'
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>CarePathIQ Beta Feedback</title>
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
                        function sendEmail() {{
                            var recipient = document.getElementById('recipient').value;
                            if (!recipient) {{ alert('Please enter a recipient email.'); return; }}
                            
                            var body = "BETA FEEDBACK RESULTS:\\n\\n";
                            var textareas = document.getElementsByTagName('textarea');
                            var labels = document.getElementsByTagName('label');
                            
                            for (var i = 0; i < textareas.length; i++) {{
                                body += labels[i].innerText + "\\n" + textareas[i].value + "\\n\\n";
                            }}
                            
                            var subject = "CarePathIQ Feedback: {cond}";
                            window.location.href = 'mailto:' + recipient + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
                        }}
                    </script>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">CarePathIQ</div>
                            <p>Clinical Pathway Beta Feedback Form</p>
                        </div>
                        
                        <p><strong>Pathway:</strong> {cond}</p>
                        <p><strong>Audience:</strong> {audience}</p>
                        <hr>
                        
                        <form onsubmit="event.preventDefault(); sendEmail();">
                            <div style="margin-bottom: 20px; background-color: #eef; padding: 10px; border-radius: 5px;">
                                <label style="font-weight:bold;">Send Results To (Email):</label>
                                <input type="email" id="recipient" placeholder="manager@hospital.org" style="width:100%; padding:8px; margin-top:5px;" required>
                            </div>
                            
                            {q_html}
                            
                            <button type="submit" class="btn">Submit Feedback (via Email)</button>
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
            
            Return a JSON Object with this structure:
            {{
                "title": "Main Presentation Title",
                "audience": "{audience}",
                "slides": [
                    {{"title": "Clinical Gap", "content": "Describe the gap: {prob}"}},
                    {{"title": "Scope", "content": "..."}},
                    {{"title": "Objectives", "content": "Goals: {goals}"}},
                    {{"title": "Format", "content": "This slide displays the visual flowchart segment (Image inserted automatically)."}},
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
        st.info("Format: Word Document (.docx)")
        if st.session_state.p5_files["docx"]:
            st.download_button(
                label="Download Guide (.docx)",
                data=st.session_state.p5_files["docx"],
                file_name="Beta_Testing_Guide.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )

    with c2:
        st.subheader("Interactive Feedback Form")
        st.info("Format: HTML (Google Form Alternative)")
        if st.session_state.p5_files.get("html"):
            st.download_button(
                label="Download Form (.html)",
                data=st.session_state.p5_files["html"],
                file_name="Beta_Feedback_Form.html",
                mime="text/html",
                type="primary"
            )

    with c3:
        st.subheader("Education Deck")
        st.info(f"Audience: {st.session_state.target_audience}\nFormat: PowerPoint (.pptx)")
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
