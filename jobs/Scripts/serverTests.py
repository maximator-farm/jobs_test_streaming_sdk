import socket
import sys
import os
from time import sleep
import psutil
from subprocess import PIPE
import traceback
import win32gui
import shlex
import pyautogui
from utils import close_process
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


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
        # switch keyboard language to English
        win32api.LoadKeyboardLayout("00000409", 1)

        keys = keys_string.split()

        for key in keys:
            main_logger.info("Press: {}".format(key))
            pyautogui.press(key)
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
            main_logger.info("Processes was succesfully found")
            sock.send("done".encode())
        else:
            main_logger.error("Failed to close processes")
            sock.send("failed".encode())
    except Exception as e:
        main_logger.error("Failed to finish case execution: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("failed".encode())


def start_server_side_tests(args, case, sync_port, current_try):
    # configure socket
    sock = socket.socket()
    sock.bind(("", sync_port))
    # max one connection
    sock.listen(1)
    connection, address = sock.accept()

    request = connection.recv(1024).decode()

    try:
        if request == "ready":

            connection.send("ready".encode())

            while True:
                request = connection.recv(1024).decode()

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
                elif command == "finish":
                    finish(connection)
                    break
                else:
                    raise Exception("Unknown commnad: {}".format(request))

        else:
            raise Exception("Unknown client request: {}".format(request))
    except Exception as e:
        main_logger.error("Fatal error. Case will be aborted:".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        sock.send("abort".encode())
    finally:
        connection.close()
