from ...models.request import ExecutionRequest


class BaseDriver:
    """Driver is the abstract base class for all drivers."""

    driver_name: str = "base"

    @classmethod
    def from_execution_request(cls, req: ExecutionRequest) -> "BaseDriver":
        """Create driver instance from a execution request."""
        raise NotImplementedError

    @classmethod
    def validate(cls, req: ExecutionRequest) -> None:
        """Validate the request without creating the driver instance."""
        raise NotImplementedError

    def __init__(self, **kwargs):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def send(self, session, command: list[str]):
        raise NotImplementedError

    def config(self, session, config: list[str]):
        raise NotImplementedError

    def disconnect(self, session):
        raise NotImplementedError
