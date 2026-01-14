class CQRSException(Exception):
    """
    Base exception for all CQRS-related errors.

    This serves as a common root for catching any error emitted by the
    command/query bus infrastructure.
    """

    ...


class HandlerAlreadyRegistered(CQRSException):
    """
    Raised when attempting to register a handler for a message type that already has one.

    In this CQRS implementation, there is a strict 1-to-1 mapping between a message
    type (Command or Query) and its handler to ensure deterministic behavior.
    """

    ...


class HandlerNotFound(CQRSException):
    """
    Raised when a message is dispatched but no handler is registered for its type.

    This usually indicates a configuration error where the `bus.register` call
    was missed or the message type is incorrect.
    """

    ...


class InvalidMessage(CQRSException):
    """
    Raised when a message payload is malformed or invalid.

    This can occur during deserialization or validation checks within the
    message envelope.
    """

    ...
