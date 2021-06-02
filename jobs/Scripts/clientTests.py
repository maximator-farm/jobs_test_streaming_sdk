import socket
import sys
import os
from time import sleep
import shlex
import traceback
import win32gui
import pyautogui
import pyscreenshot
import shlex
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


current_image_num = 1
SERVER_ACTIONS = ["execute_cmd", "check_game", "press_keys_server"]


def execute_cmd(sock, action):
    sock.send(action.encode())


def check_game(sock, action):
    sock.send(action.encode())


def make_screen(screen_path, screen_name=""):
    screen = pyscreenshot.grab()
    if screen_name:
        screen = screen.convert("RGB")
        global current_image_num
        screen.save(os.path.join(screen_path, "{:03}_{}.jpg".format(current_image_num, screen_name)))
        current_image_num += 1


def move(x, y):
    main_logger.info("Move to x = {}, y = {}".format(x, y))
    pyautogui.moveTo(int(x), int(y))
    sleep(1)


def click():
    pyautogui.click()
    sleep(1)


def do_sleep(seconds):
    sleep(int(seconds))


def press_keys(keys_string):
    keys = keys_string.split()

    for key in keys:
        main_logger.info("Press: {}".format(key))
        pyautogui.press(key)
        sleep(1)


def press_keys_server(sock, action):
    sock.send(action.encode())


def sleep_and_screen(initial_delay, number_of_screens, delay, screen_name, screen_path):
    sleep(int(initial_delay))

    screen_number = 1

    while True:
        make_screen(screen_path, screen_name="{}_{:02}".format(screen_name, screen_number))
        screen_number += 1

        if screen_number > int(number_of_screens):
            break
        else:
            sleep(int(delay))


def finish(sock):
    sock.send("finish".encode())
    response = sock.recv(1024).decode()
    main_logger.info("Server response for 'finish' action: {}".format(response))


def abort(sock):
    sock.send("abort".encode())
    response = sock.recv(1024).decode()
    main_logger.info("Server response for 'abort' action: {}".format(response))


def next_case(sock):
    sock.send("next_case".encode())
    response = sock.recv(1024).decode()
    main_logger.info("Server response for 'next_case' action: {}".format(response))


def start_client_side_tests(args, case, is_workable_condition, ip_address, sync_port, screens_path, current_try):
    if current_try == 0:
        current_image_num = 1

    sock = socket.socket()

    while True:
        try:
            sock.connect((ip_address, sync_port))
            break
        except Exception:
            main_logger.info("Could not connect to server. Try it again")
            sleep(5)

    try:
        # try to communicate with server few times
        sock.send("ready".encode())
        response = sock.recv(1024).decode()

        is_previous_command_done = True
        is_failed = False
        is_aborted = False
        is_finished = False
        commands_to_skip = 0

        if response == "ready":

            if not is_workable_condition():
                raise Exception("Client has non-workable state")

            for action in case["client_actions"]:
                if commands_to_skip > 0:
                    commands_to_skip -= 1
                    continue

                parts = action.split(' ', 1)
                command = parts[0]
                if len(parts) > 1:
                    args = shlex.split(parts[1])
                else:
                    args = None

                if command == "execute_cmd":
                    execute_cmd(sock, action)
                elif command == "check_game":
                    check_game(sock, action)
                elif command == "make_screen":
                    if args is not None:
                        make_screen(screens_path)
                    else:
                        make_screen(screens_path, screen_name="{}_try_{}".format(*args, current_try))
                elif command == "move":
                    move(*args)
                elif command == "click":
                    click()
                elif command == "sleep":
                    do_sleep(*args)
                elif command == "press_keys":
                    press_keys(*args)
                elif command == "press_keys_server":
                    press_keys_server(sock, action)
                elif command == "sleep_and_screen":
                    sleep_and_screen(*args, screens_path)
                elif command == "finish":
                    is_finished = True
                    finish(sock)
                elif command == "skip_if_done":
                    if is_previous_command_done:
                        commands_to_skip += int(args[0])
                else:
                    raise Exception("Unknown client command: {}".format(command))

                if command in SERVER_ACTIONS:
                    response = sock.recv(1024).decode()

                    if response == "done":
                        is_previous_command_done = True
                        pass
                    elif response == "failed":
                        is_previous_command_done = False

                        if command != "check_game":
                            raise Exception("Action failed on server side")
                    elif response == "abort":
                        is_aborted = True
                        raise Exception("Server sent abort status")
                    else:
                        raise Exception("Unknown server status: {}".format(response))

        elif response == "fail":
            raise Exception("Server has non-workable state")
        else:
            raise Exception("Unknown server answer: {}".format(response))
    except Exception as e:
        is_failed = True
        main_logger.error("Fatal error. Case will be aborted:".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

        raise e
    finally:
        if is_failed:
            abort(sock)
        elif is_aborted:
            pass
        elif is_finished:
            pass
        else:
            next_case(sock)

        sock.close()
