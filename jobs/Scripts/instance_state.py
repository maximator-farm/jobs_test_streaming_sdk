class InstanceState:
    def __init__(self):
        self.prev_action_done = True
        self.non_workable_client = False
        self.non_workable_server = False
        self.is_aborted_client = False
        self.is_aborted_server = False

        self.commands_to_skip = 0

    def format_current_state(self):
        return f"""
            Previous actions done: {self.prev_action_done}
            Client has non workable state: {self.non_workable_client}
            Server has non workable state: {self.non_workable_server}
            Is case aborted by client: {self.is_aborted_client}
            Is case aborted by server: {self.is_aborted_server}
        """
