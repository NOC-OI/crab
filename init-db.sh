#!/bin/bash
# This assumes the docker containers have already been brought up
source .env
docker compose down
docker compose up -d minio

echo "Waiting for MinIO to start..."
pingcount=0
until docker exec -it crab-minio curl -s -f -o /dev/null "http://localhost:9000/minio/health/live"
do
        symbol="|"
        case $(($pingcount % 4)) in
        0)
                symbol="/"
                ;;
        1)
                symbol="-"
                ;;
        2)
                symbol="\\"
                ;;
        3)
                symbol="|"
                ;;
        esac
        secs=$(($pingcount/10))
        echo -en "\rStill waiting for MinIO to start $symbol [$secs s]"
        pingcount=$(($pingcount+1))
        sleep 0.1
done
echo ""
echo "MinIO started!"
MC_ALIAS="local"
if [[ -z "$S3_ACCESS_KEY" ]]; then
S3_REGION="us-east-1"
S3_ENDPOINT="http://minio:9000"
S3_BUCKET="crab"
S3_ACCESS_KEY="crabsystem"
S3_SECRET_KEY="$(mktemp -u XXXXXXXXXXXXXXXXXXXXXXXX)"
echo "S3_REGION=\"$S3_REGION\"" >> .env
echo "S3_ENDPOINT=\"$S3_ENDPOINT\"" >> .env
echo "S3_ENDPOINT_LOCAL=\"http://localhost:9000\""
echo "S3_BUCKET=\"$S3_BUCKET\"" >> .env
echo "S3_ACCESS_KEY=\"$S3_ACCESS_KEY\"" >> .env
echo "S3_SECRET_KEY=\"$S3_SECRET_KEY\"" >> .env
else
MC_ALIAS="remote"
echo "Existing configutation for \"$S3_ENDPOINT\" as S3 backend found, skipping autoconf for MinIO"
fi
if [[ "$S3_ENDPOINT" = "http://localhost:9000" ]]; then
echo "Local MinIO specified, applying policy automatically"
./migrate-minio.sh
fi
docker exec -it crab-minio mc alias set $MC_ALIAS "$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
echo "Done bucket setup"
./migrate-couchdb.sh
