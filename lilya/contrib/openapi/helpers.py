import inspect
from typing import Any, Literal, _GenericAlias, get_args

from pydantic import BaseModel, TypeAdapter, create_model
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue

from lilya._internal._encoders import ENCODER_TYPES
from lilya.contrib.openapi.params import ResponseParam


def get_definitions(
    *,
    fields: list[FieldInfo] | list[ResponseParam],
    schema_generator: GenerateJsonSchema,
) -> tuple[
    dict[tuple[FieldInfo, Literal["validation", "serialization"]], JsonSchemaValue],
    dict[str, dict[str, Any]],
]:
    inputs = [(field, "validation", TypeAdapter(field.annotation).core_schema) for field in fields]
    field_mapping, definitions = schema_generator.generate_definitions(
        inputs=inputs  # type: ignore
    )

    return field_mapping, definitions  # type: ignore[return-value]


def get_base_annotations(base_annotation: Any, is_class: bool = False) -> dict[str, Any]:
    """
    Returns the annotations of the base class.

    Args:
        base_annotation (Any): The base class.
        is_class (bool): Whether the base class is a class or not.
    Returns:
        dict[str, Any]: The annotations of the base class.
    """
    base_annotations: dict[str, Any] = {}
    if not is_class:
        bases = base_annotation.__bases__
    else:
        bases = base_annotation.__class__.__bases__

    for base in bases:
        base_annotations.update(**get_base_annotations(base))
        if hasattr(base, "__annotations__"):
            for name, annotation in base.__annotations__.items():
                base_annotations[name] = annotation
    return base_annotations


def convert_annotation_to_pydantic_model(field_annotation: Any) -> Any:
    """
    Converts any annotation of the body into a Pydantic
    base model.

    This is used for OpenAPI representation purposes only.

    Lilya will try internally to convert the model into a Pydantic BaseModel,
    this will serve as representation of the model in the documentation but internally,
    it will use the native type to validate the data being sent and parsed in the
    payload/data field.

    Encoders are not supported in the OpenAPI representation, this is because the encoders
    are unique to Lilya and are not part of the OpenAPI specification. This is why
    we convert the encoders into a Pydantic model for OpenAPI representation purposes only.
    """
    annotation_args = get_args(field_annotation)
    if isinstance(field_annotation, (_GenericAlias, list, tuple)):
        annotations = tuple(convert_annotation_to_pydantic_model(arg) for arg in annotation_args)
        field_annotation.__args__ = annotations
        return field_annotation

    if (  # type: ignore
        not isinstance(field_annotation, BaseModel)
        # call before encoder check, because this test is faster
        and inspect.isclass(field_annotation)
        and any(encoder.is_type(field_annotation) for encoder in ENCODER_TYPES.get())
    ):
        field_definitions: dict[str, Any] = {}

        # Get any possible annotations from the base classes
        # This can be useful for inheritance with custom encoders
        base_annotations: dict[str, Any] = {**get_base_annotations(field_annotation)}
        field_annotations = {
            **base_annotations,
            **field_annotation.__annotations__,
        }
        for name, annotation in field_annotations.items():
            field_definitions[name] = (annotation, ...)
        return create_model(
            field_annotation.__name__,
            __config__={"arbitrary_types_allowed": True},
            **field_definitions,
        )
    return field_annotation
