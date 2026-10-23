class ExceptionTuoniRequestFailed(Exception):
    """
    An HTTP or transport failure, with details suitable for programmatic handling.

    Attributes:
        status_code (int | None): HTTP status, if a response was received.
        method (str | None): HTTP method.
        url (str | None): Requested URL.
        response_body: Parsed JSON or response text, if available.
        response_headers (dict): Response headers, if available.
        requires_login (bool): Whether the authentication session was invalidated.

    Exception attributes do not retain request headers or bodies, which can
    contain passwords or tokens.
    """

    def __init__(self, message=None, *, status_code=None, method=None, url=None,
                 response_body=None, response_headers=None, requires_login=False):
        self.message = message
        self.status_code = status_code
        self.method = method
        self.url = url
        self.response_body = response_body
        self.response_headers = dict(response_headers or {})
        self.requires_login = requires_login
        super().__init__(message)


class ExceptionTuoniAuthentication(ExceptionTuoniRequestFailed):
    """Missing, expired or rejected authentication (including HTTP 401)."""


class ExceptionTuoniAuthorization(ExceptionTuoniRequestFailed):
    """Insufficient permissions (including HTTP 403). Refresh is not automatic."""


class ExceptionTuoniTransport(ExceptionTuoniRequestFailed):
    """A connection or TLS failure prevented the request from completing."""


class ExceptionTuoniTimeout(ExceptionTuoniTransport):
    """The configured connection or read timeout was exceeded."""


class ExceptionTuoniWebSocket(ExceptionTuoniRequestFailed):
    """A WebSocket or STOMP connection/protocol failure."""


class ExceptionTuoniDeleted(Exception):
    """
    Exception class raised when attempting to interact with a deleted resource.
    """
    
    def __init__(self, message=None):
        """
        Constructor for the deleted resource exception.

        Args:
            message (str): The error message describing the interaction attempt with the deleted resource.
        """
        self.message = message
        super().__init__(message)
