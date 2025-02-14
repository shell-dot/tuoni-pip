import time
from tuoni.TuoniExceptions import *


class TuoniDataCredential:
    """
    A class that provides data and functionality for a credential data model entry.

    Attributes:
        id (GUID): The unique identifier (GUID) for the credential.
        username (str): The username.
        password (str): The password.
        host (str): Host where credential works.
        realm (str): Credential realm.
        source (str): Source of the credential.
        note (str): Additional notes.
        status (str): Status of the entry.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the credential data class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.id = conf["id"]
        self.username = conf["username"]
        self.password = conf["password"]
        self.host = conf["host"]
        self.realm = conf["realm"]
        self.source = conf["source"]
        self.note = conf["note"]
        self.status = conf["status"]

    def reload(self):
        """
        Reload the credential data from the C2 server.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get("/api/v1/discovery/credential/%s" % self.id)
        self._load_conf(data)

    def archive(self):
        """
        Archive the file.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_post("/api/v1/discovery/credentials/bulk-archive", {"credentialIds": [self.id]})

    def update(self):
        """
        Update data on the server.
        """
        if self.id is None:
            raise ExceptionTuoniDeleted("")
        req = {
            "source": self.source,
            "note": self.note
        }
        self.c2.request_patch("/api/v1/discovery/credential/%s" % self.id, req)
        self.reload()

