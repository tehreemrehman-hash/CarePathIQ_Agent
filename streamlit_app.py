import streamlit as st
import google.generativeai as genai
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
import time
from io import BytesIO

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
        <span style="white-space: nowrap; margin-left: 5px;">
            <img src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt="CC" style="height:1.2em; vertical-align:middle;">
            <img src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt="BY" style="height:1.2em; vertical-align:middle;">
            <img src="https://mirrors.creativecommons.org/presskit/icons/sa.svg" alt="SA" style="height:1.2em; vertical-align:middle;">
        </span>
    </p>
</div>
"""

# ==========================================
# 2. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="CarePathIQ AI Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Mint Color Styling
st.markdown("""
<style>
    /* Main Buttons (Mint) */
    div.stButton > button {
        background-color: #4DB6AC; 
        color: white;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #26A69A;
        color: white;
    }
    /* Phase Selection Radio Buttons */
    div[role="radiogroup"] > label > div:first-child {
        background-color: #E0F2F1;
    }
    h1, h2, h3 { color: #00695C; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONFIG ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
    st.title("AI Agent")
    st.divider()
    
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Use Google AI Studio Key")
    
    # UPDATED MODEL LIST TO 2.5 SERIES
    model_choice = st.selectbox("AI Model", ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-pro-preview"], index=0)
    
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        st.success(f"✅ Connected: {model_choice}")
    else:
        st.warning("⚠️ Enter API Key to activate.")
        
    st.divider()
    st.info(f"Current Phase: {st.session_state.get('current_phase_label', 'Start')}")

# --- SESSION STATE INITIALIZATION ---
if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "", "population": "", "setting": "", "problem": "", "objectives": ""},
        "phase2": {"evidence": [], "pico_p": "", "pico_i": "", "pico_c": "", "pico_o": "", "mesh_query": ""},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}}, 
        "phase5": {"beta_email": "", "beta_content": "", "slides": "", "epic_csv": ""} 
    }

if "suggestions" not in st.session_state:
    st.session_state.suggestions = {}

# ==========================================
# 3. ROBUST AI FUNCTIONS
# ==========================================
def get_gemini_response(prompt, json_mode=False):
    if not gemini_api_key: return None
    try:
        model = genai.GenerativeModel(model_choice)
        # Clinical content often triggers default safety filters, so we disable them for medical context
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        text = response.text
        
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            # Attempt to find the first '{' and last '}' to handle chatty preambles
            start_idx = text.find('{') if '{' in text else text.find('[')
            end_idx = text.rfind('}') + 1 if '}' in text else text.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx]
            return json.loads(text)
        return text
    except Exception as e:
        st.error(f"AI Error ({model_choice}): {e}")
        return None

def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        search_params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': 5}
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            id_list = data.get('esearchresult', {}).get('idlist', [])
        
        if not id_list: return []
        
        summary_params = {'db': 'pubmed', 'id': ','.join(id_list), 'retmode': 'json'}
        url = base_url + "esummary.fcgi?" + urllib.parse.urlencode(summary_params)
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode()).get('result', {})
            
        citations = []
        for uid in id_list:
            if uid in result:
                item = result[uid]
                citations.append({
                    "title": item.get('title', 'No Title'),
                    "author": item.get('authors', [{'name': 'Unknown'}])[0]['name'],
                    "source": item.get('source', 'Journal'),
                    "date": item.get('pubdate', 'No Date')[:4],
                    "id": uid,
                    "grade": "Un-graded"
                })
        return citations
    except Exception as e:
        st.error(f"PubMed Error: {e}")
        return []

# ==========================================
# 4. MAIN UI
# ==========================================
st.title("CarePathIQ AI Agent")
st.markdown(f"### Intelligent Clinical Pathway Development")

if not gemini_api_key:
    st.info("👋 Welcome. Please enter your Gemini API Key in the sidebar.")
    st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
    st.stop()

phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", 
                  "Phase 2: Evidence & Mesh", 
                  "Phase 3: Logic Construction",
                  "Phase 4: Visualization & Testing",
                  "Phase 5: Operationalize"], 
                 horizontal=True)

st.session_state.current_phase_label = phase
st.divider()

# ------------------------------------------
# PHASE 1: SCOPING
# ------------------------------------------
if "Phase 1" in phase:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Project Parameters")
        cond = st.text_input("Target Condition", value=st.session_state.data['phase1']['condition'], placeholder="e.g. Sepsis")
        
        # Trigger suggestion generation only if condition changes
        if cond and cond != st.session_state.suggestions.get('condition_ref'):
            with st.spinner("🤖 AI generating suggestions..."):
                prompt = f"""
                Act as a Chief Medical Officer. User is building a pathway for: '{cond}'.
                Return JSON with:
                - population: (String)
                - setting: (String)
                - problem: (String)
                - objectives: (List of 3 strings, SMART goals)
                """
                data = get_gemini_response(prompt, json_mode=True)
                if data:
                    st.session_state.suggestions = data
                    st.session_state.suggestions['condition_ref'] = cond # Prevent re-running
                    st.rerun()

        if st.session_state.suggestions:
            pop = st.text_input("Target Population", value=st.session_state.data['phase1']['population'], placeholder=st.session_state.suggestions.get('population', ''))
            setting = st.text_input("Care Setting", value=st.session_state.data['phase1']['setting'], placeholder=st.session_state.suggestions.get('setting', ''))
            prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'], placeholder=st.session_state.suggestions.get('problem', ''))
        else:
            pop = st.text_input("Target Population", value=st.session_state.data['phase1']['population'])
            setting = st.text_input("Care Setting", value=st.session_state.data['phase1']['setting'])
            prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'])

        st.session_state.data['phase1'].update({"population": pop, "setting": setting, "problem": prob, "condition": cond})

    with col2:
        st.subheader("Objectives")
        obj = st.text_area("Define Project Objectives", value=st.session_state.data['phase1']['objectives'])
        st.session_state.data['phase1']['objectives'] = obj
        
        if st.session_state.suggestions.get('objectives'):
            st.markdown("**:gray[AI Suggestions:]**")
            for goal in st.session_state.suggestions['objectives']:
                st.markdown(f":gray[- *{goal}*]")
        
        st.divider()
        if st.button("Generate Project Charter"):
            prompt = f"Create a formal Project Charter (Markdown).\nCondition: {cond}\nPopulation: {pop}\nSetting: {setting}\nProblem: {prob}\nObjectives: {obj}"
            response = get_gemini_response(prompt)
            if response:
                final_charter = response + "\n\n" + COPYRIGHT_HTML
                st.download_button("📥 Download Charter", final_charter, "charter.md")

# ------------------------------------------
# PHASE 2: EVIDENCE
# ------------------------------------------
elif "Phase 2" in phase:
    st.subheader("Dynamic Evidence Synthesis")
    col1, col2 = st.columns([1, 2])
    
    p1_cond = st.session_state.data['phase1']['condition']
    
    with col1:
        st.markdown("#### PICO Framework")
        p = st.text_input("P (Population)", value=st.session_state.data['phase1']['population'])
        i = st.text_input("I (Intervention)", value="Standardized Pathway")
        c = st.text_input("C (Comparison)", value="Current Variation")
        o = st.text_input("O (Outcome)", value="Reduced Mortality / LOS")
        st.session_state.data['phase2'].update({"pico_p": p, "pico_i": i, "pico_c": c, "pico_o": o})

        st.divider()
        if st.button("Generate MeSH Query"):
            if not p1_cond:
                 st.error("Please define a condition in Phase 1.")
            else:
                with st.spinner("Building query..."):
                    prompt = f"""
                    Create a PubMed search query using MeSH terms.
                    Condition: {p1_cond}, P: {p}, I: {i}, O: {o}.
                    Output ONLY the raw query string.
                    """
                    query = get_gemini_response(prompt)
                    st.session_state.data['phase2']['mesh_query'] = query
                    st.rerun()

    with col2:
        st.markdown("#### Literature Search")
        current_query = st.session_state.data['phase2'].get('mesh_query', '')
        search_q = st.text_area("Search Query", value=current_query, height=100)
        
        if st.button("Search PubMed"):
            if search_q:
                with st.spinner("Searching..."):
                    results = search_pubmed(search_q)
                    # Deduplicate
                    existing = {e['id'] for e in st.session_state.data['phase2']['evidence']}
                    for r in results:
                        if r['id'] not in existing:
                            st.session_state.data['phase2']['evidence'].append(r)
        
        if st.session_state.data['phase2']['evidence']:
            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            edited_df = st.data_editor(df, column_config={
                "grade": st.column_config.SelectboxColumn("GRADE", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)"]),
                "id": st.column_config.TextColumn("PMID", disabled=True)
            }, hide_index=True, key="evidence_editor")
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')

# ------------------------------------------
# PHASE 3: LOGIC
# ------------------------------------------
elif "Phase 3" in phase:
    st.subheader("Pathway Logic")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("Define clinical steps.")
        if st.button("Auto-Draft Logic"):
            cond = st.session_state.data['phase1']['condition']
            evidence_list = [e['title'] for e in st.session_state.data['phase2']['evidence']]
            
            if not cond:
                st.error("Missing Phase 1 data.")
            else:
                with st.spinner("Synthesizing logic..."):
                    prompt = f"""
                    Create a clinical logic flow for {cond}.
                    Based on evidence titles: {evidence_list[:3]}.
                    Return JSON list of objects: {{"type": "Start|Decision|Process|End", "label": "text", "evidence": "citation"}}.
                    """
                    nodes = get_gemini_response(prompt, json_mode=True)
                    if isinstance(nodes, list):
                        st.session_state.data['phase3']['nodes'] = nodes
                        st.rerun()

    with col2:
        evidence_options = ["N/A"] + [f"PMID:{e['id']}" for e in st.session_state.data['phase2']['evidence']]
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes']) if st.session_state.data['phase3']['nodes'] else pd.DataFrame([{"type":"Start","label":"Start","evidence":"N/A"}])
        
        edited_nodes = st.data_editor(df_nodes, column_config={
            "type": st.column_config.SelectboxColumn("Type", options=["Start", "Decision", "Process", "Note", "End"]),
            "evidence": st.column_config.SelectboxColumn("Evidence", options=evidence_options)
        }, num_rows="dynamic", hide_index=True, use_container_width=True)
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# ------------------------------------------
# PHASE 4: VISUALIZATION
# ------------------------------------------
elif "Phase 4" in phase:
    st.subheader("Visual Flowchart")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        nodes = st.session_state.data['phase3']['nodes']
        if nodes:
            try:
                graph = graphviz.Digraph()
                graph.attr(rankdir='TB')
                for i, n in enumerate(nodes):
                    color = {'Start':'#D5E8D4', 'Decision':'#F8CECC', 'Process':'#FFF2CC', 'End':'#D5E8D4'}.get(n.get('type'), '#E0F2F1')
                    shape = {'Decision':'diamond', 'Start':'oval', 'End':'oval'}.get(n.get('type'), 'box')
                    graph.node(str(i), n.get('label', '?'), shape=shape, style='filled', fillcolor=color)
                    if i > 0: graph.edge(str(i-1), str(i))
                
                st.graphviz_chart(graph)
                
                # Robust Download
                try:
                    png = graph.pipe(format='png')
                    st.download_button("🖼️ Download PNG", png, "flowchart.png", "image/png")
                except:
                    st.warning("Download failed (Server missing Graphviz binary).")
            except Exception as e:
                st.error(f"Graph Error: {e}")

    with col2:
        if st.button("Start AI Analysis"):
            with st.spinner("Analyzing..."):
                prompt = f"Analyze clinical logic: {json.dumps(nodes)}. Return JSON keys H1..H10 with Nielsen Heuristic risks."
                risks = get_gemini_response(prompt, json_mode=True)
                st.session_state.data['phase4']['heuristics_data'] = risks
        
        risks = st.session_state.data['phase4'].get('heuristics_data', {})
        for k,v in risks.items():
            with st.expander(k): st.write(v)

# ------------------------------------------
# PHASE 5: OPERATIONALIZE
# ------------------------------------------
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    c1, c2, c3 = st.columns(3)
    
    # 1. Beta Testing
    with c1:
        st.markdown("#### 1. Beta Testing")
        email = st.text_input("User Email", placeholder="user@hospital.org")
        if st.button("Generate Interact Guide"):
            with st.spinner("Drafting Guide..."):
                prompt = f"Create a 'Beta Testing Guide' (Markdown) for {st.session_state.data['phase1']['condition']}. Include 5 Google Form questions."
                content = get_gemini_response(prompt)
                st.session_state.data['phase5']['beta_content'] = content
        
        if st.session_state.data['phase5']['beta_content']:
             st.download_button("📥 Download Guide", st.session_state.data['phase5']['beta_content'], "beta_guide.md")

    # 2. Education
    with c2:
        st.markdown("#### 2. Frontline Education")
        if st.button("Generate Slide Deck"):
            with st.spinner("Drafting Slides..."):
                prompt = f"Create content for 5 educational slides (Markdown) about {st.session_state.data['phase1']['condition']} pathway."
                slides = get_gemini_response(prompt)
                st.session_state.data['phase5']['slides'] = slides
        
        if st.session_state.data['phase5']['slides']:
             st.download_button("📥 Download Slides", st.session_state.data['phase5']['slides'], "slides.md")

    # 3. HR Integration
    with c3:
        st.markdown("#### 3. HR Integration")
        if st.button("Generate OPS/Epic Specs"):
            with st.spinner("Mapping to OPS..."):
                nodes_json = json.dumps(st.session_state.data['phase3']['nodes'])
                prompt = f"""
                Map these nodes to Epic/HR tools.
                Nodes: {nodes_json}
                Use 'OPS' (Practice Advisory) instead of BPA.
                Return CSV string with headers: Phase, Logic_Node, OPS_Action, Decision_Tree_Element.
                """
                csv = get_gemini_response(prompt)
                st.session_state.data['phase5']['epic_csv'] = csv
        
        if st.session_state.data['phase5']['epic_csv']:
            st.download_button("📥 Download CSV", st.session_state.data['phase5']['epic_csv'], "ops_specs.csv")

# ==========================================
# FOOTER
# ==========================================
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
