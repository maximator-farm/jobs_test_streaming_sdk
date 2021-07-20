import socket
import sys
import os
import json
from time import sleep, time
import psutil
from subprocess import PIPE
import traceback
import win32gui
import win32api
import shlex
import pyautogui
import pydirectinput
from utils import close_process, collect_traces
from threading import Thread
from instance_state import ServerInstanceState
from server_actions import *

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import *

pyautogui.FAILSAFE = False

GAMES_WITH_TIMEOUTS = ['apexlegends']

# some games should be rebooted sometimes
SECONDS_TO_CLOSE = {"valorant": 3000, "lol": 3000}


ACTIONS_MAPPING = {
    "execute_cmd": ExecuteCMD,
    "check_window": CheckWindow,
    "check_game": CheckWindow,
    "press_keys_server": PressKeysServer,
    "abort": Abort,
    "retry": Retry,
    "next_case": NextCase,
    "click_server": ClickServer,
    "start_test_actions_server": DoTestActions,
    "gpuview": GPUView
}


def start_server_side_tests(args, case, is_workable_condition, current_try):
    archive_path = os.path.join(args.output, "gpuview")
    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

    # configure socket
    sock = socket.socket()
    sock.bind(("", int(args.communication_port)))
    # max one connection
    sock.listen(1)
    connection, address = sock.accept()

    request = connection.recv(1024).decode("utf-8")

    game_name = args.game_name

    global GAMES_WITH_TIMEOUTS

    if game_name.lower() in GAMES_WITH_TIMEOUTS:
        pydirectinput.press("space")

    processes = {}

    try:
        instance_state = ServerInstanceState()

        if request == "ready":

            if is_workable_condition():
                connection.send("ready".encode("utf-8"))
            else:
                connection.send("fail".encode("utf-8"))

            # non-blocking usage
            connection.setblocking(False)

            # build params dict with all necessary variables for test actions
            params = {}
            params["archive_path"] = archive_path
            params["current_try"] = current_try
            params["args"] = args
            params["case"] = case
            params["game_name"] = game_name
            params["processes"] = processes

            while instance_state.wait_next_command:
                try:
                    request = connection.recv(1024).decode("utf-8")
                    instance_state.executing_test_actions = False
                except Exception as e:
                    if instance_state.executing_test_actions:
                        command_object = DoTestActions(sock, params, instance_state, main_logger)
                        command_object.do_action()
                    else:
                        sleep(1)
                    continue

                main_logger.info("\nReceived action: {}".format(request))
                main_logger.info("Current state:\n{}".format(instance_state.format_current_state()))

                parts = request.split(" ", 1)
                command = parts[0]
                if len(parts) > 1:
                    arguments_line = parts[1]
                else:
                    arguments_line = None

                params["action_line"] = request
                params["command"] = command
                params["arguments_line"] = arguments_line

                if command in ACTIONS_MAPPING:
                    if command == "start_test_actions_server":
                        connection.send("done".encode("utf-8"))

                    command_object = ACTIONS_MAPPING[command](connection, params, instance_state, main_logger)
                    command_object.do_action()
                else:
                    raise ServerActionException("Unknown server command: {}".format(command))

        else:
            raise Exception("Unknown client request: {}".format(request))
    except Exception as e:
        main_logger.error("Fatal error. Case will be aborted:".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        if not instance_state.is_aborted:
            connection.send("abort".encode("utf-8"))

        raise e
    finally:
        global SECONDS_TO_CLOSE
        
        with open(os.path.join(ROOT_PATH, "state.py"), "r") as json_file:
            state = json.load(json_file)

        if state["restart_time"] == 0:
            state["restart_time"] = time.time()
            main_logger.info("Reboot time was set")
        else:
            main_logger.info("Time left from the latest restart of game: {}".format(time.time() - state["restart_time"]))
            if args.game_name.lower() in SECONDS_TO_CLOSE and (time.time() - state["restart_time"]) > SECONDS_TO_CLOSE[args.game_name.lower()]:
                result = close_processes(processes, main_logger)
                main_logger.info("Processes were closed with status: {}".format(result))
                state["restart_time"] = time.time()
                
        with open(os.path.join(ROOT_PATH, "state.py"), "w+") as json_file:
            json.dump(state, json_file, indent=4)

        connection.close()
