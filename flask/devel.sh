#!/bin/bash
if [ -f .env ]; then
    echo "Using local .env"
else
    echo "Copying .env from project root (../.env)"
    cp ../.env .env
fi
source .env
cd ../

docker compose up -d minio couchdb keycloak rabbitmq
SECONDS=0

waiting_on=()
function health_check(){
        waiting_on=()
        ac=0
        if docker exec -it crab-minio curl -m 1 -s -f -o /dev/null "http://localhost:9000/minio/health/live"; then
                let "ac+=1"
        else
                waiting_on+=("MinIO")
        fi
        if docker exec -it crab-couchdb curl -m 1 -s -f -o /dev/null "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/_dbs_info"; then
                let "ac+=1"
        else
                waiting_on+=("CouchDB")
        fi
        if docker exec -it crab-rabbitmq rabbitmq-diagnostics -q ping > /dev/null; then
                let "ac+=1"
        else
                waiting_on+=("RabbitMQ")
        fi
        if curl -m 1 -s -f -o /dev/null http://localhost:7080/realms/master/.well-known/openid-configuration; then
                let "ac+=1"
        else
                waiting_on+=("Keycloak")
        fi
        if [ $ac -ge 4 ]; then
                return 0
        fi
        return 1
}

echo "Launching foundational containers, this usually takes around 30s"
pingcount=0
until health_check
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
        printf -v joined_waiting_on '%s, ' "${waiting_on[@]}"
        joined_waiting_on=${joined_waiting_on::-2}
        echo -en "\rWaiting for $joined_waiting_on to start... $symbol [$SECONDS s]                                           "
        pingcount=$(($pingcount+1))
        sleep 0.1
done
echo ""
echo "Foundation containers OK!"

cd ./flask/src
rm -r temp
mkdir temp
echo "Connected to S3 server at $S3_ENDPOINT_LOCAL"
export S3_REGION=$S3_REGION
export S3_ENDPOINT=$S3_ENDPOINT_LOCAL
export S3_BUCKET=$S3_BUCKET
export S3_ACCESS_KEY=$S3_ACCESS_KEY
export S3_SECRET_KEY=$S3_SECRET_KEY
export COUCHDB_ROOT_USER=$COUCHDB_ROOT_USER
export COUCHDB_ROOT_PASSWORD=$COUCHDB_ROOT_PASSWORD
export COUCHDB_HOST=$COUCHDB_HOST
export CRAB_CSRF_SECRET_KEY=$CRAB_CSRF_SECRET_KEY
export CRAB_OPENID_CONFIG_URI=$CRAB_OPENID_CONFIG_URI
export CRAB_OPENID_CLIENT_ID=$CRAB_OPENID_CLIENT_ID
export CRAB_OPENID_CLIENT_SECRET=$CRAB_OPENID_CLIENT_SECRET
export CRAB_EXTERNAL_HOST=$CRAB_EXTERNAL_HOST
export CRAB_EXTERNAL_PORT=$CRAB_EXTERNAL_PORT
export RABBITMQ_DEFAULT_USER=$RABBITMQ_DEFAULT_USER
export RABBITMQ_DEFAULT_PASS=$RABBITMQ_DEFAULT_PASS
export RABBITMQ_HOST=$RABBITMQ_HOST
export RABBITMQ_PORT=$RABBITMQ_PORT

gunicorn -w 4 main:app -b 0.0.0.0
