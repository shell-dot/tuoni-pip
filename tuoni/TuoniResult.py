from tuoni.TuoniResultPart import *


class TuoniResult:
    """
    Class providing data of the command result

    Attributes:
        status (str): Status of the result
        error_message (str): Error message of the result
        received (datetime): When was result received
        parts (list[TuoniResultPart]): List of result parts
    """
    
    def __init__(self, conf, c2):
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


