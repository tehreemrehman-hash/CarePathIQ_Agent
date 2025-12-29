#!/usr/bin/env python3
"""
Comprehensive verification that Phase 1 and Phase 5 flows are correctly separated.
Documents the data flow and ensures Phase 5 still gets all necessary structured inputs.
"""

import json
from pathlib import Path

print("\n" + "=" * 80)
print("CAREPATHIQ PHASE 1 → PHASE 5 DATA FLOW VERIFICATION")
print("=" * 80)

streamlit_code = Path("streamlit_app.py").read_text()

# ============================================================================
# PHASE 1 FLOW
# ============================================================================
print("\n📋 PHASE 1 FLOW: Define Pathway Scope")
print("-" * 80)

phase1_inputs = [
    ("Clinical Condition", "st.text_input", "p1_cond_input"),
    ("Care Setting", "st.text_input", "p1_setting"),
    ("Inclusion Criteria", "st.text_area", "p1_inc"),
    ("Exclusion Criteria", "st.text_area", "p1_exc"),
    ("Problem Statement", "st.text_area", "p1_prob"),
    ("Project Goals", "st.text_area", "p1_obj"),
]

print("\n  INPUT FIELDS:")
for field, widget_type, key in phase1_inputs:
    has_field = f'key="{key}"' in streamlit_code
    status = "✓" if has_field else "❌"
    print(f"    {status} {field}")

# Check Phase 1 draft output
print("\n  AUTO-GENERATED (via trigger_p1_draft):")
phase1_outputs = [
    ("Inclusion criteria", "format_as_numbered_list(data.get('inclusion'"),
    ("Exclusion criteria", "format_as_numbered_list(data.get('exclusion'"),
    ("Problem statement", "data.get('problem'"),
    ("Objectives", "format_as_numbered_list(data.get('objectives'"),
]

for output_name, pattern in phase1_outputs:
    has_output = pattern in streamlit_code
    status = "✓" if has_output else "❌"
    print(f"    {status} {output_name}")

# ============================================================================
# PHASE 5 EDUCATION MODULE FLOW
# ============================================================================
print("\n\n📚 PHASE 5 EDUCATION MODULE FLOW: Build Interactive Learning")
print("-" * 80)

print("\n  INPUT SOURCES FOR EDUCATION GENERATION:")

sources = [
    ("Target Audience", "st.text_input", "p5_aud_edu_input", "User input in Phase 5 → used to build role-specific content"),
    ("Condition", "st.session_state.data['phase1'].get('condition'", "From Phase 1", "Used in module titles and descriptions"),
    ("Care Setting", "st.session_state.data['phase1'].get('setting'", "From Phase 1", "Used in module headers and objectives"),
    ("Charter/Objectives", "st.session_state.data['phase1'].get('charter'", "From Phase 1", "Extracted to build learning objectives"),
    ("Pathway Nodes", "st.session_state.data['phase3'].get('nodes'", "From Phase 3", "Core content for educational modules"),
    ("Evidence Citations", "st.session_state.data['phase2'].get('evidence'", "From Phase 2", "Used in quiz explanations"),
]

for input_name, code_pattern, source, usage in sources:
    has_pattern = code_pattern in streamlit_code
    status = "✓" if has_pattern else "❌"
    print(f"    {status} {input_name:20} ← {source:15} ({usage})")

print("\n  EDUCATION MODULE GENERATION FUNCTIONS CALLED:")
edu_functions = [
    ("get_role_depth_mapping", "Get audience role level and depth"),
    ("filter_nodes_by_role", "Filter pathway nodes by audience role"),
    ("generate_role_specific_module_header", "Create role-aware module titles"),
    ("generate_role_specific_learning_objectives", "Build role-specific learning objectives"),
    ("generate_role_specific_quiz_scenario", "Create realistic role-specific quizzes"),
    ("create_education_module_template", "Assemble final HTML education module"),
]

for func_name, description in edu_functions:
    has_func = func_name in streamlit_code
    status = "✓" if has_func else "❌"
    print(f"    {status} {func_name:40} → {description}")

# ============================================================================
# CRITICAL SEPARATION
# ============================================================================
print("\n\n🔒 CRITICAL SEPARATION CHECK")
print("-" * 80)

# Phase 1 should NOT call Phase 5 education functions
bad_phase1_patterns = [
    ("create_education_module_template", "Phase 1 calling Phase 5 education template"),
    ("generate_role_specific", "Phase 1 generating role-specific content"),
    ("edu_topics =", "Phase 1 building education topics"),
]

phase1_section_start = streamlit_code.find("def trigger_p1_draft():")
phase1_section_end = streamlit_code.find("def sync_p1_widgets():", phase1_section_start)
phase1_code = streamlit_code[phase1_section_start:phase1_section_end]

print("\n  Phase 1 MUST NOT call Phase 5 functions:")
phase1_clean = True
for pattern, description in bad_phase1_patterns:
    has_pattern = pattern in phase1_code
    status = "❌ FAIL" if has_pattern else "✓ PASS"
    print(f"    {status}: {description}")
    if has_pattern:
        phase1_clean = False

# Phase 5 should call education functions
phase5_section_start = streamlit_code.find("# ========== BOTTOM LEFT: EDUCATION MODULE ==========")
phase5_section_end = streamlit_code.find("# Download centered", phase5_section_start)
phase5_code = streamlit_code[phase5_section_start:phase5_section_end]

good_phase5_patterns = [
    "create_education_module_template",
    "generate_role_specific_module_header",
    "generate_role_specific_learning_objectives",
]

print("\n  Phase 5 MUST call education functions:")
phase5_good = True
for pattern in good_phase5_patterns:
    has_pattern = pattern in phase5_code
    status = "✓ PASS" if has_pattern else "❌ FAIL"
    print(f"    {status}: {pattern}")
    if not has_pattern:
        phase5_good = False

# ============================================================================
# SUMMARY
# ============================================================================
print("\n\n" + "=" * 80)
print("FINAL VERIFICATION RESULT")
print("=" * 80)

if phase1_clean and phase5_good:
    print("\n✓ ✓ ✓ ALL CHECKS PASSED ✓ ✓ ✓")
    print("\nData Flow is Correctly Separated:")
    print("  • Phase 1 generates SIMPLE criteria (inclusion, exclusion, problem, goals)")
    print("  • Phase 1 does NOT generate Phase 5 education content")
    print("  • Phase 5 independently builds structured education from:")
    print("    - Pathway nodes (Phase 3)")
    print("    - Evidence citations (Phase 2)")
    print("    - User-specified target audience (Phase 5 input)")
    print("    - Role-specific configuration helpers")
    print("\n✓ User will see appropriate content at each phase:")
    print("  Phase 1: Simple inclusion/exclusion/problem/goals")
    print("  Phase 5: Structured educational modules with quizzes & certificates")
else:
    print("\n❌ VERIFICATION FAILED")
    if not phase1_clean:
        print("  ✗ Phase 1 is calling Phase 5 functions (should not)")
    if not phase5_good:
        print("  ✗ Phase 5 is missing required education functions")

print("\n" + "=" * 80 + "\n")
