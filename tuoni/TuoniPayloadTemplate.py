import random
from tuoni.TuoniListener import *


class TuoniPayloadTemplate:
    """
    A class that provides data and functionality for a payload template.

    Attributes:
        id (str): The unique identifier of the payload template.
        name (str): The name of the payload template.
        status (str): The status of the payload template.
        description (str): A description of the payload template.
        payload_type (str): The type of payload associated with the payload template.
        plugin_id (str): The unique identifier of the payload plugin.
        example_configurations (list[dict]): A list of example configurations for the payload template.
        conf_schema (dict): The configuration schema for the payload template.
        available_listeners (list[TuoniListener]): A list of available listeners that can be used with this payload template.

    Examples:
        Inspect a template's configuration schema and create a payload for each
        supported type:

        >>> payload_plugins = tuoni_c2.load_payload_plugins()
        >>> for plugin in payload_plugins.values():
        ...     for template in plugin.templates:
        ...         print(f"Template: {template.id}, type: {template.payload_type}")
        ...         type_values = (
        ...             template.conf_schema
        ...             .get("properties", {})
        ...             .get("type", {})
        ...             .get("enum", [])
        ...         )
        ...         for type_value in type_values:
        ...             payload = TuoniPayload(
        ...                 conf={
        ...                     "templateId": template.id,
        ...                     "configuration": {"type": type_value}
        ...                 },
        ...                 c2=tuoni_c2
        ...             )
        ...             payload.create(listener_id=1)
        ...             data = payload.download()
        ...             with open(f"{payload.payload_id}.bin", "wb") as f:
        ...                 f.write(data)
        ...             payload.delete()
    """

    def __init__(self, conf, c2):
        """
        Constructor for the command template class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.id = conf["name"]
        self.name = conf["name"]
        self.status = conf["status"]
        self.description = conf["description"]
        self.payload_type = conf["payloadType"]
        self.plugin_id = conf["pluginId"]
        self.example_configurations = conf["exampleConfigurations"]
        self.conf_schema = conf["configurationSchema"]
        self.available_listeners = []
        if "availableListeners" in conf:
            for listener in conf["availableListeners"]:
                self.available_listeners.append(TuoniListener(listener, c2))
        self.c2 = c2


