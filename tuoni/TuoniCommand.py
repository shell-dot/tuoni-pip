import time
from tuoni.TuoniExceptions import *
from tuoni.TuoniResult import *


_TERMINAL_TOP_STATUSES = {"CANCELED", "FAILED", "COMPLETE"}
_FAILED_TOP_STATUSES = {"CANCELED", "FAILED"}


class TuoniCommand:
    """
    A class that provides data and functionality for a sent command.

    Attributes:
        command_id (int): The unique identifier of the command.
        commandTemplateId (str): The unique identifier of the command template used to create the command.
        commandTemplateName (str): The name of the command template used to create the command.
        configuration (dict): The configuration settings for the command.
        execConf (dict): The execution configuration for the command.
        status (str): Top-level lifecycle status from the server: one of
            ``CREATED``, ``SENT``, ``ONGOING``, ``CANCELED``, ``FAILED``,
            ``COMPLETE``. May be ``None`` on older servers.
        created (str): The time, as a string, indicating when the command was created.
        sent (str): The time, as a string, indicating when the command was sent.
        result (TuoniResult): The result data returned from the command execution.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the command class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.command_id = conf["id"]
        self.commandTemplateId = conf["commandTemplateId"]
        self.commandTemplateName = conf["commandTemplateName"]
        self.configuration = conf["configuration"]
        self.execConf = conf["execConf"]
        self.status = conf.get("status", None)
        self.created = conf["created"]
        self.sent = conf["sent"]
        self.result = conf["result"]

    def reload(self):
        """
        Reload the command data from the C2 server.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/commands/{self.command_id}")
        self._load_conf(data)

    def result_status_done(self, reload = True):
        """
        Check if the command has completed.

        Args:
            reload (bool): If True, reload the command data from the server to verify the current status.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        if reload:
            self.reload()
        if self.result is None:
            return False
        if self.result["status"].lower() == "ongoing":
            return False
        return True

    def result_status_ongoing(self, reload = True):
        """
        Check if the command is still ongoing.

        Args:
            reload (bool): If True, reload the command data from the server to verify the current status.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        if reload:
            self.reload()
        if self.result is None:
            return False
        if self.result["status"].lower() == "ongoing":
            return True
        return False

    def get_result(self, reload = True):
        """
        Retrieve the result object of the command.

        Args:
            reload (bool): If True, reload the command result data from the server.

        Returns:
            TuoniResult: The result object containing the data from the command execution.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        if reload:
            self.reload()
        if self.result is None:
            return None
        return TuoniResult(self.result, self.c2)

    def wait_result(self, interval = 1, maxWait = 0):
        """
        Wait for the command result object to be available (command done or in case of ongoing result, the initial results)

        Args:
            interval (int): The interval, in seconds, to reload the data from the server.
            maxWait (int): The maximum time to wait, in seconds, before giving up. A value of 0 means wait indefinitely.

        Returns:
            TuoniResult: The result object containing the data from the command execution, if available within the specified time.
        """
        self.reload()
        while self.result is None:
            time.sleep(interval)
            self.reload()
            if maxWait > 0:
                maxWait -= interval
                if maxWait <= 0:
                    return None
        return TuoniResult(self.result, self.c2)

    def wait_done(self, interval = 1, maxWait = 0):
        """
        Wait for the command to be done (success, failed, or canceled).

        Args:
            interval (int): The interval, in seconds, to reload the data from the server.
            maxWait (int): The maximum time to wait, in seconds, before giving up. A value of 0 means wait indefinitely.

        Returns:
            TuoniResult: The result object containing the data from the command execution, if available within the specified time. For commands that finish without a result (e.g. canceled before send), returns ``None`` once the terminal status is reached.
        """
        self.reload()
        while not self.is_done():
            time.sleep(interval)
            self.reload()
            if maxWait > 0:
                maxWait -= interval
                if maxWait <= 0:
                    return None
        return TuoniResult(self.result, self.c2) if self.result is not None else None
    
    def wait_sent(self, interval = 1, maxWait = 0):
        """
        Wait for the command to be sent

        Args:
            interval (int): The interval, in seconds, to reload the data from the server.
            maxWait (int): The maximum time to wait, in seconds, before giving up. A value of 0 means wait indefinitely.

        Returns:
            bool: Was command sent
        """
        self.reload()
        while self.sent is None:
            time.sleep(interval)
            self.reload()
            if maxWait > 0:
                maxWait -= interval
                if maxWait <= 0:
                    return False
        return True

    def is_done(self, reload_from_server = False):
        """
        Checks has the command done/finished

        Args:
            reload_from_server (bool): Should command data be reloaded from server.

        Returns:
            bool: Is command done
        """
        if reload_from_server:
            self.reload()
        if self.status in _TERMINAL_TOP_STATUSES:
            return True
        return (self.result is not None and self.result["status"].lower() != "ongoing")

    def is_success(self, reload_from_server = False):
        """
        Checks was the command successful

        Args:
            reload_from_server (bool): Should command data be reloaded from server.

        Returns:
            bool: Was command successful
        """
        if reload_from_server:
            self.reload()
        if self.status == "COMPLETE":
            return True
        if self.status is not None:
            return False
        return (self.result is not None and self.result["status"].lower() == "success")

    def is_failed(self, reload_from_server = False):
        """
        Checks did the command fail or get canceled

        Args:
            reload_from_server (bool): Should command data be reloaded from server.

        Returns:
            bool: Did command fail
        """
        if reload_from_server:
            self.reload()
        if self.status in _FAILED_TOP_STATUSES:
            return True
        if self.status is not None:
            return False
        return (self.result is not None and self.result["status"].lower() == "failed")

    def is_ongoing(self, reload_from_server = False):
        """
        Checks is the command running as ongoing command

        Args:
            reload_from_server (bool): Should command data be reloaded from server.

        Returns:
            bool: Is command ongoing
        """
        if reload_from_server:
            self.reload()
        if self.status == "ONGOING":
            return True
        if self.status is not None:
            return False
        return (self.result is not None and self.result["status"].lower() == "ongoing")

    def is_sent(self, reload_from_server = False):
        """
        Checks was the command sent to the agent

        Args:
            reload_from_server (bool): Should command data be reloaded from server.

        Returns:
            bool: Is command sent to agent
        """
        if reload_from_server:
            self.reload()
        return (self.sent is not None)
    
    def get_template(self):
        """
        Retrieve the command template used to create this command.

        Returns:
            TuoniCommandTemplate: The command template object, or None if the template could not be found.
        """
        return self.c2.load_command_template(self.commandTemplateId)

    def stop(self):
        """
        Stops the command execution on the agent or if it is not yet sent then cancel it.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_put(f"/api/v1/commands/{self.command_id}/stop")

    def send_update(self, config: dict, files: dict = None, persistence_type: str = "TRANSIENT"):
        """
        Send an update to a running command (e.g. additional data for an ongoing operation).

        Args:
            config (dict): The update configuration to send (wrapped server-side as
                ``updateConfiguration``).
            files (dict): Optional files to include with the update. Same format as the
                ``files`` parameter of :func:`TuoniAgent.send_command`.
            persistence_type (str): ``"TRANSIENT"`` (default) or ``"PERSISTENT"``.

        Examples:
            >>> command.send_update({"input": "yes"})
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        body = {
            "updateConfiguration": config,
            "configurationFiles": [],
            "persistenceType": persistence_type,
        }
        self.c2.request_post(f"/api/v1/commands/{self.command_id}/update", body, files)
