

```python
import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import base64
import os
import datetime
import graphviz

# =========================================================
# 0. CONFIGURATION & ASSETS
# =========================================================
st.set_page_config(
    page_title="CarePathIQ - Clinical Pathway Designer",
    layout="centered", 
    initial_sidebar_state="expanded"
)

# Custom CSS for White Expanders & Clean Look
st.markdown("""
<style>
.streamlit-expanderHeader { background-color: white !important; color: black !important; }
.streamlit-expanderContent { background-color: white !important; border: 1px solid #ddd; }
div[data-testid="stExpander"] { background-color: white !important; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

def get_image_base64(image_file):
    if not os.path.exists(image_file): return ""
    with open(image_file, "rb") as f: data = f.read()
    return base64.b64encode(data).decode()

# ✅ LOGO SETUP
logo_filename = "CarePathIQ_Logo.png" 
logo_b64 = get_image_base64(logo_filename)

# Standardized Footer Tag for HTML Deliverables
logo_html_tag = f"""
<div style="text-align: right; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
    <img src="data:image/png;base64,{logo_b64}" alt="CarePathIQ" style="height: 45px;">
    <br><span style="font-family: sans-serif; font-size: 0.8em; color: #777;">Powered by CarePathIQ</span>
</div>
""" if logo_b64 else "<div style='text-align:right; margin-top:20px;'><strong>CarePathIQ</strong></div>"

# =========================================================
# 1. PATHWAY GENERATION (Swimlanes, PMIDs, End Nodes)
# =========================================================
def search_pubmed(condition, setting):
    # Query: Keywords only (No Quotes)
    query = f"Guidelines Managing Patients {condition} {setting}"
    current_year = datetime.date.today().year
    start_year = current_year - 5
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed", "term": query, "retmax": 20, "sort": "relevance", "retmode": "json",
        "mindate": f"{start_year}/01/01", "maxdate": f"{current_year}/12/31", "datetype": "pdat"
    }
    try:
        response = requests.get(base_url, params=params)
        return response.json().get("esearchresult", {}).get("idlist", [])
    except: return []

def fetch_details(id_list):
    if not id_list: return []
    ids = ",".join(id_list)
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    try:
        response = requests.get(base_url, params={"db": "pubmed", "id": ids, "retmode": "xml"})
        root = ET.fromstring(response.content)
        articles = []
        for article in root.findall(".//PubmedArticle"):
            title = article.find(".//ArticleTitle").text
            pmid = article.find(".//PMID").text 
            
            # Mock Grading
            if "Systematic Review" in title: grade = "High (A)"
            elif "Guideline" in title: grade = "High (A)"
            elif "Randomized" in title: grade = "Moderate (B)"
            else: grade = "Low (C)"
            
            articles.append({"Grade": grade, "PMID": pmid, "Title": title})
        return articles
    except: return []

def render_pathway_generator():
    st.header("1. Evidence & Pathway Generation")
    
    col1, col2 = st.columns(2)
    with col1: condition = st.text_input("Condition:", "Asymptomatic Hypertension")
    with col2: setting = st.text_input("Setting:", "Emergency Department")
    
    if st.button("🔍 Generate Pathway", use_container_width=True):
        st.info(f"Searching: 'Guidelines Managing Patients {condition} {setting}' (Last 5 Years)...")
        
        # --- Phase 2: Evidence (With PMIDs) ---
        ids = search_pubmed(condition, setting)
        articles = fetch_details(ids)
        
        if articles:
            df = pd.DataFrame(articles)
            grade_order = ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)"]
            df['Grade'] = pd.Categorical(df['Grade'], categories=grade_order, ordered=True)
            df = df.sort_values('Grade')
            
            st.subheader("Phase 2: Supporting Evidence")
            # ✅ Displaying PMID Column
            st.dataframe(df[['Grade', 'PMID', 'Title']], use_container_width=True, hide_index=True)
        else:
            st.warning("No recent guidelines found.")

        st.divider()

        # --- Phase 3: Algorithm (Swimlanes + End Nodes) ---
        st.subheader("Phase 3: Clinical Algorithm")
        
        pathway_prompt = f"""
        ACT AS: Clinical Informatics Architect.
        TASK: Create a clinical pathway for '{condition}' in '{setting}'.
        OUTPUT: Valid Graphviz DOT syntax.
        
        VISUAL RULES:
        1. END NODES (Discharge/Admit): Shape=oval, Fillcolor="#D5F5E3" (Green).
        2. PROCESS: Shape=box, Fillcolor="#FCF3CF" (Yellow).
        3. DECISION: Shape=diamond, Fillcolor="#FADBD8" (Red).
        4. NOTES: Shape=parallelogram, Fillcolor="#AED6F1" (Blue), style=dashed.
        5. SWIMLANES: Use subgraphs (cluster_0, cluster_1, cluster_2).
        """
        
        with st.expander("View AI Prompt"):
            st.code(pathway_prompt, language="markdown")

        # Simulated DOT with Swimlanes & Correct Colors
        dot_code = """
        digraph G {
            rankdir=TB; splines=ortho; nodesep=0.6;
            node [fontname="Arial", fontsize=10, style="filled,rounded", penwidth=0, margin=0.2];
            edge [fontname="Arial", fontsize=9, color="#5D6D7E", penwidth=1.2];

            # Swimlane 1
            subgraph cluster_0 {
                label = "Assessment";
                style = filled; color = "#F4F6F6";
                Start [label="1. Triage\nBP > 160/100", shape=oval, fillcolor="#D5F5E3"];
                Dec_Symp [label="2. Symptomatic\nor End-Organ Damage?", shape=diamond, fillcolor="#FADBD8"];
            }

            # Swimlane 2
            subgraph cluster_1 {
                label = "Management";
                style = filled; color = "#F4F6F6";
                Act_Emerg [label="3. Treat as Emergency\nICU Admit", shape=box, fillcolor="#FCF3CF"];
                Act_Obs [label="4. Observation\nRecheck 30min", shape=box, fillcolor="#FCF3CF"];
                Note_Meds [label="Note: Check Formulary", shape=parallelogram, fillcolor="#AED6F1"];
            }
            
            # Swimlane 3
            subgraph cluster_2 {
                label = "Disposition";
                style = filled; color = "#F4F6F6";
                End_Admit [label="5. Admit to ICU", shape=oval, fillcolor="#D5F5E3"];
                End_Disch [label="6. Discharge Home", shape=oval, fillcolor="#D5F5E3"];
            }

            # Edges
            Start -> Dec_Symp;
            Dec_Symp -> Act_Emerg [label="Yes"];
            Dec_Symp -> Act_Obs [label="No"];
            Act_Emerg -> End_Admit;
            Act_Obs -> End_Disch [label="Improved"];
            Act_Emerg -> Note_Meds [style=dashed, arrowhead=none, color="#AED6F1"];
        }
        """
        
        try:
            graph = graphviz.Source(dot_code)
            st.graphviz_chart(graph, use_container_width=True)
            png_bytes = graph.pipe(format='png')
            st.download_button("📥 Download High-Res Flowchart", png_bytes, "Pathway.png", "image/png")
        except: st.error("Graphviz Error")

# =========================================================
# 2. HEURISTIC EVALUATION (Radio Buttons)
# =========================================================
def render_heuristic_dashboard():
    st.header("2. Heuristic Evaluation Dashboard")
    
    if 'heuristic_evaluations' not in st.session_state:
        st.session_state['heuristic_evaluations'] = {}

    heuristics = {
        "H1: Visibility of system status": "Keep users informed.",
        "H2: Match between system and real world": "Speak users' language.",
        "H3: User control and freedom": "Emergency exits.",
        "H4: Consistency and standards": "Follow conventions.",
        "H5: Error prevention": "Prevent problems first.",
        "H6: Recognition rather than recall": "Minimize memory load.",
        "H7: Flexibility and efficiency": "Accelerators for experts.",
        "H8: Aesthetic and minimalist": "No irrelevant info.",
        "H9: Help users recover": "Plain error messages.",
        "H10: Help and documentation": "Easy to search."
    }

    # Radio Button Selection
    selected_h = st.radio("Select Heuristic:", list(heuristics.keys()))
    st.info(f"**Description:** {heuristics[selected_h]}")

    existing = st.session_state['heuristic_evaluations'].get(selected_h, {})
    
    with st.form("eval_form"):
        severity = st.radio("Severity:", [0, 1, 2, 3, 4], 
                           format_func=lambda x: f"{x} - {['None','Cosmetic','Minor','Major','Catastrophe'][x]}",
                           index=existing.get('severity', 0), horizontal=True)
        obs = st.text_area("Observations:", value=existing.get('observation', ""))
        
        if st.form_submit_button("Save Evaluation"):
            st.session_state['heuristic_evaluations'][selected_h] = {'observation': obs, 'severity': severity}
            st.success("Saved!")
            st.rerun()

    if st.session_state['heuristic_evaluations']:
        st.divider()
        st.subheader("Summary")
        data = [{"Heuristic": k, "Severity": v['severity'], "Obs": v['observation']} 
                for k, v in st.session_state['heuristic_evaluations'].items()]
        st.dataframe(pd.DataFrame(data), use_container_width=True)

# =========================================================
# 3. BETA TESTING (Restored Full HTML + Logo)
# =========================================================
def render_beta_testing():
    st.header("3. Beta Testing Resources")
    
    # Sophisticated HTML Protocol
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 30px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; margin-top: 30px; }}
            .box {{ background: #fff; padding: 15px; border-left: 5px solid #3498db; margin: 15px 0; }}
            .warning {{ background: #fff; padding: 15px; border-left: 5px solid #e74c3c; margin: 15px 0; color: #c0392b; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #2c3e50; color: white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>CarePathIQ: Beta Testing Protocol</h1>
            <p><strong>Status:</strong> Draft | <strong>Target:</strong> {st.session_state.get('setting_input', 'ED')}</p>

            <h2>1. Objectives</h2>
            <div class="box">
                We are testing the system's ability to generate accurate clinical decision support.
                <br><strong>Primary Metric:</strong> Time to identifying the correct exclusion criteria.
            </div>

            <h2>2. Test Scenarios</h2>
            <h3>Scenario A: {st.session_state.get('condition_input', 'Hypertension')}</h3>
            <table>
                <tr><th>Step</th><th>Success Criteria</th></tr>
                <tr><td>1. Login & Navigation</td><td>Finds "Create New" < 10s.</td></tr>
                <tr><td>2. Input Criteria</td><td>Correctly inputs exclusion criteria.</td></tr>
                <tr><td>3. Verification</td><td>Identifies hallucinated drug dosages (Safety Check).</td></tr>
            </table>

            <div class="warning">
                CRITICAL SAFETY CHECK: Ensure user verifies all medication dosages against the hospital formulary.
            </div>

            {logo_html_tag}
        </div>
    </body>
    </html>
    """
    
    st.components.v1.html(html_content, height=600, scrolling=True)
    st.download_button("Download Protocol (HTML)", html_content, "Beta_Protocol.html", "text/html")

# =========================================================
# 4. EDUCATION MODULE (Restored Interactive LMS & Art Director)
# =========================================================
def generate_slide_deck_prompt(topic, audience, points):
    # ✅ RESTORED: The sophisticated "Art Director" prompt
    return f"""
    ACT AS: Senior Medical Education Designer and Visual Communication Expert.
    TASK: Create a 5-slide presentation outline for a new clinical pathway: "{topic}".
    TARGET AUDIENCE: {audience}.
    
    OUTPUT FORMAT: 
    For each slide, provide:
    1. SLIDE TITLE: Catchy and informative.
    2. VISUAL LAYOUT: Describe the visual composition (e.g., "Split screen: Old workflow vs. New workflow").
    3. BULLET POINTS: Max 3-4 high-impact lines per slide.
    4. SPEAKER NOTES: Script for the presenter explaining the "Why".
    5. ENGAGEMENT HOOK: A question or poll to ask the audience.

    DESIGN STYLE: Minimalist, clean, high-contrast text.
    """

def get_interactive_education_html(title, content, logo_tag):
    date_str = datetime.date.today().strftime("%B %d, %Y")
    # ✅ RESTORED: The Interactive LMS with Tabs, Quiz, and Certificate
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{ --primary: #2c3e50; --accent: #3498db; --success: #27ae60; --bg: #f4f7f6; }}
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; line-height: 1.6; color: #333; background: var(--bg); margin: 0; display: flex; flex-direction: column; min-height: 100vh; }}
            
            header {{ background: var(--primary); color: white; padding: 2rem 0; text-align: center; }}
            .container {{ max-width: 800px; margin: -30px auto 40px; background: white; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); overflow: hidden; padding-bottom: 20px; flex: 1; }}
            
            .tabs {{ display: flex; border-bottom: 1px solid #ddd; background: #f9f9f9; }}
            .tab-btn {{ flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #666; transition: 0.3s; }}
            .tab-btn:hover {{ background: #eee; }}
            .tab-btn.active {{ background: white; border-top: 3px solid var(--accent); color: var(--accent); }}
            
            .content-pane {{ display: none; padding: 30px; }}
            .content-pane.active {{ display: block; }}
            
            .quiz-question {{ background: #f0f8ff; padding: 15px; border-left: 4px solid var(--accent); margin-bottom: 20px; border-radius: 4px; }}
            .feedback {{ display: none; padding: 10px; margin-top: 10px; border-radius: 4px; font-weight: bold; }}
            .correct {{ background: #d4edda; color: #155724; display: block; }}
            .incorrect {{ background: #f8d7da; color: #721c24; display: block; }}
            
            /* Certificate Styles - Hidden until Print/Unlock */
            #certificate-view {{ display: none; text-align: center; padding: 50px; border: 10px solid var(--primary); background: white; position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; }}
            
            /* Print Styles */
            @media print {{
                body * {{ visibility: hidden; }}
                #certificate-view, #certificate-view * {{ visibility: visible; }}
                #certificate-view {{ position: absolute; left: 0; top: 0; width: 100%; border: 5px solid #333; }}
                .no-print {{ display: none !important; }}
            }}
            .footer {{ margin-top: auto; padding: 20px; text-align: right; border-top: 1px solid #ddd; }}
        </style>
    </head>
    <body>

    <header class="no-print">
        <h1>🎓 {title}</h1>
        <p>Interactive Staff Education Module</p>
    </header>

    <div class="container no-print" id="main-container">
        <div class="tabs">
            <button class="tab-btn active" onclick="openTab(event, 'Protocol')">1. The Protocol</button>
            <button class="tab-btn" onclick="openTab(event, 'Quiz')">2. Knowledge Check</button>
        </div>

        <div id="Protocol" class="content-pane active">
            <h2>Clinical Objectives</h2>
            <p>{content}</p>
            <h3>Exclusion Criteria</h3>
            <ul><li>Signs of end-organ damage</li><li>Recent dosage change</li></ul>
        </div>

        <div id="Quiz" class="content-pane">
            <h2>Verify Your Understanding</h2>
            <div class="quiz-question" id="q1">
                <p><strong>Q1: A patient presents with BP 190/100 and no symptoms. What is the primary goal?</strong></p>
                <button onclick="checkAnswer('correct', 'fb1')">Confirm absence of end-organ damage</button>
                <button onclick="checkAnswer('wrong', 'fb1')">Immediately lower BP</button>
                <div id="fb1" class="feedback"></div>
            </div>

            <div id="cert-unlock" style="display:none; margin-top:30px; background:#e8f6f3; padding:20px; border-radius:8px;">
                <h3>🎉 Module Complete!</h3>
                <p>Enter your full name to generate your certificate.</p>
                <input type="text" id="cert-name-input" placeholder="Dr. Jane Doe" style="padding:8px; width:60%;">
                <button onclick="generateCertificate()" style="padding:8px 16px; background:var(--success); color:white; border:none; cursor:pointer;">Generate Certificate</button>
            </div>
        </div>
        
        <div class="footer">{logo_tag}</div>
    </div>

    <div id="certificate-view">
        <h1 style="color: var(--primary);">Certificate of Completion</h1>
        <p>This certifies that</p>
        <h2 id="cert-name-display" style="font-family: 'Georgia', serif; font-size: 3em; margin: 20px 0; color: var(--accent);"></h2>
        <p>has successfully completed the education module for:</p>
        <h3>{title}</h3>
        <p>Date: <strong>{date_str}</strong></p>
        <div style="margin-top: 50px;">{logo_tag}</div>
    </div>

    <script>
        function openTab(evt, tabName) {{
            var i, x, tablinks;
            x = document.getElementsByClassName("content-pane");
            for (i = 0; i < x.length; i++) {{ x[i].className = "content-pane"; }}
            tablinks = document.getElementsByClassName("tab-btn");
            for (i = 0; i < tablinks.length; i++) {{ tablinks[i].className = tablinks[i].className.replace(" active", ""); }}
            document.getElementById(tabName).className += " active";
            evt.currentTarget.className += " active";
        }}

        function checkAnswer(val, fbId) {{
            var fb = document.getElementById(fbId);
            if(val === "correct") {{
                fb.innerHTML = "✅ Correct!"; fb.className = "feedback correct";
                document.getElementById("cert-unlock").style.display = "block";
            }} else {{
                fb.innerHTML = "❌ Incorrect. Review the Protocol."; fb.className = "feedback incorrect";
            }}
        }}

        function generateCertificate() {{
            var name = document.getElementById("cert-name-input").value;
            if(name.trim() === "") {{ alert("Please enter your name."); return; }}
            document.getElementById("cert-name-display").innerText = name;
            document.getElementById("main-container").style.display = "none";
            document.querySelector("header").style.display = "none";
            document.getElementById("certificate-view").style.display = "block";
            window.print();
        }}
    </script>
    </body>
    </html>
    """

def render_education_module():
    st.header("4. Education Module")
    mode = st.radio("Tool Selection", ["Slide Deck Prompter", "Interactive HTML Module"], horizontal=True)
    
    topic = st.session_state.get('condition_input', 'Asymptomatic Hypertension')
    points = st.text_area("Key Clinical Points", "Focus on ruling out end-organ damage. Do not treat asymptomatic numbers acutely.")
    
    if mode == "Slide Deck Prompter":
        if st.button("Generate Slide Outline"):
            prompt = generate_slide_deck_prompt(topic, "Resident Physicians", points)
            st.code(prompt, language="markdown")
            
    elif mode == "Interactive HTML Module":
        if st.button("Generate Interactive Module"):
            html_content = get_interactive_education_html(topic, points, logo_html_tag)
            st.components.v1.html(html_content, height=600, scrolling=True)
            st.download_button(
                label="Download HTML Module",
                data=html_content,
                file_name="Education_Module.html",
                mime="text/html"
            )

# =========================================================
# MAIN APP
# =========================================================
def main():
    with st.sidebar:
        if logo_b64: st.image(f"data:image/png;base64,{logo_b64}", use_column_width=True)
        else: st.title("CarePathIQ")
        st.markdown("---")
        menu = st.radio("Navigation", ["Pathway Generation", "Heuristic Analysis", "Beta Testing Guide", "Education Module"])
        st.markdown("---")
        with st.expander("Give Feedback"):
            with st.form("fb"):
                st.text_area("Comments:")
                if st.form_submit_button("Submit"): st.success("Sent!")

    if menu == "Pathway Generation": render_pathway_generator()
    elif menu == "Heuristic Analysis": render_heuristic_dashboard()
    elif menu == "Beta Testing Guide": render_beta_testing()
    elif menu == "Education Module": render_education_module()

if __name__ == "__main__":
    main()
```