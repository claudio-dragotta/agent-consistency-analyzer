"""
Model Refiner Service

Applies corrections and suggestions to produce a refined domain model
ready for Agent 3 (Specification Generator).

Uses LLM to interpret user answers and apply concrete model changes.
"""

import logging
import copy
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import httpx

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

    Uses LLM to interpret user answers and apply concrete changes.
    Produces a refined model for Agent 3 with:
    - Automatic fixes for clear violations
    - LLM-interpreted user decisions
    - Annotations for unresolved issues
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._refinement_counter = 0

    async def _call_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Ollama API for LLM-based interpretation."""
        url = self.settings.get_ollama_generate_url()
        payload = {
            "model": self.settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 2048
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.settings.OLLAMA_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    def _get_next_refinement_id(self) -> str:
        """Generate next refinement ID."""
        self._refinement_counter += 1
        return f"REF-{self._refinement_counter:03d}"

    def _deep_copy_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of the domain model."""
        return copy.deepcopy(model)

    # ─── Model element finders ───────────────────────────────────────

    def _find_entity_in_model(
        self, model: Dict[str, Any], entity_name: str, context_name: Optional[str] = None
    ) -> Tuple[Optional[Dict], str]:
        """Find an entity in the model by name and optionally context."""
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
        self, model: Dict[str, Any], event_name: str
    ) -> Tuple[Optional[Dict], str, int]:
        """Find an event in the model by name."""
        events = model.get("eventDrivenModel", {}).get("domainEvents", [])
        for i, event in enumerate(events):
            if event.get("name", "").lower() == event_name.lower():
                return event, f"eventDrivenModel.domainEvents[{i}]", i
        return None, "", -1

    def _find_domain_in_model(
        self, model: Dict[str, Any], domain_name: str
    ) -> Tuple[Optional[Dict], str, str]:
        """Find a domain in the model by name."""
        domain_map = model.get("domainMap", {})
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for i, domain in enumerate(domains):
                if domain.get("name", "").lower() == domain_name.lower():
                    return domain, f"domainMap.{domain_type}[{i}]", domain_type
        return None, "", ""

    # ─── Auto-fix methods ────────────────────────────────────────────

    def fix_naming_violation(self, model: Dict[str, Any], event_name: str) -> Optional[Refinement]:
        """Auto-fix naming violation by converting event name to past tense."""
        event, path, idx = self._find_event_in_model(model, event_name)
        if not event:
            return None
        old_name = event["name"]
        if old_name.endswith("e"):
            new_name = old_name + "d"
        elif old_name.endswith("y"):
            new_name = old_name[:-1] + "ied"
        else:
            new_name = old_name + "ed"
        event["name"] = new_name
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="auto",
            description=f"Rinominato evento da '{old_name}' a '{new_name}' (tempo passato)",
            applied=True,
            source_issue_type="NAMING_VIOLATION",
            affected_path=path,
            original_value=old_name,
            new_value=new_name
        )

    # ─── Annotation methods ──────────────────────────────────────────

    def _add_annotation(self, model: Dict[str, Any], annotation: Dict[str, Any]) -> None:
        """Add a validation annotation to the model."""
        if "_validationAnnotations" not in model:
            model["_validationAnnotations"] = []
        model["_validationAnnotations"].append(annotation)

    def annotate_entity_overlap(self, model: Dict[str, Any], issue: SemanticIssue) -> Optional[Refinement]:
        annotation = {
            "type": "ENTITY_OVERLAP",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        self._add_annotation(model, annotation)
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotato entity overlap: {', '.join(issue.affected_elements)}",
            applied=False,
            source_issue_type="ENTITY_OVERLAP",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )

    def annotate_semantic_ambiguity(self, model: Dict[str, Any], issue: SemanticIssue) -> Optional[Refinement]:
        annotation = {
            "type": "SEMANTIC_AMBIGUITY",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        self._add_annotation(model, annotation)
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotata ambiguità semantica: {', '.join(issue.contexts)}",
            applied=False,
            source_issue_type="SEMANTIC_AMBIGUITY",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )

    def annotate_requirement_conflict(self, model: Dict[str, Any], issue: ConflictIssue) -> Optional[Refinement]:
        annotation = {
            "type": "REQUIREMENT_CONFLICT",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "evidence": issue.evidence,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        self._add_annotation(model, annotation)
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotato conflitto requisiti: {', '.join(issue.contexts)}",
            applied=False,
            source_issue_type="REQUIREMENT_CONFLICT",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )

    def fix_duplicate_event(self, model: Dict[str, Any], issue: ConflictIssue) -> Optional[Refinement]:
        annotation = {
            "type": "DUPLICATE_EVENT",
            "affectedElements": issue.affected_elements,
            "emitters": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        self._add_annotation(model, annotation)
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotato evento duplicato: {', '.join(issue.contexts)}",
            applied=False,
            source_issue_type="DUPLICATE_EVENT",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )

    def suggest_domain_reclassification(self, model: Dict[str, Any], issue: ConflictIssue) -> Optional[Refinement]:
        domain_name = issue.affected_elements[0] if issue.affected_elements else "Unknown"
        annotation = {
            "type": "MISCLASSIFIED_DOMAIN",
            "domain": domain_name,
            "currentClassification": "core",
            "suggestedClassification": "generic",
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        self._add_annotation(model, annotation)
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Suggerita riclassificazione per: {domain_name}",
            applied=False,
            source_issue_type="MISCLASSIFIED_DOMAIN",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )

    def annotate_incompatible_pattern(self, model: Dict[str, Any], issue: ConflictIssue) -> Optional[Refinement]:
        annotation = {
            "type": "INCOMPATIBLE_PATTERN",
            "affectedElements": issue.affected_elements,
            "contexts": issue.contexts,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "requiresManualResolution": True
        }
        self._add_annotation(model, annotation)
        return Refinement(
            refinement_id=self._get_next_refinement_id(),
            refinement_type="suggested",
            description=f"Annotato pattern incompatibile: {issue.description[:50]}...",
            applied=False,
            source_issue_type="INCOMPATIBLE_PATTERN",
            affected_path="_validationAnnotations",
            original_value=None,
            new_value=annotation
        )

    # ─── LLM-based answer interpretation ─────────────────────────────

    async def _interpret_answer_with_llm(
        self,
        question: FollowUpQuestion,
        answer: str,
        max_retries: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to interpret a user answer and decide what model changes to apply.
        Retries up to max_retries times on failure.

        Returns a dict with action/description/changes, or None if all attempts fail
        (caller should use rule-based fallback).
        """
        system_prompt = (
            "Sei un esperto DDD. Dato un problema di dominio, una domanda e la risposta dell'utente, "
            "determina le modifiche concrete da applicare al modello di dominio.\n\n"
            "Rispondi con un JSON con questi campi:\n"
            '- "action": una tra "rename_event", "set_owner", "reclassify_domain", '
            '"resolve_conflict", "add_mapping", "update_pattern"\n'
            '- "description": cosa fa questa modifica (in italiano, breve)\n'
            '- "changes": oggetto con le modifiche specifiche. Esempi:\n'
            '  Per rename_event: {"old_name": "...", "new_name": "..."}\n'
            '  Per set_owner: {"entity": "...", "owner_context": "..."}\n'
            '  Per reclassify_domain: {"domain": "...", "from": "core", "to": "generic"}\n'
            '  Per resolve_conflict: {"resolution": "...", "priority": "req1|req2|both"}\n'
            '  Per add_mapping: {"entity": "...", "source_context": "...", "target_context": "..."}\n'
            '  Per update_pattern: {"upstream": "...", "downstream": "...", "new_pattern": "..."}\n\n'
            "IMPORTANTE: Non usare mai 'no_change'. Scegli SEMPRE un'azione concreta.\n"
            "Se non sai quale azione specifica applicare, usa 'resolve_conflict'.\n"
            "Rispondi SOLO con JSON valido (niente markdown)."
        )

        prompt = (
            f"Tipo problema: {question.related_issue_type}\n"
            f"Severità: {question.severity}\n"
            f"Domanda: {question.question}\n"
            f"Risposta utente: {answer}\n"
            f"Elementi coinvolti: {json.dumps(question.affected_elements, ensure_ascii=False)}\n"
            f"Contesto: {question.context}\n\n"
            f"Quale modifica concreta applicare al modello?"
        )

        for attempt in range(max_retries + 1):
            try:
                response = await self._call_ollama(prompt, system_prompt)
                raw = response.strip()
                # Strip markdown fences
                if raw.startswith("```"):
                    raw = re.sub(r"```(?:json)?\n?", "", raw).strip()
                    raw = raw.strip("`").strip()
                # Extract JSON object
                start = raw.find("{")
                end = raw.rfind("}")
                if start >= 0 and end > start:
                    raw = raw[start : end + 1]
                result = json.loads(raw)
                action = result.get("action", "")
                # Reject no_change: retry to get a real action
                if action == "no_change" and attempt < max_retries:
                    logger.info(
                        f"LLM returned no_change (attempt {attempt + 1}/{max_retries + 1}), retrying..."
                    )
                    continue
                # Accept any valid action (including no_change on last attempt)
                if action and action != "no_change":
                    return result
                # Last attempt returned no_change → let fallback handle it
                logger.warning("LLM returned no_change after all retries")
                return None
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"LLM interpretation attempt {attempt + 1} failed: {e}, retrying..."
                    )
                    continue
                logger.warning(
                    f"LLM interpretation failed after {max_retries + 1} attempts: {e}"
                )
                return None
        return None

    def _interpret_answer_by_rules(
        self,
        question: FollowUpQuestion,
        answer: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Rule-based fallback for interpreting user answers when LLM fails.

        Returns a concrete interpretation if rules can determine the action,
        or None if the answer is too ambiguous (caller will handle re-asking).
        """
        issue_type = question.related_issue_type
        affected = question.affected_elements or []
        answer_lower = answer.lower().strip()

        # ── First: try to match against suggested_answers we generated ──
        # When user picks a radio button, the answer IS one of our suggestions.
        # Since we wrote them, we can parse them reliably.
        if question.suggested_answers:
            for sa in question.suggested_answers:
                if answer.strip() == sa.strip():
                    parsed = self._parse_suggested_answer(question, sa)
                    if parsed:
                        return parsed

        # ── Second: pattern matching on answer text by issue type ──
        if issue_type == "ENTITY_OVERLAP":
            ctx = re.search(r"(\w+Context)", answer, re.IGNORECASE)
            if not ctx:
                ctx = re.search(
                    r"(?:assegn\w*|assign\w*|ownership)\s+(?:to|a|al?)\s+(\w+)",
                    answer, re.IGNORECASE,
                )
            if ctx and affected:
                return {
                    "action": "set_owner",
                    "description": f"Assegnata ownership di {affected[0]} a {ctx.group(1)}",
                    "changes": {"entity": affected[0], "owner_context": ctx.group(1)},
                }

        elif issue_type == "MISCLASSIFIED_DOMAIN":
            target_type = None
            if any(w in answer_lower for w in ["generic", "generico", "generica"]):
                target_type = "generic"
            elif any(w in answer_lower for w in ["supporting", "supporto", "supporti"]):
                target_type = "supporting"
            elif "core" in answer_lower:
                target_type = "core"
            if target_type and affected:
                return {
                    "action": "reclassify_domain",
                    "description": f"Riclassificato {affected[0]} come {target_type}",
                    "changes": {"domain": affected[0], "from": "", "to": target_type},
                }

        elif issue_type == "DUPLICATE_EVENT":
            name_match = re.search(
                r'(?:rinomina\w*|rename|→|->|in\s+)[\s"\']*([A-Z]\w+)', answer
            )
            if name_match and affected:
                return {
                    "action": "rename_event",
                    "description": f"Rinominato {affected[0]} -> {name_match.group(1)}",
                    "changes": {"old_name": affected[0], "new_name": name_match.group(1)},
                }

        elif issue_type == "INCOMPATIBLE_PATTERN":
            patterns = {
                "event-driven": "event-driven",
                "shared-kernel": "shared-kernel",
                "anti-corruption": "anti-corruption-layer",
                "conformist": "conformist",
                "open-host": "open-host-service",
                "published-language": "published-language",
            }
            for key, pattern in patterns.items():
                if key in answer_lower:
                    return {
                        "action": "update_pattern",
                        "description": f"Pattern aggiornato a {pattern}",
                        "changes": {
                            "upstream": affected[0] if len(affected) > 0 else "",
                            "downstream": affected[1] if len(affected) > 1 else "",
                            "new_pattern": pattern,
                        },
                    }

        # ── No match: return None (don't fake a resolution) ──
        logger.warning(
            f"Rules could not interpret answer for {issue_type}: '{answer[:60]}...'"
        )
        return None

    def _parse_suggested_answer(
        self, question: FollowUpQuestion, suggested: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a suggested_answer string into an action.

        Since WE generated the suggested answers, we know their common patterns
        and can match them reliably.
        """
        affected = question.affected_elements or []
        s = suggested.lower()

        # Ownership patterns: "Assegna ownership a X", "Assign to X"
        ctx_match = re.search(r"(\w+Context)", suggested, re.IGNORECASE)
        if ctx_match and affected:
            if any(kw in s for kw in ["owner", "assegn", "assign", "gestit"]):
                return {
                    "action": "set_owner",
                    "description": f"Ownership: {affected[0]} -> {ctx_match.group(1)}",
                    "changes": {"entity": affected[0], "owner_context": ctx_match.group(1)},
                }

        # Reference/mapping patterns: "Crea riferimento", "ProductRef"
        if any(kw in s for kw in ["riferimento", "reference", "ref ", "mapping", "acl"]):
            source = ""
            target = ""
            contexts = re.findall(r"(\w+Context)", suggested, re.IGNORECASE)
            if len(contexts) >= 2:
                source, target = contexts[0], contexts[1]
            elif len(contexts) == 1:
                target = contexts[0]
            if affected:
                return {
                    "action": "add_mapping",
                    "description": f"Mapping per {affected[0]}",
                    "changes": {"entity": affected[0], "source_context": source, "target_context": target},
                }

        # Reclassification patterns: "Sposta in generic", "Riclassifica come supporting"
        for domain_type in ["core", "supporting", "generic"]:
            if domain_type in s:
                if any(kw in s for kw in ["sposta", "riclassific", "move", "reclassif", "classificare"]):
                    if affected:
                        return {
                            "action": "reclassify_domain",
                            "description": f"Riclassificato {affected[0]} come {domain_type}",
                            "changes": {"domain": affected[0], "from": "", "to": domain_type},
                        }

        # Rename patterns: "Rinomina in X", "→ NewName"
        name_match = re.search(r'(?:rinomina\w*|rename|→|->)\s*["\']?([A-Z]\w+)', suggested)
        if name_match and affected:
            return {
                "action": "rename_event",
                "description": f"Rinominato {affected[0]} -> {name_match.group(1)}",
                "changes": {"old_name": affected[0], "new_name": name_match.group(1)},
            }

        # Pattern update: mentions a specific integration pattern
        for key, pattern in {
            "event-driven": "event-driven", "shared-kernel": "shared-kernel",
            "anti-corruption": "anti-corruption-layer", "conformist": "conformist",
        }.items():
            if key in s:
                return {
                    "action": "update_pattern",
                    "description": f"Pattern aggiornato a {pattern}",
                    "changes": {
                        "upstream": affected[0] if len(affected) > 0 else "",
                        "downstream": affected[1] if len(affected) > 1 else "",
                        "new_pattern": pattern,
                    },
                }

        return None

    def _apply_model_changes(
        self,
        model: Dict[str, Any],
        question: FollowUpQuestion,
        answer: str,
        interpretation: Dict[str, Any],
    ) -> bool:
        """
        Apply concrete model changes based on LLM interpretation.

        Returns True if changes were actually applied to the model.
        """
        action = interpretation.get("action", "no_change")
        changes = interpretation.get("changes", {})

        if action == "rename_event":
            old_name = changes.get("old_name", "")
            new_name = changes.get("new_name", "")
            if old_name and new_name:
                event, path, idx = self._find_event_in_model(model, old_name)
                if event:
                    event["name"] = new_name
                    logger.info(f"Renamed event '{old_name}' → '{new_name}'")
                    return True

        elif action == "set_owner":
            entity_name = changes.get("entity", "")
            owner = changes.get("owner_context", "")
            if entity_name and owner:
                # Mark ownership in model metadata
                if "_ownershipDecisions" not in model:
                    model["_ownershipDecisions"] = []
                model["_ownershipDecisions"].append({
                    "entity": entity_name,
                    "owner": owner,
                    "decidedAt": datetime.utcnow().isoformat() + "Z"
                })
                # Remove entity from non-owner contexts
                self._enforce_entity_ownership(model, entity_name, owner)
                logger.info(f"Set ownership: '{entity_name}' → '{owner}'")
                return True

        elif action == "reclassify_domain":
            domain_name = changes.get("domain", "")
            from_type = changes.get("from", "")
            to_type = changes.get("to", "")
            if domain_name and to_type:
                applied = self._move_domain(model, domain_name, to_type)
                if applied:
                    logger.info(f"Reclassified '{domain_name}': {from_type} → {to_type}")
                    return True

        elif action == "resolve_conflict":
            # Record the resolution decision
            if "_conflictResolutions" not in model:
                model["_conflictResolutions"] = []
            model["_conflictResolutions"].append({
                "issue_type": question.related_issue_type,
                "resolution": changes.get("resolution", answer),
                "priority": changes.get("priority", ""),
                "affected_elements": question.affected_elements,
                "decidedAt": datetime.utcnow().isoformat() + "Z"
            })
            logger.info(f"Conflict resolved: {changes.get('resolution', answer)[:80]}")
            return True

        elif action == "add_mapping":
            entity = changes.get("entity", "")
            source = changes.get("source_context", "")
            target = changes.get("target_context", "")
            if entity:
                if "_contextMappings" not in model:
                    model["_contextMappings"] = []
                model["_contextMappings"].append({
                    "entity": entity,
                    "sourceContext": source,
                    "targetContext": target,
                    "mappingType": "anti-corruption-layer",
                    "decidedAt": datetime.utcnow().isoformat() + "Z"
                })
                logger.info(f"Added mapping for '{entity}': {source} → {target}")
                return True

        elif action == "update_pattern":
            upstream = changes.get("upstream", "")
            downstream = changes.get("downstream", "")
            new_pattern = changes.get("new_pattern", "")
            if upstream and downstream and new_pattern:
                # Update integration pattern
                integrations = (
                    model.get("contextIntegrations", [])
                    or model.get("domainMap", {}).get("contextIntegrations", [])
                )
                for integration in integrations:
                    if (integration.get("upstream", "") == upstream and
                            integration.get("downstream", "") == downstream):
                        old_pattern = integration.get("integrationPattern", "")
                        integration["integrationPattern"] = new_pattern
                        logger.info(f"Updated pattern {upstream}→{downstream}: {old_pattern} → {new_pattern}")
                        return True

        return False

    def _enforce_entity_ownership(
        self, model: Dict[str, Any], entity_name: str, owner_context: str
    ) -> None:
        """Remove entity from non-owner contexts, keeping only a reference by ID."""
        domain_map = model.get("domainMap", {})
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for domain in domains:
                context = domain.get("boundedContext", {}).get("name", "")
                if context.lower() == owner_context.lower():
                    continue
                entities = domain.get("entities", [])
                for i, entity in enumerate(entities):
                    if entity.get("name", "").lower() == entity_name.lower():
                        # Replace with reference
                        entities[i] = {
                            "name": entity_name,
                            "_referenceOnly": True,
                            "_ownedBy": owner_context,
                            "_note": f"Riferimento: entità gestita da {owner_context}"
                        }
                        break

    def _move_domain(self, model: Dict[str, Any], domain_name: str, to_type: str) -> bool:
        """Move a domain from one classification to another."""
        type_map = {"core": "coreDomains", "supporting": "supportingDomains", "generic": "genericDomains"}
        target_key = type_map.get(to_type.lower(), "")
        if not target_key:
            return False

        domain_map = model.get("domainMap", {})
        for from_key in ["coreDomains", "supportingDomains", "genericDomains"]:
            if from_key == target_key:
                continue
            domains = domain_map.get(from_key, [])
            for i, domain in enumerate(domains):
                if domain.get("name", "").lower() == domain_name.lower():
                    # Move to target
                    moved = domains.pop(i)
                    if target_key not in domain_map:
                        domain_map[target_key] = []
                    domain_map[target_key].append(moved)
                    return True
        return False

    # ─── User answer processing ──────────────────────────────────────

    def _count_previous_failures(
        self,
        model: Dict[str, Any],
        issue_type: str,
        affected_elements: List[str],
    ) -> int:
        """Count how many times this issue was answered but NOT applied."""
        count = 0
        affected_set = {e.lower() for e in affected_elements}
        for fix in model.get("_userGuidedFixes", []):
            if not fix.get("applied", True):
                fix_elements = {e.lower() for e in fix.get("affected_elements", [])}
                if fix.get("type", "").startswith(issue_type) and fix_elements & affected_set:
                    count += 1
        return count

    async def _apply_user_answers(
        self,
        model: Dict[str, Any],
        questions: List[FollowUpQuestion],
        answers: Dict[str, str],
        use_llm: bool = True,
    ) -> List[Refinement]:
        """
        Apply user answers to refine the model iteratively.

        Interpretation chain (honest - no faking):
        1. LLM with retry (up to 3 attempts)
        2. Rule-based fallback (suggested_answers matching + pattern matching)
        3. If BOTH fail → applied=false, issue stays open, will be re-asked
           The system NEVER fakes a resolution.
        """
        refinements = []

        for question_id, answer in answers.items():
            try:
                question_index = int(question_id.replace("q", ""))
            except (ValueError, IndexError):
                logger.warning(f"Invalid question ID format: {question_id}")
                continue

            if question_index >= len(questions):
                logger.warning(f"Question index {question_index} out of range")
                continue

            question = questions[question_index]

            # --- Interpretation chain: LLM (with retry) → rules ---
            interpretation = None
            interpretation_source = "none"

            if use_llm:
                interpretation = await self._interpret_answer_with_llm(question, answer)
                if interpretation:
                    interpretation_source = "llm"

            if interpretation is None:
                interpretation = self._interpret_answer_by_rules(question, answer)
                if interpretation:
                    interpretation_source = "rules"
                    logger.info(
                        f"Rule-based fallback for {question.related_issue_type}: "
                        f"action={interpretation.get('action')}"
                    )

            if interpretation is None:
                # Both failed → honest failure: record but DON'T mark as resolved.
                # The issue stays open and will be re-asked next iteration.
                logger.warning(
                    f"Cannot interpret answer for {question.related_issue_type}: "
                    f"'{answer[:60]}'. Issue stays open, will be re-asked."
                )

            # --- Apply changes (or skip if interpretation is None) ---
            applied = False
            description = (
                f"{question.related_issue_type}: risposta non interpretata, "
                f"verra ri-chiesta con domanda piu specifica"
            )

            if interpretation is not None:
                applied = self._apply_model_changes(model, question, answer, interpretation)
                description = interpretation.get(
                    "description",
                    f"{question.related_issue_type} risolto: {answer[:80]}",
                )

            logger.info(
                f"Answer for {question.related_issue_type}: "
                f"source={interpretation_source}, "
                f"action={interpretation.get('action', 'NONE') if interpretation else 'NONE'}, "
                f"applied={applied}"
            )

            # --- Record with honest applied status ---
            if "_userGuidedFixes" not in model:
                model["_userGuidedFixes"] = []
            model["_userGuidedFixes"].append({
                "type": f"{question.related_issue_type}_RESOLVED",
                "question": question.question[:200],
                "answer": answer,
                "affected_elements": question.affected_elements,
                "context": question.context,
                "applied": applied,
                "interpretation_source": interpretation_source,
                "action": interpretation.get("action", "none") if interpretation else "none",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            refinements.append(Refinement(
                refinement_id=self._get_next_refinement_id(),
                refinement_type="manual",
                description=description,
                applied=applied,
                source_issue_type=question.related_issue_type,
                affected_path="_userGuidedFixes",
                original_value="unresolved",
                new_value=answer[:100],
            ))

        return refinements

    # ─── Main entry point ────────────────────────────────────────────

    async def refine_model(
        self,
        domain_model: Dict[str, Any],
        semantic_issues: List[SemanticIssue],
        conflict_issues: List[ConflictIssue],
        follow_up_questions: List[FollowUpQuestion],
        previous_answers: Dict[str, str] = None,
        apply_auto_fixes: bool = True,
        use_llm: bool = True,
    ) -> Tuple[Dict[str, Any], RefinementReport]:
        """
        Apply refinements to the domain model.

        Now async to support LLM-based answer interpretation.
        """
        if previous_answers is None:
            previous_answers = {}

        logger.info("Starting model refinement...")
        if previous_answers:
            logger.info(f"Applying {len(previous_answers)} user answers with LLM interpretation")

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

        # Apply user answers from previous iteration (LLM-interpreted)
        if previous_answers:
            user_refinements = await self._apply_user_answers(
                refined, follow_up_questions, previous_answers, use_llm=use_llm
            )
            refinements.extend(user_refinements)
            auto_fixed += len([r for r in user_refinements if r.applied])

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
