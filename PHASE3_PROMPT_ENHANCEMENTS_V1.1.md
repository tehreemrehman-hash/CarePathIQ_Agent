# Phase 3 AI Prompt Enhancements v1.1

**Date:** January 3, 2026  
**Enhancement Type:** Sophisticated Clinical Pattern Integration  
**Source:** Real-world DVT/PE Pathway Analysis

---

## Summary

Enhanced all Phase 3 AI prompts with sophisticated clinical patterns extracted from your DVT (Deep Vein Thrombosis) and PE (Pulmonary Embolism) pathway screenshots. These patterns represent best-practice clinical decision-making that produces immediately implementable pathways.

---

## Extracted Patterns from DVT/PE Pathways

### 1. **Validated Risk Stratification**
**What we saw:** Wells' Criteria scores with specific thresholds (≤1 low-risk, 2-6 intermediate, ≥7 high-risk), YEARS score, PERC rule, PESI score (86-105, >105)

**Now in prompts:**
- "Validated clinical prediction scores (e.g., Wells' ≤1, 2-6, ≥7 for DVT; PERC for PE; PESI for severity)"
- "Use validated scores BEFORE diagnostic tests (not generic 'assess risk')"
- "Clinical score thresholds with numerical cutoffs"

### 2. **Age-Adjusted Calculations**
**What we saw:** D-dimer cutoff = age × 10 for patients >50 years

**Now in prompts:**
- "Age-adjusted or population-specific thresholds (e.g., 'D-dimer = age × 10 if >50 years')"

### 3. **Special Population Screening EARLY**
**What we saw:** "Is the patient pregnant?" decision node early in pathway, bHCG/Urine testing before radiation imaging

**Now in prompts:**
- "Special population screening EARLY (pregnancy check via bHCG/Urine before radiation imaging, renal function before contrast)"
- "Special populations: Ensure pregnancy checks, contraindications, age adjustments clearly labeled"

### 4. **Contraindication Checks BEFORE Treatment**
**What we saw:** "Absolute contraindications to anticoagulation" box BEFORE treatment initiation

**Now in prompts:**
- "Contraindication checks BEFORE treatment initiation (e.g., 'Absolute contraindications to anticoagulation')"
- "Explicit contraindication checks BEFORE treatment"

### 5. **Resource Availability Contingencies**
**What we saw:** "If ultrasound NOT available → Hold anticoagulation, Transfer to facility with imaging, OR Give one-time therapeutic dose"

**Now in prompts:**
- "Resource availability contingencies: 'If preferred test unavailable → Alternative pathway'"
- "Resource availability branches: 'ED Observation bed available?', 'Ultrasound available now?'"
- "Resource contingencies: Clearly label alternative pathways when resources unavailable"

### 6. **Medication Specificity (Brand + Generic)**
**What we saw:** 
- "Apixaban (Eliquis) - Give first dose in ED"
- "Rivaroxaban (Xarelto) - Preferred for CKD or ESRD"
- "Enoxaparin (Lovenox)"

**Now in prompts:**
- "Brand AND generic names: 'Apixaban (Eliquis)', 'Rivaroxaban (Xarelto)', 'Enoxaparin (Lovenox)'"
- "Medication specificity: Use brand AND generic with exact dosing where present"

### 7. **Exact Dosing Protocols**
**What we saw:** "10 mg twice daily for 7 days followed by 5 mg twice daily (74 tablets)"

**Now in prompts:**
- "Exact dosing: '10 mg PO twice daily × 7 days, then 5 mg PO twice daily (74 tablets total)'"
- "Never vague—always specific medications, tests, thresholds, timing"

### 8. **Administration Details**
**What we saw:** "Give first dose in ED", "Preferred for CKD/ESRD", "Prescribe starter pack"

**Now in prompts:**
- "Administration details: 'Give first dose in ED', 'Preferred for CKD/ESRD', 'Prescribe starter pack'"

### 9. **Insurance and Cost Considerations**
**What we saw:** "Ensure Rx is covered by patient's insurance" + hyperlinked coupon references (Apixaban coupon, Rivaroxaban coupon)

**Now in prompts:**
- "Insurance/cost considerations: 'Ensure Rx covered by patient's insurance' + coupon links where applicable"
- "Insurance/cost considerations with coupon links"

### 10. **Follow-Up Pathway Specificity**
**What we saw:** 
- "PCP follow-up within 2 weeks"
- "OBGYN follow-up" (for pregnant patients)
- "Vascular Surgery Referral"

**Now in prompts:**
- "EXPLICIT follow-up pathways with timing and provider type: 'PCP follow-up within 2 weeks', 'OBGYN follow-up', 'Vascular Surgery Referral'"
- "Follow-up instructions: Ensure specific timing and provider types in End nodes"

### 11. **Virtual Care Alternatives**
**What we saw:** "If unable to follow-up with PCP advise patient to follow-up with Virtual Urgent Care"

**Now in prompts:**
- "Virtual care alternatives: 'If unable to follow-up with PCP, advise Virtual Urgent Care'"
- "Follow-up timing with virtual care alternatives"

### 12. **Educational Content Integration**
**What we saw:** Hyperlinked text for "Wells' score documentation", "YEARS score documentation", "Calculate Wells' Criteria for PE"

**Now in prompts:**
- "Educational content integration: Score calculators, evidence citations, patient resources"
- "Educational content notation (hyperlink candidates)"
- "Suggest hyperlink candidates: validated scores, drug information, evidence citations"

### 13. **Bed Availability Considerations**
**What we saw:** "ED Observation if available, Medicine/SDU/MICU admission, Dispo navigator"

**Now in prompts:**
- "Bed availability considerations: 'ED Observation if available, else Medicine/SDU/MICU admit or Dispo navigator'"

### 14. **Risk Level Indicators**
**What we saw:** Color-coded end nodes (green for discharge/low-risk, yellow for intermediate, pink for high-risk/admit)

**Now in prompts:**
- "Indicate risk levels for color coding: [Low Risk], [Intermediate Risk], [High Risk], [Alert/Critical]"
- "Risk level indicators: Add [Low Risk], [High Risk], [Alert], [Info] tags where appropriate"

### 15. **Informational Boxes**
**What we saw:** Blue information boxes for contraindications, special populations, educational content

**Now in prompts:**
- "Mark informational boxes: [Info], [Contraindication], [Special Population]"

---

## Prompts Enhanced

### ✅ Phase 3 Initial Generation Prompt
**File:** [streamlit_app.py](streamlit_app.py)  
**Lines:** ~3875-4040 (expanded from 3875-3980)

**Enhancements:**
1. Added new "Sophisticated Pathway Elements" section with all 15 patterns
2. Expanded "Required Clinical Coverage" with specific pattern applications
3. Enhanced "Complexity and Specificity" constraint with examples
4. Added explicit "Actionability and Clinical Realism" guidance
5. Added "Visual Design Cues" section for Phase 4 optimization

**Result:** AI now generates pathways with validated scores, special population branches, resource contingencies, exact medication protocols, follow-up specificity, and educational content markers from the start.

---

### ✅ Phase 3 Refinement Prompt
**File:** [streamlit_app.py](streamlit_app.py)  
**Lines:** 93-175 (regenerate_nodes_with_refinement function)

**Enhancements:**
1. Expanded "Preserve Clinical Coverage" rule #3 with specific pattern applications
2. Added new "Sophisticated Clinical Realism" rule #6 with implementation guidance
3. Added output requirement: "Apply sophisticated patterns above to make pathway immediately implementable by clinicians"

**Result:** When users refine pathways, AI now applies the same sophisticated patterns—adding risk scores, contraindication checks, medication specificity, resource contingencies, and follow-up details while preserving all clinical branches.

---

### ✅ Phase 3 Organization Prompt (>20 nodes)
**File:** [streamlit_app.py](streamlit_app.py)  
**Lines:** ~4193-4228 (previously 4113-4132)

**Enhancements:**
1. Added explicit "Apply sophisticated clinical patterns" section with 6 bullet points
2. Changed goal from "clear sections" to "clear clinical stages" (Initial Evaluation, Risk Stratification, Diagnosis, Treatment, Disposition)
3. Added instruction to add risk level indicators [Low Risk], [High Risk], [Alert], [Info]
4. Emphasized: "GOAL: More readable organization, NOT fewer clinical considerations"

**Result:** Large pathway reorganization now improves readability while actively applying sophisticated patterns—ensuring thresholds are explicit, special populations are clearly labeled, and resource contingencies are highlighted.

---

## Documentation Updates

### ✅ AI_PROMPTS_REFERENCES.md
**File:** [AI_PROMPTS_REFERENCES.md](AI_PROMPTS_REFERENCES.md)

**Changes:**
1. Updated version from 1.0 → 1.1
2. Added comprehensive changelog at document header
3. Added new "Sophisticated Clinical Pattern Extraction (v1.1)" section with all 15 patterns documented
4. Updated Phase 3 Prompt 1 section with new sophisticated elements
5. Updated Phase 3 Prompt 3 section with enhanced preservation rules
6. Updated Phase 3 Prompt 4 section with organization pattern details
7. Updated Version History at document end

**Purpose:** Comprehensive reference for understanding what patterns are embedded in prompts and why.

---

## Expected Outcomes

### When Generating New Pathways (Phase 3 Initial):
✅ Risk stratification using validated scores (Wells', PERC, YEARS, PESI) with thresholds  
✅ Pregnancy/special population screening EARLY before risky procedures  
✅ Contraindication checks BEFORE treatment initiation  
✅ Medication names with brand + generic, exact doses, timing, routes  
✅ Insurance considerations and coupon references where applicable  
✅ Resource unavailable contingencies (alternative pathways specified)  
✅ Bed availability branches (ED observation vs. admission)  
✅ Specific follow-up: timing, provider type, virtual care alternatives  
✅ Educational content markers for hyperlinks (score calculators, drug info)  
✅ Risk level tags for visual design ([Low Risk], [High Risk], [Alert])

### When Refining Pathways:
✅ User refinements applied while enhancing specificity with patterns above  
✅ "Simplify" requests interpreted as "organize better" NOT "remove branches"  
✅ Vague nodes replaced with specific validated scores, exact medications, clear alternatives

### When Organizing Large Pathways (>20 nodes):
✅ Better staging: Initial → Risk Stratification → Diagnosis → Treatment → Disposition  
✅ Thresholds made explicit in labels  
✅ Special populations clearly marked and organized  
✅ Resource contingencies highlighted  
✅ Risk level indicators added  
✅ NO reduction in clinical content—only improved readability

---

## Testing Recommendations

1. **Generate a new DVT pathway** and verify:
   - Wells' score with thresholds appears
   - Pregnancy check before D-dimer/imaging
   - Medications include brand + generic with exact dosing
   - Follow-up specifies "PCP within 2 weeks" or similar

2. **Refine existing pathway** with request like "add more detail on medications" and verify:
   - AI adds brand names, generics, exact doses, insurance considerations
   - Doesn't collapse clinical branches

3. **Trigger >20 node organization** and verify:
   - Pathway reorganized with clear stages
   - Risk level indicators added
   - Special populations clearly labeled
   - Node count unchanged (no clinical content removed)

---

## Files Modified

1. **streamlit_app.py** - Phase 3 prompts enhanced (3 locations)
2. **AI_PROMPTS_REFERENCES.md** - Comprehensive documentation updated

---

## Next Steps (Optional Future Enhancements)

### Phase 4 Heuristics Enhancement (Potential)
Could apply similar pattern extraction to Phase 4 usability analysis:
- Check for validated score usability
- Assess medication information clarity (brand/generic, dosing visible)
- Evaluate resource contingency visibility
- Assess follow-up instruction clarity
- Review educational content integration

**Recommendation:** Test v1.1 Phase 3 enhancements first to validate impact before extending to Phase 4.

---

**Status:** ✅ **COMPLETE** - All Phase 3 prompts enhanced with sophisticated clinical patterns from real-world pathways.
