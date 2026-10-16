class ReproDoctorError(Exception):
    """Base error for expected repro-doctor failures."""


class InputError(ReproDoctorError):
    """The requested source cannot be isolated."""


class UnsupportedRepositoryError(ReproDoctorError):
    """The source is not a supported, unambiguous repository."""


class DetectionError(ReproDoctorError):
    """Repository metadata could not be interpreted safely."""


class AgentError(ReproDoctorError):
    """An OmniRush or injected generation runner failed."""


class AgentTimeoutError(AgentError):
    """A generation role exceeded its bounded timeout."""


class AgentProcessError(AgentError):
    """The OmniRush subprocess could not start or exited unsuccessfully."""


class AgentProtocolError(AgentError):
    """A generation role returned an invalid response."""


class ArtifactValidationError(AgentProtocolError):
    """A role returned an unsafe, duplicate, or out-of-scope artifact."""
