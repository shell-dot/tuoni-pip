import random
from TuoniLib.TuoniListener import *

class TuoniListenerPlugin:
    def __init__(self, conf, c2):
        self.name = conf["info"]["name"]
        self.vendor = conf["info"]["vendor"]
        self.description = conf["info"]["description"]
        self.plugin_id = conf["identifier"]["id"]
        self.conf_schema = conf["configurationSchema"]
        self.conf_default = conf["defaultConfiguration"]
        self.c2 = c2

    def create(self, new_listener_conf, new_listener_name=None):
        json_data = {
            "plugin": self.plugin_id,
            "configuration": new_listener_conf
        }
        if new_listener_name is not None:
            json_data["name"] = new_listener_name
        listener_data = self.c2.request_post("/api/v1/listeners", json_data)
        listener_obj = TuoniListener(listener_data, self.c2)
        return listener_obj

    def get_default_conf(self):
        return self.conf_default

    def get_minimal_conf(self):
        return self.conf_default

