# CarePathIQ AI Prompts and Literature References

**Document Version:** 1.1  
**Last Updated:** January 3, 2026  
**Changelog:**
- **v1.1** (2026-01-03): Enhanced Phase 3 prompts with sophisticated clinical patterns extracted from real-world DVT/PE pathways
  - Added validated risk stratification requirements (Wells', PERC, YEARS, PESI scores)
  - Added special population handling (pregnancy screening, contraindications, age adjustments)
  - Added resource availability contingencies and alternative pathways
  - Added medication specificity requirements (brand+generic, exact dosing, insurance considerations)
  - Added explicit follow-up pathway requirements with virtual care alternatives
  - Added educational content integration guidance (score calculators, evidence citations)
  - Enhanced all Phase 3 prompts: Initial generation, Refinement, and Organization (>20 nodes)
- **v1.0** (2026-01-03): Initial documentation of AI prompts and literature references

---

## Overview

This document details the AI prompting strategies and academic/industry references used in CarePathIQ's clinical pathway development workflow, specifically for **Phase 3 (Decision Tree)** and **Phase 4 (Usability Heuristics)**.

---

## Sophisticated Clinical Pattern Extraction (v1.1)

**Source**: Real-world DVT (Deep Vein Thrombosis) and PE (Pulmonary Embolism) clinical pathways from 10_24_25 documentation

**Important**: These are **universal clinical design patterns**, not DVT/PE-specific requirements. The DVT/PE examples below illustrate HOW to apply each pattern—the AI adapts these principles to whatever clinical condition is being developed.

**15 Universal Patterns with DVT/PE Examples**:

1. **Validated Risk Scores with Thresholds** [UNIVERSAL PATTERN]
   - Pattern: Use published, validated clinical prediction scores BEFORE testing with specific numerical cutoffs
   - DVT/PE Examples: Wells' Criteria (≤1 low, 2-6 intermediate, ≥7 high), PERC rule, YEARS score, PESI score
   - Apply to Other Conditions: HEART score (chest pain), GRACE score (ACS), NIHSS (stroke), qSOFA (sepsis), etc.

2. **Age-Adjusted Calculations** [UNIVERSAL PATTERN]
   - Pattern: Apply population-specific or age-adjusted thresholds where established in literature
   - DVT/PE Example: D-dimer cutoff = age × 10 for patients >50 years
   - Apply to Other Conditions: Age-adjusted reference ranges, pediatric vs. geriatric dosing adjustments

3. **Special Population Screening** [UNIVERSAL PATTERN]
   - Pattern: Screen for high-risk populations EARLY before exposing to risks
   - DVT/PE Example: Pregnancy check (bHCG/Urine) BEFORE radiation imaging (CT, X-ray)
   - Apply to Other Conditions: Renal function before contrast/NSAIDs, pregnancy before teratogens, immunosuppression status

4. **Contraindication Checks** [UNIVERSAL PATTERN]
   - Pattern: Explicit "Absolute contraindications?" decision nodes BEFORE treatment initiation
   - DVT/PE Example: "Absolute contraindications to anticoagulation?" before starting blood thinners
   - Apply to Other Conditions: Check before thrombolytics, before steroids, before live vaccines, etc.

5. **Resource Availability Contingencies** [UNIVERSAL PATTERN]
   - Pattern: "If preferred test/procedure NOT available → Alternative pathway"
   - DVT/PE Example: "If ultrasound NOT available → Hold/Transfer/One-time dose and return"
   - Apply to Other Conditions: If CT unavailable, if specialist unavailable, if equipment unavailable

6. **Bed Availability Considerations** [UNIVERSAL PATTERN]
   - Pattern: Disposition decisions based on resource constraints
   - DVT/PE Example: "ED Observation bed available?" → YES/NO with distinct pathways
   - Apply to Other Conditions: ICU bed availability, telemetry bed availability, transfer to specialty center

7. **Medication Brand + Generic Specificity** [UNIVERSAL PATTERN]
   - Pattern: Always include both brand AND generic names for commonly prescribed medications
   - DVT/PE Examples: "Apixaban (Eliquis)", "Rivaroxaban (Xarelto)", "Enoxaparin (Lovenox)"
   - Apply to Other Conditions: Any frequently prescribed drug (e.g., "Lisinopril (Zestril)", "Metoprolol (Lopressor)")

8. **Exact Dosing Protocols** [UNIVERSAL PATTERN]
   - Pattern: "X mg [route] [frequency] × duration (total quantity)"
   - DVT/PE Example: "10 mg PO BID × 7 days, then 5 mg PO BID (74 tablets total)"
   - Apply to Other Conditions: Always specify exact dose, route, frequency, duration for ANY medication

9. **Administration Details** [UNIVERSAL PATTERN]
   - Pattern: Specify timing, location, and population-specific considerations
   - DVT/PE Examples: "Give first dose in ED", "Preferred for CKD/ESRD", "Prescribe starter pack"
   - Apply to Other Conditions: "Administer within 30 min", "Preferred for elderly", "Adjust for renal function"

10. **Insurance/Cost Handling** [UNIVERSAL PATTERN]
    - Pattern: Address cost barriers to adherence
    - DVT/PE Example: "Ensure Rx covered by insurance; provide Apixaban coupon link if needed"
    - Apply to Other Conditions: Generic alternatives, patient assistance programs, cost-effective options

11. **Follow-Up Timing Specificity** [UNIVERSAL PATTERN]
    - Pattern: "[Provider type] follow-up within [specific timeframe]"
    - DVT/PE Examples: "PCP within 2 weeks", "OBGYN follow-up" (pregnant), "Vascular Surgery Referral"
    - Apply to Other Conditions: "Cardiology within 1 week", "Wound check in 48 hours", etc.

12. **Virtual Care Alternatives** [UNIVERSAL PATTERN]
    - Pattern: Provide telehealth backup when in-person follow-up unavailable
    - DVT/PE Example: "If unable to follow-up with PCP, advise Virtual Urgent Care"
    - Apply to Other Conditions: Any discharge requiring follow-up—always provide virtual alternative

13. **Educational Hyperlinks** [UNIVERSAL PATTERN]
    - Pattern: Note opportunities for interactive clinical tools, drug info, evidence citations
    - DVT/PE Examples: "Wells' score calculator", "YEARS score documentation", drug information links
    - Apply to Other Conditions: HEART score calculator, medication guides, disease-specific education

14. **Risk-Level Color Coding** [UNIVERSAL PATTERN]
    - Pattern: Tag nodes with risk levels for visual optimization
    - DVT/PE Example: Green (discharge/low-risk), Yellow (intermediate), Pink/Red (high-risk/admit)
    - Apply to Other Conditions: Any pathway benefits from color-coded risk stratification

15. **Visual Design Cues** [UNIVERSAL PATTERN]
    - Pattern: Mark special node types for UI enhancement
    - DVT/PE Examples: [Info] boxes, [Contraindication] alerts, [Special Population] branches
    - Apply to Other Conditions: [Alert], [Warning], [Calculation], [Educational] tags as appropriate

**How AI Applies These**: When generating a pathway for ANY condition (sepsis, MI, stroke, trauma, etc.), the AI identifies which patterns are relevant and adapts the examples above to that specific clinical context. Wells' score becomes GRACE score for ACS, anticoagulation becomes thrombolytics for stroke, etc.

---

## Phase 3: Decision Tree Generation

### Literature & Framework References

#### 1. **Medical Decision Analysis (MDA)**
- **Primary Citation**: Dobler, C. C., et al. (2021). "Users' Guide to Medical Decision Analysis." *Mayo Clinic Proceedings*, [specific details to be verified]
- **Application in CarePathIQ**:
  - Make decision/chance/terminal flows EXPLICIT through directed acyclic graph (DAG) structure
  - Trade off benefits vs. harms at every decision point with evidence-backed rationales
  - Use evidence-based probabilities and utilities to guide branching
- **Location in Code**: Line 3882-3886 (streamlit_app.py)

#### 2. **CGT/Ad/it Principles**
- **Full Name**: Clinical Guidelines Theory / Advocacy / Iterative Development
- **Core Concept**: Explicit decision structure that separates content from form
- **Application in CarePathIQ**:
  - Separate clinical decision logic (nodes, branches) from presentation (visualization)
  - Allow iterative refinement without destroying underlying structure
  - Maintain formal decision-tree representation
- **Location in Code**: Line 3881 (streamlit_app.py)

#### 3. **GRADE (Grading of Recommendations Assessment, Development and Evaluation)**
- **Standard**: International evidence quality assessment framework
- **Levels Used**:
  - **High (A)**: Further research very unlikely to change confidence in estimate
  - **Moderate (B)**: Further research likely to have important impact on confidence
  - **Low (C)**: Further research very likely to have important impact
  - **Very Low (D)**: Any estimate of effect is very uncertain
- **Application in CarePathIQ**:
  - Auto-grades Phase 2 evidence using Gemini API with GRADE criteria
  - Evidence quality ratings feed into Phase 3 decision tree generation
  - PMIDs with abstracts and GRADE ratings inform node recommendations
- **Location in Code**: Lines 1468-1499 (auto_grade_evidence_list function)

#### 4. **Evidence-Based Medicine Principles**
- **Application**: All decision nodes should cite supporting evidence (PMIDs) when available
- **Constraint**: "Do NOT hallucinate PMIDs—use 'N/A' if no supporting evidence"
- **Integration**: Phase 2 PubMed search results (up to 20 articles with abstracts) feed directly into Phase 3 prompts

---

### Phase 3 AI Prompts

#### **Prompt 1: Initial Auto-Generation**
**Location**: Lines 3875-4040 (streamlit_app.py)

**Role Assignment**:
```
"Act as a CLINICAL DECISION SCIENTIST with expertise in Medical Decision Analysis and evidence-based medicine."
```

**Input Context**:
- **Phase 1 Data**: Clinical condition + care setting
- **Phase 2 Evidence**: Up to 20 PubMed articles (PMID + Title + Abstract [200 chars] + GRADE rating)

**Framework References**:
- CGT/Ad/it principles (explicit decision structure)
- Dobler et al. Medical Decision Analysis guide (Mayo Clinic Proceedings 2021)
- Evidence-based probabilities and utilities

**Sophisticated Pathway Elements** (NEW v1.1):
1. **Validated Risk Stratification**: Clinical scores BEFORE tests with specific thresholds (Wells' ≤1, 2-6, ≥7; PERC; YEARS; PESI)
2. **Special Population Handling**: Pregnancy screening (bHCG/Urine), contraindications, age/renal adjustments
3. **Resource Availability Contingencies**: Alternative pathways when preferred test/procedure unavailable
4. **Medication Specificity**: Brand + generic names, exact dosing, route, timing, administration location
   - Example: "Apixaban (Eliquis): 10 mg PO BID × 7d, then 5 mg PO BID. Give first dose in ED."
5. **Insurance/Cost Considerations**: "Ensure Rx covered by insurance; provide coupon link if needed"
6. **Follow-Up Pathways**: Specific timing, provider types, virtual care alternatives
   - Example: "PCP within 2 weeks; if unavailable → Virtual Urgent Care"
7. **Educational Content Integration**: Note hyperlink candidates (score calculators, drug info, evidence citations)

**Required Clinical Coverage** (4 mandatory stages with enhanced specificity):
1. **Initial Evaluation**: Chief complaint, vitals, exam, validated risk scores, age-adjusted thresholds, special population screening, early workup
2. **Diagnosis and Treatment**: Differential dx, resource contingencies, contraindication checks BEFORE treatment, exact medication details (brand/generic, dosing, route, location, insurance), risk-benefit, edge cases
3. **Re-evaluation**: Monitoring, response assessment, escalation/de-escalation, bed availability considerations
4. **Final Disposition**: Discharge instructions, explicit follow-up with timing/provider/virtual alternatives, educational content, admit/transfer criteria, return precautions

**Output Structure**:
```json
{
  "type": "Start" | "Decision" | "Process" | "End",
  "label": "Concise clinical step with medical abbreviations",
  "evidence": "PMID or N/A",
  "detail": "(optional) Extended rationale or threshold"
}
```

**Key Constraints**:
1. **Decision Divergence**: Every Decision creates distinct branches that don't reconverge
2. **Terminal End Nodes**: No content after End; each outcome gets own End node
3. **Evidence-Backed**: Cite PMIDs from Phase 2 evidence list
4. **DAG Structure**: No cycles; escalation moves forward only
5. **Complexity and Specificity**: Build comprehensive pathway (15-40 nodes) with:
   - ALL special populations and edge cases (pregnancy, renal failure, allergies, age extremes)
   - Never vague—always specific medications, tests, thresholds, timing
   - Resource availability branches with explicit alternatives
   - Clinical score thresholds with numerical cutoffs
6. **Actionability and Clinical Realism**: Every node represents real-time clinical action
7. **Visual Design Cues**: Indicate risk levels, informational boxes, hyperlink candidates, resource dependencies
6. **Specificity**: Use exact medications with doses/routes, not vague terms

---

#### **Prompt 2: Auto-Enhancement (Minimal Pathways)**
**Location**: Lines 4043-4075 (streamlit_app.py)

**Trigger**: When pathway has <15 nodes and complexity_level == 'minimal'

**Instruction**:
```
"EXPAND this into a comprehensive clinical decision pathway (25-35+ nodes) that covers:
1. Initial Evaluation (vitals, exam, initial workup)
2. Diagnosis/Treatment (diagnostic tests, medications with doses, interventions)
3. Re-evaluation (monitoring, response assessment, escalation criteria)
4. Final Disposition (discharge instructions, admit criteria, transfer criteria)

Add decision branches, edge cases, and specific clinical details. DO NOT simplify—EXPAND."
```

**Purpose**: Prevent over-simplification; ensure clinical completeness

---

#### **Prompt 3: User Refinement**
**Location**: Lines 93-175 (regenerate_nodes_with_refinement function)

**Role Assignment**:
```
"Act as a CLINICAL DECISION SCIENTIST. Refine the EXISTING pathway based on the user's request."
```

**Critical Directive**:
```
"Apply refinements while PRESERVING and potentially ENHANCING clinical complexity."
```

**Mandatory Preservation Rules**:
1. **Decision Science Framework**: Keep CGT/Ad/it + MDA principles intact
2. **Decision Divergence**: Don't collapse multiple branches
3. **Clinical Coverage**: All 4 stages must remain; EXPAND specificity:
   - Validated clinical scores with thresholds (Wells', PERC, YEARS, PESI)
   - Age-adjusted calculations (e.g., "D-dimer = age × 10 if >50")
   - Special population screening (pregnancy, renal function, contraindications)
   - Medication specificity: Brand + generic, exact dosing, timing, route, location
   - Insurance/cost considerations with coupon links
   - Resource contingencies (alternatives when preferred unavailable)
   - Follow-up timing with virtual care alternatives
4. **Enhance Depth**: Add detail, don't remove branches
5. **DAG Structure**: No cycles
6. **Sophisticated Clinical Realism** (NEW v1.1):
   - Risk stratification using validated scores BEFORE tests
   - Explicit contraindication checks BEFORE treatment
   - Resource availability branches with specified alternatives
   - Educational content notation (hyperlink candidates)
   - Specific disposition with follow-up provider, timing, alternatives

**Context Provided**:
- Current nodes (full JSON)
- Phase 2 evidence (PMID + Title + Abstract)
- User's refinement request (free text)
- Optional: Phase 4 heuristics recommendations

**Special Instruction**:
```
"If user asks to 'simplify,' interpret as 'make more understandable' (clearer labels, better organization)—NOT 'remove clinical branches' or reduce node count."
```

**Output Requirement**:
```
"Apply sophisticated patterns above to make pathway immediately implementable by clinicians."
```

---

#### **Prompt 4: Pathway Organization (>20 nodes)**
**Location**: Lines 4193-4228 (streamlit_app.py)

**Trigger**: When pathway has >20 nodes

**Instruction**:
```
"Re-organize for better clarity and structure.
Requirements:
- Preserve ALL existing nodes and clinical content—DO NOT reduce complexity or remove nodes
- Group logically into clear clinical stages (Initial Evaluation, Risk Stratification, Diagnosis, Treatment, Disposition)
- Apply sophisticated clinical patterns to enhance clarity and implementability:
  * Validated clinical scores: Ensure thresholds explicit (Wells' ≤1, 2-6, ≥7)
  * Special populations: Ensure pregnancy checks, contraindications, age adjustments clearly labeled
  * Medication specificity: Use brand AND generic with exact dosing where present
  * Resource contingencies: Clearly label alternative pathways when resources unavailable
  * Follow-up instructions: Ensure specific timing and provider types in End nodes
  * Risk level indicators: Add [Low Risk], [High Risk], [Alert], [Info] tags where appropriate
- Improve label clarity using standard medical abbreviations while maintaining clinical precision
- Maintain complete clinical flow with all decision branches—no merging or eliminating edge cases
- Preserve evidence citations; keep all edge cases organized into labeled subsections
- GOAL: More readable organization, NOT fewer clinical considerations"
```

**Purpose**: Improve large pathway readability while preserving comprehensive clinical decision-making

**New Enhancement (v1.1)**: Added explicit sophisticated patterns from real-world pathways to ensure organization improves implementability without sacrificing clinical depth
- Group logically into clear sections
- Improve label clarity using standard medical abbreviations
- Maintain complete clinical flow with all decision branches
- Keep all edge cases and special population considerations"
```

**Purpose**: Improve organization and readability without reducing clinical content

---

## Phase 4: Usability Heuristics Analysis

### Literature & Framework References

#### **Nielsen's 10 Usability Heuristics**
- **Primary Source**: Jakob Nielsen, Nielsen Norman Group
- **Standard**: Industry-standard UI/UX evaluation framework
- **Original Publication**: Nielsen, J. (1994). "Enhancing the explanatory power of usability heuristics." *Proceedings of the SIGCHI conference on Human Factors in Computing Systems (CHI '94)*, 152-158.
- **Application in CarePathIQ**: Applied to clinical pathway interface design

**The 10 Heuristics**:
1. **H1**: Visibility of system status
2. **H2**: Match between system and real world
3. **H3**: User control and freedom
4. **H4**: Consistency and standards
5. **H5**: Error prevention
6. **H6**: Recognition rather than recall
7. **H7**: Flexibility and efficiency of use
8. **H8**: Aesthetic and minimalist design
9. **H9**: Help users recognize, diagnose, and recover from errors
10. **H10**: Help and documentation

**CarePathIQ Classification**:
- **Pathway-Modifiable** (H2, H4, H5): Can be addressed by changing pathway structure/content
- **UI-Only** (H1, H3, H6-H10): Addressed through interface design, not pathway content

---

### Phase 4 AI Prompts

#### **Prompt 1: Auto-Generate Heuristics Analysis**
**Location**: Lines 4456-4472 (streamlit_app.py)

**Task**:
```
"Analyze the following clinical decision pathway for Nielsen's 10 Usability Heuristics.
For each heuristic (H1-H10), provide a specific, actionable critique and suggestion in 2-3 sentences."
```

**Input**: First 10 nodes of pathway (to avoid token overflow)

**Output Format**:
```json
{
  "H1": "The pathway lacks clear status indicators...",
  "H2": "Medical jargon should be...",
  ...
  "H10": "..."
}
```

**Purpose**: Provide usability recommendations for pathway improvement

---

## Key Design Principles

### 1. **Evidence Integration**
Phase 2 PubMed evidence (PMIDs, abstracts, GRADE ratings) directly feeds Phase 3 prompts, ensuring evidence-based pathway generation.

### 2. **Complexity Preservation**
Multiple safeguards prevent over-simplification:
- Auto-enhancement for minimal pathways
- Refinement prompts emphasize "EXPAND, not reduce"
- Organization prompts preserve all clinical content
- No arbitrary node count limits

### 3. **No Citation Hallucination**
Explicit instruction: "Do NOT hallucinate PMIDs—use 'N/A' if no supporting evidence in list"

### 4. **Clinical Realism**
- Every node represents real-time clinical action or decision
- Specific medications with doses/routes
- Realistic decision points with thresholds
- Edge cases and special populations included

### 5. **Decision Science Foundation**
Explicitly references Mayo Clinic Proceedings 2021 paper (Dobler et al.) for Medical Decision Analysis principles, ensuring formal decision-tree structure.

---

## References for Further Reading

1. **Dobler, C. C., et al.** (2021). "Users' Guide to Medical Decision Analysis." *Mayo Clinic Proceedings*. [Verify exact citation]

2. **Nielsen, J.** (1994). "Enhancing the explanatory power of usability heuristics." *Proceedings of the SIGCHI conference on Human Factors in Computing Systems (CHI '94)*, 152-158.

3. **GRADE Working Group.** (2004). "Grading quality of evidence and strength of recommendations." *BMJ*, 328(7454), 1490.

4. **Guyatt, G. H., et al.** (2008-2011). "GRADE series." *Journal of Clinical Epidemiology* (multiple articles).

5. **Pauker, S. G., & Kassirer, J. P.** (1987). "Decision analysis." *New England Journal of Medicine*, 316(5), 250-258.

---

## Version History

- **v1.1** (January 3, 2026): Enhanced prompts with sophisticated clinical patterns
  - Extracted 15 specific patterns from real-world DVT/PE pathways
  - Enhanced Phase 3 Initial Generation prompt with validated risk scores, special populations, resource contingencies, medication specificity, follow-up pathways, educational content
  - Enhanced Phase 3 Refinement prompt with same sophisticated patterns
  - Enhanced Phase 3 Organization (>20 nodes) prompt with clinical staging and pattern application
  - Added comprehensive "Sophisticated Clinical Pattern Extraction" section documenting all patterns
  - Line number updates throughout to reflect expanded code

- **v1.0** (January 3, 2026): Initial documentation
  - Removed prescriptive benefit-harm framework requirement
  - Removed prescriptive 30+ node preference
  - Clarified >20 node feature as organization (not reduction)
  - Added comprehensive literature references

---

**End of Document**
