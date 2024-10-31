from models.customers import Customers
from models.texts import Text


class Campaign:
    def __init__(self, test_mode: bool, name: str, message: str, customers: Customers, media_url: str = None):
        self.test_mode: bool = test_mode
        self.name: str = name
        self.message: str = message
        self.media_url: str = media_url
        self.customers: Customers = customers
        self.texts: list[Text] = []
        self.get_texts()

    def get_texts(self):
        for customer in self.customers:
            if customer.type == 'Business':
                if customer.contact_2:
                    # If there is a contact 2, use that name instead of the customer name
                    name = customer.contact_2
                else:
                    name = customer.name

            if customer.phone_1:
                text = Text(
                    campaign=self.name,
                    contact=1,
                    base_message=self.message,
                    phone=customer.phone_1,
                    cust_no=customer.number,
                    name=customer.name,
                    points=customer.points,
                    category=customer.category,
                    media_url=self.media_url,
                )
                self.texts.append(text)

            # If there is a phone 2, create a text for that as well
            if customer.phone_2:
                if customer.phone_1 == customer.phone_2:
                    continue  # Skip if phone 1 and phone 2 are the same
                if customer.contact_2:
                    # If there is a contact 2, use that name instead of the customer name
                    name = customer.contact_2
                else:
                    name = customer.name
                text = Text(
                    campaign=self.name,
                    contact=2,
                    base_message=self.message,
                    phone=customer.phone_2,
                    cust_no=customer.number,
                    name=name,
                    points=customer.points,
                    category=customer.category,
                    media_url=self.media_url,
                )
                self.texts.append(text)
