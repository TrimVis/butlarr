from .secrets import APIS

from ..services."<FILE0>" import "<CLASS0>"
from ..services."<FILE1>" import "<CLASS1>"

SERVICES = [
    "<CLASS0>"(
        commands=["<CMD0>"],
        api_host=APIS.get("<CMD0>")[0],
        api_key=APIS.get("<CMD0>")[1],
    ),
    "<CLASS1>"(
        commands=["<CMD1>"],
        api_host=APIS.get("<CMD1>")[0],
        api_key=APIS.get("<CMD1>")[1],
    ),
]
