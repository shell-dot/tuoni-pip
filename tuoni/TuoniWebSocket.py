import json
import random
import string
import ssl
import threading

try:
    import websocket
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    _WEBSOCKET_AVAILABLE = False


class TuoniWebSocket:
    """
    Real-time WebSocket client for the Tuoni server using SockJS/STOMP.

    Subscribes to server-pushed events (agent checkins, command results, listener
    changes, etc.) without polling. Requires the ``websocket-client`` package.

    Attributes:
        TOPIC_AGENT (str): New agent registered.
        TOPIC_AGENT_HEARTBEAT (str): Agent heartbeat/checkin.
        TOPIC_AGENT_ACTIVE (str): Agent active-status change.
        TOPIC_AGENT_METADATA (str): Agent metadata changed.
        TOPIC_COMMAND_SENT (str): Command dispatched to agent.
        TOPIC_COMMAND_RESULT (str): Command result received.
        TOPIC_COMMAND_TEMPLATE_NEW (str): New command template available.
        TOPIC_COMMAND_TEMPLATE_REMOVED (str): Command template removed.
        TOPIC_LISTENER_NEW (str): New listener created.
        TOPIC_LISTENER_REMOVED (str): Listener deleted.
        TOPIC_LISTENER_MODIFIED (str): Listener configuration changed.
        TOPIC_PAYLOAD_NEW (str): New payload created.
        TOPIC_PAYLOAD_ARCHIVED (str): Payload archived.
        TOPIC_USER_NEW (str): New user created.
        TOPIC_USER_MODIFIED (str): User modified.

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
    TOPIC_LISTENER_NEW = "/topic/listener/new"
    TOPIC_LISTENER_REMOVED = "/topic/listener/removed"
    TOPIC_LISTENER_MODIFIED = "/topic/listener/modified"
    TOPIC_PAYLOAD_NEW = "/topic/payload/new"
    TOPIC_PAYLOAD_ARCHIVED = "/topic/payload/archived"
    TOPIC_USER_NEW = "/topic/users/new"
    TOPIC_USER_MODIFIED = "/topic/users/modified"

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
        self._connect_event = threading.Event()

    def _build_ws_url(self):
        base = self.c2._url
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
        url = self._build_ws_url()
        headers = [f"Authorization: Bearer {self.c2._token}"]

        sslopt = {}
        if not self.c2._verify:
            sslopt = {"cert_reqs": ssl.CERT_NONE}

        self._ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        t = threading.Thread(
            target=self._ws.run_forever,
            kwargs={"sslopt": sslopt},
            daemon=True,
        )
        t.start()
        self._connect_event.wait(timeout=timeout)
        return self._stomp_connected

    # ------------------------------------------------------------------
    # websocket-client callbacks
    # ------------------------------------------------------------------

    def _on_open(self, ws):
        pass  # Wait for SockJS 'o' frame before sending STOMP CONNECT

    def _on_message(self, ws, message):
        if not message:
            return
        msg_type = message[0]
        if msg_type == "o":
            # SockJS open — send STOMP CONNECT
            frame = (
                "CONNECT\n"
                f"Authorization:Bearer {self.c2._token}\n"
                "accept-version:1.1,1.0\n"
                "heart-beat:0,0\n"
                "\n\x00"
            )
            ws.send(json.dumps([frame]))
        elif msg_type == "h":
            pass  # SockJS heartbeat
        elif msg_type == "a":
            try:
                frames = json.loads(message[1:])
                for frame in frames:
                    self._handle_stomp_frame(frame)
            except Exception:
                pass
        elif msg_type == "c":
            with self._lock:
                self._stomp_connected = False

    def _on_error(self, ws, error):
        self._connect_event.set()

    def _on_close(self, ws, status_code, msg):
        with self._lock:
            self._stomp_connected = False

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
        try:
            frame = f"SUBSCRIBE\nid:{sub_id}\ndestination:{topic}\n\n\x00"
            self._ws.send(json.dumps([frame]))
        except Exception:
            pass

    def _handle_stomp_frame(self, frame_str):
        frame_type, headers, body = self._parse_stomp_frame(frame_str)

        if frame_type == "CONNECTED":
            with self._lock:
                for topic, sub_id in list(self._subscriptions.items()):
                    self._send_stomp_subscribe(topic, sub_id)
                self._stomp_connected = True
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
                try:
                    threading.Thread(target=cb, args=(data,), daemon=True).start()
                except Exception:
                    pass

        elif frame_type == "ERROR":
            self._connect_event.set()

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
        with self._lock:
            if topic not in self._callbacks:
                self._callbacks[topic] = []
                sub_id = f"sub-{self._sub_counter}"
                self._sub_counter += 1
                self._subscriptions[topic] = sub_id
                if self._stomp_connected:
                    self._send_stomp_subscribe(topic, sub_id)
            self._callbacks[topic].append(callback)

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

    def disconnect(self):
        """
        Send STOMP DISCONNECT and close the WebSocket.
        """
        if self._ws:
            with self._lock:
                if self._stomp_connected:
                    try:
                        self._ws.send(json.dumps(["DISCONNECT\n\n\x00"]))
                    except Exception:
                        pass
                    self._stomp_connected = False
            try:
                self._ws.close()
            except Exception:
                pass

    @property
    def is_connected(self) -> bool:
        """True if the STOMP session is active."""
        with self._lock:
            return self._stomp_connected
