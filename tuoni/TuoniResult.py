from tuoni.TuoniResultPart import *


class TuoniResult:
    """
    A class that provides data for a command result.

    Attributes:
        status (str): The status of the result.
        error_message (str): The error message, if any, for the result.
        received (str): The time, in string format, indicating when the result was received.
        parts (list[TuoniResultPart]): A list of parts that make up the result.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the result class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self.c2 = c2
        self._load_conf(conf)

    def _load_conf(self, conf):
        self.status = conf["status"]
        self.error_message = conf["errorMessage"]
        self.received = conf["received"]
        self.parts = []
        for part_conf in conf["childResults"]:
            part_obj = TuoniResultPart(part_conf, self.c2)
            self.parts.append(part_obj)

    def is_text(self):
        """
        Check if the result contains typical text output (result part where name is "stdout", "text", or "message").

        Returns:
            bool: True if the result is a text output, False otherwise.
        """
        for part in self.parts:
            if part.type == "text" and (part.name.lower() == "stdout" or part.name.lower() == "text" or part.name.lower() == "message"):
                return True
        return False
    
    def is_json(self):
        """
        Check if the result contains JSON output (result part where name "json").

        Returns:
            bool: True if the result is a JSON output, False otherwise.
        """
        for part in self.parts:
            if part.type == "text" and part.name.lower() == "json":
                return True
        return False
    
    def is_file(self):
        """
        Check if the result contains file output (result part where type is "file").

        Returns:
            bool: True if the result is a file output, False otherwise.
        """
        for part in self.parts:
            if part.type == "file":
                return True
        return False
    
    def get_text(self):
        """
        Retrieve the text output from the result parts.

        Returns:
            str: The text output if available, otherwise None.
        """
        for part in self.parts:
            if part.type == "text" and (part.name.lower() == "stdout" or part.name.lower() == "text" or part.name.lower() == "message"):
                return part.get_as_text()
        return None
    
    def get_json(self):
        """
        Retrieve the JSON output from the result parts.

        Returns:
            dict: The JSON output if available, otherwise None.
        """
        for part in self.parts:
            if part.type == "text" and part.name.lower() == "json":
                return part.get_as_json()
        return None
    
    def get_files(self, download = False):
        """
        Retrieve the file outputs from the result parts.

        Returns:
            dict: A dictionary where keys are filenames and values are the file contents if download is True, otherwise a ResultPart object.
        """
        files = {}
        for part in self.parts:
            if part.type == "file":
                if download:
                    files[part.filename] = part.get_as_bytes()
                else:
                    files[part.filename] = part
        return files

