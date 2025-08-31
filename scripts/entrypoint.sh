#!/bin/bash

# SmartArb Engine - Docker Entrypoint Script

# Secure container initialization and startup script

# Optimized for production deployment on Raspberry Pi 5

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================

# CONFIGURATION

# =============================================================================

# Application settings

APP_HOME=”${APP_HOME:-/app}”
APP_USER=”${APP_USER:-smartarb}”
APP_GROUP=”${APP_GROUP:-smartarb}”

# Environment settings

ENVIRONMENT=”${ENVIRONMENT:-production}”
DEBUG_MODE=”${DEBUG_MODE:-false}”
LOG_LEVEL=”${LOG_LEVEL:-INFO}”

# Database settings

POSTGRES_HOST=”${POSTGRES_HOST:-postgres}”
POSTGRES_PORT=”${POSTGRES_PORT:-5432}”
POSTGRES_DATABASE=”${POSTGRES_DATABASE:-smartarb}”
POSTGRES_USERNAME=”${POSTGRES_USERNAME:-smartarb_user}”
POSTGRES_MAX_RETRIES=”${POSTGRES_MAX_RETRIES:-30}”
POSTGRES_RETRY_DELAY=”${POSTGRES_RETRY_DELAY:-2}”

# Redis settings

REDIS_HOST=”${REDIS_HOST:-redis}”
REDIS_PORT=”${REDIS_PORT:-6379}”
REDIS_MAX_RETRIES=”${REDIS_MAX_RETRIES:-30}”
REDIS_RETRY_DELAY=”${REDIS_RETRY_DELAY:-2}”

# Security settings

ENABLE_HEALTH_CHECK=”${ENABLE_HEALTH_CHECK:-true}”
HEALTH_CHECK_PORT=”${HEALTH_CHECK_PORT:-8000}”

# =============================================================================

# UTILITY FUNCTIONS

# =============================================================================

# Logging functions

log_info() {
echo “$(date ‘+%Y-%m-%d %H:%M:%S’) [INFO] $1” >&2
}

log_warn() {
echo “$(date ‘+%Y-%m-%d %H:%M:%S’) [WARN] $1” >&2
}

log_error() {
echo “$(date ‘+%Y-%m-%d %H:%M:%S’) [ERROR] $1” >&2
}

log_debug() {
if [[ “${DEBUG_MODE}” == “true” ]]; then
echo “$(date ‘+%Y-%m-%d %H:%M:%S’) [DEBUG] $1” >&2
fi
}

# Check if running as root

check_root() {
if [[ $EUID -eq 0 ]]; then
log_error “Container should not run as root user”
exit 1
fi
}

# Check required environment variables

check_environment() {
local required_vars=(
“POSTGRES_HOST”
“POSTGRES_DATABASE”
“POSTGRES_USERNAME”
)

```
local missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    log_error "Missing required environment variables: ${missing_vars[*]}"
    exit 1
fi
```

}

# Wait for service to be ready

wait_for_service() {
local host=”$1”
local port=”$2”
local service_name=”$3”
local max_retries=”${4:-30}”
local retry_delay=”${5:-2}”

```
local retry_count=0

log_info "Waiting for $service_name at $host:$port..."

while ! nc -z "$host" "$port" >/dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    
    if [[ $retry_count -ge $max_retries ]]; then
        log_error "$service_name at $host:$port is not available after $max_retries attempts"
        return 1
    fi
    
    log_debug "$service_name not ready, attempt $retry_count/$max_retries"
    sleep "$retry_delay"
done

log_info "$service_name at $host:$port is ready"
return 0
```

}

# Test database connection

test_database() {
log_info “Testing database connection…”

```
local password_file=""
if [[ -f "/run/secrets/postgres_password" ]]; then
    password_file="/run/secrets/postgres_password"
elif [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
    password_file="/tmp/pgpass"
    echo "$POSTGRES_PASSWORD" > "$password_file"
    chmod 600 "$password_file"
else
    log_error "No database password provided"
    return 1
fi

if command -v pg_isready >/dev/null 2>&1; then
    if PGPASSFILE="$password_file" pg_isready \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USERNAME" \
        -d "$POSTGRES_DATABASE" >/dev/null 2>&1; then
        log_info "Database connection successful"
        return 0
    fi
fi

# Fallback: test with python
python3 -c "
```

import asyncio
import asyncpg
import sys
import os

async def test_connection():
try:
password = ‘’
if os.path.exists(’/run/secrets/postgres_password’):
with open(’/run/secrets/postgres_password’, ‘r’) as f:
password = f.read().strip()
elif ‘POSTGRES_PASSWORD’ in os.environ:
password = os.environ[‘POSTGRES_PASSWORD’]

```
    dsn = f'postgresql://{os.environ['POSTGRES_USERNAME']}:{password}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DATABASE']}'
    
    conn = await asyncpg.connect(dsn, command_timeout=5)
    result = await conn.fetchval('SELECT 1')
    await conn.close()
    
    if result == 1:
        print('Database connection successful')
        sys.exit(0)
    else:
        sys.exit(1)
        
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
```

asyncio.run(test_connection())
“ && return 0 || return 1
}

# Test Redis connection

test_redis() {
log_info “Testing Redis connection…”

```
local password=""
if [[ -f "/run/secrets/redis_password" ]]; then
    password=$(cat "/run/secrets/redis_password")
elif [[ -n "${REDIS_PASSWORD:-}" ]]; then
    password="$REDIS_PASSWORD"
fi

if command -v redis-cli >/dev/null 2>&1; then
    if [[ -n "$password" ]]; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$password" ping >/dev/null 2>&1; then
            log_info "Redis connection successful"
            return 0
        fi
    else
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
            log_info "Redis connection successful"
            return 0
        fi
    fi
fi

# Fallback: test with python
python3 -c "
```

import redis
import sys
import os

try:
password = ‘’
if os.path.exists(’/run/secrets/redis_password’):
with open(’/run/secrets/redis_password’, ‘r’) as f:
password = f.read().strip()
elif ‘REDIS_PASSWORD’ in os.environ:
password = os.environ[‘REDIS_PASSWORD’]

```
r = redis.Redis(
    host=os.environ['REDIS_HOST'],
    port=int(os.environ['REDIS_PORT']),
    password=password if password else None,
    socket_timeout=5
)

if r.ping():
    print('Redis connection successful')
    sys.exit(0)
else:
    sys.exit(1)
```

except Exception as e:
print(f’Redis connection failed: {e}’)
sys.exit(1)
“ && return 0 || return 1
}

# Setup application directories

setup_directories() {
log_info “Setting up application directories…”

```
local dirs=(
    "$APP_HOME/logs"
    "$APP_HOME/data"
    "$APP_HOME/tmp"
)

for dir in "${dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_debug "Created directory: $dir"
    fi
    
    # Ensure correct permissions
    if [[ -O "$dir" ]]; then
        chmod 755 "$dir"
    fi
done
```

}

# Load secrets from files

load_secrets() {
log_info “Loading secrets…”

```
local secrets_dir="/run/secrets"
if [[ -d "$secrets_dir" ]]; then
    for secret_file in "$secrets_dir"/*; do
        if [[ -f "$secret_file" ]]; then
            local secret_name=$(basename "$secret_file")
            local env_var=$(echo "$secret_name" | tr '[:lower:]' '[:upper:]')
            
            if [[ -z "${!env_var:-}" ]]; then
                export "$env_var"="$(cat "$secret_file")"
                log_debug "Loaded secret: $secret_name"
            fi
        fi
    done
fi
```

}

# Run database migrations

run_migrations() {
log_info “Running database migrations…”

```
# Check if alembic is available and migrations exist
if command -v alembic >/dev/null 2>&1 && [[ -f "$APP_HOME/alembic.ini" ]]; then
    cd "$APP_HOME"
    if alembic upgrade head; then
        log_info "Database migrations completed successfully"
    else
        log_error "Database migrations failed"
        return 1
    fi
else
    log_warn "No database migrations to run"
fi
```

}

# Perform health check

health_check() {
if [[ “${ENABLE_HEALTH_CHECK}” != “true” ]]; then
return 0
fi

```
log_info "Performing health check..."

# Check if health check script exists
if [[ -f "$APP_HOME/scripts/health_check.py" ]]; then
    if python3 "$APP_HOME/scripts/health_check.py"; then
        log_info "Health check passed"
        return 0
    else
        log_error "Health check failed"
        return 1
    fi
fi

# Fallback: simple port check
if nc -z localhost "$HEALTH_CHECK_PORT" >/dev/null 2>&1; then
    log_info "Health check passed (port check)"
    return 0
else
    log_warn "Health check failed (port check)"
    return 1
fi
```

}

# Signal handlers for graceful shutdown

cleanup() {
log_info “Received shutdown signal, cleaning up…”

```
# Kill child processes
if [[ -n "${app_pid:-}" ]]; then
    log_info "Stopping application (PID: $app_pid)..."
    kill -TERM "$app_pid" 2>/dev/null || true
    
    # Wait for graceful shutdown
    local timeout=30
    while kill -0 "$app_pid" 2>/dev/null && [[ $timeout -gt 0 ]]; do
        sleep 1
        timeout=$((timeout - 1))
    done
    
    # Force kill if still running
    if kill -0 "$app_pid" 2>/dev/null; then
        log_warn "Force killing application..."
        kill -KILL "$app_pid" 2>/dev/null || true
    fi
fi

log_info "Cleanup completed"
exit 0
```

}

# Setup signal handlers

setup_signal_handlers() {
trap cleanup SIGTERM SIGINT SIGQUIT
}

# Pre-flight checks

preflight_checks() {
log_info “Running pre-flight checks…”

```
# Check security
check_root

# Check environment
check_environment

# Load secrets
load_secrets

# Setup directories
setup_directories

# Wait for dependencies
if ! wait_for_service "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL" "$POSTGRES_MAX_RETRIES" "$POSTGRES_RETRY_DELAY"; then
    log_error "PostgreSQL is not available"
    exit 1
fi

if ! wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" "$REDIS_MAX_RETRIES" "$REDIS_RETRY_DELAY"; then
    log_error "Redis is not available"
    exit 1
fi

# Test connections
if ! test_database; then
    log_error "Database connection test failed"
    exit 1
fi

if ! test_redis; then
    log_error "Redis connection test failed"
    exit 1
fi

# Run migrations
if ! run_migrations; then
    log_error "Database migration failed"
    exit 1
fi

log_info "Pre-flight checks completed successfully"
```

}

# Start application

start_application() {
log_info “Starting SmartArb Engine…”

```
# Change to application directory
cd "$APP_HOME"

# Set Python path
export PYTHONPATH="$APP_HOME/src:$PYTHONPATH"

# Start the application
exec python3 -m src.core.engine "$@"
```

}

# =============================================================================

# MAIN EXECUTION

# =============================================================================

main() {
log_info “SmartArb Engine container starting…”
log_info “Environment: $ENVIRONMENT”
log_info “Debug mode: $DEBUG_MODE”
log_info “Log level: $LOG_LEVEL”
log_info “User: $(whoami)”
log_info “Working directory: $(pwd)”

```
# Setup signal handlers
setup_signal_handlers

# Handle special commands
case "${1:-}" in
    "health-check")
        health_check
        exit $?
        ;;
    "test-connections")
        test_database && test_redis
        exit $?
        ;;
    "migrations")
        run_migrations
        exit $?
        ;;
    "shell")
        log_info "Starting interactive shell..."
        exec /bin/bash
        ;;
    "--help"|"-h")
        cat << EOF
```

SmartArb Engine - Docker Entrypoint

Usage: $0 [COMMAND] [OPTIONS]

Commands:
(default)         Start the SmartArb Engine
health-check      Perform health check and exit
test-connections  Test database and Redis connections
migrations        Run database migrations only
shell            Start interactive shell
–help, -h       Show this help message

Environment Variables:
ENVIRONMENT              Environment name (default: production)
DEBUG_MODE              Enable debug mode (default: false)
LOG_LEVEL               Logging level (default: INFO)
POSTGRES_HOST           PostgreSQL host (default: postgres)
POSTGRES_PORT           PostgreSQL port (default: 5432)
POSTGRES_DATABASE       Database name (default: smartarb)
POSTGRES_USERNAME       Database username (default: smartarb_user)
REDIS_HOST              Redis host (default: redis)
REDIS_PORT              Redis port (default: 6379)
ENABLE_HEALTH_CHECK     Enable health checks (default: true)

Examples:
$0                      # Start the application
$0 health-check        # Run health check
$0 shell               # Start interactive shell

For more information, visit: https://github.com/your-username/smartarb-engine
EOF
exit 0
;;
esac

```
# Run pre-flight checks
preflight_checks

# Start the application
start_application "$@" &
app_pid=$!

# Wait for application to start
sleep 5

# Verify application is running
if ! kill -0 "$app_pid" 2>/dev/null; then
    log_error "Application failed to start"
    exit 1
fi

log_info "SmartArb Engine started successfully (PID: $app_pid)"

# Wait for application to finish
wait "$app_pid"
exit_code=$?

if [[ $exit_code -eq 0 ]]; then
    log_info "SmartArb Engine exited normally"
else
    log_error "SmartArb Engine exited with code: $exit_code"
fi

exit $exit_code
```

}

# Execute main function with all arguments

main “$@”