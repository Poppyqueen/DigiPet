import random

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