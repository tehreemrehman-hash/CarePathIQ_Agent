#!/usr/bin/env python3
"""
Test script to verify Phase 4 preview + Phase 5 flows
Checks:
1. Phase 4 preview renders inline with zoom controls
2. Phase 4 refine & regenerate updates flowchart
3. Phase 5 expert/beta forms include pathway
"""

import json
import sys
from pathlib import Path

# Check 1: Phase 4 preview block exists with zoom/fit controls
print("=" * 60)
print("TEST 1: Phase 4 Inline Preview with Zoom Controls")
print("=" * 60)

streamlit_code = Path("streamlit_app.py").read_text()

checks = {
    "preview_expander": 'st.expander("Open Preview", expanded=False)' in streamlit_code,
    "zoom_out_button": 'id="cpq-zoom-out"' in streamlit_code,
    "zoom_in_button": 'id="cpq-zoom-in"' in streamlit_code,
    "fit_button": 'id="cpq-fit"' in streamlit_code,
    "svg_canvas": 'id="cpq-canvas"' in streamlit_code,
    "js_zoom_logic": 'scale = Math.min(scale + 0.1, 3)' in streamlit_code,
}

for check_name, result in checks.items():
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"  {status}: {check_name}")

print(f"\nOverall: {'PASS' if all(checks.values()) else 'FAIL'}\n")

# Check 2: Refine & Regenerate section exists and calls regenerate function
print("=" * 60)
print("TEST 2: Phase 4 Refine & Regenerate Flow")
print("=" * 60)

refine_checks = {
    "refine_expander": 'st.expander("Refine & Regenerate"' in streamlit_code,
    "file_uploader": 'st.file_uploader(' in streamlit_code and 'p4_upload' in streamlit_code,
    "text_area": 'st.text_area(' in streamlit_code and 'p4_refine_notes' in streamlit_code,
    "apply_button": 'st.button("Apply Refinements"' in streamlit_code and 'p4_apply_refine' in streamlit_code,
    "regenerate_function_call": 'regenerate_nodes_with_refinement(nodes, refine_with_file, h_data)' in streamlit_code,
    "updates_session_state": "st.session_state.data['phase3']['nodes'] = refined" in streamlit_code,
    "clears_cache": "p4_state['viz_cache'] = {}" in streamlit_code,
    "triggers_rerun": "st.rerun()" in streamlit_code,
}

for check_name, result in refine_checks.items():
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"  {status}: {check_name}")

print(f"\nOverall: {'PASS' if all(refine_checks.values()) else 'FAIL'}\n")

# Check 3: Phase 5 expert/beta forms include pathway
print("=" * 60)
print("TEST 3: Phase 5 Expert/Beta Forms Include Pathway")
print("=" * 60)

phase5_checks = {
    "expert_form_generated": 'generate_expert_form_html(' in streamlit_code,
    "expert_includes_nodes": 'nodes=nodes' in streamlit_code and 'generate_expert_form_html' in streamlit_code,
    "beta_form_generated": 'generate_beta_form_html(' in streamlit_code,
    "beta_includes_nodes": 'nodes=nodes' in streamlit_code and 'generate_beta_form_html' in streamlit_code,
    "edu_form_generated": 'create_education_module_template' in streamlit_code,
    "forms_branded": 'ensure_carepathiq_branding(' in streamlit_code,
}

for check_name, result in phase5_checks.items():
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"  {status}: {check_name}")

print(f"\nOverall: {'PASS' if all(phase5_checks.values()) else 'FAIL'}\n")

# Check 4: Flowchart updates after refinement
print("=" * 60)
print("TEST 4: Flowchart Updates After Refinement")
print("=" * 60)

flowchart_checks = {
    "cache_cleared_on_update": "p4_state['viz_cache'] = {}" in streamlit_code,
    "nodes_updated": "st.session_state.data['phase3']['nodes'] = refined" in streamlit_code,
    "rerun_triggered": "st.rerun()" in streamlit_code and "Apply Refinements" in streamlit_code,
    "graphviz_rebuild": "build_graphviz_from_nodes(nodes_for_viz, \"TD\")" in streamlit_code,
    "svg_recalculated": "svg_bytes = cache.get(sig, {}).get(\"svg\")" in streamlit_code,
}

for check_name, result in flowchart_checks.items():
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"  {status}: {check_name}")

print(f"\nOverall: {'PASS' if all(flowchart_checks.values()) else 'FAIL'}\n")

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)

all_checks = {**checks, **refine_checks, **phase5_checks, **flowchart_checks}
passed = sum(1 for v in all_checks.values() if v)
total = len(all_checks)

print(f"\nTotal: {passed}/{total} checks passed")

if passed == total:
    print("\n✓ All sanity checks PASSED!")
    sys.exit(0)
else:
    print(f"\n✗ {total - passed} checks FAILED")
    sys.exit(1)
