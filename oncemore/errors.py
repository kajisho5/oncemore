"""Exception types. Anything derived from OncemoreError is shown to the user
as a plain message (no traceback)."""


class OncemoreError(Exception):
    exit_code = 1

    def __init__(self, message, hint=None, details=None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.details = details or {}


class ProjectError(OncemoreError):
    """The project file is invalid. `issues` lists every problem found."""

    exit_code = 2

    def __init__(self, message, issues=None):
        super().__init__(message)
        self.issues = issues or []


class MissingToolsError(OncemoreError):
    exit_code = 3


class ToolFailedError(OncemoreError):
    """An external program exited with an error."""

    exit_code = 4
