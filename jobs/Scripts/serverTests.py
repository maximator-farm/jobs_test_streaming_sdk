
import socket
import sys
import os
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

        if window is not None and window != 0:
            main_logger.info("Window {} was succesfully found".format(window_name))
            try:
                win32gui.ShowWindow(window, 5)
                win32gui.SetForegroundWindow(window)
            except Exception as e1:
                main_logger.error("Failed to make window foreground: {}".format(str(e1)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
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
            duration = 0

            if "_" in key:
                parts = key.split("_")
                key = parts[0]
                duration = int(parts[1])

            main_logger.info("Press: {}. Duration: {}".format(key, duration))

            if duration == 0:
                times = 1

                if ":" in key:
                    parts = key.split(":")
                    key = parts[0]
                    times = int(parts[1])

                keys_to_press = key.split("+")

                for i in range(times):
                    for key_to_press in keys_to_press:
                        pydirectinput.keyDown(key_to_press)

                    sleep(0.1)

                    for key_to_press in keys_to_press:
                        pydirectinput.keyUp(key_to_press)

                    sleep(0.5)
            else:
                keys_to_press = key.split("+")

                for key_to_press in keys_to_press:
                    pydirectinput.keyDown(key_to_press)

                sleep(duration)

                for key_to_press in keys_to_press:
                    pydirectinput.keyUp(key_to_press)

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

        pyautogui.moveTo(x, y)
        sleep(1)
        pyautogui.click()

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
        elif game_name == "apexlegends":
            pydirectinput.keyDown("a")
            pydirectinput.keyDown("space")
            sleep(0.5)
            pydirectinput.keyUp("a")
            pydirectinput.keyUp("space")

            pydirectinput.keyDown("d")
            pydirectinput.keyDown("space")
            sleep(0.5)
            pydirectinput.keyUp("d")
            pydirectinput.keyUp("space")
            pyautogui.click(button="right")
        elif game_name == "lol":
            edge_x = win32api.GetSystemMetrics(0)
            edge_y = win32api.GetSystemMetrics(1)
            center_x = edge_x / 2
            center_y = edge_y / 2

            sleep(4)

            pyautogui.moveTo(center_x + 360, center_y - 360)
            sleep(0.1)
            pyautogui.click()
            sleep(0.1)
            pyautogui.moveTo(edge_x - 255, edge_y - 60)
            sleep(0.1)
            pyautogui.click(button="right")
            sleep(1.5)

            pyautogui.moveTo(edge_x - 290, edge_y - 20)
            sleep(0.1)
            pyautogui.click()
            sleep(0.1)
            pyautogui.moveTo(center_x, center_y)
            sleep(0.1)
            pyautogui.click(button="right")
            sleep(1.5)

    except Exception as e:
        main_logger.error("Failed to do test actions: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))


def gpuview(sock, start_collect_traces, archive_path, archive_name):
    if start_collect_traces == "True":
        sock.send("start".encode())

        try:
            collect_traces(archive_path, archive_name + "_server.zip")
        except Exception as e:
            main_logger.warning("Failed to collect GPUView traces: {}".format(str(e)))
            main_logger.warning("Traceback: {}".format(traceback.format_exc()))
    else:
        sock.send("skip".encode())


def start_server_side_tests(args, case, is_workable_condition, communication_port, current_try):
    archive_path = os.path.join(args.output, "gpuview")

    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

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
    
    pydirectinput.press("space")

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
                    arguments = shlex.split(parts[1])
                else:
                    arguments = None

                if command == "execute_cmd":
                    execute_cmd(connection, *arguments)
                elif command == "check_game":
                    check_game(connection, *arguments)
                elif command == "press_keys_server":
                    press_keys_server(connection, *arguments)
                elif command == "click_server":
                    click_server(connection, *arguments)
                elif command == "start_test_actions":
                    connection.send("done".encode())
                    do_test_actions(game_name.lower())
                    execute_test_actions = True
                elif command == "gpuview":
                    gpuview(connection, args.collect_traces, archive_path, case["case"])
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
