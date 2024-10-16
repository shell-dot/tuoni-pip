import time
import requests
import json
import threading
import shutil
import base64
from tuoni.TuoniExceptions import *
from tuoni.TuoniListenerPlugin import *
from tuoni.TuoniListener import *
from tuoni.TuoniAgent import *
from tuoni.TuoniPayloadPlugin import *


class TuoniC2:
    def __init__(self):
        self.token: str = None
        self.url: str = None
        self.monitoring_threads: list = []

    def login(self, url: str, username: str, password: str):
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('utf-8')
        }

        response = requests.post(f"{url}/api/v1/auth/login", headers=headers, verify=False)
        if response.status_code != 200:
            raise ExceptionTuoniAuthentication(response.text)
        self.token = response.text
        self.url = url

    def _request_check(self):
        if self.token is None:
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
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.request(method, f"{self.url}{uri}", headers=headers, verify=False, **kwargs)
        if response.status_code != 200:
            self._raise_request_exception(response.text)
        return response

    def request_get(self, uri: str, result_as_json: bool = True):
        response = self._make_request("GET", uri)
        if response.text == "":
            return None
        return json.loads(response.text) if result_as_json else response.text

    def request_get_file(self, uri: str, file_name: str):
        response = self._make_request("GET", uri, stream=True)
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

    def request_post(self, uri: str, json_data: dict = None, files: dict = None):
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
        response = self._make_request("PUT", uri, json=json_data)
        return json.loads(response.text) if response.text else None

    def request_delete(self, uri: str, json_data: dict = None):
        response = self._make_request("DELETE", uri, json=json_data)
        return json.loads(response.text) if response.text else None

    def load_listener_plugins(self):
        plugins_data = self.request_get("/api/v1/plugins/listeners")
        return {plugin_data["identifier"]["id"]: TuoniListenerPlugin(plugin_data, self) for plugin_data in plugins_data.values()}

    def load_listeners(self):
        listeners_data = self.request_get("/api/v1/listeners")
        return [TuoniListener(listener_data, self) for listener_data in listeners_data.values()]

    def load_payload_plugins(self):
        plugins_data = self.request_get("/api/v1/plugins/payloads")
        return {plugin_data["identifier"]["id"]: TuoniPayloadPlugin(plugin_data, self) for plugin_data in plugins_data.values()}

    def create_payload(self, payload_template: str, payload_listener: str, payload_conf: dict, encrypted: bool = True):
        json_data = {
            "payloadTemplateId": payload_template,
            "configuration": payload_conf,
            "listenerId": payload_listener,
            "encrypted": encrypted
        }
        payload_data = self.request_post("/api/v1/payloads", json_data)
        return payload_data["id"]

    def download_payload(self, payload_id: int, file_name: str):
        self.request_get_file(f"/api/v1/payloads/{payload_id}/download", file_name)

    def load_agents(self):
        agents_data = self.request_get("/api/v1/agents")
        return [TuoniAgent(agent_data, self) for agent_data in agents_data]

    def wait_new_agent(self, interval: int = 1, max_wait: int = 0):
        original_agents = {agent_data["guid"] for agent_data in self.request_get("/api/v1/agents")}
        while True:
            time.sleep(interval)
            agents_data = self.request_get("/api/v1/agents")
            for agent_data in agents_data:
                if agent_data["guid"] not in original_agents:
                    return TuoniAgent(agent_data, self)
            if max_wait > 0:
                max_wait -= interval
                if max_wait <= 0:
                    return None

    def on_new_agent(self, function, interval: int = 1):
        monitor_thread = threading.Thread(target=self._monitor_for_new_agents, args=(function, interval), daemon=True)
        monitor_thread.start()
        self.monitoring_threads.append(monitor_thread)

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

    def let_it_run(self):
        for monitoring_thread in self.monitoring_threads:
            monitoring_thread.join()