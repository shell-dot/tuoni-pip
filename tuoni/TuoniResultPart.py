import json
from tuoni.TuoniExceptions import *


class TuoniResultPart:
    """
    A class that provides data and functionality for a part of a command result.

    Attributes:
        type (str): The type of the result part.
        name (str): The name of the result part.
        value (str): The value associated with the result part.
        filename (str): The filename of any file included in the result part.
        uri (str): The URI for accessing the file in the result part.
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
        self.type = conf["type"]
        if self.type == "text":
            self.name = conf["name"]
            self.value = conf["value"]
        if self.type == "file":
            self.filename = conf["filename"]
            self.href = conf["href"]
            if "//" in self.href:
                self.uri = self.href[self.href.find("//")+2:]
                self.uri = self.uri[self.uri.find("/"):]
            else:
                self.uri = self.href

    def get_as_text(self):
        """
        Retrieve the value of the result part as text.

        Returns:
            str: The value of the result part as a string.
        """
        if self.type == "text":
            return self.value
        if self.type == "file":
            return self.c2.request_get(self.uri, result_as_json=False)
        return None

    def get_as_file(self, filename):
        """
        Retrieve the value of the result part as a file and save it to the specified location.

        Args:
            filename (str): The path where the file should be saved.
        """
        if self.type == "file":
            self.c2.request_get_file(self.uri, filename)
        return None

    def get_as_bytes(self):
        """
        Retrieve the value of the result part as bytes.
        """        
        if self.type == "file":
            return self.c2.request_get(self.uri, result_as_json=False, result_as_bytes=True)
        if self.type == "text":
            return self.value.encode('utf-8')
        return None

    def get_as_json(self):
        """
        Retrieve the value of the result part as JSON and convert it to a dictionary.

        Returns:
            dict: The result part as a dictionary.
        """
        if self.type == "text":
            return json.loads(self.value)
        if self.type == "file":
            return json.loads(self.c2.request_get(self.uri, result_as_json=False))
        return None
