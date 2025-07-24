from tuoni.TuoniExceptions import *
from tuoni.TuoniCommand import *
from tuoni.TuoniAlias import *
from tuoni.TuoniDefaultCommands import *
import warnings

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
            >>> command1 = agent.send_command(TuoniCommandLs(".\\subdir", 2))
            >>> command2 = agent.send_command(
            >>>     TuoniCommandProcinfo(), 
            >>>     execution_conf ={"execType": "NEW"}
            >>> )
            >>> command3 = agent.send_command(
            >>>     TuoniCommandProcinfo(), 
            >>>     execution_conf = {
            >>>         "execType": "EXISTING", 
            >>>         "pid": 1234
            >>>     }
            >>> )
            >>> command4 = agent.send_command("ls", {"dir": ".\\subdir", "depth": 2})
            >>> command5 = agent.send_command(
            >>>     alias_object, 
            >>>     {"conf_value_name": "conf_value"}
            >>> )
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
        data = self.c2.request_post(f"/api/v1/agents/{self.guid}/commands", data, files)
        return TuoniCommand(data, self.c2)

    def get_commands(self):
        """
        Retrieves a list of all commands associated with the agent.

        Returns:
            list[TuoniCommand]: List of commands sent to the agent.
        """
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        commands_data = self.c2.request_get(f"/api/v1/agents/{self.guid}/commands")
        commands = []
        for command_nr in commands_data:
            command_data = commands_data[command_nr]
            command_obj = TuoniCommand(command_data, self.c2)
            commands.append(command_obj)
        return commands

    def delete(self):
        """
        Deletes agent (actually makes it inactive but close enough).
        """
        if self.guid is None:
            raise ExceptionTuoniDeleted("")
        self.c2.request_put(f"/api/v1/agents/{self.guid}/inactive")
        self.listener_id = None
        
    def _fill_available_commands(self, command_list):
        self.availableCommands = {}
        for cmd in self.c2.request_get("/api/v1/command-templates"):
            if cmd["id"] in command_list:
                self.availableCommands[cmd["name"]] = cmd["id"]

    def matches(self, criteria):
        """
        Check if the agent matches the given criteria.

        Args:
            criteria (dict): Dictionary containing matching criteria. Keys can 
            use dot notation like 'metadata.os' to access nested attributes.

        Returns:
            bool: True if all criteria match, False otherwise.
        """
        
        for key, expected_value in criteria.items():
            # Handle dot notation for nested attributes
            current_obj = self
            
            # Split the key by dots and traverse the object
            key_parts = key.split('.')
            
            try:
                for part in key_parts:
                    if hasattr(current_obj, part):
                        current_obj = getattr(current_obj, part)
                    elif isinstance(current_obj, dict) and part in current_obj:
                        current_obj = current_obj[part]
                    else:
                        # Debug: print available attributes
                        if hasattr(current_obj, '__dict__'):
                            available_attrs = list(current_obj.__dict__.keys())
                        elif isinstance(current_obj, dict):
                            available_attrs = list(current_obj.keys())
                        else:
                            available_attrs = []
                        return False
                
                # Compare the final value (case-insensitive for strings)
                if isinstance(current_obj, str) and isinstance(expected_value, str):
                    if current_obj.upper() != expected_value.upper():
                        return False
                else:
                    if current_obj != expected_value:
                        print(f"{Fore.YELLOW}Debug: Value mismatch for '{key}': got '{current_obj}', expected '{expected_value}'{Style.RESET_ALL}")
                        return False
                        
            except (AttributeError, TypeError) as e:
                print(f"{Fore.YELLOW}Debug: Exception accessing '{key}': {e}{Style.RESET_ALL}")
                return False
        
        # All criteria matched
        return True
    
    def setCustomProperties(self, name, value):
        """
        .. deprecated
            Use :func:`set_custom_property` instead.

        Adds or updates a property in the agents customProperties metadata.
        

        Parameters:
            name (str): The name (key) of the property to add or update.
            value (Any): The value to assign to the given name.

        Behavior:
            - If the property with the given name exists, its value will be updated.
            - If it does not exist, a new name/value pair will be added.
            - If value is None the name/value pair will be deleted.

        Example:
            myAgent.setCustomProperties("notes", "Domain Controller")
        """
        warnings.warn(
            f"Function setCustomProperties is deprecated; it will be removed in a future release. Please use `set_custom_property` instead.",
            category=DeprecationWarning
        )
        self.set_custom_property(name, value)

    def set_custom_property(self, name, value):
        """
        Adds or updates a property in the agents customProperties metadata.

        Parameters:
            name (str): The name (key) of the property to add or update.
            value (Any): The value to assign to the given name.

        Behavior:
            - If the property with the given name exists, its value will be updated.
            - If it does not exist, a new name/value pair will be added.
            - If value is None the name/value pair will be deleted.

        Example:
            myAgent.set_custom_property("notes", "Domain Controller")
        """
        self.metadata['customProperties'][name] = value
        self.c2.request_put(f"/api/v1/agents/{self.guid}/metadata", self.metadata)
