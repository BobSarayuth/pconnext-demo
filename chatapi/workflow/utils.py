import time


class Timer:
    def __init__(self) -> None:
        self._start: float = time.time()

    def __float__(self) -> float:
        return round(self.elapsed, 2)

    def stop(self) -> None:
        self.elapsed = time.time() - self._start


def conv_str_bytes(size_str: str) -> int:
    size_str = size_str.strip().upper()
    unit = "".join(filter(str.isalpha, size_str))
    value = int("".join(filter(str.isdigit, size_str)))

    if unit == "MB":
        return value * 1024 * 1024
    elif unit == "KB":
        return value * 1024
    elif unit == "B":
        return value
    else:
        raise ValueError("Invalid unit")


# def get_prompt(file_name: str):
#     try:
#         with open(f"./workflow/invokes/prompts/{file_name}", "r", encoding="utf-8") as file:
#             return file.read().strip()
#     except FileNotFoundError as ex:
#         raise Exception(ex)
