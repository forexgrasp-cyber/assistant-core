#!/bin/bash
# Deployment script for Tutor Service on languages.snapford.com

set -e

COMPOSE_FILE="docker-compose.languages.yml"
PROJECT_NAME="languages"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check .env file
    if [ ! -f .env ]; then
        log_error ".env file not found. Copy from .env.example and configure."
        exit 1
    fi

    # Check .postgres_password
    if [ ! -f .postgres_password ]; then
        log_error ".postgres_password file not found. Generate with: openssl rand -base64 24"
        exit 1
    fi

    # Check tutor-service .env
    if [ ! -f ../tutor-service/.env ]; then
        log_error "../tutor-service/.env not found. Copy from shared.env.template and configure."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

build() {
    log_info "Building Docker images..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME build --no-cache
    log_success "Build complete"
}

up() {
    log_info "Starting services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
    log_success "Services started"

    # Wait for health checks
    log_info "Waiting for services to be healthy..."
    sleep 10

    # Check health
    check_health
}

down() {
    log_info "Stopping services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    log_success "Services stopped"
}

restart() {
    log_info "Restarting services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart
    log_success "Services restarted"
    sleep 5
    check_health
}

check_health() {
    log_info "Checking service health..."

    # Check tutor service
    for i in {1..30}; do
        if curl -sf http://localhost:8147/health > /dev/null 2>&1; then
            log_success "Tutor service is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Tutor service health check failed"
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs tutor-service --tail=50
            exit 1
        fi
        sleep 2
    done

    # Check nginx
    for i in {1..10}; do
        if curl -sf http://localhost/health > /dev/null 2>&1; then
            log_success "Nginx is healthy"
            break
        fi
        if [ $i -eq 10 ]; then
            log_warning "Nginx health check failed (may need SSL certs first)"
            break
        fi
        sleep 2
    done
}

logs() {
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f --tail=100
}

status() {
    log_info "Service status:"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps

    echo ""
    log_info "Health checks:"
    check_health
}

ssl() {
    log_info "Obtaining SSL certificates for languages.snapford.com..."

    # Ensure nginx is running for ACME challenge
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d nginx

    # Wait for nginx to be ready
    sleep 5

    # Obtain certificates
    docker run -it --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot \
        -w /var/www/certbot \
        -d languages.snapford.com \
        -d www.languages.snapford.com \
        --email admin@snapford.com \
        --agree-tos \
        --no-eff-email \
        --force-renewal

    if [ $? -eq 0 ]; then
        log_success "SSL certificates obtained"
        # Reload nginx with new certs
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec nginx nginx -s reload
        log_success "Nginx reloaded with SSL"
    else
        log_error "Failed to obtain SSL certificates"
        log_info "Check DNS: dig languages.snapford.com"
        log_info "Check nginx logs: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs nginx"
        exit 1
    fi
}

ssl_renew() {
    log_info "Renewing SSL certificates..."
    docker run -it --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot renew \
        --webroot \
        -w /var/www/certbot

    if [ $? -eq 0 ]; then
        log_success "SSL certificates renewed"
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec nginx nginx -s reload
    else
        log_error "Failed to renew SSL certificates"
        exit 1
    fi
}

backup() {
    BACKUP_DIR="backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/languages_backup_$TIMESTAMP.tar.gz"

    log_info "Creating backup..."
    mkdir -p $BACKUP_DIR

    # Backup PostgreSQL
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres pg_dumpall -U postgres | gzip > "$BACKUP_FILE"

    log_success "Backup created: $BACKUP_FILE"
}

restore() {
    if [ -z "$1" ]; then
        log_error "Usage: $0 restore <backup_file>"
        exit 1
    fi

    BACKUP_FILE=$1

    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    log_warning "This will restore the database from $BACKUP_FILE. Continue? (y/N)"
    read -r confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database..."
    gunzip -c "$BACKUP_FILE" | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres
    log_success "Database restored"
}

migrate() {
    log_info "Running database migrations for tutor-service..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec tutor-service alembic upgrade head
    log_success "Migrations complete"
}

seed() {
    log_info "Seeding curriculum..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec tutor-service python -m app.scripts.seed_curriculum
    log_success "Curriculum seeded"
}

test_webhook() {
    log_info "Testing webhook endpoint..."
    curl -X POST https://languages.snapford.com/api/v1/agent/telephony/voice \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -H "X-Telephony-Provider: mock" \
        -d "CallSid=test123&From=+15551234567&To=+15559876543&CallStatus=ringing&Direction=inbound"
}

show_help() {
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build       - Build all Docker images"
    echo "  up          - Start all services"
    echo "  down        - Stop all services"
    echo "  restart     - Restart all services"
    echo "  status      - Show service status and health"
    echo "  logs        - Follow logs (Ctrl+C to exit)"
    echo "  ssl         - Obtain Let's Encrypt SSL certificates"
    echo "  ssl-renew   - Renew SSL certificates"
    echo "  backup      - Create database backup"
    echo "  restore     - Restore database from backup file"
    echo "  migrate     - Run database migrations"
    echo "  seed        - Seed curriculum data"
    echo "  test-webhook - Test telephony webhook endpoint"
    echo ""
    echo "Examples:"
    echo "  $0 up          # Deploy and start"
    echo "  $0 ssl         # Get SSL certs (run after up)"
    echo "  $0 status      # Check health"
    echo "  $0 logs        # View logs"
}

# Main
case "${1:-}" in
    build)
        check_prerequisites
        build
        ;;
    up)
        check_prerequisites
        up
        ;;
    down)
        down
        ;;
    restart)
        check_prerequisites
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    ssl)
        ssl
        ;;
    ssl-renew)
        ssl_renew
        ;;
    backup)
        backup
        ;;
    restore)
        restore "$2"
        ;;
    migrate)
        migrate
        ;;
    seed)
        seed
        ;;
    test-webhook)
        test_webhook
        ;;
    *)
        show_help
        exit 1
        ;;
esac