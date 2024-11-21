class ExceptionTuoniAuthentication(Exception):
    """
    Exception class thrown in case of authentication issues
    """
    def __init__(self, message=None):
        self.message = message
        super().__init__(message)

class ExceptionTuoniRequestFailed(Exception):
    """
    Exception class thrown in case of failed HTTP request
    """
    def __init__(self, message=None):
        self.message = message
        super().__init__(message)

class ExceptionTuoniDeleted(Exception):
    """
    Exception class thrown in case of trying to interact with deleted resource
    """
    def __init__(self, message=None):
        self.message = message
        super().__init__(message)