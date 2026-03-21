NOTES, MOVE SOMEWHERE LATER:

For making tick based items:

if an item type is both stackable and has tick-mutated state that's shared across the stack, all set_item_attribute and remove_item calls in the tick loop must use quantity=0