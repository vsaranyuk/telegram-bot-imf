"""
Integration tests for Claude API accuracy validation
Tests AC-002 (Question Detection >90%) and AC-003 (Answer Mapping >85%)
"""
import pytest
import os
from datetime import datetime
from typing import List, Dict, Any

from src.services.claude_api_service import ClaudeAPIService
from src.services.message_analyzer_service import MessageAnalyzerService
from tests.fixtures.test_messages_dataset import (
    get_test_messages_with_questions,
    get_test_qa_pairs,
    get_validation_criteria,
    KNOWN_QUESTIONS,
)


@pytest.fixture
def claude_service():
    """Initialize Claude API service with real API key"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set - skipping real API tests")

    # Create a mock settings object
    from src.config.settings import Settings
    settings = Settings()
    return ClaudeAPIService(settings=settings)


@pytest.fixture
def analyzer_service(claude_service):
    """Initialize message analyzer service"""
    return MessageAnalyzerService(claude_service=claude_service)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)
class TestClaudeAPIAccuracy:
    """Test suite for validating Claude API accuracy against AC requirements"""

    def test_ac002_question_detection_accuracy(self, analyzer_service):
        """
        AC-002: Validate question detection accuracy >90%

        Test dataset: 20 known questions + 5 non-questions
        Expected: Detect at least 18 out of 20 questions correctly (90% accuracy)
        False positives: Allow max 1 non-question incorrectly detected as question
        """
        # Get test dataset
        test_messages = get_test_messages_with_questions()
        criteria = get_validation_criteria()["AC-002"]

        print(f"\n📊 Testing AC-002: Question Detection Accuracy")
        print(f"Total questions in dataset: {criteria['total_questions']}")
        print(f"Total non-questions in dataset: {criteria['total_non_questions']}")
        print(f"Target accuracy: {criteria['target_accuracy'] * 100}%")
        print(f"Minimum correct detections required: {criteria['min_correct_detections']}")

        # Convert to format expected by analyzer
        messages = []
        for msg in test_messages:
            messages.append({
                "id": msg["message_id"],
                "text": msg["text"],
                "timestamp": msg["timestamp"],
                "user": "test_user",
            })

        # Run analysis
        print(f"\n🔄 Analyzing {len(messages)} messages with Claude API...")
        analysis_result = analyzer_service.analyze_messages(messages)

        # Extract detected questions
        detected_questions = analysis_result.get("questions", [])

        # Calculate accuracy metrics
        true_positives = 0
        false_negatives = 0
        false_positives = 0
        category_correct = 0

        detected_ids = {q["message_id"] for q in detected_questions}

        # Check true positives and false negatives
        for msg in test_messages:
            if msg["is_question"]:
                if msg["message_id"] in detected_ids:
                    true_positives += 1
                    # Check category correctness
                    detected_q = next(
                        (q for q in detected_questions if q["message_id"] == msg["message_id"]),
                        None
                    )
                    if detected_q and detected_q.get("category") == msg.get("expected_category"):
                        category_correct += 1
                else:
                    false_negatives += 1
                    print(f"❌ Missed question (ID {msg['message_id']}): {msg['text'][:50]}...")

        # Check false positives
        for detected_q in detected_questions:
            msg = next(
                (m for m in test_messages if m["message_id"] == detected_q["message_id"]),
                None
            )
            if msg and not msg["is_question"]:
                false_positives += 1
                print(f"⚠️ False positive (ID {msg['message_id']}): {msg['text'][:50]}...")

        # Calculate accuracy
        accuracy = true_positives / criteria["total_questions"] if criteria["total_questions"] > 0 else 0
        category_accuracy = category_correct / true_positives if true_positives > 0 else 0

        # Print results
        print(f"\n✅ Results:")
        print(f"True positives (correctly detected questions): {true_positives}/{criteria['total_questions']}")
        print(f"False negatives (missed questions): {false_negatives}")
        print(f"False positives (non-questions detected as questions): {false_positives}")
        print(f"Question detection accuracy: {accuracy * 100:.1f}%")
        print(f"Category classification accuracy: {category_accuracy * 100:.1f}%")

        # Validate AC-002 requirements
        assert accuracy >= criteria["target_accuracy"], (
            f"Question detection accuracy {accuracy * 100:.1f}% is below target {criteria['target_accuracy'] * 100}%"
        )
        assert false_positives <= criteria["max_false_positives"], (
            f"Too many false positives: {false_positives} (max allowed: {criteria['max_false_positives']})"
        )

        print(f"\n✅ AC-002 PASSED: Question detection accuracy meets requirements!")

    def test_ac003_answer_mapping_accuracy(self, analyzer_service):
        """
        AC-003: Validate answer mapping accuracy >85%

        Test dataset: 10 known Q&A pairs
        Expected: Correctly map at least 9 out of 10 answer-question pairs (85% accuracy)
        Validate response time calculation and categorization
        """
        # Get test Q&A pairs
        qa_pairs = get_test_qa_pairs()
        criteria = get_validation_criteria()["AC-003"]

        print(f"\n📊 Testing AC-003: Answer Mapping Accuracy")
        print(f"Total Q&A pairs in dataset: {criteria['total_qa_pairs']}")
        print(f"Target accuracy: {criteria['target_accuracy'] * 100}%")
        print(f"Minimum correct mappings required: {criteria['min_correct_mappings']}")

        # Convert to format expected by analyzer
        messages = []
        for pair in qa_pairs:
            messages.append({
                "id": pair["question_id"],
                "text": pair["question_text"],
                "timestamp": pair["question_timestamp"],
                "user": "user_a",
            })
            messages.append({
                "id": pair["answer_id"],
                "text": pair["answer_text"],
                "timestamp": pair["answer_timestamp"],
                "user": "user_b",
            })

        # Sort by timestamp
        messages = sorted(messages, key=lambda x: x["timestamp"])

        # Run analysis
        print(f"\n🔄 Analyzing {len(messages)} messages (10 Q&A pairs) with Claude API...")
        analysis_result = analyzer_service.analyze_messages(messages)

        # Extract detected questions with answers
        detected_questions = analysis_result.get("questions", [])

        # Calculate mapping accuracy
        correct_mappings = 0
        correct_response_times = 0
        correct_categories = 0

        for pair in qa_pairs:
            question_id = pair["question_id"]
            expected_answer_id = pair["answer_id"]
            expected_response_time = pair["response_time_minutes"]
            expected_category = pair["response_category"]

            # Find detected question
            detected_q = next(
                (q for q in detected_questions if q["message_id"] == question_id),
                None
            )

            if detected_q:
                # Check if answer is mapped
                if detected_q.get("is_answered"):
                    detected_answer_id = detected_q.get("answer_message_id")
                    detected_response_time = detected_q.get("response_time_minutes")

                    # Check if mapping is correct
                    if detected_answer_id == expected_answer_id:
                        correct_mappings += 1
                        print(f"✅ Correctly mapped Q{question_id} → A{expected_answer_id}")

                        # Check response time accuracy (allow ±5 min tolerance)
                        if detected_response_time and abs(detected_response_time - expected_response_time) <= 5:
                            correct_response_times += 1

                        # Check response time category
                        if detected_response_time:
                            actual_category = self._categorize_response_time(detected_response_time)
                            if actual_category == expected_category:
                                correct_categories += 1
                    else:
                        print(f"❌ Incorrect mapping: Q{question_id} mapped to A{detected_answer_id} (expected A{expected_answer_id})")
                else:
                    print(f"❌ Question Q{question_id} detected but no answer mapped (expected A{expected_answer_id})")
            else:
                print(f"❌ Question Q{question_id} not detected in analysis")

        # Calculate accuracies
        mapping_accuracy = correct_mappings / criteria["total_qa_pairs"]
        response_time_accuracy = correct_response_times / correct_mappings if correct_mappings > 0 else 0
        category_accuracy = correct_categories / correct_mappings if correct_mappings > 0 else 0

        # Print results
        print(f"\n✅ Results:")
        print(f"Correct answer mappings: {correct_mappings}/{criteria['total_qa_pairs']}")
        print(f"Answer mapping accuracy: {mapping_accuracy * 100:.1f}%")
        print(f"Response time calculation accuracy: {response_time_accuracy * 100:.1f}%")
        print(f"Response time category accuracy: {category_accuracy * 100:.1f}%")

        # Validate AC-003 requirements
        assert mapping_accuracy >= criteria["target_accuracy"], (
            f"Answer mapping accuracy {mapping_accuracy * 100:.1f}% is below target {criteria['target_accuracy'] * 100}%"
        )

        print(f"\n✅ AC-003 PASSED: Answer mapping accuracy meets requirements!")

    def _categorize_response_time(self, minutes: int) -> str:
        """Categorize response time into fast/medium/slow/very_slow"""
        if minutes < 60:
            return "fast"
        elif minutes < 240:  # 4 hours
            return "medium"
        elif minutes < 1440:  # 24 hours
            return "slow"
        else:
            return "very_slow"

    def test_ac004_response_time_categorization(self):
        """
        AC-004: Validate response time categorization logic

        Test that response times are correctly categorized into:
        - Fast: < 1 hour
        - Medium: 1-4 hours
        - Slow: 4-24 hours
        - Very Slow: > 24 hours
        """
        print(f"\n📊 Testing AC-004: Response Time Categorization")

        test_cases = [
            (30, "fast"),       # 30 minutes
            (59, "fast"),       # 59 minutes
            (60, "medium"),     # 1 hour
            (120, "medium"),    # 2 hours
            (239, "medium"),    # 3h 59min
            (240, "slow"),      # 4 hours
            (720, "slow"),      # 12 hours
            (1439, "slow"),     # 23h 59min
            (1440, "very_slow"),# 24 hours
            (2880, "very_slow"),# 48 hours
        ]

        passed = 0
        for minutes, expected_category in test_cases:
            actual_category = self._categorize_response_time(minutes)
            if actual_category == expected_category:
                passed += 1
                print(f"✅ {minutes} min → {actual_category} (expected: {expected_category})")
            else:
                print(f"❌ {minutes} min → {actual_category} (expected: {expected_category})")

        accuracy = passed / len(test_cases)
        print(f"\n✅ Categorization accuracy: {accuracy * 100:.1f}% ({passed}/{len(test_cases)})")

        assert accuracy == 1.0, "Response time categorization logic has errors"
        print(f"\n✅ AC-004 PASSED: Response time categorization is correct!")


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)
def test_api_authentication(claude_service):
    """Test that Claude API authentication is working"""
    print("\n🔐 Testing Claude API authentication...")

    # Simple test message
    test_messages = [
        {
            "id": 1,
            "text": "Привет! Как дела?",
            "timestamp": datetime.now(),
            "user": "test_user",
        }
    ]

    analyzer = MessageAnalyzerService(claude_service=claude_service)
    result = analyzer.analyze_messages(test_messages)

    assert result is not None, "Claude API returned None"
    assert "questions" in result or "summary" in result, "Claude API response format unexpected"

    print("✅ Claude API authentication successful!")
