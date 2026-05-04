import networkx as nx
from collections import defaultdict
from typing import Dict, List, Any

from src import database as db

class KnowledgeGraph:
    """
    Dynamic Knowledge Graph Engine using NetworkX and SQLite.
    Persists data in SQLite and keeps an in-memory NetworkX graph for fast computation.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self.load_from_db()

    def load_from_db(self):
        """Load all nodes and edges from SQLite into the NetworkX graph."""
        self.graph.clear()
        
        nodes = db.get_kg_nodes()
        for node in nodes:
            # NetworkX expects node ID and then kwargs for attributes
            props = node.get('properties') or {}
            self.graph.add_node(
                node['id'],
                type=node['type'],
                name=node['name'],
                **props
            )
            
        edges = db.get_kg_edges()
        for edge in edges:
            props = edge.get('properties') or {}
            self.graph.add_edge(
                edge['source_id'],
                edge['target_id'],
                type=edge['type'],
                weight=edge['weight'],
                **props
            )

    def refresh(self):
        """Reload the graph from the database."""
        self.load_from_db()

    def get_borrower_neighborhood(self, borrower_id: str, radius: int = 1) -> dict:
        """Get the subgraph around a borrower."""
        if borrower_id not in self.graph:
            return {"nodes": [], "links": []}
            
        # For undirected neighborhood exploration we use the undirected version
        undirected_G = self.graph.to_undirected()
        subgraph_nodes = nx.single_source_shortest_path_length(undirected_G, borrower_id, cutoff=radius).keys()
        subgraph = self.graph.subgraph(subgraph_nodes)
        
        return self._format_for_frontend(subgraph)

    def compute_graph_features(self, borrower_id: str) -> dict:
        """
        Compute graph-derived features for a specific borrower.
        Returns features like default contagion risk, degree centrality, etc.
        """
        if borrower_id not in self.graph:
            return {
                "degree_centrality": 0.0,
                "employer_default_rate": 0.0,
                "community_repayment_rate": 1.0,
                "similarity_risk": 0.0,
                "network_density": 0.0
            }
            
        features = {}
        
        # 1. Centrality (using the whole graph or a localized subgraph? We'll use degree)
        features['degree_centrality'] = self.graph.degree(borrower_id) if self.graph.is_directed() else 0
        
        employer_default_rate = 0.0
        community_repayment_rate = 1.0
        similarity_risk = 0.0
        
        # Look at neighbors
        similar_defaults = 0
        similar_total = 0
        
        for neighbor in self.graph.successors(borrower_id):
            edge_data = self.graph.get_edge_data(borrower_id, neighbor)
            neighbor_data = self.graph.nodes[neighbor]
            
            if edge_data['type'] == 'works_at' and neighbor_data.get('type') == 'employer':
                employer_default_rate = neighbor_data.get('avg_default_rate', 0.0)
                
            elif edge_data['type'] == 'lives_in' and neighbor_data.get('type') == 'community':
                community_repayment_rate = neighbor_data.get('avg_repayment_rate', 1.0)
                
            elif edge_data['type'] == 'similar_to' and neighbor_data.get('type') == 'borrower':
                similar_total += 1
                if neighbor_data.get('decision') == 'REJECTED':
                    similar_defaults += 1
                    
        # Also check incoming edges
        for neighbor in self.graph.predecessors(borrower_id):
            edge_data = self.graph.get_edge_data(neighbor, borrower_id)
            neighbor_data = self.graph.nodes[neighbor]
            
            if edge_data['type'] == 'similar_to' and neighbor_data.get('type') == 'borrower':
                similar_total += 1
                if neighbor_data.get('decision') == 'REJECTED':
                    similar_defaults += 1

        if similar_total > 0:
            similarity_risk = similar_defaults / similar_total
            
        features['employer_default_rate'] = employer_default_rate
        features['community_repayment_rate'] = community_repayment_rate
        features['similarity_risk'] = similarity_risk
        features['network_density'] = nx.density(self.graph)
        
        return features

    def get_stats(self) -> dict:
        """Get summary statistics for the dashboard."""
        return db.get_kg_stats()

    def get_full_graph_data(self) -> dict:
        """Return the full graph formatted for react-force-graph-2d."""
        return self._format_for_frontend(self.graph)

    def _format_for_frontend(self, G: nx.Graph) -> dict:
        """Convert a NetworkX graph to the node/link format expected by frontend."""
        nodes = []
        for node_id, data in G.nodes(data=True):
            node_dict = {"id": node_id}
            node_dict.update(data)
            # Ensure name exists
            if 'name' not in node_dict:
                node_dict['name'] = node_id
            nodes.append(node_dict)
            
        links = []
        for u, v, data in G.edges(data=True):
            link_dict = {
                "source": u,
                "target": v,
            }
            link_dict.update(data)
            links.append(link_dict)
            
        return {"nodes": nodes, "links": links}
