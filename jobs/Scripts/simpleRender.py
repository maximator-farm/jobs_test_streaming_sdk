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
from subprocess import PIPE, STDOUT
from threading import Thread
from pyffmpeg import FFmpeg
import copy
import traceback
import time
import win32api

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import *
from jobs_launcher.core.system_info import get_gpu


# process of Streaming SDK client / server
PROCESS = None
# path to Streaming SDK client / server run script
SCRIPT_PATH = None


def get_audio_device_name():
    try:
        ff = FFmpeg()
        ffmpeg_exe = ff.get_ffmpeg_bin()

        # list all existing audio devices
        ffmpeg_command = "{} -list_devices true -f dshow -i dummy".format(ffmpeg_exe)

        ffmpeg_process = psutil.Popen(ffmpeg_command, stdout=PIPE, stderr=STDOUT, shell=True)

        audio_device = None

        for line in ffmpeg_process.stdout:
            line = line.decode("utf8")
            if "Stereo Mix" in line:
                audio_device = line.split("\"")[1]
                break
        else:
            raise Exception("Audio device wasn't found")

        main_logger.info("Found audio device: {}".format(audio_device))

        return audio_device
    except Exception as e:
        main_logger.error("Can't get audio device name. Use default name instead")
        main_logger.error(str(e))
        main_logger.error("Traceback:\n{}".format(traceback.format_exc()))

        return "Stereo Mix (Realtek High Definition Audio)"


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

            test_case_report = {}
            test_case_report['test_case'] = case['case']
            test_case_report['render_device'] = args.server_gpu_name
            test_case_report['script_info'] = case['script_info']
            test_case_report['test_group'] = args.test_group
            test_case_report['tool'] = 'StreamingSDK'
            test_case_report['render_time'] = 0.0
            test_case_report['execution_time'] = 0.0
            test_case_report['execution_type'] = args.execution_type
            test_case_report['keys'] = case['server_keys'] if args.execution_type == 'server' else case['client_keys']
            test_case_report['transport_protocol'] = case['transport_protocol'].upper()
            test_case_report['tool_path'] = args.server_tool if args.execution_type == 'server' else args.client_tool
            test_case_report['date_time'] = datetime.now().strftime(
                '%m/%d/%Y %H:%M:%S')
            min_latency_key = 'min_{}_latency'.format(args.execution_type)
            test_case_report[min_latency_key] = -0.0
            max_latency_key = 'max_{}_latency'.format(args.execution_type)
            test_case_report[max_latency_key] = -0.0
            median_latency_key = 'median_{}_latency'.format(args.execution_type)
            test_case_report[median_latency_key] = -0.0
            test_case_report[SCREENS_PATH_KEY] = os.path.join(args.output, "Color", case["case"])
            test_case_report["number_of_tries"] = 0
            test_case_report["client_configuration"] = get_gpu() + " " + platform.system()
            test_case_report["server_configuration"] = args.server_gpu_name + " " + args.server_os_name
            test_case_report["message"] = []

            # update script info using current params (e.g. ip and communication port, resolution)
            for i in range(len(test_case_report["script_info"])):
                if "Client keys" in test_case_report["script_info"][i]:
                    test_case_report["script_info"][i] = "{base} -connectionurl {transport_protocol}://{ip_address}:1235".format(
                        base=test_case_report["script_info"][i],
                        transport_protocol=case["transport_protocol"],
                        ip_address=args.ip_address
                    )

                elif "Server keys" in test_case_report["script_info"][i]:
                    test_case_report["script_info"][i] = test_case_report["script_info"][i].replace("<resolution>", args.screen_resolution.replace("x", ","))

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


def save_results(args, case, cases, execution_time = 0.0, test_case_status = "", error_messages = []):
    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "r") as file:
        test_case_report = json.loads(file.read())[0]
        test_case_report["test_status"] = test_case_status
        test_case_report["execution_time"] = execution_time
        test_case_report["server_log"] = os.path.join("tool_logs", case["case"] + "_server.log")
        test_case_report["client_log"] = os.path.join("tool_logs", case["case"] + "_client.log")

        if args.collect_traces == "True":
            if args.execution_type == "server":
                test_case_report["server_trace_archive"] = os.path.join("gpuview", case["case"] + "_server.zip")
            else:
                test_case_report["client_trace_archive"] = os.path.join("gpuview", case["case"] + "_client.zip")

        test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        test_case_report["number_of_tries"] += 1

        test_case_report["message"] = list(error_messages)

        if test_case_status == "passed" or test_case_status == "error":
            test_case_report["group_timeout_exceeded"] = False

        video_path = os.path.join("Color", case["case"] + ".mp4")

        if os.path.exists(os.path.join(args.output, video_path)):
            test_case_report[VIDEO_KEY] = video_path

    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "w") as file:
        json.dump([test_case_report], file, indent=4)

    if test_case_status:
       case["status"] = test_case_status

    with open(os.path.join(args.output, "test_cases.json"), "w") as file:
        json.dump(cases, file, indent=4)


def start_streaming(args):
    global PROCESS, SCRIPT_PATH

    main_logger.info("Start StreamingSDK {}".format(args.execution_type))

    # start Streaming SDK process
    PROCESS = psutil.Popen(SCRIPT_PATH, stdout=PIPE, stderr=PIPE, shell=True)

    main_logger.info("Start execution_type depended script")

    # Wait a bit to launch streaming SDK client/server
    time.sleep(3)

    main_logger.info("Screen resolution: width = {}, height = {}".format(win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)))


def is_workable_condition():
    # is process with Streaming SDK alive
    try:
        global PROCESS
        PROCESS.wait(timeout=0)
        main_logger.error("StreamingSDK was down")

        return False
    except psutil.TimeoutExpired as e:
        main_logger.info("StreamingSDK is alive") 

        return True


def execute_tests(args, current_conf):
    rc = 0

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    tool_path = args.server_tool if args.execution_type == "server" else args.client_tool

    tool_path = os.path.abspath(tool_path)

    if args.execution_type == "client":
        # name of Stereo mix device can be different on different machines
        audio_device_name = get_audio_device_name()
    else:
        audio_device_name = None

    # copy log from last log line (it's actual for groups without restarting of client / server)
    last_log_line = None

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:

        case_start_time = time.time()

        # take tool keys based on type of the instance (server/client)
        keys = case["server_keys"] if args.execution_type == "server" else case["client_keys"]

        current_try = 0

        while current_try < args.retries:
            global PROCESS, SCRIPT_PATH

            error_messages = set()

            try:
                if args.execution_type == "server":
                    # copy settings.json to update transport protocol using by server instance
                    settings_dir_path = os.path.join(os.getenv("APPDATA"), "..", "Local", "AMD", "RemoteGameServer", "settings")
                    settings_json_path = os.path.join(settings_dir_path, "settings.json")
                    
                    if not os.path.exists(settings_dir_path):
                        os.makedirs(settings_dir_path)

                    copyfile(
                        os.path.realpath(
                            os.path.join(os.path.dirname(__file__),
                            "..",
                            "Configs",
                            "settings_{}.json".format(case["transport_protocol"].upper()))
                        ), 
                        settings_json_path
                    )

                    with open(settings_json_path, "r") as file:
                        settings_json_content = json.load(file)

                    main_logger.info("Network in settings.json: {}".format(settings_json_content["Headset"]["Network"]))
                    main_logger.info("Datagram size in settings.json: {}".format(settings_json_content["Headset"]["DatagramSize"]))

                    execution_script = "{tool} {keys}".format(tool=tool_path, keys=keys)

                    # replace 'x' in resolution by ',' (1920x1080 -> 1920,1080)
                    # place the current screen resolution in keys of the server instance
                    execution_script = execution_script.replace("<resolution>", args.screen_resolution.replace("x", ","))
                else:
                    execution_script = "{tool} {keys} -connectionurl {transport_protocol}://{ip_address}:1235".format(
                        tool=tool_path,
                        keys=keys,
                        transport_protocol=case["transport_protocol"],
                        ip_address=args.ip_address
                    )

                SCRIPT_PATH = os.path.join(args.output, "{}.bat".format(case["case"]))
       
                with open(SCRIPT_PATH, "w") as f:
                    f.write(execution_script)

                # provide start Streaming SDK func if Streaming SDK was closed in previous case
                if PROCESS is None:
                    start_streaming_func = start_streaming
                else:
                    start_streaming_func = None

                if args.execution_type == "server":
                    start_server_side_tests(args, case, start_streaming_func, is_workable_condition, current_try)
                else:
                    start_client_side_tests(args, case, start_streaming_func, is_workable_condition, audio_device_name, current_try)

                execution_time = time.time() - case_start_time
                save_results(args, case, cases, execution_time = execution_time, test_case_status = "passed", error_messages = [])

                break
            except Exception as e:
                execution_time = time.time() - case_start_time
                save_results(args, case, cases, execution_time = execution_time, test_case_status = "failed", error_messages = error_messages)
                main_logger.error("Failed to execute test case (try #{}): {}".format(current_try, str(e)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
            finally:
                if "keep_{}".format(args.execution_type) not in case or not case["keep_{}".format(args.execution_type)]:
                    # close the current Streaming SDK process
                    if PROCESS is not None:
                        close_process(PROCESS)

                    # additional try to kill Streaming SDK server/client (to be sure that all processes are closed)

                    status = 0

                    while status != 128:
                        status = subprocess.call("taskkill /f /im RemoteGameClient.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    status = 0

                    while status != 128:
                        status = subprocess.call("taskkill /f /im RemoteGameServer.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    PROCESS = None

                current_try += 1

                try:
                    log_source_path = tool_path + ".log"
                    log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + "_{}".format(args.execution_type) + ".log")

                    with open(log_source_path, "rb") as file:
                        logs = file.read()

                    # Firstly, convert utf-2 le bom to utf-8 with BOM. Secondly, remove BOM
                    logs = logs.decode("utf-16-le").encode("utf-8").decode("utf-8-sig").encode("utf-8")

                    lines = logs.split(b"\n")

                    # index of first line of the current log in whole log file
                    first_log_line_index = 0

                    for i in range(len(lines)):
                        if last_log_line is not None and last_log_line in lines[i]:
                            first_log_line_index = i + 1
                            break

                    # update last log line
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i] and lines[i] != b"\r":
                            last_log_line = lines[i]
                            break

                    if first_log_line_index != 0:
                        lines = lines[first_log_line_index:]

                    logs = b"\n".join(lines)

                    with open(log_destination_path, "ab") as file:
                        file.write("\n---------- Try #{} ----------\n\n".format(current_try).encode("utf-8"))
                        file.write(logs)
                except Exception as e:
                    main_logger.error("Failed during logs saving. Exception: {}".format(str(e)))
                    main_logger.error("Traceback: {}".format(traceback.format_exc()))
        else:
            main_logger.error("Failed to execute case '{}' at all".format(case["case"]))
            rc = -1
            execution_time = time.time() - case_start_time
            save_results(args, case, cases, execution_time = execution_time, test_case_status = "error", error_messages = error_messages)

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
    parser.add_argument('--communication_port', required=True)
    parser.add_argument('--server_gpu_name', required=True)
    parser.add_argument('--server_os_name', required=True)
    parser.add_argument('--game_name', required=True)
    parser.add_argument('--common_actions_path', required=True)
    parser.add_argument('--collect_traces', required=True)
    parser.add_argument('--screen_resolution', required=True)

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

        # use OS name and GPU name from server (to skip and merge cases correctly)
        render_device = args.server_gpu_name
        system_pl = args.server_os_name
        current_conf = set(system_pl) if not render_device else {system_pl, render_device}
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
