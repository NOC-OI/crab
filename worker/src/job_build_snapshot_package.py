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
from datetime import datetime

class BuildSnapshotPackageJob:
    def __init__(self):
        pass

    def build_ifdo_package(self, snapshot_uuid):

        couch_client = get_couch_client()

        self.progress_func(0.1)

        snapshot_info = couch_client.get_document("crab_snapshots", snapshot_uuid)

        self.s3_profile = snapshot_info["s3_profile"]

        # minimal ifdo interpretation
        ifdo_metadata = {
                "image-set-header": {
                        "image-set-ifdo-version": "v2.1.0",
                        "image-set-uuid": snapshot_info["_id"],
                        "image-set-name": snapshot_info["identifier"],
                        "image-set-handle": "https://example.com"
                    },
                "image-set-items": {}
            }

        samples_len = len(snapshot_info["samples"])
        i = 0
        last_push_time = time.time()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipper:
            for sample_id in snapshot_info["samples"]:
                raw_format = snapshot_info["samples"][sample_id]["type"]["format"].split("/", 1)
                f_ext = "bin"
                m_type = None
                if raw_format[0] == "image":
                    if raw_format[1] == "tiff":
                        f_ext = "tiff"
                        m_type = "TIFF"
                file_name = sample_id + "." + f_ext
                ifdo_metadata["image-set-items"][file_name] = {
                        "image-uuid": sample_id,
                        "image-media-type": m_type
                    }
                image_path = "snapshots/" + snapshot_info["_id"] + "/raw_img/" + sample_id + "." + f_ext
                #infile_object = get_bucket_object(path=image_path)
                #infile_content = infile_object['Body'].read()
                #zipper.writestr(file_name, infile_content)

                with io.BytesIO() as img_fp:
                    get_s3_client(snapshot_info["s3_profile"]).download_fileobj(get_s3_bucket_name(snapshot_info["s3_profile"]), image_path, img_fp)
                    img_fp.seek(0)
                    zipper.writestr(file_name, img_fp.read())

                i += 1
                if (last_push_time + 5) < time.time():
                    last_push_time = time.time()
                    self.progress_func(0.1 + ((i/samples_len) * 0.8))


            zipper.writestr("ifdo.json", json.dumps(ifdo_metadata, indent=4))

        get_s3_client(self.s3_profile).put_object(Bucket=get_s3_bucket_name(self.s3_profile), Key="snapshots/" + snapshot_uuid + "/ifdo_package.zip", Body=zip_buffer.getvalue())

        self.progress_func(0.9)

        if not "packages" in snapshot_info:
            snapshot_info["packages"] = {}
        snapshot_info["packages"]["ifdo"] = {
                "path": "snapshots/" + snapshot_uuid + "/ifdo_package.zip",
                "s3_profile": get_s3_bucket_uri(self.s3_profile)
            }
        couch_client.put_document("crab_snapshots", snapshot_uuid, snapshot_info)

    def execute(self, job_md, progress_func):
        self.job_md = job_md
        self.progress_func = progress_func
        #print(json.dumps(job_md, indent=4))
        snapshot_uuid = job_md["target_id"]

        #self.s3_profile = "default"
        #self.s3_profile = job_md["job_args"]["s3_profile"]


        patch = {}

        if job_md["job_args"]["p_type"] == "IFDO":
            patch["samples_processed"] = self.build_ifdo_package(snapshot_uuid)

        return patch
