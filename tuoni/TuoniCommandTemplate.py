import random
from tuoni.TuoniListener import *


class TuoniCommandTemplate:
    """
    A class that provides data and functionality for a command template.

    Attributes:
        id (str): The unique identifier of the command template.
        name (str): The name of the command template.
        plugin_id (str): The unique identifier of the command plugin.
        scope (str): The scope of the command template.
        qualifiedName (str): The qualified name of the command template.
        fullyQualifiedName (str): The fully qualified name of the command template.
        description (str): A description of the command template.
        conf_schema (dict): The configuration schema for the command template.
        conf_examples (dict): Examples of valid configurations for the command template.
    """

    def __init__(self, conf, c2):
        """
        Constructor for the command template class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.id = conf["id"]
        self.name = conf["name"]
        self.plugin_id = conf["pluginId"]
        self.scope = conf["scope"]
        self.qualifiedName = conf["qualifiedName"]
        self.fullyQualifiedName = conf["fullyQualifiedName"]
        self.description = conf["description"]
        self.conf_schema = conf["configurationSchema"]
        self.conf_examples = {}
        if "defaultConfiguration" in conf:
            self.conf_examples["default"] = conf["defaultConfiguration"]
        if "exampleConfigurations" in conf:
            for example in conf["exampleConfigurations"]:
                self.conf_examples[example["name"]] = example["configuration"]
        self.c2 = c2

    def get_default_conf(self):
        """
        Retrieve the default configuration for the command template.

        Returns:
            dict: The default configuration settings, or an empty dictionary if none are defined.
        """
        if "default" in self.conf_examples:
            return self.conf_examples["default"]
        return {}  # Might change but let's say for now that if no "default" conf then empty conf is same

    def get_minimal_conf(self):
        """
        Retrieve the minimal configuration for the command template.

        Returns:
            dict: The minimal configuration settings, or an empty dictionary if none are defined.
        """
        return self.get_default_conf()
