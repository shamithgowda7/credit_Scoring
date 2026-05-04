import json
import logging
from typing import Dict, Any, List
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from src import database as db
from src.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class GraphIngestor:
    def __init__(self, kg: KnowledgeGraph = None):
        self.kg = kg or KnowledgeGraph()

    def ingest_completed_session(self, session_data: Dict[str, Any]):
        """
        Process a finalized assessment session and update the Knowledge Graph.
        """
        session_id = session_data['session_id']
        borrower_id = f"b_{session_id}"
        
        features = session_data.get('extracted_features')
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                features = {}
                
        # 1. Upsert Borrower Node
        self.kg.add_node(
            node_id=borrower_id,
            node_type="borrower",
            name=session_data.get('name', 'Unknown Borrower'),
            properties={
                "features": features,
                "score": session_data.get('final_score'),
                "decision": session_data.get('decision'),
                "risk_tier": session_data.get('risk_tier')
            }
        )
        
        # 2. Upsert Assessment Node
        assessment_id = f"a_{session_id}"
        self.kg.add_node(
            node_id=assessment_id,
            node_type="assessment",
            name=f"Assessment {session_id}",
            properties={
                "session_id": session_id,
                "score": session_data.get('final_score'),
                "confidence": session_data.get('extraction_confidence'),
                "duration_sec": session_data.get('interview_duration_sec')
            }
        )
        
        # Edge: Borrower -> Assessment
        self.kg.add_edge(
            source_id=borrower_id,
            target_id=assessment_id,
            edge_type="assessed_on",
            properties={"timestamp": session_data.get('created_at')}
        )
        
        # 3. Extract Context Nodes (Employer, Community)
        bank_context = session_data.get('bank_context', '').lower()
        
        # Very simple extraction for demo purposes
        if "agrico" in bank_context:
            self._link_employer(borrower_id, "emp_agrico", "AgriCo East Africa")
        elif "techcorp" in bank_context:
            self._link_employer(borrower_id, "emp_techcorp", "TechCorp India")
        
        if "greenfield" in bank_context:
            self._link_community(borrower_id, "com_greenfield", "Greenfield District")
        elif "kibera" in bank_context:
            self._link_community(borrower_id, "com_kibera", "Kibera Cooperative")
            
        # 4. Extract Income Source
        employment_status = features.get('employment_status', '') if features else ""
        if not isinstance(employment_status, str):
            employment_status = str(employment_status) if employment_status is not None else ""
        employment_status = employment_status.lower()
        
        if 'salaried' in employment_status:
            self._link_income(borrower_id, "inc_salary", "Salaried Employment")
        elif 'freelance' in employment_status or 'gig' in employment_status:
            self._link_income(borrower_id, "inc_freelance", "Freelance/Gig")
        elif 'business' in employment_status or 'self' in employment_status:
            self._link_income(borrower_id, "inc_business", "Self-Employed/Business")

        # 5. Compute Similarity Edges (optional, usually done in batch)
        # self.kg.compute_similarity_edges()
        
    def _link_employer(self, borrower_id: str, emp_id: str, emp_name: str):
        self.kg.add_node(node_id=emp_id, node_type="employer", name=emp_name)
        self.kg.add_edge(source_id=borrower_id, target_id=emp_id, edge_type="works_at")
        
    def _link_community(self, borrower_id: str, com_id: str, com_name: str):
        self.kg.add_node(node_id=com_id, node_type="community", name=com_name)
        self.kg.add_edge(source_id=borrower_id, target_id=com_id, edge_type="lives_in")
        
    def _link_income(self, borrower_id: str, inc_id: str, inc_name: str):
        self.kg.add_node(node_id=inc_id, node_type="income_source", name=inc_name)
        self.kg.add_edge(source_id=borrower_id, target_id=inc_id, edge_type="income_from")

# Helper functions for standalone use (seeder / API)
def ingest_completed_session(kg: KnowledgeGraph, session_data: Dict[str, Any]):
    """Top-level helper to ingest a single session."""
    ingestor = GraphIngestor(kg)
    ingestor.ingest_completed_session(session_data)
    return f"b_{session_data['session_id']}"

def ingest_all_existing_sessions(kg: KnowledgeGraph) -> int:
    """Read all completed sessions from DB and ingest them."""
    sessions = db.get_all_completed_sessions()
    ingestor = GraphIngestor(kg)
    for session in sessions:
        ingestor.ingest_completed_session(session)
    return len(sessions)

def recompute_employer_stats(kg: KnowledgeGraph):
    """Aggregate borrower outcomes by employer."""
    employers = [n for n, d in kg.graph.nodes(data=True) if d.get('type') == 'employer']
    for eid in employers:
        borrowers = [u for u, v, d in kg.graph.in_edges(eid, data=True) if d.get('type') == 'works_at']
        if not borrowers: continue
        
        scores = []
        rejected = 0
        for bid in borrowers:
            bdata = kg.graph.nodes[bid]
            scores.append(bdata.get('score', 500))
            if bdata.get('decision') in ('REJECTED', 'DECLINE'):
                rejected += 1
        
        avg_default_rate = rejected / len(borrowers)
        avg_score = sum(scores) / len(scores)
        
        kg.add_node(eid, "employer", kg.graph.nodes[eid].get('name'), {
            "avg_default_rate": avg_default_rate,
            "avg_score": avg_score,
            "borrower_count": len(borrowers)
        })

def recompute_community_stats(kg: KnowledgeGraph):
    """Aggregate borrower outcomes by community."""
    communities = [n for n, d in kg.graph.nodes(data=True) if d.get('type') == 'community']
    for cid in communities:
        borrowers = [u for u, v, d in kg.graph.in_edges(cid, data=True) if d.get('type') == 'lives_in']
        if not borrowers: continue
        
        approved = 0
        for bid in borrowers:
            if kg.graph.nodes[bid].get('decision') == 'APPROVE':
                approved += 1
        
        avg_repayment_rate = approved / len(borrowers)
        
        kg.add_node(cid, "community", kg.graph.nodes[cid].get('name'), {
            "avg_repayment_rate": avg_repayment_rate,
            "borrower_count": len(borrowers)
        })
