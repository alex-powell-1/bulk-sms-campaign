import creds
from query_engine import QueryEngine
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

db = QueryEngine()


class SMSEngine:
    def __init__(self):
        self.phone = creds.twilio_phone_number
        self.sid = creds.twilio_account_sid
        self.token = creds.twilio_auth_token

    def send_text(
        self,
        cust_no,
        to_phone,
        message,
        log_location,
        url=None,
        create_log=True,
        test_mode=False,
    ):
        twilio_response = ""

        if test_mode:
            print(f"Sending test sms text to {cust_no}: {message}")
            twilio_response = "Test Mode"

        if not test_mode:
            # for SMS Messages
            client = Client(self.sid, self.token)

            try:
                # MMS
                if url is not None:
                    twilio_message = client.messages.create(
                        from_=self.phone, to=to_phone, media_url=url, body=message
                    )

                # SMS
                else:
                    twilio_message = client.messages.create(
                        from_=self.phone, to=to_phone, body=message
                    )

            except TwilioRestException as err:
                if err.code in [21614, 30003, 30005, 30006]:
                    move_phone_1_to_landline(cust_no, to_phone)
                    twilio_response = err.msg

            else:
                twilio_response = twilio_message.sid
                print(twilio_message.to, twilio_message.body)

        if create_log:
            create_sms_log(cust_no, to_phone, message, twilio_response, log_location)


def move_phone_1_to_landline(cust_no, phone_number):
    cp_phone = format_phone(phone_number, mode="counterpoint")
    move_landline_query = f"""
        UPDATE AR_CUST
        SET MBL_PHONE_1 = '{cp_phone}'
        WHERE PHONE_1 = '{cp_phone}'

        UPDATE AR_CUST
        SET PHONE_1 = NULL
        WHERE MBL_PHONE_1 = '{cp_phone}'
    """
    db.query_db(move_landline_query, commit=True)


def format_phone(phone_number, mode="clickable", prefix=False):
    """Cleanses input data and returns masked phone for either Twilio or Counterpoint configuration"""
    if phone_number != "":
        phone_number_as_string = str(phone_number)
        # Strip away extra symbols
        formatted_phone = phone_number_as_string.replace(" ", "")  # Remove Spaces
        formatted_phone = formatted_phone.replace("-", "")  # Remove Hyphens
        formatted_phone = formatted_phone.replace("(", "")  # Remove Open Parenthesis
        formatted_phone = formatted_phone.replace(")", "")  # Remove Close Parenthesis
        formatted_phone = formatted_phone.replace("+1", "")  # Remove +1
        formatted_phone = formatted_phone[-10:]  # Get last 10 characters
        if mode == "counterpoint":
            # Masking ###-###-####
            cp_phone = (
                formatted_phone[0:3]
                + "-"
                + formatted_phone[3:6]
                + "-"
                + formatted_phone[6:10]
            )
            return cp_phone

        elif mode == "clickable":
            # Masking ###-###-####
            clickable_phone = (
                "("
                + formatted_phone[0:3]
                + ") "
                + formatted_phone[3:6]
                + "-"
                + formatted_phone[6:10]
            )
            return clickable_phone
        else:
            if prefix:
                formatted_phone = "+1" + formatted_phone
            return formatted_phone
    else:
        return None