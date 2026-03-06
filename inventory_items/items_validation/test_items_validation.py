# python -m inventory_items.items_validation.test_items_validation

from inventory_items.items_validation.item_pydantic_models import validate_item_dict

from inventory_items.items_provider.item_store import ItemStore

from pydantic import BaseModel
from typing import List

class ItemReport(BaseModel):
    name: str
    error: str | None = None

class ReportData(BaseModel):
    total_items: int
    valid_items: int
    invalid_items: int
    invalid_items_list: List[ItemReport]

item_store = ItemStore()

all_items = item_store.get_all_items()

def single_item_test(item_name: str):
    item_data = item_store.get_item(item_name)
    validated_item, error = validate_item_dict(item_data)
    print(f"Testing item: {item_data['name']}")
    if error:
        #print(f"Invalid item: {item_data['name']}")
        print(f"Error: {error}")
    else:
        print(f"Valid item!, {item_data['name']}")

    print("-" * 20)

def make_report()->ReportData:
    data_structure = ReportData(
        total_items=len(all_items),
        valid_items=0,
        invalid_items=0,
        invalid_items_list=[]
    )
    for item_data in all_items:
        # Grab the name before validation in case validation wipes the item variable
        item_name = item_data.get('name', 'Unknown Item') 
        
        validated_item, error = validate_item_dict(item_data)
        
        if error:
            data_structure.invalid_items += 1
            # Use the stored item_name instead of item['name']
            data_structure.invalid_items_list.append(ItemReport(name=item_name, error=error))
        else:
            data_structure.valid_items += 1
    return data_structure


print("-" * 20)


# single_item_test("Wall-Mounted Snack Dispenser")

# single_item_test("Wall-Mounted Modern OLED TV")


report = make_report()
print("Invalid items:")
print(report.invalid_items)
print("Valid items:")
print(report.valid_items)
print("Total items:")
print(report.total_items)
print("-" * 20)
print("Invalid items list report:")
for item in report.invalid_items_list:
    print(f"Item: {item.name}")
    print(f"Error: {item.error}")
    print("-" * 20)