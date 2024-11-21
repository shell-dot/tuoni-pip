import time
import requests
import json
import threading
import shutil
import base64
import inspect
from tuoni.TuoniExceptions import *
from tuoni.TuoniListenerPlugin import *
from tuoni.TuoniListener import *
from tuoni.TuoniAgent import *
from tuoni.TuoniPayloadPlugin import *
from tuoni.TuoniAlias import *
from tuoni.TuoniUser import *


class TuoniC2:
    """
    Tuoni main class for connecting and controlling Tuoni server
    """
    def __init__(self):
        self._token: str = None
        self._url: str = None
        self._monitoring_threads: list = []

    def login(self, url: str, username: str, password: str):
        """
        Login to tuoni server

        Args:
            url (str): What URL to connect
            username (str): Username to use
            password (str): Password to use
        """
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('utf-8')
        }

        response = requests.post(f"{url}/api/v1/auth/login", headers=headers, verify=False)
        if response.status_code != 200:
            raise ExceptionTuoniAuthentication(response.text)
        self._token = response.text
        self._url = url

    def _request_check(self):
        if self._token is None:
            raise ExceptionTuoniAuthentication("You have not done the login")

    @staticmethod
    def _raise_request_exception(result_msg: str):
        try:
            data = json.loads(result_msg)
            msg = data.get("message", result_msg)
        except json.JSONDecodeError:
            msg = result_msg
        raise ExceptionTuoniRequestFailed(msg)

    def _make_request(self, method: str, uri: str, **kwargs):
        self._request_check()
        headers = {"Authorization": f"Bearer {self._token}"}
        response = requests.request(method, f"{self._url}{uri}", headers=headers, verify=False, **kwargs)
        if response.status_code != 200:
            self._raise_request_exception(response.text)
        return response

    def request_get(self, uri: str, result_as_json: bool = True):
        """
        GET request to tuoni server

        Args:
            uri (str): URI to use
            result_as_json (bool): Is result from server handled as json and converted to dict

        Returns:
            str | dict: Result of the request
        """
        response = self._make_request("GET", uri)
        if response.text == "":
            return None
        return json.loads(response.text) if result_as_json else response.text

    def request_get_file(self, uri: str, file_name: str):
        """
        GET request to tuoni server, result written to filesystem

        Args:
            uri (str): URI to use
            file_name (str): Filename to create
        """
        response = self._make_request("GET", uri, stream=True)
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

    def request_post(self, uri: str, json_data: dict = None, files: dict = None):
        """
        POST request to tuoni server

        Args:
            uri (str): URI to use
            json_data (dict): JSON data to send in POST content
            files (dict): Files to send in POST

        Returns:
            dict: Result of the request
        """
        if files is None:
            response = self._make_request("POST", uri, json=json_data)
        else:
            all_data = {}
            if json_data is not None:
                all_data["requestBody"] = (None, json.dumps(json_data), 'application/json')
            for var_name, file_info in files.items():
                all_data[var_name] = (file_info[0], file_info[1], 'application/octet-stream')
            response = self._make_request("POST", uri, files=all_data)
        return json.loads(response.text) if response.text else None

    def request_put(self, uri: str, json_data: dict = None):
        """
        PUT request to tuoni server

        Args:
            uri (str): URI to use
            json_data (dict): JSON data to send in PUT content

        Returns:
            dict: Result of the request
        """
        response = self._make_request("PUT", uri, json=json_data)
        return json.loads(response.text) if response.text else None

    def request_delete(self, uri: str, json_data: dict = None):
        """
        DELETE request to tuoni server

        Args:
            uri (str): URI to use
            json_data (dict): JSON data to send in DELETE content

        Returns:
            dict: Result of the request
        """
        response = self._make_request("DELETE", uri, json=json_data)
        return json.loads(response.text) if response.text else None

    def load_listener_plugins(self):
        """
        Get list of listener plugins

        Returns:
            list[TuoniListenerPlugin]: List of plugins
        """
        plugins_data = self.request_get("/api/v1/plugins/listeners")
        return {plugin_data["identifier"]["id"]: TuoniListenerPlugin(plugin_data, self) for plugin_data in plugins_data.values()}

    def load_listeners(self):
        """
        Get list of listeners

        Returns:
            list[TuoniListener]: List of listeners
        """
        listeners_data = self.request_get("/api/v1/listeners")
        return [TuoniListener(listener_data, self) for listener_data in listeners_data.values()]

    def load_payload_plugins(self):
        """
        Get list of payload plugins

        Returns:
            list[TuoniPayloadPlugin]: List of plugins
        """
        plugins_data = self.request_get("/api/v1/plugins/payloads")
        return {plugin_data["identifier"]["id"]: TuoniPayloadPlugin(plugin_data, self) for plugin_data in plugins_data.values()}

    def create_payload(self, payload_template: str, payload_listener: int, payload_conf: dict, encrypted: bool = True, payload_name: str = None):
        """
        Create new payload

        Args:
            payload_template (str): URI to use
            payload_listener (int): Listener id
            payload_conf (dict): Payload configuration
            encrypted (bool): Should traffic with this payload be encrypted
            payload_name (dict): Payload name

        Returns:
            id: Payload id
        """
        json_data = {
            "payloadTemplateId": payload_template,
            "configuration": payload_conf,
            "listenerId": payload_listener,
            "encrypted": encrypted,
            "name": payload_name
        }
        payload_data = self.request_post("/api/v1/payloads", json_data)
        return payload_data["id"]

    def download_payload(self, payload_id: int, file_name: str):
        """
        Download payload

        Args:
            payload_id (int): Payload ID
            file_name (str): What file to write into
        """
        self.request_get_file(f"/api/v1/payloads/{payload_id}/download", file_name)

    def load_agents(self):
        """
        Get agents list

        Returns:
            list[TuoniAgent]: List of agents
        """
        agents_data = self.request_get("/api/v1/agents/active")
        return [TuoniAgent(agent_data, self) for agent_data in agents_data]

    def wait_new_agent(self, interval: int = 1, max_wait: int = 0):
        """
        Wait for new agent to connect

        Args:
            interval (int): How often to check for new connections in second
            max_wait (int): Maximum time to wait - 0 means infinite

        Returns:
            TuoniAgent: Agent that connected
        """
        original_agents = {agent_data["guid"] for agent_data in self.request_get("/api/v1/agents/active")}
        while True:
            time.sleep(interval)
            agents_data = self.request_get("/api/v1/agents/active")
            for agent_data in agents_data:
                if agent_data["guid"] not in original_agents:
                    return TuoniAgent(agent_data, self)
            if max_wait > 0:
                max_wait -= interval
                if max_wait <= 0:
                    return None

    def on_new_agent(self, function, interval: int = 1):
        """
        Callback when new agent connects

        Args:
            function (func): What function to call
            interval (int): How often to check
        """
        monitor_thread = threading.Thread(target=self._monitor_for_new_agents, args=(function, interval), daemon=True)
        monitor_thread.start()
        self._monitoring_threads.append(monitor_thread)

    def _monitor_for_new_agents(self, function, interval: int = 1):
        original_agents = {agent_data["guid"] for agent_data in self.request_get("/api/v1/agents")}
        while True:
            time.sleep(interval)
            agents_data = self.request_get("/api/v1/agents")
            for agent_data in agents_data:
                if agent_data["guid"] not in original_agents:
                    original_agents.add(agent_data["guid"])
                    agent = TuoniAgent(agent_data, self)
                    threading.Thread(target=function, args=(agent,)).start()

    def load_aliases(self):
        """
        Get aliases list

        Returns:
            list[TuoniAlias]: List of aliases
        """
        all_aliases = self.request_get("/api/v1/command-alias")
        return [TuoniAlias(alias_data, self) for alias_data in all_aliases]
        
    def add_alias(self, name, description, command_type, command_conf=None, files = None):
        """
        Add alias

        Args:
            name (str): Name of the alias being created
            description (str): Alias description
            command_type (str | TuoniDefaultCommand): Base command to use 
            command_conf (dict): Set configuration for alias
            files (dict): Set file parameters for alias

        Returns:
            TuoniAlias: Alias that was created
        """
        if isinstance(command_type, TuoniDefaultCommand):
            command_conf = command_type.command_conf
            files = command_type.files
            command_type = command_type.command_type
        if inspect.isclass(command_type) and issubclass(command_type, TuoniDefaultCommand):
            command_type = command_type._class_base_type
    
        json_data = {
            "name": name,
            "description": description,
            "baseTemplate": command_type,
            "fixedConfiguration": command_conf
        }
        alias_data = self.request_post("/api/v1/command-alias", json_data, files = files)
        return TuoniAlias(alias_data, self)

    def load_hosted(self):
        """
        Get hosted file list

        Returns:
            dict: Hosted files
        """
        return self.request_get("/api/v1/files")
        
    def add_hosted(self, filename, file_content):
        """
        Add hosted file

        Args:
            filename (str): Filename 
            file_content (bytes): File content

        Returns:
            str: API URI for the uploaded file
        """
        return self.request_post("/api/v1/files", files = {"file": [filename, file_content]})
        
    def delete_hosted(self, hosted):
        """
        Delete hosted file

        Returns:
            dict: Hosted files
        """
        full_uri = hosted
        if "/api/v1/files/" not in hosted:
            hosted = "/api/v1/files/" + hosted
        self.request_delete(hosted)

    def load_users(self):
        """
        Get users list

        Returns:
            list[TuoniUser]: List of users
        """
        all_users = self.request_get("/api/v1/users")
        return [TuoniUser(user_data, self) for user_data in all_users]
        
    def add_user(self, username, password, authorities):
        """
        Add user

        Args:
            username (str): Username to create 
            password (str): Initial password 
            authorities (list[str]): List of authorities

        Returns:
            TuoniUser: User that was created
        """
        json_data = {
            "username": username,
            "password": password,
            "authorities": authorities
        }
        user_data = self.request_post("/api/v1/users", json_data, None)
        return TuoniUser(user_data, self)

    def let_it_run(self):
        """
        If there are any callback functions initialized, then wait forever or until monitoring threads end
        """
        for monitoring_thread in self._monitoring_threads:
            monitoring_thread.join()
