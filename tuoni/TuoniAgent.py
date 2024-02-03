from tuoni.TuoniExceptions import *
from tuoni.TuoniCommand import *
from tuoni.TuoniDefaultCommands import *

class TuoniAgent:
    def __init__(self, conf, c2):
        self._load_conf(conf)
        self.c2 = c2

    def _load_conf(self, conf):
        self.guid = conf["guid"]
        self.first_registration_time = conf["firstRegistrationTime"]
        self.last_callback_time = conf["lastCallbackTime"]
        self.metadata = conf["metadata"]
        self.active = conf["active"]
        self.recentListeners = conf["recentListeners"]
        self.availableCommands = conf["availableCommands"]

    def send_command(self, command_type, command_conf=None, execution_conf = None):
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        if isinstance(command_type, TuoniDefaultCommand):
            command_conf = command_type.command_conf
            execution_conf = command_type.execution_conf
            command_type = command_type.command_type
        if command_conf is None:
            command_conf = {}
        data = {
            "template": command_type,
            "configuration": command_conf
        }
        if execution_conf is not None:
            data["execConf"] = execution_conf
        data = self.c2.request_post("/api/v1/agents/%s/commands" % self.guid, data)
        return TuoniCommand(data, self.c2)

    def get_commands(self):
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        commands_data = self.c2.request_get("/api/v1/agents/%s/commands" % self.guid)
        commands = []
        for command_nr in commands_data:
            command_data = commands_data[command_nr]
            command_obj = TuoniCommand(command_data, self.c2)
            commands.append(command_obj)
        return commands

    def delete(self):
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_delete("/api/v1/agents/%s" % self.guid)
        self.listener_id = None

