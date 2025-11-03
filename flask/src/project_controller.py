from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case, get_s3_profile_array_for_ui
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object, advertise_job
import markdown
from pygments.formatters import HtmlFormatter
from base64 import urlsafe_b64encode


project_pages = Blueprint("project_pages", __name__)
project_api = Blueprint("project_api", __name__)

def can_view(project_uuid):
    session_info = get_session_info()
    project_data = get_couch()["crab_projects"][project_uuid]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return project_data["public_visibility"]

def can_edit(project_uuid):
    session_info = get_session_info()
    project_data = get_couch()["crab_projects"][project_uuid]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return False

@project_pages.route("/projects/new", methods=['GET'])
def project_new_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    return render_template("project_new.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())



@project_pages.route("/projects/new", methods=['POST'])
def unpack_upload():
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')

    project_uuid = str(uuid.uuid4())
    identifier = request.form.get("identifier", project_uuid)
    public_visibility = request.form.get("public_visibility", False) == "on"
    description = request.form.get("description", "")
    readme = request.form.get("readme", "")
    dt = datetime.datetime.now()
    timestamp = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second)

    document_template = {
            "identifier": identifier,
            "public_visibility": public_visibility,
            "collaborators": [session_info["user_uuid"]],
            "description": description,
            "readme": readme,
            "creation_timestamp": timestamp,
            "deposits": []
        }

    project_dblist = get_couch()["crab_projects"]
    project_dblist[project_uuid] = document_template

    response = make_response(redirect("/projects/" + project_uuid, code=302))
    return response

@project_pages.route("/projects/<raw_uuid>/edit", methods=['GET'])
def project_edit_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        return render_template("project_edit.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), project_data=project_data)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')


@project_pages.route("/projects/<raw_uuid>/export", methods=['GET'])
def project_export_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        return render_template("project_export.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), project_data=project_data, s3_profiles=get_s3_profile_array_for_ui())
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_pages.route("/projects/<raw_uuid>/edit", methods=['POST'])
def project_edit_function(raw_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]

        project_data["identifier"] = request.form.get("identifier", str(uuid_obj))
        project_data["public_visibility"] = request.form.get("public_visibility", False) == "on"
        project_data["description"] = request.form.get("description", "")
        colabs_raw = request.form.get("collaborators", "").splitlines()
        collaborators = []
        if len(colabs_raw) == 0:
            collaborators.append(session_info["user_uuid"])
        for collaborator in colabs_raw:
            try:
                uuid_colab = uuid.UUID(collaborator, version=4)
                collaborators.append(str(uuid_colab))
            except ValueError:
                pass
        project_data["collaborators"] = collaborators
        project_data["readme"] = request.form.get("readme", "")

        get_couch()["crab_projects"][str(uuid_obj)] = project_data

        response = make_response(redirect("/projects/" + str(uuid_obj), code=302))
        return response
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_pages.route("/projects/<raw_uuid>", methods=['GET'])
def project_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        md_template_string = markdown.markdown(
            project_data["readme"], extensions=[
                "markdown.extensions.extra",
                "markdown.extensions.codehilite",
                "markdown.extensions.sane_lists"
            ]
        )
        md_template_string = md_template_string.replace("<table>", "<table class=\"table table-hover\">")
        formatter = HtmlFormatter(style="emacs",full=True,cssclass="codehilite")
        css_string = formatter.get_style_defs()
        md_css_string = "<style>" + css_string + "</style>"
        md_template_string = md_template_string.replace("<div class=\"codehilite\">", "<div class=\"codehilite container p-2 my-3 border rounded\">")
        md_template_string = md_template_string.replace("<pre>", "<pre style=\"margin:0;\">")
        md_template = md_css_string + md_template_string

        deposits = []
        for deposit_id in project_data:
            if deposit_id in get_couch()["crab_deposits"]:
                deposits.append(get_couch()["crab_deposits"][deposit_id])

        via_project_string = urlsafe_b64encode(json.dumps({
                "remote_project": "/api/v1/projects/" + project_data["_id"] + "/via_annotation_project"
            }).encode("utf-8")).decode("utf-8")

        return render_template("project_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), project_data=project_data, project_readme=md_template, deposits=deposits, via_project_string=via_project_string, can_edit=can_edit(str(uuid_obj)))
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_pages.route("/projects", methods=['GET'])
def project_browse_screen():
    return render_template("projects.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@project_api.route("/api/v1/projects/<raw_uuid>/export", methods=["POST"])
def api_v1_export_project(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        export_uuid = str(uuid.uuid4())
        job_uuid = str(uuid.uuid4())

        name = request.form.get("export_name", "")
        if len(name) == 0:
            name = datetime.datetime.now().strftime("%Y-%m-%d")

        export_type_raw = request.form.get("export_type", "croissant")
        export_type = "CROISSANT"
        if export_type_raw  == "ecotaxa":
            export_type = "ECOTAXA"
        elif export_type_raw  == "ifdo":
            export_type = "IFDO"
        else:
            export_type = "CROISSANT"

        prefer_project = request.form.get("prefer_project", "off") == "on"

        s3_profile = request.form.get("s3_profile", None)
        export_md = {
                "identifier": name,
                "prefer_project": prefer_project,
                "export_type": export_type,
                "s3_profile": s3_profile
            }

        job_md = {
            "type": "EXPORT_PROJECT",
            "target_id": str(uuid_obj),
            "status": "PENDING",
            "progress": 0.0,
            "job_args": export_md
        }
        get_couch()["crab_jobs"][job_uuid] = job_md

        advertise_job(job_uuid)

        redirect_uri = request.args.get("redirect", "")
        view_job = request.args.get("view_job", "false") == "true"
        if view_job:
            redirect_uri = "/jobs/" + job_uuid
        if len(redirect_uri) > 0:
            return redirect(redirect_uri, code=302)
        else:
            return Response(json.dumps({
                "msg": "done",
                "export_id": export_uuid
                }), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_api.route("/api/v1/projects", methods=["POST", "GET"])
def api_v1_get_projects():
    raw_selector = json.dumps({})
    mango_selector = json.loads(raw_selector)
    raw_sort = json.dumps([{
            "creation_timestamp": "desc"
        }])
    mango_sort = json.loads(raw_sort)
    for sortby in mango_sort:
        for key in sortby:
            if not key in mango_selector:
                mango_selector[key] = {"$exists": True}
    page = int(request.form.get("page",request.args.get("page", 0)))
    limit = 12
    mango = {
            "selector": mango_selector,
            "fields": ["collaborators", "creation_timestamp", "_id", "identifier", "description", "deposits"],
            "skip": page * limit,
            "sort": mango_sort,
            "limit": limit
        }
    #            "sort": mango_sort,

    ret = requests.post(get_couch_base_uri() + "crab_projects/" + "_find", json=mango).json()
    return Response(json.dumps(ret), status=200, mimetype='application/json')

@project_api.route("/api/v1/projects/<raw_uuid>", methods=['GET'])
def api_v1_get_project(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        return Response(json.dumps(project_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
