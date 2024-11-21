from tuoni.TuoniExceptions import *

class TuoniListener:
    """
    Class providing data and functionality of the created listener

    Attributes:
        listener_id (int): Listener id
        name (str): Name of the listener
        info (str): Information of the listener
        status (str): Status of the listener
        plugin (str): Listener plugin of the listener
        configuration (dict): Listener configuration
    """
    
    def __init__(self, conf, c2):
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
        Stop listener
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_put("/api/v1/listeners/%s/stop" % self.listener_id)
        self._load_conf(data)

    def start(self):
        """
        Start listener
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_put("/api/v1/listeners/%d/stop" % self.listener_id)
        self._load_conf(data)

    def delete(self):
        """
        Delete listener
        """
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_delete("/api/v1/listeners/%d" % self.listener_id)
        self.listener_id = None


