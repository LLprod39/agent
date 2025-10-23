# 🚀 Руководство по Настройке DevOps AI Агента

## ✅ Что Уже Работает

Базовая инфраструктура агента полностью функциональна:

- ✅ LLM Router с multi-provider поддержкой
- ✅ Planner Agent (создание планов)
- ✅ Executor Agent (выполнение команд)
- ✅ Verifier Agent (проверка результатов)
- ✅ Local Provider (простые планы без интернета)
- ✅ Orchestrator (координация всех агентов)
- ✅ Database с миграциями
- ✅ Authentication система
- ✅ API endpoints

## 🔧 Быстрый Старт

### 1. Проверка Работы (БЕЗ Gemini)

```bash
# Запустить демонстрацию с local provider
python demo_simple.py
```

Это покажет что система работает, но планы будут простыми (local provider).

### 2. Настройка Gemini API (Рекомендуется)

#### Шаг 1: Получить API ключ

1. Перейти на https://aistudio.google.com/app/apikey
2. Нажать "Create API key"
3. Скопировать ключ

#### Шаг 2: Активировать API

**ВАЖНО:** API ключ должен иметь доступ к Gemini API. Проверьте:

1. Перейдите в https://console.cloud.google.com/
2. Выберите ваш проект
3. Перейдите в "APIs & Services" > "Library"
4. Найдите "Generative Language API"
5. Нажмите "Enable"

#### Шаг 3: Проверить Квоту

1. https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
2. Убедитесь что есть доступные квоты

#### Шаг 4: Обновить Конфигурацию

Ваш API ключ уже добавлен в `config/llm.yml`:

```yaml
gemini:
  type: gemini
  priority: 10
  enabled: true
  config:
    api_key: AIzaSyBdMFRLoZPNVPyqSZ2CL4SoQQ7_4PnRpW4
    model: gemini-1.5-flash
```

#### Шаг 5: Тестирование Gemini

```bash
python test_agent_workflow.py
```

Если видите ошибку 403:
- Проверьте что API включен в Google Cloud Console
- Убедитесь что ключ правильный
- Проверьте квоты

### 3. Настройка SSH Подключений

Для выполнения команд на реальных серверах нужно настроить SSH.

#### Создать Environment Profile

Файл: `environments/my-server.yaml`

```yaml
id: my-server
display_name: My Development Server
type: vm
auth:
  ssh_key_path: ~/.ssh/id_rsa
  username: admin
networking:
  bastion: bastion.example.com  # Опционально
policies:
  risk_level: medium
  require_approval: false
defaults:
  working_directory: /home/admin
```

#### Тестирование SSH

```bash
# Через CLI
python -m apps.cli.main run "Проверь использование CPU" -e my-server

# Через API (запустите сервер)
uvicorn apps.api.main:app --reload

# В другом терминале
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Собери метрики CPU и памяти",
    "environment_profile": "my-server",
    "auto_approve": true
  }'
```

## 📊 Текущий Статус

### Работает ✅

1. **Planning**: Создание планов из задач
2. **Local Provider**: Базовые планы без интернета
3. **Orchestration**: Координация агентов
4. **Database**: Сохранение задач
5. **API**: REST endpoints для всех операций
6. **CLI Tool**: Командная строка

### Требует Настройки ⚙️

1. **Gemini API**: Нужно активировать в Google Cloud
   - Текущая ошибка: 403 Forbidden
   - Решение: Включить "Generative Language API"

2. **SSH Connections**: Нужны реальные серверы
   - Создать environment profiles
   - Настроить SSH ключи

3. **Execution**: Работает, но нужны серверы для тестирования

## 🐛 Известные Проблемы

### 1. Gemini API 403 Forbidden

**Проблема**:
```
403 Forbidden. Your client does not have permission to get URL
/v1beta/models/gemini-1.5-flash:generateContent
```

**Решения**:

1. **Проверить активацию API**:
   - https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
   - Нажать "Enable"

2. **Создать новый API ключ**:
   - https://aistudio.google.com/app/apikey
   - Create API key > Create API key in new project

3. **Проверить квоты**:
   - https://console.cloud.google.com/iam-admin/quotas
   - Искать "Generative Language API"

4. **Альтернатива - использовать Ollama локально**:
   ```bash
   # Установить Ollama
   curl https://ollama.ai/install.sh | sh

   # Скачать модель
   ollama pull llama3

   # В config/llm.yml включить:
   ollama:
     enabled: true
     config:
       base_url: http://localhost:11434
       model: llama3
   ```

### 2. Local Provider дает простые планы

**Это нормально**. Local provider - это fallback для работы без интернета.
Он создает базовые планы используя правила, а не AI.

Для умных планов нужен Gemini или Ollama.

## 📝 Примеры Использования

### CLI

```bash
# Установить CLI
pip install -e .

# Логин
devops-agent login --username admin

# Выполнить задачу
devops-agent run "Проверь статус nginx" -e dev-vm

# Интерактивный режим
devops-agent interactive

# Посмотреть статус задачи
devops-agent status <task-id>

# Список задач
devops-agent list
```

### Python API

```python
import asyncio
from config.settings import get_settings
from apps.orchestrator.llm_router import LLMRouter
from apps.orchestrator.agents import PlannerAgent, AgentRequest

async def run_task():
    settings = get_settings()
    llm_router = LLMRouter(settings.llm_providers)
    planner = PlannerAgent({"name": "planner"}, llm_router)

    request = AgentRequest(
        task="Собери метрики CPU и памяти",
        context={"environment": "dev"}
    )

    response = await planner.process(request)
    print(response.metadata["plan"])

asyncio.run(run_task())
```

### REST API

```bash
# Запустить сервер
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Создать задачу
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Проверь использование диска",
    "environment_profile": "dev-vm",
    "auto_approve": true
  }'

# Получить статус
curl http://localhost:8000/api/v1/tasks/{task_id}

# Health check
curl http://localhost:8000/health
```

## 🎯 Следующие Шаги

1. **Настроить Gemini API** для умных планов
2. **Добавить SSH серверы** для реального выполнения
3. **Протестировать полный workflow**: Задача → План → Выполнение → Проверка → Отчет
4. **Настроить Web UI** (уже есть компоненты)

## 💡 Советы

- Начните с simple demo (`python demo_simple.py`)
- Используйте local provider для разработки
- Gemini дает НАМНОГО лучшие планы
- SSH можно тестировать на localhost
- Включите debug logging: `export LOG_LEVEL=DEBUG`

## 📞 Помощь

Если что-то не работает:

1. Проверьте логи
2. Запустите `python demo_simple.py`
3. Проверьте что все зависимости установлены: `pip install -r requirements.txt`
4. Проверьте .env файл

## ✅ Checklist Готовности

- [x] Базовая инфраструктура работает
- [x] Local provider работает
- [ ] Gemini API настроен и работает
- [ ] SSH подключение к серверу настроено
- [ ] Полный workflow протестирован
- [ ] Web UI запущен
- [ ] CLI установлен
