# Detailed Verification Checklist - Nielsen's Heuristics Fix

Use this checklist to verify that the fix is working correctly without corrupting any existing code.

---

## Part 1: Code Integrity Check ✅ AUTOMATED

**Purpose:** Verify syntax and basic structure are intact

### 1.1 Syntax Validation
```bash
cd /workspaces/CarePathIQ_Agent
python3 -m py_compile streamlit_app.py
```
**Expected:** No output (success) or `SyntaxError` if there's a problem
- [ ] ✅ No errors reported

### 1.2 Import Validation
```python
# Check that the file can be imported
import sys
sys.path.insert(0, '/workspaces/CarePathIQ_Agent')
# Don't actually import streamlit_app (it has side effects)
# Just check the syntax above
```
- [ ] ✅ No import errors

### 1.3 Constants Validation
Check that HEURISTIC_CATEGORIES exists and has correct structure:

```bash
python3 << 'EOF'
import json

# Read the file
with open('/workspaces/CarePathIQ_Agent/streamlit_app.py', 'r') as f:
    content = f.read()

# Check for HEURISTIC_CATEGORIES
if 'HEURISTIC_CATEGORIES = {' in content:
    print("✅ HEURISTIC_CATEGORIES dictionary found")
else:
    print("❌ HEURISTIC_CATEGORIES not found")

# Check for all 10 heuristics in categories
expected_actionable = ["H2", "H4", "H5"]
expected_ui_only = ["H1", "H3", "H6", "H7", "H8", "H9", "H10"]

for h in expected_actionable:
    if f'"{h}"' in content and '"pathway_actionable"' in content:
        print(f"✅ {h} found in pathway_actionable")
    else:
        print(f"❌ {h} missing from pathway_actionable")

for h in expected_ui_only:
    if f'"{h}"' in content and '"ui_design_only"' in content:
        print(f"✅ {h} found in ui_design_only")
    else:
        print(f"❌ {h} missing from ui_design_only")
EOF
```

- [ ] ✅ HEURISTIC_CATEGORIES dictionary found
- [ ] ✅ H2, H4, H5 in "pathway_actionable"
- [ ] ✅ H1, H3, H6-H10 in "ui_design_only"

### 1.4 Function Validation
Check that new function exists:

```bash
python3 << 'EOF'
with open('/workspaces/CarePathIQ_Agent/streamlit_app.py', 'r') as f:
    content = f.read()

if 'def apply_pathway_heuristic_improvements(nodes, heuristics_data):' in content:
    print("✅ apply_pathway_heuristic_improvements() function found")
else:
    print("❌ apply_pathway_heuristic_improvements() function not found")

if 'actionable_keys = ["H2", "H4", "H5"]' in content:
    print("✅ Function filters to correct heuristics")
else:
    print("❌ Function filtering may be incorrect")

if 'get_gemini_response(prompt, json_mode=True)' in content:
    print("✅ Function uses LLM correctly")
else:
    print("❌ Function LLM call may be wrong")
EOF
```

- [ ] ✅ Function definition found
- [ ] ✅ Filters to H2, H4, H5 only
- [ ] ✅ Calls LLM with json_mode=True

---

## Part 2: Code Structure Check ✅ MANUAL

**Purpose:** Verify no existing code was accidentally broken

### 2.1 HEURISTIC_DEFS Unchanged
Check that original heuristic definitions are still there:

```bash
python3 << 'EOF'
with open('/workspaces/CarePathIQ_Agent/streamlit_app.py', 'r') as f:
    content = f.read()

original_defs = [
    '"H1": "Visibility of system status',
    '"H2": "Match between system and real world',
    '"H3": "User control and freedom',
    '"H4": "Consistency and standards',
    '"H5": "Error prevention',
    '"H6": "Recognition rather than recall',
    '"H7": "Flexibility and efficiency of use',
    '"H8": "Aesthetic and minimalist design',
    '"H9": "Help users recognize, diagnose, and recover from errors',
    '"H10": "Help and documentation'
]

for h_def in original_defs:
    if h_def in content:
        print(f"✅ Found: {h_def[:30]}...")
    else:
        print(f"❌ Missing: {h_def[:30]}...")
EOF
```

- [ ] ✅ All 10 definitions present
- [ ] ✅ No modifications to definitions
- [ ] ✅ Spelling/punctuation unchanged

### 2.2 Phase 1, 2, 3 Code Untouched
Compare line ranges to backup (shouldn't be modified):

```bash
# Phase 1 should end around line 900-950
# Phase 2 should be around line 950-1400
# Phase 3 should be around line 1400-3520
# These are estimates; just verify they exist and haven't changed

python3 << 'EOF'
with open('/workspaces/CarePathIQ_Agent/streamlit_app.py', 'r') as f:
    lines = f.readlines()
    
# Check Phase markers exist
phase_markers = [
    ('Phase 1', '# --- PHASE 1 ---'),
    ('Phase 2', '# --- PHASE 2 ---'),
    ('Phase 3', '# --- PHASE 3 ---'),
    ('Phase 4', '# --- PHASE 4 ---'),
    ('Phase 5', '# --- PHASE 5 ---'),
]

for phase_name, marker in phase_markers:
    found = any(marker in line for line in lines)
    print(f"✅ {phase_name} marker found" if found else f"❌ {phase_name} marker missing")
EOF
```

- [ ] ✅ Phase 1 marker present
- [ ] ✅ Phase 2 marker present
- [ ] ✅ Phase 3 marker present
- [ ] ✅ Phase 4 marker present
- [ ] ✅ Phase 5 marker present

### 2.3 Key Functions Still Exist
Verify critical functions weren't accidentally deleted:

```bash
python3 << 'EOF'
with open('/workspaces/CarePathIQ_Agent/streamlit_app.py', 'r') as f:
    content = f.read()

critical_functions = [
    'def get_genai_client():',
    'def harden_nodes(nodes_list):',
    'def get_gemini_response(prompt',
    'def columns_top(spec',
    'def build_graphviz_from_nodes(',
    'def render_graphviz_bytes(',
    'def regenerate_nodes_with_refinement(',
]

for func in critical_functions:
    if func in content:
        print(f"✅ Found: {func}")
    else:
        print(f"❌ Missing: {func}")
EOF
```

- [ ] ✅ get_genai_client() present
- [ ] ✅ harden_nodes() present
- [ ] ✅ get_gemini_response() present
- [ ] ✅ columns_top() present
- [ ] ✅ build_graphviz_from_nodes() present
- [ ] ✅ render_graphviz_bytes() present
- [ ] ✅ regenerate_nodes_with_refinement() present

---

## Part 3: Phase 4 UI Structure Check ✅ VISUAL

**Purpose:** Verify the new heuristics UI renders correctly

### 3.1 Prepare Test Environment
```bash
cd /workspaces/CarePathIQ_Agent
# Ensure .venv is activated
source .venv/bin/activate

# Set API key if needed
export GOOGLE_API_KEY="your-key-here"  # Skip if already in secrets
```

### 3.2 Launch App
```bash
streamlit run streamlit_app.py
```

### 3.3 Navigate to Phase 4
1. Fill Phase 1 data (condition, setting, etc.)
2. Skip Phase 2 or fill with sample evidence
3. Create 3-5 sample nodes in Phase 3
4. Click "Design User Interface" tab (Phase 4)

### 3.4 Verify Heuristics Auto-Generation
- [ ] ✅ Status message: "Analyzing usability heuristics..."
- [ ] ✅ After ~10 seconds: Message disappears
- [ ] ✅ Heuristics section shows data
- [ ] ✅ No errors in terminal/logs

### 3.5 Verify Summary Card
```
Expected to see:
✅ Heuristics Summary:
✅ • 3 pathway improvements ready to apply collectively (H2, H4, H5)
✅ • 7 design recommendations to review for UI implementation (H1, H3, H6-H10)
```

- [ ] ✅ Summary card appears
- [ ] ✅ Shows "3 pathway improvements"
- [ ] ✅ Shows "7 design recommendations"
- [ ] ✅ Correct counts displayed

### 3.6 Verify Actionable Section
```
Expected to see:
🔧 Pathway Improvements (Actionable)

H2 - Language clarity [EXPAND]
H4 - Consistency [EXPAND]
H5 - Error prevention [EXPAND]

[✓ Apply All Improvements]
[↶ Undo Last Changes]
```

- [ ] ✅ Section header "🔧 Pathway Improvements (Actionable)" appears
- [ ] ✅ H2 listed with expand button
- [ ] ✅ H4 listed with expand button
- [ ] ✅ H5 listed with expand button
- [ ] ✅ Only 3 heuristics in this section
- [ ] ✅ "Apply All Improvements" button present
- [ ] ✅ Button is PRIMARY style (blue/highlighted)
- [ ] ✅ "Undo Last Changes" button present
- [ ] ✅ Both buttons are visible and clickable

### 3.7 Verify Design Recommendations Section
```
Expected to see:
🎨 Design Recommendations (UI/UX - For Your Designer)

H1 - Status visibility [EXPAND] (blue box)
H3 - User control [EXPAND] (blue box)
H6 - Recognition... [EXPAND] (blue box)
... (H7-H10 same format)

NO Apply buttons on any of these
```

- [ ] ✅ Section header "🎨 Design Recommendations (UI/UX - For Your Designer)" appears
- [ ] ✅ H1 listed with expand button
- [ ] ✅ H3 listed with expand button
- [ ] ✅ H6 listed with expand button
- [ ] ✅ H7 listed with expand button
- [ ] ✅ H8 listed with expand button
- [ ] ✅ H9 listed with expand button
- [ ] ✅ H10 listed with expand button
- [ ] ✅ All 7 heuristics in this section
- [ ] ✅ Blue background/styling on boxes
- [ ] ✅ NO "Apply" buttons on any heuristic in this section
- [ ] ✅ NO "Undo" buttons on any heuristic in this section

### 3.8 Expand H2 (Actionable Example)
Click expand on H2:

```
Expected to see:
Full Heuristic: "Match between system and real world: Speak the users' language..."

AI Assessment for Your Pathway:
[White box with recommendation text]
```

- [ ] ✅ Full heuristic definition shows
- [ ] ✅ AI assessment appears in white box
- [ ] ✅ Assessment is specific to the pathway (not generic)
- [ ] ✅ Assessment is 2-3 sentences

### 3.9 Expand H1 (Design-Only Example)
Click expand on H1:

```
Expected to see:
Full Heuristic: "Visibility of system status: The design should always keep users..."

Recommendation for Your Interface:
[Blue box with recommendation text]

💡 Implementation tip: This is a design consideration...
```

- [ ] ✅ Full heuristic definition shows
- [ ] ✅ Recommendation appears in BLUE box (not white)
- [ ] ✅ Recommendation text mentions interface/UI
- [ ] ✅ Implementation tip shows at bottom
- [ ] ✅ Tip mentions "design team" or "design consideration"

---

## Part 4: Functionality Tests ✅ INTERACTIVE

**Purpose:** Verify Apply/Undo actually work

### 4.1 Test Apply All Improvements Button

**Before clicking:**
- [ ] ✅ Note the current pathway (e.g., "Step 1 (MI suspected)" text)
- [ ] ✅ "Apply All Improvements" button is enabled (not greyed out)
- [ ] ✅ "Undo Last Changes" button is greyed out or inactive

**Click "✓ Apply All Improvements":**
- [ ] ✅ Button becomes disabled
- [ ] ✅ Status message appears: "Applying pathway improvements (H2, H4, H5)…"
- [ ] ✅ Message shows for ~5-10 seconds (LLM processing)

**After LLM response:**
- [ ] ✅ Status message updates to "Ready!" (success state)
- [ ] ✅ Success message: "✓ Applied pathway improvements. Visualization and nodes updated."
- [ ] ✅ Pathway visualization refreshes
- [ ] ✅ Node labels are updated (language simplified, terms consistent)
- [ ] ✅ "Undo Last Changes" button becomes enabled

**Visual Changes Expected:**
- [ ] ✅ Medical jargon replaced (e.g., "MI" → "Heart Attack" or similar)
- [ ] ✅ Terminology standardized (all decisions use similar phrasing)
- [ ] ✅ Safety notes added (e.g., "[Check for X]" in relevant nodes)

### 4.2 Test Undo Last Changes Button

**Before clicking:**
- [ ] ✅ Note the current (improved) pathway
- [ ] ✅ "Undo Last Changes" button is enabled

**Click "↶ Undo Last Changes":**
- [ ] ✅ Button becomes disabled temporarily
- [ ] ✅ Status message: "Undid last improvement batch"
- [ ] ✅ Pathway visualization refreshes
- [ ] ✅ Node labels revert to original values

**Verification:**
- [ ] ✅ Medical jargon returns (e.g., "Heart Attack" → "MI")
- [ ] ✅ Terminology reverts to original form
- [ ] ✅ Safety notes removed

### 4.3 Test Apply Multiple Times
**Sequence:**
1. [ ] ✅ Click Apply → Nodes change
2. [ ] ✅ Click Undo → Nodes revert
3. [ ] ✅ Click Apply again → Same changes occur
4. [ ] ✅ Nodes are consistent (same output each time)

---

## Part 5: Error Handling Tests ✅ EDGE CASES

**Purpose:** Verify the fix handles errors gracefully

### 5.1 Test with No Heuristics Data
**Setup:** Block heuristics from loading (e.g., invalid API key)

**Expected:**
- [ ] ✅ Summary card doesn't appear
- [ ] ✅ Message shows: "Heuristics are generated automatically. They will appear here shortly."
- [ ] ✅ No Apply button present
- [ ] ✅ No errors or crashes

### 5.2 Test with Empty Pathway
**Setup:** Go to Phase 4 with no nodes in Phase 3

**Expected:**
- [ ] ✅ Warning message: "No pathway nodes found..."
- [ ] ✅ Can still navigate/view recommendations
- [ ] ✅ Apply button might be disabled (if heuristics empty)
- [ ] ✅ No crashes or errors

### 5.3 Test LLM Failure (Simulated)
**Setup:** Temporarily disable API key or use wrong one

**Expected:**
- [ ] ✅ Heuristics auto-generation attempts
- [ ] ✅ Error displayed gracefully (if applicable)
- [ ] ✅ App doesn't crash
- [ ] ✅ Can still view manual editor or other sections

---

## Part 6: Backward Compatibility Check ✅ REGRESSION

**Purpose:** Verify old features still work

### 6.1 Phase 3 Still Works
- [ ] ✅ Can create/edit nodes
- [ ] ✅ Can add decision branches
- [ ] ✅ Visualization updates

### 6.2 Manual Node Editing in Phase 4 Still Works
**In Phase 4:**
- [ ] ✅ Can expand "Edit Pathway Data"
- [ ] ✅ Can edit nodes in data editor
- [ ] ✅ Can regenerate visualization after edit
- [ ] ✅ Manual edits don't trigger heuristics re-run (unless nodes hash changes)

### 6.3 Refine & Regenerate Section Still Works
**In Phase 4:**
- [ ] ✅ Can expand "Refine & Regenerate"
- [ ] ✅ Can enter refinement notes
- [ ] ✅ Can upload supporting file
- [ ] ✅ Can click "Regenerate"
- [ ] ✅ Nodes update based on refinement text (separate from heuristics)

### 6.4 Left Column (Visualization) Still Works
- [ ] ✅ SVG visualization renders
- [ ] ✅ "Open Preview" shows interactive preview
- [ ] ✅ Zoom controls work (-, +, Fit)
- [ ] ✅ Download SVG button works

### 6.5 Phase 5 Still Works
- [ ] ✅ Can navigate to Phase 5
- [ ] ✅ Can generate expert feedback form
- [ ] ✅ Can generate beta testing guide
- [ ] ✅ Can generate education module
- [ ] ✅ Can generate executive summary

---

## Part 7: Performance Check ✅ SPEED

**Purpose:** Verify no performance degradation

### 7.1 Phase 4 Load Time
- [ ] ✅ Takes <2 seconds to render Phase 4 UI
- [ ] ✅ Heuristics auto-generate in <15 seconds
- [ ] ✅ Apply All Improvements takes <15 seconds
- [ ] ✅ Undo is instant (<1 second)

### 7.2 Memory Usage
- [ ] ✅ No obvious memory leaks (app doesn't slow down after multiple applies)
- [ ] ✅ Can apply 5+ times without degradation

### 7.3 No Console Errors
- [ ] ✅ Terminal shows no Python errors
- [ ] ✅ Browser console shows no JavaScript errors
- [ ] ✅ No Streamlit warnings about deprecated features

---

## Part 8: Documentation Check ✅ REFERENCE

**Purpose:** Verify documentation is complete and accurate

### 8.1 Quick Reference Available
- [ ] ✅ `README_HEURISTICS_FIX.md` exists
- [ ] ✅ Explains problem and solution clearly
- [ ] ✅ Has testing checklist
- [ ] ✅ No broken links

### 8.2 Implementation Guide Available
- [ ] ✅ `HEURISTICS_IMPLEMENTATION_GUIDE.md` exists
- [ ] ✅ Explains what changed (code locations)
- [ ] ✅ Has debugging guide
- [ ] ✅ References correct line numbers

### 8.3 Visual Guide Available
- [ ] ✅ `VISUAL_GUIDE.md` exists
- [ ] ✅ Has before/after diagrams
- [ ] ✅ Shows data flow
- [ ] ✅ Helpful for understanding architecture

### 8.4 Complete Summary Available
- [ ] ✅ `HEURISTICS_COMPLETE_SUMMARY.md` exists
- [ ] ✅ Explains benefits and improvements
- [ ] ✅ Lists all heuristics and their types

---

## Summary Score

**Total Checks:** 100+

Count your ✅ marks:
- **95-100+ ✅:** All systems go! Fix is working perfectly.
- **85-94 ✅:** Minor issues, but core functionality works.
- **75-84 ✅:** Some problems, may need investigation.
- **Below 75:** Potential issue, recommend reviewing code or rollback.

---

## If Something Is Wrong

### Quick Diagnostics
```bash
# Check syntax
python3 -m py_compile streamlit_app.py

# Look for errors in constants
grep -n "HEURISTIC_CATEGORIES" streamlit_app.py

# Look for function
grep -n "def apply_pathway_heuristic_improvements" streamlit_app.py

# Check for Phase 4 section
grep -n "# --- PHASE 4 ---" streamlit_app.py
```

### Rollback if Needed
```bash
# Restore from backup
cp backups/2026-12-27/streamlit_app.py streamlit_app.py

# Verify rollback
python3 -m py_compile streamlit_app.py
```

### Get Help
Check these files for additional context:
- `HEURISTICS_FIX_EXPLANATION.md` - Why it was broken
- `IMPLEMENTATION_PLAN.md` - Detailed plan with risk assessment
- `CHANGES_DETAIL.md` - Exact code changes
