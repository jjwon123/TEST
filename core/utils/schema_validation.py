"""Small schema validation boundary.

The project can later swap this for full `jsonschema` validation everywhere.
For the scaffold, this module uses `jsonschema` when available and falls back
to required-field/type checks so workflow and handlers still have a stable API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationIssue:
    path: str
    message: str


class SchemaValidationError(ValueError):
    def __init__(
        self,
        issues: list[ValidationIssue],
        data_label: str = "data",
        schema_label: str = "schema",
    ) -> None:
        self.issues = issues
        self.data_label = data_label
        self.schema_label = schema_label
        detail = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"{data_label} failed validation against {schema_label}: {detail}")


def validate_json(
    data: Any,
    schema: dict[str, Any],
    data_label: str = "data",
    schema_label: str = "schema",
) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        issues = _fallback_validate(data, schema)
        if issues:
            raise SchemaValidationError(issues, data_label=data_label, schema_label=schema_label)
        return

    validator = jsonschema.Draft202012Validator(schema)
    try:
        errors = sorted(validator.iter_errors(data), key=str)
    except Exception as exc:
        if exc.__class__.__name__ not in {"_WrappedReferencingError", "Unresolvable"}:
            raise
        errors = []
        issues = _fallback_validate(data, schema)
        if issues:
            raise SchemaValidationError(issues, data_label=data_label, schema_label=schema_label)
        return

    issues = [
        ValidationIssue(
            path=".".join(str(part) for part in error.absolute_path) or "$",
            message=error.message,
        )
        for error in errors
    ]
    if issues:
        raise SchemaValidationError(issues, data_label=data_label, schema_label=schema_label)


def _fallback_validate(data: Any, schema: dict[str, Any], path: str = "$") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected_type = schema.get("type")
    if expected_type and not _matches_type(data, expected_type):
        issues.append(ValidationIssue(path, f"expected {expected_type}"))
        return issues

    if isinstance(data, dict):
        for field in schema.get("required", []):
            if field not in data:
                issues.append(ValidationIssue(f"{path}.{field}", "required field missing"))

        properties = schema.get("properties", {})
        for key, child_schema in properties.items():
            if key in data and isinstance(child_schema, dict):
                issues.extend(_fallback_validate(data[key], child_schema, f"{path}.{key}"))

    if isinstance(data, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(data):
                issues.extend(_fallback_validate(item, item_schema, f"{path}[{index}]"))

    return issues


def _matches_type(value: Any, expected_type: Any) -> bool:
    expected = expected_type if isinstance(expected_type, list) else [expected_type]
    return any(
        (item == "object" and isinstance(value, dict))
        or (item == "array" and isinstance(value, list))
        or (item == "string" and isinstance(value, str))
        or (item == "integer" and isinstance(value, int) and not isinstance(value, bool))
        or (item == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
        or (item == "boolean" and isinstance(value, bool))
        or (item == "null" and value is None)
        for item in expected
    )
