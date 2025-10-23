#!/usr/bin/env python
"""Простая демонстрация работы агента."""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from apps.orchestrator.llm_router import LLMRouter, LLMRequest
from apps.orchestrator.agents import PlannerAgent, AgentRequest


def print_banner(text):
    """Print a nice banner."""
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"  {text}")
    logger.info("=" * 80)


async def demo_workflow():
    """Demonstrate the agent workflow."""
    print_banner("🤖 ДЕМОНСТРАЦИЯ DEVOPS AI АГЕНТА")

    logger.info("""
Этот агент может:
✅ Понимать задачи на русском языке
✅ Создавать план выполнения
✅ Определять необходимые команды
✅ Оценивать риски
✅ Запрашивать подтверждение для опасных операций
    """)

    # Initialize components
    logger.info("🔧 Инициализация компонентов...")
    settings = get_settings()
    llm_router = LLMRouter(settings.llm_providers)
    planner = PlannerAgent({"name": "planner"}, llm_router)
    logger.info("✅ Компоненты инициализированы")

    # Test tasks
    test_tasks = [
        {
            "name": "Проверка метрик системы",
            "task": "Собери метрики CPU и использования памяти на сервере",
            "context": {
                "environment": "development",
                "server": "dev-vm-01"
            }
        },
        {
            "name": "Проверка дискового пространства",
            "task": "Проверь свободное место на диске и покажи топ 10 самых больших файлов",
            "context": {
                "environment": "development",
                "threshold": "80%"
            }
        },
        {
            "name": "Проверка статуса сервиса",
            "task": "Проверь работает ли nginx и покажи его статус",
            "context": {
                "environment": "production",
                "service": "nginx"
            }
        }
    ]

    for i, test_task in enumerate(test_tasks, 1):
        print_banner(f"ЗАДАЧА {i}/{len(test_tasks)}: {test_task['name']}")

        logger.info(f"\n📝 Задача: {test_task['task']}")
        logger.info(f"🌍 Окружение: {test_task['context'].get('environment', 'N/A')}")

        # Create request
        request = AgentRequest(
            task=test_task["task"],
            context=test_task["context"],
            environment_profile={
                "id": test_task['context'].get('environment', 'dev'),
                "type": "vm",
                "policies": {
                    "risk_level": "medium",
                    "require_approval": False
                }
            }
        )

        logger.info("\n⏳ Планирование...")

        # Process request
        response = await planner.process(request)

        if response.status.value == "completed":
            logger.info("\n✅ ПЛАН СОЗДАН УСПЕШНО\n")

            if response.metadata and "plan" in response.metadata:
                plan = response.metadata["plan"]

                logger.info(f"📋 Описание: {plan.get('description', 'N/A')}")
                logger.info(f"⚠️  Уровень риска: {plan.get('risk_level', 'N/A').upper()}")
                logger.info(f"🔐 Требуется подтверждение: {'Да' if plan.get('requires_approval') else 'Нет'}")

                steps = plan.get("steps", [])
                logger.info(f"\n📝 Шаги выполнения ({len(steps)}):\n")

                for step_num, step in enumerate(steps, 1):
                    logger.info(f"   {step_num}. {step.get('description')}")
                    if step.get('command'):
                        logger.info(f"      💻 Команда: {step.get('command')}")
                    logger.info(f"      🔧 Инструмент: {step.get('tool', 'N/A')}")
                    logger.info(f"      ⚠️  Риск: {step.get('risk_level', 'N/A')}")
                    logger.info("")

                duration = plan.get('estimated_duration', 0)
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    logger.info(f"⏱️  Примерное время выполнения: {minutes}м {seconds}с")

        else:
            logger.error(f"\n❌ ОШИБКА: {response.error}")

        logger.info("\n" + "-" * 80)

        if i < len(test_tasks):
            logger.info("")
            await asyncio.sleep(1)  # Small pause between tasks

    print_banner("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")

    logger.info("""
✅ Агент успешно обработал все задачи!

📌 Что показано:
   • Планирование задач на русском языке
   • Разбиение на шаги выполнения
   • Определение команд и инструментов
   • Оценка рисков
   • Определение необходимости подтверждения

🚀 Следующие шаги:
   1. Настроить SSH подключение к серверу
   2. Добавить execution агента для выполнения команд
   3. Добавить verification агента для проверки результатов
   4. Настроить Gemini API для более умных планов

📖 Для полной документации см. README.md
    """)


async def main():
    """Main entry point."""
    try:
        await demo_workflow()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Демонстрация прервана пользователем")
    except Exception as e:
        logger.error(f"\n\n❌ Ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
