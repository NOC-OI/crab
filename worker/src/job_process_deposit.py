import couchbeans
import crabdeposit
from crabdeposit import Deposit, DepositFile
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
import re
import io
import csv
from datetime import datetime
import pyarrow
import pyarrow.parquet
import pyarrow.compute

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
        other_data_file_names = []

        couch_client = get_couch_client()
        workspace_info = couch_client.get_document("crab_workspaces", workspace_uuid)
        #print(json.dumps(workspace_info, indent=4))
        for file_name in workspace_info["files"].keys():
            if file_name.endswith(".parquet"):
                parquet_file_names.append(file_name)
            else:
                other_data_file_names.append(file_name)

        #print(json.dumps(parquet_file_names, indent=4))

        self.progress_func(0.1)

        s3_profile = workspace_info["s3_profile"]
        s3_client = get_s3_client(s3_profile)
        s3_fs = get_s3_fs(s3_profile)
        s3_bucket = get_s3_bucket_name(s3_profile)
        crab_deposit = Deposit()

        parquet_file_info_collection = []

        for parquet_file_name in parquet_file_names:
            file_def = workspace_info["files"][parquet_file_name]
            file_path = s3_bucket + "/" + file_def["path"]
            deposit_file = DepositFile(pyarrow.parquet.ParquetFile(file_path, filesystem=s3_fs))
            crab_deposit.add_deposit_file(deposit_file)
            parquet_file_info_collection.append({
                    "origin_file_def": file_def,
                    "origin_file_path": file_path,
                    "original_file_name": parquet_file_name,
                    "deposit_file_uuid": str(uuid.uuid4()),
                    "deposit_file": deposit_file
                })


        self.progress_func(0.2)

        related_udts = crab_deposit.get_all_compact_udts()
        patch["related_nse_udts"] = related_udts

        self.progress_func(0.3)

        #for parquet_file_name in parquet_file_names:
        #    fh_map[parquet_file_name].close()

        self.progress_func(0.9)

        deposit_uuid = str(uuid.uuid4())
        deposit_info = {
                "related_nse_udts": related_udts,
                "data_files": [],
                "annotation_files": [],
                "source_files": [],
                "s3_profile": s3_profile,
                "public_visibility": True,
                "owners": []
            }

        for parquet_file_info in parquet_file_info_collection:
            df_type = parquet_file_info["deposit_file"].get_type()
            df_def = {
                    "origin_filename": parquet_file_info["original_file_name"]
                }
            if df_type == "DATA":
                output_key = "deposits/" + deposit_uuid + "/data/" + parquet_file_info["deposit_file_uuid"] + ".parquet"
                df_def["contains_nse_udts"] = parquet_file_info["deposit_file"].get_nse_udts()
                deposit_info["data_files"].append(df_def)
            elif df_type == "ANNOTATION":
                output_key = "deposits/" + deposit_uuid + "/annotation/" + parquet_file_info["deposit_file_uuid"] + ".parquet"
                df_def["references_nse_udts"] = parquet_file_info["deposit_file"].get_nse_udts()
                deposit_info["annotation_files"].append(df_def)

            df_def["s3_location"] = output_key
            s3_client.copy({"Bucket": s3_bucket, "Key": parquet_file_info["origin_file_def"]["path"]}, s3_bucket, output_key)

        for other_data_file_name in other_data_file_names:
            file_def = workspace_info["files"][other_data_file_name]
            sanitized_filename = re.sub("[^\\w\\s\\./-]", "", other_data_file_name)
            sanitized_filename = re.sub("^/+", "", sanitized_filename)
            sanitized_filename = re.sub("\\.+/", "", sanitized_filename).strip()
            output_key = "deposits/" + deposit_uuid + "/source/" + sanitized_filename
            df_def = {
                    "origin_filename": other_data_file_name,
                    "sanitized_filename": sanitized_filename,
                    "s3_location": output_key
                }
            deposit_info["source_files"].append(df_def)
            s3_client.copy({"Bucket": s3_bucket, "Key": file_def["path"]}, s3_bucket, output_key)


        couch_client.put_document("crab_deposits", deposit_uuid, deposit_info)

        patch["workspace_deleted"] = workspace_uuid
        patch["deposit_uuid"] = deposit_uuid
        patch["deposit_info"] = deposit_info

        self.progress_func(1)

        return patch
