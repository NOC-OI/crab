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
cd /opt/keycloak/bin/
./kcadm.sh config credentials --server http://localhost:7080 --realm master --user $KC_BOOTSTRAP_ADMIN_USERNAME --password $KC_BOOTSTRAP_ADMIN_PASSWORD
./kcadm.sh update realms/master -s sslRequired=NONE
./kcadm.sh config credentials --server http://localhost:7080 --realm master --user $KC_BOOTSTRAP_ADMIN_USERNAME --password $KC_BOOTSTRAP_ADMIN_PASSWORD
./kcadm.sh update realms/crab -s sslRequired=NONE
