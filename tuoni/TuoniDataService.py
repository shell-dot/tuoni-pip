import time
from tuoni.TuoniExceptions import *


class TuoniDataService:
    """
    A class that provides data and functionality for a service data model entry.

    Attributes:
        id (GUID): The unique identifier (GUID) for the service.
        address (str): The service address.
        port (int): Port number.
        protocol (str): Service protocol.
        banner (str): Service banner.
        note (str): Additional notes.
        status (str): Status of the entry.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the service data class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.id = conf["id"]
        self.address = conf["address"]
        self.port = conf["port"]
        self.protocol = conf["protocol"]
        self.banner = conf["banner"]
        self.note = conf["note"]
        self.status = conf["status"]

    def reload(self):
        """
        Reload the service data from the C2 server.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get("/api/v1/discovery/service/%s" % self.id)
        self._load_conf(data)

    def archive(self):
        """
        Archive the file.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_post("/api/v1/discovery/services/bulk-archive", {"serviceIds": [self.id]})

    def update(self):
        """
        Update data on the server.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        req = {
            "protocol": self.protocol,
            "banner": self.banner,
            "note": self.note
        }
        self.c2.request_patch("/api/v1/discovery/service/%s" % self.id, req)
        self.reload()

