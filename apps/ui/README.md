# 🖥️ DevOps Agent Web UI

Современный веб-интерфейс для управления DevOps агентом на базе Next.js 14 и React 18.

## ✨ Возможности

### 📊 Dashboard
- Real-time мониторинг системных метрик (CPU, Memory, Disk)
- Список последних задач
- Quick actions для быстрого доступа
- WebSocket обновления в реальном времени

### 📋 Управление Задачами
- Создание новых задач на естественном языке
- Просмотр истории задач с фильтрацией
- Детальная информация о каждой задаче
- Live обновления статуса выполнения
- Approval workflow для критических операций

### 💻 Интерактивный Терминал
- Браузерный терминал для выполнения команд
- История команд с навигацией стрелками
- Цветной вывод (input/output/error/system)
- Специальные команды (help, clear, history)

### 🖥️ Управление Серверами
- Добавление/редактирование SSH серверов
- Тестирование подключений
- Поддержка bastion hosts
- SSH keys и password auth
- Environment profiles (dev/staging/prod)
- Статусы серверов (online/offline/testing)

### 🤖 Управление LLM Провайдерами
- Настройка Gemini, Ollama, Local провайдеров
- Управление API ключами с маскированием
- Тестирование подключений к провайдерам
- Настройка приоритетов и параметров
- Включение/выключение провайдеров

### 🔐 Аутентификация
- JWT аутентификация
- Login/Logout формы
- Регистрация пользователей
- Первый пользователь = admin

## 🚀 Быстрый Старт

### Установка зависимостей

```bash
cd apps/ui
npm install
```

### Запуск в режиме разработки

```bash
npm run dev
```

Откройте [http://localhost:3000](http://localhost:3000) в браузере.

### Production Build

```bash
npm run build
npm start
```

## 📁 Структура Компонентов

```
src/
├── components/
│   ├── AppLayout.tsx           # Главный layout с навигацией
│   ├── Dashboard.tsx           # Dashboard с метриками
│   ├── TaskList.tsx            # Список задач
│   ├── TaskDetail.tsx          # Детали задачи
│   ├── Terminal.tsx            # Интерактивный терминал
│   ├── ServersManagement.tsx   # Управление серверами
│   ├── ProvidersManagement.tsx # Управление LLM провайдерами
│   ├── LoginForm.tsx           # Форма входа
│   └── RegisterForm.tsx        # Форма регистрации
├── hooks/
│   └── useWebSocket.ts         # WebSocket hook
└── lib/
    └── api.ts                  # API client
```

## 🔧 Конфигурация

### Environment Variables

Создайте файл `.env.local`:

```env
# API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### API Configuration

API клиент настроен в `src/lib/api.ts`:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

## 📖 Использование Компонентов

### Dashboard

```tsx
import { Dashboard } from '@/components/Dashboard';

export default function DashboardPage() {
  return <Dashboard />;
}
```

### Servers Management

```tsx
import { ServersManagement } from '@/components/ServersManagement';

export default function ServersPage() {
  return <ServersManagement />;
}
```

### Providers Management

```tsx
import { ProvidersManagement } from '@/components/ProvidersManagement';

export default function ProvidersPage() {
  return <ProvidersManagement />;
}
```

### App Layout

```tsx
import { AppLayout } from '@/components/AppLayout';

export default function RootLayout({ children }) {
  return (
    <AppLayout>
      {children}
    </AppLayout>
  );
}
```

## 🎨 Стилизация

Используется **Tailwind CSS** для стилизации компонентов.

### Цветовая Схема

- **Primary**: Blue (bg-blue-600, text-blue-600)
- **Success**: Green (bg-green-600, text-green-600)
- **Warning**: Yellow (bg-yellow-600, text-yellow-600)
- **Danger**: Red (bg-red-600, text-red-600)
- **Dark**: Gray (bg-gray-900, text-gray-900)

### Компоненты UI

Все компоненты используют единый стиль:
- Rounded corners: `rounded-lg`
- Shadows: `shadow`, `shadow-lg`
- Transitions: `transition-colors`, `transition-all`
- Hover effects: `hover:bg-*-700`

## 🔌 API Integration

### Endpoints

```typescript
// Tasks
POST   /api/v1/tasks          - Создать задачу
GET    /api/v1/tasks/:id      - Получить задачу
GET    /api/v1/tasks          - Список задач
POST   /api/v1/tasks/:id/approve - Подтвердить задачу

// Health
GET    /health                - Health check
GET    /api/v1/health/:env    - Environment health

// Auth
POST   /api/v1/auth/register  - Регистрация
POST   /api/v1/auth/login     - Вход
POST   /api/v1/auth/logout    - Выход
GET    /api/v1/auth/me        - Текущий пользователь
```

### WebSocket Events

```typescript
{
  type: 'task_update',
  task_id: 'task-123',
  task: { /* task data */ }
}

{
  type: 'health_update',
  metrics: { /* health metrics */ }
}
```

## 🧪 Тестирование

### Компонентов

```bash
npm test
```

### E2E тесты

```bash
npm run test:e2e
```

## 📦 Сборка для Production

```bash
npm run build
npm start
```

Или с Docker:

```bash
docker build -t devops-agent-ui .
docker run -p 3000:3000 devops-agent-ui
```

## 🐛 Отладка

### Проблемы с API

1. Проверьте что API сервер запущен на `http://localhost:8000`
2. Проверьте CORS настройки в API
3. Откройте DevTools → Network для просмотра запросов

### Проблемы с WebSocket

1. Проверьте WebSocket URL в `.env.local`
2. Убедитесь что сервер поддерживает WebSocket
3. Проверьте firewall и proxy настройки

## 📚 Документация

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/docs)

## 🤝 Вклад

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License

---

**Made with ❤️ for DevOps Engineers**
