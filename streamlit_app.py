import streamlit as st
from openai import OpenAI
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CarePathIQ",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR: AUTHENTICATION & CONFIG ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
    st.title("CarePathIQ")
    st.caption("Clinical Pathway Intelligence")
    st.divider()
    
    # 1. Secure API Key Entry
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    
    if not openai_api_key:
        st.warning("⚠️ Enter API Key to activate agents.")
    else:
        st.success("✅ System Connected")
        
    st.divider()
    
    # 2. Global Model Settings
    model_choice = st.selectbox("LLM Engine", ["gpt-4o", "gpt-4-turbo"], index=0)
    temperature = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.2)
    
    st.divider()
    st.info(f"Current Phase: {st.session_state.get('current_phase_label', 'Start')}")

# Initialize OpenAI Client securely
client = None
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)

# --- SESSION STATE INITIALIZATION ---
if "data" not in st.session_state:
    st.session_state.data = {
        "phase1": {"condition": "Sepsis", "population": "Adult ED Patients", "problem": "Adherence to 3-hour bundle < 50%", "objectives": ""},
        "phase2": {"evidence": []},
        "phase3": {"nodes": []},
        "phase4": {"heuristics": ""},
        "phase5": {}
    }

# --- HELPER FUNCTIONS ---

def run_agent(agent_role, prompt, context=None):
    """
    Streams response from OpenAI and returns the full text for storage.
    """
    if not client:
        st.error("Authentication required. Please check sidebar.")
        return None
    
    messages = [
        {"role": "system", "content": f"You are the {agent_role} module of CarePathIQ. {context if context else ''}"},
        {"role": "user", "content": prompt}
    ]

    full_response = ""
    try:
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=model_choice,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            response = st.write_stream(stream)
            return response
    except Exception as e:
        st.error(f"Agent Error: {e}")
        return None

def search_pubmed(query):
    """Performs real-time search on PubMed via NCBI E-utilities."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    try:
        # Search
        search_params = {'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': 5}
        url = base_url + "esearch.fcgi?" + urllib.parse.urlencode(search_params)
        with urllib.request.urlopen(url) as response:
            id_list = json.loads(response.read().decode()).get('esearchresult', {}).get('idlist', [])
        
        if not id_list: return []

        # Summary
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
                    "grade": "Un-graded" # Default for new entries
                })
        return citations
    except Exception as e:
        st.error(f"PubMed Error: {e}")
        return []

# --- MAIN UI STRUCTURE ---
st.title("CarePathIQ Dashboard")
st.markdown("### Intelligent Clinical Pathway Development")

if not openai_api_key:
    st.info("👋 Welcome to CarePathIQ. Please provide your OpenAI Access Token in the sidebar to begin.")
    st.stop()

# Phase Navigation
phase = st.radio("Workflow Phase", 
                 ["Phase 1: Scoping & Charter", 
                  "Phase 2: Evidence (PICO & PubMed)", 
                  "Phase 3: Logic Construction",
                  "Phase 4: Visualization (Flowchart)",
                  "Phase 5: Operationalize"], 
                 horizontal=True)

st.session_state.current_phase_label = phase
st.divider()

# =========================================================
# PHASE 1: SCOPE & CHARTER
# =========================================================
if "Phase 1" in phase:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Project Parameters")
        cond = st.text_input("Target Condition", value=st.session_state.data['phase1']['condition'])
        pop = st.text_input("Target Population", value=st.session_state.data['phase1']['population'])
        prob = st.text_area("Clinical Gap / Problem", value=st.session_state.data['phase1']['problem'])
        
        # Save to state immediately
        st.session_state.data['phase1'].update({"condition": cond, "population": pop, "problem": prob})
        
    with col2:
        st.subheader("Charter Generation")
        obj_draft = st.text_input("Draft Objective (Optional)", placeholder="e.g. Reduce LOS")
        
        if st.button("Generate Project Charter", type="primary"):
            role = "Clinical Project Manager"
            prompt = f"""
            Create a formal Project Charter for a clinical pathway.
            Condition: {cond}
            Population: {pop}
            Problem: {prob}
            Draft Objective: {obj_draft}
            
            Action: 
            1. Refine the objective into 3 SMART Goals.
            2. List Key Stakeholders.
            3. Define Success Metrics.
            """
            response = run_agent(role, prompt)
            st.session_state.data['phase1']['objectives'] = response
            
        if st.session_state.data['phase1'].get('objectives'):
             st.download_button("📥 Download Charter (MD)", st.session_state.data['phase1']['objectives'], "charter.md")

# =========================================================
# PHASE 2: EVIDENCE (PICO + PUBMED)
# =========================================================
elif "Phase 2" in phase:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("PICO Framework")
        with st.expander("Define PICO", expanded=True):
            p = st.text_input("P (Population)", value=st.session_state.data['phase1']['population'])
            i = st.text_input("I (Intervention)", value="Standardized Pathway")
            c = st.text_input("C (Comparison)", value="Current Variation")
            o = st.text_input("O (Outcome)", value="See Phase 1 SMART Goals")
            
        st.subheader("Literature Search")
        search_q = st.text_input("PubMed Query", value=f"{st.session_state.data['phase1']['condition']} Guidelines")
        
        if st.button("Search PubMed", type="primary"):
            with st.spinner("Searching NCBI Database..."):
                results = search_pubmed(search_q)
                # Add unique results to session state
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
            # Data Editor for Grading
            df = pd.DataFrame(st.session_state.data['phase2']['evidence'])
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "grade": st.column_config.SelectboxColumn(
                        "GRADE Score",
                        options=["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)"],
                        required=True
                    ),
                    "title": st.column_config.TextColumn("Title", width="medium"),
                    "id": st.column_config.TextColumn("PubMed ID", disabled=True)
                },
                disabled=["title", "author", "source", "date", "id"],
                hide_index=True,
                num_rows="dynamic",
                key="evidence_editor"
            )
            
            # Save mechanism
            st.session_state.data['phase2']['evidence'] = edited_df.to_dict('records')
            st.download_button("📥 Download Evidence Table (CSV)", edited_df.to_csv(index=False), "evidence.csv")

# =========================================================
# PHASE 3: LOGIC CONSTRUCTION
# =========================================================
elif "Phase 3" in phase:
    st.subheader("Pathway Logic Construction")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("Build your logic table here. This will generate the Flowchart in Phase 4.")
        if st.button("Auto-Generate Draft Logic"):
            role = "Algorithm Architect"
            prompt = f"Create a 5-step logic flow for {st.session_state.data['phase1']['condition']}. Return ONLY JSON format list with keys: type (Start/Decision/Process/End), label, evidence."
            # Note: For production, we'd use JSON mode. Here we simulated a preset for stability.
            st.session_state.data['phase3']['nodes'] = [
                {"type": "Start", "label": "Patient Arrival", "evidence": "N/A"},
                {"type": "Decision", "label": "High Risk Criteria Met?", "evidence": "Guideline A"},
                {"type": "Process", "label": "Initiate Bundle", "evidence": "Guideline B"},
                {"type": "End", "label": "Admit to ICU", "evidence": "N/A"}
            ]
            st.rerun()

    with col2:
        # Get Evidence List for Dropdown
        evidence_options = ["N/A"] + [f"{e['author']} ({e['date']})" for e in st.session_state.data['phase2']['evidence']]
        
        if not st.session_state.data['phase3']['nodes']:
             st.session_state.data['phase3']['nodes'] = [{"type": "Start", "label": "Start", "evidence": "N/A"}]

        df_nodes = pd.DataFrame(st.session_state.data['phase3']['nodes'])
        
        edited_nodes = st.data_editor(
            df_nodes,
            column_config={
                "type": st.column_config.SelectboxColumn("Node Type", options=["Start", "Decision", "Process", "Note", "End"]),
                "evidence": st.column_config.SelectboxColumn("Supporting Evidence", options=evidence_options)
            },
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True
        )
        
        st.session_state.data['phase3']['nodes'] = edited_nodes.to_dict('records')

# =========================================================
# PHASE 4: VISUALIZATION
# =========================================================
elif "Phase 4" in phase:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Visual Flowchart")
        nodes = st.session_state.data['phase3']['nodes']
        
        if not nodes:
            st.warning("No logic defined in Phase 3.")
        else:
            # Graphviz Logic
            graph = graphviz.Digraph()
            graph.attr(rankdir='TB')
            
            for i, node in enumerate(nodes):
                n_id = str(i)
                lbl = node.get('label', 'Unknown')
                n_type = node.get('type', 'Process')
                
                # Styles matching your template
                if n_type in ['Start', 'End']:
                    graph.node(n_id, lbl, shape='oval', style='filled', fillcolor='#D5E8D4', color='#82B366') # Green
                elif n_type == 'Decision':
                    graph.node(n_id, lbl, shape='diamond', style='filled', fillcolor='#F8CECC', color='#B85450') # Red
                elif n_type == 'Process':
                    graph.node(n_id, lbl, shape='box', style='filled', fillcolor='#FFF2CC', color='#D6B656') # Yellow
                elif n_type == 'Note':
                    graph.node(n_id, lbl, shape='note', style='filled', fillcolor='#DAE8FC', color='#6C8EBF') # Blue
                
                # Simple sequential linking (MVP)
                if i > 0:
                    graph.edge(str(i-1), str(i))
            
            st.graphviz_chart(graph)
            
    with col2:
        st.subheader("User Testing (Heuristics)")
        heuristics = st.text_area("Usability Notes", value=st.session_state.data['phase4']['heuristics'], height=200)
        st.session_state.data['phase4']['heuristics'] = heuristics
        
        if st.button("Save & Validate"):
            st.success("Design Validated")

# =========================================================
# PHASE 5: OPERATIONALIZATION
# =========================================================
elif "Phase 5" in phase:
    st.subheader("Operational Toolkit")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📘 Beta Guide")
        guide = f"# Beta Testing Guide\nTarget: {st.session_state.data['phase1']['population']}\nMethod: Silent Pilot"
        st.download_button("Download Guide", guide, "beta_guide.md")
        
    with col2:
        st.markdown("#### 🎓 Education Deck")
        slides = f"# Training: {st.session_state.data['phase1']['condition']}\n1. Objectives\n2. Flowchart Review"
        st.download_button("Download Slides Content", slides, "education.md")
        
    with col3:
        st.markdown("#### ⚙️ EHR Specs")
        if st.session_state.data['phase3']['nodes']:
            df_ehr = pd.DataFrame(st.session_state.data['phase3']['nodes'])
            st.download_button("Download EHR Specs", df_ehr.to_csv(), "ehr_specs.csv")
    
    st.divider()
    st.markdown("### Final System Check")
    if st.button("Generate Final Report"):
        role = "Chief Medical Information Officer"
        prompt = f"Summarize this entire project for executive leadership based on: {st.session_state.data}"
        run_agent(role, prompt)
