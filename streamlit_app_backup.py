import streamlit as st
import google.generativeai as genai
import pandas as pd
import graphviz
import urllib.request
import urllib.parse
import json
import time
from io import StringIO

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CarePathIQ (Gemini Edition)",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. PROMPT ENGINEERING (THE BRAIN)
# ==========================================
# This is the "Few-Shot" prompt that trains the Agent to sound like a top-tier resident.
SYSTEM_PROMPT = """
ROLE: You are an expert Emergency Medicine Resident and Clinical Pathway Agent.
GOAL: Analyze unstructured patient intake data, identify the most likely clinical condition, and map it to the correct 'OPA' (Our Practice Advisory) protocol.

GUIDELINES:
1. Be concise and action-oriented.
2. Prioritize life threats (Sepsis, Stroke, STEMI).
3. Do not be chatty. Use bullet points.
4. Always reference the specific OPA version.

---
FEW-SHOT TRAINING EXAMPLES:

Input: "55yom c/o crushing substernal chest pressure x 45 mins, radiating to left jaw. Diaphoretic."
Response:
**Assessment:** Acute Coronary Syndrome (High Probability)
**OPA Trigger:** Chest Pain Protocol (OPA-C v4.0)
**Plan:**
* STAT EKG (<10 min target)
* Aspirin 324mg PO
* Troponin I & CBC
* Prepare for potential Cath Lab activation

Input: "88F from SNF, AMS compared to baseline, foul smelling urine, temp 101.4, BP 88/50."
Response:
**Assessment:** Septic Shock (Likely Source: Urinary)
**OPA Trigger:** Sepsis Protocol (OPA-S v2.1)
**Plan:**
* Serum Lactate & Blood Cultures x2
* 30mL/kg IV Crystalloid Bolus (Hypotension)
* Start Empiric Antibiotics (Zosyn/Vanc per local antibiogram)
* Monitor Urine Output

Input: "24F ankle pain after twisting it playing soccer. No deformity. Ambulating with difficulty."
Response:
**Assessment:** Ankle Sprain (Low Acuity)
**OPA Trigger:** Musculoskeletal/Trauma (OPA-M v1.0)
**Plan:**
* Apply Ottawa Ankle Rules
* XR Ankle if malleolar pain + inability to bear weight
* RICE instructions
---
"""

# ==========================================
# 3. SIDEBAR SETUP
# ==========================================
with st.sidebar:
    st.title("Clinical Pathway Agent")
    st.caption("v1.0.5 | Few-Shot Integrated")
    
    st.markdown("---")
    
    # Status Indicators
    st.success("**Protocol Database:** Online")
    st.info("**Active Standard:** OPA v2.1")
    
    st.markdown("### ⚙️ Model Config")
    st.text("Temperature: 0.0 (Strict)")
    
    # NEW: Feature to show the prompt during a demo
    with st.expander("👁️ View Agent System Prompt"):
        st.code(SYSTEM_PROMPT, language="text")
        st.caption("This prompt is sent to the LLM to enforce 'Resident-level' reasoning.")

    st.markdown("---")
    if st.button("Reset Session", type="primary"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. AGENT LOGIC (SIMULATION)
# ==========================================
# ==========================================
# 4. AGENT LOGIC (SIMULATION)
# ==========================================
def get_agent_response(user_input):
    """
    Simulates the AI response matching the 'Few-Shot' style defined above.
    """
    user_text = user_input.lower()
    time.sleep(1.2) # Simulate API latency
    
    # LOGIC: SEPSIS
    if any(x in user_text for x in ["fever", "temp", "hot", "hypotensive", "bp 80", "bp 70", "lactate", "infection", "sepsis"]):
        return (
            "**Assessment:** Septic Shock (Suspected)\n"
            "**OPA Trigger:** Sepsis Protocol (OPA-S v2.1)\n"
            "**Plan:**\n"
            "* **Labs:** Serum Lactate, CBC, CMP, Blood Cultures x2\n"
            "* **Fluids:** 30mL/kg IV Crystalloid Bolus (due to hypotension/tachycardia)\n"
            "* **Meds:** Review allergies; prep Broad Spectrum Abx (Zosyn/Cefepime)\n"
            "* **Vitals:** Re-check MAP in 15 mins"
        )

    # LOGIC: ACS / CHEST PAIN
    elif any(x in user_text for x in ["chest pain", "pressure", "arm pain", "jaw", "substernal", "cp", "heart"]):
        return (
            "**Assessment:** Acute Coronary Syndrome (Rule Out)\n"
            "**OPA Trigger:** Chest Pain Protocol (OPA-C v4.0)\n"
            "**Plan:**\n"
            "* **Diagnostic:** STAT 12-lead EKG (Target < 10 mins)\n"
            "* **Meds:** Aspirin 324mg PO (chewed) unless contraindicated\n"
            "* **Labs:** High-sensitivity Troponin, BMP\n"
            "* **Monitor:** Continuous cardiac telemetry"
        )

    # LOGIC: STROKE
    elif any(x in user_text for x in ["slurred", "droop", "weakness", "numbness", "face", "speech", "stroke"]):
        return (
            "**Assessment:** Acute CVA (Code Stroke)\n"
            "**OPA Trigger:** Stroke Protocol (OPA-N v1.5)\n"
            "**Plan:**\n"
            "* **Critical:** Establish Last Known Well (LKW) time\n"
            "* **Imaging:** STAT CT Head (Non-contrast) & CTA Head/Neck\n"
            "* **Safety:** Keep NPO pending swallow screen\n"
            "* **Access:** Two large-bore IVs (18g preferred)"
        )

    # LOGIC: GENERAL
    else:
        return (
            "**Assessment:** General Intake (Non-Critical)\n"
            "**OPA Trigger:** Standard Triage (OPA-Gen v1.0)\n"
            "**Plan:**\n"
            "* Continue standard nursing assessment\n"
            "* Update vitals\n"
            "* specific OPA criteria not met in current text snippet"
        )

# ==========================================
# 5. MAIN INTERFACE
# ==========================================
st.markdown("## Patient Triage Interface")
st.markdown(
    """
    <div style='font-size: 1.1rem; color: #555;'>
    <b>Instructions:</b> Enter unstructured clinical text (e.g. "Pt 65M c/o cp x 2hrs"). 
    The Agent uses Few-Shot reasoning to map inputs to OPA Guidelines.
    </div>
    """, unsafe_allow_html=True
)
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Ready. Awaiting clinical input."
    })

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter clinical narrative..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent analyzing against OPA Protocols..."):
            response = get_agent_response(prompt)
            st.markdown(response)
            
    st.session_state.messages.append({"role": "assistant", "content": response})
