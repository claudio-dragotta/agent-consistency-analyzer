"""
Agent 2 Services Package

This package contains the core services for the Consistency & Conflict Analyzer:
- SemanticAnalyzer: Embedding-based similarity detection
- ConflictDetector: LLM-powered conflict detection
- QuestionGenerator: Follow-up question generation
- ModelRefiner: Model refinement based on detected issues
"""

from app.services.semantic_analyzer import SemanticAnalyzer, SemanticIssue, IssueType
from app.services.conflict_detector import ConflictDetector, ConflictIssue, ConflictType
from app.services.question_generator import QuestionGenerator, FollowUpQuestion
from app.services.model_refiner import ModelRefiner, Refinement, RefinementReport

__all__ = [
    # Semantic Analyzer
    "SemanticAnalyzer",
    "SemanticIssue", 
    "IssueType",
    # Conflict Detector
    "ConflictDetector",
    "ConflictIssue",
    "ConflictType",
    # Question Generator
    "QuestionGenerator",
    "FollowUpQuestion",
    # Model Refiner
    "ModelRefiner",
    "Refinement",
    "RefinementReport"
]
