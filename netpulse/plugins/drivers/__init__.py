from ...models.request import PullingRequest, PushingRequest


class BaseDriver:
    """Driver is the abstract base class for all drivers."""

    driver_name: str = "base"

    @classmethod
    def from_pulling_request(cls, req: PullingRequest) -> "BaseDriver":
        """Create driver instance from a pulling request."""
        raise NotImplementedError

    @classmethod
    def from_pushing_request(cls, req: PushingRequest) -> "BaseDriver":
        """Create driver instance from a pushing request."""
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
