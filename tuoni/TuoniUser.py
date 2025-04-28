import time
from tuoni.TuoniExceptions import *


class TuoniUser:
    """
    A class that provides data and functionality for users.

    Attributes:
        username (str): The username of the user.
        enabled (bool): Indicates whether the user is enabled.
        authorities (list[str]): A list of authorities or roles assigned to the user.
    """
    def __init__(self, conf, c2):
        """
        Constructor for the result part class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.username = conf["username"]
        self.enabled = conf["enabled"]
        self.authorities = conf["authorities"]

    def reload(self):
        """
        Reload the user data from the C2 server.
        """
        if self.alias_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/users/{self.username}")
        self._load_conf(data)

    def disable(self):
        """
        Disable the user.
        """
        data = {"enabled": False, "authorities": self.authorities}
        data = self.c2.request_put(f"/api/v1/users/{self.username}", data)
        self._load_conf(data)

    def enable(self):
        """
        Enable the user.
        """
        data = {"enabled": True, "authorities": self.authorities}
        data = self.c2.request_put(f"/api/v1/users/{self.username}", data)
        self._load_conf(data)

    def set_authorities(self, authorities):
        """
        Change the authorities assigned to the user.
        """
        data = {"authorities": authorities, "enabled": self.enabled}
        data = self.c2.request_put(f"/api/v1/users/{self.username}", data)
        self._load_conf(data)

    def set_password(self, new_password):
        """
        Set a new password for the user.
        """
        data = {"newPassword": new_password}
        data = self.c2.request_put(f"/api/v1/users/{self.username}/password", data)
        
    

