import streamlit as st
import google.generativeai as genai
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
import time
from io import StringIO

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

COPYRIGHT_MD = """
---
[CarePathIQ](https://www.carepathiq.org) © 2024 by [Tehreem Rehman](https://www.tehreemrehman.com) is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
"""

# ==========================================
# 2. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="CarePathIQ (Gemini Edition)",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR: AUTHENTICATION & CONFIG ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
    st.title("CarePathIQ")
    st.caption("Powered by Google Gemini")
    st.divider()
    
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Get a free key at aistudio.google.com")
    
    if not gemini_api_key:
        st.warning("⚠️ Enter API Key to activate.")
        st.markdown("[Get Free API Key](https://aistudio.google.com/app/apikey)")
    else:
        st.success("✅ Gemini Connected")
        genai.configure(api_key=gemini_api_key)
        
    st.divider()
    model_choice = st.selectbox("Gemini Model", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    st.divider()
    st.info(f"Current Phase: {st.session_state.get('current_phase_label', 'Start')}")

# --- SESSION STATE INITIALIZATION ---
if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {
            "condition": "", 
            "population": "", 
            "setting": "", 
            "problem": "", 
            "objectives": ""
        },
        "phase2": {"evidence": []},
        "phase3": {"nodes": []},
        "phase4": {"heuristics_data": {}}, 
        "phase5": {"slides": "", "html": "", "epic_csv": ""} 
    }

# Suggestions cache
if "suggestions" not in st.session_state:
    st.session_state.suggestions = {
        "population": "e.g. Adult patients presenting to ED...",
        "setting": "e.g. Emergency Department, ICU...",
        "problem": "e.g. High variability in treatment protocols...",
        "objectives": [],
        "outcome": "e.g. Reduce Length of Stay by 10%...",
        "query": "e.g. Sepsis Clinical Guidelines"
    }

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def generate_suggestions():
    condition = st.session_state.data['phase1']['condition']
    if not condition or not gemini_api_key:
        return

    try:
        model = genai.GenerativeModel(model_choice)
        prompt = f"""
        You are a clinical expert. The user is building a pathway for the condition: '{condition}'.
        Provide short, realistic examples for the following fields.
        
        Return ONLY a raw JSON object (no markdown formatting) with these keys:
        - population: (String)
        - setting: (String)
        - problem: (String)
        - objectives: (List of 3 Strings, SMART goals format)
        - outcome: (String, primary clinical outcome)
        - query: (String, optimized PubMed search query)
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        st.session_state.suggestions = data
        
    except Exception as e:
        st.session_state.suggestions = {
            "population": "Error generating suggestions",
            "setting": "Error",
            "problem": "Error",
            "objectives": ["Error"],
            "outcome": "Error",
            "query": condition
        }

def run_gemini_agent(agent_role, prompt, context=None):
    if not gemini_api_key:
        st.error("Authentication required.")
        return None
    full_prompt = f"SYSTEM ROLE: You are the {agent_role} module of CarePathIQ. {context if context else ''}
USER PROMPT: {prompt}"
    try:
        model = genai.GenerativeModel(model_choice)
        with st.chat_message("assistant"):
            response_stream = model.generate_content(full_prompt, stream=True)
            def stream_parser(stream):
                for chunk in stream:
                    if chunk.text: yield chunk.text
            full_text = st.write_stream(stream_parser(response_stream))
            return full_text
    except Exception as e:
        st.error(f"Gemini Error: {e}")
        return None

def generate_text_content(prompt):
    try:
        model = genai.GenerativeModel(model_choice)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        search_params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': 5}
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

def analyze_heuristics(nodes):
    if not nodes or not gemini_api_key:
        return {}
    try:
        model = genai.GenerativeModel(model_choice)
        prompt = f"""
        Analyze this clinical pathway logic (JSON format below) against Nielsen's 10 Usability Heuristics.
        LOGIC NODES: {json.dumps(nodes)}
        For EACH of the 10 heuristics, provide a specific "Risk Insight".
        Return ONLY a raw JSON object with keys "H1", "H2", ... "H10".
        """
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data
    except Exception as e:
        st.error(f"Heuristic Analysis Error: {e}")
        return {}

# ==========================================
# 4. MAIN UI STRUCTURE
# ==========================================
st.title("CarePathIQ Dashboard")
st.markdown("### Intelligent Clinical Pathway Development")

if not gemini_api_key:
    st.info("👋 Welcome. Please enter your Gemini API Key in the sidebar.")
    st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
    st.stop()

phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", 
                  "Phase 2: Evidence (PICO & PubMed)", 
                  "Phase 3: Logic Construction",
                  "Phase 4: Visualization & Testing",
                  "Phase 5: Operationalize"], 
                 horizontal=True)

st.session_state.current_phase_label = phase
st.divider()

# PHASE 1
if "Phase 1" in phase:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Project Parameters")
        cond = st.text_input("Target Condition", value=st.session_state.data['phase1']['condition'], placeholder="e.g. Sepsis, Stroke, Heart Failure", help="Type a condition and press Enter to generate suggestions.")
        if cond != st.session_state.data['phase1']['condition']:
            st.session_state.data['phase1']['condition'] = cond
            if cond:
                with st.spinner("🤖 Generating clinical suggestions..."):
                    generate_suggestions()
                st.rerun()

        pop = st.text_input("Target Population", value=st.session_state.data['phase1']['population'], placeholder=st.session_state.suggestions.get('population', ''))
        setting = st.text_input("Care Setting", value=st.session_state.data['phase1']['setting'], placeholder=st.session_state.suggestions.get('setting', ''))
        prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'], placeholder=st.session_state.suggestions.get('problem', ''))
        st.session_state.data['phase1'].update({"population": pop, "setting": setting, "problem": prob})
        
    with col2:
        st.subheader("Objectives")
        obj = st.text_area("Define Project Objectives", value=st.session_state.data['phase1']['objectives'], placeholder="Enter your SMART goals here...")
        st.session_state.data['phase1']['objectives'] = obj
        if st.session_state.suggestions.get('objectives'):
            st.markdown("**:gray[AI Suggestions (SMART Framework):]**")
            for goal in st.session_state.suggestions['objectives']:
                st.markdown(f":gray[- *{goal}*]")
        st.divider()
        if st.button("Generate Project Charter", type="primary"):
            role = "Clinical Project Manager"
            prompt = f"Create a formal Project Charter.\nCondition: {cond}\nPopulation: {pop}\nSetting: {setting}\nProblem: {prob}\nObjectives: {obj}"
            response = run_gemini_agent(role, prompt)
            
            if response:
                final_charter = response + "\n\n" + COPYRIGHT_MD
                st.download_button("📥 Download Charter (MD)", final_charter, "charter.md")

# PHASE 2
elif "Phase 2" in phase:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("PICO Framework")
        with st.expander("Define PICO", expanded=True):
            p = st.text_input("P (Population)", value=st.session_state.data['phase1']['population'])
            i = st.text_input("I (Intervention)", value="Standardized Pathway")
            c = st.text_input("C (Comparison)", value="Current Variation")
            outcome_placeholder = st.session_state.suggestions.get('outcome', 'e.g. Reduced Mortality')
            o = st.text_input("O (Outcome)", placeholder=outcome_placeholder)
        st.subheader("Literature Search")
        query_placeholder = st.session_state.suggestions.get('query', f"{st.session_state.data['phase1']['condition']} Guidelines")
        search_q = st.text_input("PubMed Query", value="", placeholder=query_placeholder)
        final_query = search_q if search_q else query_placeholder
        if st.button("Search PubMed", type="primary"):
            st.info(f"Searching: {final_query}")
            with st.spinner("Searching NCBI Database..."):
                results = search_pubmed(final_query)
                existing_ids = [e['id'] for e in st.session_state.data['phase2']['evidence']]
                for r in results:
                    if r['id'] not in existing_ids:
                        st.session_state.data['phase2']['evidence'].append(r)
                if not results:
                    st.warning("No results found.")
    
    with col2:
        st.subheader("Evidence Appraisal (GRADE)")
        if not st.session_state.data['phase2']['evidence']:
            st.info("Perform a search to populate the evidence table.")
        else:
            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            edited_df = st.data_editor(df, column_config={
                "grade": st.column_config.SelectboxColumn("GRADE Score", options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)"], required=True),
                "title": st.column_config.TextColumn("Title", width="medium"),
                "id": st.column_config.TextColumn("PubMed ID", disabled=True)
            }, disabled=["title", "author", "source", "date", "id"], hide_index=True, num_rows="dynamic", key="evidence_editor")
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            st.download_button("📥 Download Evidence Table (CSV)", edited_df.to_csv(index=False), "evidence.csv")

# PHASE 3
elif "Phase 3" in phase:
    st.subheader("Pathway Logic Construction")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("Define the steps of your pathway below.")
        if st.button("Auto-Generate Draft Logic"):
            st.session_state.data['phase3']['nodes'] = [
                {"type": "Start", "label": "Patient Arrival", "evidence": "N/A"},
                {"type": "Decision", "label": "Meets Sepsis Criteria?", "evidence": "Guideline A"},
                {"type": "Process", "label": "Order Lactate & Cultures", "evidence": "Guideline B"},
                {"type": "End", "label": "Admit to ICU", "evidence": "N/A"}
            ]
            st.rerun()
    with col2:
        evidence_options = ["N/A"] + [f"{e['author']} ({e['date']})" for e in st.session_state.data['phase2']['evidence']]
        if not st.session_state.data['phase3']['nodes']:
             st.session_state.data['phase3']['nodes'] = [{"type": "Start", "label": "Start", "evidence": "N/A"}]
        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        edited_nodes = st.data_editor(df_nodes, column_config={
            "type": st.column_config.SelectboxColumn("Node Type", options=["Start", "Decision", "Process", "Note", "End"]),
            "label": st.column_config.TextColumn("Content", help="What text appears inside the shape?"),
            "evidence": st.column_config.SelectboxColumn("Supporting Evidence", options=evidence_options)
        }, num_rows="dynamic", hide_index=True, use_container_width=True)
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# PHASE 4
elif "Phase 4" in phase:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Visual Flowchart")
        nodes = st.session_state.data['phase3']['nodes']
        if not nodes:
            st.warning("No logic defined in Phase 3.")
        else:
            graph = graphviz.Digraph()
            graph.attr(rankdir='TB')
            for i, node in enumerate(nodes):
                n_id, lbl, n_type = str(i), node.get('label', '?'), node.get('type', 'Process')
                if n_type in ['Start', 'End']: graph.node(n_id, lbl, shape='oval', style='filled', fillcolor='#D5E8D4', color='#82B366')
                elif n_type == 'Decision': graph.node(n_id, lbl, shape='diamond', style='filled', fillcolor='#F8CECC', color='#B85450')
                elif n_type == 'Process': graph.node(n_id, lbl, shape='box', style='filled', fillcolor='#FFF2CC', color='#D6B656')
                elif n_type == 'Note': graph.node(n_id, lbl, shape='note', style='filled', fillcolor='#DAE8FC', color='#6C8EBF')
                if i > 0: graph.edge(str(i-1), str(i))
            
            st.graphviz_chart(graph)
            
            try:
                png_bytes = graph.pipe(format='png')
                svg_bytes = graph.pipe(format='svg')
                
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.download_button("🖼️ Download High-Res (PNG)", png_bytes, "pathway_flowchart.png", "image/png")
                with d_col2:
                    st.download_button("✏️ Download Visio-Ready (SVG)", svg_bytes, "pathway_editable.svg", "image/svg+xml")
            except Exception as e:
                st.warning(f"Download generation failed: {e}")
            
    with col2:
        st.subheader("Heuristic Evaluation")
        st.caption("AI-Guided Usability Testing (Nielsen's 10)")
        if st.button("Start AI Analysis", type="primary"):
            with st.spinner("Analyzing pathway logic against heuristics..."):
                risks = analyze_heuristics(st.session_state.data['phase3']['nodes'])
                st.session_state.data['phase4']['heuristics_data'] = risks
        
        heuristics_list = ["H1: Visibility of status", "H2: Match system/real world", "H3: User control", "H4: Consistency", "H5: Error prevention", "H6: Recognition vs recall", "H7: Flexibility", "H8: Aesthetic design", "H9: Error recovery", "H10: Documentation"]
        risks_data = st.session_state.data['phase4'].get('heuristics_data', {})
        for i, h_title in enumerate(heuristics_list):
            key_id = f"H{i+1}"
            ai_insight = risks_data.get(key_id, "Click 'Start AI Analysis' to generate insights.")
            with st.expander(f"{h_title}", expanded=False):
                st.info(f"🤖 **AI Insight:** {ai_insight}")
                user_note = st.text_area(f"Fix for {key_id}", key=f"note_{key_id}")
                st.checkbox(f"Resolved {key_id}", key=f"check_{key_id}")

# PHASE 5
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🌐 Beta Website Generator")
        st.caption("Create a landing page for clinician feedback.")
        
        contact_link = st.text_input("Google Form Link (or Email)", placeholder="https://forms.gle/...")
        
        if st.button("Generate Beta Site"):
            if not contact_link:
                st.warning("Please enter a link first.")
            else:
                with st.spinner("Coding HTML/CSS..."):
                    cond = st.session_state.data['phase1']['condition']
                    prob = st.session_state.data['phase1']['problem']
                    
                    embed_code = f'<iframe src="{contact_link}" width="100%" height="600" frameborder="0" marginheight="0" marginwidth="0">Loading...</iframe>'
                    if "@" in contact_link and "http" not in contact_link:
                        embed_code = f'<div style="text-align:center; padding: 20px;"><a href="mailto:{contact_link}" class="button">Email Feedback</a></div>'
                    
                    prompt = f"""
                    Write a single-file HTML5 code for a responsive 'Beta Testing Landing Page' for a clinical pathway.
                    Condition: {cond}
                    Problem Solved: {prob}
                    
                    Design requirements:
                    - Modern, clean medical aesthetic (Blues/Whites).
                    - Header: "Clinical Pathway Beta: {cond}"
                    - Section 1: "Why this change?" (Use the problem statement).
                    - Section 2: "Feedback Module" -> INSERT THIS EXACT CODE HERE: {embed_code}
                    - Footer: "Generated by CarePathIQ".
                    
                    Return ONLY raw HTML code.
                    """
                    html_content = generate_text_content(prompt)
                    html_content = html_content.replace("```html", "").replace("```", "")
                    
                    html_content = html_content + "\n" + COPYRIGHT_HTML
                    
                    st.session_state.data['phase5']['html'] = html_content
                    st.success("Website Generated!")
        
        if st.session_state.data['phase5']['html']:
            st.download_button("📥 Download HTML File", st.session_state.data['phase5']['html'], "beta_landing_page.html", "text/html")

    with col2:
        st.markdown("#### 📊 Slide Deck Generator")
        if st.button("Generate Slide Content"):
            with st.spinner("Drafting presentation..."):
                cond = st.session_state.data['phase1']['condition']
                prompt = f"""
                Create a 5-slide educational presentation for {cond} Pathway.
                Structure: 1.Title 2.Gap 3.Flow 4.Evidence 5.Ops.
                Format: Markdown with 'Speaker Notes'.
                """
                slides_content = generate_text_content(prompt)
                
                slides_content = slides_content + "\n\n" + COPYRIGHT_MD
                
                st.session_state.data['phase5']['slides'] = slides_content
                st.success("Slides Ready!")

        if st.session_state.data['phase5'].get('slides'):
             st.download_button("📥 Download Slides (MD)", st.session_state.data['phase5']['slides'], "presentation_content.md")

    with col3:
        st.markdown("#### 🏥 EHR Spreadsheet Generator")
        st.caption("Map logic nodes to Epic build tools.")
        
        if st.button("Generate Epic Specs"):
            nodes = st.session_state.data['phase3']['nodes']
            if not nodes:
                st.warning("No logic nodes found in Phase 3.")
            else:
                with st.spinner("Mapping to Epic (BPA/Orders)..."):
                    prompt = f"""
                    Act as an Epic Analyst. Map the following clinical logic nodes to specific Epic Build Tools.
                    Nodes: {json.dumps(nodes)}
                    
                    Return a CSV formatted string with these headers:
                    Phase, Logic_Node, Epic_Tool_Type, Build_Suggestion, Alert_Logic
                    
                    Examples: 
                    - "Decision", "Sepsis Criteria", "BPA (BestPracticeAdvisory)", "Alert: HM Sepsis", "Trigger if Lactate > 2"
                    - "Process", "Order Abx", "SmartSet", "ED Sepsis Order Set", "Default Zosyn/Vanc"
                    
                    Return ONLY the CSV string.
                    """
                    csv_content = generate_text_content(prompt)
                    csv_content = csv_content.replace("```csv", "").replace("```", "")
                    st.session_state.data['phase5']['epic_csv'] = csv_content
                    st.success("Mapping Complete!")
        
        if st.session_state.data['phase5']['epic_csv']:
            try:
                preview_df = pd.read_csv(StringIO(st.session_state.data['phase5']['epic_csv']))
                st.dataframe(preview_df, height=150, hide_index=True)
                st.download_button("📥 Download .CSV", st.session_state.data['phase5']['epic_csv'], "epic_build_specs.csv", "text/csv")
            except:
                st.warning("Preview unavailable, but download is ready.")
                st.download_button("📥 Download .CSV", st.session_state.data['phase5']['epic_csv'], "epic_build_specs.csv", "text/csv")

    st.divider()
    st.subheader("Executive Summary")
    if st.button("Generate Final Report"):
        run_gemini_agent("CMIO", f"Summarize project: {st.session_state.data}")

# ==========================================
# 5. FOOTER INJECTION (APP-WIDE)
# ==========================================
st.markdown(COPYRIGHT_HTML, unsafe_allow_html=True)
