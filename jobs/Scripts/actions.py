from abc import ABC, abstractmethod


class ClientActionException(Exception):
    def __init__(self, message = ""):
        self.message = message
        super().__init__(self.message)


class ServerActionException(Exception):
    def __init__(self, message = ""):
        self.message = message
        super().__init__(self.message)


class Action(ABC):
	def __init__(self, sock, params, state, logger):
        self.sock = sock
        self.params = params
        self.state = state
        self.logger = logger

    # parse all necessary params before execution
    def parse(self):
        pass

    # execute the current action
    @abstractmethod
    def execute(self):
        pass

    # analyze the result and the state and do some additional actions based on it
    def analyze_result(self):
        pass

    def wait_server_answer(self, analyze_answer = True, abort_if_fail = True):
        response = self.sock.recv(1024).decode("utf-8")

        logger.info("Server answer: {}".format(response))

        if analyze_result:
            self.state.prev_action_done = (response == "done")

            if response == "abort":
                self.state.is_aborted_server = True
                raise ServerActionException("Server sent abort status")
            elif response == "failed":
                if abort_if_fail:
                    raise ServerActionException("Action failed on server side")
            else:
                raise ServerActionException("Unknown server status: {}".format(response))
