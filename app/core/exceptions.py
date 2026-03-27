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

class HandoffAuthorizationError(TranslatorError):
    """Raised when the provided EAT (Engram Access Token) is invalid or unauthorized."""
    pass

# Transient Errors (Retriable)
class TransientError(TranslatorError):
    """Base for errors that are likely to succeed on retry."""
    pass

class RateLimitError(TransientError):
    """Raised when an external API returns a rate limit error (e.g. 429)."""
    pass

class NetworkError(TransientError):
    """Raised for network connection or timeout errors."""
    pass

# Permanent Errors (Non-Retriable)
class PermanentError(TranslatorError):
    """Base for errors that will fail even on retry."""
    pass

class InvalidCredentialsError(PermanentError):
    """Raised when API keys or OAuth tokens are invalid or missing."""
    pass

class ExpiredTokenError(PermanentError):
    """Raised when a session or provider token has expired and requires user action."""
    pass

