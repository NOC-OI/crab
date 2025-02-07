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
MC_ALIAS="remote"
if [[ "$DEFAULT_S3_ENDPOINT" = "http://localhost:9000" ]]; then
echo "Local MinIO specified, applying policy automatically"
./migrate-minio.sh
fi
docker exec -it crab-minio mc alias set $MC_ALIAS "$DEFAULT_S3_ENDPOINT" "$DEFAULT_S3_ACCESS_KEY" "$DEFAULT_S3_SECRET_KEY"
echo "Done bucket setup"
./migrate-couchdb.sh
