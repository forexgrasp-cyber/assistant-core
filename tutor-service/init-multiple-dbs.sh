#!/bin/bash
# =============================================================================
# PostgreSQL Multiple Database Initialization Script
# Creates databases and users for each service
# =============================================================================

set -e

# Function to create database and user
create_db_and_user() {
    local db_name=$1
    local user_name=$2
    local password=$3

    echo "Creating database '$db_name' and user '$user_name'..."

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        -- Create user if not exists
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$user_name') THEN
                CREATE ROLE $user_name WITH LOGIN PASSWORD '$password';
            ELSE
                ALTER ROLE $user_name WITH PASSWORD '$password';
            END IF;
        END
        \$\$;

        -- Create database if not exists
        SELECT 'CREATE DATABASE $db_name OWNER $user_name'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db_name')\gexec

        -- Grant privileges
        GRANT ALL PRIVILEGES ON DATABASE $db_name TO $user_name;

        -- Connect to the new database and grant schema privileges
        \c $db_name
        GRANT ALL ON SCHEMA public TO $user_name;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $user_name;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $user_name;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $user_name;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $user_name;

        -- Enable required extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        CREATE EXTENSION IF NOT EXISTS "btree_gin";
        CREATE EXTENSION IF NOT EXISTS "btree_gist";
EOSQL

    echo "Database '$db_name' ready for user '$user_name'"
}

# Create databases for each service
# Passwords are read from environment variables (set via Docker secrets/env)
create_db_and_user "tutor_service" "tutor_user" "${TUTOR_DB_PASSWORD}"
create_db_and_user "callagent_service" "callagent_user" "${CALLAGENT_DB_PASSWORD}"
create_db_and_user "jarvis_service" "jarvis_user" "${JARVIS_DB_PASSWORD}"
create_db_and_user "hvac_service" "hvac_user" "${HVAC_DB_PASSWORD}"

echo "All databases initialized successfully!"