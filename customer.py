from database import Database


class CustomerText:
    def __init__(self, data):
        self.phone = data["PHONE_1"]
        if "CUST_NO" in data:
            self.cust_no = data["CUST_NO"]
        else:
            self.cust_no = Database.Counterpoint.Customer.get_cust_no(self.phone)

        if "NAM" in data:
            self.name = data["NAM"]
        else:
            self.name = Database.Counterpoint.Customer.get_name(self.cust_no)

        if "LOY_PTS_BAL" in data:
            self.points = data["LOY_PTS_BAL"]
        else:
            self.points = Database.Counterpoint.Customer.get_loyalty_balance(
                self.cust_no
            )
        if "CATEG_COD" in data:
            self.category = data["CATEG_COD"]
        else:
            self.category = Database.Counterpoint.Customer.get_category(self.cust_no)

        self.message = None
        self.media = None
        self.sid = None
        self.response_code = None
        self.response_text = None
        self.count = None
        self.campaign = None

    def __str__(self):
        return f"Customer {self.cust_no}: {self.name} - {self.phone}"
