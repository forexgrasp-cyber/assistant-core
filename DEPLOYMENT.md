# Retention Analytics Platform - Production Deployment Guide

## Overview

This guide covers deploying the Retention Analytics Platform to production using Docker Compose.

## Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Domain name with SSL certificates
- PostgreSQL 15+ (managed or self-hosted)
- Redis 7+ (managed or self-hosted)
- 4GB+ RAM, 2+ vCPUs recommended

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your production values
```

Required variables:
- `POSTGRES_PASSWORD` - Strong database password
- `REDIS_PASSWORD` - Strong Redis password
- `SECRET_KEY` - 32+ character random string
- `JWT_SECRET_KEY` - Different 32+ character random string
- `GRAFANA_PASSWORD` - Grafana admin password

### 2. SSL Certificates

Place your SSL certificates in `nginx/ssl/`:
```
nginx/ssl/
├── cert.pem    # Full chain certificate
└── key.pem     # Private key
```

### 3. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Verify

```bash
# Check all services are healthy
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Health checks
curl https://yourdomain.com/health
curl https://api.yourdomain.com/health
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80/443 | Reverse proxy, SSL termination |
| web-customer | 3000 | Customer portal (Next.js) |
| web-dev | 3000 | Developer portal (Next.js) |
| api | 8000 | FastAPI backend |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache/queue |
| prometheus | 9090 | Metrics collection |
| grafana | 3001 | Dashboards & alerting |
| loki | 3100 | Log aggregation |
| promtail | 9080 | Log shipper |

## Monitoring

### Grafana Dashboards

Access: `https://yourdomain.com:3001` (or configure subdomain)

Default credentials:
- User: `admin` (from `GRAFANA_USER`)
- Password: from `GRAFANA_PASSWORD`

Pre-configured dashboards:
- System Overview (CPU, Memory, Disk, Network)
- API Performance (latency, error rate, throughput)
- Business Metrics (workflows, executions, users)
- Database Performance (connections, queries, cache hit rate)

### Prometheus Metrics

Access: `https://yourdomain.com:9090` (internal only)

Key metrics:
- `http_requests_total` - Request count by endpoint/status
- `http_request_duration_seconds` - Latency percentiles
- `workflow_executions_total` - Execution count
- `database_connections_active` - Active DB connections
- `redis_memory_used_bytes` - Redis memory usage

### Logs (Loki + Grafana)

Logs are automatically collected from all containers and available in Grafana's "Explore" section.

Query examples:
- `{job="api"} |= "error"` - API errors
- `{job="nginx"} |~ " 5[0-9]{2} "` - 5xx responses
- `{job="docker"} | json | container_name="api"` - API container logs

## Database Migrations

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Create new migration
docker compose -f docker-compose.prod.yml exec api alembic revision --autogenerate -m "description"
```

## Backup & Restore

### PostgreSQL Backup

```bash
# Backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U retention retention > backup_$(date +%Y%m%d).sql

# Restore
docker compose -f docker-compose.prod.yml exec -T postgres psql -U retention retention < backup_20240101.sql
```

### Redis Backup

```bash
# Backup (RDB)
docker compose -f docker-compose.prod.yml exec redis redis-cli --rdb /data/dump.rdb
docker cp retention-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

## Scaling

### Horizontal Scaling (API)

```yaml
# In docker-compose.prod.yml
api:
  deploy:
    replicas: 3
```

Or with Docker Swarm/Kubernetes.

### Database Scaling

- Use managed PostgreSQL (AWS RDS, Google Cloud SQL, Azure Database)
- Enable read replicas for read-heavy workloads
- Configure connection pooling (PgBouncer)

## Security Hardening

### Network
- All services communicate via internal Docker network
- Only nginx exposes ports 80/443
- Database/Redis not exposed externally

### Application
- Security headers via nginx and FastAPI middleware
- Rate limiting on API endpoints
- JWT token expiration (60 min default)
- CORS restricted to configured origins
- Trusted host middleware in production

### Secrets
- Never commit `.env` to version control
- Use Docker secrets or external secret manager (HashiCorp Vault, AWS Secrets Manager)
- Rotate secrets regularly

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs <service-name>

# Check resource usage
docker stats
```

### Database Connection Issues

```bash
# Test connectivity
docker compose -f docker-compose.prod.yml exec api pg_isready -h postgres -U retention

# Check PostgreSQL logs
docker compose -f docker-compose.prod.yml logs postgres
```

### High Memory Usage

```bash
# Check memory limits
docker compose -f docker-compose.prod.yml config | grep -A5 "deploy:"

# Adjust limits in docker-compose.prod.yml
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) handles:

1. **Lint & Test** - TypeScript, Python, ESLint, Ruff, pytest
2. **Build** - Multi-arch Docker images pushed to GHCR
3. **Security Scan** - Trivy vulnerability scan, npm audit, pip-audit
4. **Deploy** - Staging (develop branch), Production (main branch)

Required secrets in GitHub:
- `GITHUB_TOKEN` (automatic)
- Environment-specific secrets for deployment

## Rollback

```bash
# Quick rollback to previous image
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate

# Or specify image tag
docker tag ghcr.io/yourorg/retention-analytics-platform/api:sha-abc123 ghcr.io/yourorg/retention-analytics-platform/api:latest
docker compose -f docker-compose.prod.yml up -d api
```

## Support

For issues:
1. Check Grafana dashboards for anomalies
2. Review Loki logs for errors
3. Check GitHub Actions for failed deployments
4. Review this guide for common solutions