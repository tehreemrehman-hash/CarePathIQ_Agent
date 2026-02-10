"""
Gemini Function Declarations for CarePathIQ Agent

This module defines native function calling declarations for use with
Gemini API's function calling feature. These replace the previous
regex-based JSON parsing approach with structured function calls.

Requires thought signature validation for Gemini 3+ models.
See: https://ai.google.dev/gemini-api/docs/thought-signatures
"""

from google.genai import types

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Primary model aliases - use -latest for automatic updates
PRIMARY_MODEL = "gemini-flash-latest"
FALLBACK_MODEL = "gemini-pro-latest"

# Model cascade for automatic fallback on quota exhaustion
MODEL_CASCADE = [
    "gemini-flash-latest",
    "gemini-pro-latest",
]

# Thinking configuration for thought signature validation
DEFAULT_THINKING_CONFIG = types.ThinkingConfig(
    thinking_budget=1024  # Default tokens for internal reasoning
)

COMPLEX_THINKING_CONFIG = types.ThinkingConfig(
    thinking_budget=2048  # Higher budget for complex pathway generation
)

LIGHT_THINKING_CONFIG = types.ThinkingConfig(
    thinking_budget=512  # Lower budget for simple tasks
)


# =============================================================================
# FUNCTION DECLARATIONS
# =============================================================================

# -----------------------------------------------------------------------------
# Pathway Node Generation
# -----------------------------------------------------------------------------
GENERATE_PATHWAY_NODES = types.FunctionDeclaration(
    name="generate_pathway_nodes",
    description="Generate a clinical care pathway as a directed acyclic graph of nodes. Each node represents a step in the clinical workflow.",
    parameters={
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "description": "Array of pathway nodes forming a directed acyclic graph",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["Start", "Decision", "Process", "End"],
                            "description": "Node type: Start (entry point), Decision (branching), Process (action), End (terminal)"
                        },
                        "label": {
                            "type": "string",
                            "description": "Brief descriptive label (max 120 characters)"
                        },
                        "evidence": {
                            "type": "string",
                            "description": "PMID citation for evidence-based steps, or 'N/A' if consensus-based"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Clinical details: red flags, thresholds, timing considerations"
                        },
                        "branches": {
                            "type": "array",
                            "description": "For Decision nodes: array of branch options",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {
                                        "type": "string",
                                        "description": "Branch condition label (e.g., 'Yes', 'No', 'High Risk')"
                                    },
                                    "target": {
                                        "type": "integer",
                                        "description": "Index of the target node in the nodes array"
                                    }
                                },
                                "required": ["label", "target"]
                            }
                        }
                    },
                    "required": ["type", "label", "evidence"]
                }
            }
        },
        "required": ["nodes"]
    }
)

# -----------------------------------------------------------------------------
# Phase 1 Scope Definition
# -----------------------------------------------------------------------------
DEFINE_PATHWAY_SCOPE = types.FunctionDeclaration(
    name="define_pathway_scope",
    description="Define the clinical scope, inclusion/exclusion criteria, problem statement, and objectives for a care pathway.",
    parameters={
        "type": "object",
        "properties": {
            "inclusion": {
                "type": "string",
                "description": "Patient inclusion criteria, one criterion per line"
            },
            "exclusion": {
                "type": "string",
                "description": "Patient exclusion criteria, one criterion per line"
            },
            "problem": {
                "type": "string",
                "description": "Clinical problem statement in 1-2 sentences"
            },
            "objectives": {
                "type": "string",
                "description": "Pathway objectives, one objective per line"
            }
        },
        "required": ["inclusion", "exclusion", "problem", "objectives"]
    }
)

# -----------------------------------------------------------------------------
# IHI Project Charter
# -----------------------------------------------------------------------------
CREATE_IHI_CHARTER = types.FunctionDeclaration(
    name="create_ihi_charter",
    description="Create an IHI Model for Improvement project charter with all required components for quality improvement initiatives.",
    parameters={
        "type": "object",
        "properties": {
            "project_description": {
                "type": "string",
                "description": "Brief description of the improvement project"
            },
            "rationale": {
                "type": "string",
                "description": "Why this project is important and needed"
            },
            "expected_outcomes": {
                "type": "string",
                "description": "Anticipated results and benefits"
            },
            "aim_statement": {
                "type": "string",
                "description": "SMART aim statement: Specific, Measurable, Achievable, Relevant, Time-bound"
            },
            "outcome_measures": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Primary and secondary outcome measures (list of strings)"
            },
            "process_measures": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Process measures to track implementation (list of strings)"
            },
            "balancing_measures": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Measures to detect unintended consequences (list of strings)"
            },
            "initial_activities": {
                "type": "string",
                "description": "First steps and activities to begin the project"
            },
            "change_ideas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of potential change ideas to test"
            },
            "stakeholders": {
                "type": "string",
                "description": "Key stakeholders and their roles"
            },
            "barriers": {
                "type": "string",
                "description": "Anticipated barriers and mitigation strategies"
            },
            "boundaries": {
                "type": "object",
                "properties": {
                    "in_scope": {
                        "type": "string",
                        "description": "What is included in the project scope"
                    },
                    "out_of_scope": {
                        "type": "string",
                        "description": "What is explicitly excluded"
                    }
                },
                "required": ["in_scope", "out_of_scope"]
            }
        },
        "required": [
            "project_description",
            "rationale",
            "aim_statement",
            "outcome_measures",
            "process_measures"
        ]
    }
)

# -----------------------------------------------------------------------------
# Evidence Grading (GRADE Framework)
# -----------------------------------------------------------------------------
GRADE_EVIDENCE = types.FunctionDeclaration(
    name="grade_evidence",
    description="Assign GRADE quality ratings to medical evidence from PubMed citations.",
    parameters={
        "type": "object",
        "properties": {
            "grades": {
                "type": "object",
                "description": "Map of PMID to grade assessment",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "grade": {
                            "type": "string",
                            "enum": ["High (A)", "Moderate (B)", "Low (C)", "Very Low (D)"],
                            "description": "GRADE quality rating"
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Brief justification for the assigned grade"
                        }
                    },
                    "required": ["grade", "rationale"]
                }
            }
        },
        "required": ["grades"]
    }
)

# -----------------------------------------------------------------------------
# Heuristics Analysis (Nielsen's 10)
# -----------------------------------------------------------------------------
ANALYZE_HEURISTICS = types.FunctionDeclaration(
    name="analyze_heuristics",
    description="Analyze a clinical pathway against Nielsen's 10 usability heuristics and provide actionable recommendations.",
    parameters={
        "type": "object",
        "properties": {
            "H1": {
                "type": "string",
                "description": "Visibility of system status: Recommendations for keeping users informed"
            },
            "H2": {
                "type": "string",
                "description": "Match between system and real world: Use familiar clinical language"
            },
            "H3": {
                "type": "string",
                "description": "User control and freedom: Support for undo, escape, flexibility"
            },
            "H4": {
                "type": "string",
                "description": "Consistency and standards: Follow clinical conventions"
            },
            "H5": {
                "type": "string",
                "description": "Error prevention: Safeguards against clinical errors"
            },
            "H6": {
                "type": "string",
                "description": "Recognition rather than recall: Reduce cognitive load"
            },
            "H7": {
                "type": "string",
                "description": "Flexibility and efficiency of use: Accommodate different expertise levels"
            },
            "H8": {
                "type": "string",
                "description": "Aesthetic and minimalist design: Remove unnecessary information"
            },
            "H9": {
                "type": "string",
                "description": "Help users recognize, diagnose, and recover from errors"
            },
            "H10": {
                "type": "string",
                "description": "Help and documentation: Provide accessible guidance"
            }
        },
        "required": ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H10"]
    }
)

# -----------------------------------------------------------------------------
# Apply Heuristics to Pathway
# -----------------------------------------------------------------------------
APPLY_HEURISTICS = types.FunctionDeclaration(
    name="apply_heuristics",
    description="Apply selected heuristic improvements to pathway nodes, returning modified nodes with tracked changes.",
    parameters={
        "type": "object",
        "properties": {
            "updated_nodes": {
                "type": "array",
                "description": "Modified pathway nodes with heuristic improvements applied",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["Start", "Decision", "Process", "End"]
                        },
                        "label": {"type": "string"},
                        "evidence": {"type": "string"},
                        "notes": {"type": "string"},
                        "branches": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "target": {"type": "integer"}
                                },
                                "required": ["label", "target"]
                            }
                        }
                    },
                    "required": ["type", "label", "evidence"]
                }
            },
            "applied_heuristics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of heuristic IDs that were applied (e.g., ['H2', 'H4', 'H5'])"
            },
            "applied_summary": {
                "type": "string",
                "description": "Summary of changes made to improve usability"
            }
        },
        "required": ["updated_nodes", "applied_heuristics", "applied_summary"]
    }
)

# -----------------------------------------------------------------------------
# Beta Test Scenario Generation
# -----------------------------------------------------------------------------
GENERATE_BETA_TEST_SCENARIOS = types.FunctionDeclaration(
    name="generate_beta_test_scenarios",
    description="Generate realistic clinical test scenarios for pathway validation by end-users.",
    parameters={
        "type": "object",
        "properties": {
            "scenarios": {
                "type": "array",
                "description": "Array of exactly 3 diverse test scenarios",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Brief scenario title"
                        },
                        "vignette": {
                            "type": "string",
                            "description": "Clinical vignette (max 50 words) describing the patient case"
                        },
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Exactly 3 specific tasks for the tester to complete"
                        },
                        "success_criteria": {
                            "type": "string",
                            "description": "How to determine if the pathway handled this scenario correctly"
                        },
                        "notes_placeholder": {
                            "type": "string",
                            "description": "Prompt for tester notes"
                        }
                    },
                    "required": ["title", "vignette", "tasks", "success_criteria"]
                }
            }
        },
        "required": ["scenarios"]
    }
)

# -----------------------------------------------------------------------------
# Audience Analysis for Executive Summary
# -----------------------------------------------------------------------------
ANALYZE_AUDIENCE = types.FunctionDeclaration(
    name="analyze_audience",
    description="Analyze target audience characteristics to customize executive summary content and tone.",
    parameters={
        "type": "object",
        "properties": {
            "strategic_focus": {
                "type": "boolean",
                "description": "Whether audience needs strategic/high-level view"
            },
            "operational_focus": {
                "type": "boolean",
                "description": "Whether audience needs operational/implementation details"
            },
            "detail_level": {
                "type": "string",
                "enum": ["executive", "detailed", "moderate"],
                "description": "Appropriate level of detail for this audience"
            },
            "tone": {
                "type": "string",
                "enum": ["executive", "clinical", "accessible"],
                "description": "Communication tone to use"
            },
            "priorities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top 3 priorities for this audience"
            },
            "emphasis_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Areas to emphasize in the summary"
            }
        },
        "required": ["strategic_focus", "operational_focus", "detail_level", "tone", "priorities"]
    }
)


# =============================================================================
# TOOL COLLECTIONS
# =============================================================================

# All pathway-related function declarations
PATHWAY_TOOLS = [
    GENERATE_PATHWAY_NODES,
    DEFINE_PATHWAY_SCOPE,
    APPLY_HEURISTICS,
]

# Quality improvement tools
QI_TOOLS = [
    CREATE_IHI_CHARTER,
    GRADE_EVIDENCE,
    ANALYZE_HEURISTICS,
]

# Phase 5 tools
PHASE5_TOOLS = [
    GENERATE_BETA_TEST_SCENARIOS,
    ANALYZE_AUDIENCE,
]

# All tools combined
ALL_TOOLS = PATHWAY_TOOLS + QI_TOOLS + PHASE5_TOOLS


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tool(function_declaration):
    """Wrap a FunctionDeclaration in a Tool object."""
    return types.Tool(function_declarations=[function_declaration])


def get_tools(function_declarations):
    """Wrap multiple FunctionDeclarations in a Tool object."""
    return types.Tool(function_declarations=function_declarations)


def get_generation_config(
    enable_thinking=True,
    thinking_budget=1024,
    force_function_call=False,
    function_name=None
):
    """
    Create a GenerateContentConfig with thinking and tool configuration.
    
    Args:
        enable_thinking: Whether to enable thought signature validation
        thinking_budget: Token budget for internal reasoning (512-4096)
        force_function_call: Whether to force function calling (mode=ANY)
        function_name: Specific function to call (requires force_function_call=True)
    
    Returns:
        types.GenerateContentConfig object
    """
    config_kwargs = {}
    
    # Configure thinking for Gemini 3+ models
    if enable_thinking:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=thinking_budget
        )
    
    # Configure tool/function calling behavior
    if force_function_call:
        fc_config = types.FunctionCallingConfig(mode="ANY")
        if function_name:
            fc_config = types.FunctionCallingConfig(
                mode="ANY",
                allowed_function_names=[function_name]
            )
        config_kwargs["tool_config"] = types.ToolConfig(
            function_calling_config=fc_config
        )
    
    return types.GenerateContentConfig(**config_kwargs) if config_kwargs else None


def extract_function_call_result(response):
    """
    Extract function call arguments from a Gemini response.
    
    Args:
        response: Gemini API response object
    
    Returns:
        dict with 'function_name' and 'arguments', or None if no function call
    """
    if not response or not response.candidates:
        return None
    
    for candidate in response.candidates:
        if not candidate.content or not candidate.content.parts:
            continue
        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                return {
                    "function_name": part.function_call.name,
                    "arguments": dict(part.function_call.args) if part.function_call.args else {}
                }
    
    return None


def has_text_response(response):
    """Check if response contains text (not just function call)."""
    if not response:
        return False
    try:
        return bool(response.text)
    except (AttributeError, ValueError):
        return False
