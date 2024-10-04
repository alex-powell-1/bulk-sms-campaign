import creds
import pyodbc
from pyodbc import ProgrammingError, Error
import time
from utilities import PhoneNumber
from error_handler import SMSErrorHandler

verbose = False


class Database:
    SERVER = creds.SERVER
    DATABASE = creds.DATABASE
    USERNAME = creds.USERNAME
    PASSWORD = creds.PASSWORD

    @staticmethod
    def query(query):
        """Runs Query Against SQL Database. Use Commit Kwarg for updating database"""
        connection = pyodbc.connect(
            f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={Database.SERVER};PORT=1433;DATABASE={Database.DATABASE};'
            f'UID={Database.USERNAME};PWD={Database.PASSWORD};TrustServerCertificate=yes;timeout=3;ansi=True;',
            autocommit=True,
        )

        connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-16-le')
        connection.setencoding('utf-16-le')

        cursor = connection.cursor()
        query = str(query).strip()
        try:
            response = cursor.execute(query)
            sql_data = response.fetchall()
        except ProgrammingError as e:
            if e.args[0] == 'No results.  Previous SQL was not a query.':
                if cursor.rowcount > 0:
                    sql_data = {'code': 200, 'affected rows': cursor.rowcount, 'message': 'success'}
                else:
                    # No rows affected
                    sql_data = {
                        'code': 201,
                        'affected rows': cursor.rowcount,
                        'message': 'No rows affected',
                        'query': query,
                    }
            else:
                if len(e.args) > 1:
                    sql_data = {'code': f'{e.args[0]}', 'message': f'{e.args[1]}', 'query': query}
                else:
                    sql_data = {'code': f'{e.args[0]}', 'query': query, 'message': 'Unknown Error'}

        except Error as e:
            if e.args[0] == '40001':
                print('Deadlock Detected. Retrying Query')
                time.sleep(1)
                Database.query(query)
            else:
                sql_data = {'code': f'{e.args[0]}', 'message': f'{e.args[1]}', 'query': query}

        cursor.close()
        connection.close()
        return sql_data if sql_data else None

    class SMS:
        ORIGIN = creds.origin

        class CustomerText:
            def __init__(self, phone, cust_no=None, name=None, points=None, category=None):
                self.phone = phone
                self.cust_no = cust_no or Database.Counterpoint.Customer.get_cust_no(self.phone)
                self.name = name or Database.Counterpoint.Customer.get_name(self.cust_no)
                self.first_name = self.name.split(' ')[0] or None
                self.points = points or Database.Counterpoint.Customer.get_loyalty_balance(self.cust_no)
                self.category = category or Database.Counterpoint.Customer.get_category(self.cust_no)
                self.message = None
                self.media = None
                self.sid = None
                self.response_code = None
                self.response_text: str = None
                self.count = None
                self.campaign = None

            def __str__(self):
                return f'Customer {self.cust_no}: {self.name} - {self.phone}'

        @staticmethod
        def get(cust_no=None):
            if cust_no:
                query = f"""
                SELECT * FROM {creds.sms_table}
                WHERE CUST_NO = '{cust_no}'
                """
            else:
                query = f"""
                SELECT * FROM {creds.sms_table}
                """
            return Database.query(query)

        @staticmethod
        def insert(customer_text: CustomerText):
            campaign = customer_text.campaign
            from_phone = creds.TWILIO_PHONE_NUMBER
            to_phone = customer_text.phone
            cust_no = customer_text.cust_no
            name = customer_text.name
            category = customer_text.category
            body = customer_text.message
            media = customer_text.media
            sid = customer_text.sid
            error_code = customer_text.response_code
            error_message = customer_text.response_text

            username = 'Mass Campaign'

            if name:
                name = name.replace("'", "''")
                name = name[:80]  # Truncate name to 80 characters

            if body:
                body = body.replace("'", "''")
                body = body[:1000]  # Truncate body to 1000 characters

            if error_message:
                error_message = str(error_message)
                error_message = error_message.replace("'", "''")
                error_message = error_message[:255]

            if media:
                media = media[:500]  # Truncate media to 500 characters

            if name is not None:
                name = name.replace("'", "''")

            to_phone = PhoneNumber(to_phone).to_cp()
            from_phone = PhoneNumber(from_phone).to_cp()

            if from_phone == PhoneNumber(creds.TWILIO_PHONE_NUMBER).to_cp():
                direction = 'OUTBOUND'
            else:
                direction = 'INBOUND'

            query = f"""
                INSERT INTO {creds.sms_table} (ORIGIN, CAMPAIGN, DIRECTION, TO_PHONE, FROM_PHONE, CUST_NO, NAME, BODY, 
                USERNAME, CATEGORY, MEDIA, SID, ERROR_CODE, ERROR_MESSAGE)
                VALUES ('{Database.SMS.ORIGIN}', {f"'{campaign}'" if campaign else 'NULL'}, '{direction}', '{to_phone}', '{from_phone}', 
                {f"'{cust_no}'" if cust_no else 'NULL'}, {f"'{name}'" if name else 'NULL'},'{body}', {f"'{username}'" if username else 'NULL'},
                {f"'{category}'" if category else 'NULL'}, {f"'{media}'" if media else 'NULL'}, {f"'{sid}'" if sid else 'NULL'}, 
                {f"'{error_code}'" if error_code else 'NULL'}, {f"'{error_message}'" if error_message else 'NULL'})
                """
            response = Database.query(query)
            if response['code'] == 200:
                if verbose:
                    if direction == 'OUTBOUND':
                        SMSErrorHandler.logger.success(f'SMS sent to {to_phone} added to Database.')
                    else:
                        SMSErrorHandler.logger.success(f'SMS received from {from_phone} added to Database.')
            else:
                error = f'Error adding SMS sent to {to_phone} to Middleware. \nQuery: {query}\nResponse: {response}'
                SMSErrorHandler.error_handler.add_error_v(error=error, origin='insert_sms')

        @staticmethod
        def move_phone_1_to_landline(customer_text: CustomerText):
            cp_phone = PhoneNumber(customer_text.phone).to_cp()
            move_landline_query = f"""
                UPDATE AR_CUST
                SET MBL_PHONE_1 = '{cp_phone}', PHONE_1 = NULL
                WHERE PHONE_1 = '{cp_phone}'
            """
            response = Database.query(move_landline_query)

            if response['code'] == 200:
                query = f"""
                INSERT INTO {creds.sms_activity_table} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
                VALUES ('{Database.SMS.ORIGIN}', '{customer_text.campaign}', '{customer_text.phone}', '{customer_text.cust_no}', '{customer_text.name}', '{customer_text.category}', 
                'Landline', 'SET MBL_PHONE_1 = {cp_phone}, SET PHONE_1 = NULL')"""

                response = Database.query(query)
                if response['code'] != 200:
                    SMSErrorHandler.error_handler.add_error_v(
                        error=f'Error inserting move_phone_1_to_landline event for {customer_text.phone}. Response: {response}',
                        origin='move_phone_1_to_landline',
                    )
            elif response['code'] == 201:
                """No rows affected"""
                SMSErrorHandler.error_handler.add_error_v(
                    error=f'No target phone found for {customer_text.phone}', origin='move_phone_1_to_landline'
                )
            else:
                SMSErrorHandler.error_handler.add_error_v(
                    error=f'Error moving {customer_text.phone} to landline. Response: {response}',
                    origin='move_phone_1_to_landline',
                )

        def log_sms_activity(
            origin: str,
            campaign: str,
            phone: str,
            cust_no: str,
            name: str,
            category: str,
            event_type: str,
            message: str,
        ):
            query = f"""
            INSERT INTO {creds.sms_activity_table} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
            VALUES ('{origin}', '{campaign}', '{phone}', '{cust_no}', '{name}', '{category}', '{event_type}', '{message}')"""
            response = Database.query(query)
            if response['code'] != 200:
                SMSErrorHandler.error_handler.add_error_v(
                    f'Error inserting {event_type} event for {phone}. Response: {response}'
                )

        @staticmethod
        def subscribe(customer_text: CustomerText):
            phone = PhoneNumber(customer_text.phone).to_cp()

            query1 = f"""
            UPDATE AR_CUST
            SET SMS_1_IS_SUB = 'Y'
            WHERE PHONE_1 = '{phone}'
            """

            query2 = f"""
            UPDATE AR_CUST
            SET SMS_2_IS_SUB = 'Y'
            WHERE PHONE_2 = '{phone}'
            """

            try:
                responses = [Database.query(query1), Database.query(query2)]
                no_rows = 0
                errors = 0

                for responseIndex, response in enumerate(responses):
                    if response['code'] == 200:
                        column_str = 'SMS_1_IS_SUB' if responseIndex == 0 else 'SMS_2_IS_SUB'

                        log_sms_activity(
                            Database.SMS.ORIGIN,
                            customer_text.campaign,
                            phone,
                            customer_text.cust_no,
                            customer_text.name,
                            customer_text.category,
                            'Subscribe',
                            f'SET {column_str} = Y',
                        )
                    elif response['code'] == 201:
                        no_rows += 1
                    else:
                        errors += 1

                if no_rows > 1:
                    SMSErrorHandler.error_handler.add_error_v(
                        error=f'Error subscribing {phone}. Response: {responses}', origin='subscribe_sms'
                    )

                if errors > 1:
                    SMSErrorHandler.error_handler.add_error_v(
                        error=f'Error subscribing {phone}. Response: {responses}', origin='subscribe_sms'
                    )

            except Exception as err:
                SMSErrorHandler.error_handler.add_error_v(
                    error=f'Error subscribing {phone}. Response: {err}', origin='subscribe_sms'
                )

        @staticmethod
        def unsubscribe(customer_text: CustomerText):
            phone = PhoneNumber(customer_text.phone).to_cp()

            query1 = f"""
            UPDATE AR_CUST
            SET SMS_1_IS_SUB = 'N'
            WHERE PHONE_1 = '{phone}'
            """

            query2 = f"""
            UPDATE AR_CUST
            SET SMS_2_IS_SUB = 'N'
            WHERE PHONE_2 = '{phone}'
            """

            try:
                responses = [Database.query(query1), Database.query(query2)]
                no_rows = 0
                errors = 0

                for responseIndex, response in enumerate(responses):
                    if response['code'] == 200:
                        column_str = 'SMS_1_IS_SUB' if responseIndex == 0 else 'SMS_2_IS_SUB'

                        log_sms_activity(
                            Database.SMS.ORIGIN,
                            customer_text.campaign,
                            phone,
                            customer_text.cust_no,
                            customer_text.name,
                            customer_text.category,
                            'Unsubscribe',
                            f'SET {column_str} = N',
                        )
                    elif response['code'] == 201:
                        no_rows += 1
                    else:
                        errors += 1

                if no_rows > 1:
                    SMSErrorHandler.error_handler.add_error_v(
                        error=f'Error unsubscribing {phone}. Response: {responses}', origin='unsubscribe_sms'
                    )

                if errors > 1:
                    SMSErrorHandler.error_handler.add_error_v(
                        error=f'Error unsubscribing {phone}. Response: {responses}', origin='unsubscribe_sms'
                    )

            except Exception as err:
                SMSErrorHandler.error_handler.add_error_v(
                    error=f'Error unsubscribing {phone}. Response: {err}', origin='unsubscribe_sms'
                )

            # query = f"""
            # UPDATE AR_CUST
            # SET {creds.sms_subscribe_status} = 'N'
            # WHERE PHONE_1 = '{phone}' OR PHONE_2 = '{phone}'
            # """
            # response = Database.query(query=query)
            # if response['code'] == 200:
            #     query = f"""
            #     INSERT INTO {creds.sms_activity_table} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
            #     VALUES ('{Database.SMS.ORIGIN}', '{customer_text.campaign}', '{phone}', '{customer_text.cust_no}', '{customer_text.name}', '{customer_text.category}',
            #     'Unsubscribe', 'SET {creds.sms_subscribe_status} = N')"""
            #     response = Database.query(query)
            #     if response['code'] != 200:
            #         SMSErrorHandler.error_handler.add_error_v(
            #             f'Error inserting unsubscribe event for {phone}. Response: {response}'
            #         )
            # elif response['code'] == 201:
            #     """No rows affected"""
            #     SMSErrorHandler.error_handler.add_error_v(
            #         error=f'No target phone found for {phone}', origin='unsubscribe_sms'
            #     )
            # else:
            #     SMSErrorHandler.error_handler.add_error_v(
            #         error=f'Error unsubscribing {phone} from SMS. Response: {response}', origin='unsubscribe_sms'
            #     )

    class Counterpoint:
        class Customer:
            def get_cust_no(phone_no):
                phone = PhoneNumber(phone_no).to_cp()
                query = f"""
                SELECT CUST_NO FROM AR_CUST
                WHERE PHONE_1 = '{phone}' OR PHONE_2 = '{phone}'
                """
                response = Database.query(query)
                if response:
                    return response[0][0]
                else:
                    return None

            def get_category(cust_no):
                query = f"""
                SELECT CATEG_COD FROM AR_CUST
                WHERE CUST_NO = '{cust_no}'
                """
                response = Database.query(query)
                if response:
                    return response[0][0]
                else:
                    return None

            def get_loyalty_balance(cust_no):
                query = f"""
                SELECT LOY_PTS_BAL FROM AR_CUST
                WHERE CUST_NO = '{cust_no}'
                """
                response = Database.query(query)
                if response:
                    return response[0][0]
                else:
                    return None

            def get_name(cust_no):
                query = f"""
                SELECT NAM FROM AR_CUST
                WHERE CUST_NO = '{cust_no}'
                """
                response = Database.query(query)
                if response:
                    return response[0][0]
                else:
                    return None


if __name__ == '__main__':
    pass
