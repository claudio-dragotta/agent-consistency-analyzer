"""
Model Refiner Service

Applies corrections and suggestions to produce a refined domain model
ready for Agent 3 (Specification Generator).
"""

import logging
import copy
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.config import Settings, get_settings
from app.services.semantic_analyzer import SemanticIssue, IssueType
from app.services.conflict_detector import ConflictIssue, ConflictType
from app.services.question_generator import FollowUpQuestion

logger = logging.getLogger(__name__)


@dataclass
class Refinement:
    """Represents a refinement applied to the model."""
    refinement_id: str
    refinement_type: str  # "auto", "suggested", "manual"
    description: str
    applied: bool
    source_issue_type: str
    affected_path: str  # JSON path to affected element
    original_value: Any
    new_value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "refinement_id": self.refinement_id,
            "refinement_type": self.refinement_type,
            "description": self.description,
            "applied": self.applied,
            "source_issue_type": self.source_issue_type,
            "affected_path": self.affected_path,
            "original_value": str(self.original_value)[:100],
            "new_value": str(self.new_value)[:100]
        }


@dataclass
class RefinementReport:
    """Summary of all refinements applied to a model."""
    total_issues: int
    auto_fixed: int
    requires_manual: int
    refinements: List[Refinement]
    unresolved_issues: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_issues": self.total_issues,
            "auto_fixed": self.auto_fixed,
            "requires_manual": self.requires_manual,
            "refinements": [r.to_dict() for r in self.refinements],
            "unresolved_issues": self.unresolved_issues
        }


class ModelRefiner:
    """
    Applies corrections and refinements to domain models.
    
    Produces a refined model for Agent 3 with:
    - Automatic fixes for clear violations
    - Annotations for manual resolution
    - Metadata about applied changes
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the model refiner.
        
        Args:
            settings: Application settings (uses global if not provided)
        """
        self.settings = settings or get_settings()
        self._refinement_counter = 0
    
    def _get_next_refinement_id(self) -> str:
        """Generate next refinement ID."""
        self._refinement_counter += 1
        return f"REF-{self._refinement_counter:03d}"
    
    def _deep_copy_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of the domain model."""
        return copy.deepcopy(model)
    
    def _find_entity_in_model(
        self,
        model: Dict[str, Any],
        entity_name: str,
        context_name: Optional[str] = None
    ) -> Tuple[Optional[Dict], str]:
        """
        Find an entity in the model by name and optionally context.
        
        Returns:
            Tuple of (entity dict, JSON path)
        """
        domain_map = model.get("domainMap", {})
        
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for i, domain in enumerate(domains):
                context = domain.get("boundedContext", {}).get("name", "")
                
                if context_name and context != context_name:
                    continue
                
                for j, entity in enumerate(domain.get("entities", [])):
                    if entity.get("name", "").lower() == entity_name.lower():
                        path = f"domainMap.{domain_type}[{i}].entities[{j}]"
                        return entity, path
        
        return None, ""
    
    def _find_event_in_model(
        self,
        model: Dict[str, Any],
        event_name: str
    ) -> Tuple[Optional[Dict], str, int]:
        """
        Find an event in the model by name.
        
        Returns:
            Tuple of (event dict, JSON path, index)
        """
        events = model.get("eventDrivenModel", {}).get("domainEvents", [])
        
        for i, event in enumerate(events):
            if event.get("name", "").lower() == event_name.lower():
                return event, f"eventDrivenModel.domainEvents[{i}]", i
        
        return None, "", -1
    
    def _find_domain_in_model(
        self,
        model: Dict[str, Any],
        domain_name: str
    ) -> Tuple[Optional[Dict], str, str]:
        """
        Find a domain in the model by name.
        
        Returns:
            Tuple of (domain dict, JSON path, domain type)
        """
        domain_map = model.get("domainMap", {})
        
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for i, domain in enumerate(domains):
                if domain.get("name", "").lower() == domain_name.lower():
                    return domain, f"domainMap.{domain_type}[{i}]", domain_type
        
        return None, "", ""
    
    def fix_naming_violation(
        self,
        model: Dict[str, Any],
        event_name: str
    ) -> Optional[Refinement]:
        """
        Auto-fix naming violation by converting event name to past tense.
        
        Args:
            model: The domain model (modified in place)
            event_name: Name of the event to fix
            
        Returns:
            Refinement record if fix was applied
        """
        event, path, idx = self._find_event_in_model(model, event_name)
        
        if not event:
            return None
        
        old_name = event["name"]
        
        # Convert to past tense
        new_name = old_name
        if old_name.endswith("e"):
            new_name = old_name + "d"
        elif old_name.endswith(("y",)):
            new_name = old_name[:-1] + "ied"
        else:
            new_name = old_name + "ed"
        
        # Apply fix
        event["name"] = new_name
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="auto",
            description=f"Renamed event from '{old_name}' to '{new_name}' (past tense)",
            applied=True,
            source_issue_type="NAMING_VIOLATION",
            affected_path=path,
            original_value=old_name,
            new_value=new_name
        )
    
    def annotate_entity_overlap(
        self,
        model: Dict[str, Any],
        issue: SemanticIssue
    ) -> Optional[Refinement]:
        """
        Annotate entity overlap for manual resolution.
        
        Args:
            model: The domain model (modified in place)
            issue: The entity overlap issue
            
        Returns:
            Refinement record
        """
        # Add annotation to model metadata
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        
        annotation = {
            "type": "ENTITY_OVERLAP",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        
        model["_validationAnnotations"].append(annotation)
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotated entity overlap: {', '.join(issue.affected_elements)}",
            applied=False,
            source_issue_type="ENTITY_OVERLAP",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )
    
    def annotate_semantic_ambiguity(
        self,
        model: Dict[str, Any],
        issue: SemanticIssue
    ) -> Optional[Refinement]:
        """
        Annotate semantic ambiguity for manual resolution.
        
        Args:
            model: The domain model (modified in place)
            issue: The semantic ambiguity issue
            
        Returns:
            Refinement record
        """
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        
        annotation = {
            "type": "SEMANTIC_AMBIGUITY",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        
        model["_validationAnnotations"].append(annotation)
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotated semantic ambiguity in contexts: {', '.join(issue.contexts)}",
            applied=False,
            source_issue_type="SEMANTIC_AMBIGUITY",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )
    
    def annotate_requirement_conflict(
        self,
        model: Dict[str, Any],
        issue: ConflictIssue
    ) -> Optional[Refinement]:
        """
        Annotate requirement conflict for manual resolution.
        
        Args:
            model: The domain model (modified in place)
            issue: The requirement conflict issue
            
        Returns:
            Refinement record
        """
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        
        annotation = {
            "type": "REQUIREMENT_CONFLICT",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "evidence": issue.evidence,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        
        model["_validationAnnotations"].append(annotation)
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotated requirement conflict in: {', '.join(issue.contexts)}",
            applied=False,
            source_issue_type="REQUIREMENT_CONFLICT",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )
    
    def fix_duplicate_event(
        self,
        model: Dict[str, Any],
        issue: ConflictIssue
    ) -> Optional[Refinement]:
        """
        Annotate duplicate event for manual resolution.
        Cannot auto-fix as ownership decision is needed.
        
        Args:
            model: The domain model (modified in place)
            issue: The duplicate event issue
            
        Returns:
            Refinement record
        """
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        
        annotation = {
            "type": "DUPLICATE_EVENT",
            "affectedElements": issue.affected_elements,
            "emitters": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        
        model["_validationAnnotations"].append(annotation)
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotated duplicate event from emitters: {', '.join(issue.contexts)}",
            applied=False,
            source_issue_type="DUPLICATE_EVENT",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )
    
    def suggest_domain_reclassification(
        self,
        model: Dict[str, Any],
        issue: ConflictIssue
    ) -> Optional[Refinement]:
        """
        Suggest domain reclassification.
        
        Args:
            model: The domain model (modified in place)
            issue: The misclassified domain issue
            
        Returns:
            Refinement record
        """
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        
        domain_name = issue.affected_elements[0] if issue.affected_elements else "Unknown"
        
        annotation = {
            "type": "MISCLASSIFIED_DOMAIN",
            "domain": domain_name,
            "currentClassification": "core",  # It was flagged from core
            "suggestedClassification": "generic",
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        
        model["_validationAnnotations"].append(annotation)
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Suggested reclassification for domain: {domain_name}",
            applied=False,
            source_issue_type="MISCLASSIFIED_DOMAIN",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )
    
    def annotate_incompatible_pattern(
        self,
        model: Dict[str, Any],
        issue: ConflictIssue
    ) -> Optional[Refinement]:
        """
        Annotate incompatible pattern for manual resolution.
        
        Args:
            model: The domain model (modified in place)
            issue: The incompatible pattern issue
            
        Returns:
            Refinement record
        """
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        
        annotation = {
            "type": "INCOMPATIBLE_PATTERN",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        
        model["_validationAnnotations"].append(annotation)
        
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotated incompatible pattern: {issue.description[:50]}...",
            applied=False,
            source_issue_type="INCOMPATIBLE_PATTERN",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )
    
    def refine_model(
        self,
        domain_model: Dict[str, Any],
        semantic_issues: List[SemanticIssue],
        conflict_issues: List[ConflictIssue],
        follow_up_questions: List[FollowUpQuestion],
        apply_auto_fixes: bool = True
    ) -> Tuple[Dict[str, Any], RefinementReport]:
        """
        Apply refinements to the domain model.
        
        Args:
            domain_model: Original domain model
            semantic_issues: Detected semantic issues
            conflict_issues: Detected conflict issues
            follow_up_questions: Generated follow-up questions
            apply_auto_fixes: Whether to apply automatic fixes
            
        Returns:
            Tuple of (refined model, refinement report)
        """
        logger.info("Starting model refinement...")
        
        # Create deep copy to avoid modifying original
        refined = self._deep_copy_model(domain_model)
        refinements = []
        unresolved = []
        auto_fixed = 0
        
        # Update metadata
        if "metadata" not in refined:
            refined["metadata"] = {}
        
        refined["metadata"]["refinedAt"] = datetime.utcnow().isoformat() + "Z"
        refined["metadata"]["refinedBy"] = "agent-2-consistency-analyzer"
        refined["metadata"]["validationVersion"] = "1.0.0"
        
        # Process semantic issues
        for issue in semantic_issues:
            if issue.issue_type == IssueType.ENTITY_OVERLAP:
                ref = self.annotate_entity_overlap(refined, issue)
                if ref:
                    refinements.append(ref)
                    unresolved.append(f"ENTITY_OVERLAP: {issue.description}")
            
            elif issue.issue_type == IssueType.SEMANTIC_AMBIGUITY:
                ref = self.annotate_semantic_ambiguity(refined, issue)
                if ref:
                    refinements.append(ref)
                    unresolved.append(f"SEMANTIC_AMBIGUITY: {issue.description}")
        
        # Process conflict issues
        for issue in conflict_issues:
            if issue.conflict_type == ConflictType.NAMING_VIOLATION:
                if apply_auto_fixes:
                    # Extract event name from affected elements
                    event_name = issue.affected_elements[0] if issue.affected_elements else ""
                    ref = self.fix_naming_violation(refined, event_name)
                    if ref and ref.applied:
                        refinements.append(ref)
                        auto_fixed += 1
                    else:
                        unresolved.append(f"NAMING_VIOLATION: {issue.description}")
                else:
                    unresolved.append(f"NAMING_VIOLATION: {issue.description}")
            
            elif issue.conflict_type == ConflictType.REQUIREMENT_CONFLICT:
                ref = self.annotate_requirement_conflict(refined, issue)
                if ref:
                    refinements.append(ref)
                    unresolved.append(f"REQUIREMENT_CONFLICT: {issue.description}")
            
            elif issue.conflict_type == ConflictType.DUPLICATE_EVENT:
                ref = self.fix_duplicate_event(refined, issue)
                if ref:
                    refinements.append(ref)
                    unresolved.append(f"DUPLICATE_EVENT: {issue.description}")
            
            elif issue.conflict_type == ConflictType.MISCLASSIFIED_DOMAIN:
                ref = self.suggest_domain_reclassification(refined, issue)
                if ref:
                    refinements.append(ref)
                    unresolved.append(f"MISCLASSIFIED_DOMAIN: {issue.description}")
            
            elif issue.conflict_type == ConflictType.INCOMPATIBLE_PATTERN:
                ref = self.annotate_incompatible_pattern(refined, issue)
                if ref:
                    refinements.append(ref)
                    unresolved.append(f"INCOMPATIBLE_PATTERN: {issue.description}")
        
        # Add follow-up questions to model
        refined["_followUpQuestions"] = [q.to_dict() for q in follow_up_questions]
        
        # Create report
        total_issues = len(semantic_issues) + len(conflict_issues)
        report = RefinementReport(
            total_issues=total_issues,
            auto_fixed=auto_fixed,
            requires_manual=total_issues - auto_fixed,
            refinements=refinements,
            unresolved_issues=unresolved
        )
        
        logger.info(
            f"Model refinement complete. "
            f"Total issues: {total_issues}, "
            f"Auto-fixed: {auto_fixed}, "
            f"Requires manual: {report.requires_manual}"
        )
        
        return refined, report
