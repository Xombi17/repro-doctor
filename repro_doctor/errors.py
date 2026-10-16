class ReproDoctorError(Exception):
    """Base error for expected repro-doctor failures."""


class InputError(ReproDoctorError):
    """The requested source cannot be isolated."""


class UnsupportedRepositoryError(ReproDoctorError):
    """The source is not a supported, unambiguous repository."""


class DetectionError(ReproDoctorError):
    """Repository metadata could not be interpreted safely."""
