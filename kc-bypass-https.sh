source .env
docker compose up -d keycloak
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
docker exec -it crab-keycloak /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:7080 --realm master --user $KC_BOOTSTRAP_ADMIN_USERNAME --password $KC_BOOTSTRAP_ADMIN_PASSWORD
docker exec -it crab-keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE

docker exec -it crab-keycloak /opt/keycloak/bin/kcadm.sh create realms -s realm=crab -s enabled=true -o
docker exec -it crab-keycloak /opt/keycloak/bin/kcadm.sh update realms/crab -s sslRequired=NONE
docker exec -it crab-keycloak bash -c "/opt/keycloak/bin/kcadm.sh create clients -r crab -s clientId=crab -s 'redirectUris=[\"http://$CRAB_EXTERNAL_HOST:$CRAB_EXTERNAL_PORT/*\", \"http://$CRAB_EXTERNAL_HOST/*\", \"https://$CRAB_EXTERNAL_HOST:$CRAB_EXTERNAL_PORT/*\", \"https://$CRAB_EXTERNAL_HOST/*\"]' -i > /opt/keycloak/crab-kc-cid.txt"

docker exec -it crab-keycloak /opt/keycloak/bin/kcadm.sh create users -r crab -s username=root -s enabled=true
#docker exec -it crab-keycloak bash -c "/opt/keycloak/bin/kcadm.sh get clients/\$(cat /opt/keycloak/crab-kc-cid.txt | tr -d '\\n')/installation/providers/keycloak-oidc-keycloak-json"
docker exec -it crab-keycloak /opt/keycloak/bin/kcadm.sh set-password -r crab --username root --password $KC_BOOTSTRAP_ADMIN_PASSWORD --temporary
