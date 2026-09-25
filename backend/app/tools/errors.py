class ToolError(Exception):
    """Tool'un kontrollü hatası. code makine için, message kullanıcı için (Türkçe)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message