def contains_duplicate(numbers: list[int]) -> bool:
    for index, number in enumerate(numbers):
        if number in numbers[index + 1:]:
            return True

    return False