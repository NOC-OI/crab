#!/bin/bash

mkdir -p config

CRAB_EXTERNAL_HOST=$(hostname -f)
CRAB_EXTERNAL_HTTP_PORT=8080
CRAB_EXTERNAL_HTTP_PORT=8443
CRAB_DEPLOYMENT_PREFIX=crab-
CRAB_DATA_DIR=/var/chumbucket/data

CRAB_OPENID_CONFIG_URI="http://$CRAB_EXTERNAL_HOST:7080/realms/crab/.well-known/openid-configuration"

MINIO_ROOT_USER=root
MINIO_ROOT_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

COUCHDB_ROOT_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

KEYCLOAK_ADMIN_PASSWORD=$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)

cat > .env << EOF
CRAB_EXTERNAL_HOST=$CRAB_EXTERNAL_HOST
CRAB_EXTERNAL_HTTP_PORT=$CRAB_EXTERNAL_HTTP_PORT
CRAB_DEPLOYMENT_PREFIX=$CRAB_DEPLOYMENT_PREFIX
CRAB_DATA_DIR=$CRAB_DATA_DIR

CRAB_OPENID_CONFIG_URI=$CRAB_OPENID_CONFIG_URI

GUNICORN_WORKERS=8

# NOTE: This is used to autoconfigure the database, assuming you are using the included MinIO image
# If you are using a pre-existing cloud or on-prem S3 object store, you need to configure the S3 setting below
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD"
MINIO_BROWSER_REDIRECT_URL=http://${CRAB_EXTERNAL_HOST}:9001/

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

CERTBOT_EMAIL="webmaster@$CRAB_EXTERNAL_HOST"

# Uncomment and fill out the following to use and external MinIO instance:
#S3_REGION="us-east-1"
#S3_ENDPOINT="https://s3.us-east-1.amazonaws.com"
#S3_BUCKET="crab"
#S3_ACCESS_KEY="crabsystem"
#S3_SECRET_KEY=""

EOF

mkdir -p config/couchdb
cat > config/couchdb/docker.ini << EOF
[admins]
root = $COUCHDB_ROOT_PASSWORD
single_node = true
EOF

echo "You'll probably want to configure the DBs automatically using \"init-db.sh\""
echo "More complicated deployments using external S3 buckets e.t.c. should edit .env first"
