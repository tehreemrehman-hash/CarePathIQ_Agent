# Quick Reference: Decision Science Logic in CarePathIQ

## What Changed?

Your decision science prompts were **greatly amplified** to prevent oversimplification. The system now:

1. **Generates 25-40+ nodes** instead of 5-10 (richer complexity)
2. **Enforces benefit/harm trade-offs** at every Decision node
3. **Requires evidence citations** (PMIDs) on clinical steps
4. **Validates DAG structure** (no circular logic)
5. **Checks for all 4 clinical stages** (Initial Eval → Diagnosis → Re-evaluation → Disposition)
6. **Preserves complexity during refinement** (never simplifies without warning)

---

## How to Get the Best Pathways

### ✓ DO This

**Generous with specificity:**
- "Include vague, mysterious presentations and rare diagnoses"
- "Add edge cases: pregnancy, elderly, immunocompromised, renal failure"
- "Include specific medication doses and regimens"
- "Explain benefit/harm trade-offs for each major decision"

**Reference real complexity:**
- "What does a real chest pain workup look like in the ED?"
- "How do you actually manage sepsis? Show me the escalation pathway."
- "Include de-escalation: when do you step down from ICU care?"

**Request metric improvements:**
- "Increase evidence coverage—cite PMIDs for each major step"
- "Add more decision branches for different risk groups"
- "Expand the re-evaluation stage with monitoring criteria"

### ❌ DON'T Do This

**Requests that will trigger warnings:**
- "Simplify this pathway" (Will be interpreted as "make clearer", not "remove branches")
- "Make it shorter" (System will preserve or expand complexity)
- "Reduce the number of decision points" (Explicitly prevented)

**These won't work:**
- Asking for oversimplification gets flagged
- Collapsing distinct pathways triggers validation warnings
- Removing edge cases alerts the user

---

## Understanding the Validation Output

When you generate or refine a pathway, you might see metrics like:

```
Complexity Assessment:
  ✓ Node count: 28 (comprehensive)
  ⚠️ Evidence coverage: 60% (add more PMIDs)
  ✓ Clinical stages: All 4 represented
  ✓ Decision divergence: Good (branches stay separate)

Integrity Check:
  ✓ DAG structure: Valid (no cycles)
  ✓ Terminal End nodes: All pathways end properly
  ✓ No "or" logic: Clean decision structure
  ⚠️ Benefit/harm: Add trade-off annotations to 2 more decisions
  ✓ Evidence cited: Good coverage (15 PMIDs)

Recommendations:
  - Consider adding edge case: pregnant patients with sepsis
  - Re-evaluation stage could include de-escalation criteria
  - Overall quality: 0.85/1.0 (very good)
```

---

## Examples

### Example 1: Good Complexity
✓ **Chest Pain Management (28 nodes)**
- Initial Evaluation (vitals, EKG, troponin)
- Decision 1: EKG shows STEMI? → Yes→Cath lab | No→Continue
- Decision 2: Troponin elevated? → Yes→ACS pathway | No→Low-risk
- Decision 3: Patient stable x 6h? → Yes→Discharge | No→Admit
- Re-evaluation (serial troponin, monitoring criteria)
- Disposition (specific prescriptions, follow-up timing)

Metrics:
- Nodes: 28 ✓
- Decisions: 4 ✓
- Evidence: 12 PMIDs ✓
- Stages: All 4 ✓
- Quality: 0.92/1.0

### Example 2: Oversimplified (Will Warn)
❌ **Chest Pain (5 nodes)**
- Start: patient with chest pain
- Process: assess vitals
- Decision: is patient unstable?
- Process: resuscitate
- End: admit to ICU

Metrics:
- Nodes: 5 ❌ (should be 20+)
- Decisions: 1 ❌ (should be 3-5)
- Evidence: 0 ❌ (should be 30%+)
- Stages: 2/4 ❌ (missing diagnosis, re-evaluation)
- Quality: 0.35/1.0 ⚠️

**System response:** 
> "⚠️ Pathway may be oversimplified. Consider adding:
> - More decision branches for different presentations
> - Evidence citations (PMIDs) for clinical steps
> - Missing clinical stages: Diagnosis/Treatment, Re-evaluation"

---

## Decision Science Framework Used

The system enforces **Medical Decision Analysis** principles:

### CGT/Ad/it Principles
✓ **Explicit decision structure:** Each Decision node has clear branches
✓ **Separate structure from content:** Node type determines flow, labels provide details
✓ **DAG-only pathways:** No cycles, clear escalation flow

### Benefit/Harm Trade-offs
Every Decision node should annotate:
- **Benefit:** Why this decision matters (e.g., "Early intervention reduces mortality")
- **Harm:** What's the risk (e.g., "Unnecessary procedures, ICU admission costs")
- **Threshold:** When to choose each branch (e.g., "If troponin >99th percentile")

### Four Clinical Stages
1. **Initial Evaluation:** Presentation, vitals, early assessment
2. **Diagnosis & Treatment:** Diagnostic workup, therapeutic interventions
3. **Re-evaluation:** Monitoring, response to treatment, adjustment of therapy
4. **Final Disposition:** Discharge, admit, transfer, follow-up

### Evidence-Based
- Clinical steps cite PMIDs when available
- Thresholds and criteria come from literature
- Drug doses and regimens match current guidelines

---

## Common Prompts That Work Well

| Your Request | System Does |
|--------------|------------|
| "Add edge cases for special populations" | Expands to 30-40+ nodes with branches for elderly, pregnant, renal failure, etc. |
| "Include specific medication doses" | Converts "treat infection" → "Vancomycin 15-20 mg/kg IV q8-12h + meropenem 1g IV q8h" |
| "Show the escalation pathway" | Creates sequence: ED → Observation → ICU with clear triggers for each step |
| "What's the de-escalation?" | Adds branches for stepping down: "Stable x 24h → step down from ICU → discharge" |
| "Explain the decision logic" | Annotates each Decision with benefit/harm trade-off and threshold |
| "Cite the evidence" | Adds PMIDs to nodes: "PMID 35739876: Cardiac troponin for ACS" |

---

## If Your Pathway Is Still Too Simple...

**Step 1:** Check the metrics
- Node count < 20? → Ask for more edges cases and branches
- Evidence coverage < 30%? → Ask for PMIDs on each step
- Missing stages? → Ask which ones and request expansion
- No trade-offs? → Ask to document benefit/harm at decisions

**Step 2:** Specific refinement requests
```
"The pathway for diagnosis/treatment is too brief. 
Expand it to include:
- Differential diagnosis tree (what rules in/out each condition?)
- Edge cases (pregnant, immunocompromised, elderly)
- Specific medications with doses
- Evidence citations from literature
Add at least 10 more nodes to this section."
```

**Step 3:** Iterate
Each refinement should increase (or preserve) complexity while improving clarity.

---

## Summary

🎯 **The goal:** Pathways reflect real clinical decision-making with appropriate complexity

✅ **The system now:**
- Generates rich, detailed pathways (25-40+ nodes)
- Enforces decision science framework
- Validates complexity and integrity
- Warns if simplification occurs
- Helps you identify gaps

📈 **Your role:**
- Request specific improvements
- Review metrics to understand gaps
- Refine iteratively
- Build pathways that real clinicians will use

---

**Questions?** See [DECISION_SCIENCE_RESTORATION.md](DECISION_SCIENCE_RESTORATION.md) for technical details.
