# Visual Guide: Nielsen's Heuristics Fix

## The Problem Explained Visually

### Architecture Before (Broken)
```
┌──────────────────────────────────────────────────────────┐
│                  Nielsen's 10 Heuristics                 │
│  (UI/UX Design Principles for Evaluating Interfaces)     │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Apply each  │
                    │  separately  │
                    └──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │ Apply  │      │ Apply  │      │ Apply  │
    │  H1    │      │  H2    │      │  H3    │  ... (10 times)
    │(FAILS!)│      │(Works!)│      │(FAILS!)│
    └────────┘      └────────┘      └────────┘
        │                  │                  │
        ▼                  ▼                  ▼
   No change    Language update    No change
  (UI principle) (Pathway modified) (UI principle)

❌ Problem: LLM confused by "Apply UI principle to data"
❌ Hangs or returns invalid JSON
❌ User sees no changes
❌ No clear feedback
```

### Architecture After (Fixed)
```
┌──────────────────────────────────────────────────────────┐
│                  Nielsen's 10 Heuristics                 │
│  (UI/UX Design Principles for Evaluating Interfaces)     │
└──────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
        ┌──────────────┐      ┌──────────────┐
        │ CAN modify   │      │ UI design    │
        │ pathway      │      │ only (review)│
        └──────────────┘      └──────────────┘
                │                     │
                │                     │
        ┌───────┴────────┐          │
        ▼                ▼          ▼
       H2              H4,H5       H1,H3,H6-H10
    Language         Consistency   Status Visibility
    Clarity          Error Prev.   Control
                                   Recognition
    ┌─────────────────┐           Design
    │ Single LLM call │           Help
    │ (All 3 together)│           ...
    │                 │
    │ Clear prompt:   │
    │ "Simplify       │           ┌─────────────┐
    │  jargon +       │           │ REVIEW ONLY │
    │  standardize +  │           │ (No Apply)  │
    │  add alerts"    │           │             │
    └─────────────────┘           │ Show as:    │
            │                      │ - Blue boxes│
            ▼                      │ - No buttons│
    ┌──────────────┐               │ - Design    │
    │ UPDATED NODES│               │   guidance  │
    │              │               │ - Share with│
    │ • Clearer    │               │   design    │
    │ • Consistent │               │   team      │
    │ • Safe       │               └─────────────┘
    └──────────────┘

✅ Problem solved
✅ Clear expectations
✅ Works immediately
✅ Good user feedback
```

---

## Data Flow Comparison

### OLD FLOW (Broken)
```
User clicks "Apply" on H1
       │
       ▼
  Save history
       │
       ▼
  LLM prompt: "Apply visibility of system status to this pathway"
       │
       ▼ ❌ Confused - this is a UI principle, not a data modification
       │
       ├─→ Returns unchanged nodes
       │
       ├─→ Returns invalid JSON
       │
       └─→ Timeout/no response
              (UI HANGS)

Result: User clicks button, nothing happens, app loads forever ❌
```

### NEW FLOW (Fixed)
```
User clicks "Apply All Improvements"
       │
       ▼
  Save current nodes to history
       │
       ▼
  Collect H2, H4, H5 recommendations
       │
       ▼
  Build focused LLM prompt:
  ┌─────────────────────────────────────────────┐
  │ Apply these improvements to the pathway:    │
  │                                              │
  │ H2: Simplify medical jargon (MI→Heart Atk) │
  │ H4: Standardize terminology (all like this)│
  │ H5: Add safety alerts (check allergies!)   │
  │                                              │
  │ Return ONLY updated JSON nodes              │
  └─────────────────────────────────────────────┘
       │
       ▼ ✅ Clear, specific instructions
       │
       ▼
  LLM processes all 3 at once
       │
       ▼
  ✅ Returns valid JSON with:
     - Simplified labels
     - Consistent terminology
     - Safety warnings added
       │
       ▼
  Update session state
       │
       ▼
  Refresh visualization
       │
       ▼
  Show success message
  "✓ Applied pathway improvements"
       │
       ▼
  User sees nodes updated immediately
  "Undo" button becomes active

Result: User clicks button, sees results in 5-10 seconds ✅
```

---

## Clinical Pathway Structure: DAG with Escalation

All clinical pathways are **directed acyclic graphs (DAG)** - no loops or cycles allowed. This reflects real clinical practice:

### Why DAG-Only?
- **Clinical reality**: Treatments escalate (1st → 2nd → 3rd line), they don't cycle
- **Clear progression**: Each reassessment moves forward to next decision point
- **Explicit disposition**: After treatment attempts, pathway terminates with admission/discharge/transfer
- **Auditable**: Linear progression easier to review and validate

### Escalation Pattern (Not Loops)
When clinical reassessment is needed, model as **sequential decision branches**:

```
Initial assessment
  ├─ High risk → Admit immediately (Terminal)
  └─ Moderate risk → 1st line treatment
                     ├─ Response? → Discharge (Terminal)
                     └─ No response → Reassess symptoms (Decision)
                                      ├─ Stable → 2nd line treatment
                                      │           ├─ Response? → Discharge
                                      │           └─ No response → 3rd line
                                      │                          └─ Failed all → Admit
                                      └─ Deteriorating → Escalate to admission
```

### Node Types
- **Decision** (pink diamond): Branch point based on clinical criteria
- **Process** (light yellow box): Action, treatment, or assessment
- **Start/End** (light green oval): Entry and exit points

### Key Principle
If you're tempted to create a loop:
1. Ask: "Is this really escalation through treatment options?"
2. Model as: Decision → Treatment A → Reassess (Decision) → Treatment B → etc.
3. Always terminate with disposition (admit/discharge/transfer)

---

## UI Layout: Before vs After

### BEFORE (Confusing)
```
┌─ Nielsen's Heuristics Evaluation ────────────────────┐
│                                                        │
│  H1 - Visibility of system status [EXPAND]           │
│  Definition: Keep users informed about system status │
│  AI Recommendation:                                   │
│  "You need progress bars..."                          │
│  [✓ Apply]  [↶ Undo]    ← These don't work!         │
│                                                        │
│  H2 - Match between system and real world [EXPAND]   │
│  Definition: Speak the users' language                │
│  AI Recommendation:                                   │
│  "Use plain language instead of jargon..."            │
│  [✓ Apply]  [↶ Undo]    ← This works sometimes      │
│                                                        │
│  H3 - User control and freedom [EXPAND]              │
│  Definition: Provide emergency exits                  │
│  AI Recommendation:                                   │
│  "Add undo buttons to interface..."                   │
│  [✓ Apply]  [↶ Undo]    ← These don't work!         │
│                                                        │
│  ... (10 more times, all mixed together) ...         │
│                                                        │
└────────────────────────────────────────────────────────┘

❌ Confusing: Which can I apply? Which won't work?
❌ No clear separation of concerns
```

### AFTER (Clear)
```
┌─ Nielsen's Heuristics Evaluation ────────────────────┐
│                                                        │
│  ✅ Heuristics Summary:                               │
│  • 3 pathway improvements ready to apply (H2,H4,H5)   │
│  • 7 design recommendations to review (H1,H3,H6-H10) │
│                                                        │
├─ 🔧 Pathway Improvements (Actionable) ────────────────┤
│                                                        │
│  H2 - Language clarity [EXPAND]                       │
│  AI Assessment: "Replace medical jargon with..."      │
│                                                        │
│  H4 - Consistency [EXPAND]                            │
│  AI Assessment: "Standardize terminology..."          │
│                                                        │
│  H5 - Error prevention [EXPAND]                       │
│  AI Assessment: "Add safety alerts for..."            │
│                                                        │
│  [✓ Apply All Improvements]  [↶ Undo Last Changes]   │
│                              (These work!)            │
│                                                        │
├─ 🎨 Design Recommendations (UI/UX - For Designer) ────┤
│ (Styled in blue background)                           │
│                                                        │
│  H1 - Status visibility [EXPAND]                      │
│  Recommendation: "Implement progress bar..."          │
│  💡 Tip: Share with design team                      │
│  (No Apply button - for designer review)              │
│                                                        │
│  H3 - User control [EXPAND]                           │
│  Recommendation: "Add undo/back options..."           │
│  💡 Tip: Share with design team                      │
│  (No Apply button - for designer review)              │
│                                                        │
│  ... (H6-H10 same format) ...                         │
│                                                        │
└────────────────────────────────────────────────────────┘

✅ Clear: Which 3 are actionable, which 7 are review-only
✅ Obvious what Apply does (all 3 together)
✅ Design-only ones clearly marked
✅ No confusing buttons that don't work
```

---

## When Apply Works vs When It Doesn't

### ACTIONABLE HEURISTICS (Apply Works!)

**H2: Language Clarity**
```
Before: "MI" "PCI" "ACS" "ACE inhibitor"
Apply H2 (Language)
       ↓
After: "Heart Attack" "Angioplasty" "Acute heart event" "Blood pressure meds"
```

**H4: Consistency**
```
Before: "Does patient qualify?" (Decision 1)
        "Is patient eligible?" (Decision 2)
        "Patient suitable?" (Decision 3)
Apply H4 (Consistency)
       ↓
After:  "Does patient qualify?" (all the same)
        "Does patient qualify?"
        "Does patient qualify?"
```

**H5: Error Prevention**
```
Before: "Administer aspirin"
Apply H5 (Error Prevention)
       ↓
After: "Administer aspirin [Check: Patient not allergic? Bleeding risk assessed?]"
```

---

### UI-DESIGN-ONLY HEURISTICS (No Apply - Review Only!)

**H1: Status Visibility**
```
Requires UI work:
- Add progress bar component
- Style current step highlight
- Update CSS
- Implement frontend logic

❌ Cannot apply to pathway data
✅ Share with frontend team
```

**H3: User Control**
```
Requires UI work:
- Add "Undo" button
- Add "Go Back" button
- Implement history navigation
- Wire up to backend

❌ Cannot apply to pathway data
✅ Share with frontend team
```

**H6: Recognition vs Recall**
```
Requires design work:
- Choose icons for each step
- Design visual language
- Create component library
- Test with users

❌ Cannot apply to pathway data
✅ Share with design team
```

---

## Key Insight

```
┌─────────────────────────────────────────────────────────┐
│  Nielsen's Heuristics are EVALUATION TOOLS             │
│  for interface design, not data structure modification │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │ Only 3 CAN modify pathway data: │
        │ • H2 (use plain language)       │
        │ • H4 (consistent terms)         │
        │ • H5 (prevent errors)           │
        └─────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │ 7 are UI DESIGN GUIDANCE:       │
        │ • H1 (show progress)            │
        │ • H3 (add escape routes)        │
        │ • H6 (icons over text)          │
        │ • H7 (shortcuts)                │
        │ • H8 (minimize clutter)         │
        │ • H9 (error messages)           │
        │ • H10 (help content)            │
        └─────────────────────────────────┘
```

This separation is what makes the new implementation work correctly.

---

## User Experience Timeline

### BEFORE (Frustrating)
```
1:00 PM - User clicks "Apply" on H1
1:02 PM - App loads... loading... loading...
1:05 PM - Still loading?
1:07 PM - Gives up, refreshes page
1:08 PM - "Why did nothing happen??"
```

### AFTER (Satisfying)
```
1:00 PM - User reads summary: "3 improvements ready"
1:01 PM - Clicks "Apply All Improvements"
1:02 PM - Sees status: "Applying pathway improvements..."
1:06 PM - Success! "✓ Applied pathway improvements"
1:07 PM - Sees updated nodes with clearer language
1:08 PM - Clicks "Undo" - reverts perfectly
1:09 PM - Reviews H1-H10, notes design recommendations
1:10 PM - Forwards blue section to UI designer
1:11 PM - Happy! Everything makes sense.
```
