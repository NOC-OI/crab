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
import time
import uuid
from datetime import datetime

class RunApplyUploadProfileJob:
    def __init__(self):
        pass

    def raw_image_unpack(self, run_uuid, workdir, namelist, metadata_template = {}, generate_annotation_set_from_folder_structure = False):
        targets = []
        for in_file in namelist:
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".png" or in_file_s[1] == ".jpg" or in_file_s[1] == ".jpeg" or in_file_s[1] == ".tif" or in_file_s[1] == ".tiff":
                targets.append(in_file)

        targets = list(set(targets))

        couch_client = get_couch_client()

        #run_dblist = get_couch()["crab_runs"]
        #observation_dblist = get_couch()["crab_observations"]
        observations = []

        run_metadata = {}
        mapping = {}

        targets_len = len(targets)
        i = 0
        last_push_time = time.time()

        annotations = {}

        for target in targets:
            im = Image.open(workdir + "/" + target)
            observation_uuid = str(uuid.uuid4())
            ofn = "runs/" + run_uuid + "/" + observation_uuid + ".tiff"
            ifn = workdir + "/" + in_file + ".tiff"
            im.save(ifn)
            #get_bucket().upload_file(ifn, ofn)
            get_s3_client(self.s3_profile).upload_file(ifn, get_s3_bucket_name(self.s3_profile), ofn)
            #print(ofn)

            observation_raw_metadata = {
                    "filename": target
                }


            if generate_annotation_set_from_folder_structure:
                hierarchy = os.path.split(target)
                if len(hierarchy) > 1:
                    annotations[observation_uuid] = {
                            "global": {
                                    "category": hierarchy[-2],
                                    "hierarchy": hierarchy[:-1]
                                }
                        }

            for key in mapping:
                observation_transformed_metadata[mapping[key]] = observation_raw_metadata[key]

            observation_transformed_metadata = {}

            mode_to_bpp = {'1':1, 'L':8, 'P':8, 'RGB':24, 'RGBA':32, 'CMYK':32, 'YCbCr':24, 'I':32, 'F':32}

            observation_metadata = {
                "path": ofn,
                "s3_profile": self.s3_profile,
                "from_run": run_uuid,
                "type": {
                        "dimensions": 2,
                        "format": "image/tiff",
                        "channels": [
                                {
                                    "type": im.mode,
                                    "bit_depth": mode_to_bpp[im.mode]
                                }
                            ]
                    },
                "origin_tags": observation_raw_metadata,
                "tags": observation_transformed_metadata
            }
            couch_client.put_document("crab_observations", observation_uuid, observation_metadata)
            observations.append(observation_uuid)

            im.close()

            i += 1
            if (last_push_time + 5) < time.time():
                last_push_time = time.time()
                self.progress_func(i/targets_len)

        run_transformed_metadata = {}

        for key in mapping:
            run_transformed_metadata[mapping[key]] = run_metadata[key]

        current_unix_timestamp = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

        annotation_set_uuid = str(uuid.uuid4())

        annotation_set = {
                "basis": {
                        "type": "run",
                        "id": run_uuid,
                        "parent_sets": []
                    },
                "bind_id": "OBSERVATION",
                "created": current_unix_timestamp,
                "tags": annotations,
                "tag_format": {
                        "global": {
                            "category": "STRING",
                            "hierarchy": "ARRAY:STRING"
                        }
                    }
            }

        couch_client.put_document("crab_annotation_sets", annotation_set_uuid, annotation_set)

        metadata_template["origin_tags"] = run_metadata
        metadata_template["tags"] = run_transformed_metadata
        metadata_template["ingest_timestamp"] = current_unix_timestamp
        metadata_template["sensor"] = "RAW_IMAGE"
        metadata_template["observations"] = observations

        if generate_annotation_set_from_folder_structure:
            metadata_template["attached_annotation_sets"] = [annotation_set_uuid]

        couch_client.put_document("crab_runs", run_uuid, metadata_template)

        return {"observations": len(observations)}

    def lisst_holo_unpack(self, run_uuid, workdir, namelist, metadata_template = {}):
        targets = []
        for in_file in namelist:
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".pgm":
                targets.append(in_file_s[0])
        targets = list(set(targets))

        targets_len = len(targets)
        i = 0
        last_push_time = time.time()

        couch_client = get_couch_client()
        observations = []

        run_metadata = {}

        for target in targets:
            microtiff.lisst_holo.extract_image(workdir + "/" + target)

        mapping = {}

        for target in targets:
            ofn = "runs/" + run_uuid + "/" + target + ".tiff"
            #print(ofn)
            ifn = workdir + "/" + in_file
            get_s3_client(self.s3_profile).upload_file(ifn, get_s3_bucket_name(self.s3_profile), ofn)
            observation_uuid = str(uuid.uuid4())

            observation_raw_metadata = {}

            for key in mapping:
                observation_transformed_metadata[mapping[key]] = observation_raw_metadata[key]

            observation_transformed_metadata = {}

            observation_metadata = {
                "path": ofn,
                "s3_profile": self.s3_profile,
                "from_run": run_uuid,
                "type": {
                        "dimensions": 2,
                        "format": "image/tiff",
                        "channels": [
                                {
                                    "type": "L",
                                    "bit_depth": 8
                                }
                            ]
                    },
                "origin_tags": observation_raw_metadata,
                "tags": observation_transformed_metadata
            }
            couch_client.put_document("crab_observations", observation_uuid, observation_metadata)
            observations.append(observation_uuid)
            i += 1
            if (last_push_time + 5) < time.time():
                last_push_time = time.time()
                self.progress_func(i/targets_len)

        run_transformed_metadata = {}

        for key in mapping:
            run_transformed_metadata[mapping[key]] = run_metadata[key]

        current_unix_timestamp = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

        metadata_template["origin_tags"] = run_metadata
        metadata_template["tags"] = run_transformed_metadata
        metadata_template["ingest_timestamp"] = current_unix_timestamp
        metadata_template["sensor"] = "LISST_HOLO"
        metadata_template["observations"] = observations

        couch_client.put_document("crab_runs", run_uuid, metadata_template)

        return {"observations": len(observations)}

    def ifcb_unpack(self, run_uuid, workdir, namelist, metadata_template = {}):
        targets = []
        for in_file in os.listdir(workdir):
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".adc" or in_file_s[1] == ".hdr" or in_file_s[1] == ".roi":
                targets.append(in_file_s[0])
        targets = list(set(targets))


        #print(targets)
        run_metadata = None
        group_metadata = {}
        for target in targets:
            with open(workdir + "/" + target + ".hdr") as f:
                header_lines = f.readlines()
                extracted_metadata = microtiff.ifcb.header_file_to_dict(header_lines)
                filtered_metadata = {}
                for key in extracted_metadata:
                    filtered_metadata[to_snake_case(key)] = extracted_metadata[key]
                group_metadata[target] = filtered_metadata
                if run_metadata is None:
                    run_metadata = group_metadata[target].copy()
                for gmk in group_metadata[target]:
                    if not run_metadata[gmk] == group_metadata[target][gmk]:
                        run_metadata[gmk] = []
            microtiff.ifcb.extract_images(workdir + "/" + target)

        for group in group_metadata:
            for gmk in group_metadata[group]:
                #print(gmk)
                if type(run_metadata[gmk]) is list:
                    #print(group_metadata[group][gmk])
                    run_metadata[gmk].append(group_metadata[group][gmk])
                else:
                    group_metadata[group][gmk] = None
            group_metadata[group] = {k: v for k, v in group_metadata[group].items() if v is not None}
        run_metadata = {k: v for k, v in run_metadata.items() if v is not None}

        couch_client = get_couch_client()
        observations = []

        mapping = {
                "software_version": "source_software",
                "analog_firmware_version": "firmware_version",
                "sample_time": "observation_time",
                "imager_id": "vendor_issued_hardware_id"
            }

        targets_len = len(os.listdir(workdir))
        i = 0
        last_push_time = time.time()

        for in_file in os.listdir(workdir):
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".tiff":
                base_group = in_file_s[0].split("_TN")[0]
                ofn = "runs/" + run_uuid + "/" + in_file_s[0] + ".tiff"
                get_s3_client(self.s3_profile).upload_file(workdir + "/" + in_file, get_s3_bucket_name(self.s3_profile), ofn)
                observation_uuid = str(uuid.uuid4())

                observation_transformed_metadata = {}
                for key in mapping:
                    if key in group_metadata:
                        observation_transformed_metadata[mapping[key]] = group_metadata[base_group][key]

                observation_metadata = {
                    "path": ofn,
                    "s3_profile": self.s3_profile,
                    "from_run": run_uuid,
                    "type": {
                            "dimensions": 2,
                            "format": "image/tiff",
                            "channels": [
                                    {
                                        "type": "L",
                                        "bit_depth": 8
                                    }
                                ]
                        },
                    "tags": observation_transformed_metadata,
                    "origin_tags": group_metadata[base_group].copy()
                }
                couch_client.put_document("crab_observations", observation_uuid, observation_metadata)
                observations.append(observation_uuid)
                i += 1
                if (last_push_time + 5) < time.time():
                    last_push_time = time.time()
                    self.progress_func(i/targets_len)

        run_transformed_metadata = {}

        for key in mapping:
            run_transformed_metadata[mapping[key]] = run_metadata[key]

        current_unix_timestamp = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()

        metadata_template["origin_tags"] = run_metadata
        metadata_template["tags"] = run_transformed_metadata
        metadata_template["ingest_timestamp"] = current_unix_timestamp
        metadata_template["sensor"] = "MCLANE_IFCB"
        metadata_template["observations"] = observations

        couch_client.put_document("crab_runs", run_uuid, metadata_template)

        return {"observations": len(observations)}

    def execute(self, job_md, progress_func):
        self.job_md = job_md
        self.progress_func = progress_func
        #print(json.dumps(job_md, indent=4))
        profile = job_md["job_args"]["profile"]
        metadata_template = job_md["job_args"]["input_md"]
        run_uuid = job_md["target_id"]

        self.s3_profile = job_md["job_args"]["s3_profile"]

        patch = {}

        with tempfile.TemporaryDirectory() as workdir:
            namelist = None

            with io.BytesIO() as zip_fp:
                get_s3_client(self.s3_profile).download_fileobj(get_s3_bucket_name(self.s3_profile), "raw_uploads/" + run_uuid + ".zip", zip_fp)
                with zipfile.ZipFile(zip_fp) as zipf:
                    namelist = zipf.namelist()
                    zipf.extractall(workdir)

            if profile == "IFCB":
                patch["unpacker_output"] = self.ifcb_unpack(run_uuid, workdir, namelist, metadata_template)
            elif profile == "LISST_HOLO":
                patch["unpacker_output"] = self.lisst_holo_unpack(run_uuid, workdir, namelist, metadata_template)
            elif profile == "PRE_CLASSIFIED":
                patch["unpacker_output"] = self.raw_image_unpack(run_uuid, workdir, namelist, metadata_template, True)
            else:
                patch["unpacker_output"] = self.raw_image_unpack(run_uuid, workdir, namelist, metadata_template)

        return patch
