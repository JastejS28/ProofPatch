class LLMError(Exception):
    """Base exception for LLM provider failures."""


class LLMQuotaExceededError(LLMError):
    """Provider quota, token, or rate limit exhausted."""


class LLMUnavailableError(LLMError):
    """Provider is temporarily unavailable."""


class LLMRequestError(LLMError):
    """Provider rejected the request."""


class LLMTimeoutError(LLMError):
    """Provider call exceeded our application timeout."""