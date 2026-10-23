import os
import time
import requests
import json
import threading
import inspect
import math
import weakref
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib3.exceptions import ReadTimeoutError
from tuoni.TuoniExceptions import *
from tuoni.TuoniListenerPlugin import *
from tuoni.TuoniListener import *
from tuoni.TuoniAgent import *
from tuoni.TuoniPayloadPlugin import *
from tuoni.TuoniPayload import *
from tuoni.TuoniAlias import *
from tuoni.TuoniUser import *
from tuoni.TuoniFile import *
from tuoni.TuoniDataHost import *
from tuoni.TuoniDataService import *
from tuoni.TuoniDataCredential import *
from tuoni.TuoniJob import *
from tuoni.TuoniCommandPlugin import *
from tuoni.TuoniCommandTemplate import *
from tuoni.TuoniNote import TuoniNote


@dataclass(frozen=True, repr=False)
class _AuthenticationSession:
    url: str
    access_token: str
    refresh_token: str
    refresh_at: float
    refresh_expires_at: datetime
    identity: object


class TuoniC2:
    """
    The primary class for establishing connections to and managing interactions with the Tuoni server. It provides functionality for controlling server operations and facilitating communication.

    Args:
        verify (str | bool): Defaults to False to accept self-signed certificates.
            True enables certificate verification; a string selects a CA bundle.
            The setting applies to both REST and WebSockets.
        timeout (float | tuple[float, float]): HTTP connection/read timeout in
            seconds. Defaults to (10, 60). A single number applies to both.
    """
    def __init__(self, verify: str | bool = False, timeout=(10, 60)):
        self._auth = None
        self._auth_lock = threading.RLock()
        self._websockets = weakref.WeakSet()
        self._monitoring_threads: list = []
        self._set_verify(verify)
        values = timeout if isinstance(timeout, tuple) else (timeout, timeout)
        if len(values) != 2 or any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0 for value in values
        ):
            raise ValueError("timeout must be a positive number or (connect, read) pair")
        self._timeout = values

    def login(self, url: str, username: str, password: str):
        """
        Log in using v2 authentication. Passwords are not retained.

        Access tokens refresh automatically before expiry. Refresh sessions have
        a fixed server-provided deadline, after which login is required again.
        A successful login disconnects WebSockets belonging to the previous login.

        Args:
            url (str): The URL of the Tuoni server to connect to.
            username (str): The username for authentication.
            password (str): The password for authentication.

        Examples:
            >>> tuoni_server = TuoniC2()
            # Enable SSL verification using the standard trust store
            >>> tuoni_server = TuoniC2(verify=True)
            # Set path for CA bundle
            >>> tuoni_server = TuoniC2(verify="/path/to/ca_bundle.pem")
            # Login to the server
            >>> tuoni_server.login("https://localhost:8443", "my_user", "S3cr37")


        """
        url = url.rstrip("/")
        with self._auth_lock:
            started = time.monotonic()
            with self._send_request(
                "POST", f"{url}/api/v2/auth/login",
                headers={"Authorization": "Basic " + base64.b64encode(
                    f"{username}:{password}".encode("utf-8")
                ).decode("ascii")},
            ) as response:
                self._raise_for_status(response, "POST", f"{url}/api/v2/auth/login")
                auth = self._parse_tokens(response, url, started, object())
            previous_connections = list(self._websockets)
            self._auth = auth
        for connection in previous_connections:
            connection.disconnect()

    def refresh(self):
        """Explicitly refresh, for example after permissions have been granted.

        All refreshes are serialized. A failed or ambiguous rotation invalidates
        the local session; log in again instead of retrying the old refresh token.
        """
        with self._auth_lock:
            self._require_auth()
            self._refresh_locked()

    def logout(self):
        """Revoke the refresh session, clear local tokens and disconnect WebSockets.

        Local logout completes even if the server request fails; that failure is
        still raised. Already-issued access JWTs remain valid until their expiry.
        """
        with self._auth_lock:
            auth = self._auth
            self._auth = None
            connections = list(self._websockets)
        for connection in connections:
            connection.disconnect()
        if auth is not None:
            url = f"{auth.url}/api/v2/auth/logout"
            with self._send_request("POST", url, json={"refreshToken": auth.refresh_token}) as response:
                self._raise_for_status(response, "POST", url)

    def _require_auth(self, identity=None):
        if self._auth is None or (identity is not None and self._auth.identity is not identity):
            raise ExceptionTuoniAuthentication("Log in again to establish a session", requires_login=True)

    def _get_auth(self, identity=None):
        with self._auth_lock:
            self._require_auth(identity)
            if self._needs_refresh(self._auth):
                self._refresh_locked()
            return self._auth

    @staticmethod
    def _needs_refresh(auth):
        return time.monotonic() >= auth.refresh_at

    def _session_is_current(self, identity):
        with self._auth_lock:
            return self._auth is not None and self._auth.identity is identity

    def _register_websocket(self, connection):
        with self._auth_lock:
            auth = self._get_auth()
            self._websockets.add(connection)
            return auth

    def _refresh_after_rejection(self, rejected):
        with self._auth_lock:
            self._require_auth(rejected.identity)
            # Another request may already have rotated this token.
            if self._auth is rejected:
                self._refresh_locked()
            return self._auth

    def _invalidate_auth(self, rejected):
        with self._auth_lock:
            if self._auth is rejected:
                self._auth = None

    def _refresh_locked(self):
        auth = self._auth
        if datetime.now(timezone.utc) >= auth.refresh_expires_at:
            self._auth = None
            raise ExceptionTuoniAuthentication("Refresh session expired; log in again", requires_login=True)
        url = f"{auth.url}/api/v2/auth/refresh"
        # No failure or interruption after sending may leave this token reusable.
        # Other callers cannot observe the transition while this lock is held.
        self._auth = None
        try:
            started = time.monotonic()
            with self._send_request("POST", url, json={"refreshToken": auth.refresh_token}) as response:
                self._raise_for_status(response, "POST", url)
                replacement = self._parse_tokens(response, auth.url, started, auth.identity)
            if replacement.refresh_expires_at != auth.refresh_expires_at:
                raise ExceptionTuoniAuthentication("Server changed the refresh-session deadline")
            self._auth = replacement
        except ExceptionTuoniRequestFailed as error:
            # Even a timeout may mean the server consumed the token. Never reuse it.
            self._auth = None
            error.requires_login = True
            error.message = f"{error.message}. Refresh failed; log in again before continuing"
            error.args = (error.message,)
            raise

    @staticmethod
    def _parse_tokens(response, url, started, identity):
        try:
            data = response.json()
            access = data["accessToken"]
            refresh = data["refreshToken"]
            lifetime = data["expiresIn"]
            deadline = datetime.fromisoformat(data["refreshExpiresAt"].replace("Z", "+00:00"))
            if (data["tokenType"] != "Bearer"
                    or not isinstance(access, str) or not access
                    or not isinstance(refresh, str) or not refresh
                    or isinstance(lifetime, bool) or not isinstance(lifetime, (int, float))
                    or not math.isfinite(lifetime) or lifetime <= 0
                    or deadline.tzinfo is None):
                raise ValueError("Invalid token fields")
            # Use elapsed time from the request start; issuer and client clocks
            # can differ, so JWT wall-clock claims cannot set this deadline.
            return _AuthenticationSession(
                url, access, refresh, started + lifetime - min(30, lifetime / 10),
                deadline, identity,
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            # Never attach a successful token response to an exception.
            raise ExceptionTuoniAuthentication("Invalid authentication response from server") from None

    def _set_verify(self, verify: str | bool):
        if isinstance(verify, bool):
            self._verify = verify
        elif isinstance(verify, str):
            if Path(verify).is_file():
                self._verify = str(Path(verify).resolve())
            else:
                raise ValueError("The path to the CA bundle is not valid")
        else:
            raise TypeError("verify must be a boolean or a CA bundle path")


    @classmethod
    def _raise_for_status(cls, response, method, url):
        if 200 <= response.status_code < 300:
            return
        try:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            message = (body.get("message") or body.get("error")) if isinstance(body, dict) else body
            message = str(message) if message else response.reason or f"HTTP {response.status_code}"
            error_type = {401: ExceptionTuoniAuthentication, 403: ExceptionTuoniAuthorization}.get(
                response.status_code, ExceptionTuoniRequestFailed
            )
            raise error_type(
                f"{method} {url}: {message}", status_code=response.status_code,
                method=method, url=url, response_body=body, response_headers=response.headers,
            )
        except requests.RequestException as error:
            failure = cls._transport_error(error, method, url)
            failure.status_code = response.status_code
            failure.response_headers = dict(response.headers)
            raise failure from error
        finally:
            response.close()

    @staticmethod
    def _is_timeout(error):
        # Requests wraps response-body read timeouts in ConnectionError.
        return isinstance(error, requests.Timeout) or (
            isinstance(error, requests.ConnectionError)
            and any(isinstance(cause, ReadTimeoutError) for cause in error.args)
        )

    @classmethod
    def _transport_error(cls, error, method, url):
        if cls._is_timeout(error):
            return ExceptionTuoniTimeout(f"{method} {url}: request timed out", method=method, url=url)
        return ExceptionTuoniTransport(f"{method} {url}: {error}", method=method, url=url)

    def _send_request(self, method, url, **kwargs):
        try:
            return requests.request(
                method, url, verify=self._verify, timeout=self._timeout,
                allow_redirects=True, **kwargs,
            )
        except requests.RequestException as error:
            raise self._transport_error(error, method, url) from error

    def _make_request(self, method: str, uri: str, **kwargs):
        auth = self._get_auth()
        url = f"{auth.url}{uri}"
        response = self._send_request(method, url, headers={"Authorization": f"Bearer {auth.access_token}"}, **kwargs)
        # Only reads are replayed. Mutations and uploads may have side effects or
        # consumed streams; their caller decides whether to retry after a 401.
        if response.status_code == 401:
            try:
                auth = self._refresh_after_rejection(auth)
            except Exception:
                response.close()
                raise
            if method in {"GET", "HEAD", "OPTIONS"}:
                response.close()
                response = self._send_request(method, url, headers={"Authorization": f"Bearer {auth.access_token}"}, **kwargs)
                if response.status_code == 401:
                    self._invalidate_auth(auth)
        try:
            self._raise_for_status(response, method, url)
        except ExceptionTuoniRequestFailed as error:
            if response.status_code == 401:
                error.requires_login = not self._session_is_current(auth.identity)
            raise
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
        with self._make_request("GET", uri, stream=True) as response:
            try:
                with open(file_name, 'wb') as out_file:
                    for chunk in response.iter_content(chunk_size=65536):
                        out_file.write(chunk)
            except requests.RequestException as error:
                raise self._transport_error(error, "GET", response.url) from error

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

    def request_put_multipart(self, uri: str, files: dict):
        """
        Send a PUT request with multipart/form-data to the Tuoni server.

        Args:
            uri (str): The URI endpoint to send the request to.
            files (dict): A dictionary of files to upload. Each key is the form field name
                and the value is a list of [filename, file_content].

        Returns:
            dict: The server's response as a dictionary, or None.
        """
        all_data = {}
        for var_name, file_info in files.items():
            all_data[var_name] = (file_info[0], file_info[1], "application/octet-stream")
        response = self._make_request("PUT", uri, files=all_data)
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
            int: The unique ID of the created payload.

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

    def rename_payload(self, payload_id: int, new_name: str):
        """
        Rename a payload.

        Args:
            payload_id (int): The unique ID of the payload to rename.
            new_name (str): The new name for the payload.
        """
        self.request_patch(f"/api/v1/payloads/{payload_id}", {"name": new_name})

    def load_payloads(self, include_non_active: bool = False):
        """
        Retrieve a list of payloads.

        Args:
            include_non_active (bool): If True, archived and unavailable payloads are included.

        Returns:
            list[TuoniPayload]: A list of payloads.

        Examples:
            >>> payloads = tuoni_server.load_payloads()
            >>> for p in payloads:
            >>>     print(p.payload_id, p.name)
        """
        param = "true" if include_non_active else "false"
        payloads_data = self.request_get(f"/api/v1/payloads?includeNonActive={param}")
        if payloads_data is None:
            return []
        return [TuoniPayload(p, self) for p in payloads_data]

    def load_payload(self, payload_id: int):
        """
        Retrieve a single payload by its ID.

        Args:
            payload_id (int): The unique ID of the payload.

        Returns:
            TuoniPayload: The requested payload.

        Examples:
            >>> payload = tuoni_server.load_payload(42)
            >>> print(payload.status)
        """
        payload_data = self.request_get(f"/api/v1/payloads/{payload_id}")
        return TuoniPayload(payload_data, self)

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

    def load_command_plugins(self):
        """
        Retrieve a list of command plugins.

        Returns:
            list[TuoniCommandPlugin]: A list of available command plugins.
        """
        plugins_data = self.request_get("/api/v1/plugins/commands")
        return {plugin_data["identifier"]["id"]: TuoniCommandPlugin(plugin_data, self) for plugin_data in plugins_data.values()}
    
    def load_command_templates(self):
        """
        Retrieve a list of command templates.

        Returns:
            list[TuoniCommandTemplate]: A list of available command templates.
        """
        templates_data = self.request_get("/api/v1/command-templates")
        return [TuoniCommandTemplate(template_data, self) for template_data in templates_data]
    
    def load_command_template(self, guid):
        """
        Retrieve a specific command template by its unique identifier.

        Args:
            guid (str): The unique identifier of the command template to retrieve.

        Returns:
            TuoniCommandTemplate: The requested command template, or None if not found.
        """
        template_data = self.request_get(f"/api/v1/command-templates/{guid}")
        if template_data:
            return TuoniCommandTemplate(template_data, self)
        return None

    def load_command_notes(self, agent_guid, command_id, page=0, pageSize=100,
                           label=None, include_archived=False):
        """Load one page of notes for a visible command, ordered oldest first.

        Requires the server's v2 command-notes API and ``VIEW_RESOURCES``.

        Args:
            agent_guid (str): UUID of the command's agent.
            command_id (int): Command identifier.
            page (int): Zero-based page number. Defaults to 0.
            pageSize (int): Notes per page, from 1 to 1000. Defaults to 100.
            label (str | None): Exact, case-sensitive label filter. None omits it.
            include_archived (bool): Include archived notes. Defaults to False.

        Returns:
            list[TuoniNote]: Notes in the requested page, or an empty list.
                Pagination metadata is not returned; pages are not fetched
                automatically.
        """
        uri = (f"/api/v2/agents/{quote(str(agent_guid), safe='')}/commands/"
               f"{quote(str(command_id), safe='')}/notes")
        query = {"page": page, "pageSize": pageSize,
                 "includeArchived": str(include_archived).lower()}
        if label is not None:
            query["label"] = label
        data = self.request_get(f"{uri}?{urlencode(query)}")
        return [TuoniNote(note, self) for note in data["items"]]

    def load_command_note(self, agent_guid, command_id, note_id):
        """Retrieve a command note, including an archived note.

        Args:
            agent_guid (str): UUID of the command's agent.
            command_id (int): Command identifier.
            note_id (str): Note UUID.

        Returns:
            TuoniNote: The note. Requires ``VIEW_RESOURCES``; a missing or
                mismatched command/note raises an HTTP 404 request exception.
        """
        uri = (f"/api/v2/agents/{quote(str(agent_guid), safe='')}/commands/"
               f"{quote(str(command_id), safe='')}/notes/{quote(str(note_id), safe='')}")
        return TuoniNote(self.request_get(uri), self)

    def add_command_note(self, agent_guid, command_id, label, content):
        """Create a note on a visible command. Requires ``SEND_COMMANDS``.

        Args:
            agent_guid (str): UUID of the command's agent.
            command_id (int): Command identifier.
            label (str): Nonblank label, limited to 128 characters. The server
                trims surrounding whitespace.
            content (str): Nonblank content, limited to 2,000 characters.
                Whitespace, including newlines, is preserved.

        Returns:
            TuoniNote: The created note, including its audit events.
        """
        uri = (f"/api/v2/agents/{quote(str(agent_guid), safe='')}/commands/"
               f"{quote(str(command_id), safe='')}/notes")
        data = self.request_post(uri, {"label": label, "content": content})
        return TuoniNote(data, self)

    def load_aliases(self):
        """
        Retrieve a list of aliases.

        Returns:
            list[TuoniAlias]: A list of aliases.
        """
        all_aliases = self.request_get("/api/v1/command-alias")
        return [TuoniAlias(alias_data, self) for alias_data in all_aliases]

    def add_alias(self, name, description, command_type, command_conf=None, files = None):
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
            if command_conf is None:
                command_conf = command_type.command_conf
            if files is None:
                files = command_type.files
            command_type = command_type.command_type
        if inspect.isclass(command_type) and issubclass(command_type, TuoniDefaultCommand):
            command_type = command_type._class_base_type
        if command_conf is None:
            command_conf = {}

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

    def load_hosted_by_path(self, path: str):
        """
        Retrieve a hosted file by its path.

        Args:
            path (str): The hosted path of the file (e.g. ``/somedir/file.txt``).

        Returns:
            TuoniFile: The hosted file.

        Examples:
            >>> f = tuoni_server.load_hosted_by_path("/payloads/agent.exe")
        """
        encoded = quote(path.lstrip("/"), safe="/")
        file_data = self.request_get(f"/api/v1/file/by-path/{encoded}")
        return TuoniFile(file_data, self)

    def delete_hosted_by_path(self, path: str):
        """
        Delete a hosted file by its path.

        Args:
            path (str): The hosted path of the file (e.g. ``/somedir/file.txt``).

        Examples:
            >>> tuoni_server.delete_hosted_by_path("/payloads/agent.exe")
        """
        encoded = quote(path.lstrip("/"), safe="/")
        self.request_delete(f"/api/v1/files/{encoded}")

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
            page (int): Page of the result (only used when ``inactives=True``).
            pageSize (int): How many results per page (only used when ``inactives=True``).
            sort_col (str): Based of what field to sort
            sort_order (str): Order of sort
            inactives (bool): Should also inactive jobs be returned


        Returns:
            list[TuoniJob]: A list of jobs.
        """
        sort_param = f"sort={sort_col}:{sort_order}"
        if inactives:
            all_jobs = self.request_get(f"/api/v1/jobs/all?page={page}&pageSize={pageSize}&{sort_param}")
            if all_jobs is None:
                return []
            if isinstance(all_jobs, dict) and "items" in all_jobs:
                return [TuoniJob(job_data, self) for job_data in all_jobs["items"]]
            return []
        active_jobs = self.request_get(f"/api/v1/jobs/active?{sort_param}")
        if active_jobs is None:
            return []
        return [TuoniJob(job_data, self) for job_data in active_jobs]

    def load_settings(self):
        """
        Retrieve all server settings.

        Returns:
            dict: A dict with ``server`` and ``plugin`` keys, each containing setting objects.

        Examples:
            >>> settings = tuoni_server.load_settings()
            >>> for key, s in settings["server"].items():
            >>>     print(key, s["currentValue"])
        """
        return self.request_get("/api/v1/settings")

    def update_settings(self, settings: dict):
        """
        Update multiple server settings at once.

        Args:
            settings (dict): A mapping of setting key to new value. Follows the same
                structure as ``AllSettingsUpdateRequest`` on the server.

        Returns:
            dict: The updated settings.
        """
        return self.request_patch("/api/v1/settings", settings)

    def load_setting(self, key: str):
        """
        Retrieve a single server setting by key.

        Args:
            key (str): The setting key.

        Returns:
            dict: The setting object including ``currentValue``, ``defaultValue``, ``type``, etc.

        Examples:
            >>> s = tuoni_server.load_setting("tuoni.websocket.command-result-max-size")
            >>> print(s["currentValue"])
        """
        return self.request_get(f"/api/v1/setting/{key}")

    def update_setting(self, key: str, value):
        """
        Update a single server setting.

        Args:
            key (str): The setting key.
            value: The new value for the setting (must be JSON-serialisable).

        Returns:
            dict: The updated setting object.

        Examples:
            >>> tuoni_server.update_setting("tuoni.agent.default-sleep", 5)
        """
        return self.request_put(f"/api/v1/setting/{key}", {"value": value})

    def connect_websocket(self, timeout: float = 10, on_error=None):
        """
        Connect to the Tuoni server's real-time WebSocket endpoint.

        Requires the ``websocket-client`` package (``pip install websocket-client``).

        Args:
            timeout (float): Seconds to wait for the STOMP handshake to complete.
            on_error (callable): Optional callback(exception) for connection or
                permission failures, including failures during reconnection.

        Returns:
            TuoniWebSocket: A connected WebSocket client ready for subscriptions.

        Raises:
            Exception: If the connection cannot be established within ``timeout`` seconds.

        Examples:
            >>> ws = tuoni_server.connect_websocket()
            >>> results = []
            >>> ws.on_command_result(lambda data: results.append(data))
        """
        from tuoni.TuoniWebSocket import TuoniWebSocket
        ws = TuoniWebSocket(self)
        if on_error is not None:
            ws.on_error(on_error)
        connected = ws.connect(timeout=timeout)
        if not connected:
            raise ws.last_error or ExceptionTuoniTimeout("Failed to connect to Tuoni WebSocket within timeout")
        return ws

    def let_it_run(self):
        """
        Block execution and wait indefinitely if any callback functions are initialized,
        or until all monitoring threads have completed.
        """
        for monitoring_thread in self._monitoring_threads:
            monitoring_thread.join()
