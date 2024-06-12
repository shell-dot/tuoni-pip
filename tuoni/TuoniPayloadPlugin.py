import random
from tuoni.TuoniListener import *

class TuoniPayloadPlugin:
    def __init__(self, conf, c2):
        self.name = conf["info"]["name"]
        self.vendor = conf["info"]["vendor"]
        self.description = conf["info"]["description"]
        self.plugin_id = conf["identifier"]["id"]
        self.templates = []
        for payloadTemplate in conf["payloads"]:
            self.templates.append(payloadTemplate)
        self.c2 = c2

