# NGINX Deploy Runbook

1. Подготовьте артефакты: проверьте теги образов и changelog.
2. Выполните `make validate-environments` и подтвердите, что профиль цели актуален.
3. Выполните rollout через агента: `agent plan --env prod-k8s --task "deploy nginx"`.
4. Наблюдайте метрики и логи в течение 15 минут. При аномалиях выполните `kubectl rollout undo`.
