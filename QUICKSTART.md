# DevOps LLM Agent - Быстрый старт

## Обзор

DevOps LLM Agent - это автономный помощник для DevOps операций, работающий как инженер DevOps в неоднородных инфраструктурах. Агент может анализировать состояние инфраструктуры, формировать безопасные команды, выполнять их через SSH/Docker/Kubernetes API и проверять результат с минимальным участием человека.

## Возможности

- 🤖 **Автономное планирование** - разбивает задачи на шаги с оценкой рисков
- 🔒 **Безопасность** - строгие политики безопасности и guardrails
- 🌐 **Мульти-провайдер LLM** - поддержка Gemini, Ollama и других провайдеров
- 🛠️ **Инструменты** - SSH, Kubernetes, Docker, Terraform
- 📊 **Наблюдаемость** - метрики, логи, трейсинг, аудит
- 🎯 **Веб-интерфейс** - современный чат-интерфейс для взаимодействия

## Быстрый запуск

### 1. Клонирование и настройка

```bash
git clone <repository-url>
cd agent_test
cp env.example .env
```

### 2. Настройка переменных окружения

Отредактируйте `.env` файл:

```bash
# Обязательные настройки
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-secret-key-here

# Опциональные настройки
DATABASE_URL=postgresql://devops:devops@localhost:5432/devops_agent
REDIS_URL=redis://localhost:6379
```

### 3. Запуск с Docker Compose

```bash
# Запуск всех сервисов
docker-compose -f docker-compose.dev.yml up -d

# Проверка статуса
docker-compose -f docker-compose.dev.yml ps
```

### 4. Доступ к сервисам

- **Веб-интерфейс**: http://localhost:3000
- **API**: http://localhost:8000
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

### 5. Проверка работоспособности

```bash
# Проверка API
curl http://localhost:8000/health

# Проверка UI
curl http://localhost:3000
```

## Локальная разработка

### 1. Установка зависимостей

```bash
# Python зависимости
make bootstrap

# Node.js зависимости (для UI)
cd apps/ui
npm install
```

### 2. Запуск в режиме разработки

```bash
# API сервер
cd apps/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# UI сервер
cd apps/ui
npm run dev
```

### 3. Запуск тестов

```bash
# Python тесты
make test

# Линтинг
make lint

# Валидация окружений
make validate-environments
```

## Использование

### 1. Веб-интерфейс

1. Откройте http://localhost:3000
2. Выберите окружение (dev, staging, prod)
3. Начните чат с агентом

Примеры запросов:
- "Покажи статус всех подов в кластере"
- "Разверни nginx в namespace production"
- "Проверь логи приложения my-app"

### 2. API

```bash
# Отправка сообщения
curl -X POST http://localhost:8000/api/v1/conversation/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Покажи статус подов",
    "environment_profile": "dev-k8s"
  }'

# Проверка статуса задачи
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### 3. CLI (планируется)

```bash
# Планируемая CLI утилита
devops-agent chat "Разверни nginx" --env prod-k8s
devops-agent status --task-id abc123
```

## Конфигурация

### 1. Профили окружений

Создайте профили в `environments/`:

```yaml
# environments/my-env.yaml
id: my-env
display_name: "My Environment"
type: k8s
cluster:
  name: my-cluster
  context: my-context
networking:
  proxy:
    http: http://proxy.local:3128
auth:
  vault_role: my-env/admin
policies:
  risk_level: medium
  require_approval: true
```

### 2. Политики безопасности

Настройте в `config/security.yml`:

```yaml
command_policies:
  blocked_commands:
    - "rm -rf /"
    - "shutdown"
  
  approval_required_commands:
    - "kubectl delete"
    - "terraform destroy"
```

### 3. LLM провайдеры

Настройте в `config/llm.yml`:

```yaml
providers:
  - name: "gemini"
    type: "gemini"
    enabled: true
    config:
      api_key: "${GEMINI_API_KEY}"
      model: "gemini-1.5-flash"
```

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   API Gateway   │    │   Orchestrator  │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Agents)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Database      │    │   Tool Executors│
                       │   (PostgreSQL)  │    │   (SSH/K8s/Docker)│
                       └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Cache         │    │   LLM Providers │
                       │   (Redis)       │    │   (Gemini/Ollama)│
                       └─────────────────┘    └─────────────────┘
```

## Компоненты

### 1. Агенты
- **Planner Agent** - планирует задачи и разбивает на шаги
- **Executor Agent** - выполняет команды через инструменты
- **Verifier Agent** - проверяет результаты выполнения

### 2. Инструменты
- **SSH Executor** - выполнение команд на удаленных хостах
- **Kubectl Executor** - операции с Kubernetes
- **Docker Executor** - управление контейнерами

### 3. Безопасность
- **Command Policies** - блокировка опасных команд
- **Risk Assessment** - оценка рисков операций
- **Approval Policies** - требования к одобрению

### 4. Наблюдаемость
- **Metrics** - Prometheus метрики
- **Logging** - структурированные логи
- **Tracing** - распределенная трассировка
- **Audit** - аудит всех операций

## Мониторинг

### 1. Grafana Dashboards

Доступны дашборды для:
- Обзор системы
- LLM метрики
- Безопасность
- Производительность

### 2. Prometheus Metrics

Основные метрики:
- `llm_requests_total` - количество запросов к LLM
- `tasks_total` - количество задач
- `security_violations_total` - нарушения безопасности
- `system_cpu_usage_percent` - использование CPU

### 3. Логи

Структурированные логи в JSON формате:
- Операции агентов
- Выполнение команд
- События безопасности
- Ошибки системы

## Безопасность

### 1. Политики безопасности

- Блокировка опасных команд
- Оценка рисков операций
- Требования к одобрению
- Аудит всех действий

### 2. Аутентификация

- JWT токены
- RBAC роли
- Интеграция с Vault

### 3. Сетевая безопасность

- TLS шифрование
- Firewall правила
- Сегментация сети

## Разработка

### 1. Структура проекта

```
├── apps/
│   ├── api/                 # FastAPI сервис
│   ├── orchestrator/        # Агенты и планировщик
│   ├── tool-executors/      # Исполнители инструментов
│   └── ui/                  # Next.js фронтенд
├── config/                  # Конфигурационные файлы
├── environments/            # Профили окружений
├── docs/                    # Документация
├── infra/                   # Инфраструктура
├── packages/                # Общие пакеты
└── tests/                   # Тесты
```

### 2. Добавление новых инструментов

1. Создайте класс в `apps/tool-executors/`
2. Наследуйтесь от `BaseToolExecutor`
3. Реализуйте методы `execute()` и `health_check()`
4. Добавьте в конфигурацию

### 3. Добавление новых агентов

1. Создайте класс в `apps/orchestrator/agents/`
2. Наследуйтесь от `BaseAgent`
3. Реализуйте метод `process()`
4. Добавьте в оркестратор

## Устранение неполадок

### 1. Проблемы с запуском

```bash
# Проверка логов
docker-compose -f docker-compose.dev.yml logs

# Перезапуск сервисов
docker-compose -f docker-compose.dev.yml restart

# Очистка данных
docker-compose -f docker-compose.dev.yml down -v
```

### 2. Проблемы с LLM

```bash
# Проверка Ollama
curl http://localhost:11434/api/tags

# Проверка Gemini API
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models
```

### 3. Проблемы с безопасностью

```bash
# Проверка политик
make validate-environments

# Проверка аудит логов
curl http://localhost:8000/api/v1/audit/logs
```

## Поддержка

- 📖 **Документация**: `docs/`
- 🐛 **Issues**: GitHub Issues
- 💬 **Обсуждения**: GitHub Discussions
- 📧 **Email**: support@example.com

## Лицензия

MIT License - см. файл LICENSE для деталей.



