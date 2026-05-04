"""
Graph Utilities — Knowledge-Graph-Augmented Credit Scoring
==========================================================
Loads a synthetic knowledge graph from data/graph_data.json, computes
graph-derived features per borrower, and provides helper functions
used by the scoring API and the dashboard.

Dependencies: networkx (>=3.2)
"""

import json
from pathlib import Path
from typing import Dict, Optional

import networkx as nx

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GRAPH_DATA_PATH = DATA_DIR / "graph_data.json"
GRAPH_CONTEXTS_PATH = DATA_DIR / "graph_contexts.json"


# ── Graph Loading ─────────────────────────────────────────────────────────────

def load_graph(path: Path = None) -> nx.Graph:
    """
    Load the synthetic knowledge graph from JSON into a networkx Graph.

    Parameters
    ----------
    path : Path, optional
        Path to graph_data.json. Defaults to data/graph_data.json.

    Returns
    -------
    nx.Graph with node/edge attributes populated.
    """
    path = path or GRAPH_DATA_PATH
    if not path.exists():
        # Return an empty graph if file is missing
        return nx.Graph()

    with open(path, "r") as f:
        data = json.load(f)

    G = nx.Graph()

    # Add nodes with attributes
    for node in data.get("nodes", []):
        node_id = node.pop("id")
        G.add_node(node_id, **node)

    # Add edges with attributes
    for edge in data.get("edges", []):
        G.add_edge(
            edge["source"],
            edge["target"],
            type=edge.get("type", "unknown"),
            weight=edge.get("weight", 1.0),
        )

    return G


def compute_graph_features(G: nx.Graph, user_node_id: str) -> Dict:
    """
    Compute graph-derived features for a specific borrower node.

    Features computed:
    - graph_degree: number of direct connections
    - employer_default_rate: default rate of the borrower's employer
    - community_trust_score: avg repayment rate of the borrower's community
    - referral_bonus: whether the borrower was referred by an existing user
    - graph_risk_adjustment: net score adjustment (positive = beneficial)

    Parameters
    ----------
    G : nx.Graph
        The loaded knowledge graph.
    user_node_id : str
        The node ID (e.g., "user_1").

    Returns
    -------
    dict with computed features.
    """
    if user_node_id not in G:
        return _empty_features()

    degree = G.degree(user_node_id)

    # Find employer
    employer_default_rate = 0.05  # default assumption
    employer_name = "Unknown"
    employer_sector = "unknown"
    for neighbor in G.neighbors(user_node_id):
        if G.nodes[neighbor].get("type") == "employer":
            employer_name = G.nodes[neighbor].get("name", "Unknown")
            employer_sector = G.nodes[neighbor].get("sector", "unknown")
            employer_default_rate = G.nodes[neighbor].get("avg_employee_default_rate", 0.05)
            break

    # Find community
    community_trust = 0.80  # default
    community_name = "Unknown"
    for neighbor in G.neighbors(user_node_id):
        if G.nodes[neighbor].get("type") == "community":
            community_name = G.nodes[neighbor].get("name", "Unknown")
            community_trust = G.nodes[neighbor].get("avg_repayment_rate", 0.80)
            break

    # Check referrals
    referral_bonus = False
    referred_by = None
    for neighbor in G.neighbors(user_node_id):
        edge_data = G.edges[user_node_id, neighbor]
        if edge_data.get("type") == "referred_by":
            referral_bonus = True
            referred_by = G.nodes[neighbor].get("name", neighbor)
            break

    # Compute risk adjustment
    # Formula: community_bonus + employer_bonus + referral_bonus + degree_bonus
    community_bonus = int((community_trust - 0.80) * 50)   # +6 for 0.92, -1 for 0.78
    employer_bonus = int((0.05 - employer_default_rate) * 100)  # +3 for 0.02, -1 for 0.06
    referral_pts = 2 if referral_bonus else 0
    degree_bonus = min(degree - 2, 3)  # +1 per extra connection, max +3

    adjustment = community_bonus + employer_bonus + referral_pts + degree_bonus

    return {
        "graph_degree": degree,
        "employer_name": employer_name,
        "employer_sector": employer_sector,
        "employer_default_rate": employer_default_rate,
        "community_name": community_name,
        "community_trust_score": community_trust,
        "referral_bonus": referral_bonus,
        "referred_by": referred_by,
        "graph_risk_adjustment": adjustment,
        "graph_notes": _generate_notes(employer_name, employer_default_rate,
                                        community_name, community_trust,
                                        referral_bonus, degree),
    }


def get_dynamic_graph_context(borrower_id: str, kg) -> Dict:
    """
    Adapter function that uses the KnowledgeGraph engine to compute features.
    
    Parameters
    ----------
    borrower_id : str
        The node ID (e.g., "b_session_id").
    kg : KnowledgeGraph
        The live KnowledgeGraph engine instance.
    """
    if borrower_id not in kg.graph:
        return _empty_features()
        
    # Use the KG engine's logic
    kg_feats = kg.compute_graph_features(borrower_id)
    
    # Get direct nodes for names
    employer_name = "Unknown"
    community_name = "Unknown"
    
    for neighbor in kg.graph.successors(borrower_id):
        ndata = kg.graph.nodes[neighbor]
        etype = kg.graph.get_edge_data(borrower_id, neighbor).get('type')
        if etype == 'works_at' and ndata.get('type') == 'employer':
            employer_name = ndata.get('name', 'Unknown')
        elif etype == 'lives_in' and ndata.get('type') == 'community':
            community_name = ndata.get('name', 'Unknown')
            
    # Map back to the format expected by the frontend ScoringResponse
    adjustment = int((kg_feats['community_repayment_rate'] - 0.80) * 50) + \
                 int((0.05 - kg_feats['employer_default_rate']) * 100) + \
                 int(min(kg_feats['degree_centrality'] - 2, 3))
                 
    return {
        "graph_degree": kg_feats['degree_centrality'],
        "employer_name": employer_name,
        "employer_default_rate": kg_feats['employer_default_rate'],
        "community_name": community_name,
        "community_trust_score": kg_feats['community_repayment_rate'],
        "graph_risk_adjustment": adjustment,
        "graph_notes": _generate_notes(
            employer_name, kg_feats['employer_default_rate'],
            community_name, kg_feats['community_repayment_rate'],
            False, kg_feats['degree_centrality']
        )
    }


def _generate_notes(emp_name, emp_rate, comm_name, comm_trust, referral, degree):
    """Generate a human-readable explanation of the graph adjustment."""
    parts = []
    if emp_rate <= 0.03:
        parts.append(f"Low employer risk ({emp_name}: {emp_rate:.0%} default rate)")
    elif emp_rate >= 0.05:
        parts.append(f"Elevated employer risk ({emp_name}: {emp_rate:.0%} default rate)")

    if comm_trust >= 0.90:
        parts.append(f"Strong community ({comm_name}: {comm_trust:.0%} repayment)")
    elif comm_trust < 0.80:
        parts.append(f"Weaker community ({comm_name}: {comm_trust:.0%} repayment)")

    if referral:
        parts.append("Referred by existing good borrower (+2 pts)")

    if degree >= 4:
        parts.append(f"Well-connected (degree {degree})")

    return "; ".join(parts) if parts else "Average graph profile"


def _empty_features():
    """Return empty graph features when a user is not found."""
    return {
        "graph_degree": 0,
        "employer_name": "Unknown",
        "employer_sector": "unknown",
        "employer_default_rate": 0.05,
        "community_name": "Unknown",
        "community_trust_score": 0.80,
        "referral_bonus": False,
        "referred_by": None,
        "graph_risk_adjustment": 0,
        "graph_notes": "User not found in knowledge graph",
    }


# ── Pre-computed Context (Fast Path) ─────────────────────────────────────────

def load_graph_contexts(path: Path = None) -> Dict:
    """
    Load pre-computed graph contexts from graph_contexts.json.

    Returns
    -------
    dict mapping user_id (str) -> context dict
    """
    path = path or GRAPH_CONTEXTS_PATH
    if not path.exists():
        return {}

    with open(path, "r") as f:
        data = json.load(f)

    return data.get("contexts", {})


def get_graph_context(user_id: int, contexts: Dict = None) -> Dict:
    """
    Get pre-computed graph context for a user by their numeric ID.

    Parameters
    ----------
    user_id : int
        Numeric user ID (1-indexed).
    contexts : dict, optional
        Pre-loaded contexts dict. If None, loads from disk.

    Returns
    -------
    dict with graph features, or empty features if not found.
    """
    if contexts is None:
        contexts = load_graph_contexts()

    ctx = contexts.get(str(user_id))
    if ctx is None:
        return _empty_features()

    return ctx


# ── Graph Statistics (for Dashboard) ──────────────────────────────────────────

def get_graph_stats(G: nx.Graph = None) -> Dict:
    """
    Return summary statistics about the knowledge graph.

    Returns
    -------
    dict with node_count, edge_count, node_types, avg_degree, etc.
    """
    if G is None:
        G = load_graph()

    if len(G) == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "avg_degree": 0.0,
            "node_types": {},
            "edge_types": {},
            "borrower_count": 0,
        }

    # Count by node type
    node_types = {}
    for _, attrs in G.nodes(data=True):
        t = attrs.get("type", "unknown")
        node_types[t] = node_types.get(t, 0) + 1

    # Count by edge type
    edge_types = {}
    for _, _, attrs in G.edges(data=True):
        t = attrs.get("type", "unknown")
        edge_types[t] = edge_types.get(t, 0) + 1

    avg_degree = sum(dict(G.degree()).values()) / len(G) if len(G) > 0 else 0

    return {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "avg_degree": round(avg_degree, 2),
        "node_types": node_types,
        "edge_types": edge_types,
        "borrower_count": node_types.get("borrower", 0),
    }


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Graph Utils — Self-Test")
    print("=" * 55)

    G = load_graph()
    stats = get_graph_stats(G)
    print(f"\n  Graph loaded: {stats['node_count']} nodes, {stats['edge_count']} edges")
    print(f"  Node types: {stats['node_types']}")
    print(f"  Edge types: {stats['edge_types']}")
    print(f"  Avg degree: {stats['avg_degree']}")

    print("\n  --- Per-user graph features (computed live) ---")
    for uid in range(1, 13):
        node_id = f"user_{uid}"
        feats = compute_graph_features(G, node_id)
        print(f"  User {uid:2d} ({feats.get('employer_name', '?'):20s}) "
              f"deg={feats['graph_degree']} "
              f"adj={feats['graph_risk_adjustment']:+3d} "
              f"referral={feats['referral_bonus']}")

    print("\n  --- Pre-computed contexts ---")
    ctxs = load_graph_contexts()
    print(f"  Loaded {len(ctxs)} user contexts")

    print("\n  All tests passed.")
    print("=" * 55)
