import random
from tuoni.TuoniListener import *

class TuoniPayloadPlugin:
    """
    A class that provides data for a payload plugin.

    Attributes:
        name (str): The name of the payload plugin.
        vendor (str): The vendor of the payload plugin.
        description (str): A description of the payload plugin.
        plugin_id (str): The unique identifier of the payload plugin.
        templates (list): A list of available payload templates.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the payload plugin class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.name = conf["info"]["name"]
        self.vendor = conf["info"]["vendor"]
        self.description = conf["info"]["description"]
        self.plugin_id = conf["identifier"]["id"]
        self.templates = []
        for payloadTemplate in conf["payloads"]:
            self.templates.append(payloadTemplate)
        self.c2 = c2

