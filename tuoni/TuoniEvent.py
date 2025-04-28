import time
from tuoni.TuoniExceptions import ExceptionTuoniDeleted


class TuoniEvent:
    """
    A class that provides data and functionality for a event.

    Attributes:
        event_id (GUID): The unique identifier of the event.
        eventType (string): Type of the event.
        time (*): Event type.
        actor (dict): Actor that event is about.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the event class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.event_id = conf["id"]
        self.eventType = conf["eventType"]
        self.time = conf["time"]
        self.actor = conf["actor"]

    def reload(self):
        """
        Reload the command data from the C2 server.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/event/{self.event_id}")
        self._load_conf(data)