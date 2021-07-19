class InstanceState:
	def __init__(self):
		self.flags = {
		    "prev_action_done": True,
            "non_workable_client": False,
            "non_workable_server": False,
            "is_aborted_client": False,
            "is_aborted_server": False
		}

		self.commands_to_skip = 0

    def get_current_state():
        return self.flags

    def format_current_state():
    	return f"""
            Previous actions done: {self.flags.prev_action_done}
            Client has non workable state: {self.flags.non_workable_client}
            Server has non workable state: {self.flags.non_workable_server}
            Is case aborted by client: {self.flags.is_aborted_client}
            Is case aborted by server: {self.flags.is_aborted_server}
    	"""
