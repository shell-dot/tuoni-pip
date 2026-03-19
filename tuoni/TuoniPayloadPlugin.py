import random
from tuoni.TuoniListener import *
from tuoni.TuoniPayloadTemplate import *

class TuoniPayloadPlugin:
    """
    A class that provides data for a payload plugin.

    Attributes:
        name (str): The name of the payload plugin.
        vendor (str): The vendor of the payload plugin.
        description (str): A description of the payload plugin.
        plugin_id (str): The unique identifier of the payload plugin.
        templates (list): A list of available payload templates.

    Examples:
        Iterate over payload plugins, inspect their templates, and create a payload
        for each type defined in the template's configuration schema:

        >>> payload_plugins = tuoni_c2.load_payload_plugins()
        >>> for plugin in payload_plugins.values():
        ...     print(f"Plugin: {plugin.name} ({plugin.plugin_id})")
        ...     for template in plugin.templates:
        ...         print(f"  Template: {template.id}")
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
        ...             print(f"    Created payload ID: {payload.payload_id}")
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
        for payloadTemplateName, payloadTemplate in conf["payloads"].items():
            self.templates.append(TuoniPayloadTemplate(payloadTemplate, c2))
        self.c2 = c2

