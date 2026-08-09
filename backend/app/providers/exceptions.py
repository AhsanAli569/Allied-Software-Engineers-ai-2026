class ProviderError(Exception):
    """Base class for all AI-provider failures. Retryable unless noted otherwise."""


class ProviderRateLimitError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    """5xx / connection failure / model unavailable."""


class ProviderAuthError(ProviderError):
    """Bad or missing API key. Not retried against the same provider."""


class AllProvidersExhaustedError(Exception):
    def __init__(self, attempts: dict[str, str]):
        self.attempts = attempts
        super().__init__(f"All providers failed: {attempts}")


class ProviderMidStreamError(Exception):
    """A provider failed after it had already committed to streaming a response
    (i.e. after the client started receiving content). We do not silently switch
    providers mid-response, since that would mix output from two different models.
    """
