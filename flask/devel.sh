#!/bin/bash
if [ -f .env ]; then
    echo "Using local .env"
else
    echo "Copying .env from project root (../.env)"
    cp ../.env .env
fi
source .env
cd ../
docker compose up -d minio
docker compose up -d couchdb
cd ./flask/src
echo "Connected to S3 server at $S3_ENDPOINT"
export S3_REGION=$S3_REGION
export S3_ENDPOINT=$S3_ENDPOINT
export S3_BUCKET=$S3_BUCKET
export S3_ACCESS_KEY=$S3_ACCESS_KEY
export S3_SECRET_KEY=$S3_SECRET_KEY
export COUCHDB_ROOT_USER=$COUCHDB_ROOT_USER
export COUCHDB_ROOT_PASSWORD=$COUCHDB_ROOT_PASSWORD
export COUCHDB_HOST=$COUCHDB_HOST
gunicorn -w 4 main:app -b 0.0.0.0
