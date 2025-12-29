# Implementation Guide: Fixed Heuristics Evaluation

## What Changed in the Code

### 1. Added Heuristic Categories Dictionary
**Location:** [streamlit_app.py](streamlit_app.py#L635)

```python
HEURISTIC_CATEGORIES = {
    "pathway_actionable": {
        "H2": "Language clarity (replace medical jargon with patient-friendly terms where appropriate)",
        "H4": "Consistency (standardize terminology and node types across pathway)",
        "H5": "Error prevention (add critical alerts, validation rules, and edge case handling)"
    },
    "ui_design_only": {
        "H1": "Status visibility (implement progress indicators and highlighting in the interface)",
        # ... etc
    }
}
```

This replaces the old approach of treating all heuristics equally.

### 2. Added Batch Application Function
**Location:** [streamlit_app.py](streamlit_app.py#L1545)

```python
def apply_pathway_heuristic_improvements(nodes, heuristics_data):
    """Apply only H2, H4, H5 with focused LLM prompt"""
```

**Key differences from old approach:**
- Filters to only `["H2", "H4", "H5"]`
- Provides specific instructions for each heuristic
- Single LLM call instead of 10
- Clear prompt about what can/cannot be modified

### 3. Refactored Phase 4 Heuristics Panel
**Location:** [streamlit_app.py](streamlit_app.py#L3823)

**Old logic:**
- Loop through all 10 heuristics
- Each has individual "Apply" button
- Each attempts to modify nodes independently
- No clear feedback on what's happening

**New logic:**
```python
# 1. Separate heuristics into categories
actionable_h = {k: v for k, v in h_data.items() if k in HEURISTIC_CATEGORIES["pathway_actionable"]}
ui_only_h = {k: v for k, v in h_data.items() if k in HEURISTIC_CATEGORIES["ui_design_only"]}

# 2. Show summary card
st.info(f"**{len(actionable_h)} pathway improvements** ready to apply...")

# 3. Show actionable heuristics with single collective Apply button
if actionable_h:
    st.markdown("### 🔧 Pathway Improvements (Actionable)")
    # ... display H2, H4, H5
    if st.button("✓ Apply All Improvements"):
        improved_nodes = apply_pathway_heuristic_improvements(nodes, actionable_h)

# 4. Show UI-design-only heuristics (no Apply button)
if ui_only_h:
    st.markdown("### 🎨 Design Recommendations (UI/UX - For Your Designer)")
    # ... display H1, H3, H6-H10 in blue boxes
```

---

## How to Test

### Setup
1. Ensure you have a few pathway nodes created in Phase 3
2. Navigate to Phase 4 (Design Interface)
3. Wait for heuristics to auto-analyze

### Test Scenario 1: Verify Categorization
**Expected:** Summary card shows "3 pathway improvements" and "7 design recommendations"
```
# Check what's displayed:
- H2 should be in the top section with "Apply All Improvements" button ✓
- H1 should be in the bottom section (blue box) with NO Apply button ✓
- H4 and H5 should be in top section ✓
- H6-H10 should be in bottom section ✓
```

### Test Scenario 2: Apply Improvements
**Steps:**
1. Click "✓ Apply All Improvements"
2. Wait for LLM response (~5-10 seconds)
3. Observe changes in the pathway visualization

**Expected results:**
- Nodes are updated (labels simplified, terminology standardized, safety notes added)
- Visualization refreshes to show new nodes
- "↶ Undo Last Changes" button becomes active
- Success message: "✓ Applied pathway improvements"

### Test Scenario 3: Undo Changes
**Steps:**
1. Click "↶ Undo Last Changes"
2. Observe pathway reverts to previous state

**Expected:**
- Nodes revert to previous version
- Visualization refreshes
- Success message: "Undid last improvement batch"

### Test Scenario 4: Design Recommendations
**Steps:**
1. Scroll to "Design Recommendations" section
2. Expand H1 (Visibility of system status)
3. Read the recommendation

**Expected:**
- Blue-styled box with recommendation
- Text like "implement a progress bar..."
- Tip about sharing with design team
- NO "Apply" button

---

## Debugging

### Symptom: "Apply All Improvements" button doesn't respond
**Cause:** LLM error or rate limit
**Fix:** 
- Check API key in settings
- Verify sufficient API quota
- Try again after a few seconds
- Check the ai_activity status message

### Symptom: Nodes unchanged after apply
**Possible causes:**
1. LLM returned invalid JSON → Check `get_gemini_response` error handling
2. `harden_nodes()` stripped modifications → Review node validation logic
3. State not saved → Check `st.session_state` writes

**Debugging:**
```python
# Add temporary debug in apply_pathway_heuristic_improvements:
improved = apply_pathway_heuristic_improvements(nodes, actionable_h)
print(f"Original nodes: {nodes}")
print(f"Improved nodes: {improved}")  # Check if different
print(f"After harden: {harden_nodes(improved)}")  # Check if validation broke it
```

### Symptom: Undo button doesn't work
**Cause:** `nodes_history` not properly appended before applying
**Fix:** Verify this line runs BEFORE LLM call:
```python
p4_state.setdefault('nodes_history', []).append(copy.deepcopy(nodes))
```

---

## Future Enhancements

### Option 1: Per-Heuristic Toggle
Allow users to select which heuristics to apply:
```python
st.checkbox("Apply H2 (Language Clarity)")
st.checkbox("Apply H4 (Consistency)")
st.checkbox("Apply H5 (Error Prevention)")
# Then apply only selected ones
```

### Option 2: Export Design Recommendations
Generate PDF for designer handoff:
```python
def export_design_recommendations(h_data):
    # Creates PDF with H1, H3, H6-H10
    # One page per heuristic
    # Designer-friendly formatting
```

### Option 3: Track Applied Changes
Show summary of what was improved:
```python
p4_state['improvements_applied'] = {
    'H2': ['Simplified "MI" to "Heart Attack"', ...],
    'H4': [...],
    'H5': [...]
}
```

### Option 4: Selective H2/H4/H5 Application
Instead of applying all 3 together:
```python
if st.button("Apply Only Language Clarity (H2)"):
    # Apply just H2
if st.button("Apply Only Consistency (H4)"):
    # Apply just H4
# etc
```

---

## Code References

| Component | Location | Purpose |
|-----------|----------|---------|
| `HEURISTIC_CATEGORIES` | Line 635 | Defines which heuristics are actionable |
| `apply_pathway_heuristic_improvements()` | Line 1545 | Applies H2, H4, H5 collectively |
| Phase 4 heuristics UI | Line 3823 | Displays categorized recommendations |
| `HEURISTIC_DEFS` | Line 623 | Original heuristic definitions (unchanged) |

---

## Conceptual Model

```
┌─────────────────────────────────────────────────────────┐
│  Nielsen's 10 Usability Heuristics (Theory)            │
└─────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
    ┌──────────────────────┐  ┌──────────────────────┐
    │ Can modify pathway   │  │ UI/UX design only   │
    │ structure?           │  │ (no pathway mod)     │
    └──────────────────────┘  └──────────────────────┘
          │                           │
    ┌─────┴──────────┐           ┌────┴────────────┐
    ▼                ▼           ▼                 ▼
   H2              H4, H5      H1, H3        H6, H7, H8, H9, H10
Language       Consistency  Status, Control  Recognition, Efficiency,
Clarity        & Prevention  Freedom        Design, Help

    ACTIONABLE              REVIEW-ONLY
    (Apply Button)          (For Designers)
    Single LLM call         No modification
    Direct node updates     Design guidance
```

This separation is what makes the new implementation work correctly.
