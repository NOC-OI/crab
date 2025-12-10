import couchbeans
from crabdeposit import Deposit
from utils import get_couch_client, get_s3_client, get_s3_bucket_name, get_s3_bucket_uri, to_snake_case, get_s3_fs
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
import crabdeposit
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

        parquet_file_names = []

        couch_client = get_couch_client()
        workspace_info = couch_client.get_document("crab_workspaces", workspace_uuid)
        #print(json.dumps(workspace_info, indent=4))
        for file_name in workspace_info["files"].keys():
            if file_name.endswith(".parquet"):
                parquet_file_names.append(file_name)

        #print(json.dumps(parquet_file_names, indent=4))


        fs_map = {}
        parquet_filesystems = []
        parquet_s3_paths = []

        for parquet_file_name in parquet_file_names:
            file_def = workspace_info["files"][parquet_file_name]
            if file_def["s3_profile"] not in fs_map.keys():
                fs_map[file_def["s3_profile"]] = get_s3_fs(file_def["s3_profile"])
            parquet_filesystems.append(fs_map[file_def["s3_profile"]])
            parquet_s3_paths.append(get_s3_bucket_name(file_def["s3_profile"]) + "/" + file_def["path"])

        crab_deposit = Deposit()
        crab_deposit.set_deposit_files(parquet_s3_paths, parquet_filesystems)

        udts = crab_deposit.get_all_compact_udts()

        print(udts)

        #for parquet_file_name in parquet_file_names:
        #    fh_map[parquet_file_name].close()

        patch["related_udts"] = udts

        patch["workspace_deleted"] = workspace_uuid

        return patch
