"""
Clinical Pathway Generator
Generates evidence-based clinical pathway decision trees and flowcharts
for any care condition and clinical setting.

This module provides:
1. Data classes for structured clinical pathway representation
2. Generator class for creating pathways programmatically
3. Conversion utilities between generator format and app node format
4. Export functions for Mermaid, Markdown, JSON, and Graphviz DOT

Based on analysis of ED clinical pathways with standardized structure:
- Patient Entry
- Criticality Checks (Initial & Secondary)
- PIT Orders (Provider in Triage)
- Evidence-Based Additions
- Disposition Logic
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json
import re
import textwrap


class NodeType(Enum):
    """Types of nodes in the pathway"""
    START = "Start"
    DECISION = "Decision"
    PROCESS = "Process"
    END = "End"
    # Extended types for clinical specificity
    ENTRY = "entry"
    CRITICAL_CARE = "critical_care"
    DISPOSITION = "disposition"
    OUTCOME = "outcome"


class DispositionType(Enum):
    """Standard disposition options"""
    DISCHARGE = "Discharge"
    OBSERVATION = "Observation"
    INPATIENT = "Inpatient"
    ICU = "ICU"
    TRANSFER = "Transfer"


@dataclass
class Order:
    """Represents a clinical order (lab, imaging, medication, etc.)"""
    category: str  # "Labs", "Imaging", "Meds", "CV", "Urine", etc.
    items: List[str]
    conditional: Optional[str] = None  # Condition for when to order
    notes: Optional[str] = None
    
    def to_label(self) -> str:
        """Convert order to node label format"""
        items_str = ", ".join(self.items)
        if self.conditional:
            return f"{self.category} ({self.conditional}): {items_str}"
        return f"{self.category}: {items_str}"


@dataclass
class CriticalityCheck:
    """Represents a criticality assessment point"""
    check_id: str
    title: str
    criteria: List[str]  # List of criteria to check
    is_initial: bool = True  # Initial vs secondary criticality check
    
    def to_label(self) -> str:
        """Convert to decision node label"""
        return " OR ".join(self.criteria) + "?"


@dataclass
class EvidenceBasedAddition:
    """Evidence-based interventions, risk stratification, or advanced diagnostics"""
    category: str  # "Risk Stratification", "Advanced Imaging", "Treatment", etc.
    name: str
    description: str
    criteria: Optional[str] = None  # When to apply
    scoring_system: Optional[Dict[str, Any]] = None  # For scoring systems
    pmid: Optional[str] = None  # Supporting evidence
    
    def to_label(self) -> str:
        """Convert to node label"""
        label = f"{self.name}"
        if self.criteria:
            label += f" ({self.criteria})"
        return label


@dataclass
class DispositionCriteria:
    """Criteria for each disposition option"""
    disposition_type: DispositionType
    criteria: List[str]
    additional_notes: Optional[str] = None
    follow_up: Optional[str] = None
    
    def to_label(self) -> str:
        """Convert to End node label"""
        criteria_str = "; ".join(self.criteria[:2])  # First 2 criteria for label
        return f"{self.disposition_type.value}: {criteria_str}"


@dataclass 
class AppNode:
    """
    Node format compatible with CarePathIQ streamlit_app.py
    This is the format used in st.session_state.data['phase3']['nodes']
    """
    type: str  # "Start", "Decision", "Process", "End"
    label: str
    evidence: str = "N/A"  # PMID or "N/A"
    notes: str = ""  # Actionable clinical details
    branches: Optional[List[Dict[str, Any]]] = None  # For Decision nodes: [{"label": "Yes", "target": 2}]
    target: Optional[int] = None  # Explicit next node (for non-linear flow)
    role: Optional[str] = None  # Swimlane assignment
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for session state"""
        d = {
            "type": self.type,
            "label": self.label,
            "evidence": self.evidence,
            "notes": self.notes
        }
        if self.branches:
            d["branches"] = self.branches
        if self.target is not None:
            d["target"] = self.target
        if self.role:
            d["role"] = self.role
        return d
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'AppNode':
        """Create AppNode from dictionary"""
        return cls(
            type=d.get("type", "Process"),
            label=d.get("label", ""),
            evidence=d.get("evidence", "N/A"),
            notes=d.get("notes", d.get("detail", "")),
            branches=d.get("branches"),
            target=d.get("target"),
            role=d.get("role")
        )


@dataclass
class ClinicalPathway:
    """Complete clinical pathway structure"""
    condition_name: str
    chief_complaint: str
    clinical_setting: str  # "ED", "Inpatient", "Outpatient", etc.
    
    # Core pathway components
    initial_criticality_criteria: List[str] = field(default_factory=list)
    critical_care_actions: List[str] = field(default_factory=list)
    pit_orders: List[Order] = field(default_factory=list)
    secondary_criticality_criteria: Optional[List[str]] = None
    evidence_based_additions: List[EvidenceBasedAddition] = field(default_factory=list)
    disposition_criteria: List[DispositionCriteria] = field(default_factory=list)
    
    # Special considerations
    special_populations: List[str] = field(default_factory=list)
    
    # Metadata
    references: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    version: str = "1.0"


class PathwayGenerator:
    """Generator for clinical pathway decision trees"""
    
    def __init__(self):
        self.pathways: Dict[str, ClinicalPathway] = {}
    
    def create_pathway(
        self,
        condition_name: str,
        chief_complaint: str,
        clinical_setting: str = "ED",
        initial_criticality_criteria: List[str] = None,
        pit_orders: List[Order] = None,
        secondary_criticality_criteria: Optional[List[str]] = None,
        evidence_based_additions: List[EvidenceBasedAddition] = None,
        disposition_criteria: List[DispositionCriteria] = None,
        special_populations: List[str] = None,
        critical_care_actions: List[str] = None
    ) -> ClinicalPathway:
        """
        Create a new clinical pathway
        
        Args:
            condition_name: Name of the condition (e.g., "Chest Pain (ACS)")
            chief_complaint: Chief complaint description
            clinical_setting: Clinical setting (ED, Inpatient, etc.)
            initial_criticality_criteria: List of criteria for initial criticality check
            pit_orders: List of PIT orders
            secondary_criticality_criteria: Optional secondary criticality check criteria
            evidence_based_additions: Evidence-based interventions
            disposition_criteria: Criteria for each disposition option
            special_populations: Special population considerations
            critical_care_actions: Actions for critical care pathway
        """
        pathway = ClinicalPathway(
            condition_name=condition_name,
            chief_complaint=chief_complaint,
            clinical_setting=clinical_setting,
            initial_criticality_criteria=initial_criticality_criteria or [],
            critical_care_actions=critical_care_actions or ["Immediate Resuscitation"],
            pit_orders=pit_orders or [],
            secondary_criticality_criteria=secondary_criticality_criteria,
            evidence_based_additions=evidence_based_additions or [],
            disposition_criteria=disposition_criteria or [],
            special_populations=special_populations or []
        )
        
        self.pathways[condition_name] = pathway
        return pathway
    
    def pathway_to_app_nodes(self, pathway: ClinicalPathway) -> List[Dict[str, Any]]:
        """
        Convert ClinicalPathway to list of app-compatible node dictionaries.
        This is the format used by st.session_state.data['phase3']['nodes']
        """
        nodes = []
        node_idx = 0
        
        # Step 1: Entry node
        nodes.append({
            "type": "Start",
            "label": f"Patient presents to {pathway.clinical_setting} with {pathway.chief_complaint}",
            "evidence": "N/A",
            "notes": ""
        })
        node_idx += 1
        
        # Step 2: Initial Criticality Check (Decision node)
        if pathway.initial_criticality_criteria:
            crit_label = " OR ".join(pathway.initial_criticality_criteria[:3])
            if len(pathway.initial_criticality_criteria) > 3:
                crit_label += " OR other critical findings"
            nodes.append({
                "type": "Decision",
                "label": f"Initial Criticality: {crit_label}?",
                "evidence": "N/A",
                "notes": "Red flags: " + ", ".join(pathway.initial_criticality_criteria),
                "branches": [
                    {"label": "YES - Critical", "target": node_idx + 1},
                    {"label": "NO - Stable", "target": node_idx + 2}
                ]
            })
            node_idx += 1
            
            # Critical Care pathway node
            crit_actions = "; ".join(pathway.critical_care_actions[:3])
            nodes.append({
                "type": "Process",
                "label": f"ERU/Critical Care: {crit_actions}",
                "evidence": "N/A",
                "notes": "Activate resuscitation team. " + "; ".join(pathway.critical_care_actions),
                "role": "Critical Care"
            })
            node_idx += 1
        
        # Step 3: PIT Orders (Process node)
        if pathway.pit_orders:
            orders_labels = []
            orders_notes = []
            for order in pathway.pit_orders[:6]:  # Limit for readability
                orders_labels.append(order.to_label())
                if order.notes:
                    orders_notes.append(f"{order.category}: {order.notes}")
            
            nodes.append({
                "type": "Process",
                "label": f"PIT Orders: {'; '.join(orders_labels[:4])}",
                "evidence": "N/A",
                "notes": "; ".join(orders_notes) if orders_notes else "Standard workup orders"
            })
            node_idx += 1
        
        # Step 4: Secondary Criticality (if applicable)
        if pathway.secondary_criticality_criteria:
            sec_crit_label = " OR ".join(pathway.secondary_criticality_criteria[:2])
            nodes.append({
                "type": "Decision",
                "label": f"Secondary Criticality: {sec_crit_label}?",
                "evidence": "N/A",
                "notes": "Re-evaluate after initial workup: " + ", ".join(pathway.secondary_criticality_criteria),
                "branches": [
                    {"label": "YES - Escalate", "target": 2},  # Back to critical care
                    {"label": "NO - Continue", "target": node_idx + 1}
                ]
            })
            node_idx += 1
        
        # Step 5: Evidence-Based Additions
        for eba in pathway.evidence_based_additions[:3]:  # Limit for readability
            nodes.append({
                "type": "Process",
                "label": eba.to_label(),
                "evidence": eba.pmid or "N/A",
                "notes": eba.description or ""
            })
            node_idx += 1
        
        # Step 6: Disposition Decision
        if pathway.disposition_criteria:
            nodes.append({
                "type": "Decision",
                "label": "Disposition Assessment",
                "evidence": "N/A",
                "notes": "Determine appropriate disposition based on clinical status and criteria",
                "branches": [
                    {"label": dc.disposition_type.value, "target": node_idx + 1 + i}
                    for i, dc in enumerate(pathway.disposition_criteria)
                ]
            })
            node_idx += 1
            
            # Create End node for each disposition
            for dc in pathway.disposition_criteria:
                follow_up = f" Follow-up: {dc.follow_up}" if dc.follow_up else ""
                nodes.append({
                    "type": "End",
                    "label": dc.to_label() + follow_up,
                    "evidence": "N/A",
                    "notes": dc.additional_notes or "; ".join(dc.criteria)
                })
                node_idx += 1
        else:
            # Default end node
            nodes.append({
                "type": "End",
                "label": "Disposition per clinical judgment",
                "evidence": "N/A",
                "notes": ""
            })
        
        return nodes
    
    def app_nodes_to_pathway(self, nodes: List[Dict[str, Any]], 
                             condition_name: str = "Imported Pathway",
                             clinical_setting: str = "ED") -> ClinicalPathway:
        """
        Convert app node list back to ClinicalPathway structure.
        Useful for exporting existing pathways.
        """
        # Extract chief complaint from Start node
        chief_complaint = "Clinical presentation"
        for node in nodes:
            if node.get("type") == "Start":
                label = node.get("label", "")
                if "with" in label:
                    chief_complaint = label.split("with")[-1].strip()
                break
        
        # Extract criticality criteria from Decision nodes
        initial_crit = []
        secondary_crit = []
        for node in nodes:
            if node.get("type") == "Decision":
                label = node.get("label", "").lower()
                notes = node.get("notes", "")
                if "criticality" in label or "critical" in label:
                    # Extract criteria from notes
                    if notes:
                        criteria = [c.strip() for c in notes.replace("Red flags:", "").split(",")]
                        if "initial" in label or "secondary" not in label:
                            initial_crit.extend(criteria[:5])
                        else:
                            secondary_crit.extend(criteria[:5])
        
        # Extract disposition criteria from End nodes
        disp_criteria = []
        for node in nodes:
            if node.get("type") == "End":
                label = node.get("label", "")
                notes = node.get("notes", "")
                
                # Determine disposition type
                disp_type = DispositionType.DISCHARGE
                label_lower = label.lower()
                if "icu" in label_lower:
                    disp_type = DispositionType.ICU
                elif "inpatient" in label_lower or "admit" in label_lower:
                    disp_type = DispositionType.INPATIENT
                elif "observation" in label_lower or "obs" in label_lower:
                    disp_type = DispositionType.OBSERVATION
                elif "transfer" in label_lower:
                    disp_type = DispositionType.TRANSFER
                
                disp_criteria.append(DispositionCriteria(
                    disposition_type=disp_type,
                    criteria=[label],
                    additional_notes=notes
                ))
        
        return ClinicalPathway(
            condition_name=condition_name,
            chief_complaint=chief_complaint,
            clinical_setting=clinical_setting,
            initial_criticality_criteria=initial_crit,
            secondary_criticality_criteria=secondary_crit if secondary_crit else None,
            disposition_criteria=disp_criteria
        )
    
    def generate_mermaid_diagram(self, pathway: ClinicalPathway, include_styling: bool = True) -> str:
        """
        Generate Mermaid flowchart diagram from pathway.
        For use in markdown documentation and exports.
        
        Args:
            pathway: ClinicalPathway object
            include_styling: Whether to include CSS styling classes
        """
        # Convert to app nodes first, then generate Mermaid from those
        nodes = self.pathway_to_app_nodes(pathway)
        return self.mermaid_from_app_nodes(nodes, include_styling)
    
    def mermaid_from_app_nodes(self, nodes: List[Dict[str, Any]], include_styling: bool = True) -> str:
        """
        Generate Mermaid flowchart from app node format.
        This works with st.session_state.data['phase3']['nodes']
        
        Args:
            nodes: List of node dictionaries in app format
            include_styling: Whether to include CSS styling classes
        """
        if not nodes:
            return "graph TD\n    NoNodes[No pathway nodes defined]"
        
        lines = ["graph TD"]
        
        # Collect note references
        notes_list = []
        notes_node_map = {}
        note_counter = 1
        for i, node in enumerate(nodes):
            notes_text = node.get('notes', '') or node.get('detail', '')
            if notes_text and str(notes_text).strip():
                notes_list.append((note_counter, str(notes_text).strip()))
                notes_node_map[i] = note_counter
                note_counter += 1
        
        if include_styling:
            lines.extend([
                "",
                "    %% Styling",
                "    classDef startEnd fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724,font-weight:bold",
                "    classDef decision fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#721c24,font-weight:bold",
                "    classDef process fill:#fff3cd,stroke:#ffc107,stroke-width:1px,color:#856404",
                "    classDef reeval fill:#ffe0b2,stroke:#e65100,stroke-width:2px,color:#bf360c",
                "    classDef noteBox fill:#bbdefb,stroke:#1565c0,stroke-width:1px,color:#0d47a1,font-size:11px",
                ""
            ])
        
        # Generate node definitions
        start_nodes = []
        decision_nodes = []
        process_nodes = []
        end_nodes = []
        reeval_nodes = []
        
        for i, node in enumerate(nodes):
            node_id = f"N{i}"
            node_type = node.get("type", "Process")
            label = self._escape_mermaid_label(node.get("label", f"Step {i}"))
            
            # Add note reference to label
            if i in notes_node_map:
                label = f"{label} &#91;Note {notes_node_map[i]}&#93;"
            
            # Determine shape based on type
            if node_type == "Start":
                lines.append(f'    {node_id}(["{label}"])')
                start_nodes.append(node_id)
            elif node_type == "End":
                lines.append(f'    {node_id}(["{label}"])')
                end_nodes.append(node_id)
            elif node_type == "Decision":
                lines.append(f'    {node_id}{{"{label}"}}')
                decision_nodes.append(node_id)
            elif node_type == "Reevaluation":
                lines.append(f'    {node_id}[/"{label}"\\]')
                reeval_nodes.append(node_id)
            else:  # Process
                lines.append(f'    {node_id}["{label}"]')
                process_nodes.append(node_id)
        
        lines.append("")
        
        # Generate edges using branch-aware logic
        computed_edges = self._compute_edges(nodes)
        for src_idx, dst_idx, lbl in computed_edges:
            src = f"N{src_idx}"
            dst = f"N{dst_idx}"
            if lbl:
                safe_lbl = self._escape_mermaid_label(lbl, max_length=35)
                lines.append(f'    {src} -->|"{safe_lbl}"| {dst}')
            else:
                lines.append(f'    {src} --> {dst}')
        
        # Add notes legend as a separate subgraph
        if notes_list:
            lines.append("")
            lines.append("    subgraph Notes Legend")
            lines.append("    direction TB")
            for note_num, note_text in notes_list:
                escaped_note = self._escape_mermaid_label(note_text, max_length=80)
                note_id = f"NOTE{note_num}"
                lines.append(f'    {note_id}["{note_num}. {escaped_note}"]')
            lines.append("    end")
            # Style note nodes
            note_ids = [f"NOTE{n}" for n, _ in notes_list]
            lines.append(f"    class {','.join(note_ids)} noteBox")
        
        # Apply styling classes
        if include_styling:
            lines.append("")
            if start_nodes or end_nodes:
                lines.append(f"    class {','.join(start_nodes + end_nodes)} startEnd")
            if decision_nodes:
                lines.append(f"    class {','.join(decision_nodes)} decision")
            if process_nodes:
                lines.append(f"    class {','.join(process_nodes)} process")
            if reeval_nodes:
                lines.append(f"    class {','.join(reeval_nodes)} reeval")
        
        return "\n".join(lines)
    
    def _escape_mermaid_label(self, text: str, max_length: int = 60) -> str:
        """Escape and truncate label for Mermaid compatibility.
        
        Mermaid is sensitive to: quotes, parentheses, brackets, angle brackets,
        curly braces, pipe characters, and hash symbols in labels.
        """
        if not text:
            return "Step"
        # Replace problematic characters for Mermaid
        text = str(text).replace('"', "'").replace('\n', ' ').replace('\\n', ' ')
        # Characters that break Mermaid syntax when inside quoted labels
        text = text.replace('#', '&#35;')
        text = text.replace('&', '&#38;')
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        return text
    
    def _compute_edges(self, nodes: List[Dict[str, Any]]):
        """
        Compute edges with branch-aware logic so that nodes inside a
        Decision branch region do NOT spuriously connect across branches.

        Logic:
        - Decision nodes: explicit branch targets with labels
        - End nodes: terminal, no outgoing edges
        - Nodes with explicit 'target': use that target
        - Nodes inside a branch region: sequential within that region,
          last node connects to reconvergence point
        - Other nodes: sequential to next node

        Returns list of (src_idx, dst_idx, label_str) tuples.
        """
        if not nodes:
            return []

        n = len(nodes)
        edges = []

        # Step 1: Build decision-branch structure
        decision_targets = {}
        for i, node in enumerate(nodes):
            if node.get('type') == 'Decision' and node.get('branches'):
                fwd = []
                for b in node.get('branches', []):
                    t = b.get('target')
                    if isinstance(t, (int, float)) and 0 <= int(t) < n:
                        fwd.append(int(t))
                if fwd:
                    decision_targets[i] = sorted(fwd)

        # Step 2: Compute branch regions
        branch_region_of = {}
        for dec_idx, sorted_tgts in decision_targets.items():
            fwd_tgts = sorted([t for t in sorted_tgts if t > dec_idx])
            if len(fwd_tgts) < 2:
                continue
            reconverge = max(fwd_tgts) + 1
            for b_idx, tgt in enumerate(fwd_tgts):
                if b_idx + 1 < len(fwd_tgts):
                    region_end = fwd_tgts[b_idx + 1] - 1
                else:
                    region_end = reconverge - 1
                for node_idx in range(tgt, min(region_end + 1, n)):
                    if node_idx not in branch_region_of:
                        branch_region_of[node_idx] = (region_end, reconverge)

        # Step 3: Generate edges
        for i, node in enumerate(nodes):
            ntype = node.get('type', 'Process')

            if ntype == 'Decision' and node.get('branches'):
                for b in node.get('branches', []):
                    t = b.get('target')
                    lbl = b.get('label', '')
                    if isinstance(t, (int, float)) and 0 <= int(t) < n:
                        edges.append((i, int(t), lbl))
            elif ntype == 'End':
                pass
            else:
                explicit = node.get('target')
                if explicit is not None and isinstance(explicit, (int, float)):
                    target_idx = int(explicit)
                    if 0 <= target_idx < n:
                        edges.append((i, target_idx, ''))
                elif i in branch_region_of:
                    region_end, reconverge = branch_region_of[i]
                    if i == region_end:
                        if reconverge < n:
                            edges.append((i, reconverge, ''))
                    elif i + 1 < n:
                        edges.append((i, i + 1, ''))
                elif i + 1 < n:
                    edges.append((i, i + 1, ''))

        return edges

    def generate_graphviz_dot(self, pathway: ClinicalPathway, orientation: str = "TD") -> str:
        """
        Generate Graphviz DOT source from pathway.
        This is compatible with the app's existing DOT rendering.
        
        Args:
            pathway: ClinicalPathway object
            orientation: "TD" (top-down) or "LR" (left-right)
        """
        nodes = self.pathway_to_app_nodes(pathway)
        return self.dot_from_app_nodes(nodes, orientation)
    
    def dot_from_app_nodes(self, nodes: List[Dict[str, Any]], orientation: str = "TD") -> str:
        """
        Generate Graphviz DOT source from app node format with clean decision tree layout.
        Compatible with streamlit_app.py's dot_from_nodes function.
        
        LAYOUT PRINCIPLES:
        1. Start node at top (rank=source)
        2. Clear top-to-bottom flow
        3. Decision nodes create true branching
        4. End nodes at bottom (rank=sink)
        
        Args:
            nodes: List of node dictionaries in app format
            orientation: "TD" (top-down) or "LR" (left-right)
        """
        if not nodes:
            return "digraph G {\n  // No nodes\n}"
        
        # Identify special nodes
        start_node_idx = None
        end_node_indices = []
        decision_node_indices = []
        
        for i, node in enumerate(nodes):
            node_type = node.get("type", "Process")
            if node_type == "Start" and start_node_idx is None:
                start_node_idx = i
            elif node_type == "End":
                end_node_indices.append(i)
            elif node_type == "Decision":
                decision_node_indices.append(i)
        
        rankdir = 'TB' if orientation == 'TD' else 'LR'
        lines = [
            "digraph G {",
            f"  rankdir={rankdir};",
            "  splines=ortho;",
            "  nodesep=0.8;",
            "  ranksep=1.0;",
            "  node [fontname=Helvetica, fontsize=11];",
            "  edge [fontname=Helvetica, fontsize=10];"
        ]
        
        # Node definitions
        for i, node in enumerate(nodes):
            node_id = f"N{i}"
            label = self._escape_dot_label(node.get("label", f"Step {i}"))
            node_type = node.get("type", "Process")
            
            # Determine shape and color
            if node_type == "Decision":
                shape, fill = "diamond", "#F8CECC"
            elif node_type == "Start":
                shape, fill = "oval", "#D5E8D4"
            elif node_type == "End":
                shape, fill = "oval", "#D5E8D4"
            else:
                shape, fill = "box", "#FFF2CC"
            
            # Add notes reference if present
            notes = node.get("notes", "")
            if notes:
                label += f"\\n(Note {i+1})"
            
            lines.append(f'  {node_id} [label="{label}", shape={shape}, style=filled, fillcolor="{fill}"];')
        
        lines.append("")
        
        # Layout constraints
        if start_node_idx is not None:
            lines.append(f"  {{ rank=source; N{start_node_idx}; }}")
        
        if end_node_indices:
            end_nids = [f"N{i}" for i in end_node_indices]
            lines.append(f"  {{ rank=sink; {'; '.join(end_nids)}; }}")
        
        # Group Decision branch targets at same rank
        for dec_idx in decision_node_indices:
            dec_node = nodes[dec_idx]
            branches = dec_node.get("branches", [])
            if len(branches) >= 2:
                branch_targets = []
                for b in branches:
                    t = b.get("target")
                    if isinstance(t, int) and 0 <= t < len(nodes):
                        branch_targets.append(f"N{t}")
                if len(branch_targets) >= 2:
                    lines.append(f"  {{ rank=same; {'; '.join(branch_targets)}; }}")
        
        lines.append("")
        
        # Edges — use branch-aware logic to avoid cross-branch connections
        computed_edges = self._compute_edges(nodes)
        for src_idx, dst_idx, lbl in computed_edges:
            src = f"N{src_idx}"
            dst = f"N{dst_idx}"
            if lbl:
                safe_lbl = self._escape_dot_label(lbl)
                lines.append(f'  {src} -> {dst} [label="{safe_lbl}"];')
            else:
                lines.append(f'  {src} -> {dst};')
        
        lines.append("}")
        return "\n".join(lines)
    
    def _escape_dot_label(self, text: str, max_length: int = 40) -> str:
        """Escape label for DOT format"""
        if not text:
            return "Step"
        # Escape quotes and backslashes
        text = str(text).replace("\\", "\\\\").replace('"', "'")
        # Replace newlines with DOT newline
        text = text.replace("\n", "\\n").replace("\\n", " ")
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Wrap text
        wrapped = textwrap.wrap(text, width=max_length)
        return "\\n".join(wrapped) if wrapped else text
    
    def generate_markdown(self, pathway: ClinicalPathway) -> str:
        """Generate markdown documentation for pathway"""
        md = [f"# {pathway.condition_name}"]
        md.append("")
        md.append(f"**Clinical Setting:** {pathway.clinical_setting}")
        md.append(f"**Chief Complaint:** {pathway.chief_complaint}")
        md.append("")
        
        # Add Mermaid diagram
        md.append("## Pathway Flowchart")
        md.append("")
        md.append("```mermaid")
        md.append(self.generate_mermaid_diagram(pathway))
        md.append("```")
        md.append("")
        
        # Pathway Details
        md.append("## Pathway Details")
        md.append("")
        
        md.append("### Step 1: Patient Entry")
        md.append(f"- Chief Complaint: {pathway.chief_complaint}")
        md.append("")
        
        if pathway.initial_criticality_criteria:
            md.append("### Step 2: Initial Criticality Check")
            for criterion in pathway.initial_criticality_criteria:
                md.append(f"- {criterion}")
            md.append("")
            md.append("**If Critical:** → ERU / Critical Care")
            for action in pathway.critical_care_actions:
                md.append(f"- {action}")
            md.append("")
        
        if pathway.pit_orders:
            md.append("### Step 3: PIT Orders")
            for order in pathway.pit_orders:
                md.append(f"- **{order.category}:** {', '.join(order.items)}")
                if order.conditional:
                    md.append(f"  - *Conditional: {order.conditional}*")
                if order.notes:
                    md.append(f"  - *Note: {order.notes}*")
            md.append("")
        
        if pathway.secondary_criticality_criteria:
            md.append("### Step 4: Secondary Criticality Check")
            for criterion in pathway.secondary_criticality_criteria:
                md.append(f"- {criterion}")
            md.append("")
        
        if pathway.evidence_based_additions:
            step_num = 5 if pathway.secondary_criticality_criteria else 4
            md.append(f"### Step {step_num}: Evidence-Based Additions")
            for eba in pathway.evidence_based_additions:
                md.append(f"- **{eba.category}:** {eba.name}")
                if eba.description:
                    md.append(f"  - {eba.description}")
                if eba.criteria:
                    md.append(f"  - Criteria: {eba.criteria}")
                if eba.pmid:
                    md.append(f"  - Evidence: PMID {eba.pmid}")
            md.append("")
        
        if pathway.disposition_criteria:
            disp_step = 6 if pathway.secondary_criticality_criteria else 5
            md.append(f"### Step {disp_step}: Disposition")
            md.append("")
            for dc in pathway.disposition_criteria:
                md.append(f"#### {dc.disposition_type.value}")
                for criterion in dc.criteria:
                    md.append(f"- {criterion}")
                if dc.follow_up:
                    md.append(f"- Follow-up: {dc.follow_up}")
                if dc.additional_notes:
                    md.append(f"- *{dc.additional_notes}*")
                md.append("")
        
        if pathway.special_populations:
            md.append("## Special Population Considerations")
            for pop in pathway.special_populations:
                md.append(f"- {pop}")
            md.append("")
        
        if pathway.references:
            md.append("## References")
            for ref in pathway.references:
                md.append(f"- {ref}")
        
        return "\n".join(md)
    
    def export_to_json(self, pathway: ClinicalPathway) -> str:
        """Export pathway to JSON format"""
        data = {
            "condition_name": pathway.condition_name,
            "chief_complaint": pathway.chief_complaint,
            "clinical_setting": pathway.clinical_setting,
            "initial_criticality_criteria": pathway.initial_criticality_criteria,
            "critical_care_actions": pathway.critical_care_actions,
            "pit_orders": [
                {
                    "category": order.category,
                    "items": order.items,
                    "conditional": order.conditional,
                    "notes": order.notes
                }
                for order in pathway.pit_orders
            ],
            "evidence_based_additions": [
                {
                    "category": eba.category,
                    "name": eba.name,
                    "description": eba.description,
                    "criteria": eba.criteria,
                    "pmid": eba.pmid
                }
                for eba in pathway.evidence_based_additions
            ],
            "disposition_criteria": [
                {
                    "disposition_type": dc.disposition_type.value,
                    "criteria": dc.criteria,
                    "follow_up": dc.follow_up,
                    "additional_notes": dc.additional_notes
                }
                for dc in pathway.disposition_criteria
            ],
            "special_populations": pathway.special_populations,
            "references": pathway.references,
            "version": pathway.version
        }
        
        if pathway.secondary_criticality_criteria:
            data["secondary_criticality_criteria"] = pathway.secondary_criticality_criteria
        
        return json.dumps(data, indent=2)
    
    def load_from_json(self, json_str: str) -> ClinicalPathway:
        """Load pathway from JSON format"""
        data = json.loads(json_str)
        
        # Reconstruct orders
        orders = [
            Order(
                category=o["category"],
                items=o["items"],
                conditional=o.get("conditional"),
                notes=o.get("notes")
            )
            for o in data.get("pit_orders", [])
        ]
        
        # Reconstruct evidence-based additions
        eba_list = [
            EvidenceBasedAddition(
                category=eba["category"],
                name=eba["name"],
                description=eba.get("description", ""),
                criteria=eba.get("criteria"),
                pmid=eba.get("pmid")
            )
            for eba in data.get("evidence_based_additions", [])
        ]
        
        # Reconstruct disposition criteria
        disp_criteria = [
            DispositionCriteria(
                disposition_type=DispositionType(dc["disposition_type"]),
                criteria=dc["criteria"],
                follow_up=dc.get("follow_up"),
                additional_notes=dc.get("additional_notes")
            )
            for dc in data.get("disposition_criteria", [])
        ]
        
        return self.create_pathway(
            condition_name=data["condition_name"],
            chief_complaint=data["chief_complaint"],
            clinical_setting=data["clinical_setting"],
            initial_criticality_criteria=data.get("initial_criticality_criteria", []),
            pit_orders=orders,
            secondary_criticality_criteria=data.get("secondary_criticality_criteria"),
            evidence_based_additions=eba_list,
            disposition_criteria=disp_criteria,
            special_populations=data.get("special_populations", []),
            critical_care_actions=data.get("critical_care_actions", [])
        )


# Convenience functions for direct use without instantiating PathwayGenerator

def create_mermaid_from_nodes(nodes: List[Dict[str, Any]], include_styling: bool = True) -> str:
    """
    Generate Mermaid diagram from app node format.
    Convenience function for use in streamlit_app.py
    
    Args:
        nodes: st.session_state.data['phase3']['nodes']
        include_styling: Whether to include CSS styling classes
    
    Returns:
        Mermaid diagram source code
    """
    generator = PathwayGenerator()
    return generator.mermaid_from_app_nodes(nodes, include_styling)


def create_dot_from_nodes(nodes: List[Dict[str, Any]], orientation: str = "TD") -> str:
    """
    Generate Graphviz DOT from app node format.
    Convenience function as alternative to streamlit_app.py's dot_from_nodes
    
    Args:
        nodes: st.session_state.data['phase3']['nodes']
        orientation: "TD" (top-down) or "LR" (left-right)
    
    Returns:
        DOT source code
    """
    generator = PathwayGenerator()
    return generator.dot_from_app_nodes(nodes, orientation)


def export_pathway_markdown(nodes: List[Dict[str, Any]], 
                            condition_name: str,
                            clinical_setting: str = "ED") -> str:
    """
    Export pathway nodes to markdown documentation.
    
    Args:
        nodes: st.session_state.data['phase3']['nodes']
        condition_name: Name of the clinical condition
        clinical_setting: Clinical setting (ED, Inpatient, etc.)
    
    Returns:
        Markdown documentation string
    """
    generator = PathwayGenerator()
    pathway = generator.app_nodes_to_pathway(nodes, condition_name, clinical_setting)
    return generator.generate_markdown(pathway)


# Example usage and testing
if __name__ == "__main__":
    generator = PathwayGenerator()
    
    # Example: Create a chest pain pathway
    pathway = generator.create_pathway(
        condition_name="Chest Pain (ACS)",
        chief_complaint="Chest Pain / Chest Discomfort",
        clinical_setting="ED",
        initial_criticality_criteria=[
            "STEMI or Equivalent?",
            "Hemodynamic Instability?",
            "Cardiac Arrest/Post-ROSC?"
        ],
        pit_orders=[
            Order(category="Labs", items=["CBC", "BMP", "Troponin", "BNP"]),
            Order(category="Imaging", items=["CXR"]),
            Order(category="Meds", items=["ASA 162mg PO", "NTG 0.4mg SL"], conditional="If no contraindications"),
            Order(category="CV", items=["EKG Immediate", "Cardiac Monitor"])
        ],
        secondary_criticality_criteria=[
            "STEMI on EKG?",
            "Critical Lab Values?"
        ],
        evidence_based_additions=[
            EvidenceBasedAddition(
                category="Risk Stratification",
                name="HEART Score",
                description="Calculate HEART score for ACS risk stratification",
                criteria="Low Risk: Score <= 3; High Risk: Score >= 4"
            )
        ],
        disposition_criteria=[
            DispositionCriteria(
                disposition_type=DispositionType.DISCHARGE,
                criteria=["HEART <= 3", "Negative serial troponins", "Pain resolved"],
                follow_up="Cardiology within 1 week"
            ),
            DispositionCriteria(
                disposition_type=DispositionType.OBSERVATION,
                criteria=["HEART 4-6", "Needs stress test"],
                follow_up="Stress test within 24h"
            ),
            DispositionCriteria(
                disposition_type=DispositionType.INPATIENT,
                criteria=["Positive troponin", "NSTEMI", "Unstable angina"],
                additional_notes="Cardiology consult, consider cath lab"
            )
        ],
        critical_care_actions=[
            "Activate STEMI Team",
            "Immediate Resuscitation",
            "Prepare for Cath Lab"
        ],
        special_populations=["Pregnant", "Elderly >75", "Renal Disease"]
    )
    
    print("=== App Node Format ===")
    nodes = generator.pathway_to_app_nodes(pathway)
    print(json.dumps(nodes, indent=2))
    
    print("\n=== Mermaid Diagram ===")
    print(generator.generate_mermaid_diagram(pathway))
    
    print("\n=== Graphviz DOT ===")
    print(generator.generate_graphviz_dot(pathway))
