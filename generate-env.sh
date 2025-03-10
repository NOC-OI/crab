#!/bin/bash

mkdir -p config

CRAB_EXTERNAL_HOST=$(hostname -f)
CRAB_EXTERNAL_HTTP_PORT=8080
CRAB_OPENID_CONFIG_URI="http://$CRAB_EXTERNAL_HOST/keycloak/realms/crab/.well-known/openid-configuration"
#CRAB_CSRF_SECRET_KEY=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

MINIO_ROOT_USER=root
MINIO_ROOT_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

RABBITMQ_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

COUCHDB_ROOT_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

KEYCLOAK_ADMIN_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

S3_ENDPOINT="http://minio:9000"
S3_BUCKET="crab"
S3_ACCESS_KEY="crabsystem"
S3_SECRET_KEY="$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXX)"

cat > .env << EOF
CRAB_EXTERNAL_HOST=$CRAB_EXTERNAL_HOST
CRAB_EXTERNAL_PORT=$CRAB_EXTERNAL_HTTP_PORT

GUNICORN_WORKERS=8

RABBITMQ_DEFAULT_USER=crab
RABBITMQ_DEFAULT_PASS="$RABBITMQ_PASSWORD"

COUCHDB_ROOT_USER="root"
COUCHDB_ROOT_PASSWORD="$COUCHDB_ROOT_PASSWORD"
COUCHDB_HOST="couchdb"


KC_HOSTNAME=$CRAB_EXTERNAL_HOST
KC_HOSTNAME_PORT=7080
KC_HOSTNAME_STRICT_BACKCHANNEL=true
KC_BOOTSTRAP_ADMIN_USERNAME="root"
KC_BOOTSTRAP_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD"
KC_HEALTH_ENABLED=true
KC_LOG_LEVEL=info

# NOTE: This is only for using the bundled MinIO S3 bucket.
# CRAB will pull credentials cron config/crab.json NOT this .env file!
# If you are using a pre-existing cloud or on-prem S3 object store, you need to add your configuration in config/crab.json
# If you're not running MinIO as part of your docker compose stack, you can safely delete the configuration below
DEFAULT_S3_ENDPOINT="$S3_ENDPOINT"
DEFAULT_S3_BUCKET="$S3_BUCKET"
DEFAULT_S3_ACCESS_KEY="$S3_ACCESS_KEY"
DEFAULT_S3_SECRET_KEY="$S3_SECRET_KEY"
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD"
MINIO_BROWSER_REDIRECT_URL=http://${CRAB_EXTERNAL_HOST}:9001/

EOF

mkdir -p config/couchdb
cat > config/couchdb/docker.ini << EOF
[admins]
root = $COUCHDB_ROOT_PASSWORD
single_node = true
EOF

cat > config/crab.json << EOF
{
    "brand": "CRAB",
    "long_brand": "Centralised Repository for Annotations and BLOBs",
    "s3_buckets": {
        "main": {
            "endpoint": "$DEFAULT_S3_ENDPOINT",
            "bucket": "$DEFAULT_S3_BUCKET",
            "access_key": "$DEFAULT_S3_ACCESS_KEY",
            "secret_key": "$DEFAULT_S3_SECRET_KEY"
        }
    },
    "default_s3_bucket": "main",
    "default_public_s3_bucket": "main",
    "openid_providers": {
        "keycloak": {
            "name": "Local Account",
            "oid_config_uri": "$CRAB_OPENID_CONFIG_URI",
            "oid_client_id": "crab",
            "oid_client_secret": "REPLACE_ME_WITH_KEYCLOAK_KEY"
        }
    }
}
EOF

echo "You'll probably want to configure the DBs automatically using \"init-db.sh\" before launching CRAB"
echo "More complicated deployments using external S3 buckets e.t.c. should edit .env and config/crab.json instead of ruinning \"init-db.sh\""
