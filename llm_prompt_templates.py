"""
LLM Prompt Templates for Clinical Pathway Generation

These prompts can be used with Large Language Models (LLMs) to generate
robust clinical pathway decision trees and flowcharts for any care condition
and clinical setting.

Integration:
- Use with Gemini API in streamlit_app.py
- Compatible with pathway_generator.py data structures
- Outputs JSON format matching app node schema

Usage:
1. Select appropriate prompt template based on your needs
2. Fill in the condition-specific details
3. Use with LLM (Gemini, GPT-4, Claude, etc.) to generate pathway
4. Parse JSON response into app node format
5. Optionally convert to ClinicalPathway for advanced features
"""

from typing import Optional, List, Dict, Any


# ============================================================================
# PROMPT TEMPLATE 1: Comprehensive Pathway Generation
# ============================================================================

COMPREHENSIVE_PATHWAY_PROMPT = """You are an expert clinical informaticist and emergency medicine physician tasked with creating an evidence-based clinical pathway decision tree for a specific medical condition.

Your task is to generate a comprehensive, structured clinical pathway following the standardized format used in evidence-based emergency department pathways.

CONDITION INFORMATION:
- Condition Name: {condition_name}
- Chief Complaint: {chief_complaint}
- Clinical Setting: {clinical_setting}
- Special Populations to Consider: {special_populations}

AVAILABLE EVIDENCE BASE:
{evidence_context}

PATHWAY STRUCTURE REQUIREMENTS:

1. STEP 1: PATIENT ENTRY
   - Define the chief complaint and typical presenting symptoms
   - Include relevant patient demographics considerations

2. STEP 2: INITIAL CRITICALITY CHECK
   - Identify 3-5 life-threatening conditions or red flags that require immediate critical care intervention
   - These should be conditions that would trigger ERU (Emergency Resuscitation Unit) or critical care pathway
   - Format as yes/no questions (e.g., "Hemodynamic Instability?", "Airway Compromise?")

3. CRITICAL CARE PATHWAY (if criticality check is positive)
   - Specify immediate interventions required
   - List team activations needed (e.g., "Activate STEMI Team", "Trauma Activation")
   - Include resuscitation protocols

4. STEP 3: PIT ORDERS (Provider in Triage Orders)
   Organize into categories:
   - Labs: Standard panels (CBC, BMP, etc.) + condition-specific labs
   - Imaging: Initial imaging studies (CXR, CT, US, etc.)
   - Medications: Condition-specific medications with dosages when appropriate
   - Cardiac: EKG, monitoring requirements
   - Urine: UA, pregnancy tests, cultures
   - Other: Special tests, consults, etc.
   
   Include conditional orders (e.g., "Troponin if ACS concern", "HCG if female <50")

5. STEP 4: SECONDARY CRITICALITY CHECK (if applicable)
   - Additional criticality assessment after initial workup
   - Based on results from Step 3 (e.g., "STEMI on EKG?", "Critical Lab Values?")
   - May loop back to critical care if positive

6. STEP 5: EVIDENCE-BASED ADDITIONS
   Include:
   - Risk Stratification Tools: Name scoring systems (e.g., HEART, GBS, Oakland, Wells)
   - Advanced Imaging: When to order (e.g., "MRI if stroke concern", "CT PE Protocol if Wells High")
   - Advanced Treatments: Condition-specific interventions
   - Special Considerations: Age, pregnancy, comorbidities
   
   For each, specify:
   - When to apply (criteria)
   - How to interpret results
   - Action based on results

7. STEP 6: DISPOSITION
   Provide criteria for THREE disposition options:
   
   a) DISCHARGE:
      - Specific criteria for safe discharge
      - Follow-up requirements
      - Discharge medications/instructions
   
   b) OBSERVATION:
      - Criteria for observation unit admission
      - Monitoring requirements
      - Expected duration
      - Discharge criteria from observation
   
   c) INPATIENT:
      - Criteria requiring full hospital admission
      - ICU vs floor considerations
      - Specialized care needs

OUTPUT FORMAT: JSON array of nodes with THESE EXACT FIELDS:
- "type": "Start" | "Decision" | "Process" | "End" (no other types)
- "label": Concise, specific clinical step (max 120 characters)
- "evidence": PMID citation OR "N/A"
- "notes": (optional) Actionable clinical details:
  * RED FLAG SIGNS
  * CLINICAL THRESHOLDS
  * MONITORING PARAMETERS
- "branches": (only for Decision nodes) Array of {{"label": "Yes/No", "target": index}}
- "role": (optional) Swimlane assignment: "Physician", "Nurse", "Critical Care", etc.

IMPORTANT GUIDELINES:
1. Base all recommendations on current evidence-based medicine
2. Use validated risk stratification tools with specific numerical thresholds
3. Include specific medication dosages (brand and generic names)
4. Ensure disposition criteria are clear and objective
5. Consider special populations (pregnant, pediatric, elderly, immunocompromised)
6. Include appropriate safety nets and follow-up
7. Specify time-sensitive interventions clearly
8. Each Decision must have distinct branches (no immediate reconvergence)
9. All pathways must terminate in End nodes

Generate the clinical pathway now.
"""


# ============================================================================
# PROMPT TEMPLATE 2: Risk Stratification Focus
# ============================================================================

RISK_STRATIFICATION_PROMPT = """You are an expert in clinical risk stratification. Identify and describe appropriate evidence-based risk stratification tools for a clinical condition.

CONDITION: {condition_name}
CHIEF COMPLAINT: {chief_complaint}
CLINICAL SETTING: {clinical_setting}

For this condition, identify:

1. VALIDATED RISK STRATIFICATION TOOLS:
   - Name of scoring system/rule
   - Components and scoring method
   - Validation studies (include PMIDs if known)
   - Sensitivity/specificity data

2. WHEN TO USE EACH TOOL:
   - Patient characteristics
   - Timing in clinical course
   - Required data points

3. INTERPRETATION:
   - Low risk criteria and actions
   - Moderate risk criteria and actions
   - High risk criteria and actions

4. LIMITATIONS:
   - When tools may not apply
   - Special population considerations
   - Known limitations

5. INTEGRATION INTO PATHWAY:
   - Where in the pathway to apply the tool
   - How results affect disposition
   - Documentation requirements

OUTPUT FORMAT: JSON object with structure:
{{
  "risk_stratification_tools": [
    {{
      "name": "Score Name",
      "components": ["component1", "component2"],
      "scoring_method": "description",
      "pmid": "12345678",
      "interpretation": {{
        "low_risk": {{"score_range": "0-3", "action": "discharge"}},
        "moderate_risk": {{"score_range": "4-6", "action": "observation"}},
        "high_risk": {{"score_range": "≥7", "action": "admission"}}
      }},
      "limitations": ["limitation1", "limitation2"]
    }}
  ],
  "recommended_tool": "primary tool name",
  "pathway_integration": "description of when/how to use"
}}
"""


# ============================================================================
# PROMPT TEMPLATE 3: PIT Orders Generation
# ============================================================================

PIT_ORDERS_PROMPT = """You are an expert emergency physician. Generate a comprehensive PIT (Provider in Triage) order set for a specific clinical condition.

CONDITION: {condition_name}
CHIEF COMPLAINT: {chief_complaint}
CLINICAL SETTING: {clinical_setting}

Generate PIT orders organized by category:

1. LABS:
   - Standard panels needed
   - Condition-specific labs
   - Conditional labs (with criteria)

2. IMAGING:
   - Initial imaging studies
   - Conditional imaging (with criteria)
   - Special considerations (pregnancy, renal function, contrast allergy)

3. MEDICATIONS:
   - Immediate treatments
   - Pain management
   - Condition-specific medications
   - Include: Brand name (generic), dose, route, frequency

4. CARDIAC:
   - EKG requirements
   - Monitoring needs
   - Telemetry criteria

5. URINE:
   - UA requirements
   - Pregnancy testing (criteria)
   - Culture requirements

6. OTHER:
   - IV access
   - Oxygen requirements
   - Consults to initiate
   - Special tests

OUTPUT FORMAT: JSON object:
{{
  "pit_orders": [
    {{
      "category": "Labs",
      "items": ["CBC", "BMP", "Troponin"],
      "conditional": "If ACS concern",
      "notes": "Serial troponins at 0h and 3h"
    }}
  ],
  "contraindications_to_check": ["allergy list", "renal function", "pregnancy status"],
  "special_population_modifications": {{
    "pregnant": "modifications",
    "renal_failure": "modifications",
    "elderly": "modifications"
  }}
}}
"""


# ============================================================================
# PROMPT TEMPLATE 4: Disposition Criteria
# ============================================================================

DISPOSITION_CRITERIA_PROMPT = """You are an expert in clinical disposition decisions. Generate clear, objective disposition criteria for a clinical condition.

CONDITION: {condition_name}
CLINICAL CONTEXT: {clinical_context}
AVAILABLE RISK SCORES: {risk_scores}

Generate criteria for THREE disposition options:

1. DISCHARGE CRITERIA:
   - Clinical stability requirements (specific vital sign parameters)
   - Objective measures (labs, imaging results)
   - Functional status requirements
   - Pain/symptom control criteria
   - Safety considerations
   - Required follow-up
   - Discharge medications with specific dosing

2. OBSERVATION CRITERIA:
   - When observation is appropriate vs. inpatient
   - What needs to be monitored (specific parameters)
   - Expected duration
   - Discharge criteria from observation
   - Escalation criteria (to inpatient)
   - Resource requirements (telemetry, nursing ratio)

3. INPATIENT ADMISSION CRITERIA:
   - Objective criteria requiring admission
   - ICU vs floor decision criteria
   - Specialized care needs
   - Expected interventions
   - Consult requirements

OUTPUT FORMAT: JSON object:
{{
  "disposition_criteria": {{
    "discharge": {{
      "criteria": ["criterion 1", "criterion 2"],
      "follow_up": "Provider type within timeframe",
      "medications": ["med1 with dose", "med2 with dose"],
      "return_precautions": ["red flag 1", "red flag 2"]
    }},
    "observation": {{
      "criteria": ["criterion 1", "criterion 2"],
      "monitoring": ["parameter 1", "parameter 2"],
      "duration": "expected hours",
      "discharge_criteria": ["criterion 1"],
      "escalation_criteria": ["criterion 1"]
    }},
    "inpatient": {{
      "floor_criteria": ["criterion 1"],
      "icu_criteria": ["criterion 1"],
      "consults": ["specialty 1", "specialty 2"],
      "expected_los": "estimated days"
    }}
  }}
}}
"""


# ============================================================================
# PROMPT TEMPLATE 5: Special Population Modifications
# ============================================================================

SPECIAL_POPULATION_PROMPT = """You are an expert in managing special populations. Generate pathway modifications for a specific population within a clinical condition.

BASE CONDITION: {base_condition}
SPECIAL POPULATION: {special_population}
BASE PATHWAY SUMMARY: {base_pathway_summary}

For {special_population} patients with {base_condition}, identify:

1. MODIFICATIONS TO INITIAL ASSESSMENT:
   - Additional history elements
   - Modified physical exam
   - Different red flags/criticality criteria

2. MODIFICATIONS TO DIAGNOSTICS:
   - Tests to avoid (with reasons)
   - Alternative tests to use
   - Different imaging protocols
   - Modified lab interpretation

3. MODIFICATIONS TO TREATMENT:
   - Contraindicated medications
   - Dose adjustments
   - Alternative treatments
   - Special monitoring requirements

4. MODIFICATIONS TO DISPOSITION:
   - Different discharge criteria
   - Additional consultation requirements
   - Modified follow-up requirements
   - Special documentation needs

5. SPECIFIC CONSIDERATIONS:
   - Unique complications to watch for
   - Communication considerations
   - Resource requirements
   - Legal/ethical considerations

OUTPUT FORMAT: JSON object:
{{
  "population": "{special_population}",
  "modifications": {{
    "assessment": {{
      "additional_history": ["item1"],
      "modified_exam": ["item1"],
      "different_red_flags": ["item1"]
    }},
    "diagnostics": {{
      "avoid": [{{"test": "test name", "reason": "why"}}],
      "alternatives": [{{"instead_of": "original", "use": "alternative"}}],
      "modified_interpretation": ["item1"]
    }},
    "treatment": {{
      "contraindicated": [{{"medication": "name", "reason": "why"}}],
      "dose_adjustments": [{{"medication": "name", "adjustment": "details"}}],
      "alternatives": ["item1"]
    }},
    "disposition": {{
      "modified_criteria": ["item1"],
      "additional_consults": ["specialty"],
      "follow_up_changes": "description"
    }}
  }},
  "key_considerations": ["point1", "point2"]
}}
"""


# ============================================================================
# PROMPT TEMPLATE 6: Pathway Refinement
# ============================================================================

PATHWAY_REFINEMENT_PROMPT = """You are reviewing and refining an existing clinical pathway. Your task is to:

1. Validate the pathway against current evidence-based guidelines
2. Identify gaps or missing critical steps
3. Suggest improvements for clarity and usability
4. Ensure appropriate risk stratification
5. Verify disposition criteria are appropriate

EXISTING PATHWAY (JSON format):
{existing_pathway_json}

USER'S REFINEMENT REQUEST:
{refinement_request}

AVAILABLE EVIDENCE:
{evidence_context}

REFINEMENT GUIDELINES:
- PRESERVE decision science integrity (maintain branching, don't collapse to linear)
- PRESERVE clinical complexity (don't oversimplify)
- ENHANCE specificity (add validated scores, specific doses, exact thresholds)
- MAINTAIN DAG structure (no cycles, forward progression only)
- ENSURE all paths terminate in End nodes

OUTPUT: Complete revised JSON array of nodes with same format as input.
Include a brief summary of changes made at the end.
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_comprehensive_prompt(
    condition_name: str,
    chief_complaint: str,
    clinical_setting: str = "ED",
    special_populations: str = "Pregnant, Pediatric, Elderly",
    evidence_context: str = ""
) -> str:
    """Format the comprehensive pathway prompt with provided values"""
    return COMPREHENSIVE_PATHWAY_PROMPT.format(
        condition_name=condition_name,
        chief_complaint=chief_complaint,
        clinical_setting=clinical_setting,
        special_populations=special_populations,
        evidence_context=evidence_context or "No specific evidence provided."
    )


def format_risk_stratification_prompt(
    condition_name: str,
    chief_complaint: str,
    clinical_setting: str = "ED"
) -> str:
    """Format risk stratification prompt"""
    return RISK_STRATIFICATION_PROMPT.format(
        condition_name=condition_name,
        chief_complaint=chief_complaint,
        clinical_setting=clinical_setting
    )


def format_pit_orders_prompt(
    condition_name: str,
    chief_complaint: str,
    clinical_setting: str = "ED"
) -> str:
    """Format PIT orders prompt"""
    return PIT_ORDERS_PROMPT.format(
        condition_name=condition_name,
        chief_complaint=chief_complaint,
        clinical_setting=clinical_setting
    )


def format_disposition_prompt(
    condition_name: str,
    clinical_context: str,
    risk_scores: str = ""
) -> str:
    """Format disposition criteria prompt"""
    return DISPOSITION_CRITERIA_PROMPT.format(
        condition_name=condition_name,
        clinical_context=clinical_context,
        risk_scores=risk_scores or "Standard clinical assessment"
    )


def format_special_population_prompt(
    base_condition: str,
    special_population: str,
    base_pathway_summary: str
) -> str:
    """Format special population modification prompt"""
    return SPECIAL_POPULATION_PROMPT.format(
        base_condition=base_condition,
        special_population=special_population,
        base_pathway_summary=base_pathway_summary
    )


def format_refinement_prompt(
    existing_pathway_json: str,
    refinement_request: str,
    evidence_context: str = ""
) -> str:
    """Format pathway refinement prompt"""
    return PATHWAY_REFINEMENT_PROMPT.format(
        existing_pathway_json=existing_pathway_json,
        refinement_request=refinement_request,
        evidence_context=evidence_context or "No specific evidence provided."
    )


def build_evidence_context(evidence_list: List[Dict[str, Any]], max_items: int = 20) -> str:
    """
    Build evidence context string from Phase 2 evidence list.
    
    Args:
        evidence_list: st.session_state.data['phase2']['evidence']
        max_items: Maximum number of evidence items to include
    
    Returns:
        Formatted string for prompt context
    """
    if not evidence_list:
        return "No specific evidence provided."
    
    context_lines = []
    for e in evidence_list[:max_items]:
        pmid = e.get('id', 'N/A')
        title = e.get('title', 'Unknown')
        abstract = e.get('abstract', '')[:200]
        context_lines.append(f"- PMID {pmid}: {title} | Abstract: {abstract}")
    
    return "\n".join(context_lines)


def build_pathway_summary(nodes: List[Dict[str, Any]]) -> str:
    """
    Build a summary of existing pathway for context.
    
    Args:
        nodes: st.session_state.data['phase3']['nodes']
    
    Returns:
        Summary string describing the pathway
    """
    if not nodes:
        return "No existing pathway."
    
    node_count = len(nodes)
    node_types = {}
    for node in nodes:
        ntype = node.get('type', 'Unknown')
        node_types[ntype] = node_types.get(ntype, 0) + 1
    
    type_summary = ", ".join([f"{count} {ntype}" for ntype, count in node_types.items()])
    
    # Get first and last labels
    first_label = nodes[0].get('label', 'Unknown')[:50]
    last_labels = [n.get('label', '')[:30] for n in nodes if n.get('type') == 'End'][:3]
    
    summary = f"Pathway with {node_count} nodes ({type_summary}). "
    summary += f"Starts with: '{first_label}'. "
    if last_labels:
        summary += f"End points: {', '.join(last_labels)}."
    
    return summary


# ============================================================================
# PROMPT FOR MERMAID/DOT GENERATION (Alternative to programmatic generation)
# ============================================================================

MERMAID_GENERATION_PROMPT = """Convert the following clinical pathway nodes into a Mermaid flowchart diagram.

PATHWAY NODES (JSON):
{nodes_json}

REQUIREMENTS:
1. Use Mermaid syntax for flowchart (graph TD for top-down)
2. Use appropriate shapes:
   - Start/End nodes: ([ ]) stadium shape
   - Decision nodes: {{ }} diamond/rhombus
   - Process nodes: [ ] rectangle
3. Include edge labels for Decision branches
4. Keep node text concise (max 50 chars)
5. Add styling classes:
   - startEnd: green background
   - decision: red/pink background
   - process: yellow background

OUTPUT: Complete Mermaid diagram code only, no explanations.
"""


DOT_GENERATION_PROMPT = """Convert the following clinical pathway nodes into a Graphviz DOT diagram.

PATHWAY NODES (JSON):
{nodes_json}

REQUIREMENTS:
1. Use digraph with rankdir=TB (top-to-bottom)
2. Use appropriate shapes:
   - Start/End: oval shape
   - Decision: diamond shape
   - Process: box shape
3. Include edge labels for Decision branches
4. Use colors:
   - Start/End: fillcolor="#D5E8D4" (green)
   - Decision: fillcolor="#F8CECC" (pink)
   - Process: fillcolor="#FFF2CC" (yellow)
5. Wrap long labels with \\n

OUTPUT: Complete DOT source code only, no explanations.
"""


def format_mermaid_prompt(nodes_json: str) -> str:
    """Format Mermaid generation prompt"""
    return MERMAID_GENERATION_PROMPT.format(nodes_json=nodes_json)


def format_dot_prompt(nodes_json: str) -> str:
    """Format DOT generation prompt"""
    return DOT_GENERATION_PROMPT.format(nodes_json=nodes_json)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Generate comprehensive pathway prompt
    prompt = format_comprehensive_prompt(
        condition_name="Acute Stroke",
        chief_complaint="Sudden onset neurological deficit",
        clinical_setting="ED",
        special_populations="Pregnant, Pediatric, Elderly",
        evidence_context="- PMID 12345678: Stroke Guidelines 2024 | Abstract: Current recommendations..."
    )
    
    print("=== COMPREHENSIVE PATHWAY PROMPT ===")
    print(prompt[:2000] + "...")
    print("\n" + "="*80 + "\n")
    
    # Example: Build evidence context
    sample_evidence = [
        {"id": "12345678", "title": "Chest Pain Guidelines", "abstract": "This study examines..."},
        {"id": "87654321", "title": "HEART Score Validation", "abstract": "Retrospective analysis..."}
    ]
    context = build_evidence_context(sample_evidence)
    print("=== EVIDENCE CONTEXT ===")
    print(context)
