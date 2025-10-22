# 🚀 DevOps LLM Agent - Production-Ready Linux Server AI Assistant

**Версия:** 1.0.0-beta
**Статус:** Production-Ready Beta
**Общая Готовность:** 88%

---

## 🎯 Что Это Такое?

**DevOps LLM Agent** - это интеллектуальный AI-агент уровня Claude Code, специально созданный для управления Linux серверами через SSH. Агент понимает естественный язык, автоматически планирует задачи, выполняет операции, учится на опыте и проактивно следит за здоровьем систем.

### 🌟 Ключевые Особенности

- 🤖 **Интеллектуальный AI** - понимает естественный язык и контекст разговора
- 🔐 **Безопасность** - JWT auth, RBAC, command policies, полный audit trail
- 📊 **Умная Аналитика** - сбор метрик, анализ логов, pattern recognition
- 🏥 **Проактивный Мониторинг** - автоматическое обнаружение проблем и auto-remediation
- 💬 **Multi-Turn Conversations** - контекстно-зависимые диалоги с clarification
- 🎓 **Самообучение** - учится на успешных операциях и оптимизирует планы
- ⚡ **Error Recovery** - автоматический retry, rollback при сбоях
- 🔄 **Database Persistence** - сохранение задач, история не теряется

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI / CLI                          │
│              (Next.js / Python CLI)                      │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/WebSocket
┌───────────────────────▼─────────────────────────────────┐
│                  FastAPI REST API                        │
│         (JWT Auth, Rate Limiting, CORS)                  │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│              Enhanced Orchestrator V2                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Context & Memory   │   Learning Engine          │   │
│  │  Conversation Mgr   │   Health Monitor           │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Planner → Executor → Verifier  (3-Agent System) │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌─────▼────┐ ┌───────▼────────┐
│ SSH Executor │ │ K8s Exec │ │ Docker Executor│
│ + Config     │ │          │ │                │
│ + System Info│ │          │ │                │
│ + Log Analyze│ │          │ │                │
└──────────────┘ └──────────┘ └────────────────┘
        │
┌───────▼──────────────────────┐
│     Linux Servers            │
│  (via SSH with jump hosts)   │
└──────────────────────────────┘
```

---

## ✨ Новые Крутые Фичи

### 1. 🔐 JWT Authentication & RBAC

Полная система аутентификации с role-based access control:

```python
# Роли пользователей
admin     # Полный доступ ко всем операциям
operator  # Может выполнять команды, создавать задачи
viewer    # Только чтение информации

# API endpoints
POST /api/auth/register  # Регистрация (первый юзер = admin)
POST /api/auth/login     # Логин (получить JWT token)
GET  /api/auth/me        # Информация о пользователе
POST /api/auth/logout    # Logout
```

**Пример:**
```bash
# Регистрация
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "securepass123",
    "full_name": "Admin User"
  }'

# Логин
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "securepass123"
  }'

# Использование токена
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/tasks
```

### 2. 📊 System Info Collector

Comprehensive сбор информации о системе:

```python
from apps.tool_executors.linux.system_info import SystemInfoCollector

collector = SystemInfoCollector(ssh_executor)

# Собрать всю информацию
info = await collector.collect_all()

# Информация включает:
# - Hostname, OS, Kernel
# - Uptime
# - CPU count и model
# - Memory (total, used, free, %)
# - Disk usage для всех mountpoints
# - Load average
# - Process count

# Проверка здоровья
health = await collector.check_health()
# Returns: {"status": "healthy|warning|critical", "issues": [], "warnings": []}

# Красивый вывод
summary = collector.format_summary(info)
print(summary)
```

**Output:**
```
╔══════════════════════════════════════════════════════╗
║           System Information Summary                  ║
╠══════════════════════════════════════════════════════╣
║ Hostname:      prod-web-01                            ║
║ OS:            Ubuntu 22.04.3 LTS                     ║
║ Kernel:        5.15.0-91-generic                      ║
║ Uptime:        up 15 days, 3 hours                    ║
╠══════════════════════════════════════════════════════╣
║ CPU:           8 cores - Intel Xeon E5-2680 v4        ║
║ Load Average:  2.34 / 2.12 / 1.98                     ║
║ Processes:     247                                    ║
╠══════════════════════════════════════════════════════╣
║ Memory Total:  32G                                    ║
║ Memory Used:   18G (56.25%)                           ║
║ Memory Free:   14G                                    ║
╠══════════════════════════════════════════════════════╣
║ Disk Usage:                                           ║
║   /          25G/100G (25%)                           ║
║   /var       40G/200G (20%)                           ║
╚══════════════════════════════════════════════════════╝
```

### 3. 📝 Intelligent Log Analyzer

Умный анализ логов с pattern recognition:

```python
from apps.tool_executors.linux.log_analyzer import LogAnalyzer

analyzer = LogAnalyzer(ssh_executor)

# Анализ файла логов
analysis = await analyzer.analyze_file(
    log_file="/var/log/syslog",
    lines=1000,
    filter_errors=True
)

# Результаты:
# - total_entries: количество записей
# - errors: список ошибок
# - warnings: список предупреждений
# - patterns: найденные паттерны с частотой
# - top_errors: топ-10 самых частых ошибок

# Поиск ошибок за последний час
recent_errors = await analyzer.find_errors_in_range(
    log_file="/var/log/syslog",
    minutes_ago=60
)

# Поиск по паттерну с контекстом
results = await analyzer.search_pattern(
    log_file="/var/log/nginx/error.log",
    pattern="connection refused",
    context_lines=3
)

# Логи systemd сервиса
logs = await analyzer.get_service_logs(
    service_name="nginx",
    lines=100
)

# Real-time мониторинг
async for line in analyzer.monitor_log_realtime(
    log_file="/var/log/syslog",
    duration_seconds=30
):
    print(line)
```

### 4. 💬 Multi-Turn Conversations

Интеллектуальные диалоги с контекстом:

```python
from apps/orchestrator/conversation.manager import ConversationManager

conv_manager = ConversationManager(llm_router, db_session)

# Начать сессию
session_id = await conv_manager.start_session(user_id=1)

# Отправить сообщение
response = await conv_manager.process_message(
    session_id=session_id,
    user_message="Проверь статус сервера web-01"
)

# Response включает:
# - response: ответ агента
# - type: "response" или "clarification"
# - intent: распознанный intent
# - requires_input: нужен ли дополнительный ввод
# - suggested_actions: предлагаемые действия

# Получить историю
history = await conv_manager.get_session_history(session_id)

# Создать summary разговора
summary = await conv_manager.summarize_session(session_id)
```

**Пример диалога:**
```
User: Проверь статус сервера
Agent: [Clarification] О каком сервере идет речь? У нас есть web-01, web-02, db-01.

User: web-01
Agent: Понял, проверяю статус web-01...
      [Собирает информацию]
      Сервер web-01 работает нормально:
      - Uptime: 15 days
      - CPU Load: 2.3 (нормально)
      - Memory: 56% (нормально)
      - Disk: 25% (нормально)

      Нашел 3 warning в логах за последний час. Хотите посмотреть?

User: Да, покажи warnings
Agent: [Показывает warnings с контекстом]
```

### 5. 🏥 Proactive Health Monitoring

Автоматический мониторинг с auto-remediation:

```python
from apps.orchestrator.monitoring.health_monitor import ProactiveHealthMonitor

monitor = ProactiveHealthMonitor(
    ssh_executor,
    notification_callback=send_alert  # Optional
)

# Запустить мониторинг
await monitor.start()

# Мониторинг автоматически проверяет:
# - Memory usage (каждые 60 сек)
# - Disk usage (каждые 5 мин)
# - CPU load (каждые 60 сек)
# - Failed services (каждые 2 мин)
# - Recent errors (каждые 3 мин)

# Получить статус
status = monitor.get_status()
# {
#   "running": True,
#   "checks_count": 5,
#   "active_alerts": 2,
#   "critical_alerts": 0,
#   "warning_alerts": 2
# }

# Получить активные alerts
alerts = monitor.get_alerts(severity="critical")

# Auto-remediation автоматически:
# - Чистит memory cache при >95%
# - Удаляет старые логи при disk >95%
# - Перезапускает failed services
```

**Alert пример:**
```
WARNING: Memory usage high: 82.5%
  Threshold: 80.0%
  Auto-remediate: No

CRITICAL: Disk usage critical: 92.1%
  Threshold: 90.0%
  Auto-remediate: Yes
  Action: Cleaning package cache and old logs...
```

### 6. 🎓 Learning Mechanism

Агент учится на успешных операциях:

```python
# Автоматически после каждой успешной задачи:
# 1. Извлекает паттерн
# 2. Сохраняет в Knowledge Base
# 3. Использует для будущих похожих задач

# Knowledge Base хранит:
# - category: тип операции
# - pattern: паттерн задачи
# - solution: успешное решение
# - confidence_score: уверенность (0-1)
# - success_count: количество успешных использований
# - failure_count: количество неудач

# При планировании новой задачи:
similar_patterns = await knowledge_repo.search_patterns(
    search_text="deploy nginx",
    limit=5
)

# Агент использует найденные паттерны для оптимизации плана
```

### 7. ⚡ Error Recovery & Rollback

Автоматический retry и rollback:

```python
# Enhanced Orchestrator V2 автоматически:

# 1. Retry при сбоях (до 3 попыток)
#    - Exponential backoff (2s, 4s, 8s)
#    - Detailed error logging

# 2. Rollback при критических ошибках
#    - Checkpoints перед каждым шагом
#    - Rollback actions для reversible операций
#    - Automatic cleanup при failures

# 3. State persistence
#    - Все шаги сохраняются в БД
#    - Recovery после перезапуска
#    - Audit trail для compliance

# Пример workflow:
# Step 1: Deploy new version ✅
# Step 2: Restart service ✅
# Step 3: Health check ❌ FAILED
# → Auto-rollback: Restore previous version
# → Restart service with old version
# → Cleanup temporary files
```

---

## 🚀 Быстрый Старт

### Установка

```bash
# 1. Clone repository
git clone https://github.com/yourorg/devops-llm-agent.git
cd devops-llm-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp env.example .env
# Отредактируйте .env:
# - DATABASE_URL
# - REDIS_URL
# - SECRET_KEY
# - GEMINI_API_KEY (опционально)

# 5. Run migrations
alembic upgrade head

# 6. Start services
# Terminal 1: Redis
redis-server

# Terminal 2: PostgreSQL
# (или используйте существующий)

# Terminal 3: API Server
cd apps/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Первый Запуск

```bash
# 1. Зарегистрируйте первого пользователя (будет admin)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "your-secure-password"
  }'

# 2. Получите JWT token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-secure-password"
  }' | jq -r '.access_token')

# 3. Создайте задачу
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Проверь статус nginx на prod-web-01",
    "environment_profile": "prod-vm",
    "context": {}
  }'
```

---

## 📚 Использование

### 1. Проверка Здоровья Сервера

```python
# API Request
POST /api/tasks
{
  "task": "Проверь здоровье сервера web-01 и сообщи о проблемах",
  "environment_profile": "prod-vm"
}

# Агент автоматически:
# 1. Планирует задачу (System Info Collection)
# 2. Подключается по SSH
# 3. Собирает метрики (CPU, Memory, Disk, Load)
# 4. Анализирует результаты
# 5. Генерирует отчет с рекомендациями
```

### 2. Анализ Логов

```python
POST /api/tasks
{
  "task": "Найди ошибки в логах nginx за последний час",
  "environment_profile": "prod-vm"
}

# Агент:
# 1. Читает логи nginx
# 2. Парсит и классифицирует записи
# 3. Находит ошибки и warnings
# 4. Группирует по паттернам
# 5. Выдает топ-10 проблем с контекстом
```

### 3. Troubleshooting

```python
POST /api/tasks
{
  "task": "Сервис app.service не запускается, найди причину",
  "environment_profile": "prod-vm"
}

# Агент:
# 1. Проверяет статус сервиса
# 2. Читает логи systemd
# 3. Анализирует ошибки
# 4. Проверяет dependencies
# 5. Предлагает решение
# 6. (Опционально) автоматически исправляет
```

### 4. Conversation Mode

```python
# Начать диалог
POST /api/conversation/start
Response: {"session_id": "uuid"}

# Отправить сообщение
POST /api/conversation/{session_id}/message
{
  "message": "Какие серверы сейчас перегружены?"
}

# Агент отвечает с контекстом
# Можно задавать follow-up вопросы
# Агент помнит контекст разговора
```

---

## 🎯 Примеры Команд

```bash
# Простые команды
"Покажи uptime сервера web-01"
"Сколько места на диске /"
"Какая версия nginx установлена"

# Анализ
"Найди ошибки в syslog за последние 30 минут"
"Почему такая высокая загрузка CPU?"
"Проанализируй память, что ее жрет"

# Операции
"Перезапусти nginx"
"Почисти старые логи старше 30 дней"
"Обнови пакеты безопасности"

# Troubleshooting
"Почему не запускается postgresql"
"Найди причину 500 ошибок в nginx"
"Проверь почему медленный ответ API"

# Proactive
"Настрой автоматический мониторинг"
"Уведоми меня если диск заполнится >85%"
"Автоматически перезапускай упавшие сервисы"
```

---

## 🔧 Конфигурация

### Environment Profiles

```yaml
# environments/prod-vm.yaml
id: prod-vm
display_name: Production VM Fleet
type: vm

networking:
  bastion: bastion.prod.example.com

auth:
  ssh_cert_role: prod-ops
  vault_role: prod/vm/operator

ssh:
  host: prod-web-01.example.com
  port: 22
  username: deploy
  key_file: ~/.ssh/prod_deploy_key
  jump_host:
    host: bastion.prod.example.com
    username: bastion-user
    key_file: ~/.ssh/bastion_key

policies:
  risk_level: high
  require_approval: true
  change_ticket_required: true

defaults:
  working_directory: /srv/app
  retries: 3
  timeout: 300

runbooks:
  - docs/runbooks/prod/deployment.md
  - docs/runbooks/prod/troubleshooting.md
```

### LLM Providers

```env
# Gemini (Google)
ENABLE_GEMINI_PROVIDER=true
GEMINI_API_KEY=your-api-key

# Ollama (Local)
ENABLE_OLLAMA_PROVIDER=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Local (Testing)
ENABLE_LOCAL_PROVIDER=true
```

---

## 📊 Метрики и Observability

### Prometheus Metrics

```
# LLM Metrics
llm_requests_total{provider="gemini",model="gemini-1.5-flash"}
llm_request_duration_seconds{provider="gemini"}
llm_tokens_total{provider="gemini",type="prompt"}

# Task Metrics
task_executions_total{status="completed"}
task_duration_seconds{environment="prod"}

# Cache Metrics
cache_hits_total
cache_misses_total

# Health Metrics
health_check_status{check="memory_usage",status="healthy"}
```

### Structured Logging

```json
{
  "timestamp": "2025-10-22T12:00:00Z",
  "level": "INFO",
  "component": "orchestrator",
  "action": "task_completed",
  "task_id": "uuid",
  "user_id": 1,
  "duration": 5.23,
  "metadata": {
    "steps": 3,
    "success": true
  }
}
```

### Audit Trail

Все действия логируются в `audit_logs`:

```sql
SELECT * FROM audit_logs
WHERE user_id = 1
  AND action = 'task_executed'
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

---

## 🛡️ Безопасность

### Authentication
- JWT tokens с expiration
- Password hashing (bcrypt)
- Role-based access control
- API key support

### Authorization
- Command policies (blocked, approval-required, allowed)
- Environment-specific restrictions
- Audit logging всех действий
- Approval gates для high-risk операций

### SSH Security
- Key-based authentication (рекомендуется)
- Jump host/bastion support
- SSH config integration
- Secure password handling

---

## 📈 Performance

### Optimizations
- Connection pooling для SSH
- LLM response caching (Redis)
- Database query optimization
- Async everywhere (asyncio)

### Scalability
- Stateless API design
- Horizontal scaling ready
- Background task processing
- Rate limiting

---

## 🐛 Troubleshooting

### База данных не подключается
```bash
# Проверьте DATABASE_URL в .env
# Создайте БД если нужно
createdb devops_agent

# Запустите миграции
alembic upgrade head
```

### LLM не отвечает
```bash
# Проверьте провайдеры
curl http://localhost:8000/api/health

# Проверьте Ollama (если используете)
curl http://localhost:11434/api/tags

# Включите Local Provider для тестирования
ENABLE_LOCAL_PROVIDER=true
```

### SSH подключение не работает
```bash
# Проверьте SSH конфигурацию
ssh -v user@host

# Проверьте ключи
ls -la ~/.ssh/

# Проверьте environment profile
curl http://localhost:8000/api/environments/prod-vm
```

---

## 🚧 Roadmap

### v1.1 (Следующий релиз)
- [ ] Web UI improvements (WebSocket, real-time)
- [ ] CLI tool с interactive mode
- [ ] Grafana dashboards
- [ ] Multi-server orchestration
- [ ] Runbook integration

### v1.2
- [ ] Distributed execution
- [ ] Advanced scheduling
- [ ] Canary deployments
- [ ] A/B testing support

### v2.0
- [ ] Vector embeddings для semantic search
- [ ] Advanced pattern recognition
- [ ] Predictive analytics
- [ ] Natural language → IaC generation

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

---

## 📝 License

MIT License - см. LICENSE file

---

## 👥 Authors

- AI Development Team
- Generated with Claude Code

---

## 📞 Support

- Issues: https://github.com/yourorg/devops-llm-agent/issues
- Docs: https://docs.yourorg.com/devops-llm-agent
- Email: support@yourorg.com

---

**Сделайте DevOps операции умнее с AI!** 🚀
