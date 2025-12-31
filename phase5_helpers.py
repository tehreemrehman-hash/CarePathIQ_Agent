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
# LLM AUDIENCE INFERENCE
# ==========================================

def infer_audience_from_description(audience_text: str, genai_client=None):
    """
    Use LLM to infer audience focus areas from free-text target audience input.
    
    Args:
        audience_text: Free-text description of target audience (e.g., "Hospital Leadership, CFO, Board Members")
        genai_client: Optional Google Generative AI client. If None, creates a new one.
    
    Returns:
        dict: Structured metadata with:
            - audience_type: str (e.g., "executive", "clinical_leadership", "implementation_team", "clinical_staff")
            - strategic_focus: bool (True for C-suite/executive focus)
            - operational_focus: bool (True for implementation/clinical staff focus)
            - clinical_focus: bool (True for clinician/clinical staff focus)
            - detail_level: str ("summary" for executives, "moderate" for leadership, "detailed" for implementation)
            - emphasis_areas: list of strings (e.g., ["ROI", "risk_mitigation", "patient_safety"])
            - tone: str ("executive_brief" or "technical_detailed")
    """
    import os
    
    if not audience_text or not audience_text.strip():
        # Default to implementation team if empty
        return {
            "audience_type": "implementation_team",
            "strategic_focus": False,
            "operational_focus": True,
            "clinical_focus": True,
            "detail_level": "detailed",
            "emphasis_areas": ["workflow", "safety", "efficiency", "implementation"],
            "tone": "technical_detailed"
        }
    
    try:
        # Create client if not provided
        if genai_client is None:
            from google import genai
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            genai_client = genai.Client(api_key=api_key)
        
        # LLM prompt for audience inference
        inference_prompt = f"""Analyze this target audience description and provide a JSON response with the following structure:
{{
  "audience_type": "one of: executive, clinical_leadership, implementation_team, clinical_staff, or other",
  "strategic_focus": true/false (true if audience is C-suite/board/executive leadership),
  "operational_focus": true/false (true if audience manages operations/implementation),
  "clinical_focus": true/false (true if audience is clinical staff/practitioners),
  "detail_level": "summary" for executives (1-2 page overview), "moderate" for leadership, or "detailed" for implementation/clinical,
  "emphasis_areas": list of 3-5 areas to emphasize (e.g., ["ROI", "patient_safety", "efficiency", "compliance"] for executives; ["workflow", "safety", "implementation", "training"] for clinical staff),
  "tone": "executive_brief" (formal, high-level) or "technical_detailed" (operational, step-by-step)
}}

Target Audience: {audience_text}

Respond ONLY with valid JSON, no other text."""
        
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=inference_prompt
        )
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Try to extract JSON from response (in case LLM adds extra text)
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        result = json.loads(response_text)
        
        # Validate response structure
        required_fields = ["audience_type", "strategic_focus", "operational_focus", "clinical_focus", 
                          "detail_level", "emphasis_areas", "tone"]
        if all(field in result for field in required_fields):
            return result
        else:
            raise ValueError("Missing required fields in LLM response")
    
    except Exception as e:
        # Fallback to default inference if LLM fails
        audience_lower = audience_text.lower()
        
        # Simple keyword-based fallback
        if any(word in audience_lower for word in ["board", "executive", "ceo", "cfo", "leadership", "hospital", "administration"]):
            return {
                "audience_type": "executive",
                "strategic_focus": True,
                "operational_focus": False,
                "clinical_focus": False,
                "detail_level": "summary",
                "emphasis_areas": ["ROI", "risk_mitigation", "compliance", "strategic_alignment"],
                "tone": "executive_brief"
            }
        elif any(word in audience_lower for word in ["clinical leader", "physician", "director", "quality", "safety"]):
            return {
                "audience_type": "clinical_leadership",
                "strategic_focus": False,
                "operational_focus": True,
                "clinical_focus": True,
                "detail_level": "moderate",
                "emphasis_areas": ["patient_safety", "efficiency", "quality", "outcomes"],
                "tone": "technical_detailed"
            }
        elif any(word in audience_lower for word in ["staff", "nurse", "rn", "clinician", "practitioner", "team", "ed"]):
            return {
                "audience_type": "clinical_staff",
                "strategic_focus": False,
                "operational_focus": True,
                "clinical_focus": True,
                "detail_level": "detailed",
                "emphasis_areas": ["workflow", "safety", "efficiency", "implementation"],
                "tone": "technical_detailed"
            }
        else:
            return {
                "audience_type": "implementation_team",
                "strategic_focus": False,
                "operational_focus": True,
                "clinical_focus": False,
                "detail_level": "detailed",
                "emphasis_areas": ["workflow", "deployment", "timeline", "resources"],
                "tone": "technical_detailed"
            }


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
    care_setting: str = "",
    pathway_svg_b64: str = None,
    genai_client=None
) -> str:
    """
    Generate standalone expert panel feedback form with CSV download capability.
    Content and structure adapt based on LLM inference of target audience focus areas.
    
    Args:
        condition: Clinical condition being reviewed
        nodes: List of pathway nodes (dicts with 'type', 'label', 'evidence')
        audience: Target audience description (free-text) for LLM-based inference
        organization: Organization name
        care_setting: Care setting/environment (e.g., "Emergency Department")
        genai_client: Optional Google Generative AI client for audience inference
        
    Returns:
        Complete standalone HTML string with audience-adapted content
    """
    # Infer audience focus to tailor form structure and questions
    audience_metadata = infer_audience_from_description(audience, genai_client)
    detail_level = audience_metadata.get('detail_level', 'moderate')
    emphasis_areas = audience_metadata.get('emphasis_areas', [])
    emphasis_text = ", ".join(emphasis_areas) if emphasis_areas else ""
    emphasis_text = ", ".join(emphasis_areas) if emphasis_areas else ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nodes_json = json.dumps(nodes)
    condition_clean = (condition or "Pathway").strip()
    care_setting_clean = (care_setting or "").strip()
    if care_setting_clean:
        pathway_title = f"Pathway: Managing {condition_clean} in {care_setting_clean}"
        page_title = f"Expert Panel Feedback: {condition_clean} ({care_setting_clean})"
    else:
        pathway_title = f"Pathway: Managing {condition_clean}"
        page_title = f"Expert Panel Feedback: {condition_clean}"
    
    # Pathway visualization removed
    pathway_button_html = ""
    pathway_script = ""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
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
            <h1>Expert Panel Feedback</h1>
            <p style="font-size: 1.05em; color: var(--brown-dark); margin-bottom: 8px; line-height: 1.6;">{pathway_title}</p>
            <p style="font-size:0.9em;margin-top:5px;color:#666;">Target Audience: {audience} | {organization}</p>
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
                <button type="button" onclick="downloadAsCSV()" style="background:var(--brown);color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:1em;">Download Responses (CSV)</button>
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
                            <label style="margin:0;cursor:pointer;font-weight:normal;display:flex;align-items:center;white-space:nowrap">
                                <input type="checkbox" id="feedback_check_${{idx}}" onchange="toggleExpansion(${{idx}})" style="width:auto;margin-right:6px;margin-top:0">
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
    care_setting: str = "",
    genai_client=None
) -> str:
    """
    Generate simplified beta testing form focused on:
    - 3 scenario-based end-to-end pathway tests
    - Nielsen's 10 heuristics evaluation
    - Overall usability feedback
    - CSV export of results
    Content and structure adapt based on LLM inference of target audience focus areas.
    
    Args:
        condition: Clinical condition being tested
        nodes: List of pathway nodes (for reference)
        audience: Target audience description (free-text) for LLM-based inference
        organization: Organization name
        care_setting: Care setting/environment (e.g., "Emergency Department")
        genai_client: Optional Google Generative AI client for audience inference
        
    Returns:
        Complete standalone HTML string with audience-adapted content
    """
    # Infer audience focus to tailor form structure and scenarios
    audience_metadata = infer_audience_from_description(audience, genai_client)
    detail_level = audience_metadata.get('detail_level', 'moderate')
    emphasis_areas = audience_metadata.get('emphasis_areas', [])
    emphasis_text = ", ".join(emphasis_areas) if emphasis_areas else ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nodes_json = json.dumps(nodes or [])
    condition_clean = (condition or "Pathway").strip()
    care_setting_clean = (care_setting or "").strip()
    if care_setting_clean:
        pathway_title = f"Pathway: Managing {condition_clean} in {care_setting_clean}"
        page_title = f"Beta Testing Guide: {condition_clean} ({care_setting_clean})"
    else:
        pathway_title = f"Pathway: Managing {condition_clean}"
        page_title = f"Beta Testing Guide: {condition_clean}"
    
    # Pathway visualization removed
    pathway_button_html = ""
    pathway_script = ""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<style>
{SHARED_CSS}
.info-grid {{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px}}
@media (max-width: 768px) {{
    .info-grid {{grid-template-columns:1fr}}
}}
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
.heuristics-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:12px}}
.heuristic-card {{border:1px solid var(--border-gray);border-radius:8px;padding:12px;background:#fff;display:flex;flex-direction:column;gap:8px}}
.heuristic-head {{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.heuristic-title {{font-weight:600;color:var(--brown-dark);font-size:0.95em;line-height:1.3}}
.heuristic-info {{width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;border:1px solid var(--border-gray);color:#555;font-size:0.8em;cursor:help;position:relative}}
.heuristic-info:hover::after {{content:attr(data-desc);position:absolute;top:28px;left:50%;transform:translateX(-50%);background:#fff;border:1px solid #ccc;padding:8px 10px;border-radius:6px;color:#333;white-space:normal;max-width:280px;box-shadow:0 2px 8px rgba(0,0,0,0.1);z-index:10;font-size:0.85em;line-height:1.4;font-weight:normal}}
.likert {{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:0.9em;color:#444}}
.likert label {{margin:0;display:inline-flex;align-items:center;gap:4px;font-weight:500;color:#444}}
.heuristic-card textarea {{min-height:50px;font-size:0.9em}}
</style>
{pathway_script}
</head>
<body>
<div class="container">
<div class="header">
<h1>Beta Testing Guide</h1>
<p style="margin-top:8px;font-size:1.1em">{pathway_title}</p>
<p style="font-size:0.9em;margin-top:5px">Target Audience: {audience} | {organization}</p>
{pathway_button_html}
</div>

<form id="betaForm">
<!-- Tester Info -->
<div class="info-grid">
<div class="form-group">
<label for="tester_name">Your Name *</label>
<input type="text" id="tester_name" required placeholder="Full name">
</div>
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
<p style="margin-bottom:20px;color:#555">Use the data provided to follow the pathway to the correct terminal node (diagnosis → treatment → disposition).</p>

<div class="scenario-card">
<h3>Scenario 1: Low-Risk Discharge</h3>
<p><strong>Vignette:</strong> 45M, 2h pleuritic chest pain after URI, reproducible on palpation, normal ECG, hs-trop <99th at 0/1h, HEAR 1.</p>
<ul class="tasks">
<li>Apply pathway criteria for low-risk chest pain</li>
<li>Choose appropriate workup and confirm no escalation needed</li>
<li>Select correct disposition: discharge with NSAID + PCP follow-up</li>
</ul>
<div class="checklist">
<strong>Did the pathway land on the correct end-node?</strong>
<label><input type="checkbox" class="scenario-check" data-scenario="lowrisk"> ✓ Reached the intended discharge branch</label>
</div>
<label style="margin-top:10px">Notes (breaks, wrong branch, missing step):</label>
<textarea id="scenario1_notes" placeholder="Describe any mismatch between vignette and end-node..."></textarea>
</div>

<div class="scenario-card">
<h3>Scenario 2: Moderate-Risk Observation</h3>
<p><strong>Vignette:</strong> 62F, 3h substernal pressure, HTN/HLD, ECG non-ischemic, hs-trop borderline rising 0→1h, HEART 5.</p>
<ul class="tasks">
<li>Follow pathway branch for moderate risk / observation</li>
<li>Confirm serial troponin/stress or CTA pathway is selected</li>
<li>Select correct disposition: obs/tele admit pending testing</li>
</ul>
<div class="checklist">
<strong>Did the pathway land on the correct end-node?</strong>
<label><input type="checkbox" class="scenario-check" data-scenario="moderate"> ✓ Reached observation/admit branch</label>
</div>
<label style="margin-top:10px">Notes (branching issues, unclear orders):</label>
<textarea id="scenario2_notes" placeholder="Where did branching feel unclear or incorrect?"></textarea>
</div>

<div class="scenario-card">
<h3>Scenario 3: High-Risk Escalation</h3>
<p><strong>Vignette:</strong> 58M, diaphoresis, ECG with new ST depressions V4–V6, elevated troponin.</p>
<ul class="tasks">
<li>Trigger high-risk branch and required meds (antiplatelet/anticoag)</li>
<li>Confirm escalation to cath lab/inpatient cardiology is reached</li>
<li>Verify no pathway steps block time-sensitive care</li>
</ul>
<div class="checklist">
<strong>Did the pathway land on the correct end-node?</strong>
<label><input type="checkbox" class="scenario-check" data-scenario="highrisk"> ✓ Reached escalation/cath lab branch</label>
</div>
<label style="margin-top:10px">Notes (delays, blockers, missing meds):</label>
<textarea id="scenario3_notes" placeholder="Note any delays or wrong routing for high-risk ACS..."></textarea>
</div>

<hr style="margin:30px 0;border:none;border-top:2px solid var(--border-gray)">

<!-- Nielsen Heuristics -->
<h2 style="color:var(--brown-dark);margin-bottom:20px">Nielsen's Usability Heuristics</h2>
<p style="margin-bottom:20px;color:#555">Rate each heuristic from 1 (Poor) to 5 (Excellent) and provide comments.</p>

<div id="heuristicsGrid" class="heuristics-grid"></div>

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

<div class="button-group" style="margin-top:30px;gap:10px;align-items:center;flex-wrap:wrap">
    <button type="button" onclick="downloadCSV()" style="background:var(--brown);color:white;font-size:1.05em;padding:14px 28px">Download Responses (CSV)</button>
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

// Initialize heuristics form (compact grid)
function initializeHeuristics() {{
    const container = document.getElementById('heuristicsGrid');
    container.innerHTML = HEURISTICS.map(h => `
        <div class="heuristic-card">
            <div class="heuristic-head">
                <span class="heuristic-title">${{h.name}}</span>
                <span class="heuristic-info" data-desc="${{h.desc}}">?</span>
            </div>
            <div class="likert" role="radiogroup" aria-label="${{h.name}} rating">
                <label><input type="radio" name="${{h.id}}_rating" value="1" required>1</label>
                <label><input type="radio" name="${{h.id}}_rating" value="2">2</label>
                <label><input type="radio" name="${{h.id}}_rating" value="3" checked>3</label>
                <label><input type="radio" name="${{h.id}}_rating" value="4">4</label>
                <label><input type="radio" name="${{h.id}}_rating" value="5">5</label>
            </div>
            <textarea id="${{h.id}}_comments" placeholder="Comment (optional)"></textarea>
        </div>
    `).join('');
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
    const s1Check = document.querySelector('input[data-scenario="lowrisk"]').checked ? 'Completed' : 'Not Completed';
  const s1Notes = document.getElementById('scenario1_notes').value.replace(/"/g, '""');
    csv += `Scenario 1 - LowRisk,${{s1Check}},"${{s1Notes}}"\n`;
  
    const s2Check = document.querySelector('input[data-scenario="moderate"]').checked ? 'Completed' : 'Not Completed';
  const s2Notes = document.getElementById('scenario2_notes').value.replace(/"/g, '""');
    csv += `Scenario 2 - Moderate,${{s2Check}},"${{s2Notes}}"\n`;
  
    const s3Check = document.querySelector('input[data-scenario="highrisk"]').checked ? 'Completed' : 'Not Completed';
  const s3Notes = document.getElementById('scenario3_notes').value.replace(/"/g, '""');
    csv += `Scenario 3 - HighRisk,${{s3Check}},"${{s3Notes}}"\n`;
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
  link.download = `BetaTesting_${{condition.replace(/\\s+/g, '_')}}_${{name.replace(/\\s+/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.csv`;
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

def create_phase5_executive_summary_docx(data: dict, condition: str, target_audience: str = "", genai_client=None):
    """
    Create a Word document executive summary for Phase 5 with audience-adaptive content.
    Requires python-docx to be installed.
    
    Args:
        data: Session data with phase1, phase2, phase3 info
        condition: Clinical condition name
        target_audience: Free-text target audience description for LLM-based inference
        genai_client: Optional Google Generative AI client for audience inference
        
    Returns:
        BytesIO buffer with .docx content, or None if python-docx unavailable
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()

        # Pull structured data once for clarity
        p1_data = data.get('phase1', {})
        p2_data = data.get('phase2', {})
        p3_data = data.get('phase3', {})
        p4_data = data.get('phase4', {})
        p5_data = data.get('phase5', {})
        
        # Infer audience focus from target audience text
        audience_metadata = infer_audience_from_description(target_audience, genai_client)
        is_executive = audience_metadata.get('strategic_focus', False)
        is_operational = audience_metadata.get('operational_focus', False)
        detail_level = audience_metadata.get('detail_level', 'moderate')
        emphasis_areas = audience_metadata.get('emphasis_areas', [])

        # Build SMART objectives scaffold from Phase 1 objectives text
        smart_source = objectives_text if objectives_text and objectives_text != 'Not provided' else "Clarify objectives in Phase 1 to align with SMART criteria."
        smart_objectives = [
            f"Specific: {smart_source}",
            "Measurable: Define baseline and target metrics (safety events, LOS, throughput, readmissions).",
            "Achievable: Resource plan and staffing validated through stakeholder review.",
            "Relevant: Aligned to organizational quality, safety, and access priorities.",
            "Time-bound: Go-live timeline with 30/60/90 day checkpoints and quarterly reviews."
        ]

        # Phase status snapshot for quick exec visibility
        phase_inputs = [
            "Phase 1 Charter captured" if p1_data else "Phase 1 Charter pending",
            f"Phase 2 Evidence items: {len(p2_data.get('evidence', []))}" if p2_data.get('evidence') else "Phase 2 Evidence pending",
            f"Phase 3 Pathway nodes: {len(p3_data.get('nodes', []))}" if p3_data.get('nodes') else "Phase 3 Pathway design pending",
            "Phase 4 Usability: completed" if p4_data.get('heuristics_data') else "Phase 4 Usability review pending"
        ]

        setting_text = p1_data.get('setting', '')
        population = p1_data.get('population', 'N/A') or 'N/A'
        problem_text = p1_data.get('problem', 'Not provided')
        objectives_text = p1_data.get('objectives', 'Not provided')

        # Title reflects clinical condition and care setting
        setting_suffix = f" - {setting_text}" if setting_text else ""
        title = doc.add_heading(f"Executive Summary: {condition}{setting_suffix}", 0)
        title_format = title.paragraph_format
        title_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add subtitle with audience and detail level
        subtitle = doc.add_paragraph(f"Prepared for: {target_audience or 'Stakeholders'}")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.runs[0].font.size = Pt(11)
        subtitle.runs[0].font.italic = True

        if emphasis_areas:
            emphasis_line = doc.add_paragraph(f"Audience focus: {', '.join(emphasis_areas)}")
            emphasis_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
            emphasis_line.runs[0].font.size = Pt(10)
        
        # AUDIENCE-ADAPTIVE CONTENT STRUCTURE
        
        if is_executive:
            # === EXECUTIVE SUMMARY (C-SUITE FOCUS) ===
            doc.add_heading("Strategic Overview", level=1)
            doc.add_paragraph(
                f"This {condition} clinical pathway addresses a critical gap in {setting_text or 'clinical'} practice, "
                f"enabling standardized, evidence-based care delivery that improves patient outcomes while optimizing resource utilization."
            )
            
            doc.add_heading("Business Case & Value Proposition", level=1)
            doc.add_paragraph(
                f"Problem: {problem_text}"
            )

            doc.add_heading("SMART Objectives", level=1)
            for item in smart_objectives:
                doc.add_paragraph(item, style='List Bullet')

            doc.add_heading("Phase Inputs Synthesized (Phases 1-4)", level=1)
            for item in phase_inputs:
                doc.add_paragraph(item, style='List Bullet')
            
            # Extract ROI/impact-related metrics from objectives
            doc.add_paragraph("Key Benefits:", style='List Bullet')
            doc.add_paragraph("Improved patient safety and outcomes through evidence-based decision-making", style='List Bullet 2')
            doc.add_paragraph("Reduced variation in care practices across providers and shifts", style='List Bullet 2')
            doc.add_paragraph("Optimized resource utilization and reduced unnecessary testing/admissions", style='List Bullet 2')
            doc.add_paragraph("Enhanced staff competency through standardized education and onboarding", style='List Bullet 2')
            doc.add_paragraph("Improved patient experience and satisfaction", style='List Bullet 2')
            
            # Evidence Summary (executive brief - counts only)
            doc.add_heading("Evidence Foundation", level=1)
            evidence = p2_data.get('evidence', [])
            if evidence:
                doc.add_paragraph(f"This pathway is built on {len(evidence)} peer-reviewed evidence items.")
                
                # Grade breakdown
                grades = {}
                for e in evidence:
                    grade = e.get('grade', 'Un-graded')
                    grades[grade] = grades.get(grade, 0) + 1
                
                high_quality = sum(count for grade, count in grades.items() if grade in ['A', 'High', 'Level 1'])
                doc.add_paragraph(f"Quality distribution: {high_quality} high-quality articles provide strong evidence base", style='List Bullet')
            
            # Implementation Scope (summary only)
            doc.add_heading("Implementation Scope", level=1)
            nodes = p3_data.get('nodes', [])
            doc.add_paragraph(f"Pathway includes {len(nodes)} care decision points and clinical actions") if nodes else doc.add_paragraph("Pathway design in progress")
            doc.add_paragraph(f"Target population: {population}", style='List Bullet')
            doc.add_paragraph(f"Clinical setting: {setting_text}", style='List Bullet')
            
            # Readiness Assessment
            doc.add_heading("Readiness for Implementation", level=1)
            doc.add_paragraph("Design and Validation:", style='List Bullet')
            doc.add_paragraph("Clinical pathway design completed and reviewed for feasibility", style='List Bullet 2')
            doc.add_paragraph("Usability testing conducted with target users" if p4_data.get('heuristics_data') else "Usability testing planned", style='List Bullet 2')
            
            doc.add_paragraph("Stakeholder Engagement:", style='List Bullet')
            doc.add_paragraph("Expert panel feedback: " + ("Completed and integrated" if p5_data.get('expert_html') else "Scheduled"), style='List Bullet 2')
            doc.add_paragraph("Beta testing: " + ("Completed" if p5_data.get('beta_html') else "Planned"), style='List Bullet 2')
            
            # Next Steps (Executive Focused)
            doc.add_heading("Executive Action Items", level=1)
            doc.add_paragraph(
                "Approve final pathway design and authorize stakeholder engagement activities",
                style='List Number'
            )
            doc.add_paragraph(
                "Allocate resources for implementation (staff education, system integration, monitoring)",
                style='List Number'
            )
            doc.add_paragraph(
                "Establish governance structure for ongoing pathway monitoring and improvement",
                style='List Number'
            )
            doc.add_paragraph(
                "Schedule go-live and define success metrics (safety, efficiency, quality outcomes)",
                style='List Number'
            )
            
        else:
            # === OPERATIONAL/CLINICAL FOCUS ===
            doc.add_heading("Project Scope", level=1)
            doc.add_paragraph(
                f"Clinical pathway for {condition or 'N/A'} in {setting_text or 'care setting not specified'}, focused on {population}."
            )
            doc.add_paragraph(f"Problem statement: {problem_text}", style='List Bullet')
            inclusion = p1_data.get('inclusion', '')
            exclusion = p1_data.get('exclusion', '')
            if inclusion:
                doc.add_paragraph(f"Inclusion criteria: {inclusion}", style='List Bullet 2')
            if exclusion:
                doc.add_paragraph(f"Exclusion criteria: {exclusion}", style='List Bullet 2')

            doc.add_heading("Project Goals & Success Measures", level=1)
            doc.add_paragraph(objectives_text)
            doc.add_paragraph(
                "Outcome focus: safer, faster care delivery with clear resource stewardship in the specified care setting.",
                style='List Bullet'
            )

            doc.add_heading("SMART Objectives", level=1)
            for item in smart_objectives:
                doc.add_paragraph(item, style='List Bullet')

            doc.add_heading("Phase Inputs Synthesized (Phases 1-4)", level=1)
            for item in phase_inputs:
                doc.add_paragraph(item, style='List Bullet')
            
            # Evidence Summary (operational - detail level determines depth)
            doc.add_heading("Evidence Summary", level=1)
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
                
                # Add node list (always for operational summaries)
                if detail_level == "detailed":
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
            heuristics = p4_data.get('heuristics_data', {})
            
            if heuristics:
                doc.add_paragraph("Nielsen Heuristics Review Completed", style='List Bullet')
                doc.add_paragraph(f"Total heuristics evaluated: {len(heuristics)}", style='List Bullet 2')
            else:
                doc.add_paragraph("Usability assessment pending")

            # Co-design, validation, and education
            doc.add_heading("Co-Design, Testing, and Education", level=1)
            expert_status = (
                "Expert panel feedback captured via structured review and integrated into the pathway." if p5_data.get('expert_html')
                else "Expert panel review planned using structured feedback form; integrate findings into the pathway."
            )
            beta_status = (
                "Beta testing completed with target users; updates folded into the current pathway version." if p5_data.get('beta_html')
                else "Beta testing planned in the target setting; incorporate usability findings into the pathway."
            )
            edu_status = (
                "Custom interactive education module prepared for staff onboarding (HTML, offline-capable)." if p5_data.get('edu_html')
                else "Interactive education module planned to support staff onboarding and competency validation."
            )
            doc.add_paragraph(expert_status, style='List Bullet')
            doc.add_paragraph(beta_status, style='List Bullet')
            doc.add_paragraph(edu_status, style='List Bullet')
            
            # Implementation Next Steps
            doc.add_heading("Implementation Next Steps", level=1)
            doc.add_paragraph(
                "Finalize and sign off the pathway after incorporating expert and beta feedback for the specified care setting.",
                style='List Number'
            )
            doc.add_paragraph(
                "Deploy the interactive education module; track staff completion and competency.",
                style='List Number'
            )
            doc.add_paragraph(
                "Go-live with monitoring for safety, throughput, and resource stewardship in the care setting.",
                style='List Number'
            )
            doc.add_paragraph(
                "Report performance to leadership and iterate monthly based on outcomes and user feedback.",
                style='List Number'
            )
            doc.add_paragraph(
                "Maintain continuous improvement cycles with refreshed education content as the pathway evolves.",
                style='List Number'
            )
        
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


# ==========================================
# ROLE-SPECIFIC EDUCATION MODULE FUNCTIONS
# ==========================================

def get_role_depth_mapping(target_audience: str) -> dict:
    """
    Map clinical roles to content depth, node types, and expectations.
    Returns configuration for role-specific education module customization.
    
    Args:
        target_audience: Free-text role description (e.g., "Emergency Medicine Residents")
    
    Returns:
        Dict with:
        - 'role_type': Simplified role (Resident, Attending, Nurse, APP, Student, etc.)
        - 'depth_level': 'deep', 'moderate', or 'focused'
        - 'node_types': List of pathway node types to include
        - 'role_statement': Explicit role statement for headers/content
        - 'expectations': Key expectations for this role in the pathway
    """
    audience_lower = (target_audience or "").lower()
    
    # Resident/Fellow/Trainee (deep clinical reasoning)
    if any(word in audience_lower for word in ['resident', 'fellow', 'trainee', 'junior', 'pgy']):
        return {
            'role_type': 'Resident',
            'depth_level': 'deep',
            'node_types': ['Start', 'Decision', 'Process', 'Action', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you are responsible for clinical decision-making and pathway execution.',
            'expectations': [
                'Understand the clinical reasoning behind each decision point',
                'Know when to escalate to attending staff',
                'Apply evidence-based protocols independently',
                'Recognize complications and deviations from pathway'
            ]
        }
    
    # Attending/Senior Physician (oversight, decision validation)
    elif any(word in audience_lower for word in ['attending', 'physician', 'doctor', 'consultant', 'provider', 'senior']):
        return {
            'role_type': 'Attending',
            'depth_level': 'deep',
            'node_types': ['Start', 'Decision', 'Process', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you provide clinical oversight and validate key care decisions.',
            'expectations': [
                'Supervise resident implementation of pathway',
                'Make final decisions at critical junctures',
                'Ensure adherence to evidence-based protocols',
                'Address complex or unusual presentations'
            ]
        }
    
    # Nurse/RN (assessment, monitoring, communication)
    elif any(word in audience_lower for word in ['nurse', 'rn', 'lpn', 'nursing', 'cna']):
        return {
            'role_type': 'Nurse',
            'depth_level': 'moderate',
            'node_types': ['Start', 'Process', 'Action', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you execute clinical assessments, monitoring, and care coordination.',
            'expectations': [
                'Perform initial and ongoing patient assessment',
                'Monitor for changes requiring escalation',
                'Execute orders and document findings',
                'Communicate status changes to medical team'
            ]
        }
    
    # APP/NP/PA (independent to semi-independent decision-making)
    elif any(word in audience_lower for word in ['app', 'np', 'nurse practitioner', 'pa', 'physician assistant', 'practitioner']):
        return {
            'role_type': 'APP',
            'depth_level': 'deep',
            'node_types': ['Start', 'Decision', 'Process', 'Action', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you make independent decisions within scope and collaborate with physicians.',
            'expectations': [
                'Make autonomous clinical decisions per scope of practice',
                'Know when to consult physician colleagues',
                'Order and interpret diagnostic tests',
                'Implement therapeutic interventions'
            ]
        }
    
    # Student/Learner (foundational understanding)
    elif any(word in audience_lower for word in ['student', 'learner', 'medical student', 'nursing student', 'clerk']):
        return {
            'role_type': 'Student',
            'depth_level': 'focused',
            'node_types': ['Start', 'Decision', 'Process', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you are learning the clinical pathway and evidence-based practice.',
            'expectations': [
                'Understand clinical presentation and initial assessment',
                'Learn how clinical decisions are made',
                'Recognize key decision points in care',
                'Ask questions and build clinical knowledge'
            ]
        }
    
    # Allied Health (specific clinical roles)
    elif any(word in audience_lower for word in ['therapist', 'tech', 'assistant', 'specialist', 'coordinator']):
        return {
            'role_type': 'Allied Health',
            'depth_level': 'focused',
            'node_types': ['Process', 'Action', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you support core clinical care through specialized skills.',
            'expectations': [
                'Understand your role in the pathway',
                'Know when your intervention is needed',
                'Communicate findings to clinical team',
                'Document activities accurately'
            ]
        }
    
    # Default/unknown
    else:
        return {
            'role_type': 'Clinical Team Member',
            'depth_level': 'moderate',
            'node_types': ['Start', 'Decision', 'Process', 'Action', 'End'],
            'role_statement': f'As a {target_audience.strip()}, you are part of the clinical team implementing this evidence-based pathway.',
            'expectations': [
                'Understand the pathway and your role within it',
                'Follow evidence-based protocols',
                'Communicate effectively with team members',
                'Contribute to quality improvement'
            ]
        }


def generate_role_specific_module_header(
    target_audience: str,
    condition: str,
    care_setting: str,
    node: dict = None
) -> str:
    """
    Generate role-specific module header with explicit role clarity.
    
    Args:
        target_audience: Target learner role
        condition: Clinical condition
        care_setting: Care environment (e.g., Emergency Department)
        node: Optional pathway node for context
    
    Returns:
        String with role-specific header statement
    """
    role_mapping = get_role_depth_mapping(target_audience)
    role_statement = role_mapping['role_statement']
    
    if node:
        node_label = node.get('label', 'Clinical Decision Point')
        return f"{role_statement} In this module, you will learn your specific role when managing: {node_label}"
    else:
        return f"{role_statement} This module covers the {condition} pathway in {care_setting or 'your clinical setting'}."


def generate_role_specific_learning_objectives(
    target_audience: str,
    condition: str,
    nodes: list = None,
    module_idx: int = 0
) -> list:
    """
    Generate role-specific learning objectives based on audience and pathway nodes.
    
    Args:
        target_audience: Target learner role
        condition: Clinical condition
        nodes: List of pathway nodes for this module
        module_idx: Module number (0-indexed)
    
    Returns:
        List of 3-4 role-specific learning objectives
    """
    role_mapping = get_role_depth_mapping(target_audience)
    role_type = role_mapping['role_type']
    expectations = role_mapping['expectations']
    
    objectives = []
    
    if nodes and len(nodes) > 0:
        # Extract key actions from nodes
        key_actions = [n.get('label', '') for n in nodes if n.get('type') in ['Decision', 'Process', 'Action'] and n.get('label')]
        
        if key_actions:
            first_action = key_actions[0]
            if role_type == 'Resident':
                objectives.append(f"Explain the clinical reasoning behind {first_action.lower()}")
                objectives.append(f"Determine when to escalate {condition} cases to senior staff")
                objectives.append(f"Implement {condition} pathway protocols independently")
            elif role_type == 'Attending':
                objectives.append(f"Supervise resident execution of {first_action.lower()}")
                objectives.append(f"Validate clinical decisions at critical junctures")
                objectives.append(f"Address complex {condition} presentations")
            elif role_type == 'Nurse':
                objectives.append(f"Perform assessment for {condition}")
                objectives.append(f"Recognize findings that require escalation")
                objectives.append(f"Execute care orders and monitor patient status")
            elif role_type == 'APP':
                objectives.append(f"Make autonomous decisions regarding {first_action.lower()}")
                objectives.append(f"Know when to consult physician colleagues")
                objectives.append(f"Order and interpret tests within scope of practice")
            else:
                objectives.append(f"Understand the approach to {condition}")
                objectives.append(f"Recognize your role in pathway implementation")
                objectives.append(f"Know when to escalate or ask for help")
    
    # Add expectation-based objectives
    if not objectives and expectations:
        objectives = expectations[:3]
    
    # Fallback
    if not objectives:
        objectives = [
            f"Understand evidence-based management of {condition}",
            f"Recognize key decision points in the pathway",
            "Implement pathway protocols appropriately"
        ]
    
    return objectives[:4]  # Return max 4 objectives


def generate_role_specific_quiz_scenario(
    question_idx: int,
    node: dict,
    target_audience: str,
    evidence_citations: list = None
) -> dict:
    """
    Generate a realistic, role-specific quiz scenario based on pathway node.
    
    Args:
        question_idx: Question number
        node: Pathway node (Decision or Process)
        target_audience: Target learner role
        evidence_citations: List of dicts with 'pmid', 'title', 'grade' from Phase 2
    
    Returns:
        Dict with 'question', 'options', 'correct', 'explanation', 'evidence'
    """
    role_mapping = get_role_depth_mapping(target_audience)
    role_type = role_mapping['role_type']
    node_label = node.get('label', 'Clinical decision point')
    node_evidence = node.get('evidence', '')
    
    # Build role-specific scenario framing
    if role_type == 'Resident':
        scenario_stem = f"You are the resident caring for a patient with findings suggesting {node_label.lower()}. "
    elif role_type == 'Attending':
        scenario_stem = f"The resident presents a case where {node_label.lower()} is being considered. You need to "
    elif role_type == 'Nurse':
        scenario_stem = f"During your assessment, you observe {node_label.lower()}. "
    elif role_type == 'APP':
        scenario_stem = f"You are evaluating a patient and need to decide on {node_label.lower()}. "
    else:
        scenario_stem = f"When managing a patient with this presentation, you should consider {node_label.lower()}. "
    
    # Create role-appropriate answer options
    if role_type == 'Resident':
        options = [
            f"Follow the pathway protocol and prepare to discuss with attending",
            "Make a decision independently without consulting",
            "Wait for attending without taking any action",
            "Refer to another service immediately"
        ]
    elif role_type == 'Attending':
        options = [
            "Validate the pathway decision and provide oversight",
            "Overrule the resident without explanation",
            "Defer entirely to the resident without review",
            "Order additional tests that contradict pathway"
        ]
    elif role_type == 'Nurse':
        options = [
            "Alert the clinical team and monitor per protocol",
            "Document and wait without escalating",
            "Perform the intervention yourself",
            "Assume it will resolve without intervention"
        ]
    elif role_type == 'APP':
        options = [
            "Implement per scope of practice and document decision",
            "Always refer to physician regardless of scope",
            "Proceed without consulting any guidelines",
            "Delay care until physician is available"
        ]
    else:
        options = [
            f"Recognize {node_label.lower()} and alert appropriate staff",
            "Ignore the finding",
            "Handle independently without telling anyone",
            "Wait to see if it resolves"
        ]
    
    # Build evidence-backed explanation
    explanation = f"The pathway recommends {node_label.lower()}. "
    if node_evidence and node_evidence != 'N/A':
        explanation += f"(Evidence: {node_evidence}) "
    
    # Add evidence citation if available
    evidence_note = ""
    if evidence_citations:
        for cite in evidence_citations[:1]:  # Use first citation
            if cite.get('pmid'):
                grade = cite.get('grade', 'Grade unknown')
                evidence_note = f" [PMID: {cite.get('pmid')}, {grade}]"
                explanation += evidence_note
                break
    
    return {
        'question': scenario_stem + f"What should you do?",
        'options': options,
        'correct': 0,  # First option is always correct
        'explanation': explanation,
        'evidence': evidence_note
    }


def filter_nodes_by_role(nodes: list, target_audience: str) -> list:
    """
    Filter pathway nodes based on role depth and responsibilities.
    
    Args:
        nodes: Full list of pathway nodes
        target_audience: Target learner role
    
    Returns:
        Filtered list of nodes appropriate for the role
    """
    role_mapping = get_role_depth_mapping(target_audience)
    allowed_types = role_mapping['node_types']
    
    return [n for n in nodes if n.get('type') in allowed_types]
