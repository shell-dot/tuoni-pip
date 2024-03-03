import time
from tuoni.TuoniExceptions import *
from tuoni.TuoniResult import *


class TuoniCommand:
    def __init__(self, conf, c2):
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.command_id = conf["id"]
        self.configuration = conf["configuration"]
        self.execConf = conf["execConf"]
        self.created = conf["created"]
        self.sent = conf["sent"]
        self.result = conf["result"]

    def reload(self):
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get("/api/v1/commands/%d" % self.command_id)
        self._load_conf(data)

    def result_status_done(self, reload = True):
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        self.reload()
        if self.result is None:
            return False
        if self.result["status"] == "ongoing":
            return False
        return True

    def result_status_ongoing(self, reload = True):
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        self.reload()
        if self.result is None:
            return False
        if self.result["status"] == "ongoing":
            return True
        return False

    def get_result(self, reload = True):
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        self.reload()
        if self.result is None:
            return None
        return TuoniResult(self.result, self.c2)

    def wait_result(self, interval = 1, maxWait = 0):
        self.reload()
        while self.result is None:
            time.sleep(interval)
            self.reload()
            if maxWait > 0:
                maxWait -= interval
                if maxWait <= 0:
                    return None
        return TuoniResult(self.result, self.c2)

