import socket
import sys
import os
from time import sleep
import psutil
from subprocess import PIPE
import traceback
import win32gui
import win32api
import pyautogui
import pydirectinput
from threading import Thread
from utils import close_process, collect_traces, parse_arguments
from actions import *

pyautogui.FAILSAFE = False


class ExecuteCMD(Action):
    def parse(self):
        self.processes = self.params["processes"]
        self.cmd_command = self.params["arguments_line"]

    @Action.server_action_decorator
    def execute(self):
        process = psutil.Popen(self.cmd_command, stdout=PIPE, stderr=PIPE, shell=True)
        self.processes[self.cmd_command] = process
        self.logger.info("Executed: {}".format(self.cmd_command))

        return True


class CheckWindow(Action):
    def parse(self):
        self.processes = self.params["processes"]
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.window_name = parsed_arguments[0]
        self.process_name = parsed_arguments[1]
        self.is_game = (self.params["command"] == "check_game")

    @Action.server_action_decorator
    def execute(self):
        result = False

        window = win32gui.FindWindow(None, self.window_name)

        if window is not None and window != 0:
            self.logger.info("Window {} was succesfully found".format(self.window_name))

            if self.is_game:
                try:
                    win32gui.ShowWindow(window, 4)
                    win32gui.SetForegroundWindow(window)
                except Exception as e1:
                    self.logger.error("Failed to make window foreground: {}".format(str(e1)))
                    self.logger.error("Traceback: {}".format(traceback.format_exc()))
        else:
            self.logger.error("Window {} wasn't found at all".format(self.window_name))
            return False

        for process in psutil.process_iter():
            if self.process_name in process.name():
                self.logger.info("Process {} was succesfully found".format(self.process_name))
                self.processes[self.process_name] = process
                result = True
                break
        else:
            self.logger.info("Process {} wasn't found at all".format(self.process_name))
            result = False

        return result


def close_processes(processes, logger):
    result = True

    for process_name in processes:
        try:
            close_process(processes[process_name])
        except Exception as e:
            logger.error("Failed to close process: {}".format(str(e)))
            logger.error("Traceback: {}".format(traceback.format_exc()))
            result = False

    return result


class PressKeysServer(Action):
    def parse(self):
        self.keys_string = self.params["arguments_line"]

    @Action.server_action_decorator
    def execute(self):
        keys = keys_string.split()

        for key in keys:
            duration = 0

            if "_" in key:
                parts = key.split("_")
                key = parts[0]
                duration = int(parts[1])

            self.logger.info("Press: {}. Duration: {}".format(key, duration))

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

        return True


class Abort(Action):
    def parse(self):
        self.processes = self.params["processes"]

    @Action.server_action_decorator
    def execute(self):
        result = close_processes(self.processes, self.logger)

        if result:
            self.logger.info("Processes was succesfully closed")
        else:
            self.logger.error("Failed to close processes")

        return result

    
    def analyze_result(self):
        self.state.is_aborted = True
        raise ClientActionException("Client sent abort command")


class Retry(Action):
    @Action.server_action_decorator
    def execute(self):
        return True

    def analyze_result(self):
        self.state.is_aborted = True
        raise ClientActionException("Client sent abort command")


class NextCase(Action):
    @Action.server_action_decorator
    def execute(self):
        return True

    def analyze_result(self):
        self.state.wait_next_command = False


class ClickServer(Action):
    def parse(self):
        parsed_arguments = parse_arguments(self.params["arguments_line"])
        self.x_description = parsed_arguments[0]
        self.y_description = parsed_arguments[1]

    @Action.server_action_decorator
    def execute(self):
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

        self.logger.info("Click at x = {}, y = {}".format(x, y))

        pyautogui.moveTo(x, y)
        sleep(1)
        pyautogui.click()

        return True


class DoTestActions(Action):
    def parse(self):
        self.game_name = self.params["game_name"]

    def execute(self):
        try:
            if self.game_name == "borderlands3":
                pass
            elif self.game_name == "valorant":
                sleep(2.0)
                pydirectinput.keyDown("space")
                sleep(0.1)
                pydirectinput.keyUp("space")            
            elif self.game_name == "apexlegends":
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
            elif self.game_name == "lol":
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
            self.logger.error("Failed to do test actions: {}".format(str(e)))
            self.logger.error("Traceback: {}".format(traceback.format_exc()))


class GPUView(Action):
    def parse(self):
        self.collect_traces = self.params["args"].collect_traces
        self.archive_path = self.params["archive_path"]
        self.archive_name = self.params["case"]["case"]

    def execute(self):
        if collect_traces == "True":
            self.sock.send("start".encode("utf-8"))

            try:
                collect_traces(archive_path, archive_name + "_server.zip")
            except Exception as e:
                self.logger.warning("Failed to collect GPUView traces: {}".format(str(e)))
                self.logger.warning("Traceback: {}".format(traceback.format_exc()))
        else:
            self.sock.send("skip".encode("utf-8"))
