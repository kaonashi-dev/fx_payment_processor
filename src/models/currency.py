from enum import Enum

class Currency(str, Enum):
    USD = "USD"
    MXN = "MXN"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        try:
            cls(value.upper())
            return True
        except ValueError:
            return False

    @classmethod
    def get_all(cls) -> list[str]:
        return [currency.value for currency in cls]
