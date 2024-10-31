from utilities import PhoneNumber


class Customer:
    def __init__(
        self,
        CUST_NO: str,
        CUST_NAM_TYP: str,
        NAM: str,
        PHONE_1: str,
        CONTCT_2: str,
        PHONE_2: str,
        LOY_PTS_BAL: int,
        CATEG_COD: str,
    ):
        self.number: str = CUST_NO
        self.type: str = 'Business' if CUST_NAM_TYP == 'B' else 'Person'
        self.name: str = NAM
        self.phone_1: str = PhoneNumber(PHONE_1).to_twilio()
        self.contact_2: str = CONTCT_2
        self.phone_2: str = PhoneNumber(PHONE_2).to_twilio()
        self.points: int = LOY_PTS_BAL
        self.category: str = CATEG_COD
        self.total_messages: int = self.get_total_messages()

    def __str__(self):
        result = f'Name: {self.name}\n'
        result += f'Type: {self.type}\n'
        result += f'Phone 1: {self.phone_1}\n'
        result += f'Contact 2: {self.contact_2}\n'
        result += f'Phone 2: {self.phone_2}\n'
        result += f'Points: {self.points}\n'
        result += f'Category: {self.category}\n'
        result += f'Total Messages: {self.total_messages}\n'
        return result

    def get_total_messages(self):
        result = 0
        if self.phone_1:
            result += 1
        if self.phone_2:
            result += 1
        return result


class Customers:
    def __init__(self, sql_data: list[dict]):
        self.list: list[Customer] = [Customer(**customer) for customer in sql_data]
        self.total_messages: int = self.get_total_messages()

    def __str__(self):
        result = ''
        for customer in self.list:
            result += str(customer) + '\n\n'
        result += f'Total Messages: {self.total_messages}\n'
        return result

    def get_total_messages(self):
        result = 0
        for customer in self.list:
            result += customer.total_messages
        return result

    def __iter__(self):
        return iter(self.list)
