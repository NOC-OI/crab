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

class TakeSnapshotJob:
    def __init__(self):
        pass

    def build_collection_snapshot(self, snapshot_uuid, snapshot_md):

        #print(json.dumps(get_couch()["crab_jobs"][job_uuid]))

        #current_job_md = get_couch()["crab_jobs"][job_uuid]
        #current_job_md["status"] = "ACTIVE"
        #current_job_md["progress"] = 0
        #get_couch()["crab_jobs"][job_uuid] = current_job_md

        couch_client = get_couch_client()

        self.progress_func(0)

        collection_info = couch_client.get_document("crab_collections", snapshot_md["collection"])

        creators = []
        creator_map = {}
        observations = []
        metadata_map = {}

        raw_metadata_run_heap = {}
        raw_metadata_observation_heap = {}
        raw_origin_metadata_run_heap = {}
        raw_origin_metadata_observation_heap = {}

        collection_global_metadata = {}
        residual_global_metadata = {}
        residual_run_metadata = {}
        residual_observation_metadata = {}
        collection_global_origin_metadata = {}
        residual_global_origin_metadata = {}
        residual_run_origin_metadata = {}
        residual_observation_origin_metadata = {}

        full_observation_metadata_heap = {}

        #run_info = []
        for run_id in collection_info["runs"]:
            #run_info = get_couch()["crab_runs"][run_id]
            run_info = couch_client.get_document("crab_runs", run_id)
            for observation_id in run_info["observations"]:
                observations.append(observation_id)
                creators.append(run_info["creator"]["uuid"])
                metadata_map[observation_id] = {
                        "creator": run_info["creator"],
                        "sensor": run_info["sensor"],
                        "from_run": run_id,
                        "ingest_timestamp": run_info["ingest_timestamp"]
                    }
                #observation_info = get_couch()["crab_observations"][observation_id]
                observation_info = couch_client.get_document("crab_observations", observation_id)
                #print(json.dumps(observation_info, indent=4))
                if not "tags" in observation_info:
                    observation_info["tags"] = {}

                raw_origin_metadata_observation_heap[observation_id] = observation_info["origin_tags"]
                raw_metadata_observation_heap[observation_id] = observation_info["tags"]
                full_observation_metadata_heap[observation_id] = observation_info
                residual_observation_origin_metadata[observation_id] = {}
                residual_observation_metadata[observation_id] = {}
            raw_origin_metadata_run_heap[run_id] = run_info["origin_tags"]
            raw_metadata_run_heap[run_id] = run_info["tags"]
            residual_run_origin_metadata[run_id] = {}
            residual_run_metadata[run_id] = {}
            #print(json.dumps(run_info, indent=4))

        self.progress_func(0.1)

        for run_id in raw_metadata_run_heap:
            for key in raw_metadata_run_heap[run_id]:
                value = raw_metadata_run_heap[run_id][key]
                #if not type(value) is list:
                if key in collection_global_metadata:
                    if not value in collection_global_metadata[key]:
                        collection_global_metadata[key].append(value)
                else:
                    collection_global_metadata[key] = [value]

        for run_id in raw_origin_metadata_run_heap:
            for key in raw_origin_metadata_run_heap[run_id]:
                value = raw_origin_metadata_run_heap[run_id][key]
                #if not type(value) is list:
                if key in collection_global_origin_metadata:
                    if not value in collection_global_origin_metadata[key]:
                        collection_global_origin_metadata[key].append(value)
                else:
                    collection_global_origin_metadata[key] = [value]


        for observation_id in raw_metadata_observation_heap:
            for key in raw_metadata_observation_heap[observation_id]:
                value = raw_metadata_observation_heap[observation_id][key]
                if not type(value) is list:
                    if key in collection_global_metadata:
                        if not value in collection_global_metadata[key]:
                            collection_global_metadata[key].append(value)
                    else:
                        collection_global_metadata[key] = [value]

        for observation_id in raw_origin_metadata_observation_heap:
            for key in raw_origin_metadata_observation_heap[observation_id]:
                value = raw_origin_metadata_observation_heap[observation_id][key]
                if not type(value) is list:
                    if key in collection_global_origin_metadata:
                        if not value in collection_global_origin_metadata[key]:
                            collection_global_origin_metadata[key].append(value)
                    else:
                        collection_global_origin_metadata[key] = [value]


        for key in collection_global_metadata:
            if len(collection_global_metadata[key]) > 1:
                for run_id in collection_info["runs"]:
                    if not type(raw_metadata_run_heap[run_id][key]) is list:
                        residual_run_metadata[run_id][key] = raw_metadata_run_heap[run_id][key]
            else:
                if not type(collection_global_metadata[key][0]) is list:
                    residual_global_metadata[key] = collection_global_metadata[key][0]

        for key in collection_global_origin_metadata:
            if len(collection_global_origin_metadata[key]) > 1:
                for run_id in collection_info["runs"]:
                    if not type(raw_origin_metadata_run_heap[run_id][key]) is list:
                        residual_run_origin_metadata[run_id][key] = raw_origin_metadata_run_heap[run_id][key]
            else:
                if not type(collection_global_origin_metadata[key][0]) is list:
                    residual_global_origin_metadata[key] = collection_global_origin_metadata[key][0]

        #print(json.dumps(residual_run_origin_metadata, indent=4))

        for run_id in residual_run_origin_metadata:
            #run_observations = get_couch()["crab_runs"][run_id]["observations"]
            run_observations = couch_client.get_document("crab_runs", run_id)["observations"]
            for observation_id in run_observations:
                residual_observation_metadata[observation_id] = residual_run_metadata[run_id]
                residual_observation_origin_metadata[observation_id] = residual_run_origin_metadata[run_id]

        for observation_id in observations:
            for key in raw_metadata_observation_heap[observation_id]:
                residual_observation_metadata[observation_id][key] = raw_metadata_observation_heap[observation_id][key]
            for key in raw_origin_metadata_observation_heap[observation_id]:
                residual_observation_origin_metadata[observation_id][key] = raw_origin_metadata_observation_heap[observation_id][key]

        #print(json.dumps(residual_observation_origin_metadata, indent=4))
        #print(json.dumps(residual_global_origin_metadata, indent=4))

        snapshot_md["observations"] = {}

        for observation_id in observations:
            snapshot_md["observations"][observation_id] = residual_observation_metadata[observation_id]
            snapshot_md["observations"][observation_id]["origin_tags"] = residual_observation_origin_metadata[observation_id]
            snapshot_md["observations"][observation_id]["type"] = full_observation_metadata_heap[observation_id]["type"]
            snapshot_md["observations"][observation_id]["from_run"] = metadata_map[observation_id]["from_run"]

        for key in residual_global_metadata:
            snapshot_md[key] = residual_global_metadata[key]
        snapshot_md["origin_tags"] = residual_global_origin_metadata

        #print(json.dumps(snapshot_md, indent=4))

        #current_job_md = get_couch()["crab_jobs"][job_uuid]
        #current_job_md["progress"] = 0.3
        #get_couch()["crab_jobs"][job_uuid] = current_job_md

        self.progress_func(0.2)



        #current_job_md = get_couch()["crab_jobs"][job_uuid]
        #current_job_md["progress"] = 0.6
        #get_couch()["crab_jobs"][job_uuid] = current_job_md


        observations_len = len(observations)
        i = 0
        last_push_time = time.time()

        for run_id in collection_info["runs"]:
            run_info = couch_client.get_document("crab_runs", run_id)#get_couch()["crab_runs"][run_id]
            for observation_id in run_info["observations"]:
                observation_info = couch_client.get_document("crab_observations", observation_id) #get_couch()["crab_observations"][observation_id]
                if "path" in observation_info:
                    #get_s3_client(self.s3_profile).copy_object(Bucket=get_s3_bucket_name(self.s3_profile), CopySource="/" + get_s3_bucket_name(self.s3_profile) + "/" + observation_info["path"], Key="snapshots/" + snapshot_uuid + "/raw_img/" + observation_id + ".tiff")
                    file_name, file_ext = os.path.splitext(observation_info["path"])

                    with io.BytesIO() as temp_file:
                        get_s3_client(observation_info["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_info["s3_profile"]), observation_info["path"], temp_file)
                        temp_file.seek(0)
                        get_s3_client(self.s3_profile).put_object(Bucket=get_s3_bucket_name(self.s3_profile), Key="snapshots/" + snapshot_uuid + "/raw_img/" + observation_id + file_ext, Body=temp_file.read())
                else:
                    print("Broken observation!:")
                    print(observation_info)

                i += 1
                if (last_push_time + 5) < time.time():
                    last_push_time = time.time()
                    self.progress_func(0.2 + ((i/observations_len) * 0.3))

        self.progress_func(0.5)
        i = 0

        zip_buffer = io.BytesIO()
        image_type = "image/tiff"
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipper:
            for observation_id in snapshot_md["observations"]:
                raw_format = snapshot_md["observations"][observation_id]["type"]["format"].split("/", 1)
                f_ext = "bin"
                m_type = None
                image_type = raw_format[0] + "/" + raw_format[1]
                if raw_format[0] == "image":
                    if raw_format[1] == "tiff":
                        f_ext = "tiff"
                        m_type = "TIFF"
                file_name = observation_id + "." + f_ext
                image_path = "snapshots/" + snapshot_uuid + "/raw_img/" + observation_id + "." + f_ext
                #infile_object = get_bucket_object(path=image_path)
                #infile_content = infile_object['Body'].read()
                #zipper.writestr(file_name, infile_content)
                with io.BytesIO() as img_fp:
                    get_s3_client(self.s3_profile).download_fileobj(get_s3_bucket_name(self.s3_profile), image_path, img_fp)
                    img_fp.seek(0)
                    zipper.writestr(file_name, img_fp.read())

                i += 1
                if (last_push_time + 5) < time.time():
                    last_push_time = time.time()
                    self.progress_func(0.5 + ((i/observations_len) * 0.3))

            self.progress_func(0.8)

            zipper.writestr("metadata.json", json.dumps(snapshot_md, indent=4))

        get_s3_client(self.s3_profile).put_object(Bucket=get_s3_bucket_name(self.s3_profile), Key="snapshots/" + snapshot_uuid + "/tiff_bundle.zip", Body=zip_buffer.getvalue())

        sha256 = hashlib.sha256()
        BUF_SIZE = 65536 # 64kb
        zip_buffer.seek(0)

        while True:
            data = zip_buffer.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)

        snapshot_md["bundle"] = {
                "type": "application/zip",
                "image_type": image_type,
                "path": "snapshots/" + snapshot_uuid + "/tiff_bundle.zip",
                "sha256": sha256.hexdigest(),
                "host": get_s3_bucket_uri(self.s3_profile)
            }

        self.progress_func(0.9)

        with io.BytesIO(json.dumps(snapshot_md, indent=4).encode()) as f:
            get_s3_client(self.s3_profile).upload_fileobj(f, get_s3_bucket_name(self.s3_profile), "snapshots/" + snapshot_uuid + "/crab_metadata.json")
        #get_couch()["crab_snapshots"][snapshot_uuid] = snapshot_md
        couch_client.put_document("crab_snapshots", snapshot_uuid, snapshot_md)

        current_collection_md = couch_client.get_document("crab_collections", collection_info["_id"]) #get_couch()["crab_collections"][collection_info["_id"]]
        if not "snapshots" in current_collection_md:
            current_collection_md["snapshots"] = []
        current_collection_md["snapshots"].append(snapshot_uuid)
        couch_client.put_document("crab_collections", collection_info["_id"], current_collection_md)

        self.progress_func(1)

        return observations_len

    def execute(self, job_md, progress_func):
        self.job_md = job_md
        self.progress_func = progress_func
        #print(json.dumps(job_md, indent=4))
        snapshot_uuid = job_md["target_id"]

        #self.s3_profile = "default"
        self.s3_profile = job_md["job_args"]["s3_profile"]

        patch = {}

        patch["observations_processed"] = self.build_collection_snapshot(snapshot_uuid, job_md["job_args"])


        return patch
