"""
Semantic Analyzer Service

Uses sentence-transformers for embeddings and cosine similarity
to detect ENTITY_OVERLAP and SEMANTIC_AMBIGUITY issues.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Types of issues detected by the semantic analyzer."""
    ENTITY_OVERLAP = "ENTITY_OVERLAP"
    SEMANTIC_AMBIGUITY = "SEMANTIC_AMBIGUITY"


@dataclass
class SemanticIssue:
    """Represents a semantic issue detected during analysis."""
    issue_type: IssueType
    severity: str  # HIGH, MEDIUM, LOW
    description: str
    affected_elements: List[str]
    contexts: List[str]
    similarity_score: Optional[float] = None
    rule_id: Optional[str] = None
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity,
            "description": self.description,
            "affected_elements": self.affected_elements,
            "contexts": self.contexts,
            "similarity_score": self.similarity_score,
            "rule_id": self.rule_id,
            "recommendation": self.recommendation
        }


@dataclass
class EntityInfo:
    """Information about an entity for analysis."""
    name: str
    context: str
    domain: str
    domain_type: str
    entity_type: str
    attributes: List[str] = field(default_factory=list)
    description: str = ""
    
    def get_semantic_text(self) -> str:
        """Get text representation for embedding."""
        parts = [
            f"Entity: {self.name}",
            f"Context: {self.context}",
            f"Domain: {self.domain}",
            f"Type: {self.entity_type}"
        ]
        if self.attributes:
            parts.append(f"Attributes: {', '.join(self.attributes)}")
        if self.description:
            parts.append(f"Description: {self.description}")
        return " | ".join(parts)


@dataclass
class TermInfo:
    """Information about a term in ubiquitous language."""
    term: str
    definition: str
    context: str
    domain: str
    
    def get_semantic_text(self) -> str:
        """Get text representation for embedding."""
        return f"{self.term}: {self.definition}"


class SemanticAnalyzer:
    """
    Analyzes domain models for semantic issues using embeddings.
    
    Detects:
    - ENTITY_OVERLAP: Same entity appears in multiple bounded contexts
    - SEMANTIC_AMBIGUITY: Same term has different meanings or is poorly defined
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.75
    ):
        """
        Initialize the semantic analyzer.
        
        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Threshold for considering entities similar
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self._model = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of the embedding model."""
        if not self._initialized:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self._initialized = True
                logger.info("Embedding model loaded successfully")
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
    
    def compute_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Compute embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of embeddings
        """
        self._ensure_initialized()
        return self._model.encode(texts, convert_to_numpy=True)
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Normalize and compute dot product
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
    
    def extract_entities(self, domain_model: Dict[str, Any]) -> List[EntityInfo]:
        """
        Extract all entities from a domain model.
        
        Args:
            domain_model: The domain model JSON
            
        Returns:
            List of EntityInfo objects
        """
        entities = []
        domain_map = domain_model.get("domainMap", {})
        
        # Process all domain types
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for domain in domains:
                context = domain.get("boundedContext", {}).get("name", "Unknown")
                domain_name = domain.get("name", "Unknown")
                d_type = domain.get("type", "unknown")
                
                for entity in domain.get("entities", []):
                    # Skip reference-only entities (ownership resolved in previous iteration)
                    if entity.get("_referenceOnly"):
                        continue
                    attrs = [
                        attr.get("name", "")
                        for attr in entity.get("attributes", [])
                    ]
                    entities.append(EntityInfo(
                        name=entity.get("name", "Unknown"),
                        context=context,
                        domain=domain_name,
                        domain_type=d_type,
                        entity_type=entity.get("type", "entity"),
                        attributes=attrs
                    ))
        
        return entities
    
    def extract_terms(self, domain_model: Dict[str, Any]) -> List[TermInfo]:
        """
        Extract all terms from ubiquitous language definitions.
        
        Args:
            domain_model: The domain model JSON
            
        Returns:
            List of TermInfo objects
        """
        terms = []
        domain_map = domain_model.get("domainMap", {})
        
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for domain in domains:
                context = domain.get("boundedContext", {}).get("name", "Unknown")
                domain_name = domain.get("name", "Unknown")
                ubiquitous_language = domain.get("boundedContext", {}).get("ubiquitousLanguage", {})
                
                for term, definition in ubiquitous_language.items():
                    terms.append(TermInfo(
                        term=term,
                        definition=definition,
                        context=context,
                        domain=domain_name
                    ))
        
        return terms
    
    def detect_entity_overlaps(
        self,
        entities: List[EntityInfo]
    ) -> List[SemanticIssue]:
        """
        Detect entities that overlap across bounded contexts.
        
        Args:
            entities: List of entities to analyze
            
        Returns:
            List of detected ENTITY_OVERLAP issues
        """
        issues = []
        
        if len(entities) < 2:
            return issues
        
        # Group entities by name (case-insensitive)
        entities_by_name: Dict[str, List[EntityInfo]] = {}
        for entity in entities:
            key = entity.name.lower()
            if key not in entities_by_name:
                entities_by_name[key] = []
            entities_by_name[key].append(entity)
        
        # Check for same-name entities in different contexts
        for name, entity_list in entities_by_name.items():
            if len(entity_list) > 1:
                # Check if they're in different contexts
                contexts = set(e.context for e in entity_list)
                if len(contexts) > 1:
                    issues.append(SemanticIssue(
                        issue_type=IssueType.ENTITY_OVERLAP,
                        severity="HIGH",
                        description=f"Entity '{entity_list[0].name}' is defined in multiple bounded contexts",
                        affected_elements=[e.name for e in entity_list],
                        contexts=list(contexts),
                        rule_id="EO-001",
                        recommendation=(
                            f"Consider using different representations of "
                            f"'{entity_list[0].name}' in each context with explicit "
                            f"translation/mapping between them, or consolidate "
                            f"ownership in one context."
                        )
                    ))
        
        # Also check semantic similarity for differently named entities
        self._ensure_initialized()
        
        # Get embeddings for all entities
        texts = [e.get_semantic_text() for e in entities]
        embeddings = self.compute_embeddings(texts)
        
        # Compare entities across different contexts
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if j <= i:
                    continue
                # Skip if same context
                if entity1.context == entity2.context:
                    continue
                # Skip if same name (already caught above)
                if entity1.name.lower() == entity2.name.lower():
                    continue
                
                similarity = self.compute_similarity(embeddings[i], embeddings[j])
                
                if similarity >= self.similarity_threshold:
                    # Check if attributes overlap significantly
                    attr_overlap = self._compute_attribute_overlap(
                        entity1.attributes, entity2.attributes
                    )
                    
                    if attr_overlap > 0.5:  # More than 50% attribute overlap
                        issues.append(SemanticIssue(
                            issue_type=IssueType.ENTITY_OVERLAP,
                            severity="MEDIUM",
                            description=(
                                f"Entities '{entity1.name}' and '{entity2.name}' "
                                f"are semantically similar and may represent the same concept"
                            ),
                            affected_elements=[entity1.name, entity2.name],
                            contexts=[entity1.context, entity2.context],
                            similarity_score=similarity,
                            rule_id="EO-002",
                            recommendation=(
                                f"Review if '{entity1.name}' and '{entity2.name}' "
                                f"represent the same real-world concept. If so, "
                                f"clarify ownership and add explicit mapping."
                            )
                        ))
        
        return issues
    
    def _compute_attribute_overlap(
        self,
        attrs1: List[str],
        attrs2: List[str]
    ) -> float:
        """Compute overlap ratio between two attribute lists."""
        if not attrs1 or not attrs2:
            return 0.0
        
        set1 = set(a.lower() for a in attrs1)
        set2 = set(a.lower() for a in attrs2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def detect_semantic_ambiguities(
        self,
        terms: List[TermInfo]
    ) -> List[SemanticIssue]:
        """
        Detect ambiguous or inconsistent term definitions.
        
        Args:
            terms: List of terms to analyze
            
        Returns:
            List of detected SEMANTIC_AMBIGUITY issues
        """
        issues = []
        
        if len(terms) < 2:
            return issues
        
        # Group terms by name
        terms_by_name: Dict[str, List[TermInfo]] = {}
        for term in terms:
            key = term.term.lower()
            if key not in terms_by_name:
                terms_by_name[key] = []
            terms_by_name[key].append(term)
        
        self._ensure_initialized()
        
        # Check for same-name terms with different definitions
        for name, term_list in terms_by_name.items():
            if len(term_list) > 1:
                # Get embeddings for definitions
                definitions = [t.definition for t in term_list]
                embeddings = self.compute_embeddings(definitions)
                
                # Check pairwise similarity
                for i in range(len(term_list)):
                    for j in range(i + 1, len(term_list)):
                        similarity = self.compute_similarity(
                            embeddings[i], embeddings[j]
                        )
                        
                        # Low similarity = different meanings = ambiguity
                        if similarity < 0.7:
                            issues.append(SemanticIssue(
                                issue_type=IssueType.SEMANTIC_AMBIGUITY,
                                severity="HIGH",
                                description=(
                                    f"Term '{term_list[i].term}' has different definitions "
                                    f"across contexts"
                                ),
                                affected_elements=[
                                    f"{t.term} ({t.context}): {t.definition}"
                                    for t in [term_list[i], term_list[j]]
                                ],
                                contexts=[term_list[i].context, term_list[j].context],
                                similarity_score=similarity,
                                rule_id="BC-001",
                                recommendation=(
                                    f"The term '{term_list[i].term}' should have a consistent "
                                    f"meaning or be explicitly mapped between contexts. "
                                    f"Consider renaming to make the distinction clear."
                                )
                            ))
        
        # Detect vague/generic terms
        vague_indicators = [
            "any", "all", "generic", "various", "misc", "other",
            "thing", "stuff", "data", "info", "object"
        ]
        
        for term in terms:
            definition_lower = term.definition.lower()
            term_lower = term.term.lower()
            
            # Check for vague definitions
            if any(v in definition_lower for v in vague_indicators):
                issues.append(SemanticIssue(
                    issue_type=IssueType.SEMANTIC_AMBIGUITY,
                    severity="MEDIUM",
                    description=f"Term '{term.term}' has a vague or generic definition",
                    affected_elements=[f"{term.term}: {term.definition}"],
                    contexts=[term.context],
                    rule_id="BC-001",
                    recommendation=(
                        f"Provide a more specific definition for '{term.term}' "
                        f"that clearly identifies its role in the domain."
                    )
                ))
            
            # Check for overly generic entity names
            generic_names = ["transaction", "item", "data", "record", "object", "entity"]
            if term_lower in generic_names:
                issues.append(SemanticIssue(
                    issue_type=IssueType.SEMANTIC_AMBIGUITY,
                    severity="MEDIUM",
                    description=f"Term '{term.term}' is too generic for a domain concept",
                    affected_elements=[f"{term.term}: {term.definition}"],
                    contexts=[term.context],
                    rule_id="BC-001",
                    recommendation=(
                        f"Consider using a more domain-specific name instead of "
                        f"'{term.term}'. For example, 'PaymentTransaction' instead "
                        f"of 'Transaction'."
                    )
                ))
        
        return issues
    
    def _get_resolved_elements(self, domain_model: Dict[str, Any]) -> set:
        """Extract element names that have already been resolved by user answers."""
        resolved = set()
        for fix in domain_model.get("_userGuidedFixes", []):
            for elem in fix.get("affected_elements", []):
                resolved.add(elem.lower())
        for decision in domain_model.get("_ownershipDecisions", []):
            entity = decision.get("entity", "")
            if entity:
                resolved.add(entity.lower())
        for resolution in domain_model.get("_conflictResolutions", []):
            for elem in resolution.get("affected_elements", []):
                resolved.add(elem.lower())
        return resolved

    def analyze(self, domain_model: Dict[str, Any]) -> List[SemanticIssue]:
        """
        Perform full semantic analysis on a domain model.

        Args:
            domain_model: The domain model JSON to analyze

        Returns:
            List of all detected semantic issues
        """
        logger.info("Starting semantic analysis...")

        resolved = self._get_resolved_elements(domain_model)
        if resolved:
            logger.info(f"Skipping already-resolved elements: {resolved}")

        issues = []

        # Extract and analyze entities
        entities = self.extract_entities(domain_model)
        logger.info(f"Extracted {len(entities)} entities")

        entity_issues = self.detect_entity_overlaps(entities)
        # Filter out issues whose affected elements are ALL already resolved
        if resolved:
            entity_issues = [
                issue for issue in entity_issues
                if not all(elem.lower() in resolved for elem in issue.affected_elements)
            ]
        issues.extend(entity_issues)
        logger.info(f"Found {len(entity_issues)} entity overlap issues")

        # Extract and analyze terms
        terms = self.extract_terms(domain_model)
        logger.info(f"Extracted {len(terms)} terms")

        term_issues = self.detect_semantic_ambiguities(terms)
        if resolved:
            term_issues = [
                issue for issue in term_issues
                if not all(elem.lower() in resolved for elem in issue.affected_elements)
            ]
        issues.extend(term_issues)
        logger.info(f"Found {len(term_issues)} semantic ambiguity issues")

        logger.info(f"Semantic analysis complete. Total issues: {len(issues)}")
        return issues
