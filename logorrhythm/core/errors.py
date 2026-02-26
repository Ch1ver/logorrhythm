"""Protocol/session exceptions."""


class LogorrhythmError(Exception):
    pass


class SchemaError(LogorrhythmError):
    pass


class HandshakeError(LogorrhythmError):
    pass


class EncodingError(LogorrhythmError):
    pass


class DecodingError(LogorrhythmError):
    pass
