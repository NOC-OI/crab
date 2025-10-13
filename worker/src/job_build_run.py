import couchbeans
import microtiff.ifcb
import microtiff.lisst_holo
from utils import get_couch_client, get_s3_client, get_s3_bucket_name, get_s3_bucket_uri, to_snake_case
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

class BuildRunJob:
    def __init__(self):
        pass

    def build_job(self, workspace_uuid):

        couch_client = get_couch_client()

        self.progress_func(0.1)

        workspace_info = couch_client.get_document("crab_workspaces", workspace_uuid)

        self.s3_profile = workspace_info["s3_profile"]

        last_push_time = time.time()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipper:
            with io.BytesIO() as img_fp:
                get_s3_client(snapshot_info["s3_profile"]).download_fileobj(get_s3_bucket_name(snapshot_info["s3_profile"]), image_path, img_fp)
                img_fp.seek(0)
                zipper.writestr(file_name, img_fp.read())

        self.progress_func(0.9)

        if not "packages" in snapshot_info:
            snapshot_info["packages"] = {}
        snapshot_info["packages"]["ifdo"] = {
                "path": "snapshots/" + snapshot_uuid + "/ifdo_package.zip",
                "s3_profile": self.s3_profile
            }
        couch_client.put_document("crab_workspaces", workspace_uuid, snapshot_info)


    def execute(self, job_md, progress_func):
        self.job_md = job_md
        self.progress_func = progress_func
        #print(json.dumps(job_md, indent=4))
        workspace_uuid = job_md["target_id"]

        #self.s3_profile = "default"
        #self.s3_profile = job_md["job_args"]["s3_profile"]


        patch = {}

        #if job_md["job_args"]["p_type"] == "IFDO":
        patch["images_processed"] = self.build_job(workspace_uuid)

        return patch
