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
docker compose up -d keycloak
echo "Waiting for CouchDB to start..."
pingcount=0
until docker exec -it crab-couchdb curl -s -f -o /dev/null "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/_dbs_info"
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
        echo -en "\rStill waiting for CouchDB to start $symbol [$secs s]"
        pingcount=$(($pingcount+1))
        sleep 0.1
done
echo ""
echo "CouchDB up!"
echo "Waiting for Keycloak to start..."
pingcount=0
until curl -s -f -o /dev/null http://localhost:7080/
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
        echo -en "\rStill waiting for Keycloak to start $symbol [$secs s]"
        pingcount=$(($pingcount+1))
        sleep 0.1
done
echo ""
echo "Keycloak up!"

cd ./flask/src
rm -r temp
mkdir temp
echo "Connected to S3 server at $S3_ENDPOINT"
export S3_REGION=$S3_REGION
export S3_ENDPOINT=$S3_ENDPOINT
export S3_BUCKET=$S3_BUCKET
export S3_ACCESS_KEY=$S3_ACCESS_KEY
export S3_SECRET_KEY=$S3_SECRET_KEY
export COUCHDB_ROOT_USER=$COUCHDB_ROOT_USER
export COUCHDB_ROOT_PASSWORD=$COUCHDB_ROOT_PASSWORD
export COUCHDB_HOST=$COUCHDB_HOST
export CRAB_OPENID_CONFIG_URI=$CRAB_OPENID_CONFIG_URI
export CRAB_OPENID_CLIENT_ID=$CRAB_OPENID_CLIENT_ID
export CRAB_OPENID_CLIENT_SECRET=$CRAB_OPENID_CLIENT_SECRET
gunicorn -w 4 main:app -b 0.0.0.0
