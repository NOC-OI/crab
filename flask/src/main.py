from flask import Flask, render_template, request, redirect, url_for
from flask import render_template
import uuid
import json
import zipfile
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

@app.route("/")
def home_screen():
    return render_template("index.html")

@app.route("/upload", methods=['GET'])
def upload_screen():
    return render_template("upload.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    run_uuid = str(uuid.uuid4())
    if uploaded_file.filename != '':
        uploaded_file.save(run_uuid + ".zip")
    zipf = zipfile.ZipFile(run_uuid + ".zip")
    namelist = zipf.namelist()
    primary_metadata_files = []
    primary_metadata = []
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
            primary_metadata.append(json.loads(mdfilefh.read()))

    ret = {
        "run_uuid": run_uuid,
        "primary_metadata_files": primary_metadata_files,
        "primary_metadata": primary_metadata,
        "secondary_metadata_files": metadata_files,
        "unknown_files": unknown_files
    }
    return ret
