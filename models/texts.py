class Text:
    def __init__(
        self,
        campaign: str,
        contact: int,
        base_message: str,
        phone: str,
        cust_no: str,
        name: str,
        points: int,
        category: str,
        media_url: str = None,  # Add media_url as an optional parameter
    ):
        self.campaign: str = campaign
        self.contact: int = contact  # Contact 1 or Contact 2
        """1 or 2, depending on which phone number is being used."""
        self.base_message: str = base_message
        self.phone: str = phone
        self.cust_no: str = cust_no
        self.name: str = name
        self.points: int = points
        self.category: str = category
        self.custom_message: str = None
        self.media_url: str = media_url
        self.sid: str = None
        self.response_code: str = None
        self.response_text: str = None
        self.count: int = None
        self.get_custom_message()

    def __str__(self):
        result = f'Campaign: {self.campaign}\n'
        result += f'Contact: {self.contact}\n'
        result += f'Phone: {self.phone}\n'
        result += f'Customer Number: {self.cust_no}\n'
        result += f'Name: {self.name}\n'
        result += f'Points: {self.points}\n'
        result += f'Category: {self.category}\n'
        result += f'Message: {self.custom_message}\n'
        return result

    def get_custom_message(self):
        self.custom_message = self.base_message

        # If the customer has points, add them to the message
        if '{rewards}' in self.base_message:
            self.custom_message = self.base_message.replace('{rewards}', f'${self.points if self.points else 0}')

        # If the customer has a name, add it to the message
        if '{name}' in self.custom_message:
            if self.name:
                first_name = self.name.split(' ')[0].title()
                self.custom_message = self.custom_message.replace('{name}', first_name)
            else:
                self.custom_message = self.custom_message.replace('{name}', 'customer')
