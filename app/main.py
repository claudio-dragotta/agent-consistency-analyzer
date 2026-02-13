"""
FastAPI entry point for Agent 2 - Consistency & Conflict Analyzer

Provides:
- A2A Protocol endpoints for inter-agent communication
- REST API for domain model validation
- Health and configuration endpoints
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from app.config import settings, get_settings
from app.services.semantic_analyzer import SemanticAnalyzer, SemanticIssue
from app.services.conflict_detector import ConflictDetector, ConflictIssue
from app.services.question_generator import QuestionGenerator, FollowUpQuestion
from app.services.model_refiner import ModelRefiner, RefinementReport

from a2a.models import (
    Task, TaskState, TaskStatus, Message, Part, Role, Artifact
)
from a2a.models.requests import SendMessageRequest, SendMessageConfiguration

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory task storage (replace with Redis/DB for production)
tasks_store: Dict[str, Task] = {}

# Initialize services
semantic_analyzer: Optional[SemanticAnalyzer] = None
conflict_detector: Optional[ConflictDetector] = None
question_generator: Optional[QuestionGenerator] = None
model_refiner: Optional[ModelRefiner] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global semantic_analyzer, conflict_detector, question_generator, model_refiner
    
    logger.info("Starting Agent 2 - Consistency & Conflict Analyzer...")
    
    # Initialize services
    semantic_analyzer = SemanticAnalyzer(
        model_name=settings.EMBEDDINGS_MODEL,
        similarity_threshold=settings.SEMANTIC_SIMILARITY_THRESHOLD
    )
    conflict_detector = ConflictDetector(settings)
    question_generator = QuestionGenerator(settings)
    model_refiner = ModelRefiner(settings)
    
    logger.info("Services initialized successfully")
    
    yield
    
    logger.info("Shutting down Agent 2...")


# Initialize FastAPI app
app = FastAPI(
    title="Agent 2 - Consistency & Conflict Analyzer",
    description="Validates DDD domain models for semantic consistency and conflicts using A2A Protocol",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class DomainModelRequest(BaseModel):
    """Request model for direct domain validation"""
    domain_model: Dict[str, Any]
    use_llm: bool = Field(default=True, description="Use LLM for deeper analysis")
    apply_auto_fixes: bool = Field(default=True, description="Apply automatic fixes")
    previous_answers: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="User answers from previous iteration for iterative model refinement"
    )


class ValidationSummary(BaseModel):
    """Summary of validation results"""
    total_issues: int
    entity_overlaps: int
    semantic_ambiguities: int
    requirement_conflicts: int
    duplicate_events: int
    naming_violations: int
    incompatible_patterns: int
    misclassified_domains: int
    auto_fixed: int
    requires_manual: int


class ValidationResponse(BaseModel):
    """Response model for validation results"""
    status: str
    task_id: str
    summary: ValidationSummary
    semantic_issues: List[Dict[str, Any]]
    conflict_issues: List[Dict[str, Any]]
    follow_up_questions: List[Dict[str, Any]]
    refinement_report: Dict[str, Any]
    refined_model: Dict[str, Any]
    suggested_max_iterations: int = 5


class A2AMessageResponse(BaseModel):
    """A2A Protocol message response"""
    task: Dict[str, Any]
    message: Optional[Dict[str, Any]] = None


# ============================================================================
# A2A Protocol Endpoints
# ============================================================================

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Get Agent Card (A2A Protocol).
    Returns the agent's capabilities and metadata.
    """
    try:
        agent_card = settings.load_agent_card()
        return JSONResponse(content=agent_card)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent card not found")
@app.post("/a2a/message/send", response_model=A2AMessageResponse)
async def a2a_send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Send a message to the agent (A2A Protocol).
    
    This is the main entry point for receiving domain models from Agent 1.
    """
    logger.info(f"Received A2A message: {request.message.message_id}")
    
    # Create task
    task_id = str(uuid.uuid4())
    context_id = request.message.context_id or str(uuid.uuid4())
    
    task = Task(
        id=task_id,
        context_id=context_id,
        status=TaskStatus(state=TaskState.SUBMITTED),
        metadata={
            "received_at": datetime.utcnow().isoformat() + "Z",
            "message_id": request.message.message_id
        }
    )
    
    tasks_store[task_id] = task
    
    # Extract domain model and optional previous answers from message
    domain_model = None
    previous_answers: Dict[str, str] = {}
    use_llm: bool = True
    apply_auto_fixes: bool = True
    for part in request.message.parts:
        if part.data:
            # Direct data part
            candidate = part.data.data
            if isinstance(candidate, dict) and (
                "domainMap" in candidate or "eventDrivenModel" in candidate or "integrations" in candidate
            ):
                domain_model = candidate
                break
        elif part.text:
            try:
                parsed = json.loads(part.text)
                # Heuristic: if it looks like a domain model, prefer it
                if isinstance(parsed, dict) and (
                    "domainMap" in parsed or "eventDrivenModel" in parsed or "integrations" in parsed
                ):
                    domain_model = parsed
                    break
                # Otherwise treat any dict payload as previous_answers (Q&A loop)
                if isinstance(parsed, dict) and not previous_answers:
                    previous_answers = {str(k): str(v) for k, v in parsed.items()}
            except json.JSONDecodeError:
                # Ignore plain text parts
                pass
    
    if not domain_model:
        task.status = TaskStatus(
            state=TaskState.FAILED,
            message=Message(
                role=Role.AGENT,
                parts=[Part.from_text("No valid domain model found in message")]
            )
        )
        tasks_store[task_id] = task
        return A2AMessageResponse(task=task.model_dump(by_alias=True))
    
    # Optional configuration overrides from A2A configuration.metadata
    if request.configuration:
        try:
            meta = getattr(request.configuration, "metadata", None) or {}
            if isinstance(meta, dict):
                use_llm = bool(meta.get("use_llm", use_llm))
                apply_auto_fixes = bool(meta.get("apply_auto_fixes", apply_auto_fixes))
        except Exception:
            pass

    # Check if blocking mode
    blocking = request.configuration.blocking if request.configuration else False
    
    if blocking:
        # Process synchronously
        result = await _process_domain_model(
            task_id,
            domain_model,
            use_llm,
            apply_auto_fixes,
            previous_answers=previous_answers,
            return_full_result=True,
        )
        task = tasks_store[task_id]
    else:
        # Process in background
        background_tasks.add_task(
            _process_domain_model,
            task_id,
            domain_model,
            use_llm,
            apply_auto_fixes,
            previous_answers,
            False,
        )
        task.status = TaskStatus(state=TaskState.WORKING)
        tasks_store[task_id] = task
    
    return A2AMessageResponse(task=task.model_dump(by_alias=True))


@app.get("/a2a/tasks/{task_id}")
async def a2a_get_task(task_id: str):
    """
    Get task status (A2A Protocol).
    """
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_store[task_id]
    return task.model_dump(by_alias=True)


@app.get("/a2a/tasks")
async def a2a_list_tasks(
    context_id: Optional[str] = None,
    limit: int = 10
):
    """
    List tasks (A2A Protocol).
    """
    tasks = list(tasks_store.values())
    
    if context_id:
        tasks = [t for t in tasks if t.context_id == context_id]
    
    tasks = sorted(tasks, key=lambda t: t.metadata.get("received_at", ""), reverse=True)
    tasks = tasks[:limit]
    
    return {
        "tasks": [t.model_dump(by_alias=True) for t in tasks]
    }
@app.post("/a2a/tasks/{task_id}/cancel")
async def a2a_cancel_task(task_id: str):
    """
    Cancel a task (A2A Protocol).
    """
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_store[task_id]
    
    if task.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
        raise HTTPException(status_code=400, detail="Task is already in terminal state")
    
    task.status = TaskStatus(state=TaskState.CANCELLED)
    tasks_store[task_id] = task
    
    return task.model_dump(by_alias=True)


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "Agent 2 - Consistency & Conflict Analyzer",
        "version": "1.0.0",
        "protocol": "A2A v0.3",
        "status": "running",
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "a2a_send": "/a2a/message/send",
            "a2a_tasks": "/a2a/tasks",
            "analyze": "/analyze",
            "health": "/health",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "semantic_analyzer": semantic_analyzer is not None,
            "conflict_detector": conflict_detector is not None,
            "question_generator": question_generator is not None,
            "model_refiner": model_refiner is not None
        },
        "config": {
            "ollama_url": settings.OLLAMA_BASE_URL,
            "llm_model": settings.OLLAMA_MODEL,
            "embeddings_model": settings.EMBEDDINGS_MODEL
        }
    }
@app.post("/analyze", response_model=ValidationResponse)
async def analyze_domain_model(request: DomainModelRequest):
    """
    Analyze domain model for consistency and conflicts.
    
    This is a direct REST endpoint (not A2A) for testing and debugging.
    
    Args:
        request: Domain model from Agent 1
        
    Returns:
        Complete validation results with issues, questions, and refined model
    """
    task_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Starting analysis for task {task_id}")
        
        result = await _process_domain_model(
            task_id=task_id,
            domain_model=request.domain_model,
            use_llm=request.use_llm,
            apply_auto_fixes=request.apply_auto_fixes,
            previous_answers=request.previous_answers,
            return_full_result=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing domain model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/source/files")
async def list_input_files() -> Dict[str, Any]:
    """List available JSON files under INPUT_DIR for testing without Agent 1."""
    try:
        input_dir = Path(settings.INPUT_DIR)
        files = []
        if input_dir.exists():
            for p in input_dir.glob("*.json"):
                try:
                    files.append({
                        "name": p.name,
                        "size": p.stat().st_size,
                        "modified": datetime.utcfromtimestamp(p.stat().st_mtime).isoformat() + "Z",
                    })
                except Exception:
                    files.append({"name": p.name})
        return {"directory": str(input_dir), "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/source/file")
async def get_input_file(name: str) -> Dict[str, Any]:
    """Return the JSON content of a file from INPUT_DIR."""
    try:
        src = Path(settings.INPUT_DIR) / name
        if not src.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {src}")
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in file: {e}")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzeByFileRequest(BaseModel):
    file_name: str
    use_llm: bool = True
    apply_auto_fixes: bool = True
    previous_answers: Optional[Dict[str, str]] = None
@app.post("/source/analyze-by-file", response_model=ValidationResponse)
async def analyze_by_file(request: AnalyzeByFileRequest):
    """Analyze a domain model by selecting a JSON file from INPUT_DIR (testing helper)."""
    try:
        src = Path(settings.INPUT_DIR) / request.file_name
        if not src.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {src}")
        try:
            domain_model = json.loads(src.read_text(encoding="utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in file: {e}")

        task_id = str(uuid.uuid4())
        result = await _process_domain_model(
            task_id=task_id,
            domain_model=domain_model,
            use_llm=request.use_llm,
            apply_auto_fixes=request.apply_auto_fixes,
            previous_answers=request.previous_answers or {},
            return_full_result=True,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/config")
async def get_configuration():
    """Get current configuration (for debugging)"""
    return {
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_timeout": settings.OLLAMA_TIMEOUT,
        "embeddings_model": settings.EMBEDDINGS_MODEL,
        "entity_overlap_threshold": settings.ENTITY_OVERLAP_THRESHOLD,
        "semantic_similarity_threshold": settings.SEMANTIC_SIMILARITY_THRESHOLD,
        "max_follow_up_questions": settings.MAX_FOLLOW_UP_QUESTIONS,
        "kafka_enabled": bool(settings.KAFKA_BOOTSTRAP_SERVERS),
        "knowledge_base_dir": settings.KNOWLEDGE_BASE_DIR
    }


# ============================================================================
# Internal Processing Functions
# ============================================================================

async def _estimate_iterations(
    summary: ValidationSummary,
    semantic_issues: list,
    conflict_issues: list,
    use_llm: bool = True,
) -> int:
    """
    Estimate how many iterations are needed to resolve all issues.

    Uses LLM when available; falls back to a severity-based heuristic.
    Always returns a value between 1 and 10, default 5 on failure.
    """
    DEFAULT = 5

    if summary.total_issues == 0:
        return 1

    # ── Try LLM estimation ──
    if use_llm:
        try:
            import httpx, json as _json
            issues_summary = (
                f"Problemi trovati: {summary.total_issues} totali\n"
                f"- Entity overlaps: {summary.entity_overlaps}\n"
                f"- Ambiguità semantiche: {summary.semantic_ambiguities}\n"
                f"- Conflitti requisiti: {summary.requirement_conflicts}\n"
                f"- Eventi duplicati: {summary.duplicate_events}\n"
                f"- Violazioni naming: {summary.naming_violations}\n"
                f"- Pattern incompatibili: {summary.incompatible_patterns}\n"
                f"- Domini misclassificati: {summary.misclassified_domains}\n"
                f"- Auto-corretti: {summary.auto_fixed}\n"
                f"- Da risolvere manualmente: {summary.requires_manual}\n"
            )
            system_prompt = (
                "Sei un esperto DDD. Dato un riepilogo dei problemi trovati in un domain model, "
                "stima quante iterazioni di domande-risposte servono per risolvere TUTTI i problemi.\n\n"
                "REGOLE:\n"
                "- Ogni iterazione risolve 1-3 problemi tramite domande all'utente\n"
                "- I problemi HIGH richiedono piu attenzione (1 per iterazione)\n"
                "- I problemi MEDIUM/LOW possono essere raggruppati (2-3 per iterazione)\n"
                "- I problemi auto-corretti NON contano\n"
                "- Rispondi SOLO con un numero intero tra 1 e 10, NIENTE altro testo\n"
            )
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": issues_summary + "\nQuante iterazioni servono? Rispondi solo con il numero.",
                "system": system_prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 16},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(settings.get_ollama_generate_url(), json=payload)
                resp.raise_for_status()
                raw = resp.json().get("response", "").strip()
                # Extract first integer from response
                import re
                match = re.search(r"\d+", raw)
                if match:
                    n = int(match.group())
                    n = max(1, min(n, 10))
                    logger.info(f"LLM estimated {n} iterations needed")
                    return n
        except Exception as e:
            logger.warning(f"LLM iteration estimation failed: {e}, using heuristic")

    # ── Heuristic fallback ──
    high_issues = sum(
        1 for i in semantic_issues if getattr(i, "severity", "MEDIUM") == "HIGH"
    ) + sum(
        1 for i in conflict_issues if getattr(i, "severity", "MEDIUM") == "HIGH"
    )
    manual = summary.requires_manual
    if manual <= 1:
        return 1
    elif manual <= 3:
        return 2
    elif manual <= 5:
        return 3
    elif high_issues >= 3:
        return min(manual, 7)
    else:
        return DEFAULT


async def _process_domain_model(
    task_id: str,
    domain_model: Dict[str, Any],
    use_llm: bool = True,
    apply_auto_fixes: bool = True,
    previous_answers: Dict[str, str] = None,
    return_full_result: bool = False
) -> Optional[ValidationResponse]:
    """
    Process a domain model through the full analysis pipeline.

    Args:
        task_id: Task identifier
        domain_model: The domain model to analyze
        use_llm: Whether to use LLM for conflict detection
        apply_auto_fixes: Whether to apply automatic fixes
        previous_answers: User answers from previous iteration for iterative refinement
        return_full_result: If True, return ValidationResponse; if False, update task

    Returns:
        ValidationResponse if return_full_result, else None
    """
    if previous_answers is None:
        previous_answers = {}
    global semantic_analyzer, conflict_detector, question_generator, model_refiner
    
    try:
        # Update task status to working
        if task_id in tasks_store:
            task = tasks_store[task_id]
            task.status = TaskStatus(state=TaskState.WORKING)
            tasks_store[task_id] = task
        
        logger.info(f"[{task_id}] Starting analysis pipeline...")

        # ── Step 0: Pre-apply previous answers BEFORE analysis ──
        # This ensures structural changes (ownership, reclassification, renames)
        # take effect before the analyzers run, so issues get resolved.
        if previous_answers:
            logger.info(f"[{task_id}] Pre-applying {len(previous_answers)} user answers to model")

            # Extract questions from previous iteration (stored in model by refiner)
            prev_questions_data = domain_model.get("_followUpQuestions", [])
            if prev_questions_data:
                from app.services.question_generator import FollowUpQuestion
                prev_questions = [
                    FollowUpQuestion(
                        question_id=q.get("question_id", f"FUQ-{i}"),
                        question=q.get("question", ""),
                        context=q.get("context", ""),
                        related_issue_type=q.get("related_issue_type", "UNKNOWN"),
                        severity=q.get("severity", "MEDIUM"),
                        affected_elements=q.get("affected_elements", []),
                        suggested_answers=q.get("suggested_answers"),
                    )
                    for i, q in enumerate(prev_questions_data)
                ]
                # Apply user answers → modifies domain_model in place
                await model_refiner._apply_user_answers(
                    domain_model, prev_questions, previous_answers, use_llm=use_llm
                )
                logger.info(f"[{task_id}] Applied answers using {len(prev_questions)} previous questions")
            else:
                logger.warning(f"[{task_id}] No _followUpQuestions in model, cannot match answers")

            # Clean up old metadata to prevent accumulation
            domain_model.pop("_validationAnnotations", None)
            domain_model.pop("_followUpQuestions", None)
            # Keep _userGuidedFixes and _ownershipDecisions for history

        # ── Step 1: Semantic Analysis (embeddings-based) ──
        semantic_issues = semantic_analyzer.analyze(domain_model)
        logger.info(f"[{task_id}] Found {len(semantic_issues)} semantic issues")

        # ── Step 2: Conflict Detection (rule-based + LLM) ──
        logger.info(f"[{task_id}] Starting conflict detection...")
        conflict_issues = await conflict_detector.analyze(domain_model, use_llm=use_llm)
        logger.info(f"[{task_id}] Found {len(conflict_issues)} conflict issues")

        # ── Step 3: Generate Follow-up Questions ──
        logger.info(f"[{task_id}] Generating follow-up questions...")
        follow_up_questions = await question_generator.generate_questions(
            semantic_issues,
            conflict_issues,
            max_questions=settings.MAX_FOLLOW_UP_QUESTIONS,
            use_llm=use_llm
        )
        logger.info(f"[{task_id}] Generated {len(follow_up_questions)} questions")

        # ── Step 4: Refine Model (auto-fixes + annotations, NO re-apply answers) ──
        logger.info(f"[{task_id}] Refining model...")
        refined_model, refinement_report = await model_refiner.refine_model(
            domain_model,
            semantic_issues,
            conflict_issues,
            follow_up_questions,
            previous_answers={},
            apply_auto_fixes=apply_auto_fixes,
            use_llm=use_llm
        )
        logger.info(f"[{task_id}] Model refinement complete")
        
        # Build summary
        summary = ValidationSummary(
            total_issues=len(semantic_issues) + len(conflict_issues),
            entity_overlaps=sum(1 for i in semantic_issues if i.issue_type.value == "ENTITY_OVERLAP"),
            semantic_ambiguities=sum(1 for i in semantic_issues if i.issue_type.value == "SEMANTIC_AMBIGUITY"),
            requirement_conflicts=sum(1 for i in conflict_issues if i.conflict_type.value == "REQUIREMENT_CONFLICT"),
            duplicate_events=sum(1 for i in conflict_issues if i.conflict_type.value == "DUPLICATE_EVENT"),
            naming_violations=sum(1 for i in conflict_issues if i.conflict_type.value == "NAMING_VIOLATION"),
            incompatible_patterns=sum(1 for i in conflict_issues if i.conflict_type.value == "INCOMPATIBLE_PATTERN"),
            misclassified_domains=sum(1 for i in conflict_issues if i.conflict_type.value == "MISCLASSIFIED_DOMAIN"),
            auto_fixed=refinement_report.auto_fixed,
            requires_manual=refinement_report.requires_manual
        )
        
        # Determine status
        status = "VALID" if summary.total_issues == 0 else "ISSUES_FOUND"

        # ── Step 5: Estimate iterations needed (LLM, fallback to heuristic) ──
        suggested_max_iterations = await _estimate_iterations(
            summary, semantic_issues, conflict_issues, use_llm=use_llm
        )
        logger.info(f"[{task_id}] Suggested max iterations: {suggested_max_iterations}")

        result = ValidationResponse(
            status=status,
            task_id=task_id,
            summary=summary,
            semantic_issues=[i.to_dict() for i in semantic_issues],
            conflict_issues=[i.to_dict() for i in conflict_issues],
            follow_up_questions=[q.to_dict() for q in follow_up_questions],
            refinement_report=refinement_report.to_dict(),
            refined_model=refined_model,
            suggested_max_iterations=suggested_max_iterations
        )
        
        # Update task if stored
        if task_id in tasks_store:
            task = tasks_store[task_id]
            task.status = TaskStatus(state=TaskState.COMPLETED)
            
            # Add artifacts
            task.artifacts = [
                Artifact.from_data(
                    data=result.model_dump(),
                    name="validation_report",
                    description="Complete validation report with issues and refined model"
                )
            ]
            tasks_store[task_id] = task
        
        # Save output to file
        await _save_output(task_id, result)
        
        if return_full_result:
            return result
            
    except Exception as e:
        logger.error(f"[{task_id}] Analysis failed: {e}", exc_info=True)
        
        if task_id in tasks_store:
            task = tasks_store[task_id]
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    role=Role.AGENT,
                    parts=[Part.from_text(f"Analysis failed: {str(e)}")]
                )
            )
            tasks_store[task_id] = task
        
        if return_full_result:
            raise


async def _save_output(task_id: str, result: ValidationResponse):
    """Save validation output to file for Agent 3."""
    try:
        output_dir = Path(settings.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"validation_{task_id}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        
        logger.info(f"Output saved to {output_file}")
    except Exception as e:
        logger.warning(f"Failed to save output: {e}")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )



