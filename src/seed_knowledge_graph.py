"""
Seed Knowledge Graph — Migrate Static Data + Existing Sessions
================================================================
One-time script to populate the KG from:
  1. data/graph_data.json (static graph)
  2. Completed assessment sessions in SQLite

Run with:  python -m src.seed_knowledge_graph
"""

import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import init_db, delete_all_kg_data
from src.knowledge_graph import KnowledgeGraph
from src.graph_ingestor import ingest_all_existing_sessions, recompute_employer_stats, recompute_community_stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_DATA_PATH = PROJECT_ROOT / "data" / "graph_data.json"


def seed_from_static_graph(kg: KnowledgeGraph):
    """Import nodes and edges from data/graph_data.json."""
    if not GRAPH_DATA_PATH.exists():
        print("  [SKIP] graph_data.json not found")
        return 0, 0

    with open(GRAPH_DATA_PATH, "r") as f:
        data = json.load(f)

    node_count = 0
    for node in data.get("nodes", []):
        nid = node.get("id")
        ntype = node.get("type", "unknown")
        name = node.get("name", nid)

        # Build properties from remaining fields
        props = {k: v for k, v in node.items() if k not in ("id", "type", "name")}

        kg.add_node(nid, ntype, name, props)
        node_count += 1

    edge_count = 0
    for edge in data.get("edges", []):
        kg.add_edge(
            edge["source"], edge["target"],
            edge.get("type", "unknown"),
            edge.get("weight", 1.0),
        )
        edge_count += 1

    print(f"  [OK] Imported {node_count} nodes + {edge_count} edges from graph_data.json")
    return node_count, edge_count


def main():
    sep = "=" * 60
    print(f"\n{sep}")
    print("  Knowledge Graph Seeder")
    print(sep)

    # Initialize DB (creates KG tables if needed)
    init_db()

    # Clear existing KG data for clean re-seed
    print("\n  Clearing existing KG data...")
    delete_all_kg_data()

    # Create KG engine
    kg = KnowledgeGraph()

    # Step 1: Import static graph
    print("\n  Step 1: Importing static graph data...")
    n_nodes, n_edges = seed_from_static_graph(kg)

    # Step 2: Ingest completed sessions
    print("\n  Step 2: Ingesting completed assessment sessions...")
    n_sessions = ingest_all_existing_sessions(kg)

    # Step 3: Compute similarity edges
    print("\n  Step 3: Computing similarity edges...")
    kg.load()  # Refresh in-memory graph
    n_sim = kg.compute_similarity_edges(threshold=0.80)
    print(f"  [OK] Created {n_sim} similarity edges")

    # Step 4: Recompute employer/community stats
    print("\n  Step 4: Recomputing employer & community stats...")
    recompute_employer_stats(kg)
    recompute_community_stats(kg)
    print("  [OK] Stats recomputed")

    # Summary
    kg.load()
    stats = kg.get_stats()
    print(f"\n{sep}")
    print("  SEED COMPLETE")
    print(sep)
    print(f"  Total nodes:  {stats['total_nodes']}")
    print(f"  Total edges:  {stats['total_edges']}")
    print(f"  Node types:   {stats.get('node_types', {})}")
    print(f"  Edge types:   {stats.get('edge_types', {})}")
    print(f"  Avg degree:   {stats.get('avg_degree', 0)}")
    print(f"  Borrowers:    {stats.get('borrower_count', 0)}")
    print(f"  Components:   {stats.get('connected_components', 0)}")
    print(f"\n  Knowledge Graph is ready.\n")


if __name__ == "__main__":
    main()
