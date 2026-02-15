"""
Conflict Detector Service

Uses Ollama/Llama3 with DDD rules as context to detect:
- REQUIREMENT_CONFLICT
- DUPLICATE_EVENT
- NAMING_VIOLATION
- INCOMPATIBLE_PATTERN
- MISCLASSIFIED_DOMAIN
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of conflicts detected by the conflict detector."""
    REQUIREMENT_CONFLICT = "REQUIREMENT_CONFLICT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    NAMING_VIOLATION = "NAMING_VIOLATION"
    INCOMPATIBLE_PATTERN = "INCOMPATIBLE_PATTERN"
    MISCLASSIFIED_DOMAIN = "MISCLASSIFIED_DOMAIN"


@dataclass
class ConflictIssue:
    """Represents a conflict issue detected during analysis."""
    conflict_type: ConflictType
    severity: str
    description: str
    affected_elements: List[str]
    contexts: List[str]
    rule_id: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "conflict_type": self.conflict_type.value,
            "severity": self.severity,
            "description": self.description,
            "affected_elements": self.affected_elements,
            "contexts": self.contexts,
            "rule_id": self.rule_id,
            "evidence": self.evidence,
            "recommendation": self.recommendation
        }


class ConflictDetector:
    """
    Detects conflicts and issues in domain models using LLM analysis.
    
    Uses Ollama/Llama3 with DDD rules as context to identify:
    - Requirement conflicts
    - Duplicate events
    - Naming violations
    - Incompatible patterns
    - Misclassified domains
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the conflict detector.
        
        Args:
            settings: Application settings (uses global if not provided)
        """
        self.settings = settings or get_settings()
        self._ddd_rules: Optional[str] = None
        self._validation_checklist: Optional[dict] = None
    
    @property
    def ddd_rules(self) -> str:
        """Lazy load DDD rules."""
        if self._ddd_rules is None:
            self._ddd_rules = self.settings.load_ddd_rules()
        return self._ddd_rules
    
    @property
    def validation_checklist(self) -> dict:
        """Lazy load validation checklist."""
        if self._validation_checklist is None:
            self._validation_checklist = self.settings.load_validation_checklist()
        return self._validation_checklist
    
    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Call Ollama API for LLM analysis.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            
        Returns:
            LLM response text
        """
        url = self.settings.get_ollama_generate_url()
        
        payload = {
            "model": self.settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.settings.OLLAMA_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            except httpx.TimeoutException:
                logger.error("Ollama request timed out")
                raise
            except httpx.HTTPError as e:
                logger.error(f"Ollama request failed: {e}")
                raise
    
    def _extract_requirements(self, domain_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all functional requirements from the domain model."""
        requirements = []
        domain_map = domain_model.get("domainMap", {})
        
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            domains = domain_map.get(domain_type, [])
            for domain in domains:
                domain_name = domain.get("name", "Unknown")
                for req in domain.get("functionalRequirements", []):
                    requirements.append({
                        "domain": domain_name,
                        "id": req.get("id", ""),
                        "description": req.get("description", ""),
                        "priority": req.get("priority", "")
                    })
        
        return requirements
    
    def _extract_events(self, domain_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all events from the domain model."""
        events = []
        event_model = domain_model.get("eventDrivenModel", {})

        # Support both "events" and "domainEvents" keys
        raw_events = event_model.get("events", []) or event_model.get("domainEvents", [])

        for event in raw_events:
            events.append({
                "name": event.get("name", ""),
                "emitter": event.get("emitter", "") or event.get("emittedBy", ""),
                "consumers": event.get("consumers", []) or event.get("consumedBy", []),
                "description": event.get("description", ""),
                "payload": event.get("payload", [])
            })

        return events
    
    def _extract_domains(self, domain_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all domains with their classification."""
        domains = []
        domain_map = domain_model.get("domainMap", {})
        
        for domain_type in ["coreDomains", "supportingDomains", "genericDomains"]:
            type_label = domain_type.replace("Domains", "").lower()
            for domain in domain_map.get(domain_type, []):
                domains.append({
                    "name": domain.get("name", ""),
                    "type": type_label,
                    "description": domain.get("description", ""),
                    "context": domain.get("boundedContext", {}).get("name", "")
                })
        
        return domains
    
    def _extract_integrations(self, domain_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract context integrations from the domain model."""
        integrations = []

        # Support both top-level and domainMap-nested contextIntegrations
        raw = (
            domain_model.get("contextIntegrations", [])
            or domain_model.get("domainMap", {}).get("contextIntegrations", [])
        )

        for integration in raw:
            integrations.append({
                "upstream": integration.get("upstream", ""),
                "downstream": integration.get("downstream", ""),
                "pattern": integration.get("integrationPattern", "") or integration.get("pattern", ""),
                "communication": integration.get("communication", "")
            })
        
        return integrations
    
    def detect_requirement_conflicts(
        self,
        requirements: List[Dict[str, Any]]
    ) -> List[ConflictIssue]:
        """
        Detect conflicts between requirements using rule-based analysis.
        
        Args:
            requirements: List of requirements to analyze
            
        Returns:
            List of detected REQUIREMENT_CONFLICT issues
        """
        issues = []
        
        # Conflict patterns to look for
        conflict_patterns = [
            {
                "pattern1": ["immutable", "cannot be changed", "fixed", "never change"],
                "pattern2": ["modify", "update", "change", "retroactive", "adjust"],
                "description": "Immutability conflicts with modification requirement"
            },
            {
                "pattern1": ["strong consistency", "immediately consistent", "synchronous", "real-time"],
                "pattern2": ["eventual consistency", "eventually consistent", "asynchronous", "async"],
                "description": "Strong consistency conflicts with eventual consistency"
            },
            {
                "pattern1": ["unique", "one and only", "single"],
                "pattern2": ["multiple", "many", "several", "various"],
                "description": "Uniqueness constraint conflicts with multiplicity"
            }
        ]
        
        # Check all pairs of requirements
        for i, req1 in enumerate(requirements):
            for j, req2 in enumerate(requirements):
                if j <= i:
                    continue
                
                desc1 = req1["description"].lower()
                desc2 = req2["description"].lower()
                
                for pattern in conflict_patterns:
                    # Check if req1 matches pattern1 and req2 matches pattern2
                    match1_p1 = any(p in desc1 for p in pattern["pattern1"])
                    match2_p2 = any(p in desc2 for p in pattern["pattern2"])
                    
                    # Or vice versa
                    match1_p2 = any(p in desc1 for p in pattern["pattern2"])
                    match2_p1 = any(p in desc2 for p in pattern["pattern1"])
                    
                    if (match1_p1 and match2_p2) or (match1_p2 and match2_p1):
                        issues.append(ConflictIssue(
                            conflict_type=ConflictType.REQUIREMENT_CONFLICT,
                            severity="HIGH",
                            description=pattern["description"],
                            affected_elements=[
                                f"{req1['id']}: {req1['description']}",
                                f"{req2['id']}: {req2['description']}"
                            ],
                            contexts=[req1["domain"], req2["domain"]],
                            rule_id="RC-001",
                            evidence=f"Requirement {req1['id']} and {req2['id']} have conflicting constraints",
                            recommendation=(
                                "Resolve the conflict by either relaxing one of the constraints, "
                                "or specifying conditions under which each applies."
                            )
                        ))
        
        return issues
    
    def detect_duplicate_events(
        self,
        events: List[Dict[str, Any]]
    ) -> List[ConflictIssue]:
        """
        Detect duplicate events (same event emitted by multiple domains).
        
        Args:
            events: List of events to analyze
            
        Returns:
            List of detected DUPLICATE_EVENT issues
        """
        issues = []
        
        # Group events by name
        events_by_name: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            name = event["name"].lower()
            if name not in events_by_name:
                events_by_name[name] = []
            events_by_name[name].append(event)
        
        # Check for duplicates
        for name, event_list in events_by_name.items():
            emitters = set(e["emitter"] for e in event_list)
            if len(emitters) > 1:
                issues.append(ConflictIssue(
                    conflict_type=ConflictType.DUPLICATE_EVENT,
                    severity="HIGH",
                    description=f"Event '{event_list[0]['name']}' is emitted by multiple domains",
                    affected_elements=[
                        f"{e['name']} (emitted by {e['emitter']})"
                        for e in event_list
                    ],
                    contexts=list(emitters),
                    rule_id="EA-001",
                    evidence=f"Multiple emitters found: {', '.join(emitters)}",
                    recommendation=(
                        "Each domain event should have a single owner/emitter. "
                        "Consider renaming events to include context (e.g., 'OrderCreated' vs 'CatalogOrderCreated') "
                        "or consolidate ownership."
                    )
                ))
        
        return issues
    
    def detect_naming_violations(
        self,
        events: List[Dict[str, Any]]
    ) -> List[ConflictIssue]:
        """
        Detect naming violations in events (not past tense).
        
        Args:
            events: List of events to analyze
            
        Returns:
            List of detected NAMING_VIOLATION issues
        """
        issues = []
        
        # Past tense suffixes
        past_tense_suffixes = ["ed", "en", "t"]
        
        # Common past tense words
        past_tense_words = [
            "created", "updated", "deleted", "completed", "cancelled",
            "shipped", "delivered", "paid", "confirmed", "rejected",
            "approved", "failed", "started", "finished", "processed",
            "changed", "modified", "added", "removed", "placed"
        ]
        
        # Present tense verbs that indicate violation
        present_tense_verbs = [
            "process", "create", "update", "delete", "ship", "deliver",
            "pay", "confirm", "reject", "approve", "start", "finish",
            "add", "remove", "place", "send", "receive", "cancel"
        ]
        
        for event in events:
            name = event["name"]
            name_lower = name.lower()
            
            # Check if any present tense verb is at the start
            is_violation = False
            violation_verb = None
            
            for verb in present_tense_verbs:
                if name_lower.startswith(verb):
                    # Make sure it's not followed by past tense suffix
                    remainder = name_lower[len(verb):]
                    if not any(remainder.endswith(suffix) for suffix in past_tense_suffixes):
                        # Check if the name doesn't contain a past tense word
                        if not any(pt in name_lower for pt in past_tense_words):
                            is_violation = True
                            violation_verb = verb
                            break
            
            if is_violation:
                issues.append(ConflictIssue(
                    conflict_type=ConflictType.NAMING_VIOLATION,
                    severity="MEDIUM",
                    description=f"Event '{name}' uses present tense instead of past tense",
                    affected_elements=[name],
                    contexts=[event["emitter"]],
                    rule_id="EA-002",
                    evidence=f"Event name starts with present tense verb '{violation_verb}'",
                    recommendation=(
                        f"Domain events should use past tense to indicate something that has happened. "
                        f"Consider renaming '{name}' to '{name}d' or similar past tense form."
                    )
                ))
        
        return issues
    
    def detect_incompatible_patterns(
        self,
        requirements: List[Dict[str, Any]],
        integrations: List[Dict[str, Any]]
    ) -> List[ConflictIssue]:
        """
        Detect incompatible integration patterns.
        
        Args:
            requirements: List of requirements
            integrations: List of context integrations
            
        Returns:
            List of detected INCOMPATIBLE_PATTERN issues
        """
        issues = []
        
        # Check for sync requirements with async-only communication
        sync_requirements = []
        for req in requirements:
            desc_lower = req["description"].lower()
            if any(kw in desc_lower for kw in ["immediately", "synchronous", "real-time", "strong consistency"]):
                sync_requirements.append(req)
        
        # Check integrations for async-only patterns
        for integration in integrations:
            comm = integration.get("communication", "").lower()
            pattern = integration.get("pattern", "").lower()
            
            is_async_only = "async" in comm or comm == "event-based"
            
            if is_async_only:
                # Check if any sync requirement involves these contexts
                for req in sync_requirements:
                    upstream = integration.get("upstream", "")
                    downstream = integration.get("downstream", "")
                    
                    if req["domain"] in [upstream, downstream]:
                        issues.append(ConflictIssue(
                            conflict_type=ConflictType.INCOMPATIBLE_PATTERN,
                            severity="HIGH",
                            description=(
                                f"Synchronous requirement in {req['domain']} conflicts with "
                                f"async-only communication between {upstream} and {downstream}"
                            ),
                            affected_elements=[
                                f"{req['id']}: {req['description']}",
                                f"Integration: {upstream} -> {downstream} ({comm})"
                            ],
                            contexts=[upstream, downstream],
                            rule_id="CP-001",
                            evidence=f"Requirement demands sync but pattern is {pattern} with {comm}",
                            recommendation=(
                                "Either relax the synchronous requirement to allow eventual consistency, "
                                "or add synchronous communication option for time-sensitive operations."
                            )
                        ))
        
        return issues
    
    def detect_misclassified_domains(
        self,
        domains: List[Dict[str, Any]]
    ) -> List[ConflictIssue]:
        """
        Detect misclassified domains using rule-based heuristics.
        
        Args:
            domains: List of domains with their classification
            
        Returns:
            List of detected MISCLASSIFIED_DOMAIN issues
        """
        issues = []
        
        # Generic domains that shouldn't be Core
        generic_indicators = [
            "authentication", "authorization", "auth", "identity",
            "notification", "email", "sms", "push",
            "logging", "monitoring", "audit",
            "file storage", "storage", "upload",
            "rate limiting", "circuit breaker"
        ]
        
        # Supporting domain indicators
        supporting_indicators = [
            "reporting", "analytics", "search", "indexing",
            "archiving", "backup", "compliance"
        ]
        
        for domain in domains:
            name_lower = domain["name"].lower()
            desc_lower = domain.get("description", "").lower()
            domain_type = domain["type"]
            
            # Check if Core domain looks Generic
            if domain_type == "core":
                for indicator in generic_indicators:
                    if indicator in name_lower or indicator in desc_lower:
                        issues.append(ConflictIssue(
                            conflict_type=ConflictType.MISCLASSIFIED_DOMAIN,
                            severity="MEDIUM",
                            description=(
                                f"Domain '{domain['name']}' is classified as Core but "
                                f"appears to be a Generic domain"
                            ),
                            affected_elements=[domain["name"]],
                            contexts=[domain.get("context", "Unknown")],
                            rule_id="DC-002",
                            evidence=f"Domain name/description contains '{indicator}'",
                            recommendation=(
                                f"'{domain['name']}' is typically a commodity/generic capability. "
                                f"Consider reclassifying as Generic unless it provides unique "
                                f"competitive advantage."
                            )
                        ))
                        break
            
            # Check if Core domain looks Supporting
            if domain_type == "core":
                for indicator in supporting_indicators:
                    if indicator in name_lower or indicator in desc_lower:
                        issues.append(ConflictIssue(
                            conflict_type=ConflictType.MISCLASSIFIED_DOMAIN,
                            severity="LOW",
                            description=(
                                f"Domain '{domain['name']}' is classified as Core but "
                                f"may be better suited as Supporting"
                            ),
                            affected_elements=[domain["name"]],
                            contexts=[domain.get("context", "Unknown")],
                            rule_id="DC-003",
                            evidence=f"Domain name/description contains '{indicator}'",
                            recommendation=(
                                f"Review if '{domain['name']}' provides direct competitive "
                                f"advantage or primarily supports other domains."
                            )
                        ))
                        break
        
        return issues
    
    async def analyze_with_llm(
        self,
        domain_model: Dict[str, Any]
    ) -> List[ConflictIssue]:
        """
        Use LLM for deeper conflict analysis.
        
        Args:
            domain_model: The domain model to analyze
            
        Returns:
            List of detected issues from LLM analysis
        """
        issues = []
        
        # Prepare context for LLM
        system_prompt = f"""You are a Domain-Driven Design expert analyzing a domain model for conflicts and issues.

Use these DDD rules as your guide:

{self.ddd_rules[:8000]}  # Truncate if too long

Analyze the domain model and identify any:
1. REQUIREMENT_CONFLICT - Contradictory requirements
2. DUPLICATE_EVENT - Same event from multiple emitters
3. NAMING_VIOLATION - Events not in past tense
4. INCOMPATIBLE_PATTERN - Mismatched integration patterns
5. MISCLASSIFIED_DOMAIN - Wrong domain classification

Respond with a JSON array of issues found. Each issue should have:
- conflict_type: one of the types above
- severity: HIGH, MEDIUM, or LOW
- description: clear description of the issue
- affected_elements: list of affected elements
- recommendation: how to fix it

If no issues found, return an empty array: []
"""
        
        # Create analysis prompt
        model_summary = json.dumps({
            "domains": self._extract_domains(domain_model),
            "requirements": self._extract_requirements(domain_model),
            "events": self._extract_events(domain_model),
            "integrations": self._extract_integrations(domain_model)
        }, indent=2)
        
        prompt = f"""Analyze this domain model for DDD conflicts:

{model_summary}

Return ONLY a valid JSON array of issues found. No markdown, no explanation."""
        
        try:
            response = await self._call_ollama(prompt, system_prompt)
            
            # Try to parse JSON from response
            # Handle potential markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r"```(?:json)?\n?", "", response)
                response = response.strip()
            
            parsed = json.loads(response)
            
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "conflict_type" in item:
                        try:
                            issues.append(ConflictIssue(
                                conflict_type=ConflictType(item["conflict_type"]),
                                severity=item.get("severity", "MEDIUM"),
                                description=item.get("description", ""),
                                affected_elements=item.get("affected_elements", []),
                                contexts=item.get("contexts", []),
                                recommendation=item.get("recommendation")
                            ))
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Failed to parse LLM issue: {e}")
        except json.JSONDecodeError:
            logger.warning("LLM response was not valid JSON")
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
        
        return issues
    
    def _get_resolved_elements(self, domain_model: Dict[str, Any]) -> set:
        """
        Extract element names that have been ACTUALLY resolved.

        Only counts fixes where applied=True (real structural changes were made).
        Fixes with applied=False stay open so the issue gets re-asked.
        """
        resolved = set()

        # Only count user fixes that were actually applied
        for fix in domain_model.get("_userGuidedFixes", []):
            if not fix.get("applied", False):
                continue
            for elem in fix.get("affected_elements", []):
                key = self._normalize_element_key(elem)
                if key:
                    resolved.add(key)

        # Ownership decisions = real structural changes
        for decision in domain_model.get("_ownershipDecisions", []):
            entity = self._normalize_element_key(decision.get("entity", ""))
            if entity:
                resolved.add(entity)

        # Conflict resolutions = explicit user decisions
        for resolution in domain_model.get("_conflictResolutions", []):
            for elem in resolution.get("affected_elements", []):
                key = self._normalize_element_key(elem)
                if key:
                    resolved.add(key)

        # Context mappings = real structural changes
        for mapping in domain_model.get("_contextMappings", []):
            entity = self._normalize_element_key(mapping.get("entity", ""))
            if entity:
                resolved.add(entity)

        return resolved

    async def analyze(
        self,
        domain_model: Dict[str, Any],
        use_llm: bool = True
    ) -> List[ConflictIssue]:
        """
        Perform full conflict analysis on a domain model.

        Args:
            domain_model: The domain model JSON to analyze
            use_llm: Whether to also use LLM for analysis

        Returns:
            List of all detected conflict issues
        """
        logger.info("Starting conflict detection...")

        resolved = self._get_resolved_elements(domain_model)
        if resolved:
            logger.info(f"Skipping already-resolved elements: {resolved}")

        issues = []

        # Extract model components
        requirements = self._extract_requirements(domain_model)
        events = self._extract_events(domain_model)
        domains = self._extract_domains(domain_model)
        integrations = self._extract_integrations(domain_model)

        logger.info(f"Extracted: {len(requirements)} requirements, {len(events)} events, "
                   f"{len(domains)} domains, {len(integrations)} integrations")

        # Rule-based detection
        req_conflicts = self.detect_requirement_conflicts(requirements)
        issues.extend(req_conflicts)
        logger.info(f"Found {len(req_conflicts)} requirement conflicts")

        dup_events = self.detect_duplicate_events(events)
        issues.extend(dup_events)
        logger.info(f"Found {len(dup_events)} duplicate events")

        naming_issues = self.detect_naming_violations(events)
        issues.extend(naming_issues)
        logger.info(f"Found {len(naming_issues)} naming violations")

        pattern_issues = self.detect_incompatible_patterns(requirements, integrations)
        issues.extend(pattern_issues)
        logger.info(f"Found {len(pattern_issues)} incompatible patterns")

        domain_issues = self.detect_misclassified_domains(domains)
        issues.extend(domain_issues)
        logger.info(f"Found {len(domain_issues)} misclassified domains")

        # Optional LLM-based detection
        if use_llm:
            try:
                llm_issues = await self.analyze_with_llm(domain_model)
                # Deduplicate by description similarity
                for llm_issue in llm_issues:
                    if not any(
                        llm_issue.description.lower() in existing.description.lower() or
                        existing.description.lower() in llm_issue.description.lower()
                        for existing in issues
                    ):
                        issues.append(llm_issue)
                logger.info(f"LLM found {len(llm_issues)} additional issues")
            except Exception as e:
                logger.warning(f"LLM analysis skipped due to error: {e}")

        # Filter out issues whose affected elements are ALL already resolved
        if resolved:
            before = len(issues)
            issues = [
                issue for issue in issues
                if not self._is_issue_resolved(issue.affected_elements, resolved)
            ]
            filtered = before - len(issues)
            if filtered:
                logger.info(f"Filtered {filtered} already-resolved issues")

        logger.info(f"Conflict detection complete. Total issues: {len(issues)}")
        return issues
    def _normalize_element_key(self, value: str) -> str:
        """Normalize affected element text for robust resolved-issue matching."""
        if not value:
            return ""
        text = str(value).strip().lower()
        text = re.sub(r"\s*\(.*\)\s*$", "", text)
        if ":" in text:
            text = text.split(":", 1)[0].strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_issue_resolved(self, issue_elements: List[str], resolved: set) -> bool:
        """Return True when all issue elements can be matched to resolved keys."""
        if not issue_elements:
            return False
        return all(self._normalize_element_key(elem) in resolved for elem in issue_elements)
