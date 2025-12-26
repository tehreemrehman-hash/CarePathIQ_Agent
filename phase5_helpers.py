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
    organization: str = "CarePathIQ",
    pathway_svg_b64: str = None
) -> str:
    """
    Generate standalone expert panel feedback form with CSV download capability.
    
    Args:
        condition: Clinical condition being reviewed
        nodes: List of pathway nodes (dicts with 'type', 'label', 'evidence')
        audience: Target audience description
        organization: Organization name
        pathway_svg_b64: Base64-encoded SVG of pathway visualization (optional)
        
    Returns:
        Complete standalone HTML string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nodes_json = json.dumps(nodes)
    
    # Prepare pathway view button if SVG is provided
    pathway_button_html = ""
    pathway_script = ""
    if pathway_svg_b64:
        pathway_button_html = '<button type="button" onclick="openPathway()" style="background:#5D4037;color:white;padding:12px 24px;border:none;border-radius:4px;cursor:pointer;font-size:1em;margin:15px 0">📊 View Pathway Visualization</button>'
        pathway_script = f'''
        <script>
        function openPathway() {{
            var w = window.open('', '_blank', 'width=1200,height=900,resizable=yes,scrollbars=yes');
            if (w) {{
                w.document.write('<html><head><title>Pathway Visualization</title>');
                w.document.write('<style>body{{margin:0;padding:20px;background:#e8f5e9;text-align:center;}}img{{max-width:100%;height:auto;display:block;margin:20px auto;border:2px solid #5D4037;border-radius:8px;}}</style>');
                w.document.write('</head><body>');
                w.document.write('<h2 style="color:#5D4037;">Clinical Pathway Visualization</h2>');
                w.document.write('<p style="color:#666;">Reference this visualization while providing feedback</p>');
                w.document.write('<img src="data:image/svg+xml;base64,{pathway_svg_b64}" alt="Pathway" />');
                w.document.write('</body></html>');
                w.document.close();
            }} else {{
                alert('Popup blocked. Please allow popups to view the pathway.');
            }}
        }}
        </script>
        '''
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expert Panel Feedback: {condition}</title>
    <style>
        {SHARED_CSS}
        .info-grid {{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px}}
        @media (max-width: 768px) {{
            .info-grid {{grid-template-columns:1fr}}
        }}
        .compact-node {{border:1px solid var(--border-gray);border-radius:6px;padding:15px;margin-bottom:15px;background:#fafafa}}
        .compact-node h4 {{margin:0 0 8px 0;color:var(--brown-dark);font-size:1em}}
        .compact-node .node-meta {{font-size:0.85em;color:#666;margin-bottom:10px}}
        .feedback-section {{display:none;margin-top:12px;padding-top:12px;border-top:1px solid var(--border-gray)}}
        .feedback-section.show {{display:block}}
        .feedback-section textarea {{min-height:70px}}
        .feedback-section select {{margin-bottom:10px}}
    </style>
    {pathway_script}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Expert Panel Review & Feedback</h1>
            <p style="font-size: 1.1em; color: var(--brown-dark); margin-bottom: 12px;"><strong>{condition}</strong> Clinical Decision Pathway</p>
            <p style="font-size: 0.95em; color: #666; margin-top: 8px; line-height: 1.6;">We appreciate your expert evaluation of this evidence-based clinical pathway. Your feedback on clinical accuracy, feasibility, and alignment with current best practices is essential to pathway refinement. Please review the pathway nodes below and provide specific recommendations where appropriate.</p>
            {pathway_button_html}
        </div>

        <form id="feedbackForm">
            <div class="info-grid">
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
                    <input type="text" id="reviewer_role" name="reviewer_role" placeholder="e.g., EM Physician">
                </div>
            </div>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid var(--border-gray);">

            <h2 style="color: var(--brown-dark); margin: 25px 0 15px 0;">Pathway Nodes</h2>
            <p style="margin-bottom: 15px; color: #666; font-size:0.95em;">Check nodes that need feedback. Only those will be included in the download.</p>

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
                <button type="button" onclick="downloadAsCSV()">Download Feedback (CSV)</button>
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
                const evidence = node.evidence && node.evidence !== 'N/A' ? `PMID ${{node.evidence}}` : 'No evidence';
                const nodeHTML = `
                    <div class="compact-node">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <h4><span class="node-badge">N${{idx + 1}}</span> ${{node.label || 'Step'}}</h4>
                            <label style="margin:0;cursor:pointer;font-weight:normal">
                                <input type="checkbox" id="feedback_check_${{idx}}" onchange="toggleExpansion(${{idx}})" style="width:auto;margin-right:6px">
                                Provide Feedback
                            </label>
                        </div>
                        <div class="node-meta">Type: ${{node.type || 'Process'}} | Evidence: ${{evidence}}</div>

                        <div id="expansion_${{idx}}" class="feedback-section">
                            <label for="feedback_${{idx}}" style="font-size:0.9em"><strong>Change/Concern *</strong></label>
                            <textarea name="feedback_${{idx}}" id="feedback_${{idx}}" placeholder="Describe issue or suggested improvement..." required></textarea>
                            
                            <label for="source_${{idx}}" style="font-size:0.9em;margin-top:10px"><strong>Source *</strong></label>
                            <select name="source_${{idx}}" id="source_${{idx}}" required>
                                <option value="">-- Select Justification Source --</option>
                                <option value="Peer-Reviewed Literature">Peer-Reviewed Literature</option>
                                <option value="National Guideline">National Guideline (ACLS, AHA, etc.)</option>
                                <option value="Institutional Policy">Institutional Policy</option>
                                <option value="Patient Safety Concern">Patient Safety Concern</option>
                                <option value="Feasibility Issue">Feasibility Issue</option>
                                <option value="Other">Other</option>
                            </select>
                            
                            <label for="details_${{idx}}" style="font-size:0.9em;margin-top:10px"><strong>Details/Citation</strong></label>
                            <textarea name="details_${{idx}}" id="details_${{idx}}" placeholder="Reference, PMID, guideline, or rationale..." style="min-height:60px"></textarea>
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
    organization: str = "CarePathIQ",
    pathway_svg_b64: str = None
) -> str:
    """
    Generate simplified beta testing form focused on:
    - 3 scenario-based end-to-end pathway tests
    - Nielsen's 10 heuristics evaluation
    - Overall usability feedback
    - CSV export of results
    
    Args:
        condition: Clinical condition being tested
        nodes: List of pathway nodes (for reference)
        audience: Target audience description
        organization: Organization name
        pathway_svg_b64: Base64-encoded SVG of pathway visualization (optional)
        
    Returns:
        Complete standalone HTML string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nodes_json = json.dumps(nodes or [])
    
    # Prepare pathway view button if SVG is provided
    pathway_button_html = ""
    pathway_script = ""
    if pathway_svg_b64:
        pathway_button_html = '<button type="button" onclick="openPathway()" style="background:#5D4037;color:white;padding:12px 24px;border:none;border-radius:4px;cursor:pointer;font-size:1em;margin:15px 0">📊 View Pathway Visualization</button>'
        pathway_script = f'''
<script>
function openPathway() {{
    var w = window.open('', '_blank', 'width=1200,height=900,resizable=yes,scrollbars=yes');
    if (w) {{
        w.document.write('<html><head><title>Pathway Visualization</title>');
        w.document.write('<style>body{{margin:0;padding:20px;background:#e8f5e9;text-align:center;}}img{{max-width:100%;height:auto;display:block;margin:20px auto;border:2px solid #5D4037;border-radius:8px;}}</style>');
        w.document.write('</head><body>');
        w.document.write('<h2 style="color:#5D4037;">Clinical Pathway Visualization</h2>');
        w.document.write('<p style="color:#666;">Use this pathway for testing scenarios</p>');
        w.document.write('<img src="data:image/svg+xml;base64,{pathway_svg_b64}" alt="Pathway" />');
        w.document.write('</body></html>');
        w.document.close();
    }} else {{
        alert('Popup blocked. Please allow popups to view the pathway.');
    }}
}}
</script>
'''
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{condition} — Beta Testing</title>
<style>
{SHARED_CSS}
{pathway_script}
.scenario-card {{background:#fff;border:2px solid var(--border-gray);border-radius:8px;padding:20px;margin-bottom:20px}}
.scenario-card h3 {{color:var(--brown-dark);margin:0 0 10px 0}}
.scenario-card p {{margin:8px 0;color:#555}}
.scenario-card .tasks {{margin:12px 0;padding-left:20px}}
.scenario-card .tasks li {{margin:6px 0}}
.checklist {{margin-top:12px}}
.checklist label {{display:flex;align-items:center;margin:8px 0;cursor:pointer}}
.checklist input[type="checkbox"] {{width:20px;height:20px;margin-right:10px;cursor:pointer}}
.scenario-card textarea {{width:100%;min-height:80px;margin-top:8px;padding:10px;border:1px solid var(--border-gray);border-radius:4px;resize:vertical}}
table {{width:100%;border-collapse:collapse;margin:15px 0}}
th,td {{border:1px solid var(--border-gray);padding:12px;text-align:left}}
th {{background:#f8f9fa;font-weight:600;color:var(--brown-dark)}}
select,input[type="text"],input[type="email"],textarea {{width:100%;padding:10px;border:1px solid var(--border-gray);border-radius:4px}}
textarea {{min-height:70px;resize:vertical}}
label {{display:block;margin-bottom:6px;font-weight:500;color:var(--brown-dark)}}
.form-row {{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
.rating-scale {{display:flex;gap:8px;align-items:center}}
.rating-scale input[type="radio"] {{width:auto;margin:0}}
.rating-scale label {{margin:0;font-weight:normal;cursor:pointer}}
.heuristic-row {{border-bottom:1px solid var(--border-gray);padding:16px 0}}
.heuristic-row:last-child {{border-bottom:none}}
.heuristic-title {{font-weight:600;color:var(--brown-dark);margin-bottom:8px}}
.heuristic-desc {{font-size:0.9em;color:#666;margin-bottom:12px}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>{condition} — Beta Testing Form</h1>
<p style="margin-top:8px">Test the clinical pathway end-to-end using 3 scenarios and evaluate usability</p>
<p style="font-size:0.9em;margin-top:5px">Target Audience: {audience} | {organization}</p>
{pathway_button_html}
</div>

<form id="betaForm">
<!-- Tester Info -->
<div class="form-group">
<label for="tester_name">Your Name *</label>
<input type="text" id="tester_name" required placeholder="Full name">
</div>
<div class="form-row">
<div class="form-group">
<label for="tester_email">Email *</label>
<input type="email" id="tester_email" required placeholder="email@example.com">
</div>
<div class="form-group">
<label for="tester_role">Role *</label>
<input type="text" id="tester_role" required placeholder="e.g., RN, Physician, APP">
</div>
</div>

<hr style="margin:30px 0;border:none;border-top:2px solid var(--border-gray)">

<!-- Clinical Scenarios -->
<h2 style="color:var(--brown-dark);margin-bottom:20px">Clinical Scenarios — End-to-End Testing</h2>
<p style="margin-bottom:20px;color:#555">Complete each scenario using the pathway. Check off tasks as you go and note any issues.</p>

<div class="scenario-card">
<h3>Scenario 1: Typical Stable Outpatient</h3>
<p><strong>Description:</strong> A stable patient with straightforward presentation. Test the standard pathway flow.</p>
<ul class="tasks">
<li>Initial assessment and triage</li>
<li>Diagnostic workup for typical presentation</li>
<li>Standard treatment recommendations</li>
<li>Follow-up and patient education</li>
</ul>
<div class="checklist">
<strong>Did the pathway work smoothly?</strong>
<label><input type="checkbox" class="scenario-check" data-scenario="typical"> ✓ Successfully completed from start to end</label>
</div>
<label style="margin-top:10px">Issues or observations (if any):</label>
<textarea id="scenario1_notes" placeholder="Note any breaks, unclear steps, or confusing decisions..."></textarea>
</div>

<div class="scenario-card">
<h3>Scenario 2: Complex Patient with Comorbidities</h3>
<p><strong>Description:</strong> A patient with multiple chronic conditions. Test pathway flexibility and decision branching.</p>
<ul class="tasks">
<li>Navigate branching decisions for comorbid conditions</li>
<li>Adjust diagnostic approach based on complexity</li>
<li>Select appropriate multi-faceted treatment plan</li>
<li>Address conflicting recommendations or contraindications</li>
</ul>
<div class="checklist">
<strong>Did the pathway work smoothly?</strong>
<label><input type="checkbox" class="scenario-check" data-scenario="complex"> ✓ Successfully completed from start to end</label>
</div>
<label style="margin-top:10px">Issues or observations (if any):</label>
<textarea id="scenario2_notes" placeholder="Note any breaks, unclear steps, or confusing decisions..."></textarea>
</div>

<div class="scenario-card">
<h3>Scenario 3: Urgent Acute Presentation</h3>
<p><strong>Description:</strong> An urgent case requiring rapid triage and intervention. Test critical pathway efficiency.</p>
<ul class="tasks">
<li>Rapid triage and risk stratification</li>
<li>Prioritize time-sensitive diagnostic tests</li>
<li>Execute urgent treatment protocols</li>
<li>Confirm safety checks and escalation criteria</li>
</ul>
<div class="checklist">
<strong>Did the pathway work smoothly?</strong>
<label><input type="checkbox" class="scenario-check" data-scenario="urgent"> ✓ Successfully completed from start to end</label>
</div>
<label style="margin-top:10px">Issues or observations (if any):</label>
<textarea id="scenario3_notes" placeholder="Note any breaks, unclear steps, or confusing decisions..."></textarea>
</div>

<hr style="margin:30px 0;border:none;border-top:2px solid var(--border-gray)">

<!-- Nielsen Heuristics -->
<h2 style="color:var(--brown-dark);margin-bottom:20px">Nielsen's Usability Heuristics</h2>
<p style="margin-bottom:20px;color:#555">Rate each heuristic from 1 (Poor) to 5 (Excellent) and provide comments.</p>

<div id="heuristicsContainer"></div>

<hr style="margin:30px 0;border:none;border-top:2px solid var(--border-gray)">

<!-- Overall Feedback -->
<h2 style="color:var(--brown-dark);margin-bottom:20px">Overall Feedback</h2>
<div class="form-row">
<div class="form-group">
<label for="overall_rating">Overall Pathway Quality (1–5)</label>
<select id="overall_rating">
<option value="1">1 - Poor</option>
<option value="2">2 - Fair</option>
<option value="3" selected>3 - Good</option>
<option value="4">4 - Very Good</option>
<option value="5">5 - Excellent</option>
</select>
</div>
<div class="form-group">
<label for="workflow_fit">Fits Clinical Workflow (1–5)</label>
<select id="workflow_fit">
<option value="1">1 - Poor Fit</option>
<option value="2">2 - Fair Fit</option>
<option value="3" selected>3 - Good Fit</option>
<option value="4">4 - Very Good Fit</option>
<option value="5">5 - Excellent Fit</option>
</select>
</div>
</div>

<div class="form-group">
<label for="strengths">What worked well? (Strengths)</label>
<textarea id="strengths" placeholder="Describe positive aspects, helpful features, clear sections..."></textarea>
</div>

<div class="form-group">
<label for="improvements">What needs improvement? (Issues & Suggestions)</label>
<textarea id="improvements" placeholder="Describe problems encountered, confusing areas, missing features..."></textarea>
</div>

<div class="button-group" style="margin-top:30px">
<button type="button" onclick="downloadCSV()" style="background:var(--brown);color:white;font-size:1.05em;padding:14px 28px">Download Feedback CSV</button>
<button type="reset" style="background:#999;color:white">Reset Form</button>
</div>
</form>

{CAREPATHIQ_FOOTER}
</div>

<script>
const HEURISTICS = [
  {{id: "h1", name: "Visibility of System Status", desc: "Does the pathway clearly show where you are and what's happening?"}},
  {{id: "h2", name: "Match Between System and Real World", desc: "Does it use familiar clinical language and concepts?"}},
  {{id: "h3", name: "User Control and Freedom", desc: "Can you easily undo mistakes or go back to previous steps?"}},
  {{id: "h4", name: "Consistency and Standards", desc: "Are terms, layouts, and actions consistent throughout?"}},
  {{id: "h5", name: "Error Prevention", desc: "Does it prevent errors before they happen (not just detect)?"}},
  {{id: "h6", name: "Recognition Rather Than Recall", desc: "Are options visible rather than requiring memorization?"}},
  {{id: "h7", name: "Flexibility and Efficiency", desc: "Does it accommodate both novice and expert users?"}},
  {{id: "h8", name: "Aesthetic and Minimalist Design", desc: "Is the interface clean without unnecessary information?"}},
  {{id: "h9", name: "Help Users Recognize and Recover from Errors", desc: "Are error messages clear with suggested solutions?"}},
  {{id: "h10", name: "Help and Documentation", desc: "Is help available when needed and easy to understand?"}}
];

const condition = "{condition}";
const nodes = {nodes_json};

// Initialize heuristics form
function initializeHeuristics() {{
  const container = document.getElementById('heuristicsContainer');
  HEURISTICS.forEach(h => {{
    const div = document.createElement('div');
    div.className = 'heuristic-row';
    div.innerHTML = `
      <div class="heuristic-title">${{h.name}}</div>
      <div class="heuristic-desc">${{h.desc}}</div>
      <div style="margin-bottom:10px">
        <strong>Rating:</strong>
        <div class="rating-scale" style="margin-top:8px">
          <label><input type="radio" name="${{h.id}}_rating" value="1" required> 1</label>
          <label><input type="radio" name="${{h.id}}_rating" value="2"> 2</label>
          <label><input type="radio" name="${{h.id}}_rating" value="3" checked> 3</label>
          <label><input type="radio" name="${{h.id}}_rating" value="4"> 4</label>
          <label><input type="radio" name="${{h.id}}_rating" value="5"> 5</label>
        </div>
      </div>
      <div>
        <label for="${{h.id}}_comments"><strong>Comments:</strong></label>
        <textarea id="${{h.id}}_comments" placeholder="Explain your rating, specific examples..." style="min-height:60px"></textarea>
      </div>
    `;
    container.appendChild(div);
  }});
}}

// Download CSV
function downloadCSV() {{
  const name = document.getElementById('tester_name').value;
  const email = document.getElementById('tester_email').value;
  const role = document.getElementById('tester_role').value;
  
  if (!name || !email || !role) {{
    alert('Please fill in your name, email, and role before downloading.');
    return;
  }}
  
  let csv = 'Category,Item,Value\\n';
  csv += `Tester Name,${{name}},"${{name}}"\\n`;
  csv += `Tester Email,${{email}},"${{email}}"\\n`;
  csv += `Tester Role,${{role}},"${{role}}"\\n`;
  csv += `Condition,"{condition}","{condition}"\\n`;
  csv += `Test Date,"${{new Date().toLocaleDateString()}}","${{new Date().toISOString()}}"\\n`;
  csv += '\\n';
  
  // Scenarios
  csv += 'Scenario Testing,Item,Notes\\n';
  const s1Check = document.querySelector('input[data-scenario="typical"]').checked ? 'Completed' : 'Not Completed';
  const s1Notes = document.getElementById('scenario1_notes').value.replace(/"/g, '""');
  csv += `Scenario 1 - Typical,${{s1Check}},"${{s1Notes}}"\\n`;
  
  const s2Check = document.querySelector('input[data-scenario="complex"]').checked ? 'Completed' : 'Not Completed';
  const s2Notes = document.getElementById('scenario2_notes').value.replace(/"/g, '""');
  csv += `Scenario 2 - Complex,${{s2Check}},"${{s2Notes}}"\\n`;
  
  const s3Check = document.querySelector('input[data-scenario="urgent"]').checked ? 'Completed' : 'Not Completed';
  const s3Notes = document.getElementById('scenario3_notes').value.replace(/"/g, '""');
  csv += `Scenario 3 - Urgent,${{s3Check}},"${{s3Notes}}"\\n`;
  csv += '\\n';
  
  // Heuristics
  csv += 'Nielsen Heuristic,Rating,Comments\\n';
  HEURISTICS.forEach(h => {{
    const rating = document.querySelector(`input[name="${{h.id}}_rating"]:checked`).value;
    const comments = document.getElementById(`${{h.id}}_comments`).value.replace(/"/g, '""');
    csv += `"${{h.name}}",${{rating}},"${{comments}}"\\n`;
  }});
  csv += '\\n';
  
  // Overall
  csv += 'Overall Feedback,Rating,Comments\\n';
  const overall = document.getElementById('overall_rating').value;
  const workflow = document.getElementById('workflow_fit').value;
  const strengths = document.getElementById('strengths').value.replace(/"/g, '""');
  const improvements = document.getElementById('improvements').value.replace(/"/g, '""');
  csv += `Overall Quality,${{overall}},"N/A"\\n`;
  csv += `Workflow Fit,${{workflow}},"N/A"\\n`;
  csv += `Strengths,"N/A","${{strengths}}"\\n`;
  csv += `Improvements Needed,"N/A","${{improvements}}"\\n`;
  
  const blob = new Blob([csv], {{ type: 'text/csv' }});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `BetaTesting_${{condition.replace(/\s+/g, '_')}}_${{name.replace(/\s+/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  
  alert('Beta testing feedback downloaded successfully!');
}}

// Initialize on load
initializeHeuristics();
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
