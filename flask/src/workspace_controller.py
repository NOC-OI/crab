import uuid
import zipfile
import re
import json
from datetime import datetime
import os
from PIL import Image
from flask import Blueprint, request, render_template, Response, make_response, redirect
import urllib.parse
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_client, advertise_job, get_s3_profiles, get_s3_profile, get_default_s3_profile_name, get_s3_client, get_s3_bucket_name

temp_loc = "temp"

workspace_pages = Blueprint("workspace_pages", __name__)
workspace_api = Blueprint("workspace_api", __name__)

@workspace_pages.route("/workspaces/new", methods=['GET'])
def new_workspace_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    s3_profiles = []
    for profile_id in get_s3_profiles():
        s3_profile_info = get_s3_profile(profile_id)
        profile_name = s3_profile_info["name"]
        if "public" in s3_profile_info:
            if s3_profile_info["public"]:
                profile_name = profile_name + " [PUBLIC ACCESS]"
        s3_profiles.append({
                "id": profile_id,
                "name": profile_name
            })

    hints = request.args.get("hints", "").split(" ")
    return render_template("workspace_new.html", global_vars=get_app_frontend_globals(), session_info=session_info, s3_profiles=s3_profiles, hints=urllib.parse.quote_plus(" ".join(hints)))

@workspace_pages.route("/workspaces/<workspace_uuid>", methods=['GET'])
def workspace_screen(workspace_uuid):
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    workspace_id = workspace_uuid
    return render_template("workspace.html", global_vars=get_app_frontend_globals(), session_info=session_info, workspace_id=workspace_id)


@workspace_api.route("/api/v1/workspaces/new", methods=['POST'])
def api_v1_new_workspace():
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')

    hints = request.args.get("hints", "").split(" ")
    workspace_uuid = str(uuid.uuid4())
    redirect_uri = request.args.get("redirect", "")
    view_resource = request.args.get("view_resource", "false") == "true"
    if view_resource:
        redirect_uri = "/workspaces/" + workspace_uuid
    if "?" in redirect_uri:
        redirect_uri = redirect_uri + "&hints=" + urllib.parse.quote_plus(" ".join(hints))
    else:
        redirect_uri = redirect_uri + "?hints=" + urllib.parse.quote_plus(" ".join(hints))

    couch_client = get_couch_client()
    couch_client.put_document("crab_workspaces", workspace_uuid, {
            "owner": session_info["user_uuid"],
            "folder_structure": {},
            "files": {}
        })

    if len(redirect_uri) > 0:
        return redirect(redirect_uri, code=302)
    else:
        return Response(json.dumps({
            "msg": "done",
            "workspace_id": workspace_uuid
            }), status=200, mimetype='application/json')

@workspace_api.route("/api/v1/workspaces/<workspace_uuid>", methods=['GET'])
def api_v1_get_workspace(workspace_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')

    try:
        uuid_obj = uuid.UUID(workspace_uuid, version=4)
        couch_client = get_couch_client()
        workspace_def = couch_client.get_document("crab_workspaces", str(uuid_obj))
        if not session_info["user_uuid"] == workspace_def["owner"]:
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        return Response(json.dumps(workspace_def), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid workspace UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@workspace_api.route("/api/v1/workspaces/<workspace_uuid>", methods=['POST'])
def api_v1_workspace_upload_file(workspace_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')

    try:
        uuid_obj = uuid.UUID(workspace_uuid, version=4)
        couch_client = get_couch_client()
        workspace_def = couch_client.get_document("crab_workspaces", str(uuid_obj))

        if not session_info["user_uuid"] == workspace_def["owner"]:
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        uploaded_file = request.files['file']
        file_size = uploaded_file.seek(0, os.SEEK_END)
        file_uuid = str(uuid.uuid4())
        if uploaded_file.filename != '':
            uploaded_file.save(temp_loc + "/" + file_uuid + ".bin")
            filename = uploaded_file.filename
            filename = re.sub("\\\\", "/", filename)
            filename = filename.strip("/")

            s3_profile = get_default_s3_profile_name()
            s3_path = "workspaces/" + workspace_uuid + "/" + file_uuid + ".bin"

            dirs = filename.split("/")
            da = 0 # DirectoryAdjust - we treat zero file size as a directory - not perfect, but a good approximation
            if file_size == 0:
                da = 1

            if len(dirs) > (1 - da):
                dir_arr = workspace_def["folder_structure"]
                for idx in range(0, (len(dirs) - (2 - da))):
                    if not dirs[idx] in dir_arr:
                        dir_arr[dirs[idx]] = {}
                    dir_arr = dir_arr[dirs[idx]]



            if file_size > 0:
                if request.args.get("s3_profile", "") in get_s3_profiles():
                    s3_profile = request.args.get("s3_profile")

                filedef = {
                        "file_uuid": file_uuid,
                        "owned": True,
                        "size": file_size,
                        "s3_profile": s3_profile,
                        "path": s3_path
                    }
                workspace_def["files"][filename] = filedef

                with open(temp_loc + "/" + file_uuid + ".bin", "rb") as f:
                    get_s3_client(s3_profile).upload_fileobj(f, get_s3_bucket_name(s3_profile), s3_path)

            couch_client.put_document("crab_workspaces", workspace_uuid, workspace_def)

            if file_size > 0:
                return Response(json.dumps({
                        "directory": False,
                        "file_uuid": file_uuid,
                        "s3_profile": s3_profile,
                        "path": s3_path
                    }), status=200, mimetype='application/json')
            else:
                return Response(json.dumps({
                        "directory": True
                    }), status=200, mimetype='application/json')


        return Response(json.dumps({
            "error": "uploadError",
            "msg": "File did not upload correctly."
            }), status=400, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid workspace UUID " + raw_uuid
            }), status=400, mimetype='application/json')
