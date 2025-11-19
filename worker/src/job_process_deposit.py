import couchbeans
from crabdeposit import Deposit
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

class ProcessDepositJob:
    def __init__(self):
        pass

    def build_ifdo_package(self, snapshot_uuid):

        couch_client = get_couch_client()

        self.progress_func(0.1)
        workspace_info = couch_client.get_document("crab_workspaces", snapshot_uuid)
        self.s3_profile = snapshot_info["s3_profile"]

        #        with io.BytesIO() as img_fp:
        #            get_s3_client(snapshot_info["s3_profile"]).download_fileobj(get_s3_bucket_name(snapshot_info["s3_profile"]), image_path, img_fp)
        #            img_fp.seek(0)
        #            zipper.writestr(file_name, img_fp.read())

        self.progress_func(0.9)

        couch_client.put_document("crab_snapshots", snapshot_uuid, snapshot_info)

    def execute(self, job_md, progress_func):
        self.job_md = job_md
        self.progress_func = progress_func

        workspace_uuid = job_md["target_id"]


        patch = {}

        patch["workspaces_deleted"] = workspace_uuid

        return patch
