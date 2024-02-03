class ExceptionTuoniAuthentication(Exception):
    def __init__(self, message=None):
        self.message = message
        super().__init__(message)

class ExceptionTuoniRequestFailed(Exception):
    def __init__(self, message=None):
        self.message = message
        super().__init__(message)

class ExceptionTuoniDeleted(Exception):
    def __init__(self, message=None):
        self.message = message
        super().__init__(message)