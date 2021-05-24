import socket
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *


def start_client_side_tests(args, case, ip_address, sync_port):
    sock = socket.socket()
    sock.connect((ip_address, sync_port))

    # try to communicate with server few times
    max_attemps = 5
    current_attempt = 0

    while current_attempt < max_attemps:
        sock.send("ready")
        sock.settimeout(10.0)
        try:
            data = sock.recv(1024).decode()
        except socket.timeout:
            current_attempt += 1

        main_logger.info(data)

        if data == "ready":
            break

    
