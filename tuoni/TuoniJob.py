import time
from tuoni.TuoniEvent import *
from tuoni.TuoniExceptions import ExceptionTuoniDeleted


class TuoniJob:
    """
    A class that provides data and functionality for a job.

    Attributes:
        job_id (int): The unique identifier of the job.
        name (str): Name of the job.
        status (str): Status of the job.
        source (dict): Source for the job.
        supportedActions (list): What actions are allowed on the job.
        openResources (list): What resources are open related to this job.
        messages (list): Messages related to job.
        createEvent (TuoniEvent): Event about job creation.
        lastUpdateEvent (TuoniEvent): Event about last job update.
    """
    
    def __init__(self, conf, c2):
        """
        Constructor for the job class.

        Args:
            conf (dict): Data from the server.
            c2 (TuoniC2): The related server object that manages communication.
        """
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.job_id = conf["id"]
        self.name = conf["name"]
        self.status = conf["status"]
        self.source = conf["source"]
        self.supportedActions = conf["supportedActions"]
        self.openResources = conf["openResources"]
        self.messages = conf["messages"]
        self.createEvent = TuoniEvent(conf["createEvent"]) if (conf["createEvent"] is not None) else None
        self.lastUpdateEvent = TuoniEvent(conf["lastUpdateEvent"]) if (conf["lastUpdateEvent"] is not None) else None

    def reload(self):
        """
        Reload the command data from the C2 server.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/job/{self.job_id}")
        self._load_conf(data)

    def restart(self):
        """
        Run restart operation on the job.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/job/{self.job_id}/restart")

    def pause(self):
        """
        Run pause operation on the job.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/job/{self.job_id}/pause")

    def resume(self):
        """
        Run resume operation on the job.
        """
        if self.command_id is None:
            raise ExceptionTuoniDeleted("")
        data = self.c2.request_get(f"/api/v1/job/{self.job_id}/resume")