from flask import Flask, render_template, request, redirect, url_for, Response, make_response
import uuid
import os
import boto3
import jwt
import json
import zipfile
import couchdb
import urllib.parse
import requests
import secrets
import re
import microtiff.ifcb
from werkzeug.middleware.proxy_fix import ProxyFix

s3_region = os.environ.get("S3_REGION")
s3_endpoint = os.environ.get("S3_ENDPOINT")
s3_bucket = os.environ.get("S3_BUCKET")
s3_access_key = os.environ.get("S3_ACCESS_KEY")
s3_secret_key = os.environ.get("S3_SECRET_KEY")
print("S3 Endpoint = " + s3_endpoint)
s3 = boto3.resource("s3",
    endpoint_url=s3_endpoint,
    aws_access_key_id=s3_access_key,
    aws_secret_access_key=s3_secret_key,
    aws_session_token=None,
    config=boto3.session.Config(signature_version='s3v4'),
    verify=False
)
couch_user = os.environ.get("COUCHDB_ROOT_USER")
couch_password = os.environ.get("COUCHDB_ROOT_PASSWORD")
couch_host = os.environ.get("COUCHDB_HOST")
couch_port = os.environ.get("COUCHDB_PORT", 5984)
couch = couchdb.Server("http://" + couch_user + ":" + couch_password + "@" + couch_host + ":" + str(couch_port) + "/")
print(couch_host + ":" + str(couch_port))
print(couch["crab_runs"])

openid_config_uri = os.environ.get("CRAB_OPENID_CONFIG_URI")
openid_client_id = os.environ.get("CRAB_OPENID_CLIENT_ID")
openid_client_secret = os.environ.get("CRAB_OPENID_CLIENT_SECRET")

openid_config = requests.get(openid_config_uri).json()
openid_keys = jwt.PyJWKClient(openid_config["jwks_uri"])

global_vars = {
        "openid": openid_config,
        "brand": "CRAB",
        "long_brand": "Centralised Repository for Annotations and BLOBs"
    }

temp_loc = "temp"

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)


def to_snake_case(str_in):
    str_out = re.sub("(?<!^)(?<![A-Z])(?=[A-Z]+)", "_", str_in).lower() # Prepend all strings of uppercase with an underscore
    str_out = re.sub("[^a-z0-9]", "_", str_out) # Replace all non-alphanumeric with underscore
    str_out = re.sub("_+", "_", str_out) # Clean up double underscores
    str_out = re.sub("(^_)|(_$)", "", str_out) # Clean up trailing or leading underscores
    return str_out

#print(to_snake_case("OWOTestString--?test_test_TEST"))

def get_session_info():
    session_uuid = None
    raw_session_id = request.cookies.get("sessionId")
    if raw_session_id is None:
        return None
    try:
        uuid_obj = uuid.UUID(raw_session_id, version=4)
        session_uuid = str(uuid_obj)
    except ValueError:
        return None
    session_info = couch["crab_sessions"][session_uuid].copy()
    if session_info["status"] == "ACTIVE":
        if session_info["access_token"] == request.cookies.get("sessionKey"):
            session_info["session_uuid"] = session_uuid
            return session_info
    return None

@app.route("/")
def home_screen():
    session_info = get_session_info()
    return render_template("index.html", global_vars=global_vars, session_info=session_info)

@app.route("/account")
def account_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    return render_template("account.html", global_vars=global_vars, session_info=session_info)

@app.route("/inbound-login")
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

    data = {
            "client_secret": openid_client_secret,
            "client_id": openid_client_id,
            "redirect_uri": couch["crab_sessions"][session_uuid]["login_redirect_uri"],
            "code": request.args.get("code"),
            "grant_type": "authorization_code"
        }

    openid_response = requests.post(openid_config["token_endpoint"], data=data).json()

    if "scope" in openid_response:
        jwt_header = jwt.get_unverified_header(openid_response["access_token"])
        jwt_key = openid_keys.get_signing_key_from_jwt(openid_response["access_token"])
        openid_user_info = jwt.decode(openid_response["access_token"], key=jwt_key, algorithms=[jwt_header["alg"]], audience="account")

        session_info = couch["crab_sessions"][session_uuid]

        session_info["openid_info"] = openid_user_info
        session_info["user_uuid"] = openid_user_info["sub"]
        if "email" in openid_user_info:
            session_info["email"] = openid_user_info["email"]
            session_info["status"] = "ACTIVE"
        else:
            session_info["status"] = "MISSING_EMAIL"
            return Response(json.dumps({
                "error": "missingEmail",
                "msg": "User " + openid_user_info["sub"] + " does not have a valid email."
                }), status=400, mimetype='application/json')

        if "name" in openid_user_info:
            session_info["short_name"] = openid_user_info["name"]
        if "given_name" in openid_user_info:
            session_info["short_name"] = openid_user_info["given_name"]

        session_info["openid_access_token"] = openid_response["access_token"]
        access_token = secrets.token_urlsafe(24)
        session_info["access_token"] = access_token

        couch["crab_sessions"][session_uuid] = session_info

        response = make_response(redirect("/account", code=302))
        response.set_cookie("sessionId", session_uuid)
        response.set_cookie("sessionKey", access_token)
        return response
    else:
        return Response(json.dumps({
            "error": "authError",
            "msg": "Could not authenticate OpenID code for session " + session_uuid
            }), status=400, mimetype='application/json')

@app.route("/logout")
def logout_outbound_redirect():
    session_info = get_session_info()
    tokens = ""
    if not session_info is None:
        session_uuid = session_info["session_uuid"]
        session_info["status"] = "DESTROYED"
        del session_info["session_uuid"]
        couch["crab_sessions"][session_uuid] = session_info
    response = make_response(redirect("/", code=302))
    response.delete_cookie("sessionId")
    response.delete_cookie("sessionKey")
    return response

@app.route("/login")
def login_outbound_redirect():
    state = str(uuid.uuid4())
    nonce = str(uuid.uuid4())

    redirect_uri = request.host_url + "inbound-login"
    couch["crab_sessions"][state] = {
            "status": "PENDING_AUTH",
            "origin_ip": request.remote_addr,
            "login_redirect_uri": redirect_uri
        }
    tokens = "response_type=code&scope=basic+email&prompt=select_account&response_mode=query&state=" + state + "&nonce=" + nonce + "&redirect_uri=" + urllib.parse.quote_plus(redirect_uri) + "&client_id=" + urllib.parse.quote_plus(openid_client_id)
    return redirect(openid_config["authorization_endpoint"] + "?" + tokens, code=302)

@app.route('/applyMapping', methods=['POST'])
def unpack_upload():
    archive = None
    run_uuid = None
    try:
        uuid_obj = uuid.UUID(request.form["run_uuid"], version=4)
        archive = temp_loc + "/" + str(uuid_obj) + ".zip"
        run_uuid = str(uuid_obj)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + request.form["run_uuid"]
            }), status=400, mimetype='application/json')
    s3.Bucket(s3_bucket).upload_file(archive, "raw_uploads/" + run_uuid + ".zip")
    profile = request.form["sensor"]
    ret = {"uuid": run_uuid, "profile": profile}
    workdir = temp_loc + "/" + run_uuid + "-unpacked"
    with zipfile.ZipFile(archive) as zipf:
        zipf.extractall(workdir)
    if profile == "ifcb":
        print("IFCB profile!")
        #microtiff.
        targets = []
        for in_file in os.listdir(workdir):
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".adc" or in_file_s[1] == ".hdr" or in_file_s[1] == ".roi":
                targets.append(in_file_s[0])
        targets = list(set(targets))
        #print(targets)
        run_metadata = None
        group_metadata = {}
        for target in targets:
            with open(workdir + "/" + target + ".hdr") as f:
                header_lines = f.readlines()
                extracted_metadata = microtiff.ifcb.header_file_to_dict(header_lines)
                filtered_metadata = {}
                for key in extracted_metadata:
                    filtered_metadata[to_snake_case(key)] = extracted_metadata[key]
                group_metadata[target] = filtered_metadata
                if run_metadata is None:
                    run_metadata = group_metadata[target].copy()
                for gmk in group_metadata[target]:
                    if not run_metadata[gmk] == group_metadata[target][gmk]:
                        run_metadata[gmk] = []
            microtiff.ifcb.extract_ifcb_images(workdir + "/" + target)

        for group in group_metadata:
            for gmk in group_metadata[group]:
                #print(gmk)
                if type(run_metadata[gmk]) is list:
                    #print(group_metadata[group][gmk])
                    run_metadata[gmk].append(group_metadata[group][gmk])
                else:
                    group_metadata[group][gmk] = None
            group_metadata[group] = {k: v for k, v in group_metadata[group].items() if v is not None}
        run_metadata = {k: v for k, v in run_metadata.items() if v is not None}

        ret["run_metadata"] = run_metadata

        run_dblist = couch["crab_runs"]
        sample_dblist = couch["crab_samples"]
        samples = []

        for in_file in os.listdir(workdir):
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".tiff":
                base_group = in_file_s[0].split("_TN")[0]
                ofn = "runs/" + run_uuid + "/" + in_file_s[0] + ".tiff"
                s3.Bucket(s3_bucket).upload_file(workdir + "/" + in_file, ofn)
                sample_uuid = str(uuid.uuid4())
                sample_metadata = {
                    "path": ofn,
                    "host": s3_endpoint + "/" + s3_bucket,
                    "type": {
                            "dimensions": 2,
                            "format": "TIFF",
                            "channels": [
                                    {
                                        "type": "L",
                                        "bit_depth": 8
                                    }
                                ]
                        },
                    "origin_tags": group_metadata[base_group].copy()
                }
                sample_dblist[sample_uuid] = sample_metadata
                samples.append(sample_uuid)


        run_dblist[run_uuid] = {
            "origin_tags": run_metadata,
            "samples": samples
        }

    else:
        return Response(json.dumps({
            "error": "badProfile",
            "msg": "Invalid Profile " + profile
            }), status=400, mimetype='application/json')

    return Response(json.dumps(ret), status=200, mimetype='application/json')


@app.route("/upload", methods=['GET'])
def upload_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    return render_template("upload.html", global_vars=global_vars, session_info=session_info)

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    run_uuid = str(uuid.uuid4())
    if uploaded_file.filename != '':
        uploaded_file.save(temp_loc + "/" + run_uuid + ".zip")
    zipf = zipfile.ZipFile(temp_loc + "/" + run_uuid + ".zip")
    timestamp = None
    namelist = zipf.namelist()
    if len(namelist) > 0:
        dt = zipf.getinfo(namelist[0]).date_time
        timestamp = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(dt[0],dt[1],dt[2],dt[3],dt[4],dt[5])
    folder_structure = {}
    for nlpath in namelist:
        cd = folder_structure
        pels = re.split("/|\\\\", nlpath)
        for pel in pels[:-1]:
            try:
                cd[pel]
            except KeyError:
                cd[pel] = {}
            cd = cd[pel]
        if len(pels[-1]) > 0:
            cd[pels[-1]] = "file"

    ret = {
        "run_uuid": run_uuid,
        "directory_structure": folder_structure,
        "file_list": namelist,
        "timestamp": timestamp
    }
    return ret
