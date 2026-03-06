# contract_mixin.py
#
# Defines ContractMixin — the required base class for ALL item and room field
# contract mixins. Enforces discipline at class *definition* time via
# __init_subclass__, so a bad mixin is an import error, not a silent runtime bug.
#
# Rules enforced (TypeError raised immediately if violated):
#   1. Every field must have a non-empty Field(description=...).
#   2. No field may be typed as Any or object.
#   3. No field may be Optional (i.e. allow None). Mixin fields are always
#      required — the LLM schema builder wraps them in Optional automatically.
#   4. model_config must set extra="forbid". Loose extra keys on a mixin are
#      a contract smell; the base model (BaseItem / BaseRoom) owns extra="allow".
#
# Usage:
#   class MyTypeFields(ContractMixin):
#       my_field: str = Field(description="What this field means.")
#
# Do NOT set model_config on your subclass — ContractMixin sets it for you.
# Do NOT mark fields Optional — if a field is conditionally present, reconsider
# whether it belongs in the mixin at all.

from typing import Any, ClassVar, Optional, get_args, get_origin, Union
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_optional(annotation: Any) -> bool:
    """Return True if annotation is Optional[X] (i.e. Union[X, None])."""
    return get_origin(annotation) is Union and type(None) in get_args(annotation)


def _is_any(annotation: Any) -> bool:
    """Return True if annotation is Any or object."""
    return annotation is Any or annotation is object


# ---------------------------------------------------------------------------
# ContractMixin
# ---------------------------------------------------------------------------

class ContractMixin(BaseModel):
    """
    Base class for all item and room field contract mixins.

    Subclasses MUST:
      - Declare every field with a non-empty Field(description=...).
      - Use concrete, non-Optional type annotations on all fields.

    Subclasses MUST NOT:
      - Set model_config themselves (ContractMixin sets extra="forbid").
      - Use Any or object as a field type.
      - Mark any field Optional.

    Violations raise TypeError at class definition time (import error).

    Optional class variable:
        model_description: ClassVar[str]
            A plain English description of what this item/room type *is*.
            Survives field flattening in build_llm_schema() and is injected
            into the generated model's docstring, giving the LLM semantic
            context about the type. Example:
                model_description: ClassVar[str] = "A vessel of spirit fuel for the lighthouse lamp."
    """

    model_config = ConfigDict(extra="forbid")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Collect all violations before raising so the dev sees everything at once.
        violations: list[str] = []

        # Guard: subclass must not override model_config to re-allow extras.
        own_config = cls.__dict__.get("model_config")
        if own_config is not None:
            extra_setting = getattr(own_config, "extra", None)
            if extra_setting is not None and extra_setting != "forbid":
                violations.append(
                    f"model_config.extra must be 'forbid' (or omitted); "
                    f"got '{extra_setting}'. ContractMixin sets this for you."
                )

        for field_name, field_info in cls.model_fields.items():
            # Skip fields inherited from ContractMixin itself (none currently,
            # but future-proofs against accidental base field additions).
            if field_name in ContractMixin.model_fields:
                continue

            annotation = field_info.annotation

            # Rule 1 — no Any / object
            if _is_any(annotation):
                violations.append(
                    f"Field '{field_name}': type 'Any' / 'object' is not allowed. "
                    f"Use a concrete type."
                )

            # Rule 2 — no Optional
            if _is_optional(annotation):
                violations.append(
                    f"Field '{field_name}': Optional fields are not allowed in mixins. "
                    f"Declare it as required; the LLM schema builder wraps it in "
                    f"Optional automatically."
                )

            # Rule 3 — must have a non-empty description
            desc = field_info.description
            if not desc or not desc.strip():
                violations.append(
                    f"Field '{field_name}': missing Field(description=...). "
                    f"Every mixin field must document what it means."
                )

        if violations:
            bullet_list = "\n  - ".join(violations)
            raise TypeError(
                f"ContractMixin subclass '{cls.__name__}' has invalid field definitions:\n"
                f"  - {bullet_list}"
            )