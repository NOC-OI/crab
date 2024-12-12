#!/bin/bash
source .env
docker compose down
docker compose up -d minio
docker compose up -d couchdb
docker compose up -d keycloak
# In this order since CouchDB usually takes longer than MinIO to start
echo "Waiting for MinIO and CouchDB to start..."
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
until curl -s -f -o /dev/null http://localhost:7080/realms/master/.well-known/openid-configuration
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

echo "Launching remaining containers..."
docker compose up -d
echo "Done!"
