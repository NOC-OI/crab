#!/bin/bash

CRAB_EXTERNAL_HOST=$(hostname -f)
CRAB_EXTERNAL_HTTP_PORT=8080
CRAB_DEPLOYMENT_PREFIX=crab-
CRAB_DATA_DIR=/var/chumbucket/data

MINIO_ROOT_USER=root
MINIO_ROOT_PASSWORD=$(head -c 32 /dev/urandom | base64)

cat > .env << EOF
CRAB_EXTERNAL_HOST=$CRAB_EXTERNAL_HOST
CRAB_EXTERNAL_HTTP_PORT=$CRAB_EXTERNAL_HTTP_PORT
CRAB_DEPLOYMENT_PREFIX=$CRAB_DEPLOYMENT_PREFIX
CRAB_DATA_DIR=$CRAB_DATA_DIR

GUNICORN_WORKERS=8

# NOTE: This is used to autoconfigure the database, assuming you are using the included MinIO image
# If you are using a pre-existing cloud or on-prem S3 object store, you need to configure the S3 setting below
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD
MINIO_BROWSER_REDIRECT_URL=http://${CRAB_EXTERNAL_HOST}:9001/

# Uncomment and fill out the following to use and external MinIO instance:
#S3_REGION="us-east-1"
#S3_ENDPOINT="https://s3.us-east-1.amazonaws.com"
#S3_BUCKET="crab"
#S3_ACCESS_KEY="crabsystem"
#S3_SECRET_KEY=""

EOF

echo "You'll probably want to configure the DBs automatically using \"init-db.sh\""
echo "More complicated deployments using external S3 buckets e.t.c. should edit .env first"
