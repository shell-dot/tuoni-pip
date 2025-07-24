import os
import time
import requests
import json
import threading
import shutil
import base64
import inspect
from pathlib import Path
from tuoni.TuoniExceptions import *
from tuoni.TuoniListenerPlugin import *
from tuoni.TuoniListener import *
from tuoni.TuoniAgent import *
from tuoni.TuoniPayloadPlugin import *
from tuoni.TuoniAlias import *
from tuoni.TuoniUser import *
from tuoni.TuoniFile import *
from tuoni.TuoniDataHost import *
from tuoni.TuoniDataService import *
from tuoni.TuoniDataCredential import *
from tuoni.TuoniJob import *


class TuoniC2:
    """
    The primary class for establishing connections to and managing interactions with the Tuoni server. It provides functionality for controlling server operations and facilitating communication.

    Args:
        verify (str | bool) [default = False]: A flag to enable or disable SSL verification. If a string is provided, it is treated as the path to a CA bundle file.
    """
    def __init__(self, verify: str | bool = False):
        self._token: str = None
        self._url: str = None
        self._monitoring_threads: list = []
        self._set_verify(verify)

    def login(self, url: str, username: str, password: str):
        """
        Login to the Tuoni server.

        Args:
            url (str): The URL of the Tuoni server to connect to.
            username (str): The username for authentication.
            password (str): The password for authentication.

        Examples:
            >>> tuoni_server = TuoniC2()
            # Disabling SSL verification
            >>> tuoni_server = TuoniC2(verify=False)
            # Set path for CA bunle
            >>> tuoni_server = TuoniC2(verify="/path/to/ca_bundle.pem")
            # Login to the server
            >>> tuoni_server.login("https://localhost:8443", "my_user", "S3cr37")


        """
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('utf-8')
        }

        response = requests.post(f"{url}/api/v1/auth/login", headers=headers, verify=self._verify)
        if response.status_code != 200:
            raise ExceptionTuoniAuthentication(response.text)
        self._token = response.text
        self._url = url

    def _request_check(self):
        if self._token is None:
            raise ExceptionTuoniAuthentication("You have not done the login")

    def _set_verify(self, verify: str | bool):
        self._verify = False
        if isinstance(verify, bool) and verify:
            self._verify = True
        elif isinstance(verify, bool) and not verify:
            self._verify = False
        elif isinstance(verify, str):
            if Path(verify).is_file():
                self._verify = verify
            else:
                raise Exception("The path to the CA bundle is not valid")


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
        response = requests.request(method, f"{self._url}{uri}", headers=headers, verify=self._verify, **kwargs)
        if response.status_code != 200:
            self._raise_request_exception(response.text)
        return response

    def request_get(self, uri: str, result_as_json: bool = True, result_as_bytes: bool = False):
        """
        Send a GET request to the Tuoni server.

        Args:
            uri (str): The URI endpoint to send the request to.
            result_as_json (bool): If True, the server's response is treated as JSON and converted to a dictionary.
            result_as_bytes (bool): If True, the server's response is returned as a bytes.

        Returns:
            str | dict | bytes: The server's response, either as a raw string or a dictionary if `result_as_json` is True or as bytes if `result_as_bytes` is True.
        """
        response = self._make_request("GET", uri)
        if len(response.content) == 0:
            return None
        if result_as_json:
            return json.loads(response.text)
        if result_as_bytes:
            return response.content
        return response.text

    def request_get_file(self, uri: str, file_name: str):
        """
        Send a GET request to the Tuoni server and save the result to the filesystem.

        Args:
            uri (str): The URI endpoint to send the request to.
            file_name (str): The name of the file where the response will be saved.
        """
        response = self._make_request("GET", uri, stream=True)
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

    def request_post(self, uri: str, json_data: dict = None, files: dict = None):
        """
        Send a POST request to the Tuoni server.

        Args:
            uri (str): The URI endpoint to send the request to.
            json_data (dict): A dictionary containing the JSON payload to include in the POST request.
            files (dict): A dictionary of files to upload with the POST request.

        Returns:
            dict: The server's response as a dictionary.

        Examples:
            >>> tuoni = TuoniC2()
            >>> tuoni_server.request_post(
            >>>     "/api/v1/command-alias",
            >>>     {
            >>>         "name": "bofX",
            >>>         "description": "Example",
            >>>         "baseTemplate": "bof",
            >>>         "fixedConfiguration": {"method": "go"}
            >>>     },
            >>>     {"bofFile" : ["some_bof.o", open("some_bof", "rb").read()]}
            >>> )
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

    def request_patch(self, uri: str, json_data: dict = None, files: dict = None):
        """
        Send a PATCH request to the Tuoni server.

        Args:
            uri (str): The URI endpoint to send the request to.
            json_data (dict): A dictionary containing the JSON payload to include in the POST request.
            files (dict): A dictionary of files to upload with the POST request.

        Returns:
            dict: The server's response as a dictionary.
        """
        if files is None:
            response = self._make_request("PATCH", uri, json=json_data)
        else:
            all_data = {}
            if json_data is not None:
                all_data["requestBody"] = (None, json.dumps(json_data), 'application/json')
            for var_name, file_info in files.items():
                all_data[var_name] = (file_info[0], file_info[1], 'application/octet-stream')
            response = self._make_request("PATCH", uri, files=all_data)
        return json.loads(response.text) if response.text else None

    def request_put(self, uri: str, json_data: dict = None):
        """
        Send a PUT request to the Tuoni server.

        Args:
            uri (str): The URI endpoint to send the request to.
            json_data (dict): A dictionary containing the JSON payload to include in the PUT request.

        Returns:
            dict: The server's response as a dictionary.
        """
        response = self._make_request("PUT", uri, json=json_data)
        return json.loads(response.text) if response.text else None

    def request_delete(self, uri: str, json_data: dict = None):
        """
        Send a DELETE request to the Tuoni server.

        Args:
            uri (str): The URI endpoint to send the request to.
            json_data (dict): A dictionary containing the JSON payload to include in the DELETE request.

        Returns:
            dict: The server's response as a dictionary.
        """
        response = self._make_request("DELETE", uri, json=json_data)
        return json.loads(response.text) if response.text else None

    def load_listener_plugins(self):
        """
        Retrieve a list of listener plugins.

        Returns:
            list[TuoniListenerPlugin]: A list of available listener plugins.

        Examples:
            >>> http_listener_plugin = tuoni_server.load_listener_plugins()[
            >>>     "shelldot.listener.agent-reverse-http"
            >>> ]
            >>> conf = http_listener_plugin.conf_examples["default"]
            >>> conf["sleep"] = 2
            >>> conf["instantResponses"] = True
            >>> listener = http_listener_plugin.create(conf)
        """
        plugins_data = self.request_get("/api/v1/plugins/listeners")
        return {plugin_data["identifier"]["id"]: TuoniListenerPlugin(plugin_data, self) for plugin_data in plugins_data.values()}

    def load_listeners(self):
        """
        Retrieve a list of listeners.

        Returns:
            list[TuoniListener]: A list of active listeners.
        """
        listeners_data = self.request_get("/api/v1/listeners")
        return [TuoniListener(listener_data, self) for listener_data in listeners_data.values()]

    def load_payload_plugins(self):
        """
        Retrieve a list of payload plugins.

        Returns:
            list[TuoniPayloadPlugin]: A list of available payload plugins.
        """
        plugins_data = self.request_get("/api/v1/plugins/payloads")
        return {plugin_data["identifier"]["id"]: TuoniPayloadPlugin(plugin_data, self) for plugin_data in plugins_data.values()}

    def create_payload(self, payload_template: str, payload_listener: int, payload_conf: dict, encrypted: bool = True, payload_name: str = None):
        """
        Create a new payload.

        Args:
            payload_template (str): The payload template to use.
            payload_listener (int): The ID of the listener associated with this payload.
            payload_conf (dict): A dictionary containing the payload's configuration.
            encrypted (bool): Specifies whether traffic for this payload should be encrypted.
            payload_name (str): The name to assign to the payload.

        Returns:
            id: The unique ID of the created payload.

        Examples:
            >>> payload_id = tuoni_server.create_payload(
            >>>     "shelldot.payload.windows-x64",
            >>>     listener_id,
            >>>     {"type": "executable"}
            >>> )
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
        Download a payload.

        Args:
            payload_id (int): The unique ID of the payload to download.
            file_name (str): The name of the file to save the downloaded payload.
        """
        self.request_get_file(f"/api/v1/payloads/{payload_id}/download", file_name)

    def load_agents(self, active = True, unactive = False):
        """
        Retrieve a list of agents.
        
        Args:
            active (bool): Should active agents be returned
            unactive (bool): Should unactive agents be returned

        Returns:
            list[TuoniAgent]: A list of agents.
        """
        agents_data = []
        if active and not unactive:
            agents_data = self.request_get("/api/v1/agents/active")
        elif not active and unactive:
            agents_data = self.request_get("/api/v1/agents/inactive")
        elif active and unactive:
            agents_data = self.request_get("/api/v1/agents")
        return [TuoniAgent(agent_data, self) for agent_data in agents_data]

    def wait_new_agent(self, interval: int = 1, max_wait: int = 0):
        """
        Wait for a new agent to connect.

        Args:
            interval (int): The interval, in seconds, to check for new connections.
            max_wait (int): The maximum time to wait, in seconds. A value of 0 means to wait indefinitely.

        Returns:
            TuoniAgent: The newly connected agent.
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
        Set a callback function to be triggered when a new agent connects.

        Args:
            function (func): The function to execute when a new agent connects.
            interval (int): The interval, in seconds, to check for new connections.

        Examples:
            >>> def new_agent_callback(agent):
            >>>     print(
            >>>         f"We got outselves a new agent {agent.guid} from {agent.metadata['hostname']}"
            >>>     )
            >>>
            >>> tuoni_server.on_new_agent(new_agent_callback)
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
        Retrieve a list of aliases.

        Returns:
            list[TuoniAlias]: A list of aliases.
        """
        all_aliases = self.request_get("/api/v1/command-alias")
        return [TuoniAlias(alias_data, self) for alias_data in all_aliases]

    def add_alias(self, name, description, command_type, command_conf={}, files = None):
        """
        Add a new alias.

        Args:
            name (str): The name of the alias to create.
            description (str): A description of the alias.
            command_type (str | TuoniDefaultCommand): The base command to associate with the alias.
            command_conf (dict): Configuration settings for the alias.
            files (dict): File parameters associated with the alias.

        Returns:
            TuoniAlias: The newly created alias.

        Examples:
            >>> alias1 = tuoni_server.add_alias(
            >>>     "ls1",
            >>>     "Alias made with python lib based on 'ls' default command class",
            >>>     TuoniCommandLs,
            >>>     {"depth": 1}
            >>> )

            >>> alias2 = tuoni_server.add_alias(
            >>>     "ls2",
            >>>     "Alias made with python lib based on command string name",
            >>>     "ls",
            >>>     {"depth": 2}
            >>> )

            >>> alias3 = tuoni_server.add_alias(
            >>>     "easm",
            >>>     "Alias for execute assembly default command class",
            >>>     TuoniCommandexecuteAssembly,
            >>>     {},
            >>>     files = {
            >>>         "executable": ["dotnet.exe",open("dotnet.exe", "rb").read()]
            >>>     }
            >>> )

            >>> alias4 = tuoni_server.add_alias(
            >>>     "bof1",
            >>>     "Alias for bof based on command string name",
            >>>     "bof",
            >>>     files = {
            >>>         "bofFile": ["bof.o",open("bof.o", "rb").read()]
            >>>     }
            >>> )

            >>> alias5 = tuoni_server.add_alias(
            >>>     "bof2",
            >>>     "Alias for bof based on command ID",
            >>>     "2ac58f33-d35e-4afd-a1ac-00e460ceb9f4",
            >>>     files = {
            >>>         "bofFile": ["bof.o",open("bof.o", "rb").read()]
            >>>     }
            >>> )
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
        Retrieve a list of hosted files.

        Returns:
            list[TuoniFile]: A list of objects containing the details of hosted files.
        """
        all_files = self.request_get("/api/v1/files")
        return [TuoniFile(file_data, self) for file_data in all_files]

    def add_hosted(self, filename, file_content, original_filename = None):
        """
        Add a hosted file.

        Args:
            filename (str): The name of the file to host.
            file_content (bytes): The content of the file in bytes.

        Returns:
            str: The API URI for the uploaded file.

        Examples:
            >>> tuoni_server.add_hosted("/hosted/file/here.txt", b"HELLO WORLD")
        """
        if original_filename is None:
            original_filename = os.path.basename(filename)
        return self.request_post("/api/v1/files", files = {filename: [original_filename, file_content]})

    def delete_hosted(self, hosted):
        """
        Delete a hosted file.

        Returns:
            None
        """
        if isinstance(hosted, TuoniFile):
            self.request_delete("/api/v1/file/" + hosted.fileId)
        else:
            self.request_delete("/api/v1/file/" + hosted)

    def load_users(self):
        """
        Retrieve a list of users.

        Returns:
            list[TuoniUser]: A list of users.
        """
        all_users = self.request_get("/api/v1/users")
        return [TuoniUser(user_data, self) for user_data in all_users]

    def add_user(self, username, password, authorities):
        """
        Add a new user.

        Args:
            username (str): The username for the new user.
            password (str): The initial password for the user.
            authorities (list[str]): A list of authorities or roles assigned to the user.

        Returns:
            TuoniUser: The newly created user.

        Examples:
            >>> user = tuoni_server.add_user(
            >>>     "cool_new_user",
            >>>     "cool_new_password",
            >>>     [
            >>>         "MANAGE_LISTENERS",
            >>>         "MANAGE_USERS",
            >>>         "SEND_COMMANDS",
            >>>         "MANAGE_PAYLOADS",
            >>>         "MODIFY_FILES",
            >>>         "VIEW_RESOURCES",
            >>>         "MANAGE_AGENTS"
            >>>     ]
            >>> )
        """
        json_data = {
            "username": username,
            "password": password,
            "authorities": authorities
        }
        user_data = self.request_post("/api/v1/users", json_data, None)
        return TuoniUser(user_data, self)

    def load_datamodel_hosts(self, page = 0, pageSize = 256, filter = None):
        """
        Retrieve a list of hosts.

        Args:
            page (int): Page of the result.
            pageSize (int): How many results per page.
            filter (str): Additional filters.

        Returns:
            list[TuoniDataHost]: A list of hosts.
        """
        if filter is None:
            filter = ""
        else:
            filter = "&" + filter

        all_hosts = self.request_get(f"/api/v1/discovery/hosts?page={page}&pageSize={pageSize}{filter}")
        if "items" in all_hosts:
            return [TuoniDataHost(host_data, self) for host_data in all_hosts["items"]]
        return []

    def add_datamodel_host(self, address, name, note):
        """
        Add a host data model entry.

        Args:
            address (str): The host address.
            name (str): Given name to the host.
            note (str): Additional notes.

        Returns:
            TuoniDataHost: The newly created host.

        Examples:
            >>> host = tuoni_server.add_datamodel_host("10.20.30.40", "WS1", "Open windows machine")
        """
        json_data = {
            "address": address,
            "name": name,
            "note": note
        }
        host_data = self.request_post("/api/v1/discovery/hosts", json_data, None)
        return TuoniDataHost(host_data, self)

    def load_datamodel_services(self, page = 0, pageSize = 256, filter = None):
        """
        Retrieve a list of services.

        Args:
            page (int): Page of the result.
            pageSize (int): How many results per page.
            filter (str): Additional filters.

        Returns:
            list[TuoniDataService]: A list of services.
        """
        if filter is None:
            filter = ""
        else:
            filter = "&" + filter

        all_services = self.request_get(f"/api/v1/discovery/services?page={page}&pageSize={pageSize}{filter}")
        if "items" in all_services:
            return [TuoniDataService(service_data, self) for service_data in all_services["items"]]
        return []

    def add_datamodel_service(self, address, port, protocol, banner, note):
        """
        Add a service data model entry.

        Args:
            address (str): The service address.
            port (int): Port number.
            protocol (str): Service protocol.
            banner (str): Service banner.
            note (str): Additional notes.

        Returns:
            TuoniDataService: The newly created service.

        Examples:
            >>> service = tuoni_server.add_datamodel_service("10.20.30.40", "443", "HTTPS", "", "")
        """
        json_data = {
            "address": address,
            "port": port,
            "protocol": protocol,
            "banner": banner,
            "note": note
        }
        service_data = self.request_post("/api/v1/discovery/services", json_data, None)
        return TuoniDataService(service_data, self)

    def load_datamodel_credentials(self, page = 0, pageSize = 256, filter = None):
        """
        Retrieve a list of credentials.

        Args:
            page (int): Page of the result.
            pageSize (int): How many results per page.
            filter (str): Additional filters.

        Returns:
            list[TuoniDataCredential]: A list of credentials.
        """
        if filter is None:
            filter = ""
        else:
            filter = "&" + filter

        all_credentials = self.request_get(f"/api/v1/discovery/credentials?page={page}&pageSize={pageSize}{filter}")
        if "items" in all_credentials:
            return [TuoniDataCredential(credential_data, self) for credential_data in all_credentials["items"]]
        return []

    def add_datamodel_credential(self, username, password, host, realm, source, note):
        """
        Add a credential data model entry.

        Args:
            username (str): The username.
            password (str): The password.
            host (str): Host where credential works.
            realm (str): Credential realm.
            source (str): Source of the credential.
            note (str): Additional notes.

        Returns:
            TuoniDataCredential: The newly created credential.

        Examples:
            >>> credential = tuoni_server.add_datamodel_credential(
            >>>     "rick",
            >>>     "NeverGonnaBypassYourEDR",
            >>>     "10.20.30.40",
            >>>     "", "", ""
            >>> )
        """
        json_data = {
            "username": username,
            "password": password,
            "host": host,
            "realm": realm,
            "source": source,
            "note": note
        }
        credential_data = self.request_post("/api/v1/discovery/credentials", json_data, None)
        return TuoniDataCredential(credential_data, self)

    def load_jobs(self, page = 0, pageSize = 256, sort_col = "id", sort_order = "asc", inactives = False):
        """
        Retrieve a list of jobs.

        Args:
            page (int): Page of the result.
            pageSize (int): How many results per page.
            sort_col (str): Based of what field to sort
            sort_order (str): Order of sort
            inactives (bool): Should also inactive jobs be returned


        Returns:
            list[TuoniJob]: A list of jobs.
        """
        sort_col = "&" + sort_col + ":" + sort_order
        urlEnd = "all" if inactives else "active"
        all_jobs = self.request_get(f"/api/v1/jobs/{urlEnd}?page={page}&pageSize={pageSize}{sort_col}")
        if "items" in all_jobs:
            return [TuoniJob(job_data, self) for job_data in all_jobs["items"]]
        return []

    def let_it_run(self):
        """
        Block execution and wait indefinitely if any callback functions are initialized,
        or until all monitoring threads have completed.
        """
        for monitoring_thread in self._monitoring_threads:
            monitoring_thread.join()
