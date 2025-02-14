from tuoni.TuoniExceptions import *

class TuoniListener:
    """
    A class that provides data and functionality for a created listener.

    Attributes:
        listener_id (int): The unique identifier of the listener.
        name (str): The name of the listener.
        info (str): Information about the listener.
        status (str): The current status of the listener.
        plugin (str): The plugin associated with the listener.
        configuration (dict): The configuration settings for the listener.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the listener class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.listener_id = conf["id"]
        self.name = conf["name"]
        self.info = conf["info"]
        self.status = conf["status"]
        self.plugin = conf["plugin"]
        self.configuration = conf["configuration"]

    def stop(self):
        """
        Stop the listener.
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_put("/api/v1/listeners/%s/stop" % self.listener_id)
        self._load_conf(data)

    def start(self):
        """
        Start the listener.
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_put("/api/v1/listeners/%d/start" % self.listener_id)
        self._load_conf(data)

    def delete(self):
        """
        Delete the listener.
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_delete("/api/v1/listeners/%d" % self.listener_id)
        self.listener_id = None

    def reload(self):
        """
        Reload the listener data from the C2 server.
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get("/api/v1/listeners/%d" % self.listener_id)
        self._load_conf(data)

    def update(self,):
        """
        Update listener on the server.
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        req = {
            "configuration": self.configuration,
            "name": self.name
        }
        self.c2.request_patch("/api/v1/listeners/%d" % self.listener_id, req)
        self.reload()


