from flask import Flask, render_template, request, redirect, url_for, Response
import uuid
import os
import boto3
import json
import zipfile
import couchdb
import requests
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

global_vars = {"openid": openid_config}

#print(openid_config)

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
    return render_template("upload.html")

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


    #for mdfile in primary_metadata_files:
    #    with zipf.open(mdfile) as mdfilefh:
    #        primary_metadata[mdfile] = json.loads(mdfilefh.read())

    #ret = {
    #    "run_uuid": run_uuid,
    #    "primary_metadata_files": primary_metadata_files,
    #    "primary_metadata": primary_metadata,
    #    "secondary_metadata_files": metadata_files,
    #    "unknown_files": unknown_files
    #}
    ret = {
        "run_uuid": run_uuid,
        "directory_structure": folder_structure,
        "file_list": namelist,
        "timestamp": timestamp
    }
    return ret
