from TuoniLib.TuoniResultPart import *


class TuoniResult:
    def __init__(self, conf, c2):
        self.c2 = c2
        self._load_conf(conf)

    def _load_conf(self, conf):
        self.status = conf["status"]
        self.received = conf["received"]
        self.parts = []
        for part_conf in conf["childResults"]:
            part_obj = TuoniResultPart(part_conf, self.c2)
            self.parts.append(part_obj)


