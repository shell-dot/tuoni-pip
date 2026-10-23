import json
import logging
import math
import random
import string
import ssl
import threading
import time

from tuoni.TuoniExceptions import (
    ExceptionTuoniAuthentication, ExceptionTuoniAuthorization,
    ExceptionTuoniRequestFailed, ExceptionTuoniTimeout,
    ExceptionTuoniTransport, ExceptionTuoniWebSocket,
)

try:
    import websocket
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    _WEBSOCKET_AVAILABLE = False

_log = logging.getLogger(__name__)


class TuoniWebSocket:
    """
    Real-time WebSocket client for the Tuoni server using SockJS/STOMP.

    Subscribes to server-pushed events (agent checkins, command results, listener
    changes, etc.) without polling. Requires the ``websocket-client`` package.

    Expiring tokens and transient disconnects trigger reconnection with restored
    subscriptions. Permission denials and invalid authentication stop recovery.
    Events sent during a disconnect are not replayed by the server.

    Application events use ``TOPIC_EVENTS_*`` resource topics and ``EVENT_*``
    event-type constants. Use ``on_events_*`` for a whole resource category,
    or ``on_event_*`` for one event type. Both receive raw event dictionaries.
    Existing topic callbacks retain their original payload formats.

    Attributes:
        TOPIC_AGENT (str): New agent registered.
        TOPIC_AGENT_HEARTBEAT (str): Agent heartbeat/checkin.
        TOPIC_AGENT_ACTIVE (str): Agent active-status change.
        TOPIC_AGENT_METADATA (str): Agent metadata changed.
        TOPIC_COMMAND_SENT (str): Command dispatched to agent.
        TOPIC_COMMAND_RESULT (str): Command result received.
        TOPIC_COMMAND_TEMPLATE_NEW (str): New command template available.
        TOPIC_COMMAND_TEMPLATE_REMOVED (str): Command template removed.
        TOPIC_COMMAND_ALIAS_NEW (str): New command alias available.
        TOPIC_COMMAND_ALIAS_REMOVED (str): Command alias removed.
        TOPIC_LISTENER_NEW (str): New listener created.
        TOPIC_LISTENER_REMOVED (str): Listener deleted.
        TOPIC_LISTENER_MODIFIED (str): Listener configuration changed.
        TOPIC_PAYLOAD_NEW (str): New payload created.
        TOPIC_PAYLOAD_ARCHIVED (str): Payload archived.
        TOPIC_USER_NEW (str): New user created.
        TOPIC_USER_MODIFIED (str): User modified.
        TOPIC_NOTE (str): Command note created, updated or archived.

    Examples:
        >>> ws = tuoni_server.connect_websocket()
        >>> results = []
        >>> ws.on_command_result(lambda data: results.append(data))
        >>> agent.send_command(TuoniCommandLs(".", 1))
        >>> # callback fires when agent returns the result
    """

    TOPIC_AGENT = "/topic/agent"
    TOPIC_AGENT_HEARTBEAT = "/topic/agent/heartbeat"
    TOPIC_AGENT_ACTIVE = "/topic/agent/active"
    TOPIC_AGENT_METADATA = "/topic/agent/metadata"
    TOPIC_COMMAND_SENT = "/topic/command/sent"
    TOPIC_COMMAND_RESULT = "/topic/command/result"
    TOPIC_COMMAND_TEMPLATE_NEW = "/topic/command-templates/new"
    TOPIC_COMMAND_TEMPLATE_REMOVED = "/topic/command-templates/removed"
    TOPIC_COMMAND_ALIAS_NEW = "/topic/command-alias/new"
    TOPIC_COMMAND_ALIAS_REMOVED = "/topic/command-alias/removed"
    TOPIC_LISTENER_NEW = "/topic/listener/new"
    TOPIC_LISTENER_REMOVED = "/topic/listener/removed"
    TOPIC_LISTENER_MODIFIED = "/topic/listener/modified"
    TOPIC_PAYLOAD_NEW = "/topic/payload/new"
    TOPIC_PAYLOAD_ARCHIVED = "/topic/payload/archived"
    TOPIC_USER_NEW = "/topic/users/new"
    TOPIC_USER_MODIFIED = "/topic/users/modified"

    # Application events share a topic per resource category.
    TOPIC_EVENTS_AGENT = "/topic/events/by-type/AGENT"
    TOPIC_EVENTS_DISCOVERED_HOST = "/topic/events/by-type/DISCOVERED_HOST"
    TOPIC_EVENTS_DISCOVERED_SERVICE = "/topic/events/by-type/DISCOVERED_SERVICE"
    TOPIC_EVENTS_DISCOVERED_CREDENTIAL = "/topic/events/by-type/DISCOVERED_CREDENTIAL"
    TOPIC_EVENTS_JOB = "/topic/events/by-type/JOB"
    TOPIC_EVENTS_COMMAND = "/topic/events/by-type/COMMAND"
    TOPIC_EVENTS_COMMAND_ALIAS = "/topic/events/by-type/COMMAND_ALIAS"
    TOPIC_EVENTS_NOTE = "/topic/events/by-type/NOTE"
    TOPIC_EVENTS_LISTENER = "/topic/events/by-type/LISTENER"
    TOPIC_EVENTS_FILE = "/topic/events/by-type/FILE"
    TOPIC_EVENTS_PAYLOAD = "/topic/events/by-type/PAYLOAD"
    TOPIC_EVENTS_SETTING = "/topic/events/by-type/SETTING"
    TOPIC_EVENTS_USER = "/topic/events/by-type/USER"
    TOPIC_NOTE = TOPIC_EVENTS_NOTE

    EVENT_REGISTER_AGENT = "REGISTER_AGENT"
    EVENT_DEACTIVATE_AGENT = "DEACTIVATE_AGENT"
    EVENT_REACTIVATE_AGENT = "REACTIVATE_AGENT"
    EVENT_BLOCK_AGENT = "BLOCK_AGENT"
    EVENT_UPDATE_AGENT_METADATA = "UPDATE_AGENT_METADATA"
    EVENT_MODIFY_AGENT_METADATA = "MODIFY_AGENT_METADATA"
    EVENT_AGENT_HEARTBEAT = "AGENT_HEARTBEAT"
    EVENT_CREATE_DISCOVERED_HOST = "CREATE_DISCOVERED_HOST"
    EVENT_EDIT_DISCOVERED_HOST = "EDIT_DISCOVERED_HOST"
    EVENT_ARCHIVE_DISCOVERED_HOST = "ARCHIVE_DISCOVERED_HOST"
    EVENT_RESTORE_DISCOVERED_HOST = "RESTORE_DISCOVERED_HOST"
    EVENT_CREATE_DISCOVERED_SERVICE = "CREATE_DISCOVERED_SERVICE"
    EVENT_EDIT_DISCOVERED_SERVICE = "EDIT_DISCOVERED_SERVICE"
    EVENT_ARCHIVE_DISCOVERED_SERVICE = "ARCHIVE_DISCOVERED_SERVICE"
    EVENT_RESTORE_DISCOVERED_SERVICE = "RESTORE_DISCOVERED_SERVICE"
    EVENT_CREATE_DISCOVERED_CREDENTIAL = "CREATE_DISCOVERED_CREDENTIAL"
    EVENT_EDIT_DISCOVERED_CREDENTIAL = "EDIT_DISCOVERED_CREDENTIAL"
    EVENT_ARCHIVE_DISCOVERED_CREDENTIAL = "ARCHIVE_DISCOVERED_CREDENTIAL"
    EVENT_RESTORE_DISCOVERED_CREDENTIAL = "RESTORE_DISCOVERED_CREDENTIAL"
    EVENT_CREATE_JOB = "CREATE_JOB"
    EVENT_UPDATE_JOB = "UPDATE_JOB"
    EVENT_CREATE_COMMAND = "CREATE_COMMAND"
    EVENT_RECOVER_COMMAND = "RECOVER_COMMAND"
    EVENT_SEND_COMMAND = "SEND_COMMAND"
    EVENT_RECEIVE_COMMAND_RESULT = "RECEIVE_COMMAND_RESULT"
    EVENT_CREATE_COMMAND_UPDATE = "CREATE_COMMAND_UPDATE"
    EVENT_SEND_COMMAND_UPDATE = "SEND_COMMAND_UPDATE"
    EVENT_CANCEL_COMMAND = "CANCEL_COMMAND"
    EVENT_CREATE_COMMAND_ALIAS = "CREATE_COMMAND_ALIAS"
    EVENT_UPDATE_COMMAND_ALIAS = "UPDATE_COMMAND_ALIAS"
    EVENT_ARCHIVE_COMMAND_ALIAS = "ARCHIVE_COMMAND_ALIAS"
    EVENT_CREATE_NOTE = "CREATE_NOTE"
    EVENT_UPDATE_NOTE = "UPDATE_NOTE"
    EVENT_ARCHIVE_NOTE = "ARCHIVE_NOTE"
    EVENT_CREATE_LISTENER = "CREATE_LISTENER"
    EVENT_RECOVER_LISTENER = "RECOVER_LISTENER"
    EVENT_UPDATE_LISTENER = "UPDATE_LISTENER"
    EVENT_START_LISTENER = "START_LISTENER"
    EVENT_STOP_LISTENER = "STOP_LISTENER"
    EVENT_DELETE_LISTENER = "DELETE_LISTENER"
    EVENT_CREATE_FILE = "CREATE_FILE"
    EVENT_UPDATE_FILE = "UPDATE_FILE"
    EVENT_DELETE_FILE = "DELETE_FILE"
    EVENT_CREATE_PAYLOAD = "CREATE_PAYLOAD"
    EVENT_RECOVER_PAYLOAD = "RECOVER_PAYLOAD"
    EVENT_UPDATE_PAYLOAD = "UPDATE_PAYLOAD"
    EVENT_ARCHIVE_PAYLOAD = "ARCHIVE_PAYLOAD"
    EVENT_CHANGE_SETTINGS = "CHANGE_SETTINGS"
    EVENT_CREATE_USER = "CREATE_USER"
    EVENT_UPDATE_USER = "UPDATE_USER"
    EVENT_LOGIN_USER = "LOGIN_USER"

    _EVENT_TOPICS = {
        EVENT_REGISTER_AGENT: TOPIC_EVENTS_AGENT,
        EVENT_DEACTIVATE_AGENT: TOPIC_EVENTS_AGENT,
        EVENT_REACTIVATE_AGENT: TOPIC_EVENTS_AGENT,
        EVENT_BLOCK_AGENT: TOPIC_EVENTS_AGENT,
        EVENT_UPDATE_AGENT_METADATA: TOPIC_EVENTS_AGENT,
        EVENT_MODIFY_AGENT_METADATA: TOPIC_EVENTS_AGENT,
        EVENT_AGENT_HEARTBEAT: TOPIC_EVENTS_AGENT,
        EVENT_CREATE_DISCOVERED_HOST: TOPIC_EVENTS_DISCOVERED_HOST,
        EVENT_EDIT_DISCOVERED_HOST: TOPIC_EVENTS_DISCOVERED_HOST,
        EVENT_ARCHIVE_DISCOVERED_HOST: TOPIC_EVENTS_DISCOVERED_HOST,
        EVENT_RESTORE_DISCOVERED_HOST: TOPIC_EVENTS_DISCOVERED_HOST,
        EVENT_CREATE_DISCOVERED_SERVICE: TOPIC_EVENTS_DISCOVERED_SERVICE,
        EVENT_EDIT_DISCOVERED_SERVICE: TOPIC_EVENTS_DISCOVERED_SERVICE,
        EVENT_ARCHIVE_DISCOVERED_SERVICE: TOPIC_EVENTS_DISCOVERED_SERVICE,
        EVENT_RESTORE_DISCOVERED_SERVICE: TOPIC_EVENTS_DISCOVERED_SERVICE,
        EVENT_CREATE_DISCOVERED_CREDENTIAL: TOPIC_EVENTS_DISCOVERED_CREDENTIAL,
        EVENT_EDIT_DISCOVERED_CREDENTIAL: TOPIC_EVENTS_DISCOVERED_CREDENTIAL,
        EVENT_ARCHIVE_DISCOVERED_CREDENTIAL: TOPIC_EVENTS_DISCOVERED_CREDENTIAL,
        EVENT_RESTORE_DISCOVERED_CREDENTIAL: TOPIC_EVENTS_DISCOVERED_CREDENTIAL,
        EVENT_CREATE_JOB: TOPIC_EVENTS_JOB,
        EVENT_UPDATE_JOB: TOPIC_EVENTS_JOB,
        EVENT_CREATE_COMMAND: TOPIC_EVENTS_COMMAND,
        EVENT_RECOVER_COMMAND: TOPIC_EVENTS_COMMAND,
        EVENT_SEND_COMMAND: TOPIC_EVENTS_COMMAND,
        EVENT_RECEIVE_COMMAND_RESULT: TOPIC_EVENTS_COMMAND,
        EVENT_CREATE_COMMAND_UPDATE: TOPIC_EVENTS_COMMAND,
        EVENT_SEND_COMMAND_UPDATE: TOPIC_EVENTS_COMMAND,
        EVENT_CANCEL_COMMAND: TOPIC_EVENTS_COMMAND,
        EVENT_CREATE_COMMAND_ALIAS: TOPIC_EVENTS_COMMAND_ALIAS,
        EVENT_UPDATE_COMMAND_ALIAS: TOPIC_EVENTS_COMMAND_ALIAS,
        EVENT_ARCHIVE_COMMAND_ALIAS: TOPIC_EVENTS_COMMAND_ALIAS,
        EVENT_CREATE_NOTE: TOPIC_EVENTS_NOTE,
        EVENT_UPDATE_NOTE: TOPIC_EVENTS_NOTE,
        EVENT_ARCHIVE_NOTE: TOPIC_EVENTS_NOTE,
        EVENT_CREATE_LISTENER: TOPIC_EVENTS_LISTENER,
        EVENT_RECOVER_LISTENER: TOPIC_EVENTS_LISTENER,
        EVENT_UPDATE_LISTENER: TOPIC_EVENTS_LISTENER,
        EVENT_START_LISTENER: TOPIC_EVENTS_LISTENER,
        EVENT_STOP_LISTENER: TOPIC_EVENTS_LISTENER,
        EVENT_DELETE_LISTENER: TOPIC_EVENTS_LISTENER,
        EVENT_CREATE_FILE: TOPIC_EVENTS_FILE,
        EVENT_UPDATE_FILE: TOPIC_EVENTS_FILE,
        EVENT_DELETE_FILE: TOPIC_EVENTS_FILE,
        EVENT_CREATE_PAYLOAD: TOPIC_EVENTS_PAYLOAD,
        EVENT_RECOVER_PAYLOAD: TOPIC_EVENTS_PAYLOAD,
        EVENT_UPDATE_PAYLOAD: TOPIC_EVENTS_PAYLOAD,
        EVENT_ARCHIVE_PAYLOAD: TOPIC_EVENTS_PAYLOAD,
        EVENT_CHANGE_SETTINGS: TOPIC_EVENTS_SETTING,
        EVENT_CREATE_USER: TOPIC_EVENTS_USER,
        EVENT_UPDATE_USER: TOPIC_EVENTS_USER,
        EVENT_LOGIN_USER: TOPIC_EVENTS_USER,
    }

    def __init__(self, c2):
        """
        Constructor.

        Args:
            c2 (TuoniC2): The server connection to attach to.
        """
        if not _WEBSOCKET_AVAILABLE:
            raise ImportError(
                "websocket-client is required for WebSocket support. "
                "Install it with: pip install websocket-client"
            )
        self.c2 = c2
        self._ws = None
        self._stomp_connected = False
        self._callbacks = {}       # topic -> [callables]
        self._subscriptions = {}   # topic -> sub_id string
        self._sub_counter = 0
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._connect_event = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._identity = None
        self._connection_auth = None
        self._auth_retry = False
        self._error_callbacks = []
        self.last_error = None

    def _build_ws_url(self, base):
        if base.startswith("https://"):
            ws_base = "wss://" + base[8:]
        elif base.startswith("http://"):
            ws_base = "ws://" + base[7:]
        else:
            ws_base = base
        server_id = str(random.randint(0, 999)).zfill(3)
        session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{ws_base}/events/{server_id}/{session_id}/websocket"

    def connect(self, timeout: float = 10) -> bool:
        """
        Connect to the server's WebSocket endpoint and complete the STOMP handshake.

        Args:
            timeout (float): Seconds to wait for the STOMP CONNECTED frame.

        Returns:
            bool: True if the STOMP session was established within ``timeout`` seconds.

        Examples:
            >>> ws = TuoniWebSocket(tuoni_server)
            >>> if not ws.connect():
            >>>     print("WebSocket connection failed")
        """
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError("timeout must be positive and finite")
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive() and self._stop.is_set():
                self._thread.join(timeout=timeout)
                if self._thread.is_alive():
                    raise ExceptionTuoniWebSocket("Previous WebSocket connection is still closing")
            if self._thread is None or not self._thread.is_alive():
                auth = self.c2._register_websocket(self)
                with self._lock:
                    self._identity = auth.identity
                    self._stop.clear()
                    self._connect_event.clear()
                    self._stomp_connected = False
                    self._auth_retry = False
                    self.last_error = None
                    self._thread = threading.Thread(target=self._run, args=(timeout,), daemon=True)
                    self._thread.start()
        self._connect_event.wait(timeout=timeout)
        if self.is_connected:
            return True
        if not self._stop.is_set():
            self._report_error(ExceptionTuoniTimeout("WebSocket handshake timed out"))
        self.disconnect()
        return False

    def _ssl_options(self):
        if self.c2._verify is False:
            return {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}
        options = {"cert_reqs": ssl.CERT_REQUIRED, "check_hostname": True}
        if isinstance(self.c2._verify, str):
            options["ca_certs"] = self.c2._verify
        return options

    def _run(self, timeout):
        delay = 1
        try:
            while not self._stop.is_set():
                ws = None
                auth = None
                renew = False
                try:
                    auth = self.c2._get_auth(self._identity)
                    ws = websocket.WebSocket(sslopt=self._ssl_options(), enable_multithread=True)
                    with self._lock:
                        if self._stop.is_set():
                            break
                        self._ws = ws
                        self._connection_auth = auth
                        self._stomp_connected = False
                    url = self._build_ws_url(auth.url)
                    deadline = time.monotonic() + timeout
                    ws.connect(
                        url, timeout=timeout, http_proxy_timeout=timeout,
                        header={"Authorization": f"Bearer {auth.access_token}"},
                    )
                    if ws.getstatus() != 101:
                        self._stop.set()
                        raise ExceptionTuoniWebSocket("WebSocket upgrade was not accepted", url=url)
                    ws.settimeout(min(1, timeout))
                    while not self._stop.is_set():
                        if not self.c2._session_is_current(self._identity):
                            raise ExceptionTuoniAuthentication("WebSocket session ended; log in again", requires_login=True)
                        if self.c2._needs_refresh(auth):
                            renew = True
                            break
                        if not self.is_connected and time.monotonic() >= deadline:
                            raise ExceptionTuoniTimeout("STOMP handshake timed out", url=url)
                        try:
                            opcode, data = ws.recv_data(control_frame=True)
                        except websocket.WebSocketTimeoutException:
                            continue
                        if opcode == websocket.ABNF.OPCODE_CLOSE:
                            code = int.from_bytes(data[:2], "big") if len(data) >= 2 else None
                            if self.c2._needs_refresh(auth):
                                renew = True
                                break
                            if code == 1008:
                                raise ExceptionTuoniAuthorization(
                                    "WebSocket access revoked or subscription denied; check account permissions",
                                    url=url,
                                )
                            raise ExceptionTuoniWebSocket(f"WebSocket closed (code {code})", url=url)
                        if opcode == websocket.ABNF.OPCODE_TEXT:
                            if self._on_message(ws, data.decode("utf-8") if isinstance(data, bytes) else data):
                                renew = True
                                break
                except websocket.WebSocketBadStatusException as error:
                    status = error.status_code
                    if status == 401 and auth is not None and not self._auth_retry:
                        try:
                            self.c2._refresh_after_rejection(auth)
                            self._auth_retry = True
                            renew = True
                        except ExceptionTuoniRequestFailed as refresh_error:
                            self._stop.set()
                            self._report_error(refresh_error)
                    else:
                        kind = {401: ExceptionTuoniAuthentication, 403: ExceptionTuoniAuthorization}.get(
                            status, ExceptionTuoniWebSocket
                        )
                        if status in {401, 403} or 300 <= status < 400:
                            self._stop.set()
                        if status == 401 and auth is not None:
                            self.c2._invalidate_auth(auth)
                        self._report_error(kind(
                            f"WebSocket handshake rejected (HTTP {status})", status_code=status,
                            method="GET", url=url,
                            response_body=getattr(error, "resp_body", None),
                            response_headers=getattr(error, "resp_headers", None),
                            requires_login=status == 401,
                        ))
                except (ExceptionTuoniAuthentication, ExceptionTuoniAuthorization) as error:
                    self._stop.set()
                    self._report_error(error)
                except ExceptionTuoniRequestFailed as error:
                    if error.requires_login:
                        self._stop.set()
                    self._report_error(error)
                except ssl.SSLError as error:
                    self._stop.set()
                    self._report_error(ExceptionTuoniTransport(f"WebSocket TLS verification/connection failed: {error}"))
                except (OSError, websocket.WebSocketException) as error:
                    if not self._stop.is_set():
                        # websocket-client raises a generic exception when the
                        # redirect limit is exhausted, retaining the HTTP status.
                        status = ws.getstatus() if ws is not None else None
                        if status is not None and 300 <= status < 400:
                            self._stop.set()
                        self._report_error(ExceptionTuoniWebSocket(f"WebSocket connection failed: {error}"))
                except Exception as error:
                    self._stop.set()
                    self._report_error(ExceptionTuoniWebSocket(f"WebSocket protocol failed: {error}"))
                finally:
                    if ws is not None:
                        try:
                            ws.shutdown()
                        except OSError:
                            _log.debug("WebSocket socket was already closed")
                    with self._lock:
                        if self._stomp_connected:
                            delay = 1
                        self._stomp_connected = False
                        self._connect_event.clear()
                        self._ws = None
                        self._connection_auth = None
                if not renew:
                    if self._stop.wait(delay):
                        break
                    delay = min(delay * 2, 30)
        finally:
            self._stop.set()
            self._connect_event.set()

    def _on_message(self, ws, message) -> bool:
        """Return True when a SockJS close requires token renewal."""
        if not message or self._stop.is_set():
            return False
        msg_type = message[0]
        if msg_type == "o":
            # SockJS open — send STOMP CONNECT
            frame = (
                "CONNECT\n"
                f"Authorization:Bearer {self._connection_auth.access_token}\n"
                "accept-version:1.1,1.0\n"
                "heart-beat:0,0\n"
                "\n\x00"
            )
            ws.send(json.dumps([frame]))
        elif msg_type == "h":
            pass  # SockJS heartbeat
        elif msg_type == "a":
            frames = json.loads(message[1:])
            for frame in frames:
                self._handle_stomp_frame(frame)
        elif msg_type == "c":
            code, reason = json.loads(message[1:])
            # The token can expire while recv_data is blocked, just as it can
            # before a raw WebSocket close. Let the supervisor renew the socket.
            if self.c2._needs_refresh(self._connection_auth):
                return True
            if code == 1008:
                raise ExceptionTuoniAuthorization(f"SockJS access denied: {reason}")
            raise ExceptionTuoniWebSocket(f"SockJS closed ({code}): {reason}")
        return False

    def _report_error(self, error):
        with self._lock:
            self.last_error = error
            callbacks = list(self._error_callbacks)
        if callbacks:
            for callback in callbacks:
                self._dispatch(callback, error)
        else:
            _log.warning("%s", error)

    @staticmethod
    def _dispatch(callback, data):
        def invoke():
            try:
                callback(data)
            except Exception:
                _log.exception("Tuoni WebSocket callback failed")
        threading.Thread(target=invoke, daemon=True).start()

    def on_error(self, callback):
        """Register callback(exception) for connection, authorization and protocol errors.

        Callbacks run in daemon threads. The most recent error is also available
        as ``last_error``. Without a callback, errors are logged as warnings.
        """
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._error_callbacks.append(callback)

    # ------------------------------------------------------------------
    # STOMP helpers
    # ------------------------------------------------------------------

    def _parse_stomp_frame(self, frame_str):
        if "\x00" in frame_str:
            frame_str = frame_str[: frame_str.index("\x00")]
        lines = frame_str.split("\n")
        if not lines:
            return "", {}, ""
        frame_type = lines[0].strip()
        headers = {}
        body_start = len(lines)
        for i in range(1, len(lines)):
            line = lines[i]
            if line == "":
                body_start = i + 1
                break
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()
        body = "\n".join(lines[body_start:]) if body_start < len(lines) else ""
        return frame_type, headers, body

    def _send_stomp_subscribe(self, topic, sub_id):
        frame = f"SUBSCRIBE\nid:{sub_id}\ndestination:{topic}\n\n\x00"
        self._ws.send(json.dumps([frame]))

    def _handle_stomp_frame(self, frame_str):
        frame_type, headers, body = self._parse_stomp_frame(frame_str)

        if frame_type == "CONNECTED":
            with self._lock:
                if self._stop.is_set():
                    return
                for topic, sub_id in list(self._subscriptions.items()):
                    self._send_stomp_subscribe(topic, sub_id)
                self._stomp_connected = True
                self._auth_retry = False
            self._connect_event.set()

        elif frame_type == "MESSAGE":
            destination = headers.get("destination", "")
            try:
                data = json.loads(body) if body.strip() else None
            except Exception:
                data = body
            with self._lock:
                callbacks = list(self._callbacks.get(destination, []))
            for cb in callbacks:
                self._dispatch(cb, data)

        elif frame_type == "ERROR":
            self._stop.set()
            raise ExceptionTuoniWebSocket(
                f"STOMP error: {headers.get('message') or body or 'request rejected'}",
                response_body=body,
            )

    # ------------------------------------------------------------------
    # Public subscription API
    # ------------------------------------------------------------------

    def on_event(self, topic: str, callback):
        """
        Subscribe to a STOMP topic and register a callback.

        If already connected the subscription is sent immediately; otherwise it
        is queued and sent once the STOMP session is established.

        Args:
            topic (str): STOMP topic (e.g. ``TuoniWebSocket.TOPIC_COMMAND_RESULT``).
            callback (callable): Called with the deserialized JSON payload when a
                message arrives. Runs in a daemon thread.

        Examples:
            >>> ws.on_event(TuoniWebSocket.TOPIC_AGENT, lambda data: print("new agent:", data))
        """
        if not callable(callback):
            raise TypeError("callback must be callable")
        if not isinstance(topic, str) or not topic or any(char in topic for char in "\r\n\x00"):
            raise ValueError("topic must be a nonempty STOMP destination without control characters")
        try:
            with self._lock:
                is_new = topic not in self._callbacks
                if is_new:
                    self._callbacks[topic] = []
                    self._subscriptions[topic] = f"sub-{self._sub_counter}"
                    self._sub_counter += 1
                self._callbacks[topic].append(callback)
                if is_new and self._stomp_connected:
                    self._send_stomp_subscribe(topic, self._subscriptions[topic])
        except (OSError, websocket.WebSocketException) as error:
            self._report_error(ExceptionTuoniWebSocket(f"Subscription failed; reconnecting: {error}"))
            with self._lock:
                ws = self._ws
            if ws is not None:
                try:
                    ws.abort()
                except OSError:
                    _log.debug("WebSocket socket was already closed")

    def on_new_agent(self, callback):
        """Register a callback for new agent registrations."""
        self.on_event(self.TOPIC_AGENT, callback)

    def on_agent_heartbeat(self, callback):
        """Register a callback for agent heartbeats."""
        self.on_event(self.TOPIC_AGENT_HEARTBEAT, callback)

    def on_agent_active_change(self, callback):
        """Register a callback for agent active-status changes."""
        self.on_event(self.TOPIC_AGENT_ACTIVE, callback)

    def on_command_result(self, callback):
        """Register a callback for command results."""
        self.on_event(self.TOPIC_COMMAND_RESULT, callback)

    def on_command_sent(self, callback):
        """Register a callback for commands dispatched to agents."""
        self.on_event(self.TOPIC_COMMAND_SENT, callback)

    def on_listener_new(self, callback):
        """Register a callback for new listeners."""
        self.on_event(self.TOPIC_LISTENER_NEW, callback)

    def on_listener_modified(self, callback):
        """Register a callback for listener modifications."""
        self.on_event(self.TOPIC_LISTENER_MODIFIED, callback)

    def on_payload_new(self, callback):
        """Register a callback for new payloads."""
        self.on_event(self.TOPIC_PAYLOAD_NEW, callback)

    def on_agent_metadata(self, callback):
        """Register a callback for agent metadata changes."""
        self.on_event(self.TOPIC_AGENT_METADATA, callback)

    def on_command_template_new(self, callback):
        """Register a callback for new command templates."""
        self.on_event(self.TOPIC_COMMAND_TEMPLATE_NEW, callback)

    def on_command_template_removed(self, callback):
        """Register a callback for removed command templates."""
        self.on_event(self.TOPIC_COMMAND_TEMPLATE_REMOVED, callback)

    def on_command_alias_new(self, callback):
        """Register a callback for new command aliases."""
        self.on_event(self.TOPIC_COMMAND_ALIAS_NEW, callback)

    def on_command_alias_removed(self, callback):
        """Register a callback for removed command aliases."""
        self.on_event(self.TOPIC_COMMAND_ALIAS_REMOVED, callback)

    def on_listener_removed(self, callback):
        """Register a callback for removed listeners."""
        self.on_event(self.TOPIC_LISTENER_REMOVED, callback)

    def on_payload_archived(self, callback):
        """Register a callback for archived payloads."""
        self.on_event(self.TOPIC_PAYLOAD_ARCHIVED, callback)

    def on_user_new(self, callback):
        """Register a callback for new users."""
        self.on_event(self.TOPIC_USER_NEW, callback)

    def on_user_modified(self, callback):
        """Register a callback for user modifications."""
        self.on_event(self.TOPIC_USER_MODIFIED, callback)

    def on_event_type(self, event_type: str, callback):
        """
        Register a callback for a single application event type.

        The server groups application events by resource topic. This method
        subscribes to the matching topic and filters its messages by
        ``eventType``. Multiple callbacks share one STOMP subscription per
        topic, including after reconnection.

        Args:
            event_type (str): A supported ``EVENT_*`` constant, such as
                ``TuoniWebSocket.EVENT_CREATE_NOTE``.
            callback (callable): Receives the unchanged event dictionary,
                including ``eventType``, ``actor``, ``parentEvent`` and
                ``references``. Runs in a daemon thread.

        Raises:
            TypeError: If callback is not callable.
            ValueError: If event_type is not a supported event type.

        User events require ``MANAGE_USERS``; other application events require
        ``VIEW_RESOURCES``. Unknown future event types can still be received
        through ``on_event(topic, callback)`` or the category callbacks.

        Examples:
            >>> ws.on_event_type(TuoniWebSocket.EVENT_CREATE_NOTE, print)
        """
        if not callable(callback):
            raise TypeError("callback must be callable")
        if not isinstance(event_type, str) or event_type not in self._EVENT_TOPICS:
            raise ValueError(f"Unsupported application event type: {event_type!r}")

        def handle_event(data):
            if isinstance(data, dict) and data.get("eventType") == event_type:
                callback(data)

        self.on_event(self._EVENT_TOPICS[event_type], handle_event)

    def on_events_agent(self, callback):
        """Register a callback for all ``AGENT`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_AGENT, callback)

    def on_events_discovered_host(self, callback):
        """Register a callback for all ``DISCOVERED_HOST`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_DISCOVERED_HOST, callback)

    def on_events_discovered_service(self, callback):
        """Register a callback for all ``DISCOVERED_SERVICE`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_DISCOVERED_SERVICE, callback)

    def on_events_discovered_credential(self, callback):
        """Register a callback for all ``DISCOVERED_CREDENTIAL`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_DISCOVERED_CREDENTIAL, callback)

    def on_events_job(self, callback):
        """Register a callback for all ``JOB`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_JOB, callback)

    def on_events_command(self, callback):
        """Register a callback for all ``COMMAND`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_COMMAND, callback)

    def on_events_command_alias(self, callback):
        """Register a callback for all ``COMMAND_ALIAS`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_COMMAND_ALIAS, callback)

    def on_events_note(self, callback):
        """Register a callback for all ``NOTE`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_NOTE, callback)

    def on_events_listener(self, callback):
        """Register a callback for all ``LISTENER`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_LISTENER, callback)

    def on_events_file(self, callback):
        """Register a callback for all ``FILE`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_FILE, callback)

    def on_events_payload(self, callback):
        """Register a callback for all ``PAYLOAD`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_PAYLOAD, callback)

    def on_events_setting(self, callback):
        """Register a callback for all ``SETTING`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_SETTING, callback)

    def on_events_user(self, callback):
        """Register a callback for all ``USER`` application events (raw JSON)."""
        self.on_event(self.TOPIC_EVENTS_USER, callback)

    def on_event_register_agent(self, callback):
        """Register a callback for ``REGISTER_AGENT`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_REGISTER_AGENT, callback)

    def on_event_deactivate_agent(self, callback):
        """Register a callback for ``DEACTIVATE_AGENT`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_DEACTIVATE_AGENT, callback)

    def on_event_reactivate_agent(self, callback):
        """Register a callback for ``REACTIVATE_AGENT`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_REACTIVATE_AGENT, callback)

    def on_event_block_agent(self, callback):
        """Register a callback for ``BLOCK_AGENT`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_BLOCK_AGENT, callback)

    def on_event_update_agent_metadata(self, callback):
        """Register a callback for ``UPDATE_AGENT_METADATA`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_AGENT_METADATA, callback)

    def on_event_modify_agent_metadata(self, callback):
        """Register a callback for ``MODIFY_AGENT_METADATA`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_MODIFY_AGENT_METADATA, callback)

    def on_event_agent_heartbeat(self, callback):
        """Register a callback for ``AGENT_HEARTBEAT`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_AGENT_HEARTBEAT, callback)

    def on_event_create_discovered_host(self, callback):
        """Register a callback for ``CREATE_DISCOVERED_HOST`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_DISCOVERED_HOST, callback)

    def on_event_edit_discovered_host(self, callback):
        """Register a callback for ``EDIT_DISCOVERED_HOST`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_EDIT_DISCOVERED_HOST, callback)

    def on_event_archive_discovered_host(self, callback):
        """Register a callback for ``ARCHIVE_DISCOVERED_HOST`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_ARCHIVE_DISCOVERED_HOST, callback)

    def on_event_restore_discovered_host(self, callback):
        """Register a callback for ``RESTORE_DISCOVERED_HOST`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RESTORE_DISCOVERED_HOST, callback)

    def on_event_create_discovered_service(self, callback):
        """Register a callback for ``CREATE_DISCOVERED_SERVICE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_DISCOVERED_SERVICE, callback)

    def on_event_edit_discovered_service(self, callback):
        """Register a callback for ``EDIT_DISCOVERED_SERVICE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_EDIT_DISCOVERED_SERVICE, callback)

    def on_event_archive_discovered_service(self, callback):
        """Register a callback for ``ARCHIVE_DISCOVERED_SERVICE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_ARCHIVE_DISCOVERED_SERVICE, callback)

    def on_event_restore_discovered_service(self, callback):
        """Register a callback for ``RESTORE_DISCOVERED_SERVICE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RESTORE_DISCOVERED_SERVICE, callback)

    def on_event_create_discovered_credential(self, callback):
        """Register a callback for ``CREATE_DISCOVERED_CREDENTIAL`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_DISCOVERED_CREDENTIAL, callback)

    def on_event_edit_discovered_credential(self, callback):
        """Register a callback for ``EDIT_DISCOVERED_CREDENTIAL`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_EDIT_DISCOVERED_CREDENTIAL, callback)

    def on_event_archive_discovered_credential(self, callback):
        """Register a callback for ``ARCHIVE_DISCOVERED_CREDENTIAL`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_ARCHIVE_DISCOVERED_CREDENTIAL, callback)

    def on_event_restore_discovered_credential(self, callback):
        """Register a callback for ``RESTORE_DISCOVERED_CREDENTIAL`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RESTORE_DISCOVERED_CREDENTIAL, callback)

    def on_event_create_job(self, callback):
        """Register a callback for ``CREATE_JOB`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_JOB, callback)

    def on_event_update_job(self, callback):
        """Register a callback for ``UPDATE_JOB`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_JOB, callback)

    def on_event_create_command(self, callback):
        """Register a callback for ``CREATE_COMMAND`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_COMMAND, callback)

    def on_event_recover_command(self, callback):
        """Register a callback for ``RECOVER_COMMAND`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RECOVER_COMMAND, callback)

    def on_event_send_command(self, callback):
        """Register a callback for ``SEND_COMMAND`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_SEND_COMMAND, callback)

    def on_event_receive_command_result(self, callback):
        """Register a callback for ``RECEIVE_COMMAND_RESULT`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RECEIVE_COMMAND_RESULT, callback)

    def on_event_create_command_update(self, callback):
        """Register a callback for ``CREATE_COMMAND_UPDATE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_COMMAND_UPDATE, callback)

    def on_event_send_command_update(self, callback):
        """Register a callback for ``SEND_COMMAND_UPDATE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_SEND_COMMAND_UPDATE, callback)

    def on_event_cancel_command(self, callback):
        """Register a callback for ``CANCEL_COMMAND`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CANCEL_COMMAND, callback)

    def on_event_create_command_alias(self, callback):
        """Register a callback for ``CREATE_COMMAND_ALIAS`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_COMMAND_ALIAS, callback)

    def on_event_update_command_alias(self, callback):
        """Register a callback for ``UPDATE_COMMAND_ALIAS`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_COMMAND_ALIAS, callback)

    def on_event_archive_command_alias(self, callback):
        """Register a callback for ``ARCHIVE_COMMAND_ALIAS`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_ARCHIVE_COMMAND_ALIAS, callback)

    def on_event_create_note(self, callback):
        """Register a callback for ``CREATE_NOTE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_NOTE, callback)

    def on_event_update_note(self, callback):
        """Register a callback for ``UPDATE_NOTE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_NOTE, callback)

    def on_event_archive_note(self, callback):
        """Register a callback for ``ARCHIVE_NOTE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_ARCHIVE_NOTE, callback)

    def on_event_create_listener(self, callback):
        """Register a callback for ``CREATE_LISTENER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_LISTENER, callback)

    def on_event_recover_listener(self, callback):
        """Register a callback for ``RECOVER_LISTENER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RECOVER_LISTENER, callback)

    def on_event_update_listener(self, callback):
        """Register a callback for ``UPDATE_LISTENER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_LISTENER, callback)

    def on_event_start_listener(self, callback):
        """Register a callback for ``START_LISTENER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_START_LISTENER, callback)

    def on_event_stop_listener(self, callback):
        """Register a callback for ``STOP_LISTENER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_STOP_LISTENER, callback)

    def on_event_delete_listener(self, callback):
        """Register a callback for ``DELETE_LISTENER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_DELETE_LISTENER, callback)

    def on_event_create_file(self, callback):
        """Register a callback for ``CREATE_FILE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_FILE, callback)

    def on_event_update_file(self, callback):
        """Register a callback for ``UPDATE_FILE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_FILE, callback)

    def on_event_delete_file(self, callback):
        """Register a callback for ``DELETE_FILE`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_DELETE_FILE, callback)

    def on_event_create_payload(self, callback):
        """Register a callback for ``CREATE_PAYLOAD`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_PAYLOAD, callback)

    def on_event_recover_payload(self, callback):
        """Register a callback for ``RECOVER_PAYLOAD`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_RECOVER_PAYLOAD, callback)

    def on_event_update_payload(self, callback):
        """Register a callback for ``UPDATE_PAYLOAD`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_PAYLOAD, callback)

    def on_event_archive_payload(self, callback):
        """Register a callback for ``ARCHIVE_PAYLOAD`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_ARCHIVE_PAYLOAD, callback)

    def on_event_change_settings(self, callback):
        """Register a callback for ``CHANGE_SETTINGS`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CHANGE_SETTINGS, callback)

    def on_event_create_user(self, callback):
        """Register a callback for ``CREATE_USER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_CREATE_USER, callback)

    def on_event_update_user(self, callback):
        """Register a callback for ``UPDATE_USER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_UPDATE_USER, callback)

    def on_event_login_user(self, callback):
        """Register a callback for ``LOGIN_USER`` application events (raw JSON)."""
        self.on_event_type(self.EVENT_LOGIN_USER, callback)

    def on_note(self, callback):
        """Register a callback for command note events.

        Args:
            callback (callable): Receives the raw JSON event for ``CREATE_NOTE``,
                ``UPDATE_NOTE`` or ``ARCHIVE_NOTE``. Note data is included in
                ``references[].data``. Runs in a daemon thread.

        Requires ``VIEW_RESOURCES``. Existing note objects are not updated
        automatically, and events missed during disconnection are not replayed.
        """
        self.on_event(self.TOPIC_NOTE, callback)

    def disconnect(self):
        """
        Send STOMP DISCONNECT and close the WebSocket.
        """
        self._stop.set()
        self._connect_event.set()
        with self._lock:
            ws = self._ws
            connected = self._stomp_connected
            self._stomp_connected = False
        if ws is not None:
            try:
                if connected:
                    ws.send(json.dumps(["DISCONNECT\n\n\x00"]))
            except (OSError, websocket.WebSocketException):
                _log.debug("WebSocket was already closed during disconnect")
            finally:
                try:
                    ws.abort()
                except OSError:
                    _log.debug("WebSocket socket was already closed")

    @property
    def is_connected(self) -> bool:
        """True if the STOMP session is active."""
        with self._lock:
            return self._stomp_connected
