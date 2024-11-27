#!/bin/bash
source .env
docker compose up -d couchdb
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
#until docker exec -it crab-couchdb curl -X PUT -H "Content-Type: application/json" -d "{\"key1\":\"value\"}" "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_sessions" > /dev/null
docker exec -it crab-couchdb curl -X PUT "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_sessions"
docker exec -it crab-couchdb curl -X PUT "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_users"
docker exec -it crab-couchdb curl -X PUT "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_jobs"
docker exec -it crab-couchdb curl -X PUT "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_samples"
docker exec -it crab-couchdb curl -X PUT "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_runs"
docker exec -it crab-couchdb curl -X PUT "http://$COUCHDB_ROOT_USER:$COUCHDB_ROOT_PASSWORD@localhost:5984/crab_projects"
