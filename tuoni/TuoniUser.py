import time
from tuoni.TuoniExceptions import *


class TuoniUser:
    """
    Class providing data and functionality of the users

    Attributes:
        username (str): Username
        enabled (bool): Is user enabled
        authorities (list[str]): List of authorities given to the user
    """
    def __init__(self, conf, c2):
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.username = conf["username"]
        self.enabled = conf["enabled"]
        self.authorities = conf["authorities"]

    def reload(self):
        """
        Reload data from server
        """
        if self.alias_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get("/api/v1/users/%s" % self.username)
        self._load_conf(data)

    def disable(self):
        """
        Disable user
        """
        data = {"enabled": False, "authorities": self.authorities}
        data = self.c2.request_put("/api/v1/users/%s" % self.username, data)
        self._load_conf(data)

    def enable(self):
        """
        Enable user
        """
        data = {"enabled": True, "authorities": self.authorities}
        data = self.c2.request_put("/api/v1/users/%s" % self.username, data)
        self._load_conf(data)

    def set_authorities(self, authorities):
        """
        Change user authorities
        """
        data = {"authorities": authorities, "enabled": self.enabled}
        data = self.c2.request_put("/api/v1/users/%s" % self.username, data)
        self._load_conf(data)

    def set_password(self, new_password):
        """
        Set user password
        """
        data = {"newPassword": new_password}
        data = self.c2.request_put("/api/v1/users/%s/password" % self.username, data)
        
    

