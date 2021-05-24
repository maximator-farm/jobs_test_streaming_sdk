import socket
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


def start_server_side_tests(args, case, sync_port):
	# configure socket
    sock = socket.socket()
    sock.bind(("", sync_port))
    # max one connection
    sock.listen(1)
    connection, address = sock.accept()

    data = sock.recv(1024).decode()
    main_logger.info(data)

    sock.send("ready")
