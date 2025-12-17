"""
Question Generator Service

Generates follow-up questions based on detected issues.
Uses templates from validation_checklist.json and LLM for contextual questions.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.services.semantic_analyzer import SemanticIssue, IssueType
from app.services.conflict_detector import ConflictIssue, ConflictType

logger = logging.getLogger(__name__)


@dataclass
class FollowUpQuestion:
    """Represents a follow-up question for stakeholders."""
    question_id: str
    question: str
    context: str
    related_issue_type: str
    severity: str
    affected_elements: List[str]
    suggested_answers: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "question_id": self.question_id,
            "question": self.question,
            "context": self.context,
            "related_issue_type": self.related_issue_type,
            "severity": self.severity,
            "affected_elements": self.affected_elements,
            "suggested_answers": self.suggested_answers
        }


class QuestionGenerator:
    """
    Generates follow-up questions based on detected issues.
    
    Uses validation checklist templates and contextual generation
    to create meaningful questions for domain experts.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the question generator.
        
        Args:
            settings: Application settings (uses global if not provided)
        """
        self.settings = settings or get_settings()
        self._validation_checklist: Optional[dict] = None
        self._question_counter = 0
    
    @property
    def validation_checklist(self) -> dict:
        """Lazy load validation checklist."""
        if self._validation_checklist is None:
            self._validation_checklist = self.settings.load_validation_checklist()
        return self._validation_checklist
    
    def _get_next_question_id(self) -> str:
        """Generate next question ID."""
        self._question_counter += 1
        return f"FUQ-{self._question_counter:03d}"
    
    def _get_template_for_rule(self, rule_id: str) -> Optional[str]:
        """Get question template for a specific rule."""
        rules = self.validation_checklist.get("validation_rules", {})
        
        for category in rules.values():
            if isinstance(category, dict) and "rules" in category:
                for rule in category["rules"]:
                    if rule.get("id") == rule_id:
                        return rule.get("question_template")
        
        return None
    
    def generate_from_semantic_issue(
        self,
        issue: SemanticIssue
    ) -> FollowUpQuestion:
        """
        Generate a follow-up question from a semantic issue.
        
        Args:
            issue: The semantic issue to generate question for
            
        Returns:
            A follow-up question
        """
        # Try to get template from checklist
        template = None
        if issue.rule_id:
            template = self._get_template_for_rule(issue.rule_id)
        
        if issue.issue_type == IssueType.ENTITY_OVERLAP:
            if template:
                # Fill template - handle missing keys gracefully
                try:
                    question = template.format(
                        entity_name=issue.affected_elements[0] if issue.affected_elements else "entity",
                        context_1=issue.contexts[0] if issue.contexts else "context1",
                        context_2=issue.contexts[1] if len(issue.contexts) > 1 else "context2"
                    )
                except KeyError:
                    template = None
            
            if not template:
                # Default question
                entities = ", ".join(issue.affected_elements[:2])
                contexts = " and ".join(issue.contexts)
                question = (
                    f"The entity/entities '{entities}' appear in multiple bounded contexts "
                    f"({contexts}). Should they be:\n"
                    f"1. The same entity shared between contexts (with clear ownership)?\n"
                    f"2. Different representations with explicit mapping?\n"
                    f"3. Merged into a single context?"
                )
            
            suggested = [
                "Same entity with shared ownership",
                "Different representations requiring translation",
                "Consolidate into single bounded context"
            ]
        
        elif issue.issue_type == IssueType.SEMANTIC_AMBIGUITY:
            if template:
                try:
                    question = template.format(
                        term=issue.affected_elements[0] if issue.affected_elements else "term",
                        context_name=issue.contexts[0] if issue.contexts else "context"
                    )
                except KeyError:
                    template = None
            
            if not template:
                term = issue.affected_elements[0].split(":")[0] if issue.affected_elements else "term"
                question = (
                    f"The term '{term}' appears to have ambiguous or inconsistent definitions. "
                    f"Can you provide:\n"
                    f"1. A precise definition for this term?\n"
                    f"2. Different names if it means different things in different contexts?\n"
                    f"3. The primary context that owns this concept?"
                )
            
            suggested = [
                "Provide single canonical definition",
                "Use different names per context",
                "Remove/replace with more specific terms"
            ]
        
        else:
            question = f"Please clarify: {issue.description}"
            suggested = None
        
        return FollowUpQuestion(
            question_id=self._get_next_question_id(),
            question=question,
            context=issue.contexts[0] if issue.contexts else "General",
            related_issue_type=issue.issue_type.value,
            severity=issue.severity,
            affected_elements=issue.affected_elements,
            suggested_answers=suggested
        )
    
    def generate_from_conflict_issue(
        self,
        issue: ConflictIssue
    ) -> FollowUpQuestion:
        """
        Generate a follow-up question from a conflict issue.
        
        Args:
            issue: The conflict issue to generate question for
            
        Returns:
            A follow-up question
        """
        template = None
        if issue.rule_id:
            template = self._get_template_for_rule(issue.rule_id)
        
        if issue.conflict_type == ConflictType.REQUIREMENT_CONFLICT:
            reqs = "\n".join(f"  - {el}" for el in issue.affected_elements[:2])
            question = (
                f"There is a conflict between these requirements:\n{reqs}\n\n"
                f"Which should take precedence, or how should this conflict be resolved?"
            )
            suggested = [
                "Requirement 1 takes precedence",
                "Requirement 2 takes precedence",
                "Define conditions when each applies",
                "Modify both to remove conflict"
            ]
        
        elif issue.conflict_type == ConflictType.DUPLICATE_EVENT:
            event = issue.affected_elements[0] if issue.affected_elements else "event"
            emitters = ", ".join(issue.contexts)
            question = (
                f"The event '{event}' is being emitted by multiple domains: {emitters}.\n"
                f"Which domain should own this event?"
            )
            suggested = [f"Owned by {ctx}" for ctx in issue.contexts]
            suggested.append("Create separate events per domain")
        
        elif issue.conflict_type == ConflictType.NAMING_VIOLATION:
            event = issue.affected_elements[0] if issue.affected_elements else "event"
            question = (
                f"The event '{event}' uses present/imperative tense instead of past tense.\n"
                f"Domain events should describe what has happened.\n"
                f"What is the correct past-tense name for this event?"
            )
            # Suggest past tense versions
            base_name = event
            suggested = [
                f"{base_name}d",
                f"{base_name}ed",
                f"{base_name}Completed",
                f"{base_name}Processed"
            ]
        
        elif issue.conflict_type == ConflictType.INCOMPATIBLE_PATTERN:
            question = (
                f"There is an incompatibility between communication patterns:\n"
                f"{issue.description}\n\n"
                f"How should this be resolved?"
            )
            suggested = [
                "Add synchronous communication option",
                "Relax consistency requirement to eventual",
                "Redesign integration pattern"
            ]
        
        elif issue.conflict_type == ConflictType.MISCLASSIFIED_DOMAIN:
            domain = issue.affected_elements[0] if issue.affected_elements else "domain"
            question = (
                f"The domain '{domain}' may be misclassified.\n"
                f"{issue.description}\n\n"
                f"What is the correct classification?"
            )
            suggested = ["Core Domain", "Supporting Domain", "Generic Domain"]
        
        else:
            question = f"Please clarify: {issue.description}"
            suggested = None
        
        return FollowUpQuestion(
            question_id=self._get_next_question_id(),
            question=question,
            context=issue.contexts[0] if issue.contexts else "General",
            related_issue_type=issue.conflict_type.value,
            severity=issue.severity,
            affected_elements=issue.affected_elements,
            suggested_answers=suggested
        )
    
    def generate_questions(
        self,
        semantic_issues: List[SemanticIssue],
        conflict_issues: List[ConflictIssue],
        max_questions: Optional[int] = None
    ) -> List[FollowUpQuestion]:
        """
        Generate follow-up questions from all detected issues.
        
        Args:
            semantic_issues: List of semantic issues
            conflict_issues: List of conflict issues
            max_questions: Maximum number of questions to generate
            
        Returns:
            List of follow-up questions
        """
        logger.info("Generating follow-up questions...")
        
        max_q = max_questions or self.settings.MAX_FOLLOW_UP_QUESTIONS
        questions = []
        
        # Combine and sort issues by severity
        all_issues = []
        
        for issue in semantic_issues:
            all_issues.append(("semantic", issue, issue.severity))
        
        for issue in conflict_issues:
            all_issues.append(("conflict", issue, issue.severity))
        
        # Sort by severity (HIGH first)
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        all_issues.sort(key=lambda x: severity_order.get(x[2], 3))
        
        # Generate questions for top issues
        for issue_type, issue, _ in all_issues[:max_q]:
            if issue_type == "semantic":
                questions.append(self.generate_from_semantic_issue(issue))
            else:
                questions.append(self.generate_from_conflict_issue(issue))
        
        logger.info(f"Generated {len(questions)} follow-up questions")
        return questions
    
    def prioritize_questions(
        self,
        questions: List[FollowUpQuestion]
    ) -> List[FollowUpQuestion]:
        """
        Prioritize questions by impact and actionability.
        
        Args:
            questions: List of questions to prioritize
            
        Returns:
            Sorted list of questions
        """
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        
        # Sort by severity, then by number of affected elements
        return sorted(
            questions,
            key=lambda q: (
                severity_order.get(q.severity, 3),
                -len(q.affected_elements)
            )
        )
