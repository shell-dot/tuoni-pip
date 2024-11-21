import time
from tuoni.TuoniExceptions import *


class TuoniAlias:
    """
    Class providing data and functionality of the connected alias

    Attributes:
        alias_id (Guid): Alias GUID
        name (str): Name of the alias
        qualifiedName (str): Qualified name
        fullyQualifiedName (str): Full qualified name
        description (str): Description of the alias
        fixedConfiguration (dict): Fixed configuration of the base command
        pluginVersion (str): Version of the plugin
        baseTemplate (dict): Base template
    """
    
    def __init__(self, conf, c2):
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
        Reload data from C2
        """
        if self.alias_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get("/api/v1/command-alias/%s" % self.alias_id)
        self._load_conf(data)

    def delete(self):
        """
        Deletes alias
        """
        if self.alias_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_delete("/api/v1/command-alias/%s" % self.alias_id)
        self._load_conf(data)

