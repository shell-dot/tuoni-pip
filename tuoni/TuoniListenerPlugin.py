import random
import os
from tuoni.TuoniListener import *

class TuoniListenerPlugin:
    """
    A class that provides data and functionality for a listener plugin.

    Attributes:
        name (str): The name of the listener plugin.
        vendor (str): The vendor of the listener plugin.
        description (str): A description of the listener plugin.
        plugin_id (str): The unique identifier of the listener plugin.
        conf_schema (dict): The configuration schema for the listener plugin.
        conf_examples (dict): Examples of valid configurations for the listener plugin.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the listener plugin class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.name = conf["info"]["name"]
        self.vendor = conf["info"]["vendor"]
        self.description = conf["info"]["description"]
        self.plugin_id = conf["identifier"]["id"]
        self.conf_schema = conf["configurationSchema"]
        self.conf_examples = {}
        if "defaultConfiguration" in conf:
            self.conf_examples["default"] = conf["defaultConfiguration"]
        if "exampleConfigurations" in conf:
            for example in conf["exampleConfigurations"]:
                self.conf_examples[example["name"]] = example["configuration"]
        self.c2 = c2

    def create(self, new_listener_conf, new_listener_name=None, keystore_path=None):
        """
        Create a new listener.

        Args:
            new_listener_conf (dict): The configuration for the new listener.
            new_listener_name (str): The name to assign to the new listener.
            keystore_path (str): Path to a keystore file that will be used by the listener.

        Returns:
            TuoniListener: An object representing the newly created listener.

        Examples:
            >>> http_listener_plugin = tuoni_server.load_listener_plugins()[
            >>>     "shelldot.listener.agent-reverse-http"
            >>> ]
            >>> conf = http_listener_plugin.conf_examples["default"]
            >>> conf["sleep"] = 2
            >>> conf["instantResponses"] = True
            >>> listener = http_listener_plugin.create(conf)
        """
        json_data = {
            "plugin": self.plugin_id,
            "configuration": new_listener_conf
        }
        file_data = None

        if new_listener_name is not None:
            json_data["name"] = new_listener_name

        if keystore_path is not None:
            with open(keystore_path, "rb") as f:
                keystore_content = f.read()

            file_data = { "keystoreFile": ( os.path.basename(keystore_path), keystore_content ) }

        listener_data = self.c2.request_post("/api/v1/listeners", json_data, file_data)
        listener_obj = TuoniListener(listener_data, self.c2)
        return listener_obj

    def get_default_conf(self):    
        """
        Retrieve the default configuration for the listener plugin.

        Returns:
            dict: The default configuration settings, or an empty dictionary if none are defined.
        """
        if "default" in self.conf_examples:
            return self.conf_examples["default"]
        return {}  #Might change but let's say for now that if no "default" conf then empty conf is same

    def get_minimal_conf(self):
        """
        Retrieve the minimal configuration for the listener plugin.

        Returns:
            dict: The minimal configuration settings, or an empty dictionary if none are defined.
        """
        return self.get_default_conf()

