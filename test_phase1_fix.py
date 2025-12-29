#!/usr/bin/env python3
"""
Quick test to verify Phase 1 prompt generates simple criteria, not Phase 5 education content
"""

import json
import sys
from pathlib import Path

# Check the Phase 1 prompt
print("=" * 70)
print("TEST: Phase 1 Prompt Specification")
print("=" * 70)

streamlit_code = Path("streamlit_app.py").read_text()

# Find the trigger_p1_draft function
phase1_section_start = streamlit_code.find("def trigger_p1_draft():")
if phase1_section_start == -1:
    print("❌ FAIL: Could not find trigger_p1_draft function")
    sys.exit(1)

phase1_section_end = streamlit_code.find("def sync_p1_widgets():", phase1_section_start)
phase1_code = streamlit_code[phase1_section_start:phase1_section_end]

# Verify the new prompt includes these requirements
required_phrases = [
    "3-5 brief",  # Conciseness requirement
    "ONLY",  # Emphasis on not generating excessive content
    "Concise phrases",  # Explicit guidance
    "not detailed descriptions",  # Prevent Phase 5-style content
    "One brief clinical problem statement",  # Short problem statement
    "3-4 brief clinical objectives",  # Limited objectives
    "Short statements, not detailed goals",  # Prevent structured education content
]

print("\n✓ Checking Phase 1 prompt structure...\n")

all_pass = True
for phrase in required_phrases:
    found = phrase.lower() in phase1_code.lower()
    status = "✓" if found else "❌"
    print(f"  {status} '{phrase}' in prompt: {found}")
    if not found:
        all_pass = False

print("\n" + "=" * 70)

# Check that Phase 5 education generation is NOT being called from Phase 1
print("TEST: Phase 5 Education Independence")
print("=" * 70)

bad_patterns = [
    ("create_education_module_template", "Phase 1 should not call Phase 5 education function"),
    ("overall_objectives = ", "Phase 1 should not build education objectives"),
    ("edu_topics", "Phase 1 should not create education topics"),
]

print("\n✓ Checking Phase 1 does NOT generate Phase 5 content...\n")

phase1_clean = True
for pattern, description in bad_patterns:
    if pattern in phase1_code:
        print(f"  ❌ FAIL: Found '{pattern}' in Phase 1 (should not: {description})")
        phase1_clean = False
    else:
        print(f"  ✓ PASS: '{pattern}' not in Phase 1")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if all_pass and phase1_clean:
    print("✓ PASS: Phase 1 prompt is correctly specified")
    print("  - Generates only simple criteria, not structured education content")
    print("  - Does not call Phase 5 education functions")
    print("\nPhase 5 education module will still:")
    print("  ✓ Extract learning objectives from Phase 1 charter")
    print("  ✓ Build structured topics from pathway nodes (Phase 3)")
    print("  ✓ Use evidence data (Phase 2)")
    print("  ✓ Apply role-specific configurations")
    sys.exit(0)
else:
    print("❌ FAIL: Phase 1 prompt needs adjustment")
    sys.exit(1)
