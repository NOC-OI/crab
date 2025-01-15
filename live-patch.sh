#!/bin/bash
source .env
./build.sh
# Just bring UI down, leave everything else possible up
docker compose down ui
docker compose up -d minio
docker compose up -d couchdb
docker compose up -d keycloak
# In this order since CouchDB usually takes longer than MinIO to start, and Keycloak takes the longest
echo "Ensuring MinIO, CouchDB and Keycloak have started..."
pingcount=0
until docker exec -it crab-minio curl -s -f -o /dev/null "http://localhost:9000/minio/health/live" && docker exec -it crab-couchdb curl -s -f -o /dev/null "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/_dbs_info" && curl -s -f -o /dev/null http://localhost:7080/realms/master/.well-known/openid-configuration
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
        echo -en "\rWaiting for containers to start $symbol [$secs s]"
        pingcount=$(($pingcount+1))
        sleep 0.1
done
echo ""
echo "Core services live!"

echo "Bringing up remaining containers..."
docker compose up -d
echo "Done!"
