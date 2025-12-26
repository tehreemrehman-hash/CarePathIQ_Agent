"""
Phase 5 Helper Functions for Shareable HTML & Document Generation
Generates standalone HTML files for Expert Panel, Beta Testing, and Education Module
Plus Word documents for Executive Summaries
"""

import json
import base64
from io import BytesIO
from datetime import datetime

# ==========================================
# SHARED STYLING & CONSTANTS
# ==========================================

CAREPATHIQ_COLORS = {
    "brown": "#5D4037",
    "brown_dark": "#3E2723",
    "teal": "#A9EED1",
    "light_gray": "#f5f5f5",
    "border_gray": "#ddd",
}

CAREPATHIQ_FOOTER = """
<div class="carepathiq-footer">
    <p style="margin: 10px 0;">
        <strong>CarePathIQ</strong> © 2024 by Tehreem Rehman
    </p>
    <p style="margin: 5px 0; font-size: 0.9em;">
        Licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank">CC BY-SA 4.0</a>
    </p>
</div>
"""

SHARED_CSS = """
:root {
    --brown: #5D4037;
    --brown-dark: #3E2723;
    --teal: #A9EED1;
    --light-gray: #f5f5f5;
    --border-gray: #ddd;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #fafafa;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.header {
    text-align: center;
    color: var(--brown-dark);
    border-bottom: 3px solid var(--teal);
    padding-bottom: 15px;
    margin-bottom: 30px;
}

.header h1 {
    font-size: 2em;
    margin-bottom: 5px;
}

.header p {
    font-size: 1.1em;
    color: #666;
}

.form-group {
    margin: 20px 0;
}

label {
    font-weight: 600;
    display: block;
    margin-bottom: 8px;
    color: var(--brown-dark);
}

input[type="text"],
input[type="email"],
input[type="number"],
textarea,
select {
    width: 100%;
    padding: 10px;
    border: 1px solid var(--border-gray);
    border-radius: 4px;
    font-family: inherit;
    font-size: 1em;
}

textarea {
    min-height: 100px;
    resize: vertical;
}

input:focus,
textarea:focus,
select:focus {
    outline: none;
    border-color: var(--teal);
    box-shadow: 0 0 5px rgba(169, 238, 209, 0.3);
}

button {
    background-color: var(--brown);
    color: white;
    padding: 12px 24px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1em;
    font-weight: 600;
    transition: background-color 0.3s ease;
    margin-right: 10px;
    margin-bottom: 10px;
}

button:hover {
    background-color: var(--brown-dark);
}

button:active {
    transform: scale(0.98);
}

.button-group {
    margin: 20px 0;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.node-card {
    border: 1px solid var(--border-gray);
    padding: 15px;
    margin: 15px 0;
    border-radius: 6px;
    background-color: var(--light-gray);
}

.node-card h3 {
    color: var(--brown);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
}

.node-badge {
    background-color: var(--teal);
    color: var(--brown-dark);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.85em;
    margin-right: 10px;
    font-weight: 600;
}

.node-type {
    font-size: 0.9em;
    color: #666;
    margin-bottom: 10px;
}

.checkbox-group {
    display: flex;
    align-items: center;
    margin: 10px 0;
}

.checkbox-group input[type="checkbox"] {
    width: auto;
    margin-right: 10px;
    cursor: pointer;
}

.checkbox-group label {
    margin: 0;
    cursor: pointer;
    font-weight: 500;
}

.expandable-section {
    margin-left: 20px;
    margin-top: 10px;
    padding: 10px;
    background-color: white;
    border-left: 3px solid var(--teal);
    display: none;
}

.expandable-section.show {
    display: block;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background-color: var(--border-gray);
    border-radius: 4px;
    overflow: hidden;
    margin: 10px 0;
}

.progress-fill {
    height: 100%;
    background-color: var(--teal);
    transition: width 0.3s ease;
}

.carepathiq-footer {
    text-align: center;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border-gray);
    color: #666;
    font-size: 0.9em;
}

.carepathiq-footer a {
    color: var(--brown);
    text-decoration: none;
}

.carepathiq-footer a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    .container {
        padding: 15px;
    }
    
    .header h1 {
        font-size: 1.5em;
    }
    
    .button-group {
        flex-direction: column;
    }
    
    button {
        width: 100%;
    }
}
"""

# ==========================================
# EXPERT PANEL FEEDBACK FORM
# ==========================================

def generate_expert_form_html(
    condition: str,
    nodes: list,
    audience: str = "Clinical Experts",
    organization: str = "CarePathIQ"
) -> str:
    """
    Generate standalone expert panel feedback form with CSV download capability.
    
    Args:
        condition: Clinical condition being reviewed
        nodes: List of pathway nodes (dicts with 'type', 'label', 'evidence')
        audience: Target audience description
        organization: Organization name
        
    Returns:
        Complete standalone HTML string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nodes_json = json.dumps(nodes)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expert Panel Feedback: {condition}</title>
    <style>
        {SHARED_CSS}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Expert Panel Feedback</h1>
            <p><strong>{condition}</strong> Clinical Pathway Review</p>
            <p style="font-size: 0.95em; margin-top: 10px;">Target Audience: {audience}</p>
        </div>

        <form id="feedbackForm">
            <div class="form-group">
                <label for="reviewer_name">Your Name *</label>
                <input type="text" id="reviewer_name" name="reviewer_name" required placeholder="Full name">
            </div>

            <div class="form-group">
                <label for="reviewer_email">Your Email *</label>
                <input type="email" id="reviewer_email" name="reviewer_email" required placeholder="email@institution.org">
            </div>

            <div class="form-group">
                <label for="reviewer_role">Your Role/Title</label>
                <input type="text" id="reviewer_role" name="reviewer_role" placeholder="e.g., Emergency Medicine Physician">
            </div>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid var(--border-gray);">

            <h2 style="color: var(--brown-dark); margin-bottom: 20px;">Pathway Nodes</h2>
            <p style="margin-bottom: 20px; color: #666;">Please review each node and provide feedback. Only nodes with feedback will be included in the download.</p>

            <div id="nodesContainer"></div>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid var(--border-gray);">

            <div class="form-group">
                <label for="overall_feedback">Overall Feedback (Optional)</label>
                <textarea id="overall_feedback" name="overall_feedback" placeholder="Any additional comments about the entire pathway..."></textarea>
            </div>

            <div class="form-group">
                <label for="implementation_barriers">Anticipated Implementation Barriers (Optional)</label>
                <textarea id="implementation_barriers" name="implementation_barriers" placeholder="What challenges do you foresee in implementing this pathway?"></textarea>
            </div>

            <div class="button-group">
                <button type="button" onclick="downloadAsCSV()">Download Responses (CSV)</button>
                <button type="button" onclick="downloadAsJSON()">Download Responses (JSON)</button>
                <button type="reset">Reset Form</button>
            </div>
        </form>

        {CAREPATHIQ_FOOTER}
    </div>

    <script>
        const pathwayNodes = {nodes_json};
        const condition = "{condition}";
        const timestamp = "{timestamp}";

        // Populate nodes on page load
        document.addEventListener('DOMContentLoaded', function() {{
            renderNodes();
        }});

        function renderNodes() {{
            const container = document.getElementById('nodesContainer');
            pathwayNodes.forEach((node, idx) => {{
                const nodeHTML = `
                    <div class="node-card">
                        <h3>
                            <span class="node-badge">Node ${{idx + 1}}</span>
                            ${{node.label || 'Step'}}
                        </h3>
                        <div class="node-type">
                            <strong>Type:</strong> ${{node.type || 'Process'}}
                            ${{node.evidence && node.evidence !== 'N/A' ? ` | <strong>Evidence:</strong> PMID ${{node.evidence}}` : ''}}
                        </div>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" id="feedback_check_${{idx}}" onchange="toggleExpansion(${{idx}})">
                            <label for="feedback_check_${{idx}}">I have feedback on this node</label>
                        </div>

                        <div id="expansion_${{idx}}" class="expandable-section">
                            <div class="form-group">
                                <label for="feedback_${{idx}}">Proposed Change or Concern *</label>
                                <textarea name="feedback_${{idx}}" id="feedback_${{idx}}" placeholder="Describe the issue or suggested improvement..." required></textarea>
                            </div>

                            <div class="form-group">
                                <label for="source_${{idx}}">Justification Source *</label>
                                <select name="source_${{idx}}" id="source_${{idx}}" required>
                                    <option value="">-- Select --</option>
                                    <option value="Peer-Reviewed Literature">Peer-Reviewed Literature</option>
                                    <option value="National Guideline">National Guideline (ACLS, AHA, etc.)</option>
                                    <option value="Institutional Policy">Institutional Policy</option>
                                    <option value="Patient Safety Concern">Patient Safety Concern</option>
                                    <option value="Feasibility Issue">Feasibility Issue</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="details_${{idx}}">Supporting Details/Citation</label>
                                <textarea name="details_${{idx}}" id="details_${{idx}}" placeholder="Reference, PMID, guideline citation, or rationale..."></textarea>
                            </div>
                        </div>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', nodeHTML);
            }});
        }}

        function toggleExpansion(nodeIdx) {{
            const expansion = document.getElementById('expansion_' + nodeIdx);
            const checkbox = document.getElementById('feedback_check_' + nodeIdx);
            if (checkbox.checked) {{
                expansion.classList.add('show');
            }} else {{
                expansion.classList.remove('show');
            }}
        }}

        function downloadAsCSV() {{
            const rows = [
                ['Reviewer Name', 'Email', 'Role', 'Node ID', 'Node Label', 'Feedback', 'Source', 'Details']
            ];

            const reviewerName = document.getElementById('reviewer_name').value || 'Anonymous';
            const reviewerEmail = document.getElementById('reviewer_email').value || '';
            const reviewerRole = document.getElementById('reviewer_role').value || '';

            // Collect feedback from nodes
            pathwayNodes.forEach((node, idx) => {{
                const checkbox = document.getElementById('feedback_check_' + idx);
                if (checkbox && checkbox.checked) {{
                    const feedback = document.getElementById('feedback_' + idx)?.value || '';
                    const source = document.getElementById('source_' + idx)?.value || '';
                    const details = document.getElementById('details_' + idx)?.value || '';
                    
                    if (feedback) {{
                        rows.push([
                            reviewerName,
                            reviewerEmail,
                            reviewerRole,
                            'N' + (idx + 1),
                            node.label,
                            feedback,
                            source,
                            details
                        ]);
                    }}
                }}
            }});

            // Add overall feedback if present
            const overallFeedback = document.getElementById('overall_feedback').value;
            const implementationBarriers = document.getElementById('implementation_barriers').value;
            
            if (overallFeedback) {{
                rows.push(['', reviewerEmail, '', '', 'OVERALL FEEDBACK', overallFeedback, '', '']);
            }}
            
            if (implementationBarriers) {{
                rows.push(['', reviewerEmail, '', '', 'IMPLEMENTATION BARRIERS', implementationBarriers, '', '']);
            }}

            // Convert to CSV
            const csv = rows.map(row => 
                row.map(cell => '"' + (cell || '').replace(/"/g, '""') + '"').join(',')
            ).join('\\n');

            // Download
            const safeCondition = condition.replace(/\\s+/g, '_');
            const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `expert_feedback_${{safeCondition}}_${{timestamp}}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}

        function downloadAsJSON() {{
            const formData = {{
                timestamp: new Date().toISOString(),
                condition: condition,
                reviewer: {{
                    name: document.getElementById('reviewer_name').value,
                    email: document.getElementById('reviewer_email').value,
                    role: document.getElementById('reviewer_role').value
                }},
                nodeFeedback: [],
                overallFeedback: document.getElementById('overall_feedback').value,
                implementationBarriers: document.getElementById('implementation_barriers').value
            }};

            pathwayNodes.forEach((node, idx) => {{
                const checkbox = document.getElementById('feedback_check_' + idx);
                if (checkbox && checkbox.checked) {{
                    formData.nodeFeedback.push({{
                        nodeId: 'N' + (idx + 1),
                        nodeLabel: node.label,
                        nodeType: node.type,
                        feedback: document.getElementById('feedback_' + idx)?.value || '',
                        source: document.getElementById('source_' + idx)?.value || '',
                        details: document.getElementById('details_' + idx)?.value || ''
                    }});
                }}
            }});

            const json = JSON.stringify(formData, null, 2);
            const safeCondition = condition.replace(/\\s+/g, '_');
            const blob = new Blob([json], {{ type: 'application/json' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `expert_feedback_${{safeCondition}}_${{timestamp}}.json`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
    </script>
</body>
</html>"""
    
    return html


# ==========================================
# BETA TESTING FEEDBACK FORM
# ==========================================

def generate_beta_form_html(
    condition: str,
    nodes: list,
    audience: str = "Clinical Team",
    organization: str = "CarePathIQ"
) -> str:
    """
    Generate enhanced standalone beta testing form with:
    - Scenario-driven testing (typical, comorbidity, urgent)
    - Nielsen's 10 heuristics evaluation
    - Per-node correctness, errors, time tracking
    - Optional System Usability Scale (SUS)
    - CSV exports (summary + node details) and JSON payload
    
    Args:
        condition: Clinical condition being tested
        nodes: List of pathway nodes
        audience: Target audience description
        organization: Organization name
        
    Returns:
        Complete standalone HTML string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nodes_json = json.dumps(nodes or [])
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{condition} — Beta Testing</title>
<style>
{SHARED_CSS}
.row {{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}}
.row3 {{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px}}
.flex {{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
table {{width:100%;border-collapse:collapse;margin:15px 0}}
th,td {{border:1px solid var(--border-gray);padding:10px;text-align:left}}
th {{background:#f8f9fa;font-weight:600;color:var(--brown-dark)}}
select,input[type="number"],textarea {{width:100%;padding:8px;border:1px solid var(--border-gray);border-radius:4px}}
textarea {{min-height:60px;resize:vertical}}
.badge {{display:inline-block;background:var(--teal);color:var(--brown-dark);padding:4px 10px;border-radius:12px;font-size:0.9em;font-weight:600}}
.timer {{font-family:monospace;font-size:1.1em;font-weight:bold;color:var(--brown)}}
button[type="button"] {{margin:5px;padding:10px 18px;font-size:0.95em}}
label {{display:block;margin-bottom:5px;font-weight:500;color:var(--brown-dark)}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>{condition} — Beta Testing</h1>
<p style="margin-top:8px">Scenario-based usability evaluation • Nielsen heuristics • Optional SUS</p>
<p style="font-size:0.9em;margin-top:5px">Target Audience: {audience} | {organization}</p>
</div>

<form id="betaForm">
<!-- Tester Info -->
<div class="form-group">
<label for="tester_name">Your Name *</label>
<input type="text" id="tester_name" required placeholder="Full name">
</div>
<div class="row">
<div class="form-group">
<label for="tester_email">Email *</label>
<input type="email" id="tester_email" required placeholder="email@example.com">
</div>
<div class="form-group">
<label for="tester_role">Role *</label>
<input type="text" id="tester_role" required placeholder="e.g., RN, Physician">
</div>
</div>

<hr style="margin:25px 0;border:none;border-top:1px solid var(--border-gray)">

<!-- Scenario Timers -->
<h2 style="color:var(--brown-dark);margin-bottom:10px">Clinical Scenarios</h2>
<p style="margin:0 0 10px 0;color:#666">Work through each scenario using the pathway. Start/stop each timer as you complete the scenario.</p>
<table>
    <thead>
        <tr>
            <th style="width:220px">Scenario</th>
            <th>Description</th>
            <th style="width:240px">Timer</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Typical: Stable Outpatient</strong></td>
            <td id="desc_typical"></td>
            <td>
                <div class="flex">
                    <span id="timer_typical" class="timer badge">00:00</span>
                    <button type="button" onclick="startTimerFor('typical')">Start</button>
                    <button type="button" onclick="stopTimerFor('typical')">Stop</button>
                    <button type="button" onclick="resetTimerFor('typical')">Reset</button>
                    <button type="button" onclick="recordRun('typical')">Record Run</button>
                </div>
            </td>
        </tr>
        <tr>
            <td><strong>Complex: Multiple Comorbidities</strong></td>
            <td id="desc_comorbidity"></td>
            <td>
                <div class="flex">
                    <span id="timer_comorbidity" class="timer badge">00:00</span>
                    <button type="button" onclick="startTimerFor('comorbidity')">Start</button>
                    <button type="button" onclick="stopTimerFor('comorbidity')">Stop</button>
                    <button type="button" onclick="resetTimerFor('comorbidity')">Reset</button>
                    <button type="button" onclick="recordRun('comorbidity')">Record Run</button>
                </div>
            </td>
        </tr>
        <tr>
            <td><strong>Urgent: Acute Presentation</strong></td>
            <td id="desc_urgent"></td>
            <td>
                <div class="flex">
                    <span id="timer_urgent" class="timer badge">00:00</span>
                    <button type="button" onclick="startTimerFor('urgent')">Start</button>
                    <button type="button" onclick="stopTimerFor('urgent')">Stop</button>
                    <button type="button" onclick="resetTimerFor('urgent')">Reset</button>
                    <button type="button" onclick="recordRun('urgent')">Record Run</button>
                </div>
            </td>
        </tr>
    </tbody>
</table>

<div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
    <div style="font-weight:600;color:var(--brown-dark)">Recorded Runs</div>
    <div class="flex">
        <button type="button" onclick="downloadRunsCSV()">Download Runs CSV</button>
        <button type="button" onclick="clearSaved()">Clear Saved</button>
    </div>
    <table style="width:100%">
        <thead>
            <tr><th style="width:220px">Scenario</th><th style="width:140px">Seconds</th><th>Timestamp</th></tr>
        </thead>
        <tbody id="runsBody"></tbody>
    </table>
  
</div>

<hr style="margin:25px 0;border:none;border-top:1px solid var(--border-gray)">

<!-- Nielsen Heuristics -->
<h2 style="color:var(--brown-dark);margin-bottom:15px">Nielsen Heuristics (1–5)</h2>
<table>
<thead><tr><th>Heuristic</th><th>Rating</th><th>Comments</th></tr></thead>
<tbody id="heuristicsBody"></tbody>
</table>

<hr style="margin:25px 0;border:none;border-top:1px solid var(--border-gray)">

<!-- System Usability Scale (SUS) -->
<div class="flex" style="justify-content:space-between">
<h2 style="color:var(--brown-dark);margin:0">System Usability Scale (SUS)</h2>
<label class="flex" style="font-weight:normal;margin:0">
<input type="checkbox" id="susEnable" style="width:auto;margin-right:6px"> Include SUS
</label>
</div>
<div id="susBlock" style="display:none;margin-top:15px">
<table>
<thead><tr><th style="width:60px">#</th><th>Statement</th><th style="width:120px">Score (1–5)</th></tr></thead>
<tbody id="susBody"></tbody>
</table>
<div class="flex" style="margin-top:12px">
<span style="font-weight:600">SUS Score:</span>
<span id="susScore" class="badge">—</span>
<span style="font-size:0.85em;color:#666;margin-left:10px">(0–100 scale; ≥68 = above average)</span>
</div>
</div>

<hr style="margin:25px 0;border:none;border-top:1px solid var(--border-gray)">

<!-- Workflow Nodes -->
<h2 style="color:var(--brown-dark);margin-bottom:15px">Workflow Nodes</h2>
<div id="nodesContainer"></div>

<hr style="margin:25px 0;border:none;border-top:1px solid var(--border-gray)">

<!-- Overall Experience -->
<h2 style="color:var(--brown-dark);margin-bottom:15px">Overall Experience</h2>
<div class="row">
<div class="form-group">
<label for="ease">Ease of use (1–5)</label>
<select id="ease">
<option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option>
</select>
</div>
<div class="form-group">
<label for="fit">Workflow fit (1–5)</label>
<select id="fit">
<option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option>
</select>
</div>
</div>
<div class="row">
<div class="form-group">
<label for="positives">What worked well?</label>
<textarea id="positives" placeholder="Strengths and positive aspects..."></textarea>
</div>
<div class="form-group">
<label for="improvements">What needs improvement?</label>
<textarea id="improvements" placeholder="Issues or suggestions..."></textarea>
</div>
</div>

<div class="button-group">
<button type="button" onclick="downloadSummaryCSV()">Download Summary CSV</button>
<button type="button" onclick="downloadNodeCSV()">Download Node Details CSV</button>
<button type="button" onclick="downloadRunsCSV()">Download Runs CSV</button>
<button type="button" onclick="downloadJSON()">Download JSON</button>
<button type="reset">Reset Form</button>
</div>
</form>

{CAREPATHIQ_FOOTER}
</div>

<script>
const SCENARIOS = {{
  typical: {{
    name: "Typical: Stable Outpatient",
    desc: "A stable patient with a straightforward condition. Focus: clarity, speed, and guidance.",
    tasks: ["Identify initial assessment path","Document routine follow-up","Recommend standard education"]
  }},
  comorbidity: {{
    name: "Complex: Multiple Comorbidities",
    desc: "A patient with multiple chronic conditions. Focus: flexibility, error prevention, and help.",
    tasks: ["Navigate branching decisions","Resolve conflicting recommendations","Tailor education to comorbidities"]
  }},
  urgent: {{
    name: "Urgent: Acute Presentation",
    desc: "An urgent scenario requiring rapid triage. Focus: visibility, control, and feedback.",
    tasks: ["Select urgent triage path","Prioritize critical actions","Confirm clear system status"]
  }}
}};

const HEURISTICS = [
  "Visibility of system status",
  "Match between system and real world",
  "User control and freedom",
  "Consistency and standards",
  "Error prevention",
  "Recognition rather than recall",
  "Flexibility and efficiency of use",
  "Aesthetic and minimalist design",
  "Help users recognize, diagnose, recover",
  "Help and documentation"
];

const SUS_ITEMS = [
  "I think that I would like to use this system frequently.",
  "I found the system unnecessarily complex.",
  "I thought the system was easy to use.",
  "I think that I would need the support of a technical person to use this system.",
  "I found the various functions in this system were well integrated.",
  "I thought there was too much inconsistency in this system.",
  "I would imagine that most people would learn to use this system very quickly.",
  "I found the system very cumbersome to use.",
  "I felt very confident using the system.",
  "I needed to learn a lot of things before I could get going with this system."
];

const condition = "{condition}";
const STORAGE_KEY = "betaFormState_" + condition.replace(/\s+/g, '_');
const NODES = {nodes_json};

function pad(n) {{ return String(n).padStart(2,'0'); }}

// Independent timers for three scenarios
let scenarioTimes = {{ typical: 0, comorbidity: 0, urgent: 0 }};
let runs = [];
let activeTimer = null; // which scenario key is running
let startEpoch = null;

function renderAllTimers() {{
    ['typical','comorbidity','urgent'].forEach(key => {{
        const v = scenarioTimes[key] || 0;
        const m = Math.floor(v/60), s = v%60;
        const el = document.getElementById('timer_' + key);
        if (el) el.textContent = pad(m)+':'+pad(s);
    }});
}}

function tick() {{
    if (!activeTimer || startEpoch === null) return;
    const now = Date.now();
    scenarioTimes[activeTimer] = Math.max(0, Math.floor((now - startEpoch)/1000));
    renderAllTimers();
}}
setInterval(tick, 250);

function startTimerFor(key) {{
    activeTimer = key;
    startEpoch = Date.now() - (scenarioTimes[key]*1000);
}}
function stopTimerFor(key) {{
    if (activeTimer === key) {{ activeTimer = null; }}
}}
function resetTimerFor(key) {{
    scenarioTimes[key] = 0;
    if (activeTimer === key) {{ startEpoch = Date.now(); }}
    renderAllTimers();
}}

// Scenario descriptions
document.getElementById('desc_typical').innerHTML = SCENARIOS.typical.desc + '<br><span style="color:#666">Tasks: ' + SCENARIOS.typical.tasks.join(' • ') + '</span>';
document.getElementById('desc_comorbidity').innerHTML = SCENARIOS.comorbidity.desc + '<br><span style="color:#666">Tasks: ' + SCENARIOS.comorbidity.tasks.join(' • ') + '</span>';
document.getElementById('desc_urgent').innerHTML = SCENARIOS.urgent.desc + '<br><span style="color:#666">Tasks: ' + SCENARIOS.urgent.tasks.join(' • ') + '</span>';
renderAllTimers();

function recordRun(key) {{
    const secs = scenarioTimes[key] || 0;
    runs.push({{ scenario: key, seconds: secs, timestamp: new Date().toISOString() }});
    renderRuns();
    scheduleSave();
}}

function renderRuns() {{
    const body = document.getElementById('runsBody');
    if (!body) return;
    body.innerHTML = '';
    runs.forEach(r => {{
        const tr = document.createElement('tr');
        const name = SCENARIOS[r.scenario]?.name || r.scenario;
        tr.innerHTML = `<td>${{name}}</td><td>${{r.seconds}}</td><td>${{r.timestamp}}</td>`;
        body.appendChild(tr);
    }});
}}

// Autosave helpers and run exports
let _saveDebounce = null;
function scheduleSave() {{
  clearTimeout(_saveDebounce);
  _saveDebounce = setTimeout(saveState, 300);
}}
function saveState() {{
  try {{
    const {{ summary, nodes }} = collectData();
    const state = {{ summary, nodes, runs, scenarioTimes }};
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }} catch (e) {{}}
}}
function restoreState() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const state = JSON.parse(raw);
    const setVal = (id, val) => {{ const el = document.getElementById(id); if (!el) return; if (el.type === 'checkbox') {{ el.checked = !!val; }} else if (typeof val !== 'undefined' && val !== null) {{ el.value = val; }} }};

    // Scenario timers
    if (state.scenarioTimes) {{
      scenarioTimes = state.scenarioTimes;
      activeTimer = null;
      startEpoch = null;
      renderAllTimers();
    }}

    const s = state.summary || {{}};
    setVal('tester_name', s.testerName || '');
    setVal('tester_email', s.testerEmail || '');
    setVal('tester_role', s.testerRole || '');
    setVal('ease', s.ease);
    setVal('fit', s.fit);
    setVal('positives', s.positives || '');
    setVal('improvements', s.improvements || '');

    // Heuristics
    if (Array.isArray(s.heuristics)) {{
      s.heuristics.forEach((h, i) => {{
        setVal('h_rate_'+i, h.rating);
        setVal('h_comment_'+i, h.comments || '');
      }});
    }}

    // SUS
    if (s.susEnabled) {{
      const chk = document.getElementById('susEnable');
      if (chk) {{
        chk.checked = true;
        document.getElementById('susBlock').style.display = 'block';
        if (document.getElementById('susBody').children.length === 0) {{ renderSUS(); }}
      }}
      if (Array.isArray(s.susScores)) {{
        s.susScores.forEach((v,i) => setVal('sus_'+i, v));
        computeSUS();
      }}
    }}

    // Nodes
    if (Array.isArray(state.nodes)) {{
      state.nodes.forEach((n, idx) => {{
        setVal('correct_'+idx, n.correctness);
        setVal('errors_'+idx, n.errors);
        setVal('time_'+idx, n.timeSeconds);
        const uc = document.getElementById('unclear_'+idx); if (uc) uc.checked = !!n.unclear;
        setVal('issue_'+idx, n.issue || '');
        setVal('suggest_'+idx, n.suggestion || '');
      }});
    }}

    // Runs
    if (Array.isArray(state.runs)) {{
      runs = state.runs;
      renderRuns();
    }}
  }} catch (e) {{}}
}}

// Wire autosave on form changes
const _formEl = document.getElementById('betaForm');
if (_formEl) {{
  _formEl.addEventListener('input', scheduleSave);
  _formEl.addEventListener('change', scheduleSave);
}}

function downloadRunsCSV() {{
  const rows = runs.map(r => ({{
    scenario: SCENARIOS[r.scenario]?.name || r.scenario,
    seconds: r.seconds,
    timestamp: r.timestamp
  }}));
  if (!rows.length) {{ alert('No runs recorded yet.'); return; }}
  const safeCondition = condition.replace(/\s+/g, '_');
  download(`Beta_Runs_${{safeCondition}}_{timestamp}.csv`, toCSV(rows), 'text/csv');
}}

function clearSaved() {{
  try {{ localStorage.removeItem(STORAGE_KEY); }} catch (e) {{}}
  runs = [];
  renderRuns();
  alert('Saved state cleared for this form.');
}}

// Render Nielsen Heuristics
HEURISTICS.forEach((h, i) => {{
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${{h}}</td>
  <td><select id="h_rate_${{i}}"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></td>
  <td><textarea id="h_comment_${{i}}" placeholder="Notes (optional)"></textarea></td>`;
  document.getElementById('heuristicsBody').appendChild(tr);
}});

// Render SUS
function renderSUS() {{
  const tbody = document.getElementById('susBody');
  SUS_ITEMS.forEach((txt, i) => {{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${{i+1}}</td><td>${{txt}}</td>
    <td><select id="sus_${{i}}"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></td>`;
    tbody.appendChild(tr);
  }});
  for (let i=0; i<10; i++) {{
    document.getElementById('sus_' + i).onchange = computeSUS;
  }}
  computeSUS();
}}

function computeSUS() {{
  let total = 0;
  for (let i=0; i<10; i++) {{
    const v = parseInt(document.getElementById('sus_' + i).value, 10);
    total += (i%2===0) ? (v-1) : (5-v);
  }}
  const score = (total * 2.5).toFixed(1);
  document.getElementById('susScore').textContent = score;
  return parseFloat(score);
}}

document.getElementById('susEnable').onchange = (e) => {{
  const show = e.target.checked;
  document.getElementById('susBlock').style.display = show ? 'block' : 'none';
  if (show && document.getElementById('susBody').children.length === 0) {{
    renderSUS();
  }}
}};

// Render Nodes
if (!NODES || NODES.length === 0) {{
  document.getElementById('nodesContainer').innerHTML = '<p style="color:#666;font-style:italic">No nodes provided. Use this form to test general usability.</p>';
}} else {{
  NODES.forEach((n, idx) => {{
    const card = document.createElement('div');
    card.className = 'node-card';
    card.innerHTML = `
    <div class="flex" style="justify-content:space-between">
    <strong>${{n.name || n.label || n.title || 'Node'}} <span class="node-badge">#${{idx+1}}</span></strong>
    <label class="flex" style="font-weight:normal;margin:0">
    <input type="checkbox" id="unclear_${{idx}}" style="width:auto;margin-right:6px"> Unclear/Problematic
    </label>
    </div>
    <p style="color:#666;font-size:0.9em;margin:5px 0">${{n.description||''}}</p>
    <div class="row3">
    <div><label>Correctness</label>
    <select id="correct_${{idx}}"><option>Incorrect</option><option>Partial</option><option selected>Correct</option></select></div>
    <div><label>Errors (count)</label><input type="number" id="errors_${{idx}}" min="0" value="0"></div>
    <div><label>Time (seconds)</label><input type="number" id="time_${{idx}}" min="0" value="0"></div>
    </div>
    <div class="row" style="margin-top:10px">
    <div><label>Issue (if any)</label><textarea id="issue_${{idx}}" placeholder="Describe issue"></textarea></div>
    <div><label>Suggestion</label><textarea id="suggest_${{idx}}" placeholder="Improvement"></textarea></div>
    </div>`;
    document.getElementById('nodesContainer').appendChild(card);
  }});
}}

function collectData() {{

  const heuristics = HEURISTICS.map((h, i) => ({{
    name: h,
    rating: parseInt(document.getElementById('h_rate_' + i).value, 10),
    comments: document.getElementById('h_comment_' + i).value.trim()
  }}));

  const susEnabled = document.getElementById('susEnable').checked;
  const susScores = susEnabled ? [...Array(10)].map((_, i) => parseInt(document.getElementById('sus_' + i).value, 10)) : [];
  const susScore = susEnabled ? computeSUS() : null;

  const nodes = (NODES||[]).map((n, idx) => ({{
    index: idx+1,
    id: n.id ?? null,
    name: n.name ?? n.label ?? n.title ?? 'Node ' + (idx+1),
    description: n.description ?? "",
    correctness: document.getElementById('correct_' + idx).value,
    errors: parseInt(document.getElementById('errors_' + idx).value, 10) || 0,
    timeSeconds: parseInt(document.getElementById('time_' + idx).value, 10) || 0,
    unclear: document.getElementById('unclear_' + idx).checked,
    issue: document.getElementById('issue_' + idx).value.trim(),
    suggestion: document.getElementById('suggest_' + idx).value.trim()
  }}));

    const summary = {{
    appTitle: "{condition}",
    testerName: document.getElementById('tester_name').value,
    testerEmail: document.getElementById('tester_email').value,
    testerRole: document.getElementById('tester_role').value,
        scenarioTimes: {{ typical: scenarioTimes.typical, comorbidity: scenarioTimes.comorbidity, urgent: scenarioTimes.urgent }},
    ease: parseInt(document.getElementById('ease').value, 10),
    fit: parseInt(document.getElementById('fit').value, 10),
    positives: document.getElementById('positives').value.trim(),
    improvements: document.getElementById('improvements').value.trim(),
    heuristics,
    susEnabled,
    susScores,
    susScore
  }};
  return {{summary, nodes}};
}}

function toCSV(rows) {{
  const headers = Object.keys(rows[0] || {{}});
  const esc = v => '"' + String(v??'').replace(/"/g,'""') + '"';
  const out = [headers.join(",")].concat(rows.map(r => headers.map(h => esc(r[h])).join(",")));
  return out.join("\n");
}}

function download(filename, content, mime) {{
  const blob = new Blob([content], {{type: mime}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href=url;
  a.download=filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}}

function downloadSummaryCSV() {{
  const {{summary}} = collectData();
  const rows = [];

  // Heuristics
    HEURISTICS.forEach((name, i) => {{
    const h = summary.heuristics[i];
    rows.push({{
      section: "Heuristic",
      name: name,
      rating: h.rating,
      comments: h.comments,
            scenarioTypicalSeconds: summary.scenarioTimes.typical,
            scenarioComorbiditySeconds: summary.scenarioTimes.comorbidity,
            scenarioUrgentSeconds: summary.scenarioTimes.urgent,
      tester: summary.testerName
    }});
  }});

  // Overall
  rows.push({{
    section: "Overall",
    name: "Experience",
    rating: "",
    comments: 'Ease=' + summary.ease + '; Fit=' + summary.fit + '; Positives=' + summary.positives + '; Improvements=' + summary.improvements,
        scenarioTypicalSeconds: summary.scenarioTimes.typical,
        scenarioComorbiditySeconds: summary.scenarioTimes.comorbidity,
        scenarioUrgentSeconds: summary.scenarioTimes.urgent,
    tester: summary.testerName
  }});

  // SUS
  if (summary.susEnabled) {{
    rows.push({{
      section: "SUS",
      name: "SUS Score",
      rating: summary.susScore,
      comments: 'Responses=' + summary.susScores.join('|'),
            scenarioTypicalSeconds: summary.scenarioTimes.typical,
            scenarioComorbiditySeconds: summary.scenarioTimes.comorbidity,
            scenarioUrgentSeconds: summary.scenarioTimes.urgent,
      tester: summary.testerName
    }});
  }}

  const safeCondition = condition.replace(/\\s+/g, '_');
  download(`Beta_Summary_${{safeCondition}}_{timestamp}.csv`, toCSV(rows), "text/csv");
}}

function downloadNodeCSV() {{
  const {{nodes, summary}} = collectData();
  const rows = nodes.map(n => ({{
        scenarioTypicalSeconds: summary.scenarioTimes.typical,
        scenarioComorbiditySeconds: summary.scenarioTimes.comorbidity,
        scenarioUrgentSeconds: summary.scenarioTimes.urgent,
    tester: summary.testerName,
    nodeIndex: n.index,
    nodeId: n.id ?? "",
    nodeName: n.name,
    correctness: n.correctness,
    errors: n.errors,
    timeSeconds: n.timeSeconds,
    unclear: n.unclear,
    issue: n.issue,
    suggestion: n.suggestion
  }}));
  const safeCondition = condition.replace(/\\s+/g, '_');
  download(`Beta_NodeDetails_${{safeCondition}}_{timestamp}.csv`, toCSV(rows), "text/csv");
}}

function downloadJSON() {{
  const {{summary, nodes}} = collectData();
  const payload = {{ summary, nodes, runs, timestamp: "{timestamp}" }};
  const safeCondition = condition.replace(/\\s+/g, '_');
  download(`Beta_${{safeCondition}}_{timestamp}.json`, JSON.stringify(payload, null, 2), "application/json");
}}

// Restore autosaved state on load
restoreState();
</script>
</body>
</html>
"""
    return html


def generate_education_module_html(
    condition: str,
    modules: list = None,
    organization: str = "CarePathIQ"
) -> str:
    """
    Generate standalone interactive education module with certificate.
    
    Args:
        condition: Topic/condition being taught
        modules: List of modules, each with 'title', 'content', 'quiz' (optional)
                If None, generates default module structure
        organization: Organization name
        
    Returns:
        Complete standalone HTML string with embedded education content
    """
    
    if modules is None:
        modules = [
            {
                "title": "Module 1: Clinical Presentation",
                "content": f"<p>This module covers the clinical presentation of {condition}.</p><p>Key features include patient history, vital signs, and initial assessment findings.</p>",
                "quiz": [
                    {
                        "question": f"Which is a key feature of {condition}?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct": 0
                    }
                ]
            },
            {
                "title": "Module 2: Diagnostic Workup",
                "content": f"<p>Learn the recommended diagnostic tests and interpretations for {condition}.</p>",
                "quiz": [
                    {
                        "question": "Which test is most specific?",
                        "options": ["Test A", "Test B", "Test C", "Test D"],
                        "correct": 1
                    }
                ]
            },
            {
                "title": "Module 3: Management Strategy",
                "content": f"<p>Understand the evidence-based management approach for {condition}.</p>",
                "quiz": [
                    {
                        "question": "First-line treatment is:",
                        "options": ["Treatment A", "Treatment B", "Treatment C", "Treatment D"],
                        "correct": 2
                    }
                ]
            }
        ]
    
    modules_json = json.dumps(modules)
    total_sections = len(modules)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Education Module: {condition}</title>
    <style>
        {SHARED_CSS}
        
        .education-nav {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        
        .module-button {{
            padding: 10px 15px;
            border: 2px solid var(--border-gray);
            background: white;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.3s ease;
            font-weight: 600;
        }}
        
        .module-button.active {{
            background-color: var(--teal);
            border-color: var(--teal);
            color: var(--brown-dark);
        }}
        
        .module-button:hover {{
            border-color: var(--teal);
        }}
        
        .module-content {{
            display: none;
            animation: fadeIn 0.3s ease;
        }}
        
        .module-content.active {{
            display: block;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .quiz {{
            background-color: var(--light-gray);
            padding: 20px;
            border-radius: 6px;
            margin-top: 20px;
        }}
        
        .quiz-question {{
            margin-bottom: 15px;
        }}
        
        .quiz-option {{
            display: flex;
            align-items: center;
            margin: 10px 0;
            cursor: pointer;
        }}
        
        .quiz-option input[type="radio"] {{
            width: auto;
            margin-right: 10px;
        }}
        
        .quiz-option label {{
            margin: 0;
            cursor: pointer;
            flex: 1;
        }}
        
        .quiz-feedback {{
            margin-top: 15px;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }}
        
        .quiz-feedback.show {{
            display: block;
        }}
        
        .quiz-feedback.correct {{
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        
        .quiz-feedback.incorrect {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        
        .progress-container {{
            margin: 20px 0;
        }}
        
        .progress-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        .certificate {{
            display: none;
            background: linear-gradient(135deg, var(--teal) 0%, white 100%);
            padding: 40px;
            border: 6px solid var(--brown);
            border-radius: 10px;
            text-align: center;
            margin: 30px 0;
            page-break-after: always;
        }}
        
        .certificate.show {{
            display: block;
        }}
        
        .certificate-content {{
            background: white;
            padding: 40px;
            border: 2px dashed var(--brown);
            border-radius: 6px;
        }}
        
        .certificate-title {{
            font-size: 2em;
            color: var(--brown-dark);
            margin-bottom: 20px;
            font-weight: bold;
        }}
        
        .certificate-text {{
            font-size: 1.1em;
            color: #333;
            margin: 15px 0;
            line-height: 1.6;
        }}
        
        .certificate-condition {{
            font-size: 1.5em;
            color: var(--brown);
            font-weight: bold;
            margin: 20px 0;
        }}
        
        .certificate-date {{
            margin-top: 30px;
            color: #666;
            font-size: 0.95em;
        }}
        
        .certificate-logo {{
            margin: 20px 0;
            color: var(--brown);
            font-weight: bold;
            font-size: 1.3em;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .container {{
                box-shadow: none;
                padding: 0;
            }}
            
            .header {{
                page-break-after: always;
            }}
            
            .education-nav,
            .module-button,
            button:not(.print-hidden),
            .progress-container {{
                display: none;
            }}
        }}
        
        @media (max-width: 768px) {{
            .education-nav {{
                flex-direction: column;
            }}
            
            .module-button {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Education Module</h1>
            <p><strong>{condition}</strong></p>
            <p style="font-size: 0.95em; margin-top: 10px;">Interactive Learning & Certification</p>
        </div>

        <div class="progress-container">
            <div class="progress-label">
                <span>Course Progress</span>
                <span id="progressText">0%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <p id="moduleStatus" style="text-align: center; color: #666; font-size: 0.9em; margin-top: 5px;">
                Completed 0 of {total_sections} modules
            </p>
        </div>

        <div class="education-nav" id="navContainer"></div>

        <div id="contentContainer"></div>

        <div class="certificate" id="certificateSection">
            <div class="certificate-content">
                <div class="certificate-logo">★ CarePathIQ ★</div>
                <div class="certificate-title">Certificate of Completion</div>
                
                <div class="certificate-text">
                    This certifies that
                </div>
                
                <input type="text" id="certificateName" placeholder="Your Name" style="font-size: 1.3em; text-align: center; border: none; border-bottom: 2px solid var(--brown); width: 100%; margin: 15px 0; padding: 10px 0;">
                
                <div class="certificate-text">
                    has successfully completed the
                </div>
                
                <div class="certificate-condition">{condition}</div>
                
                <div class="certificate-text">
                    Education Module offered by
                </div>
                
                <div style="font-weight: bold; color: var(--brown); margin: 15px 0;">{organization}</div>
                
                <div class="certificate-date">
                    <p style="margin: 10px 0;">Date Completed: <strong id="completionDate"></strong></p>
                    <p style="margin: 10px 0;">This certificate is valid as a record of learning completion.</p>
                    <p style="margin-top: 20px; font-size: 0.85em; color: #999;">
                        Certificate ID: <span id="certId"></span>
                    </p>
                </div>
            </div>
        </div>

        <div style="margin-top: 30px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button type="button" onclick="downloadCertificateImage()" id="downloadCertBtn" style="display: none;">Download Certificate (PNG)</button>
            <button type="button" onclick="printCertificate()" id="printCertBtn" style="display: none;">Print Certificate</button>
            <button type="button" onclick="restartCourse()" id="restartBtn" style="display: none;">Restart Course</button>
        </div>

        {CAREPATHIQ_FOOTER}
    </div>

    <script>
        const modules = {modules_json};
        const condition = "{condition}";
        let completedModules = {{}};
        let currentModule = 0;

        document.addEventListener('DOMContentLoaded', function() {{
            renderNav();
            renderModule(0);
            generateCertificateID();
        }});

        function renderNav() {{
            const navContainer = document.getElementById('navContainer');
            modules.forEach((mod, idx) => {{
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'module-button' + (idx === 0 ? ' active' : '');
                btn.textContent = `Module ${{idx + 1}}`;
                btn.onclick = () => switchModule(idx);
                navContainer.appendChild(btn);
            }});
        }}

        function switchModule(idx) {{
            currentModule = idx;
            const buttons = document.querySelectorAll('.module-button');
            buttons.forEach((btn, i) => {{
                btn.classList.toggle('active', i === idx);
            }});
            renderModule(idx);
        }}

        function renderModule(idx) {{
            const mod = modules[idx];
            const container = document.getElementById('contentContainer');
            
            let html = `
                <h2 style="color: var(--brown-dark); margin-top: 30px;">${{mod.title}}</h2>
                <div style="background: white; padding: 20px; margin: 15px 0; border-radius: 6px;">
                    ${{mod.content}}
                </div>
            `;
            
            if (mod.quiz && mod.quiz.length > 0) {{
                html += '<div class="quiz"><h3>Module Quiz</h3>';
                mod.quiz.forEach((q, qIdx) => {{
                    html += `
                        <div class="quiz-question">
                            <p style="font-weight: bold;">${{q.question}}</p>
                    `;
                    q.options.forEach((opt, optIdx) => {{
                        html += `
                            <div class="quiz-option">
                                <input type="radio" id="q${{idx}}_o${{optIdx}}" name="quiz_${{idx}}" value="${{optIdx}}" onchange="checkAnswer(${{idx}}, ${{optIdx}}, ${{q.correct}})">
                                <label for="q${{idx}}_o${{optIdx}}">${{opt}}</label>
                            </div>
                        `;
                    }});
                    html += `
                            <div id="feedback_${{idx}}_${{qIdx}}" class="quiz-feedback"></div>
                        </div>
                    `;
                }});
                html += '</div>';
            }}
            
            html += `
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    ${{idx > 0 ? '<button type="button" onclick="switchModule(' + (idx - 1) + ')">← Previous</button>' : ''}}
                    ${{idx < modules.length - 1 ? '<button type="button" onclick="switchModule(' + (idx + 1) + ')">Next →</button>' : ''}}
                </div>
            `;
            
            container.innerHTML = html;
        }}

        function checkAnswer(modIdx, selectedIdx, correctIdx) {{
            const feedback = document.getElementById(`feedback_${{modIdx}}_0`);
            feedback.classList.add('show');
            
            if (selectedIdx === correctIdx) {{
                feedback.classList.add('correct');
                feedback.classList.remove('incorrect');
                feedback.innerHTML = '<strong>✓ Correct!</strong> Great job.';
                completedModules[modIdx] = true;
            }} else {{
                feedback.classList.add('incorrect');
                feedback.classList.remove('correct');
                feedback.innerHTML = '<strong>✗ Incorrect.</strong> Please try again or review the module.';
            }}
            
            updateProgress();
        }}

        function updateProgress() {{
            const completed = Object.keys(completedModules).length;
            const total = modules.length;
            const percent = Math.round((completed / total) * 100);
            
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressText').textContent = percent + '%';
            document.getElementById('moduleStatus').textContent = `Completed ${{completed}} of ${{total}} modules`;
            
            if (completed === total) {{
                showCertificate();
            }}
        }}

        function showCertificate() {{
            document.getElementById('certificateSection').classList.add('show');
            document.getElementById('downloadCertBtn').style.display = 'inline-block';
            document.getElementById('printCertBtn').style.display = 'inline-block';
            document.getElementById('restartBtn').style.display = 'inline-block';
            document.getElementById('completionDate').textContent = new Date().toLocaleDateString();
        }}

        function generateCertificateID() {{
            const id = 'CPQ-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).substr(2, 9).toUpperCase();
            document.getElementById('certId').textContent = id;
        }}

        function downloadCertificateImage() {{
            const certName = document.getElementById('certificateName').value || 'Learner';
            // Create canvas and convert certificate to image
            const element = document.getElementById('certificateSection');
            
            // Use html2canvas if available, otherwise alert user to use print
            alert('To download as image, please use Print → Save as PDF or use a screenshot tool.\\n\\nAlternatively, click Print Certificate to save as PDF.');
        }}

        function printCertificate() {{
            const certName = document.getElementById('certificateName').value || 'Learner';
            window.print();
        }}

        function restartCourse() {{
            completedModules = {{}};
            currentModule = 0;
            updateProgress();
            switchModule(0);
            document.getElementById('certificateSection').classList.remove('show');
            document.getElementById('downloadCertBtn').style.display = 'none';
            document.getElementById('printCertBtn').style.display = 'none';
            document.getElementById('restartBtn').style.display = 'none';
            window.scrollTo(0, 0);
        }}
    </script>
</body>
</html>"""
    
    return html


# ==========================================
# HELPER FOR EXECUTIVE SUMMARY (using python-docx)
# ==========================================

def create_phase5_executive_summary_docx(data: dict, condition: str):
    """
    Create a Word document executive summary for Phase 5.
    Requires python-docx to be installed.
    
    Args:
        data: Session data with phase1, phase2, phase3 info
        condition: Clinical condition name
        
    Returns:
        BytesIO buffer with .docx content, or None if python-docx unavailable
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Title
        title = doc.add_heading(f"Executive Summary: {condition}", 0)
        title_format = title.paragraph_format
        title_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Overview
        doc.add_heading("Clinical Pathway Overview", level=1)
        p1_data = data.get('phase1', {})
        doc.add_paragraph(f"Condition: {p1_data.get('condition', 'N/A')}")
        doc.add_paragraph(f"Setting: {p1_data.get('setting', 'N/A')}")
        doc.add_paragraph(f"Target Population: {p1_data.get('population', 'N/A')}")
        
        # Problem Statement
        doc.add_heading("Problem Statement", level=1)
        doc.add_paragraph(p1_data.get('problem', 'Not provided'))
        
        # Goals
        doc.add_heading("Project Goals", level=1)
        doc.add_paragraph(p1_data.get('objectives', 'Not provided'))
        
        # Evidence Summary
        doc.add_heading("Evidence Summary", level=1)
        p2_data = data.get('phase2', {})
        evidence = p2_data.get('evidence', [])
        if evidence:
            doc.add_paragraph(f"Total evidence items reviewed: {len(evidence)}")
            
            # Grade breakdown
            grades = {}
            for e in evidence:
                grade = e.get('grade', 'Un-graded')
                grades[grade] = grades.get(grade, 0) + 1
            
            doc.add_paragraph("Evidence Quality Distribution:", style='List Bullet')
            for grade, count in sorted(grades.items()):
                doc.add_paragraph(f"{grade}: {count} articles", style='List Bullet 2')
        else:
            doc.add_paragraph("No evidence reviewed yet")
        
        # Pathway Overview
        doc.add_heading("Pathway Design", level=1)
        p3_data = data.get('phase3', {})
        nodes = p3_data.get('nodes', [])
        
        if nodes:
            doc.add_paragraph(f"Total pathway nodes: {len(nodes)}")
            
            node_types = {}
            for node in nodes:
                node_type = node.get('type', 'Process')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            doc.add_paragraph("Pathway Node Distribution:", style='List Bullet')
            for node_type, count in sorted(node_types.items()):
                doc.add_paragraph(f"{node_type}: {count}", style='List Bullet 2')
            
            # Add node list
            doc.add_heading("Pathway Nodes", level=2)
            table = doc.add_table(rows=1, cols=3)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'ID'
            hdr_cells[1].text = 'Node'
            hdr_cells[2].text = 'Type'
            
            for idx, node in enumerate(nodes):
                row_cells = table.add_row().cells
                row_cells[0].text = f"N{idx + 1}"
                row_cells[1].text = node.get('label', 'N/A')
                row_cells[2].text = node.get('type', 'N/A')
        else:
            doc.add_paragraph("Pathway not yet designed")
        
        # Usability Assessment
        doc.add_heading("Usability Assessment", level=1)
        p4_data = data.get('phase4', {})
        heuristics = p4_data.get('heuristics_data', {})
        
        if heuristics:
            doc.add_paragraph("Nielsen Heuristics Review Completed", style='List Bullet')
            doc.add_paragraph(f"Total heuristics evaluated: {len(heuristics)}", style='List Bullet 2')
        else:
            doc.add_paragraph("Usability assessment pending")
        
        # Implementation Next Steps
        doc.add_heading("Implementation Next Steps", level=1)
        doc.add_paragraph("1. Expert Panel Review: Share pathway with clinical experts for feedback", style='List Number')
        doc.add_paragraph("2. Beta Testing: Conduct real-world testing with target users", style='List Number')
        doc.add_paragraph("3. Education Deployment: Provide training module to clinical team", style='List Number')
        doc.add_paragraph("4. Go-Live: Implement pathway in clinical setting with monitoring", style='List Number')
        doc.add_paragraph("5. Continuous Improvement: Monitor compliance and outcomes", style='List Number')
        
        # Footer
        section = doc.sections[0]
        footer = section.footer
        footer_paragraph = footer.paragraphs[0]
        footer_paragraph.text = f"CarePathIQ Executive Summary | {condition} | Generated {datetime.now().strftime('%Y-%m-%d')}"
        footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
        
    except ImportError:
        return None


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def ensure_carepathiq_branding(html: str) -> str:
    """Ensure HTML has CarePathIQ branding and footer."""
    if CAREPATHIQ_FOOTER not in html:
        if "</body>" in html:
            html = html.replace("</body>", CAREPATHIQ_FOOTER + "</body>")
        else:
            html += CAREPATHIQ_FOOTER
    return html
