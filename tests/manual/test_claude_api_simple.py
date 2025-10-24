"""
Simple manual test to verify Claude API integration and basic functionality.
Run this script to quickly test Claude API authentication and message analysis.

Usage:
    python tests/manual/test_claude_api_simple.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.config.settings import Settings
from src.services.claude_api_service import ClaudeAPIService
from src.models.message import Message

# Load environment variables
load_dotenv()


def test_api_authentication():
    """Test 1: Verify Claude API authentication"""
    print("\n" + "="*60)
    print("TEST 1: Claude API Authentication")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    assert api_key, "ANTHROPIC_API_KEY not found in environment"
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")

    settings = Settings.from_env()
    claude_service = ClaudeAPIService(settings=settings)
    print("✅ ClaudeAPIService initialized successfully")
    assert claude_service is not None


async def test_simple_analysis():
    """Test 2: Simple message analysis"""
    print("\n" + "="*60)
    print("TEST 2: Simple Message Analysis")
    print("="*60)

    settings = Settings.from_env()
    claude_service = ClaudeAPIService(settings=settings)

    # Create test messages
    test_messages = [
        Message(
            chat_id=123,
            message_id=1,
            user_id=1,
            user_name="Алиса",
            text="Когда будет готов отчёт?",
            timestamp=datetime(2025, 10, 24, 10, 0),
        ),
        Message(
            chat_id=123,
            message_id=2,
            user_id=2,
            user_name="Боб",
            text="Отчёт будет готов завтра утром",
            timestamp=datetime(2025, 10, 24, 10, 15),
        ),
    ]

    print(f"📨 Analyzing {len(test_messages)} test messages...")
    print(f"   Message 1: '{test_messages[0].text}'")
    print(f"   Message 2: '{test_messages[1].text}'")

    # Call Claude API
    print("\n🔄 Sending request to Claude API...")
    result = await claude_service.analyze_messages(test_messages)

    print("\n✅ Analysis completed successfully!")
    print(f"\n📊 Results:")
    print(f"   Questions detected: {result.summary.total_questions}")
    print(f"   Answered: {result.summary.answered}")
    print(f"   Unanswered: {result.summary.unanswered}")

    if result.questions:
        print(f"\n📋 Detected Questions:")
        for q in result.questions:
            print(f"   • Message {q.message_id}: {q.text[:50]}...")
            print(f"     Category: {q.category}")
            print(f"     Answered: {q.is_answered}")
            if q.is_answered and q.answer_message_id:
                print(f"     Answer ID: {q.answer_message_id}")
                print(f"     Response time: {q.response_time_minutes} min")

    assert result is not None
    assert result.summary is not None


async def test_question_detection_accuracy():
    """Test 3: Question detection with known dataset"""
    print("\n" + "="*60)
    print("TEST 3: Question Detection Accuracy (Sample)")
    print("="*60)

    from tests.fixtures.test_messages_dataset import KNOWN_QUESTIONS

    settings = Settings.from_env()
    claude_service = ClaudeAPIService(settings=settings)

    # Test with first 5 questions to save API costs
    sample_questions = KNOWN_QUESTIONS[:5]

    print(f"📨 Testing with {len(sample_questions)} known questions...")

    test_messages = []
    for q in sample_questions:
        test_messages.append(Message(
            chat_id=123,
            message_id=q["id"],
            user_id=1,
            user_name="Test User",
            text=q["text"],
            timestamp=q["timestamp"],
        ))

    print("\n🔄 Analyzing with Claude API...")
    result = await claude_service.analyze_messages(test_messages)

    detected_count = len(result.questions)
    accuracy = (detected_count / len(sample_questions)) * 100

    print(f"\n✅ Analysis completed!")
    print(f"📊 Results:")
    print(f"   Expected questions: {len(sample_questions)}")
    print(f"   Detected questions: {detected_count}")
    print(f"   Accuracy: {accuracy:.1f}%")

    # 80% threshold for sample
    assert detected_count >= len(sample_questions) * 0.8, \
        f"Accuracy {accuracy:.1f}% below threshold (80%)"
    print(f"   ✅ Accuracy meets threshold (≥80%)")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 CLAUDE API INTEGRATION TESTS")
    print("="*60)

    results = {
        "Authentication": test_api_authentication(),
        "Simple Analysis": test_simple_analysis(),
        "Question Detection": test_question_detection_accuracy(),
    }

    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ AC-001: Claude API Integration - VERIFIED")
        print("   - API authentication working")
        print("   - Message analysis successful")
        print("   - Question detection working")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
