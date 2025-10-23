# 🌐 Руководство по Запуску Web UI

Полная инструкция по запуску и использованию веб-интерфейса DevOps Agent.

## 🎯 Что Включено

### ✅ Готовые Компоненты

1. **📊 Dashboard** - главная панель с метриками и задачами
2. **📋 Task Management** - управление задачами с фильтрацией и пагинацией
3. **💻 Interactive Terminal** - браузерный терминал для выполнения команд
4. **🖥️ Servers Management** - управление SSH серверами и тестирование подключений
5. **🤖 Providers Management** - настройка LLM провайдеров (Gemini, Ollama, Local)
6. **🔐 Authentication** - система входа/регистрации с JWT
7. **🎨 App Layout** - красивый интерфейс с навигацией

### 🎨 Дизайн

- Modern UI с Tailwind CSS
- Responsive дизайн для всех устройств
- Dark mode ready
- Красивые анимации и переходы
- Профессиональные цветовые схемы

## 🚀 Быстрый Запуск

### Шаг 1: Установка Зависимостей

```bash
cd apps/ui
npm install
```

### Шаг 2: Настройка Environment

Создайте файл `.env.local`:

```env
# API Backend URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# App Config
NEXT_PUBLIC_APP_NAME=DevOps Agent
NEXT_PUBLIC_APP_VERSION=1.0.0-beta
```

### Шаг 3: Запуск API Backend

В отдельном терминале:

```bash
cd /home/user/agent
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 4: Запуск Web UI

```bash
cd apps/ui
npm run dev
```

### Шаг 5: Открыть в Браузере

Откройте [http://localhost:3000](http://localhost:3000)

## 📱 Навигация по UI

### 1. Dashboard (`/dashboard`)

**Что показывает:**
- Real-time метрики системы (CPU, Memory, Disk)
- Статус провайдеров LLM
- Последние 10 задач
- Quick actions кнопки

**Как использовать:**
1. Смотрите общий статус системы
2. Проверяйте здоровье сервисов
3. Быстро создавайте новые задачи
4. Переходите к терминалу или настройкам

### 2. Задачи (`/tasks`)

**Что показывает:**
- Список всех задач
- Фильтры по статусу и окружению
- Поиск по описанию
- Пагинация

**Как использовать:**
1. Нажмите "+ Новая Задача" для создания
2. Введите задачу на естественном языке:
   - "Проверь использование CPU"
   - "Собери метрики памяти"
   - "Проверь статус nginx"
3. Выберите окружение (dev/staging/prod)
4. Нажмите "Выполнить"
5. Смотрите live обновления статуса

### 3. Терминал (`/terminal`)

**Что показывает:**
- Интерактивный терминал в браузере
- История команд
- Цветной вывод

**Как использовать:**
1. Введите команду в prompt
2. Нажмите Enter
3. Используйте ↑↓ для навигации по истории
4. Специальные команды:
   - `help` - показать помощь
   - `clear` - очистить экран
   - `history` - показать историю

### 4. Серверы (`/servers`)

**Что показывает:**
- Список всех SSH серверов
- Статус подключений (online/offline/unknown)
- Конфигурация каждого сервера

**Как использовать:**
1. **Добавить сервер:**
   - Нажмите "Добавить Сервер"
   - Заполните форму:
     - Название: "Production Web Server"
     - Host: "prod-web-01.example.com"
     - Port: 22
     - Username: "admin"
     - Auth Type: SSH Key или Password
     - Key Path: "~/.ssh/id_rsa"
     - Environment: production
   - Нажмите "Добавить"

2. **Тестировать подключение:**
   - Нажмите кнопку "Тест" у сервера
   - Смотрите результат (online/offline)

3. **Редактировать:**
   - Нажмите "Изменить"
   - Обновите данные
   - Сохраните

4. **Удалить:**
   - Нажмите "Удалить"
   - Подтвердите действие

### 5. Провайдеры (`/providers`)

**Что показывает:**
- Все LLM провайдеры (Gemini, Ollama, Local)
- Статус каждого провайдера
- Конфигурация и API ключи

**Как использовать:**

**Gemini Provider:**
1. Нажмите "Настроить" у Gemini
2. Введите API Key от Google AI Studio
3. Выберите модель (gemini-2.5-flash, gemini-1.5-flash)
4. Настройте Temperature (0.0-1.0)
5. Сохраните
6. Нажмите "Тест" для проверки
7. Включите провайдер (toggle switch)

**Ollama Provider:**
1. Установите Ollama локально: `curl https://ollama.ai/install.sh | sh`
2. Запустите: `ollama serve`
3. Скачайте модель: `ollama pull llama3`
4. В UI нажмите "Настроить"
5. Укажите Base URL: `http://localhost:11434`
6. Выберите модель: `llama3`
7. Сохраните и включите

**Local Provider:**
- Всегда включен
- Работает без настройки
- Дает простые планы без AI

### 6. Настройки (`/settings`)

**Общие настройки:**
- API ключи
- Уведомления
- Темы (light/dark)
- Язык интерфейса

## 🎨 Скриншоты Возможностей

### Dashboard
```
┌─────────────────────────────────────────────┐
│  📊 Dashboard                               │
├─────────────────────────────────────────────┤
│  Status: HEALTHY     CPU: 45%    Mem: 67%  │
│                                              │
│  Recent Tasks:                               │
│  ✓ Check CPU metrics      2 min ago         │
│  ⟳ Deploy to staging     Running...         │
│  ✗ Backup database        Failed            │
│                                              │
│  [+ New Task]  [Terminal]  [Settings]       │
└─────────────────────────────────────────────┘
```

### Servers Management
```
┌─────────────────────────────────────────────┐
│  🖥️  Servers                 [+ Add Server] │
├─────────────────────────────────────────────┤
│  Stats: Total: 3  Online: 2  Offline: 1     │
├─────────────────────────────────────────────┤
│  Development VM                              │
│  ✓ ONLINE    dev-vm-01.local:22             │
│  [Test] [Edit] [Delete]                     │
│─────────────────────────────────────────────│
│  Production Web                              │
│  ✗ OFFLINE   prod-web.com:22                │
│  [Test] [Edit] [Delete]                     │
└─────────────────────────────────────────────┘
```

### Providers Management
```
┌─────────────────────────────────────────────┐
│  🤖 LLM Providers                            │
├─────────────────────────────────────────────┤
│  Gemini                                      │
│  ✓ HEALTHY   Priority: 100   [ON]          │
│  Model: gemini-2.5-flash                    │
│  API Key: AIza••••••••••••  [👁️]           │
│  [Test] [Configure]                         │
│─────────────────────────────────────────────│
│  Ollama                                      │
│  ? UNKNOWN   Priority: 50    [OFF]         │
│  Model: llama3                               │
│  URL: http://localhost:11434                │
│  [Test] [Configure]                         │
└─────────────────────────────────────────────┘
```

## 🔥 Использование

### Сценарий 1: Проверка Метрик Сервера

1. Откройте Dashboard
2. Нажмите "+ Новая Задача"
3. Введите: "Собери метрики CPU и памяти с prod-web-01"
4. Выберите окружение: "production"
5. Нажмите "Выполнить"
6. Смотрите live обновления
7. Получите результат

### Сценарий 2: Добавление Нового Сервера

1. Перейдите в "Серверы"
2. Нажмите "Добавить Сервер"
3. Заполните:
   - Название: "Staging DB"
   - Host: "staging-db.internal"
   - Port: 22
   - Username: "postgres"
   - Auth: SSH Key
   - Key: "~/.ssh/staging_key"
   - Environment: staging
4. Нажмите "Добавить"
5. Нажмите "Тест" для проверки
6. Сервер готов к использованию!

### Сценарий 3: Настройка Gemini

1. Получите API ключ: https://aistudio.google.com/app/apikey
2. Перейдите в "Провайдеры"
3. Найдите "Gemini"
4. Нажмите "Настроить"
5. Вставьте API ключ
6. Выберите модель: "gemini-2.5-flash"
7. Сохраните
8. Нажмите "Тест" - должно показать ✓ HEALTHY
9. Включите провайдер (toggle ON)
10. Теперь задачи будут использовать Gemini!

## 🎓 Советы и Трюки

### Производительность

- Используйте WebSocket для real-time обновлений
- Local provider работает мгновенно
- Gemini быстрее чем Ollama для сложных задач

### Безопасность

- API ключи маскируются в UI
- JWT токены хранятся в localStorage
- Первый пользователь автоматически становится admin

### Workflow

1. **Утром:** Проверьте Dashboard для общего статуса
2. **Работа:** Используйте Terminal для быстрых команд
3. **Задачи:** Создавайте задачи для сложных операций
4. **Мониторинг:** Смотрите live обновления в Task Detail
5. **Настройка:** Используйте Servers/Providers для конфигурации

## 🐛 Troubleshooting

### UI не подключается к API

```bash
# Проверьте что API запущен
curl http://localhost:8000/health

# Проверьте NEXT_PUBLIC_API_URL в .env.local
echo $NEXT_PUBLIC_API_URL
```

### WebSocket не работает

```bash
# Проверьте WebSocket endpoint
# Должен быть ws:// а не http://
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Не могу войти

```bash
# Создайте первого пользователя через API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@localhost",
    "password": "admin123"
  }'
```

### Gemini не работает

1. Проверьте API ключ в Providers
2. Убедитесь что API включен в Google Cloud Console
3. Нажмите "Тест" для детальной ошибки
4. См. SETUP_GUIDE.md для подробностей

## 📚 Дополнительно

- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Metrics:** http://localhost:8000/metrics

## 🚀 Production Deployment

```bash
# Build для production
cd apps/ui
npm run build

# Запуск
npm start

# Или с PM2
pm2 start npm --name "devops-ui" -- start

# Или с Docker
docker build -t devops-agent-ui .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://your-api:8000 \
  devops-agent-ui
```

---

**Готово! Теперь у вас полноценный Web UI для управления DevOps агентом! 🎉**

Есть вопросы? Смотрите README.md в apps/ui/ или создайте issue.
