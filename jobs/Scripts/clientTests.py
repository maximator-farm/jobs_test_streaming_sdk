import socket
import sys
import os
from time import sleep
import traceback
import json
from instance_state import InstanceState, ClientActionException
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


def get_audio_device_name(logger):
    try:
        ff = FFmpeg()
        ffmpeg_exe = ff.get_ffmpeg_bin()

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
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        return "Stereo Mix (Realtek High Definition Audio)"


ACTIONS_MAPPING = {
    "execute_cmd": ExecuteCMD,
    "check_window": CheckWindow,
    "check_game": CheckWindow,
    "press_keys_server": PressKeysServer,
    "abort": Abort,
    "retry": Retry,
    "next_case": NextCase,
    "click_server": ClickServer,
    "start_test_actions_server": StartTestActionsServer,
    "make_screen": MakeScreen,
    "record_video": RecordVideo,
    "move": Move,
    "click": Click,
    "do_sleep": DoSleep,
    "parse_keys": PressKeys,
    "sleep_and_screen": SleepAndScreen,
    "do_test_actions": DoTestActions
}


def start_client_side_tests(args, case, is_workable_condition, current_try):
    audio_device_name = get_audio_device_name()

    output_path = os.path.join(args.output, "Color")

    screen_path = os.path.join(output_path, case["case"])
    if not os.path.exists(screen_path):
        os.makedirs(screen_path)

    archive_path = os.path.join(args.output, "gpuview")
    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

    sock = socket.socket()

    game_name = args.game_name

    # Connect to server to sync autotests
    while True:
        try:
            sock.connect((args.ip_address, int(args.communication_port)))
            break
        except Exception:
            main_logger.info("Could not connect to server. Try it again")
            sleep(5)

    try:
        instance_state = InstanceState()

        sock.send("ready".encode("utf-8"))
        response = sock.recv(1024).decode("utf-8")

        if response == "ready":

            if not is_workable_condition():
                instance_state.non_workable_client = True
                raise Exception("Client has non-workable state")

            actions_key = "{}_actions".format(game_name.lower())
            if actions_key in case:
                actions = case[actions_key]
            else:
                # use default list of actions if some specific list of actions doesn't exist
                with open(os.path.abspath(args.common_actions_path), "r", encoding="utf-8") as common_actions_file:
                    actions = json.load(common_actions_file)[actions_key]

            # build params dict with all necessary variables for test actions
            params = {}
            params["output_path"] = output_path
            params["screen_path"] = screen_path
            params["current_image_num"] = 1
            params["current_try"] = current_try
            params["audio_device_name"] = audio_device_name
            params["screen_path"] = screen_path
            params["args"] = args
            params["case"] = case
            params["game_name"] = game_name

            for action in actions:
                main_logger.info("Current action: {}".format(action))

                parts = action.split(" ", 1)
                command = parts[0]
                if len(parts) > 1:
                    arguments_line = parts[1]
                else:
                    arguments_line = None

                params["action_line"] = action
                params["command"] = command
                params["arguments_line"] = arguments_line

                if command in ACTIONS_MAPPING:
                    command_object = ACTIONS_MAPPING[command](sock, params, instance_state, logger)
                    command_object.parse()
                    command_object.execute()
                    command_object.analyze_result()
                else:
                    raise ClientActionException("Unknown client command: {}".format(command))

        elif response == "fail":
            instance_state.non_workable_server = True
            raise Exception("Server has non-workable state")
        else:
            raise Exception("Unknown server answer: {}".format(response))
    except Exception as e:
        instance_state.prev_action_done = False
        main_logger.error("Fatal error. Case will be aborted: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        raise e
    finally:
        if not instance_state.prev_action_done:
            if instance_state.non_workable_client or instance_state.non_workable_server:
                retry(sock)
            else:
                instance_state.is_aborted_client = True
                abort(sock)
        elif instance_state.is_aborted_server:
            pass
        else:
            next_case(sock)

        sock.close()
