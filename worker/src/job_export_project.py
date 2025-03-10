import couchbeans
import microtiff.ifcb
import microtiff.lisst_holo
from utils import get_couch_client, get_s3_client, get_s3_bucket_name, get_s3_bucket_uri, to_snake_case, get_s3_bucket_ext_uri
from PIL import Image
import zipfile
import tempfile
import json
import io
import os
import hashlib
import time
import uuid
import io
import csv
from datetime import datetime

def snake_case_to_camel(s1):
    s2 = s1.split('_')
    return s2[0] + ''.join(word.capitalize() for word in s2[1:])

class ExportProjectJob:
    def __init__(self):
        pass

    def build_croissant_package(self, project_uuid):
        couch_client = get_couch_client()
        export_log = []

        self.progress_func(0)

        project_info = couch_client.get_document("crab_projects", project_uuid)
        #print(json.dumps(project_info, indent=2))

        collections_info = []

        ps_croissant_data = {}

        annotation_set_ids = []
        project_annotation_set_ids = []
        run_annotation_set_ids = []
        all_observation_ids = []

        project_annotations_by_obs = {}
        project_annotations_by_area = {}
        annotation_categories_by_obs = set()
        annotation_categories_by_area = set()

        collaborators = []

        for collaborator_id in project_info["collaborators"]:
            collaborator_data = couch_client.get_document("crab_users", collaborator_id)

            collaborator = {
                    "@type": "sc:Person",
                    "name": collaborator_data["name"],
                    "email": collaborator_data["email"]
                }
            collaborators.append(collaborator)

        ps_croissant_data["creators"] = collaborators

        for collection_id in project_info["collections"]:
            collection_info = couch_client.get_document("crab_collections", collection_id)
            collections_info.append(collection_info)
            for run_id in collection_info["runs"]:
                run_info = couch_client.get_document("crab_runs", run_id)
                run_annotation_set_ids = run_annotation_set_ids + run_info["attached_annotation_sets"]
                all_observation_ids = all_observation_ids + run_info["observations"]

        if self.job_md["job_args"]["prefer_project"]:
            annotation_set_ids = run_annotation_set_ids + project_annotation_set_ids
        else:
            annotation_set_ids = project_annotation_set_ids + run_annotation_set_ids


        for annotation_set_id in annotation_set_ids:
            #print(annotation_set_id)
            annotation_set_info = couch_client.get_document("crab_annotation_sets", annotation_set_id)
            #print(json.dumps(annotation_set_info, indent=2))
            if annotation_set_info["bind_id"] == "OBSERVATION":
                for object_id in annotation_set_info["tags"]:
                    if "global" in annotation_set_info["tags"][object_id]:
                        project_annotations_by_obs[object_id] = annotation_set_info["tags"][object_id]["global"]
                        for tag_name in annotation_set_info["tags"][object_id]["global"]:
                            annotation_categories_by_obs.add(tag_name)


        observaion_mds = ""
        output_annot_categories = [snake_case_to_camel(category) for category in annotation_categories_by_obs]
        observation_annotation_io = io.StringIO()
        csvw = csv.writer(observation_annotation_io, delimiter=",", quotechar="\"", quoting=csv.QUOTE_MINIMAL)
        csvw.writerow(["observationId"] + output_annot_categories)
        for observation_id in all_observation_ids:
            csvrow = [observation_id]
            for tag_name in annotation_categories_by_obs:
                if tag_name in project_annotations_by_obs[observation_id]:
                    idata = project_annotations_by_obs[observation_id][tag_name]
                    if idata is list:
                        idata = json.dumps(idata)
                    csvrow.append(str(idata))
                else:
                    csvrow.append("")
            csvw.writerow(csvrow)

        fields = [
                    {
                        "@type": "cr:Field",
                        "@id": "image_uuid",
                        "name": "image_uuid",
                        "description": "The UUID of the image/observation.",
                        "dataType": "sc:Text",
                        "references": {
                            "fileObject": {
                                "@id": "annotations"
                            },
                            "extract": {
                                "column": "observationId"
                            }
                        },
                        "source": {
                            "fileSet": {
                                "@id": "tiff-set",
                            },
                            "extract": {
                                "fileProperty": "filename"
                            },
                            "transform": {
                                "regex": "([^\\/]*)\\.tiff"
                            }
                        }
                    },
                    {
                        "@type": "cr:Field",
                        "@id": "image_content",
                        "dataType": "sc:ImageObject",
                        "source": {
                            "fileSet": {
                                "@id": "tiff-set",
                            },
                            "extract": {
                                "fileProperty": "content"
                            }
                        }
                    }
                ]

        for fieldname in output_annot_categories:
            fields.append({
                    "@type": "cr:Field",
                    "@id": "image_" + fieldname,
                    "dataType": "sc:Text",
                    "source": {
                            "fileObject": {
                                "@id": "annotations"
                            },
                            "extract": {
                                "column": fieldname
                            }
                        }
                })

        ps_croissant_data["recordSet"] = [{
                "@type": "cr:RecordSet",
                "@id": "default",
                "key": {
                    "@id": "image_uuid"
                },
                "name": "default",
                "field": fields
            }]

        zip_buffer = io.BytesIO()
        image_type = "image/tiff"
        last_push_time = time.time()
        observations_len = len(all_observation_ids)
        i = 0
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipper:
            for observation_id in all_observation_ids:
                observation_info = couch_client.get_document("crab_observations", observation_id)
                with io.BytesIO() as img_fp:
                    get_s3_client(observation_info["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_info["s3_profile"]), observation_info["path"], img_fp)
                    file_name = observation_id + ".tiff"
                    img_fp.seek(0)
                    zipper.writestr(file_name, img_fp.read())

                i += 1
                if (last_push_time + 5) < time.time():
                    last_push_time = time.time()
                    self.progress_func(0.1 + ((i/observations_len) * 0.8))

            self.progress_func(0.9)

            zipper.writestr("annotations.csv", observaion_mds)

        export_uuid = str(uuid.uuid4())

        get_s3_client(self.s3_profile).put_object(Bucket=get_s3_bucket_name(self.s3_profile), Key="exports/" + export_uuid + "/image_bundle.zip", Body=zip_buffer.getvalue())


        observation_annotation_io.seek(0)
        get_s3_client(self.s3_profile).put_object(Bucket=get_s3_bucket_name(self.s3_profile), Key="exports/" + export_uuid + "/annotations.csv", Body=observation_annotation_io.getvalue().encode("utf-8"))

        BUF_SIZE = 65536 # 64kb
        sha256 = hashlib.sha256()
        zip_buffer.seek(0)

        while True:
            data = zip_buffer.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)

        image_bundle_sha = sha256.hexdigest()

        sha256 = hashlib.sha256()
        observation_annotation_io.seek(0)

        while True:
            data = observation_annotation_io.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data.encode("utf-8"))

        annotations_sha = sha256.hexdigest()

        export_md = {
                "identifier": self.job_md["job_args"]["identifier"],
                "image_bundle": {
                    "path": "exports/" + export_uuid + "/image_bundle.zip",
                    "contains": "image/tiff",
                    "format": "application/zip",
                    "sha256": image_bundle_sha,
                    "host": get_s3_bucket_ext_uri(self.s3_profile),
                    "s3_profile": self.s3_profile
                },
                "annotations": {
                    "path": "exports/" + export_uuid + "/annotations.csv",
                    "format": "text/csv",
                    "sha256": annotations_sha,
                    "host": get_s3_bucket_ext_uri(self.s3_profile),
                    "s3_profile": self.s3_profile
                },
                "croissant_template": ps_croissant_data,
                "project": project_uuid
            }

        self.progress_func(1)

        couch_client.put_document("crab_exports", export_uuid, export_md)

        return {
                "export_uuid": export_uuid
            }


    def execute(self, job_md, progress_func):
        self.job_md = job_md
        self.progress_func = progress_func
        #print(json.dumps(job_md, indent=4))
        project_uuid = job_md["target_id"]

        #self.s3_profile = "default"
        self.s3_profile = job_md["job_args"]["s3_profile"]


        patch = {}

        if job_md["job_args"]["export_type"] == "CROISSANT":
            patch["log"] = self.build_croissant_package(project_uuid)
       # elif job_md["job_args"]["export_type"] == "ECOTAXA":
        #    patch["observations_processed"] = self.build_ecotaxa_package(snapshot_uuid)

        return patch
