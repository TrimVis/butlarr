import os
import pickle
import re

from pathlib import Path
from loguru import logger
from threading import Lock

BASE_PATH = os.path.join(
    Path(os.path.dirname(os.path.realpath(__file__))).parent, "data", "session"
)


class SessionDatabase:
    lock = Lock()
    base_path: Path

    def __init__(self, base_path=BASE_PATH):
        self.base_path = Path(base_path)
        # Make sure the path exists
        self.base_path.mkdir(exist_ok=True, parents=True)

    def add_session_entry(self, session_id, value, *, key=None):
        file_name = f"{session_id}.{key}" if key else session_id
        file_path = os.path.join(self.base_path, file_name)
        with open(file_path, mode="wb+") as file:
            pickle.dump(value, file)

    def get_session_entry(self, session_id, *, key=None):
        file_name = f"{session_id}.{key}" if key else session_id
        file_path = os.path.join(self.base_path, file_name)
        with open(file_path, mode="rb+") as file:
            return pickle.load(file)

    def clear_session(self, session_id):
        all_files = os.listdir(self.base_path)

        file_regex = r"{session_id}\..*"
        for file in all_files:
            if not re.match(file_regex, file):
                continue

            file_path = os.path.join(self.base_path, file)
            os.remove(file_path)
