class ExceptionTuoniAuthentication(Exception):
    """
    Exception class raised for authentication-related issues.
    """
    
    def __init__(self, message=None):
        """
        Constructor for the authentication exception.

        Args:
            message (str): The error message describing the authentication issue.
        """
        self.message = message
        super().__init__(message)

class ExceptionTuoniRequestFailed(Exception):
    """
    Exception class raised when an HTTP request fails.
    """
    
    def __init__(self, message=None):
        """
        Constructor for the HTTP request failure exception.

        Args:
            message (str): The error message describing the reason for the failed HTTP request.
        """
        self.message = message
        super().__init__(message)

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