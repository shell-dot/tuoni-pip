import time
from tuoni.TuoniExceptions import *


class TuoniFile:
    """
    A class that provides data and functionality for a stored files.

    Attributes:
        fileId (GUID): The unique identifier (GUID) for the file.
        originalFileName (str): The original filename.
        size (int): Size of the file.
        filePaths (list): List of filepaths
        downloadHref (str): A download path.
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
        self.fileId = conf["fileId"]
        self.originalFileName = conf["originalFileName"]
        self.size = conf["size"]
        self.filePaths = conf["filePaths"]
        self.downloadHref = conf["downloadHref"]

    def reload(self):
        """
        Reload the file data from the C2 server.
        """
        if self.fileId is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/file/{self.fileId}")
        self._load_conf(data)

    def delete(self):
        """
        Delete the file.
        """
        if self.fileId is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_delete(f"/api/v1/file/{self.fileId}")
        self._load_conf(data)

    def download(self, filename):
        return self.c2.request_get_file(self.downloadHref, filename)

