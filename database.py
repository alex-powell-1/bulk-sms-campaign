from creds import SQL, Table, Twilio
import pyodbc
from pyodbc import ProgrammingError, Error
import time
from utilities import PhoneNumber
from models.texts import Text
from models.customers import Customers
from error_handler import logger

verbose = True
ORIGIN = 'MASS CAMPAIGN'


class Database:
    SERVER = SQL.SERVER
    DATABASE = SQL.DATABASE
    USERNAME = SQL.USERNAME
    PASSWORD = SQL.PASSWORD

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

    def get_customers(query: str) -> Customers:
        response = Database.query(query)

        if response:
            result = []
            for x in response:
                result.append(
                    {
                        'CUST_NO': x[0],
                        'CUST_NAM_TYP': x[1],
                        'NAM': x[2],
                        'PHONE_1': x[3],
                        'CONTCT_2': x[4],
                        'PHONE_2': x[5],
                        'LOY_PTS_BAL': x[6],
                        'CATEG_COD': x[7],
                    }
                )
            return Customers(result)
        return []

    class SMS:
        @staticmethod
        def get(cust_no=None):
            if cust_no:
                query = f"""
                SELECT * FROM {Table.sms}
                WHERE CUST_NO = '{cust_no}'
                """
            else:
                query = f"""
                SELECT * FROM {Table.sms}
                """
            return Database.query(query)

        @staticmethod
        def insert(customer_text: Text):
            campaign = customer_text.campaign
            from_phone = Twilio.phone_number
            to_phone = customer_text.phone
            cust_no = customer_text.cust_no or Database.Counterpoint.Customer.get_cust_no(to_phone)
            name = customer_text.name or Database.Counterpoint.Customer.get_name(cust_no)
            category = customer_text.category or Database.Counterpoint.Customer.get_category(cust_no)
            body = customer_text.custom_message
            media = customer_text.media_url
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

            if from_phone == PhoneNumber(Twilio.phone_number).to_cp():
                direction = 'OUTBOUND'
            else:
                direction = 'INBOUND'

            query = f"""
                INSERT INTO {Table.sms} (ORIGIN, CAMPAIGN, DIRECTION, TO_PHONE, FROM_PHONE, CUST_NO, NAME, BODY, 
                USERNAME, CATEGORY, MEDIA, SID, ERROR_CODE, ERROR_MESSAGE)
                VALUES ('{ORIGIN}', {f"'{campaign}'" if campaign else 'NULL'}, '{direction}', '{to_phone}', '{from_phone}', 
                {f"'{cust_no}'" if cust_no else 'NULL'}, {f"'{name}'" if name else 'NULL'},'{body}', {f"'{username}'" if username else 'NULL'},
                {f"'{category}'" if category else 'NULL'}, {f"'{media}'" if media else 'NULL'}, {f"'{sid}'" if sid else 'NULL'}, 
                {f"'{error_code}'" if error_code else 'NULL'}, {f"'{error_message}'" if error_message else 'NULL'})
                """
            response = Database.query(query)
            if response['code'] == 200:
                if verbose:
                    if direction == 'OUTBOUND':
                        logger.log(f'SMS sent to {to_phone} added to Database.')
                    else:
                        logger.log(f'SMS received from {from_phone} added to Database.')
            else:
                error = f'Error adding SMS sent to {to_phone} to Middleware. \nQuery: {query}\nResponse: {response}'
                logger.error(msg=error)

        @staticmethod
        def move_phone_to_landline(customer_text: Text):
            cp_phone = PhoneNumber(customer_text.phone).to_cp()

            move_landline_query = f"""
                UPDATE AR_CUST
                SET MBL_PHONE_{customer_text.contact} = '{cp_phone}', PHONE_{customer_text.contact} = NULL
                WHERE PHONE_{customer_text.contact} = '{cp_phone}'
            """
            response = Database.query(move_landline_query)

            if response['code'] == 200:
                query = f"""
                INSERT INTO {Table.sms_event} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
                VALUES ('{ORIGIN}', '{customer_text.campaign}', '{customer_text.phone}', '{customer_text.cust_no}', '{customer_text.name}', '{customer_text.category}', 
                'Landline', 'SET MBL_PHONE_{customer_text.contact} = {cp_phone}, SET PHONE_{customer_text.contact} = NULL')"""

                response = Database.query(query)
                if response['code'] != 200:
                    logger.error(f'Error logging landline event for {customer_text.phone}. Response: {response}')
            elif response['code'] == 201:
                """No rows affected"""
                logger.error(f'Error moving {customer_text.phone} to landline. Response: {response}')

            else:
                logger.error(f'Error moving {customer_text.phone} to landline. Response: {response}')

        @staticmethod
        def unsubscribe(customer_text: Text):
            phone = PhoneNumber(customer_text.phone).to_cp()
            query = f"""
            UPDATE AR_CUST
            SET SMS_{customer_text.contact}_IS_SUB = 'N'
            WHERE PHONE_{customer_text.contact} = '{phone}'
            """
            response = Database.query(query)
            if response['code'] == 200:
                query = f"""
                INSERT INTO {Table.sms_event} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
                VALUES ('{ORIGIN}', '{customer_text.campaign}', '{customer_text.phone}', '{customer_text.cust_no}', '{customer_text.name}', '{customer_text.category}', 
                'Unsubscribe', 'SET SMS_{customer_text.contact}_IS_SUB = N')"""

                response = Database.query(query)
                if response['code'] != 200:
                    logger.error(f'Error logging unsubscribe event for {customer_text.phone}. Response: {response}')
            elif response['code'] == 201:
                """No rows affected"""
                logger.error(f'Error unsubscribing {customer_text.phone}. Response: {response}')
            else:
                logger.error(f'Error unsubscribing {customer_text.phone}. Response: {response}')

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
