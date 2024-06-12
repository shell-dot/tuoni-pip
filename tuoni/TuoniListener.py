from tuoni.TuoniExceptions import *

class TuoniListener:
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
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_put("/api/v1/listeners/%s/stop" % self.listener_id)
        self._load_conf(data)

    def start(self):
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_put("/api/v1/listeners/%d/stop" % self.listener_id)
        self._load_conf(data)

    def delete(self):
        if self.listener_id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_delete("/api/v1/listeners/%d" % self.listener_id)
        self.listener_id = None


