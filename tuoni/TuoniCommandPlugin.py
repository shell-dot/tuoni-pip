import random
from tuoni.TuoniCommandTemplate import *


class TuoniCommandPlugin:
    """
    A class that provides data and functionality for a command plugin.

    Attributes:
        name (str): The name of the command plugin.
        vendor (str): The vendor of the command plugin.
        description (str): A description of the command plugin.
        plugin_id (str): The unique identifier of the command plugin.
        commands (list[TuoniCommandTemplate]): A list of command templates associated with the plugin.

    """

    def __init__(self, conf, c2):
        """
        Constructor for the command plugin class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.name = conf["info"]["name"]
        self.vendor = conf["info"]["vendor"]
        self.description = conf["info"]["description"]
        self.plugin_id = conf["identifier"]["id"]
        self.c2 = c2
        self.commands = []
        for command_name in conf["commands"]:
            self.commands.append(TuoniCommandTemplate(
                conf["commands"][command_name], c2))
