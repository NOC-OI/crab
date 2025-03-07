from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
from datetime import datetime
from multiprocessing import Process
import io
import os
import jwt
import zipfile
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case, get_crab_external_endpoint, get_csrf_secret_key
from db import get_couch, get_couch_base_uri, get_bucket_object, get_s3_client, get_bucket_name, get_couch_client, advertise_job, get_s3_bucket_name, get_s3_client, get_s3_profile, get_s3_bucket_ext_uri

export_pages = Blueprint("export_pages", __name__)
export_api = Blueprint("export_api", __name__)

csrf_secret_key = get_csrf_secret_key()


def can_view(export_uuid):
    session_info = get_session_info()
    export_data = get_couch()["crab_exports"][export_uuid]
    project_data = get_couch()["crab_projects"][export_data["project"]]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return project_data["public_visibility"]

def can_edit(export_uuid):
    session_info = get_session_info()
    export_data = get_couch()["crab_exports"][export_uuid]
    project_data = get_couch()["crab_projects"][export_data["project"]]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return False

@export_api.route("/api/v1/exports/<export_uuid>/image_bundle.zip", methods=['GET'])
def api_v1_export_download_zip(export_uuid):

    try:
        uuid_obj = uuid.UUID(export_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        export_data = get_couch()["crab_exports"][str(uuid_obj)]
        s3_path = export_data["image_bundle"]["path"]
        s3_profile = export_data["image_bundle"]["s3_profile"]
        #temp_file = get_bucket_object(path=s3path)
        #return Response(
        #    temp_file['Body'].read(),
        #    mimetype="application/zip",
        #    headers={"Content-Disposition": "attachment;filename=" + os.path.basename(s3path)}
        #    )
        with io.BytesIO() as in_temp_file:
            get_s3_client(s3_profile).download_fileobj(get_s3_bucket_name(s3_profile), s3_path, in_temp_file)
            in_temp_file.seek(0)

            return Response(
                in_temp_file.read(),
                mimetype="application/zip",
                headers={"Content-Disposition": "attachment;filename=" + os.path.basename(s3_path)}
                )
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + export_uuid
            }), status=400, mimetype='application/json')

@export_api.route("/api/v1/exports/<export_uuid>/annotations.csv", methods=['GET'])
def api_v1_export_download_csv(export_uuid):

    try:
        uuid_obj = uuid.UUID(export_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        export_data = get_couch()["crab_exports"][str(uuid_obj)]
        s3_path = export_data["annotations"]["path"]
        s3_profile = export_data["annotations"]["s3_profile"]
        #temp_file = get_bucket_object(path=s3path)
        #return Response(
        #    temp_file['Body'].read(),
        #    mimetype="application/zip",
        #    headers={"Content-Disposition": "attachment;filename=" + os.path.basename(s3path)}
        #    )
        with io.BytesIO() as in_temp_file:
            get_s3_client(s3_profile).download_fileobj(get_s3_bucket_name(s3_profile), s3_path, in_temp_file)
            in_temp_file.seek(0)

            return Response(
                in_temp_file.read(),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=" + os.path.basename(s3_path)}
                )
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + export_uuid
            }), status=400, mimetype='application/json')

@export_api.route("/api/v1/exports/<export_uuid>", methods=['GET'])
def api_v1_get_export(export_uuid):
    try:
        uuid_obj = uuid.UUID(export_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        export_data = get_couch()["crab_exports"][str(uuid_obj)]
        return Response(json.dumps(export_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + export_uuid
            }), status=400, mimetype='application/json')

@export_api.route("/api/v1/exports/<export_uuid>/croissant", methods=['GET'])
def api_v1_get_export_croissant(export_uuid):
    try:
        uuid_obj = uuid.UUID(export_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        export_data = get_couch()["crab_exports"][str(uuid_obj)]
        project_data = get_couch()["crab_projects"][export_data["project"]]

        croissant_data = {
                "@context": {
                    "@language": "en",
                    "@vocab": "https://schema.org/",
                    "citeAs": "cr:citeAs",
                    "column": "cr:column",
                    "conformsTo": "dct:conformsTo",
                    "cr": "http://mlcommons.org/croissant/",
                    "rai": "http://mlcommons.org/croissant/RAI/",
                    "data": {
                        "@id": "cr:data",
                        "@type": "@json"
                    },
                    "dataType": {
                        "@id": "cr:dataType",
                        "@type": "@vocab"
                    },
                    "dct": "http://purl.org/dc/terms/",
                    "examples": {
                        "@id": "cr:examples",
                        "@type": "@json"
                    },
                    "extract": "cr:extract",
                    "field": "cr:field",
                    "fileProperty": "cr:fileProperty",
                    "fileObject": "cr:fileObject",
                    "fileSet": "cr:fileSet",
                    "format": "cr:format",
                    "includes": "cr:includes",
                    "isLiveDataset": "cr:isLiveDataset",
                    "jsonPath": "cr:jsonPath",
                    "key": "cr:key",
                    "md5": "cr:md5",
                    "parentField": "cr:parentField",
                    "path": "cr:path",
                    "recordSet": "cr:recordSet",
                    "references": "cr:references",
                    "regex": "cr:regex",
                    "repeated": "cr:repeated",
                    "replace": "cr:replace",
                    "sc": "https://schema.org/",
                    "separator": "cr:separator",
                    "source": "cr:source",
                    "subField": "cr:subField",
                    "transform": "cr:transform"
                },
                "@type": "sc:Dataset",
                "name": to_snake_case(project_data["identifier"]) + "_" + export_data["identifier"],
                "description": project_data["description"],
                "distribution": [],
                "recordSet": export_data["croissant_template"]["recordSet"],
                "creators": export_data["croissant_template"]["creators"],
                "conformsTo": "http://mlcommons.org/croissant/1.0",
                "url": get_crab_external_endpoint() + "projects/" + project_data["_id"]
            }


        content_uri = get_crab_external_endpoint() + "api/v1/exports/" + export_data["_id"] + "/image_bundle.zip"
        s3_profile_info = get_s3_profile(export_data["image_bundle"]["s3_profile"])
        if "public" in s3_profile_info:
            if s3_profile_info["public"]:
                content_uri = get_s3_bucket_ext_uri(export_data["image_bundle"]["s3_profile"]) + "/" + export_data["image_bundle"]["path"]

        croissant_data["distribution"].append({
                "@type": "cr:FileObject",
                "@id": "all-tiffs",
                "description": "A ZIP archive containing the dataset.",
                "contentUrl": content_uri,
                "sha256": export_data["image_bundle"]["sha256"],
                "encodingFormat": "application/zip"
            })


        content_uri = get_crab_external_endpoint() + "api/v1/exports/" + export_data["_id"] + "/annotations.csv"
        s3_profile_info = get_s3_profile(export_data["annotations"]["s3_profile"])
        if "public" in s3_profile_info:
            if s3_profile_info["public"]:
                content_uri = get_s3_bucket_ext_uri(export_data["annotations"]["s3_profile"]) + "/" + export_data["annotations"]["path"]

        croissant_data["distribution"].append({
                "@type": "cr:FileObject",
                "@id": "annotations",
                "description": "A CSV file containing all whole-frame annotations.",
                "contentUrl": content_uri,
                "sha256": export_data["annotations"]["sha256"],
                "encodingFormat": "text/csv"
            })

        croissant_data["distribution"].append({
                "@type": "cr:FileSet",
                "@id": "tiff-set",
                "description": "TIFF images of dataset",
                "containedIn": {"@id": "all-tiffs"},
                "encodingFormat": "image/tiff",
                "includes": "*.tiff"
            })

        # REF: https://github.com/mlcommons/croissant/issues/651

        return Response(json.dumps(croissant_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + export_uuid
            }), status=400, mimetype='application/json')




@export_api.route("/api/v1/exports/<export_uuid>/makepkg/<package_type>", methods=["GET"])
def api_v1_create_export(export_uuid, package_type):
    """
    Creates a new async package build job
    ---
    tags:
        - Snapshots
    parameters:
        - name: export_uuid
          in: path
          type: string
          required: true

        - name: package_type
          in: path
          type: string
          enum: ["ifdo", "croissant"]
          required: true

    produces:
        - application/json

    description: Creates a new async package build job
    responses:
        200:
            description: Job has been successfully created
            examples:
                application/json:
                    job_id:
                        052ea60f-2bda-4958-9ec4-39a475e4cd45
        401:
            description: User does not have write permissions for the parent project
        400:
            description: Invalid package type
    """
    p_type = package_type.lower()
    try:
        uuid_obj = uuid.UUID(export_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        export_data = get_couch()["crab_exports"][str(uuid_obj)]
        job_uuid = uuid.uuid4()
        job_md = {
                "type": "BUILD_SNAPSHOT_PACKAGE",
                "target_id": str(uuid_obj),
                "status": "PENDING",
                "progress": 0.0
            }
        if export_data is None:
            return Response(json.dumps({
                "error": "exportNotFound",
                "msg": "Could not find export with id {" + str(uuid_obj) + "}"
                }), status=404, mimetype='application/json')
        else:
            if p_type == "ifdo":
                #proc = Process(target=build_ifdo_package, args=(str(job_uuid), str(uuid_obj), export_data))
                #proc.start()
                job_md["job_args"] = {
                        "p_type": "IFDO"
                    }
            elif p_type == "ecotaxa":
                #proc = Process(target=build_ifdo_package, args=(str(job_uuid), str(uuid_obj), export_data))
                #proc.start()
                job_md["job_args"] = {
                        "p_type": "ECOTAXA"
                    }
            else:
                return Response(json.dumps({
                    "error": "badExportType",
                    "msg": "Could not make package with type \"" + p_type + "\""
                    }), status=400, mimetype='application/json')

            get_couch_client().put_document("crab_jobs", str(job_uuid), job_md)
            advertise_job(str(job_uuid))
            #get_couch()["crab_exports"][str(uuid_obj)] = export_data
            return Response(json.dumps({
                "job_id": str(job_uuid)
                }), status=200, mimetype='application/json')
            #args": request.form.to_dict(),
    except ValueError as e:
        print(e)

        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + export_uuid
            }), status=400, mimetype='application/json')
