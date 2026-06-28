class IRBridgeError(Exception):
    """Base exception for IRBridge."""


class CodecError(IRBridgeError):
    """Raised when an IR code cannot be decoded or encoded."""
