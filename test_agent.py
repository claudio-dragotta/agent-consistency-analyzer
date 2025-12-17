"""
Quick test script to verify the Agent 2 implementation.

Usage:
    python test_agent.py
    
This script tests the analysis pipeline with the example_bad.json file.
"""

import asyncio
import json
from pathlib import Path


async def test_analysis():
    """Test the full analysis pipeline."""
    
    # Import services
    from app.config import settings
    from app.services.semantic_analyzer import SemanticAnalyzer
    from app.services.conflict_detector import ConflictDetector
    from app.services.question_generator import QuestionGenerator
    from app.services.model_refiner import ModelRefiner
    
    # Load test data
    test_file = Path("input_agent/example_bad.json")
    if not test_file.exists():
        print(f" Test file not found: {test_file}")
        return
    
    print(f" Loading test file: {test_file}")
    with open(test_file, "r", encoding="utf-8") as f:
        domain_model = json.load(f)
    
    # Expected problems from the test file
    expected_problems = domain_model.get("_testingNotes", {}).get("expectedProblems", [])
    print(f"\n Expected problems: {len(expected_problems)}")
    for problem in expected_problems:
        print(f"   - {problem}")
    
    # Initialize services
    print("\n Initializing services...")
    semantic_analyzer = SemanticAnalyzer(
        model_name=settings.EMBEDDINGS_MODEL,
        similarity_threshold=settings.SEMANTIC_SIMILARITY_THRESHOLD
    )
    conflict_detector = ConflictDetector(settings)
    question_generator = QuestionGenerator(settings)
    model_refiner = ModelRefiner(settings)
    
    # Step 1: Semantic Analysis
    print("\n Running semantic analysis...")
    try:
        semantic_issues = semantic_analyzer.analyze(domain_model)
        print(f"   OK Found {len(semantic_issues)} semantic issues:")
        for issue in semantic_issues:
            print(f"      - [{issue.severity}] {issue.issue_type.value}: {issue.description[:60]}...")
    except Exception as e:
        print(f"    Semantic analysis failed: {e}")
        semantic_issues = []
    
    # Step 2: Conflict Detection (without LLM for quick test)
    print("\n️ Running conflict detection (rule-based only)...")
    try:
        conflict_issues = await conflict_detector.analyze(domain_model, use_llm=False)
        print(f"   OK Found {len(conflict_issues)} conflict issues:")
        for issue in conflict_issues:
            print(f"      - [{issue.severity}] {issue.conflict_type.value}: {issue.description[:60]}...")
    except Exception as e:
        print(f"    Conflict detection failed: {e}")
        conflict_issues = []
    
    # Step 3: Generate Questions
    print("\n Generating follow-up questions...")
    try:
        questions = question_generator.generate_questions(semantic_issues, conflict_issues)
        print(f"   OK Generated {len(questions)} questions:")
        for q in questions[:3]:  # Show first 3
            print(f"      - [{q.severity}] {q.question[:60]}...")
    except Exception as e:
        print(f"    Question generation failed: {e}")
        questions = []
    
    # Step 4: Refine Model
    print("\n Refining model...")
    try:
        refined_model, report = model_refiner.refine_model(
            domain_model,
            semantic_issues,
            conflict_issues,
            questions,
            apply_auto_fixes=True
        )
        print(f"   OK Refinement complete:")
        print(f"      - Total issues: {report.total_issues}")
        print(f"      - Auto-fixed: {report.auto_fixed}")
        print(f"      - Requires manual: {report.requires_manual}")
    except Exception as e:
        print(f"    Model refinement failed: {e}")
    
    # Summary
    total_found = len(semantic_issues) + len(conflict_issues)
    print(f"\n Summary:")
    print(f"   - Expected problems: {len(expected_problems)}")
    print(f"   - Total found: {total_found}")
    print(f"   - Semantic issues: {len(semantic_issues)}")
    print(f"   - Conflict issues: {len(conflict_issues)}")
    print(f"   - Follow-up questions: {len(questions)}")
    
    if total_found > 0:
        print("\nOK Analysis pipeline is working!")
    else:
        print("\nWARNING️ No issues detected - check if services initialized correctly")


def test_imports():
    """Test that all imports work."""
    print(" Testing imports...")
    
    try:
        from app.config import settings
        print("   OK app.config")
    except ImportError as e:
        print(f"    app.config: {e}")
    
    try:
        from app.services import (
            SemanticAnalyzer, ConflictDetector, 
            QuestionGenerator, ModelRefiner
        )
        print("   OK app.services")
    except ImportError as e:
        print(f"    app.services: {e}")
    
    try:
        from a2a.models import Task, Message, Artifact
        print("   OK a2a.models")
    except ImportError as e:
        print(f"    a2a.models: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Agent 2 - Consistency & Conflict Analyzer - Test Script")
    print("=" * 60)
    
    test_imports()
    
    print("\n" + "=" * 60)
    print("Running Analysis Pipeline Test")
    print("=" * 60)
    
    asyncio.run(test_analysis())
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nTo start the server, run:")
    print("  uvicorn app.main:app --reload --port 8002")


if __name__ == "__main__":
    main()
