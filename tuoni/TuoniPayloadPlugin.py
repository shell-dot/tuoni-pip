import random
from tuoni.TuoniListener import *

class TuoniPayloadPlugin:
    """
    Class providing data of the payload plugin

    Attributes:
        name (str): Name of the payload plugin
        vendor (str): Vendor of the payload plugin
        description (str): Payload plugin description
        plugin_id (str): Payload plugin id
        templates (list): Available payload templates
    """
    
    def __init__(self, conf, c2):
        self.name = conf["info"]["name"]
        self.vendor = conf["info"]["vendor"]
        self.description = conf["info"]["description"]
        self.plugin_id = conf["identifier"]["id"]
        self.templates = []
        for payloadTemplate in conf["payloads"]:
            self.templates.append(payloadTemplate)
        self.c2 = c2

