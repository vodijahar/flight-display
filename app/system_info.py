import socket
import subprocess


def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["hostname", "-I"],
            check=False,
            capture_output=True,
            text=True,
        )
        for address in result.stdout.split():
            if "." in address and not address.startswith("127."):
                return address
    except Exception:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                return address
    except Exception:
        pass

    return ""
