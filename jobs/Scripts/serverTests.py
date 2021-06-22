import socket
import sys
import os
from time import sleep
import psutil
from subprocess import PIPE
import traceback
import win32gui
import win32api
import shlex
import pyautogui
from utils import close_process
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *

pyautogui.FAILSAFE = False


PROCESSES = {}


def execute_cmd(sock, cmd_command):
    try:
        global PROCESSES
        process = psutil.Popen(cmd_command, stdout=PIPE, stderr=PIPE, shell=True)
        PROCESSES[cmd_command] = process

        main_logger.info("Executed: {}".format(cmd_command))
        sock.send("done".encode())
    except Exception as e:
        main_logger.error("Failed to execute_cmd: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("failed".encode())


def check_game(sock, window_name, process_name):
    try:
        window = win32gui.FindWindow(None, window_name)

        if window is not None:
            main_logger.info("Window {} was succesfully found".format(window_name))
        else:
            main_logger.error("Window {} wasn't found at all".format(window_name))
            sock.send("failed".encode())
            return

        global PROCESSES

        for process in psutil.process_iter():
            if process_name in process.name():
                main_logger.info("Process {} was succesfully found".format(process_name))
                PROCESSES[process_name] = process
                sock.send("done".encode())
                break
        else:
            main_logger.info("Process {} wasn't found at all".format(process_name))
            sock.send("failed".encode())
    except Exception as e:
        main_logger.error("Failed to execute_cmd: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("failed".encode())


def close_processes():
    global PROCESSES
    result = True

    for process_name in PROCESSES:
        try:
            close_process(PROCESSES[process_name])
        except Exception as e:
            main_logger.error("Failed to close process: {}".format(str(e)))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))
            result = False

    PROCESSES = {}

    return result


def press_keys_server(sock, keys_string):
    try:
        keys = keys_string.split()

        for key in keys:
            main_logger.info("Press: {}".format(key))
            pyautogui.press(key)

            if "enter" in key:
                sleep(2)
            else:
                sleep(1)

        sock.send("done".encode())
    except Exception as e:
        main_logger.error("Failed to press keys: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("failed".encode())


def finish(sock):
    try:
        result = close_processes()

        if result:
            main_logger.info("Processes was succesfully closed")
            sock.send("done".encode())
        else:
            main_logger.error("Failed to close processes")
            sock.send("failed".encode())
    except Exception as e:
        main_logger.error("Failed to finish case execution: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("failed".encode())


def retry(sock):
    sock.send("done".encode())


def next_case(sock):
    sock.send("done".encode())


def click_server(sock, x_description, y_description):
    try:
        if "center_" in x_description:
            x = win32api.GetSystemMetrics(0) / 2 + int(x_description.replace("center_", ""))
        elif "edge_" in x_description:
            x = win32api.GetSystemMetrics(0) + int(x_description.replace("edge_", ""))
        else:
            x = int(x_description)

        if "center_" in y_description:
            y = win32api.GetSystemMetrics(1) / 2 + int(y_description.replace("center_", ""))
        elif "edge_" in y_description:
            y = win32api.GetSystemMetrics(1) + int(y_description.replace("edge_", ""))
        else:
            y = int(y_description)

        main_logger.info("Click at x = {}, y = {}".format(x, y))

        pyautogui.click(x=x, y=y)

        sock.send("done".encode())
    except Exception as e:
        main_logger.error("Failed to click: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("failed".encode())


def do_test_actions(game_name):
    try:
        if game_name == "borderlands3":
            pass
        elif game_name == "valorant":
            pyautogui.keyDown("a")
            sleep(0.5)
            pyautogui.keyUp("a")

            pyautogui.click()
            sleep(0.5)
            pyautogui.click()

            pyautogui.keyDown("d")
            sleep(0.5)
            pyautogui.keyUp("d")

            pyautogui.keyDown("d")
            sleep(0.5)
            pyautogui.keyUp("d")

            pyautogui.click()
            sleep(0.5)
            pyautogui.click()

            pyautogui.keyDown("a")
            sleep(0.5)
            pyautogui.keyUp("a")

    except Exception as e:
        main_logger.error("Failed to do test actions: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


def start_server_side_tests(args, case, is_workable_condition, communication_port, current_try):
    # configure socket
    sock = socket.socket()
    sock.bind(("", int(communication_port)))
    # max one connection
    sock.listen(1)
    connection, address = sock.accept()

    request = connection.recv(1024).decode()

    is_aborted = False
    is_non_workable = False
    execute_test_actions = False

    game_name = args.game_name

    try:
        if request == "ready":

            if is_workable_condition():
                connection.send("ready".encode())
            else:
                connection.send("fail".encode())

            # non-blocking usage
            connection.setblocking(False)

            while True:
                try:
                    request = connection.recv(1024).decode()
                    execute_test_actions = False
                except Exception as e:
                    if execute_test_actions:
                        do_test_actions(game_name.lower())
                    else:
                        sleep(1)
                    continue

                parts = request.split(' ', 1)
                command = parts[0]
                if len(parts) > 1:
                    args = shlex.split(parts[1])
                else:
                    args = None

                if command == "execute_cmd":
                    execute_cmd(connection, *args)
                elif command == "check_game":
                    check_game(connection, *args)
                elif command == "press_keys_server":
                    press_keys_server(connection, *args)
                elif command == "click_server":
                    click_server(connection, *args)
                elif command == "start_test_actions":
                    connection.send("done".encode())
                    do_test_actions(game_name.lower())
                    execute_test_actions = True
                elif command == "next_case":
                    next_case(connection)
                    break
                elif command == "finish":
                    finish(connection)
                    break
                elif command == "abort":
                    is_aborted = True
                    finish(connection)
                    raise Exception("Client sent abort command")
                elif command == "retry":
                    is_aborted = True
                    retry(connection)
                    raise Exception("Client sent retry command")
                else:
                    raise Exception("Unknown command: {}".format(request))

        else:
            raise Exception("Unknown client request: {}".format(request))
    except Exception as e:
        main_logger.error("Fatal error. Case will be aborted:".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        if not is_aborted:
            connection.send("abort".encode())

        raise e
    finally:
        connection.close()
