import re


class PhoneNumber:
    def __init__(self, phone_number: str):
        self.raw = phone_number
        if not PhoneNumber.is_valid(self.raw):
            raise ValueError(f"Invalid phone number format. Input: {self.raw}")
        self.stripped = PhoneNumber.strip_number(self.raw)
        self.area_code = self.stripped[0:3]
        self.exchange = self.stripped[3:6]
        self.subscriber_number = self.stripped[6:]

    @staticmethod
    def is_valid(phone_number) -> bool:
        """Validates a phone number using regex."""
        pattern = r"(\+\d{1,3})?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        if re.match(pattern, phone_number):
            return True

    @staticmethod
    def strip_number(phone_number: str):
        return (
            phone_number.replace("+1", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "")
            .replace("_", "")
        )

    def to_cp(self):
        return f"{self.area_code}-{self.exchange}-{self.subscriber_number}"

    def to_twilio(self):
        return f"+1{self.area_code}{self.exchange}{self.subscriber_number}"

    def __str__(self):
        return f"({self.area_code}) {self.exchange}-{self.subscriber_number}"
