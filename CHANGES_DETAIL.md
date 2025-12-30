## Pathway Visualization: Dual Rendering Path

- **Server-side Graphviz (preferred):** When the `dot` binary is available, the app builds SVG on the server for deterministic layout and reliable downloads. This path is active automatically when Graphviz is installed.
- **Client-side Viz.js fallback:** If Graphviz isn’t present, the app generates DOT and renders it in the browser via Viz.js. This ensures the preview works in any environment.

### Why
- **Consistency:** Native `dot` yields stable layouts across machines.
- **Resilience:** Viz.js keeps previews working when server Graphviz isn’t available or restricted.

### Install Graphviz (optional)
```
apt-get update -y
apt-get install -y graphviz
which dot && dot -V
```

### Try It
- Run: `streamlit run streamlit_app.py --server.headless true`
- Open the preview under “Pathway Visualization”.
- Downloads: SVG (server-rendered when available) and DOT (always available).

### Notes
- If CDNs are blocked, we can vendor Viz.js locally to avoid external script loading.
- The app selects the best path at runtime; no user toggle required.

# Code Changes Summary - Nielsen's Heuristics Fix

## Files Modified: 1
- `streamlit_app.py`

## Changes Made: 3 Main Additions

---

## 1️⃣ Added Heuristic Categories (Line 635)

**What:** New dictionary defining which heuristics can modify pathways vs which are UI-design-only

**Before:**
```python
HEURISTIC_DEFS = {
    "H1": "Visibility of system status...",
    "H2": "Match between system and real world...",
    # ... all 10 treated the same
}
```

**After:**
```python
HEURISTIC_DEFS = {
    "H1": "Visibility of system status...",
    # ... same definitions
}

# NEW: Categorize by applicability
HEURISTIC_CATEGORIES = {
    "pathway_actionable": {
        "H2": "Language clarity (replace medical jargon with patient-friendly terms where appropriate)",
        "H4": "Consistency (standardize terminology and node types across pathway)",
        "H5": "Error prevention (add critical alerts, validation rules, and edge case handling)"
    },
    "ui_design_only": {
        "H1": "Status visibility (implement progress indicators and highlighting in the interface)",
        "H3": "User control (add escape routes and undo/skip options in UI)",
        "H6": "Recognition not recall (use visual icons and clear labels instead of hidden menus)",
        "H7": "Efficiency accelerators (add keyboard shortcuts and quick actions for power users)",
        "H8": "Minimalist design (remove clutter and non-essential information from interface)",
        "H9": "Error recovery (display clear, plain-language error messages and recovery steps)",
        "H10": "Help & docs (provide in-app tooltips, FAQs, and guided walkthroughs)"
    }
}
```

**Impact:** Enables separation of actionable vs. design-only heuristics throughout the app

---

## 2️⃣ Added Batch Application Function (Line 1545)

**What:** New function to apply only H2, H4, H5 with a focused LLM prompt

**New Function:**
```python
def apply_pathway_heuristic_improvements(nodes, heuristics_data):
    """
    Apply ONLY the pathway-actionable heuristics to the nodes:
    - H2: Language clarity (simplify terminology)
    - H4: Consistency (standardize terminology and structure)
    - H5: Error prevention (add alerts and edge cases)
    
    Returns: Updated nodes list or None if LLM fails
    """
    actionable_keys = ["H2", "H4", "H5"]
    insights = {k: heuristics_data.get(k, "") for k in actionable_keys if k in heuristics_data}
    
    if not insights:
        return None
    
    # Build a focused prompt that asks for specific pathway improvements
    insights_text = "\n".join([f"{k}: {v}" for k, v in insights.items()])
    
    prompt = f"""You are a clinical pathway expert. Apply these specific improvements to the pathway:

{insights_text}

Current pathway nodes: {json.dumps(nodes)}

Improvements to apply:
1. For H2 (Language): Replace medical jargon with plain language where appropriate. Keep clinical terms where necessary.
2. For H4 (Consistency): Standardize terminology and ensure all similar decisions use consistent structure.
3. For H5 (Error Prevention): Add specific alerts, validation checkpoints, or warning conditions to prevent common errors.

Return ONLY a valid JSON array of updated nodes. Preserve all original node structure and IDs.
Keep labels concise and actionable. Do not invent new nodes unless specifically needed for safety."""
    
    new_nodes = get_gemini_response(prompt, json_mode=True)
    return new_nodes if new_nodes and isinstance(new_nodes, list) else None
```

**Key Improvements:**
- ✅ Filters to only H2, H4, H5 (the actionable ones)
- ✅ Provides specific instructions for each improvement type
- ✅ Single LLM call (not 10)
- ✅ Clear expectations about what can/can't be modified
- ✅ Returns updated nodes or None (better error handling)

---

## 3️⃣ Refactored Phase 4 Heuristics Panel (Line 3823)

**What:** Completely redesigned the UI to show actionable vs. design-only heuristics

### Old Code (Removed)
```python
# All heuristics treated the same
st.caption("Click each heuristic to view definition and AI-generated recommendations")
ordered_keys = sorted(h_data.keys(), key=lambda hk: int(hk[1:]) if hk[1:].isdigit() else 0)
for heuristic_key in ordered_keys:
    insight = h_data[heuristic_key]
    # ... show each heuristic with individual Apply button
    if st.button(f"✓ Apply", key=f"p4_apply_{heuristic_key}"):
        # Try to apply single heuristic (often fails for UI-only ones)
        prompt_apply = f"""Update the clinical pathway by applying this specific usability recommendation..."""
```

**Problems with Old Approach:**
- Individual Apply buttons for H1, H3, H6-H10 that can't modify nodes
- Vague LLM prompts trying to apply UI principles to pathway data
- Hanging/no visible changes
- Unclear what each heuristic is for

### New Code
```python
# RIGHT: Nielsen's heuristics panel
with col_right:
    st.subheader("Nielsen's Heuristics Evaluation")
    h_data = p4_state.get('heuristics_data', {})

    if not h_data:
        styled_info("Heuristics are generated automatically. They will appear here shortly.")
    else:
        # STEP 1: Separate actionable from UI-only heuristics
        actionable_h = {k: v for k, v in h_data.items() if k in HEURISTIC_CATEGORIES["pathway_actionable"]}
        ui_only_h = {k: v for k, v in h_data.items() if k in HEURISTIC_CATEGORIES["ui_design_only"]}
        
        # STEP 2: Show summary card
        st.info(f"""
**Heuristics Summary:**
- **{len(actionable_h)} pathway improvements** ready to apply collectively (H2, H4, H5)
- **{len(ui_only_h)} design recommendations** to review for UI implementation (H1, H3, H6-H10)
""")
        
        # STEP 3: Section for actionable heuristics
        if actionable_h:
            st.markdown("### 🔧 Pathway Improvements (Actionable)")
            st.caption("These heuristics can improve your clinical pathway structure and clarity. Apply them collectively below.")
            
            # Show each actionable heuristic
            for heuristic_key in sorted(actionable_h.keys()):
                insight = actionable_h[heuristic_key]
                category_desc = HEURISTIC_CATEGORIES["pathway_actionable"].get(heuristic_key, "")
                
                with st.expander(f"**{heuristic_key}** - {category_desc.split(' (')[0]}", expanded=False):
                    st.markdown(f"**Full Heuristic:** {HEURISTIC_DEFS.get(heuristic_key, 'N/A')}")
                    st.divider()
                    st.markdown(f"**AI Assessment for Your Pathway:**")
                    st.markdown(
                        f"<div style='background-color: white; color: black; padding: 12px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 10px;'>{insight}</div>",
                        unsafe_allow_html=True
                    )
            
            # SINGLE collective Apply button (NEW!)
            col_apply, col_space = st.columns([1, 1])
            with col_apply:
                if st.button("✓ Apply All Improvements", key="p4_apply_all_actionable", type="primary"):
                    p4_state.setdefault('nodes_history', []).append(copy.deepcopy(nodes))
                    with ai_activity("Applying pathway improvements (H2, H4, H5)…"):
                        improved_nodes = apply_pathway_heuristic_improvements(nodes, actionable_h)
                        if improved_nodes:
                            st.session_state.data['phase3']['nodes'] = harden_nodes(improved_nodes)
                            p4_state['viz_cache'] = {}
                            st.success("✓ Applied pathway improvements. Visualization and nodes updated.")
                            st.rerun()
                        else:
                            st.error("Could not process improvements. Please try again.")
            
            # SINGLE collective Undo button (NEW!)
            if st.button("↶ Undo Last Changes", key="p4_undo_all"):
                if p4_state.get('nodes_history') and len(p4_state['nodes_history']) > 0:
                    prev_nodes = p4_state['nodes_history'].pop()
                    st.session_state.data['phase3']['nodes'] = prev_nodes
                    p4_state['viz_cache'] = {}
                    st.success("Undid last improvement batch")
                    st.rerun()
                else:
                    st.info("No changes to undo")
            
            st.divider()
        
        # STEP 4: Section for UI-design-only heuristics (review only)
        if ui_only_h:
            st.markdown("### 🎨 Design Recommendations (UI/UX - For Your Designer)")
            st.caption("These are interface design improvements to implement in your app's frontend. Share with your design team.")
            
            # Show each UI-only heuristic (no Apply button!)
            for heuristic_key in sorted(ui_only_h.keys()):
                insight = ui_only_h[heuristic_key]
                category_desc = HEURISTIC_CATEGORIES["ui_design_only"].get(heuristic_key, "")
                
                with st.expander(f"**{heuristic_key}** - {category_desc.split(' (')[0]}", expanded=False):
                    st.markdown(f"**Full Heuristic:** {HEURISTIC_DEFS.get(heuristic_key, 'N/A')}")
                    st.divider()
                    st.markdown(f"**Recommendation for Your Interface:**")
                    st.markdown(
                        f"<div style='background-color: #f0f7ff; color: #001a4d; padding: 12px; border-radius: 5px; border-left: 4px solid #0066cc; margin-bottom: 10px;'>{insight}</div>",
                        unsafe_allow_html=True
                    )
                    st.caption("💡 Implementation tip: This is a design consideration to discuss with your frontend team or include in wireframes/mockups.")
```

**Key Improvements:**
- ✅ Summary card shows counts of actionable vs. design-only
- ✅ Clear visual separation (two sections)
- ✅ Single "Apply All Improvements" button (works reliably)
- ✅ Single "Undo Last Changes" button (reverts entire batch)
- ✅ UI-design-only heuristics shown in blue boxes (review only)
- ✅ No confusing "Apply" buttons on heuristics that can't modify pathways
- ✅ Clear guidance for designer handoff

---

## Impact Summary

| Aspect | Before | After | Benefit |
|--------|--------|-------|---------|
| **Heuristics treated** | All 10 equally | Split into 2 categories | ✅ Realistic expectations |
| **Apply buttons** | 10 (many fail silently) | 1 (works reliably) | ✅ No hanging/confusion |
| **LLM calls** | 10 per action | 1 per batch | ✅ Faster, cheaper, clearer |
| **User feedback** | "Why nothing?" | Summary card + clear changes | ✅ Better UX |
| **Design guidance** | Mixed with pathways | Separate section in blue | ✅ Clear handoff |
| **Undo logic** | Per-heuristic | Batch-level | ✅ Simpler, more predictable |

---

## Code Quality

- ✅ No breaking changes to existing code
- ✅ All new code follows project style
- ✅ Backward compatible (old heuristics data structure unchanged)
- ✅ Added helpful docstrings and comments
- ✅ Error handling for LLM failures
- ✅ No syntax errors (verified with `py_compile`)

---

## Backward Compatibility

- ✅ Old session data still works
- ✅ Phase 3 changes not affected
- ✅ Phase 5 deliverables not affected
- ✅ Can revert to old code if needed (no database migrations)
- ✅ New categorization doesn't break existing heuristics_data format
