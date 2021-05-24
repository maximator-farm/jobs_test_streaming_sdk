import socket
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


def start_client_side_tests(args, case, ip_address, sync_port):
    sock = socket.socket()
    sock.connect((ip_address, sync_port))

    # try to communicate with server few times
    sock.send("ready")
    data = sock.recv(1024).decode()

    main_logger.info(data)
