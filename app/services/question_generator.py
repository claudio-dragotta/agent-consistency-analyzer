"""
Question Generator Service

Generates follow-up questions based on detected issues.
Uses templates from validation_checklist.json and LLM for contextual questions.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx

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

    When use_llm=True, it adds a small number of LLM-generated questions
    for high-severity issues to enrich the template-based set.
    """
    LLM_EXTRA_QUESTIONS = 3
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the question generator.
        
        Args:
            settings: Application settings (uses global if not provided)
        """
        self.settings = settings or get_settings()
        self._validation_checklist: Optional[dict] = None
        self._question_counter = 0

    async def _call_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Ollama API to generate follow-up questions."""
        url = self.settings.get_ollama_generate_url()
        payload = {
            "model": self.settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.settings.OLLAMA_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    def _normalize_question(self, text: str) -> str:
        """Normalize question text for deduplication."""
        return re.sub(r"\s+", " ", text.strip().lower())

    def _issue_to_prompt_dict(self, issue_type: str, severity: str, description: str,
                              affected_elements: List[str], contexts: List[str]) -> Dict[str, Any]:
        """Convert an issue to a compact dict for LLM prompting."""
        return {
            "issue_type": issue_type,
            "severity": severity,
            "description": description,
            "affected_elements": affected_elements,
            "contexts": contexts
        }

    async def _generate_llm_questions(
        self,
        issues: List[Dict[str, Any]],
        max_questions: int
    ) -> List[FollowUpQuestion]:
        """Generate extra questions with LLM based on top issues."""
        if not issues or max_questions <= 0:
            return []

        system_prompt = (
            "You are a Domain-Driven Design analyst. "
            "Generate follow-up questions for domain experts to clarify issues. "
            "Return ONLY a valid JSON array (no markdown). Each item must include: "
            "question, severity, related_issue_type, affected_elements, context, "
            "suggested_answers (optional array of short hints)."
        )

        prompt = (
            "Generate up to "
            f"{max_questions} follow-up questions for these high-severity issues:\n\n"
            f"{json.dumps(issues, indent=2)}\n\n"
            "Return ONLY a JSON array."
        )

        try:
            response = await self._call_ollama(prompt, system_prompt)
            raw = response.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?\n?", "", raw).strip()
                raw = raw.strip("`").strip()
            parsed = json.loads(raw)
        except Exception as e:
            logger.warning(f"LLM question generation failed: {e}")
            return []

        questions: List[FollowUpQuestion] = []
        if isinstance(parsed, list):
            for item in parsed[:max_questions]:
                if not isinstance(item, dict) or "question" not in item:
                    continue
                questions.append(FollowUpQuestion(
                    question_id=self._get_next_question_id(),
                    question=str(item.get("question", "")).strip(),
                    context=str(item.get("context", "General")),
                    related_issue_type=str(item.get("related_issue_type", "UNKNOWN")),
                    severity=str(item.get("severity", "MEDIUM")),
                    affected_elements=list(item.get("affected_elements", []) or []),
                    suggested_answers=item.get("suggested_answers")
                ))
        return questions
    
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
    
    async def generate_questions(
        self,
        semantic_issues: List[SemanticIssue],
        conflict_issues: List[ConflictIssue],
        max_questions: Optional[int] = None,
        use_llm: bool = False
    ) -> List[FollowUpQuestion]:
        """
        Generate follow-up questions from all detected issues.
        
        Args:
            semantic_issues: List of semantic issues
            conflict_issues: List of conflict issues
            max_questions: Maximum number of questions to generate
            use_llm: Whether to enrich questions using LLM
            
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

        # Optional LLM enrichment for high-severity issues
        if use_llm and len(questions) < max_q:
            high_severity = [i for i in all_issues if i[2] == "HIGH"]
            if high_severity:
                remaining = max_q - len(questions)
                extra_cap = min(self.LLM_EXTRA_QUESTIONS, remaining)

                llm_issues: List[Dict[str, Any]] = []
                for issue_type, issue, severity in high_severity:
                    if issue_type == "semantic":
                        llm_issues.append(self._issue_to_prompt_dict(
                            issue.issue_type.value,
                            severity,
                            issue.description,
                            issue.affected_elements,
                            issue.contexts
                        ))
                    else:
                        llm_issues.append(self._issue_to_prompt_dict(
                            issue.conflict_type.value,
                            severity,
                            issue.description,
                            issue.affected_elements,
                            issue.contexts
                        ))

                llm_questions = await self._generate_llm_questions(llm_issues, extra_cap)

                existing_texts = {self._normalize_question(q.question) for q in questions}
                for q in llm_questions:
                    norm = self._normalize_question(q.question)
                    if norm and norm not in existing_texts:
                        questions.append(q)
                        existing_texts.add(norm)
                        if len(questions) >= max_q:
                            break
        
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
