import argparse
import os
import json
import sys
from glob import glob

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from jobs_launcher.core.config import SESSION_REPORT, TEST_REPORT_NAME_COMPARED


KEYS_TO_COPY = ["min_server_latency", "max_server_latency"]


def get_test_status(latency):
    if latency > 0 and latency < 100:
        return "passed"
    elif latency >= 100 and latency < 300:
        return "failed"
    else:
        return "error"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--target_dir', required=True, metavar="<path>")
    parser.add_argument('--source_dir', required=True, metavar="<path>")

    args = parser.parse_args()

    for path, dirs, files in os.walk(os.path.abspath(args.target_dir)):
        for file in files:
            if file.endswith(TEST_REPORT_NAME_COMPARED):
                target_file_path = os.path.join(path, file) 

                source_file_path = os.path.join(args.source_dir, os.path.relpath(target_file_path, args.target_dir))

                if os.path.exists(source_file_path):
                    with open(target_file_path, "r") as f:
                        target_file_content = json.load(f)

                    with open(source_file_path, "r") as f:
                        source_file_content = json.load(f)

                    for i in range(len(target_file_content)):
                        for key in KEYS_TO_COPY:
                            if key in source_file_content[i]:
                                target_file_content[i][key] = source_file_content[i][key]

                        if "max_client_latency" in target_file_content[i] and "max_server_latency" in target_file_content[i]:
                            if target_file_content[i]["max_server_latency"] > target_file_content[i]["max_client_latency"] 
                                and target_file_content[i]["max_client_latency"] != 0:

                                target_file_content[i]["test_status"] = get_test_status(target_file_content[i]["max_server_latency"])

                    with open(target_file_path, "w", encoding="utf8") as f:
                        json.dump(target_file_content, f, indent=4, sort_keys=True)

            elif file.endswith(SESSION_REPORT):
                target_file_path = os.path.join(path, file) 

                source_file_path = os.path.join(args.source_dir, os.path.relpath(target_file_path, args.target_dir))

                if os.path.exists(source_file_path):
                    with open(target_file_path, "r") as f:
                        target_file_content = json.load(f)

                    with open(source_file_path, "r") as f:
                        source_file_content = json.load(f)

                    if "machine_info" in source_file_content:
                    	target_file_content["machine_info"] = source_file_content["machine_info"]

                    for test_group in target_file_content["results"]:
                        target_group_data = target_file_content["results"][test_group][""]
                        source_group_data = source_file_content["results"][test_group][""]

                        for i in range(len(target_group_data["render_results"])):
                            for key in KEYS_TO_COPY:
                                if key in source_group_data["render_results"][i]:
                                    target_group_data["render_results"][i][key] = source_group_data["render_results"][i][key]

                            if "max_client_latency" in target_group_data["render_results"][i] and "max_server_latency" in target_group_data["render_results"][i]:
                                if target_group_data["render_results"][i]["max_server_latency"] > target_group_data["render_results"][i]["max_client_latency"] 
                                    and target_group_data["render_results"][i]["max_client_latency"] != 0:

                                    new_test_status = get_test_status(target_group_data["render_results"][i]["max_server_latency"])
                                    old_test_status = target_group_data["render_results"][i]["test_status"]

                                    target_group_data[new_test_status] += 1
                                    target_group_data[old_test_status] -= 1

                                    target_file_content["summary"][new_test_status] += 1
                                    target_file_content["summary"][old_test_status] -= 1

                                    target_group_data["render_results"][i]["test_status"] = new_test_status

                    with open(target_file_path, "w", encoding="utf8") as f:
                        json.dump(target_file_content, f, indent=4, sort_keys=True)
