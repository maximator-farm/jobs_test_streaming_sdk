import socket
import sys
import os
from time import sleep
import traceback
import json
from instance_state import ClientInstanceState
from actions import ClientActionException
from client_actions import *
import psutil
from subprocess import PIPE, STDOUT
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


ACTIONS_MAPPING = {
    "execute_cmd": ExecuteCMD,
    "check_window": CheckWindow,
    "check_game": CheckWindow,
    "press_keys_server": PressKeysServer,
    "abort": Abort,
    "retry": Retry,
    "next_case": NextCase,
    "click_server": ClickServer,
    "start_test_actions_client": StartTestActionsClient,
    "start_test_actions_server": StartTestActionsServer,
    "make_screen": MakeScreen,
    "record_video": RecordVideo,
    "move": Move,
    "click": Click,
    "sleep": DoSleep,
    "parse_keys": PressKeys,
    "sleep_and_screen": SleepAndScreen,
    "skip_if_done": SkipIfDone
}


def start_client_side_tests(args, case, is_workable_condition, audio_device_name, current_try):
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
        instance_state = ClientInstanceState()

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
            params["archive_path"] = archive_path
            params["current_image_num"] = 1
            params["current_try"] = current_try
            params["audio_device_name"] = audio_device_name
            params["args"] = args
            params["case"] = case
            params["game_name"] = game_name

            for action in actions:
                if instance_state.commands_to_skip > 0:
                    instance_state.commands_to_skip -= 1
                    continue

                main_logger.info("\nCurrent action: {}".format(action))
                main_logger.info("Current state:\n{}".format(instance_state.format_current_state()))

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
                    command_object = ACTIONS_MAPPING[command](sock, params, instance_state, main_logger)
                    command_object.do_action()
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
                command_object = Retry(sock, params, instance_state, main_logger)
                command_object.do_action()
            else:
                instance_state.is_aborted_client = True
                command_object = Abort(sock, params, instance_state, main_logger)
                command_object.do_action()
        elif instance_state.is_aborted_server:
            pass
        else:
            command_object = NextCase(sock, params, instance_state, main_logger)
            command_object.do_action()

        sock.close()
