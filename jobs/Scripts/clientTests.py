import socket
import sys
import os
from time import sleep
import shlex
import traceback
import win32gui
import pyautogui
import pyscreenshot
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


current_image_num = 0
SERVER_ACTIONS = ["execute_cmd", "check_window"]


def execute_cmd(sock, action):
    sock.send(action.encode())


def check_window(sock, action):
    sock.send(action.encode())


def make_screen(screen_path, screen_name):
    screen = pyscreenshot.grab()
    screen = screen.convert("RGB")
    global current_image_num
    screen.save(os.path.join(screen_path, "{:03}_{}".format(current_image_num, screen_name)))
    current_image_num += 1


def move(action):
    args = action.split()
    x = args[1]
    y = args[2]
    main_logger.info("Move to x = {}, y = {}".format(x, y))
    pyautogui.moveTo(int(x), int(y))


def click():
    pyautogui.click()


def start_client_side_tests(args, case, ip_address, sync_port, screens_path):
    current_image_num = 0

    sock = socket.socket()

    while True:
        try:
            sock.connect((ip_address, sync_port))
            break
        except Exception:
            main_logger.info("Could not connect to server. Try it again")
            sleep(5)

    # try to communicate with server few times
    sock.send("ready".encode())
    response = sock.recv(1024).decode()

    is_aborted = False

    try:
        if response == "ready":

            for action in case["client_actions"]:
                command = action.split()[0]

                if command == "execute_cmd":
                    execute_cmd(sock, action)
                elif command == "check_window":
                    check_window(sock, action)
                elif command == "make_screen":
                    make_screen(screens_path, action)
                elif command == "move":
                    move(action)
                elif command == "click":
                    click()
                else:
                    raise Exception("Unknown client command: {}".format(command))

                if command in SERVER_ACTIONS:
                    response = sock.recv(1024).decode()

                    if response == "done":
                        pass
                    elif response == "failed":
                        raise Exception("Action failed on server side")
                    elif response == "abort":
                        is_aborted = True
                        raise Exception("Server sent abort status")
                    else:
                        raise Exception("Unknown server status: {}".format(response))

        else:
            raise Exception("Unknown server answer: {}".format(response))
    except Exception as e:
        main_logger.error("Fatal error. Case will be aborted:".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
    finally:
        if not is_aborted:
            sock.send("finish".encode())

        response = sock.recv(1024).decode()

        main_logger.info("Server response for 'finish' action: {}".format(response))

        connection.close()
