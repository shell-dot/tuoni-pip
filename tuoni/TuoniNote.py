import re
from urllib.parse import quote, urlsplit
from uuid import UUID

from tuoni.TuoniEvent import TuoniEvent
from tuoni.TuoniExceptions import ExceptionTuoniDeleted


class TuoniNote:
    """A note attached to a command, including its audit events.

    Edit ``label`` or ``content``, then call :meth:`update` to save both fields.
    The server trims labels and preserves content whitespace. Archiving is
    permanent, but archived notes remain readable.

    Attributes:
        note_id (str): The note's UUID.
        target (dict): Command target with ``targetType``, ``commandId`` and
            an ``href`` identifying the command. Requests always use this
            client's server, including when the server returns absolute links.
        label (str): Nonblank label, limited to 128 characters by the server.
        content (str): Nonblank content, limited to 2,000 characters.
        status (str): ``ACTIVE`` or ``ARCHIVED``.
        createEvent (TuoniEvent): Note creation event.
        lastUpdateEvent (TuoniEvent): Most recent update or archive event.
        archiveEvent (TuoniEvent | None): Archive event, if archived.
    """

    def __init__(self, conf, c2):
        """Wrap a server note without making requests.

        Args:
            conf (dict): Note response from the server.
            c2 (TuoniC2): Client used for subsequent requests.
        """
        self.c2 = c2
        self._load_conf(conf)

    def _load_conf(self, conf):
        self.note_id = conf["id"]
        self.target = conf["target"]
        self.label = conf["label"]
        self.content = conf["content"]
        self.status = conf["status"]
        self.createEvent = TuoniEvent(conf["createEvent"], self.c2)
        self.lastUpdateEvent = TuoniEvent(conf["lastUpdateEvent"], self.c2)
        self.archiveEvent = (
            TuoniEvent(conf["archiveEvent"], self.c2)
            if conf.get("archiveEvent") is not None else None
        )

    def _get_uri(self):
        if self.note_id is None:
            raise ExceptionTuoniDeleted("")
        href = self.target.get("href")
        parts = urlsplit(href) if isinstance(href, str) else None
        path = ""
        if parts is not None and not parts.query and not parts.fragment:
            if not parts.scheme and not parts.netloc:
                path = parts.path
            elif parts.scheme in {"http", "https"} and parts.netloc:
                # Absolute server links may include a servlet context prefix.
                # The client already owns its base URL; use only the API path.
                start = parts.path.find("/api/v2/agents/")
                if start >= 0:
                    path = parts.path[start:]
        match = re.fullmatch(
            r"/api/v2/agents/([0-9a-fA-F-]{36})/commands/([0-9]+)", path
        )
        if (self.target.get("targetType") != "COMMAND" or match is None
                or int(match[2]) != self.target.get("commandId")):
            raise ValueError("Note target must contain a matching command API path")
        # Validate the agent identifier as well as the path shape before using it.
        UUID(match[1])
        return f"{path}/notes/{quote(str(self.note_id), safe='')}"

    def reload(self):
        """Reload this note, including an archived note, from the server.

        Requires ``VIEW_RESOURCES``. Replaces local fields and returns None.
        """
        data = self.c2.request_get(self._get_uri())
        self._load_conf(data)

    def update(self):
        """Save the current label and content, then refresh local fields.

        Requires ``SEND_COMMANDS`` and note ownership, unless ``MANAGE_USERS``
        grants an ownership override. The server rejects invalid fields with
        HTTP 400 and archived or concurrently changed notes with HTTP 409.
        Request failures use the existing Tuoni request exceptions; local
        fields are refreshed only on success. Returns None.

        Examples:
            >>> note.content = "Reviewed the command output."
            >>> note.update()
        """
        data = self.c2.request_patch(
            self._get_uri(), {"label": self.label, "content": self.content}
        )
        self._load_conf(data)

    def archive(self):
        """Permanently archive this note and refresh its status and events.

        Requires ``SEND_COMMANDS`` and ownership or a ``MANAGE_USERS`` ownership
        override. Repeated archiving is supported. The identifier is retained
        so the note can still be reloaded. Returns None.
        """
        data = self.c2.request_delete(self._get_uri())
        self._load_conf(data)
