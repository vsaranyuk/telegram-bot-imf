"""
Test dataset with 20 known questions and 10 known Q&A pairs
for validating AI analysis accuracy (AC-002: >90% question detection, AC-003: >85% answer mapping)
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any


# Dataset 1: 20 Known Questions for Question Detection Accuracy Testing (AC-002)
KNOWN_QUESTIONS = [
    {
        "id": 1,
        "text": "Когда будет готов отчёт по продажам за прошлый месяц?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 9, 30),
    },
    {
        "id": 2,
        "text": "Как настроить подключение к базе данных PostgreSQL?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 10, 15),
    },
    {
        "id": 3,
        "text": "Можете объяснить алгоритм кэширования в нашем сервисе?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 11, 0),
    },
    {
        "id": 4,
        "text": "Сколько пользователей зарегистрировались на прошлой неделе?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 11, 45),
    },
    {
        "id": 5,
        "text": "Почему тесты падают на CI?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 12, 30),
    },
    {
        "id": 6,
        "text": "Кто может помочь с проблемой в authentication модуле?",
        "category": "other",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 13, 15),
    },
    {
        "id": 7,
        "text": "Какой бюджет на рекламу в следующем квартале?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 14, 0),
    },
    {
        "id": 8,
        "text": "Где находится документация по API эндпоинтам?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 14, 45),
    },
    {
        "id": 9,
        "text": "Нужно ли обновить зависимости перед релизом?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 15, 30),
    },
    {
        "id": 10,
        "text": "Какие метрики мы отслеживаем для конверсии?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 16, 15),
    },
    {
        "id": 11,
        "text": "Как исправить ошибку 500 на production?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 17, 0),
    },
    {
        "id": 12,
        "text": "Когда планируется запуск новой фичи?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 17, 45),
    },
    {
        "id": 13,
        "text": "Какая версия Python используется в проекте?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 18, 30),
    },
    {
        "id": 14,
        "text": "Можете прислать ссылку на дизайн-макеты?",
        "category": "other",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 19, 15),
    },
    {
        "id": 15,
        "text": "Какой статус у таски IMF-MVP-1?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 20, 0),
    },
    {
        "id": 16,
        "text": "Как добавить новый эндпоинт в FastAPI?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 20, 45),
    },
    {
        "id": 17,
        "text": "Кто знает?",  # Edge case: rhetorical question
        "category": "other",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 21, 30),
    },
    {
        "id": 18,
        "text": "Нужна ли миграция базы данных или можно обойтись без неё?",  # Edge case: multi-part
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 22, 15),
    },
    {
        "id": 19,
        "text": "Какие есть риски у текущего архитектурного решения?",
        "category": "technical",
        "is_question": True,
        "timestamp": datetime(2025, 10, 23, 23, 0),
    },
    {
        "id": 20,
        "text": "Сколько времени займёт интеграция с Claude API?",
        "category": "business",
        "is_question": True,
        "timestamp": datetime(2025, 10, 24, 0, 0),
    },
]


# Dataset 2: 10 Known Q&A Pairs for Answer Mapping Accuracy Testing (AC-003)
KNOWN_QA_PAIRS = [
    {
        "question_id": 101,
        "question_text": "Когда релиз новой версии?",
        "question_category": "business",
        "question_timestamp": datetime(2025, 10, 23, 9, 0),
        "answer_id": 102,
        "answer_text": "Релиз запланирован на пятницу, 25 октября",
        "answer_timestamp": datetime(2025, 10, 23, 9, 15),
        "response_time_minutes": 15,
        "response_category": "fast",  # < 1 hour
    },
    {
        "question_id": 103,
        "question_text": "Как запустить тесты локально?",
        "question_category": "technical",
        "question_timestamp": datetime(2025, 10, 23, 10, 0),
        "answer_id": 104,
        "answer_text": "Запусти pytest из корня проекта: pytest tests/",
        "answer_timestamp": datetime(2025, 10, 23, 10, 5),
        "response_time_minutes": 5,
        "response_category": "fast",  # < 1 hour
    },
    {
        "question_id": 105,
        "question_text": "Какой статус у PR #123?",
        "question_category": "business",
        "question_timestamp": datetime(2025, 10, 23, 11, 0),
        "answer_id": 106,
        "answer_text": "PR #123 проверен и смёрджен в main",
        "answer_timestamp": datetime(2025, 10, 23, 13, 30),
        "response_time_minutes": 150,
        "response_category": "medium",  # 1-4 hours
    },
    {
        "question_id": 107,
        "question_text": "Где найти конфиг для production?",
        "question_category": "technical",
        "question_timestamp": datetime(2025, 10, 23, 14, 0),
        "answer_id": 108,
        "answer_text": "Конфиг лежит в /config/production.yaml",
        "answer_timestamp": datetime(2025, 10, 23, 14, 45),
        "response_time_minutes": 45,
        "response_category": "fast",  # < 1 hour
    },
    {
        "question_id": 109,
        "question_text": "Нужно ли обновлять зависимости?",
        "question_category": "technical",
        "question_timestamp": datetime(2025, 10, 23, 15, 0),
        "answer_id": 110,
        "answer_text": "Да, запусти pip install -U -r requirements.txt",
        "answer_timestamp": datetime(2025, 10, 23, 18, 30),
        "response_time_minutes": 210,
        "response_category": "medium",  # 1-4 hours
    },
    {
        "question_id": 111,
        "question_text": "Какой URL для staging сервера?",
        "question_category": "technical",
        "question_timestamp": datetime(2025, 10, 23, 16, 0),
        "answer_id": 112,
        "answer_text": "https://staging.imf-bot.com",
        "answer_timestamp": datetime(2025, 10, 24, 10, 0),
        "response_time_minutes": 1080,
        "response_category": "slow",  # 4-24 hours
    },
    {
        "question_id": 113,
        "question_text": "Кто может ревьюнуть код?",
        "question_category": "other",
        "question_timestamp": datetime(2025, 10, 23, 17, 0),
        "answer_id": 114,
        "answer_text": "Я посмотрю после обеда",
        "answer_timestamp": datetime(2025, 10, 23, 19, 15),
        "response_time_minutes": 135,
        "response_category": "medium",  # 1-4 hours
    },
    {
        "question_id": 115,
        "question_text": "Когда следующая встреча команды?",
        "question_category": "business",
        "question_timestamp": datetime(2025, 10, 23, 18, 0),
        "answer_id": 116,
        "answer_text": "Завтра в 11:00 по МСК",
        "answer_timestamp": datetime(2025, 10, 23, 18, 10),
        "response_time_minutes": 10,
        "response_category": "fast",  # < 1 hour
    },
    {
        "question_id": 117,
        "question_text": "Как исправить баг с авторизацией?",
        "question_category": "technical",
        "question_timestamp": datetime(2025, 10, 22, 10, 0),
        "answer_id": 118,
        "answer_text": "Проблема была в токене, уже пофиксил",
        "answer_timestamp": datetime(2025, 10, 24, 9, 0),
        "response_time_minutes": 2820,
        "response_category": "very_slow",  # > 24 hours
    },
    {
        "question_id": 119,
        "question_text": "Какие метрики мы отслеживаем?",
        "question_category": "business",
        "question_timestamp": datetime(2025, 10, 23, 20, 0),
        "answer_id": 120,
        "answer_text": "Отслеживаем: активных пользователей, время отклика API, количество ошибок",
        "answer_timestamp": datetime(2025, 10, 23, 20, 30),
        "response_time_minutes": 30,
        "response_category": "fast",  # < 1 hour
    },
]


# Dataset 3: Non-Questions (for false positive testing)
NON_QUESTIONS = [
    {
        "id": 201,
        "text": "Отчёт готов и отправлен в чат.",
        "is_question": False,
        "timestamp": datetime(2025, 10, 23, 9, 45),
    },
    {
        "id": 202,
        "text": "Спасибо за помощь!",
        "is_question": False,
        "timestamp": datetime(2025, 10, 23, 10, 30),
    },
    {
        "id": 203,
        "text": "Понятно, буду знать.",
        "is_question": False,
        "timestamp": datetime(2025, 10, 23, 11, 20),
    },
    {
        "id": 204,
        "text": "Хорошо, приступаю к задаче.",
        "is_question": False,
        "timestamp": datetime(2025, 10, 23, 12, 10),
    },
    {
        "id": 205,
        "text": "Завтра будет готово.",
        "is_question": False,
        "timestamp": datetime(2025, 10, 23, 13, 0),
    },
]


def get_test_messages_with_questions() -> List[Dict[str, Any]]:
    """
    Returns a combined dataset of questions and non-questions for testing question detection.
    Expected: 20 questions detected out of 25 total messages (20 questions + 5 non-questions).
    Target accuracy: >90% (should detect at least 18 out of 20 questions correctly).
    """
    messages = []

    # Add questions
    for q in KNOWN_QUESTIONS:
        messages.append({
            "message_id": q["id"],
            "text": q["text"],
            "timestamp": q["timestamp"],
            "is_question": q["is_question"],
            "expected_category": q["category"],
        })

    # Add non-questions
    for nq in NON_QUESTIONS:
        messages.append({
            "message_id": nq["id"],
            "text": nq["text"],
            "timestamp": nq["timestamp"],
            "is_question": nq["is_question"],
        })

    return sorted(messages, key=lambda x: x["timestamp"])


def get_test_qa_pairs() -> List[Dict[str, Any]]:
    """
    Returns a dataset of known Q&A pairs for testing answer mapping accuracy.
    Expected: 10 Q&A pairs correctly mapped.
    Target accuracy: >85% (should map at least 9 out of 10 pairs correctly, with correct response time categories).
    """
    return KNOWN_QA_PAIRS


def get_validation_criteria() -> Dict[str, Any]:
    """
    Returns validation criteria for AC-002 and AC-003.
    """
    return {
        "AC-002": {
            "description": "Question Detection Accuracy",
            "total_questions": len(KNOWN_QUESTIONS),
            "target_accuracy": 0.90,
            "min_correct_detections": int(len(KNOWN_QUESTIONS) * 0.90),  # 18 out of 20
            "total_non_questions": len(NON_QUESTIONS),
            "max_false_positives": 1,  # Allow 1 false positive
        },
        "AC-003": {
            "description": "Answer Mapping Accuracy",
            "total_qa_pairs": len(KNOWN_QA_PAIRS),
            "target_accuracy": 0.85,
            "min_correct_mappings": int(len(KNOWN_QA_PAIRS) * 0.85),  # 9 out of 10
            "response_time_categories": {
                "fast": "< 1 hour",
                "medium": "1-4 hours",
                "slow": "4-24 hours",
                "very_slow": "> 24 hours",
            },
        },
    }
