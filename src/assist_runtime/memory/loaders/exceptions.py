class MemoryError(Exception):
    pass

class MemoryLoadError(MemoryError):

    def __init__(self, message: str):

        super().__init__(message)
        self.message = message