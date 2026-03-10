class TranslatorError(Exception):
    """Base exception for translator errors."""
    pass

class ProtocolMismatchError(TranslatorError):
    """Raised when the target protocol doesn't match available translators."""
    pass

class TranslationError(TranslatorError):
    """Raised when translation logic fails."""
    pass

class HandoffRoutingError(TranslatorError):
    """Raised when no valid multi-hop translation path can be found between protocols."""
    pass
