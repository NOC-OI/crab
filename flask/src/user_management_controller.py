import uuid
import jwt
import os
import json
import secrets
import requests
import urllib
from datetime import datetime
from flask import Blueprint, request, render_template, Response, make_response, redirect

from utils import get_session_info, get_app_frontend_globals, try_get_config_prop
from db import get_couch, get_couch_client, get_couch_base_uri

#openid_config_uri = os.environ.get("CRAB_OPENID_CONFIG_URI")
#openid_client_id = os.environ.get("CRAB_OPENID_CLIENT_ID")
#openid_client_secret = os.environ.get("CRAB_OPENID_CLIENT_SECRET")

crab_external_endpoint = "http://" + os.environ.get("CRAB_EXTERNAL_HOST") + ":" + os.environ.get("CRAB_EXTERNAL_PORT") + "/"
if os.environ.get("CRAB_EXTERNAL_PORT") == "80":
    crab_external_endpoint = "http://" + os.environ.get("CRAB_EXTERNAL_HOST") + "/"
elif os.environ.get("CRAB_EXTERNAL_PORT") == "443":
    crab_external_endpoint = "https://" + os.environ.get("CRAB_EXTERNAL_HOST") + "/"

openid_config = {}
all_oid_providers_conf_info = try_get_config_prop("openid_providers")
for provider in all_oid_providers_conf_info:
    oid_conf_file = requests.get(all_oid_providers_conf_info[provider]["oid_config_uri"]).json()
    oid_keys = jwt.PyJWKClient(oid_conf_file["jwks_uri"])
    openid_config[provider] = {
            "name": all_oid_providers_conf_info[provider]["name"],
            "src_config": oid_conf_file,
            "client_id": all_oid_providers_conf_info[provider]["oid_client_id"],
            "client_secret": all_oid_providers_conf_info[provider]["oid_client_secret"],
            "scopes": all_oid_providers_conf_info[provider]["scopes"],
            "keys": oid_keys
        }

login_pages = Blueprint("login_pages", __name__)
account_pages = Blueprint("account_pages", __name__)
access_token_pages = Blueprint("access_token_pages", __name__)
session_api = Blueprint("session_api", __name__)
users_api = Blueprint("users_api", __name__)

@account_pages.route("/account")
def account_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)


    mango_selector = {
            "user_uuid": session_info["user_uuid"],
            "status": "ACTIVE",
            "auth_type": "OPENID"
        }
    mango = {
            "selector": mango_selector,
            "fields": ["_id", "access_token", "ip_addr", "last_active"]
        }
    token_search_resp = requests.post(get_couch_base_uri() + "crab_sessions/" + "_find", json=mango).json()
    sessions = token_search_resp["docs"]
    for token in sessions:
        if "last_active" in token:
            token["last_active"] = datetime.fromtimestamp(token["last_active"]).strftime('%Y-%m-%d %H:%M:%S')

    return render_template("account.html", global_vars=get_app_frontend_globals(), session_info=session_info, sessions=sessions)

@access_token_pages.route("/account/access-tokens")
def access_tokens_list():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)

    mango_selector = {
            "user_uuid": session_info["user_uuid"],
            "status": "ACTIVE",
            "auth_type": "TOKEN"
        }
    mango = {
            "selector": mango_selector,
            "fields": ["_id", "access_token", "ip_addr", "last_active"]
        }
    token_search_resp = requests.post(get_couch_base_uri() + "crab_sessions/" + "_find", json=mango).json()
    tokens = token_search_resp["docs"]
    for token in tokens:
        if "last_active" in token:
            token["last_active"] = datetime.fromtimestamp(token["last_active"]).strftime('%Y-%m-%d %H:%M:%S')
    return render_template("access_tokens.html", global_vars=get_app_frontend_globals(), session_info=session_info, token_list=tokens)

@access_token_pages.route("/account/new-access-token")
def new_access_token():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)

    token_uuid = str(uuid.uuid4())

    access_token = secrets.token_urlsafe(48)

    session_info = {
            "access_token": access_token,
            "user_uuid": session_info["user_uuid"],
            "auth_type": "TOKEN",
            "email": session_info["email"],
            "status": "ACTIVE",
            "name": session_info["name"],
            "short_name": session_info["short_name"]
        }


    get_couch()["crab_sessions"][token_uuid] = session_info

    return redirect("/account/access-tokens", code=302)

@session_api.route("/api/v1/whoami")
def api_v1_whoami():
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')


    return Response(json.dumps(get_couch()["crab_users"][session_info["user_uuid"]], indent=4), status=200, mimetype='application/json')


#@run_api.route("/api/v1/get_user/<raw_uuid>", methods=['GET'])
@users_api.route("/api/v1/users/<raw_uuid>", methods=['GET'])
def api_v1_get_user(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        user_data = get_couch()["crab_users"][str(uuid_obj)]
        return Response(json.dumps(user_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@users_api.route("/api/v1/users/search", methods=['POST'])
def api_v1_user_search():
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        couch_client = get_couch_client()
        raw_users = couch_client.find_all("crab_users", selector = {"$text": {"$search": request.form.get("all")}})
        users = raw_users
        return Response(json.dumps(users), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@session_api.route("/api/v1/sessions/<raw_uuid>/close")
def api_v1_close_session(raw_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')


    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        session_data = get_couch()["crab_sessions"][str(uuid_obj)]
        if not session_data["user_uuid"] == session_info["user_uuid"]:
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to destroy this resource."
                }), status=401, mimetype='application/json')

        session_data["status"] = "DESTROYED"
        get_couch()["crab_sessions"][str(uuid_obj)] = session_data

        redirect_uri = request.args.get("redirect", "")
        if len(redirect_uri) > 0:
            return redirect(redirect_uri, code=302)
        else:
            return Response(json.dumps({
                "msg": "done",
                "layer": layer_data
                }), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')


@login_pages.route("/inbound-login")
def login_inbound_redirect():
    session_uuid = None
    try:
        uuid_obj = uuid.UUID(request.args.get("state"), version=4)
        session_uuid = str(uuid_obj)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + request.args.get("state")
            }), status=400, mimetype='application/json')

    couch_client = get_couch_client()

    session_info = couch_client.get_document("crab_sessions", session_uuid)
    if not session_info["oid_provider"] in openid_config:
        return Response(json.dumps({
            "error": "invalidProvider",
            "msg": session_info["oid_provider"] + " is not a registered OpenID provider on this CRAB installation."
            }), status=400, mimetype='application/json')
    oid_config = openid_config[session_info["oid_provider"]]

    data = {
            "client_secret": oid_config["client_secret"],
            "client_id": oid_config["client_id"],
            "redirect_uri": session_info["login_redirect_uri"],
            "code": request.args.get("code"),
            "grant_type": "authorization_code"
        }

    openid_response = requests.post(oid_config["src_config"]["token_endpoint"], data=data).json()

    if "scope" in openid_response:
        try:
            jwt_header = jwt.get_unverified_header(openid_response["access_token"])
            jwt_key = oid_config["keys"].get_signing_key_from_jwt(openid_response["access_token"])
            openid_auth_info = jwt.decode(openid_response["access_token"], key=jwt_key, algorithms=[jwt_header["alg"]], options={"verify_aud": False, "verify_iat": False, "verify_signature": True})



            headers = {
                    "Authorization": "Bearer " + openid_response["access_token"]
                }
            #print(requests.get(oid_config["src_config"]["userinfo_endpoint"], headers=headers).text)
            openid_user_info = requests.get(oid_config["src_config"]["userinfo_endpoint"], headers=headers).json()

            user_uuid = str(uuid.uuid4()) # Start with a random uid, overwrite with existing if possible

            mango_selector = {
                    "openid_sub": session_info["oid_provider"] + ":" + openid_auth_info["sub"]
                }
            mango = {
                    "selector": mango_selector,
                    "fields": ["_id", "openid_sub"]
                }
            user_search_resp = requests.post(get_couch_base_uri() + "crab_users/" + "_find", json=mango).json()

            if len(user_search_resp["docs"]) > 0:
                user_uuid = user_search_resp["docs"][0]["_id"]
            else:
                if "email" in openid_user_info:
                    # Fallback to email if sub does not match
                    mango_selector = {
                            "email": openid_user_info["email"].lower()
                        }
                    mango = {
                            "selector": mango_selector,
                            "fields": ["_id", "openid_sub"]
                        }
                    user_search_resp = requests.post(get_couch_base_uri() + "crab_users/" + "_find", json=mango).json()
                    if len(user_search_resp["docs"]) > 0:
                        user_uuid = user_search_resp["docs"][0]["_id"]


            session_info["openid_info"] = openid_user_info
            session_info["openid_auth"] = openid_auth_info
            session_info["user_uuid"] = user_uuid
            session_info["auth_type"] = "OPENID"
            if "email" in openid_user_info:
                session_info["email"] = openid_user_info["email"].lower()
                session_info["status"] = "ACTIVE"
            else:
                session_info["status"] = "MISSING_EMAIL"
                return Response(json.dumps({
                    "error": "missingEmail",
                    "msg": "User " + openid_user_info["sub"] + " does not have a valid email.",
                    "user_info": openid_user_info
                    }), status=400, mimetype='application/json')

            if "name" in openid_user_info:
                session_info["short_name"] = openid_user_info["name"]
                session_info["name"] = openid_user_info["name"]
            else:
                session_info["name"] = session_info["email"] # Fallback just in-case name is missing or restricted
                session_info["short_name"] = session_info["name"]
            if "given_name" in openid_user_info:
                session_info["short_name"] = openid_user_info["given_name"] # Preferentially use this in UI for this user

            session_info["openid_access_token"] = openid_response["access_token"]
            access_token = secrets.token_urlsafe(24)
            session_info["access_token"] = access_token

            get_couch()["crab_sessions"][session_uuid] = session_info
            user_doc = {
                    "email": session_info["email"],
                    "name": session_info["name"],
                    "openid_sub": session_info["oid_provider"] + ":" + openid_user_info["sub"],
                    "short_name": session_info["short_name"]
                }

            # TODO update to couchbeans
            if session_info["user_uuid"] in get_couch()["crab_users"]:
                user_doc["_rev"] = get_couch()["crab_users"][session_info["user_uuid"]]["_rev"]
            get_couch()["crab_users"][session_info["user_uuid"]] = user_doc

            response = make_response(redirect("/account", code=302))
            response.set_cookie("sessionId", session_uuid)
            response.set_cookie("sessionKey", access_token)
            return response
        except jwt.exceptions.PyJWTError:
            return Response(json.dumps({
                "error": "invalidJwt",
                "msg": "Could not validate OpenID JWT for session " + session_uuid,
                "response": openid_response
                }), status=400, mimetype='application/json')

    else:
        return Response(json.dumps({
            "error": "authError",
            "msg": "Could not authenticate OpenID code for session " + session_uuid,
            "response": openid_response
            }), status=400, mimetype='application/json')

@login_pages.route("/logout")
def logout_outbound_redirect():
    session_info = get_session_info()
    tokens = ""
    if not session_info is None:
        session_uuid = session_info["session_uuid"]
        session_info["status"] = "DESTROYED"
        del session_info["session_uuid"]
        get_couch()["crab_sessions"][session_uuid] = session_info
    response = make_response(redirect("/", code=302))
    response.delete_cookie("sessionId")
    response.delete_cookie("sessionKey")
    return response


@login_pages.route("/login")
def login_choose_provider_page():
    providers = []
    for prov in openid_config:
        providers.append({
                "id": prov,
                "name": openid_config[prov]["name"]
            })

    if len(providers) == 1:
        return redirect("/api/v1/openid/" + providers[0]["id"] + "/egress", code=302)
    else:
        return render_template("login-choose-oid.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), providers=providers)

@login_pages.route("/api/v1/openid/<provider>/egress")
def login_outbound_redirect(provider):
    if not provider in openid_config:
        return Response(json.dumps({
            "error": "invalidProvider",
            "msg": provider + " is not a registered OpenID provider on this CRAB installation."
            }), status=400, mimetype='application/json')

    oid_config = openid_config[provider]

    state = str(uuid.uuid4())
    nonce = str(uuid.uuid4())

    redirect_uri = crab_external_endpoint + "inbound-login"
    get_couch()["crab_sessions"][state] = {
            "status": "PENDING_AUTH",
            "origin_ip": request.remote_addr,
            "login_redirect_uri": redirect_uri,
            "oid_provider": provider
        }
    scopes = "+".join(oid_config["scopes"])
    tokens = "response_type=code&scope=" + scopes + "&prompt=select_account&response_mode=query&state=" + state + "&nonce=" + nonce + "&redirect_uri=" + urllib.parse.quote_plus(redirect_uri) + "&client_id=" + urllib.parse.quote_plus(oid_config["client_id"])
    return redirect(oid_config["src_config"]["authorization_endpoint"] + "?" + tokens, code=302)

