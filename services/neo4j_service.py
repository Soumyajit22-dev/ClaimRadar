import os
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from neo4j import GraphDatabase
from pydantic import BaseModel


class VerificationResult(BaseModel):
    """Model for storing verification results in Neo4j"""
    input_id: str
    keywords: List[str]
    correctness: bool
    out_of_domain: bool
    misinfo: str
    rightinfo: str
    confidence_score: str
    sources: List[str]
    created_at: datetime
    raw_text_hash: str


class Neo4jService:
    def __init__(self):
        self.driver = None
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self._connect()
        self._create_constraints()

    def _connect(self):
        """Connect to Neo4j database"""
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        username = os.environ.get("NEO4J_USERNAME", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✅ Connected to Neo4j successfully")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            self.driver = None

    def _create_constraints(self):
        """Create unique constraints for better performance"""
        if not self.driver:
            return
            
        constraints = [
            "CREATE CONSTRAINT input_id_unique IF NOT EXISTS FOR (v:Verification) REQUIRE v.input_id IS UNIQUE",
            "CREATE CONSTRAINT raw_text_hash_unique IF NOT EXISTS FOR (v:Verification) REQUIRE v.raw_text_hash IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation warning: {e}")

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using TF-IDF"""
        try:
            # Clean and preprocess text
            cleaned_text = text.lower().strip()
            if not cleaned_text:
                return []
            
            # Fit vectorizer and get feature names
            tfidf_matrix = self.vectorizer.fit_transform([cleaned_text])
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Get top keywords by TF-IDF score
            scores = tfidf_matrix.toarray()[0]
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top 20 keywords
            return [kw for kw, score in keyword_scores[:20] if score > 0]
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return []

    def calculate_text_hash(self, text: str) -> str:
        """Create a hash of the raw text for exact matching"""
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def find_similar_verifications(self, keywords: List[str], threshold: float = 0.7) -> List[Dict]:
        """Find similar verifications based on keyword overlap"""
        if not self.driver or not keywords:
            return []

        try:
            with self.driver.session() as session:
                # Get all stored verifications with their keywords
                query = """
                MATCH (v:Verification)
                WHERE v.keywords IS NOT NULL
                RETURN v.input_id, v.keywords, v.correctness, v.out_of_domain, 
                       v.misinfo, v.rightinfo, v.confidence_score, v.sources, v.created_at
                """
                
                result = session.run(query)
                stored_verifications = []
                
                for record in result:
                    stored_keywords = record['v.keywords']
                    if not stored_keywords:
                        continue
                    
                    # Calculate similarity
                    similarity = self._calculate_keyword_similarity(keywords, stored_keywords)
                    
                    if similarity >= threshold:
                        stored_verifications.append({
                            'input_id': record['v.input_id'],
                            'similarity': similarity,
                            'correctness': record['v.correctness'],
                            'out_of_domain': record['v.out_of_domain'],
                            'misinfo': record['v.misinfo'],
                            'rightinfo': record['v.rightinfo'],
                            'confidence_score': record['v.confidence_score'],
                            'sources': record['v.sources'],
                            'created_at': record['v.created_at']
                        })
                
                # Sort by similarity score
                stored_verifications.sort(key=lambda x: x['similarity'], reverse=True)
                return stored_verifications
                
        except Exception as e:
            print(f"Error finding similar verifications: {e}")
            return []

    def _calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """Calculate Jaccard similarity between two keyword lists"""
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0

    def store_verification(self, result: VerificationResult) -> bool:
        """Store verification result in Neo4j"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                CREATE (v:Verification {
                    input_id: $input_id,
                    keywords: $keywords,
                    correctness: $correctness,
                    out_of_domain: $out_of_domain,
                    misinfo: $misinfo,
                    rightinfo: $rightinfo,
                    confidence_score: $confidence_score,
                    sources: $sources,
                    created_at: $created_at,
                    raw_text_hash: $raw_text_hash
                })
                """
                
                session.run(query, {
                    'input_id': result.input_id,
                    'keywords': result.keywords,
                    'correctness': result.correctness,
                    'out_of_domain': result.out_of_domain,
                    'misinfo': result.misinfo,
                    'rightinfo': result.rightinfo,
                    'confidence_score': result.confidence_score,
                    'sources': result.sources,
                    'created_at': result.created_at.isoformat(),
                    'raw_text_hash': result.raw_text_hash
                })
                
                print(f"✅ Stored verification {result.input_id} in Neo4j")
                return True
                
        except Exception as e:
            print(f"❌ Error storing verification: {e}")
            return False

    def get_verification_by_hash(self, text_hash: str) -> Optional[Dict]:
        """Get verification by exact text hash match"""
        if not self.driver:
            return None

        try:
            with self.driver.session() as session:
                query = """
                MATCH (v:Verification {raw_text_hash: $text_hash})
                RETURN v.input_id, v.keywords, v.correctness, v.out_of_domain,
                       v.misinfo, v.rightinfo, v.confidence_score, v.sources, v.created_at
                """
                
                result = session.run(query, {'text_hash': text_hash})
                record = result.single()
                
                if record:
                    return {
                        'input_id': record['v.input_id'],
                        'correctness': record['v.correctness'],
                        'out_of_domain': record['v.out_of_domain'],
                        'misinfo': record['v.misinfo'],
                        'rightinfo': record['v.rightinfo'],
                        'confidence_score': record['v.confidence_score'],
                        'sources': record['v.sources'],
                        'created_at': record['v.created_at']
                    }
                return None
                
        except Exception as e:
            print(f"Error getting verification by hash: {e}")
            return None

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()


# Global instance
neo4j_service = Neo4jService()
