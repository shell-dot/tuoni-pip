import random
from tuoni.TuoniListener import *

class TuoniListenerPlugin:
    """
    Class providing data and functionality of the listener plugin

    Attributes:
        name (str): Name of the listener plugin
        vendor (str): Vendor of the listener plugin
        description (str): Listener plugin description
        plugin_id (str): Listener plugin id
        conf_schema (dict): Configuration schema
        conf_examples (dict): Configuration examples
    """
    
    def __init__(self, conf, c2):
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

    def create(self, new_listener_conf, new_listener_name=None):
        """
        Create new listener

        Attributes:
            new_listener_conf (dict): Listener configuration
            new_listener_name (bool): Listener name

        Returns:
            TuoniListener: Object referencing the created listener
        """
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
        """
        Default configuration
        
        Returns:
            dict: Default configuration or empty dict
        """
        if "default" in self.conf_examples:
            return self.conf_examples["default"]
        return {}  #Might change but let's say for now that if no "default" conf then empty conf is same

    def get_minimal_conf(self):
        """
        Minimal configuration
        
        Returns:
            dict: Minimal configuration or empty dict
        """
        return self.get_default_conf()

