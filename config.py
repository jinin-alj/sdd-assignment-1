import os

DEFAULT_PORT = 8000
DEFAULT_DATA_DIR = "./data"
MIN_PORT = 1
MAX_PORT = 65535

def get_port() -> int:
    """return the port from PORT or the default if it is missing or invalid"""
    port_text = os.environ.get("PORT", str(DEFAULT_PORT))
    try:
        return int(port_text)
    except ValueError:
        print(f"PORT={port_text} is not a number, using {DEFAULT_PORT}")
        return DEFAULT_PORT
    if port < MIN_PORT or port > MAX_PORT:
        print(f"PORT={port} is out of range, using {DEFAULT_PORT}")
        return DEFAULT_PORT
    return port

def get_data_dir() -> str:
    """return the folder where the SQLite file will be stored"""
    return os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)
