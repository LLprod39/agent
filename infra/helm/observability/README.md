# Observability Stack for DevOps LLM Agent

This directory contains the Helm charts and configurations for the observability stack of the DevOps LLM Agent.

## Components

### 1. Prometheus
- **Chart**: `prometheus-community/prometheus`
- **Configuration**: `prometheus-values.yaml`
- **Features**:
  - Metrics collection from all agent components
  - Custom recording rules for pre-computed metrics
  - Alerting rules for proactive monitoring
  - Service discovery for dynamic targets

### 2. Grafana
- **Chart**: `grafana/grafana`
- **Configuration**: `grafana-dashboards.yaml`
- **Features**:
  - Pre-configured dashboards for agent monitoring
  - LLM metrics visualization
  - Task performance monitoring
  - Security metrics tracking
  - System health overview

### 3. Alertmanager
- **Chart**: `prometheus-community/alertmanager`
- **Configuration**: `alertmanager-config.yaml`
- **Features**:
  - Multi-channel alert routing
  - Email, Slack, and PagerDuty integrations
  - Alert grouping and inhibition
  - Silence rules for maintenance windows

## Installation

### Prerequisites
- Kubernetes cluster (1.20+)
- Helm 3.0+
- kubectl configured

### 1. Add Helm Repositories
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

### 2. Create Namespace
```bash
kubectl create namespace monitoring
```

### 3. Install Prometheus
```bash
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --values prometheus-values.yaml
```

### 4. Install Grafana
```bash
helm install grafana grafana/grafana \
  --namespace monitoring \
  --values grafana-dashboards.yaml
```

### 5. Install Alertmanager
```bash
helm install alertmanager prometheus-community/alertmanager \
  --namespace monitoring \
  --values alertmanager-config.yaml
```

## Configuration

### Environment Variables
Set the following environment variables for your environment:

```bash
# SMTP Configuration
export SMTP_HOST="smtp.company.com"
export SMTP_PORT="587"
export SMTP_USERNAME="alerts@company.com"
export SMTP_PASSWORD="password"

# Slack Configuration
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# PagerDuty Configuration
export PAGERDUTY_ROUTING_KEY="YOUR_PAGERDUTY_ROUTING_KEY"
```

### Customization
1. **Prometheus**: Modify `prometheus-values.yaml` for:
   - Resource limits
   - Storage configuration
   - Retention policies
   - Additional scrape configs

2. **Grafana**: Modify `grafana-dashboards.yaml` for:
   - Dashboard layouts
   - Panel configurations
   - Alert thresholds
   - Data source settings

3. **Alertmanager**: Modify `alertmanager-config.yaml` for:
   - Notification channels
   - Routing rules
   - Inhibition rules
   - Silence rules

## Monitoring

### Key Metrics

#### LLM Metrics
- `llm_requests_total`: Total LLM requests by provider and model
- `llm_request_duration_seconds`: Request duration histogram
- `llm_tokens_total`: Token usage by type
- `llm_request_rate`: Requests per second

#### Task Metrics
- `tasks_total`: Total tasks by status and environment
- `task_duration_seconds`: Task duration histogram
- `active_tasks`: Number of active tasks
- `task_completion_rate`: Task completion percentage

#### Security Metrics
- `security_violations_total`: Security violations by type
- `approvals_total`: Approval requests by status
- `security_violation_rate`: Violation rate over time
- `approval_rate`: Approval rate over time

#### System Metrics
- `system_memory_usage_bytes`: Memory usage
- `system_cpu_usage_percent`: CPU usage
- `up`: Service availability

### Dashboards

#### 1. Overview Dashboard
- System health status
- Active tasks count
- Task completion rate
- LLM request rate
- Task duration trends

#### 2. LLM Metrics Dashboard
- Request rate by provider
- Request duration percentiles
- Status distribution
- Token usage trends
- Duration histograms

#### 3. Task Metrics Dashboard
- Task rate by status
- Duration percentiles
- Active tasks by environment
- Completion rate trends
- Duration histograms

#### 4. Security Metrics Dashboard
- Violations by type
- Approval rate trends
- Environment distribution
- Status distribution
- Violation rate trends

## Alerting

### Alert Rules

#### Critical Alerts
- **LLMProviderDown**: LLM provider unavailable
- **SecurityViolationDetected**: Security violation detected
- **HighMemoryUsage**: Memory usage > 8GB
- **HighCPUUsage**: CPU usage > 80%

#### Warning Alerts
- **LLMRequestLatencyHigh**: Request latency > 10s
- **LLMRequestFailureRateHigh**: Failure rate > 10%
- **TaskCompletionRateLow**: Completion rate < 80%
- **TaskDurationHigh**: Task duration > 5 minutes
- **ActiveTasksHigh**: Active tasks > 100
- **ApprovalRateLow**: Approval rate < 90%

### Notification Channels
- **Email**: Primary notification channel
- **Slack**: Real-time notifications
- **PagerDuty**: Critical alert escalation

## Troubleshooting

### Common Issues

#### 1. Prometheus Not Scraping Metrics
```bash
# Check service discovery
kubectl get servicemonitor -n monitoring

# Check target status
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Open http://localhost:9090/targets
```

#### 2. Grafana Dashboards Not Loading
```bash
# Check Grafana logs
kubectl logs -n monitoring deployment/grafana

# Check data source configuration
kubectl port-forward -n monitoring svc/grafana 3000:80
# Open http://localhost:3000
```

#### 3. Alerts Not Firing
```bash
# Check alert rules
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Open http://localhost:9090/alerts

# Check Alertmanager configuration
kubectl port-forward -n monitoring svc/alertmanager 9093:80
# Open http://localhost:9093
```

### Logs
```bash
# Prometheus logs
kubectl logs -n monitoring deployment/prometheus-server

# Grafana logs
kubectl logs -n monitoring deployment/grafana

# Alertmanager logs
kubectl logs -n monitoring deployment/alertmanager
```

## Maintenance

### Backup
```bash
# Backup Prometheus data
kubectl exec -n monitoring deployment/prometheus-server -- tar czf /tmp/backup.tar.gz /prometheus

# Backup Grafana dashboards
kubectl get configmap -n monitoring devops-llm-agent-dashboards -o yaml > dashboards-backup.yaml
```

### Updates
```bash
# Update Prometheus
helm upgrade prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --values prometheus-values.yaml

# Update Grafana
helm upgrade grafana grafana/grafana \
  --namespace monitoring \
  --values grafana-dashboards.yaml
```

### Scaling
```bash
# Scale Prometheus
kubectl scale -n monitoring deployment/prometheus-server --replicas=2

# Scale Grafana
kubectl scale -n monitoring deployment/grafana --replicas=2
```

## Security

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: observability-netpol
  namespace: monitoring
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: devops-llm-agent
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: devops-llm-agent
```

### RBAC
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: observability-reader
rules:
- apiGroups: [""]
  resources: ["nodes", "services", "endpoints", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
```

## Performance Tuning

### Prometheus
- Increase memory limits for high-cardinality metrics
- Adjust retention policies based on storage capacity
- Use recording rules for expensive queries
- Configure federation for multi-cluster setups

### Grafana
- Enable query caching
- Use data source proxies
- Optimize dashboard queries
- Configure alerting thresholds

### Alertmanager
- Tune grouping intervals
- Configure inhibition rules
- Use silence rules for maintenance
- Monitor alert volume

## Integration

### External Systems
- **SIEM**: Export alerts to security information systems
- **CMDB**: Update configuration management databases
- **Ticketing**: Create tickets for critical alerts
- **ChatOps**: Integrate with team communication tools

### APIs
- **Prometheus API**: Query metrics programmatically
- **Grafana API**: Manage dashboards and alerts
- **Alertmanager API**: Manage silences and configurations

## Best Practices

1. **Monitoring**: Monitor the monitoring system itself
2. **Alerting**: Keep alert rules simple and actionable
3. **Dashboards**: Design for different user personas
4. **Documentation**: Document alert runbooks and procedures
5. **Testing**: Regularly test alerting and notification channels
6. **Capacity**: Plan for growth and scale accordingly
7. **Security**: Implement proper access controls and encryption
8. **Backup**: Regular backups of configurations and data
