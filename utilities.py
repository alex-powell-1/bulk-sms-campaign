import re
import creds
from database import Database
from error_handler import SMSErrorHandler


class PhoneNumber:
    def __init__(self, phone_number: str):
        self.raw = phone_number

        if PhoneNumber.is_valid(self.raw):
            self.stripped = PhoneNumber.strip_number(self.raw)
            self.area_code = self.stripped[0:3]
            self.exchange = self.stripped[3:6]
            self.subscriber_number = self.stripped[6:]
        else:
            self.area_code = None
            self.exchange = None
            self.subscriber_number = None

    @staticmethod
    def is_valid(phone_number) -> bool:
        """Validates a phone number using regex."""
        pattern = r'(\+\d{1,3})?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        if re.match(pattern, phone_number):
            return True

    @staticmethod
    def strip_number(phone_number: str):
        return (
            phone_number.replace('+1', '')
            .replace('-', '')
            .replace('(', '')
            .replace(')', '')
            .replace(' ', '')
            .replace('_', '')
        )

    def to_cp(self):
        return f'{self.area_code}-{self.exchange}-{self.subscriber_number}'

    def to_twilio(self):
        if self.area_code and self.exchange and self.subscriber_number:
            return f'+1{self.area_code}{self.exchange}{self.subscriber_number}'
        else:
            return None

    def __str__(self):
        return f'({self.area_code}) {self.exchange}-{self.subscriber_number}'


def log_sms_activity(
    origin: str, campaign: str, phone: str, cust_no: str, name: str, category: str, event_type: str, message: str
):
    query = f"""
    INSERT INTO {creds.sms_activity_table} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
    VALUES ('{origin}', '{campaign}', '{phone}', '{cust_no}', '{name}', '{category}', '{event_type}', '{message}')"""
    response = Database.query(query)
    if response['code'] != 200:
        SMSErrorHandler.error_handler.add_error_v(
            f'Error inserting {event_type} event for {phone}. Response: {response}'
        )
