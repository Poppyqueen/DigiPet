import os
from typing import get_args, get_origin
from inventory_items.items_validation.item_pydantic_models import TYPE_FIELD_CONTRACTS, BaseItem

def format_type_hint(annotation):
    """Clean up type hints for readable documentation."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    
    if origin is list:
        return f"List[{format_type_hint(args[0])}]"
    if origin is dict:
        return f"Dict[{format_type_hint(args[0])}, {format_type_hint(args[1])}]"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation).replace("typing.", "")

def generate_documentation(output_file: str = "ITEM_SYSTEM_DOCS.md"):
    lines = []
    lines.append("# Item System Contract Documentation")
    lines.append("\nThis document is auto-generated from the Pydantic contract registry. It defines the required keys and semantic behavior for all item types.")

    # 1. Base Item Section
    lines.append("\n## 1. Base Item (Global Contract)")
    lines.append("Every item, regardless of type, must include these fields:")
    lines.append("\n| Field | Type | Description |")
    lines.append("| :--- | :--- | :--- |")
    for name, field in BaseItem.model_fields.items():
        type_str = format_type_hint(field.annotation)
        lines.append(f"| `{name}` | `{type_str}` | {field.description} |")

    # 2. Specific Type Contracts
    lines.append("\n## 2. Specialized Item Types")
    lines.append("When an item includes one of these strings in its `type` list, it must satisfy the following additional field requirements.")

    for type_key, contract_cls in TYPE_FIELD_CONTRACTS.items():
        lines.append(f"\n### Type: `{type_key}`")
        
        # Pull model_description if it exists
        doc = getattr(contract_cls, "model_description", "No description provided.")
        if doc:
            lines.append(f"> {doc}")

        # Field Table
        fields = contract_cls.model_fields
        if not fields:
            lines.append("\n*No unique fields required (marker type).*")
        else:
            lines.append("\n| Field | Type | Description |")
            lines.append("| :--- | :--- | :--- |")
            for f_name, f_info in fields.items():
                f_type = format_type_hint(f_info.annotation)
                lines.append(f"| `{f_name}` | `{f_type}` | {f_info.description} |")
        
        # Examine behavior
        if contract_cls.examine_fields:
            lines.append(f"\n**Examine Tool Fields:** `{', '.join(contract_cls.examine_fields)}`")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Documentation successfully generated to: {output_file}")

if __name__ == "__main__":
    generate_documentation()