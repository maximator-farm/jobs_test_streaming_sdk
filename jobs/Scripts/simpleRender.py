import argparse
import os
import subprocess
import psutil
import json
import platform
from datetime import datetime
from shutil import copyfile, move, which
import sys
from utils import is_case_skipped, close_process
from clientTests import start_client_side_tests
from serverTests import start_server_side_tests
from queue import Queue
from subprocess import PIPE
from threading import Thread
import copy
import traceback
import time

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


# port throuth which client and server communicate to synchronize execution of tests
SYNC_PORT = 10000


def copy_test_cases(args):
    try:
        copyfile(os.path.realpath(os.path.join(os.path.dirname(
            __file__), '..', 'Tests', args.test_group, 'test_cases.json')),
            os.path.realpath(os.path.join(os.path.abspath(
                args.output), 'test_cases.json')))

        cases = json.load(open(os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json'))))

        with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
            cases = json.load(json_file)

        if os.path.exists(args.test_cases) and args.test_cases:
            with open(args.test_cases) as file:
                test_cases = json.load(file)['groups'][args.test_group]
                if test_cases:
                    necessary_cases = [
                        item for item in cases if item['case'] in test_cases]
                    cases = necessary_cases

            with open(os.path.join(args.output, 'test_cases.json'), "w+") as file:
                json.dump(duplicated_cases, file, indent=4)
    except Exception as e:
        main_logger.error('Can\'t load test_cases.json')
        main_logger.error(str(e))
        exit(-1)


def prepare_empty_reports(args, current_conf):
    main_logger.info('Create empty report files')

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    for case in cases:
        if is_case_skipped(case, current_conf):
            case['status'] = 'skipped'

        if case['status'] != 'done' and case['status'] != 'error':
            if case["status"] == 'inprogress':
                case['status'] = 'active'

            test_case_report['test_case'] = case['case']
            test_case_report['render_device'] = args.server_gpu_name
            test_case_report['script_info'] = case['script_info']
            test_case_report['test_group'] = args.test_group
            test_case_report['tool'] = 'StreamingSDK'
            test_case_report['execution_type'] = args.execution_type
            test_case_report['keys'] = case['server_keys'] if args.execution_type == 'server' else case['client_keys']
            test_case_report['transport_protocol'] = case['transport_protocol']
            test_case_report['tool_path'] = args.server_tool if args.execution_type == 'server' else args.client_tool
            test_case_report['date_time'] = datetime.now().strftime(
                '%m/%d/%Y %H:%M:%S')
            test_case_report[SCREENS_PATH_KEY] = os.path.join(args.output, "Color", case["case"])

            if case['status'] == 'skipped':
                test_case_report['test_status'] = 'skipped'
                test_case_report['group_timeout_exceeded'] = False
            else:
                test_case_report['test_status'] = 'error'

            case_path = os.path.join(args.output, case['case'] + CASE_REPORT_SUFFIX)

            if os.path.exists(case_path):
                with open(case_path) as f:
                    case_json = json.load(f)[0]
                    test_case_report["number_of_tries"] = case_json["number_of_tries"]

            with open(case_path, "w") as f:
                f.write(json.dumps([test_case_report], indent=4))

    with open(os.path.join(args.output, "test_cases.json"), "w+") as f:
        json.dump(cases, f, indent=4)


def save_results(args, case, cases, test_case_status, error_messages = []):
    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "r") as file:
        test_case_report = json.loads(file.read())[0]
        test_case_report["test_status"] = test_case_status
        test_case_report["{}_log".format(test_case_report["execution_type"])] = os.path.join(
            "tool_logs", case["case"] + ".log")
        test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        test_case_report["number_of_tries"] += 1

        if test_case_status != "passed":
            test_case_report["message"] = list(error_messages)

        if test_case_status == "passed" or test_case_status == "error":
            test_case_report["group_timeout_exceeded"] = False

    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "w") as file:
        json.dump([test_case_report], file, indent=4)

    case["status"] = test_case_status
    with open(os.path.join(args.output, "test_cases.json"), "w") as file:
        json.dump(cases, file, indent=4)


def execute_tests(args, current_conf):
    rc = 0

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    tool_path = args.server_tool if args.execution_type == "server" else args.client_tool

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:

        keys = case["server_keys"] if args.execution_type == "server" else case["client_keys"]

        screens_path = os.path.join(args.output, "Color", case["case"])

        current_try = 0

        error_messages = set()

        while current_try < args.retries:
            process = None

            try:
                if args.execution_type == "server":
                    execution_script = "{tool} {keys}".format(tool=tool_path, keys=keys)
                else:
                    execution_script = "{tool} {keys} -connectionurl {transport_protocol}://{ip_address}:1235".format(
                        tool=tool_path, keys=keys, transport_protocol=case["transport_protocol"],
                        ip_address=args.ip_address
                    )

                execution_script_path = os.path.join(args.output, "{}.bat".format(case["case"]))
       
                with open(execution_script_path, "w") as f:
                    f.write(execution_script)

                status = "error"

                main_logger.info("Start StreamingSDK {}".format(args.execution_type))

                process = psutil.Popen(execution_script_path, stdout=PIPE, stderr=PIPE, shell=True)

                main_logger.info("Start execution_type depended script")

                # Wait a bit to launch streaming SDK client/server
                time.sleep(5)

                if args.execution_type == "server":
                    start_server_side_tests(args, case, SYNC_PORT, current_try)
                else:
                    start_client_side_tests(args, case, args.ip_address, SYNC_PORT, screens_path, current_try)

                save_results(args, case, cases, "passed", error_messages = [])

                break
            except Exception as e:
                save_results(args, case, cases, "failed", error_messages = error_messages)
                error_messages.add(str(e))
                main_logger.error("Failed to execute test case (try #{}): {}".format(current_try, str(e)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
            finally:
                if process is not None:
                    close_process(process)

                current_try += 1

                log_source_path = tool_path + ".log"
                log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + ".log")

                with open(log_source_path, "r") as file:
                    logs = file.read()

                with open(log_destination_path, "a") as file:
                    file.write("\n---------- Try #{} ----------\n".format(current_try))
                    file.write(logs)
        else:
            main_logger.error("Failed to execute case '{}' at all".format(case["case"]))
            rc = -1
            save_results(args, case, cases, "error", error_messages = error_messages)

    return rc


def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--client_tool", required=True, metavar="<path>")
    parser.add_argument("--server_tool", required=True, metavar="<path>")
    parser.add_argument("--output", required=True, metavar="<dir>")
    parser.add_argument("--test_group", required=True)
    parser.add_argument("--test_cases", required=True)
    parser.add_argument("--retries", required=False, default=2, type=int)
    parser.add_argument('--execution_type', required=True)
    parser.add_argument('--ip_address', required=True)
    parser.add_argument('--server_gpu_name', required=True)

    return parser


if __name__ == '__main__':
    main_logger.info('simpleRender start working...')

    args = createArgsParser().parse_args()

    try:
        os.makedirs(args.output)

        if not os.path.exists(os.path.join(args.output, "Color")):
            os.makedirs(os.path.join(args.output, "Color"))
        if not os.path.exists(os.path.join(args.output, "tool_logs")):
            os.makedirs(os.path.join(args.output, "tool_logs"))

        render_device = args.server_gpu_name
        system_pl = platform.system()
        current_conf = set(platform.system()) if not render_device else {platform.system(), render_device}
        main_logger.info("Detected GPUs: {}".format(render_device))
        main_logger.info("PC conf: {}".format(current_conf))
        main_logger.info("Creating predefined errors json...")

        copy_test_cases(args)
        prepare_empty_reports(args, current_conf)
        exit(execute_tests(args, current_conf))
    except Exception as e:
        main_logger.error("Failed during script execution. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        exit(-1)
