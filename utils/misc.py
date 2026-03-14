import random
from typing import Any

def check_one_in(number: int):
  """
  Checks if a random event with a 1 in (the given argument) chance occurs.

  Returns:
      bool: True if the  event occurs, False otherwise.
  """
  # Generate a random integer between 1 and number (inclusive)
  random_number = random.randint(1, number)

  # The event occurs if the number is 1
  if random_number == 1:
    return True
  else:
    return False

def front_weighted_pick(items: list[Any], none_chance=0.0):
    """
    Picks an item from a list with front-weighted probability.
    
    Args:
        items (list[Any]): The list of items to pick from.
        none_chance (float): The probability of returning None.
    
    Returns:
        Any: The picked item.
    """
    if random.random() < none_chance:
        return None
    return random.choices(items, weights=[i for i in range(len(items), 0, -1)], k=1)[0]