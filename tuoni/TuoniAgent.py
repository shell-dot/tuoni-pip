from tuoni.TuoniExceptions import *
from tuoni.TuoniCommand import *
from tuoni.TuoniAlias import *
from tuoni.TuoniDefaultCommands import *

class TuoniAgent:
    """
    A class that encapsulates the data and functionality of a connected agent.

    Attributes:
        guid (GUID): A unique identifier (GUID) assigned to the agent.
        first_registration_time (str): The time, in string format, when the agent first connected.
        last_callback_time (str): The time, in string format, of the agent's most recent connection.
        metadata (dict): A dictionary containing metadata about the agent.
        active (bool): A boolean flag indicating whether the agent is currently active.
        recentListeners (list): A list of listeners that the agent uses to maintain its connection.
        availableCommands (dict): A dictionary of commands that the agent is capable of executing.
    """

    def __init__(self, conf, c2):
        """
        Constructor.

        Attributes:
            conf (dict): Data from server.
            c2 (TuoniC2): Related server object.
        
        """
        self.c2 = c2
        self._load_conf(conf)

    def _load_conf(self, conf):
        self.guid = conf["guid"]
        self.first_registration_time = conf["firstRegistrationTime"]
        self.last_callback_time = conf["lastCallbackTime"]
        self.metadata = conf["metadata"]
        self.active = conf["active"]
        self.recentListeners = conf["recentListeners"]
        self._fill_available_commands(conf["availableCommandTemplates"])

    def send_command(self, command_type, command_conf=None, execution_conf = None, files = None):
        """
        Send command to agent.

        Args:
            command_type (str | TuoniAlias | TuoniDefaultCommand): What command to send.
            command_conf (dict): Command configuration.
            execution_conf (dict): Execution configuration.
            files (dict): Files to send with command.

        Returns:
            TuoniCommand: An object representing the created command.

        Examples:
            >>> command1 = agent.send_command(TuoniCommandLs(".\subdir", 2))
            >>> command2 = agent.send_command(TuoniCommandProcinfo(), execution_conf ={"execType": "NEW"})
            >>> command3 = agent.send_command(TuoniCommandProcinfo(), execution_conf = {"execType": "EXISTING", "pid": 1234})
            >>> command4 = agent.send_command("ls", {"dir": ".\subdir", "depth": 2})
            >>> command5 = agent.send_command(alias_object, {"conf_value_name": "conf_value"})
        """
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        if isinstance(command_type, TuoniDefaultCommand):
            command_conf = command_type.command_conf
            execution_conf = command_type.execution_conf
            files = command_type.files
            command_type = command_type.command_type
        if isinstance(command_type, TuoniAlias):
            command_type = command_type.alias_id
        if command_conf is None:
            command_conf = {}
        data = {
            "template": command_type,
            "configuration": command_conf
        }
        if execution_conf is not None:
            data["execConf"] = execution_conf
        data = self.c2.request_post("/api/v1/agents/%s/commands" % self.guid, data, files)
        return TuoniCommand(data, self.c2)

    def get_commands(self):
        """
        Retrieves a list of all commands associated with the agent.

        Returns:
            list[TuoniCommand]: List of commands sent to the agent.
        """
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
        """
        Deletes agent.
        """
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_delete("/api/v1/agents/%s" % self.guid)
        self.listener_id = None
        
    def _fill_available_commands(self, command_list):
        self.availableCommands = {}
        for cmd in self.c2.request_get("/api/v1/command-templates"):
            if cmd["id"] in command_list:
                self.availableCommands[cmd["name"]] = cmd["id"]
            

