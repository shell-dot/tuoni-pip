import time
from tuoni.TuoniExceptions import *


class TuoniDataHost:
    """
    A class that provides data and functionality for a host data model entry.

    Attributes:
        id (GUID): The unique identifier (GUID) for the host.
        address (str): The host address.
        name (str): Given name to the host.
        note (str): Additional notes.
        status (str): Status of the entry.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the host data class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.id = conf["id"]
        self.address = conf["address"]
        self.name = conf["name"]
        self.note = conf["note"]
        self.status = conf["status"]

    def reload(self):
        """
        Reload the host data from the C2 server.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/discovery/host/{self.id}")
        self._load_conf(data)

    def archive(self):
        """
        Archive the host.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_post("/api/v1/discovery/hosts/bulk-archive", {"hostIds": [self.id]})

    def update(self):
        """
        Update data on the server.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        req = {
            "name": self.name,
            "note": self.note
        }
        self.c2.request_patch(f"/api/v1/discovery/host/{self.id}", req)
        self.reload()

