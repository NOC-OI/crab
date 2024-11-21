from flask import Flask, render_template, request, redirect, url_for, Response
import uuid
import os
import boto3
import json
import zipfile
import couchdb
import requests
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
couch = couchdb.Server("https://" + couch_user + ":" + couch_password + "@" + couch_host + ":" + str(couch_port) + "/")

openid_config_uri = os.environ.get("CRAB_OPENID_CONFIG_URI")
openid_client_id = os.environ.get("CRAB_OPENID_CLIENT_ID")
openid_client_secret = os.environ.get("CRAB_OPENID_CLIENT_SECRET")

openid_config = requests.get(openid_config_uri).json()

global_vars = {"openid": openid_config}

print(openid_config)

temp_loc = "temp"

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)



@app.route("/")
def home_screen():
    global global_vars
    return render_template("index.html", global_vars=global_vars)

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
            "error": "badRequest",
            "msg": "Invalid UUID " + request.form["run_uuid"]
            }), status=400, mimetype='application/json')
    s3.Bucket(s3_bucket).upload_file(archive, "raw_uploads/" + run_uuid + ".zip")
    with zipfile.ZipFile(archive) as zipf:
        zipf.extractall(temp_loc + "/" + run_uuid + "-unpacked")
    return Response(json.dumps(request.form["run_uuid"]), status=200, mimetype='application/json')


@app.route("/upload", methods=['GET'])
def upload_screen():
    return render_template("upload.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    run_uuid = str(uuid.uuid4())
    if uploaded_file.filename != '':
        uploaded_file.save(temp_loc + "/" + run_uuid + ".zip")
    zipf = zipfile.ZipFile(temp_loc + "/" + run_uuid + ".zip")
    namelist = zipf.namelist()
    primary_metadata_files = []
    primary_metadata = {}
    metadata_files = []
    unknown_files = []
    for nlpath in namelist:
        if nlpath.endswith(".json"):
            primary_metadata_files.append(nlpath)
        elif nlpath.endswith(".csv"):
            metadata_files.append(nlpath)
        elif nlpath.endswith(".ctx"):
            metadata_files.append(nlpath)
        elif nlpath.endswith(".txt"):
            metadata_files.append(nlpath)
        elif nlpath.endswith(".ifo"):
            metadata_files.append(nlpath)
        else:
            unknown_files.append(nlpath)

    for mdfile in primary_metadata_files:
        with zipf.open(mdfile) as mdfilefh:
            primary_metadata[mdfile] = json.loads(mdfilefh.read())

    ret = {
        "run_uuid": run_uuid,
        "primary_metadata_files": primary_metadata_files,
        "primary_metadata": primary_metadata,
        "secondary_metadata_files": metadata_files,
        "unknown_files": unknown_files
    }
    return ret
