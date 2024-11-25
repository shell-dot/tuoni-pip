from tuoni.TuoniResultPart import *


class TuoniResult:
    """
    A class that provides data for a command result.

    Attributes:
        status (str): The status of the result.
        error_message (str): The error message, if any, for the result.
        received (str): The time, in string format, indicating when the result was received.
        parts (list[TuoniResultPart]): A list of parts that make up the result.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the result class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.c2 = c2
        self._load_conf(conf)

    def _load_conf(self, conf):
        self.status = conf["status"]
        self.error_message = conf["errorMessage"]
        self.received = conf["received"]
        self.parts = []
        for part_conf in conf["childResults"]:
            part_obj = TuoniResultPart(part_conf, self.c2)
            self.parts.append(part_obj)


