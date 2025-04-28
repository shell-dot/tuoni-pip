import time
from tuoni.TuoniExceptions import *


class TuoniAlias:
    """
    A class that provides data and functionality for a command alias.

    Attributes:
        alias_id (GUID): The unique identifier (GUID) for the alias.
        name (str): The name of the alias.
        qualifiedName (str): The qualified name of the alias.
        fullyQualifiedName (str): The fully qualified name of the alias.
        description (str): A description of the alias.
        fixedConfiguration (dict): The fixed configuration settings for the base command.
        pluginVersion (str): The version of the associated plugin.
        baseTemplate (dict): The base template used for the alias.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the alias class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.alias_id = conf["id"]
        self.name = conf["name"]
        self.qualifiedName = conf["qualifiedName"]
        self.fullyQualifiedName = conf["fullyQualifiedName"]
        self.description = conf["description"]
        self.fixedConfiguration = conf["fixedConfiguration"]
        self.pluginVersion = conf["pluginVersion"]
        self.baseTemplate = conf["baseTemplate"]

    def reload(self):
        """
        Reload the alias data from the C2 server.
        """
        if self.alias_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/command-alias/{self.alias_id}")
        self._load_conf(data)

    def delete(self):
        """
        Delete the alias.
        """
        if self.alias_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_delete(f"/api/v1/command-alias/{self.alias_id}")
        self._load_conf(data)

