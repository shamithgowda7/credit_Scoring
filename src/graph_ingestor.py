import json
import logging
from typing import Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from src import database as db
from src.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class GraphIngestor:
    def __init__(self):
        self.kg = KnowledgeGraph()

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
        db.upsert_kg_node(
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
        db.upsert_kg_node(
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
        db.upsert_kg_edge(
            source_id=borrower_id,
            target_id=assessment_id,
            edge_type="assessed_on",
            properties={"timestamp": session_data.get('created_at')}
        )
        
        # 3. Extract Context Nodes (Employer, Community)
        bank_context = session_data.get('bank_context', '').lower()
        
        # Very simple extraction for demo purposes based on common keywords
        # In a real app, you'd use NER or the LLM to extract these explicitly
        if "agrico" in bank_context:
            self._link_employer(borrower_id, "emp_agrico", "AgriCo East Africa")
        elif "techcorp" in bank_context:
            self._link_employer(borrower_id, "emp_techcorp", "TechCorp India")
        elif "greenfield" in bank_context:
            self._link_community(borrower_id, "com_greenfield", "Greenfield District")
        elif "kibera" in bank_context:
            self._link_community(borrower_id, "com_kibera", "Kibera Cooperative")
            
        # 4. Extract Income Source
        employment_status = features.get('employment_status', '').lower()
        if 'salaried' in employment_status:
            self._link_income(borrower_id, "inc_salary", "Salaried Employment")
        elif 'freelance' in employment_status or 'gig' in employment_status:
            self._link_income(borrower_id, "inc_freelance", "Freelance/Gig")
        elif 'business' in employment_status or 'self' in employment_status:
            self._link_income(borrower_id, "inc_business", "Self-Employed/Business")

        # 5. Compute Similarity Edges
        self.compute_similarity_for_borrower(borrower_id, features)
        
        # Refresh the in-memory graph
        self.kg.refresh()
        
    def _link_employer(self, borrower_id: str, emp_id: str, emp_name: str):
        db.upsert_kg_node(node_id=emp_id, node_type="employer", name=emp_name)
        db.upsert_kg_edge(source_id=borrower_id, target_id=emp_id, edge_type="works_at")
        
    def _link_community(self, borrower_id: str, com_id: str, com_name: str):
        db.upsert_kg_node(node_id=com_id, node_type="community", name=com_name)
        db.upsert_kg_edge(source_id=borrower_id, target_id=com_id, edge_type="lives_in")
        
    def _link_income(self, borrower_id: str, inc_id: str, inc_name: str):
        db.upsert_kg_node(node_id=inc_id, node_type="income_source", name=inc_name)
        db.upsert_kg_edge(source_id=borrower_id, target_id=inc_id, edge_type="income_from")

    def compute_similarity_for_borrower(self, borrower_id: str, features: Dict[str, Any]):
        """Find similar borrowers and create edges."""
        if not features:
            return
            
        # Extract numerical features for vector
        feature_keys = ['income_mean', 'income_cv', 'savings_ratio', 'credit_utilization', 'repayment_history', 'social_capital_score']
        
        vec1 = []
        for k in feature_keys:
            try:
                val = float(features.get(k, 0.0))
                vec1.append(val)
            except:
                vec1.append(0.0)
                
        vec1_np = np.array(vec1).reshape(1, -1)
        
        # Get all other borrowers
        all_borrowers = db.get_kg_nodes(node_type="borrower")
        
        for other in all_borrowers:
            if other['id'] == borrower_id:
                continue
                
            other_features = other.get('properties', {}).get('features', {})
            if not other_features:
                continue
                
            vec2 = []
            for k in feature_keys:
                try:
                    val = float(other_features.get(k, 0.0))
                    vec2.append(val)
                except:
                    vec2.append(0.0)
                    
            vec2_np = np.array(vec2).reshape(1, -1)
            
            # Prevent 0 norm
            if np.linalg.norm(vec1_np) == 0 or np.linalg.norm(vec2_np) == 0:
                continue
                
            similarity = cosine_similarity(vec1_np, vec2_np)[0][0]
            
            if similarity > 0.85:
                # Create bidirected edges or an undirected edge logic
                # We'll just create a single directed edge for simplicity, or two
                db.upsert_kg_edge(
                    source_id=borrower_id, 
                    target_id=other['id'], 
                    edge_type="similar_to", 
                    weight=float(similarity)
                )
