import time
import requests
import json
import threading
import shutil
from tuoni.TuoniExceptions import *
from tuoni.TuoniListenerPlugin import *
from tuoni.TuoniListener import *
from tuoni.TuoniAgent import *


class TuoniC2:
    def __init__(self):
        self.token = None
        self.url = None
        self.monitoring_threads = []

    def login(self, url, username, password):
        headers = {
            "Authorization":
                "Basic " +
                base64
                .b64encode(
                    (username + ":" + password)
                    .encode('utf-8')
                )
                .decode('utf-8')
        }

        response = requests.request("POST", "%s/api/v1/auth/login" % url, headers=headers, verify=False)
        if response.status_code != 200:
            raise ExceptionTuoniAuthentication(response.text)
        self.token = response.text
        self.url = url

    def _request_check(self):
        if self.token is None:
            raise ExceptionTuoniAuthentication("You have not done the login")

    def _raise_request_exception(result_msg):
        msg = result_msg
        try:
            data = json.loads(result_msg)
            msg = data["message"]
        except:
            pass
        raise ExceptionTuoniRequestFailed(msg)

    def request_get(self, uri, result_as_json=True):
        self._request_check()
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get("%s%s" % (self.url, uri), headers=headers, verify=False)
        if response.status_code != 200:
            TuoniC2._raise_request_exception(response.text)
        if response.text == "":
            return None
        if result_as_json:
            return json.loads(response.text)
        return response.text

    def request_get_file(self, uri, file_name):
        self._request_check()
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get("%s%s" % (self.url, uri), headers=headers, verify=False, stream=True)
        if response.status_code != 200:
            TuoniC2._raise_request_exception(response.text)
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

    def request_post(self, uri, json_data = None):
        self._request_check()
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.post("%s%s" % (self.url, uri), headers=headers, verify=False, json=json_data)
        if response.status_code != 200:
            TuoniC2._raise_request_exception(response.text)
        if response.text == "":
            return None
        return json.loads(response.text)

    def request_put(self, uri, json_data = None):
        self._request_check()
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.put("%s%s" % (self.url, uri), headers=headers, verify=False, json=json_data)
        if response.status_code != 200:
            TuoniC2._raise_request_exception(response.text)
        if response.text == "":
            return None
        return json.loads(response.text)

    def request_delete(self, uri, json_data = None):
        self._request_check()
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.delete("%s%s" % (self.url, uri), headers=headers, verify=False, json=json_data)
        if response.status_code != 200:
            TuoniC2._raise_request_exception(response.text)
        if response.text == "":
            return None
        return json.loads(response.text)

    def load_listener_plugins(self):
        plugins_data = self.request_get("/api/v1/plugins/listeners")
        plugins = {}
        for plugin_name in plugins_data:
            plugin_data = plugins_data[plugin_name]
            plugin_obj = TuoniListenerPlugin(plugin_data, self)
            plugins[plugin_obj.plugin_id] = plugin_obj
        return plugins

    def load_listeners(self):
        listeners_data = self.request_get("/api/v1/listeners")
        listeners = []
        for listener_id in listeners_data:
            listener_data = listeners_data[listener_id]
            listener_obj = TuoniListener(listener_data, self)
            listeners.append(listener_obj)
        return listeners

    def load_agents(self):
        agents_data = self.request_get("/api/v1/agents")
        agents = []
        for agent_data in agents_data:
            agent_obj = TuoniAgent(agent_data, self)
            agents.append(agent_obj)
        return agents

    def wait_new_agent(self, interval = 1):
        agents_data = self.request_get("/api/v1/agents")
        original_agents = []
        for agent_data in agents_data:
            original_agents.append(agent_data["guid"])
        while True:
            time.sleep(interval)
            agents_data = self.request_get("/api/v1/agents")
            for agent_data in agents_data:
                if agent_data["guid"] not in original_agents:
                    return TuoniAgent(agent_data, self)

    def on_new_agent(self, function, interval = 1):
        monitor_thread = threading.Thread(target=self._monitor_for_new_agents, args=(function, interval, ), daemon=True)
        monitor_thread.start()
        self.monitoring_threads.append(monitor_thread)

    def _monitor_for_new_agents(self, function, interval=1):
        agents_data = self.request_get("/api/v1/agents")
        original_agents = []
        for agent_data in agents_data:
            original_agents.append(agent_data["guid"])
        while True:
            time.sleep(interval)
            agents_data = self.request_get("/api/v1/agents")
            for agent_data in agents_data:
                if agent_data["guid"] not in original_agents:
                    original_agents.append(agent_data["guid"])
                    agent = TuoniAgent(agent_data, self)
                    agent_event_thread = threading.Thread(target=function, args=(agent, ))
                    agent_event_thread.start()

    def let_it_run(self):
        for monitoring_thread in self.monitoring_threads:
            monitoring_thread.join()
