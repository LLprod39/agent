# Kubernetes Rolling Update

1. Сверьтесь с changelog сервиса и убедитесь в готовности зависимостей.
2. Запустите сухой прогон: `kubectl rollout status deployment/<name> --dry-run=client`.
3. Примените манифесты: `kubectl apply -f deploy/`. Используйте контекст из профиля окружения.
4. Отследите `kubectl rollout status` до завершения и соберите метрики ошибок/латентности.
5. При отклонениях выполните `kubectl rollout undo deployment/<name>` и создайте инцидент.
