import creds
import pyodbc
from pyodbc import ProgrammingError, Error
import time
from utilities import PhoneNumber
from error_handler import SMSErrorHandler


class Database:
    SERVER = creds.SERVER
    DATABASE = creds.DATABASE
    USERNAME = creds.USERNAME
    PASSWORD = creds.PASSWORD

    @staticmethod
    def query(query):
        """Runs Query Against SQL Database. Use Commit Kwarg for updating database"""
        connection = pyodbc.connect(
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={Database.SERVER};PORT=1433;DATABASE={Database.DATABASE};"
            f"UID={Database.USERNAME};PWD={Database.PASSWORD};TrustServerCertificate=yes;timeout=3;ansi=True;",
            autocommit=True,
        )

        connection.setdecoding(pyodbc.SQL_CHAR, encoding="utf-16-le")
        connection.setencoding("utf-16-le")

        cursor = connection.cursor()
        query = str(query).strip()
        try:
            response = cursor.execute(query)
            sql_data = response.fetchall()
        except ProgrammingError as e:
            if e.args[0] == "No results.  Previous SQL was not a query.":
                if cursor.rowcount > 0:
                    sql_data = {
                        "code": 200,
                        "affected rows": cursor.rowcount,
                        "message": "success",
                    }
                else:
                    # No rows affected
                    sql_data = {
                        "code": 201,
                        "affected rows": cursor.rowcount,
                        "message": "No rows affected",
                        "query": query,
                    }
            else:
                if len(e.args) > 1:
                    sql_data = {
                        "code": f"{e.args[0]}",
                        "message": f"{e.args[1]}",
                        "query": query,
                    }
                else:
                    sql_data = {
                        "code": f"{e.args[0]}",
                        "query": query,
                        "message": "Unknown Error",
                    }

        except Error as e:
            if e.args[0] == "40001":
                print("Deadlock Detected. Retrying Query")
                time.sleep(1)
                Database.query(query)
            else:
                sql_data = {
                    "code": f"{e.args[0]}",
                    "message": f"{e.args[1]}",
                    "query": query,
                }

        cursor.close()
        connection.close()
        return sql_data if sql_data else None

    class SMS:
        ORIGIN = creds.origin

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
        def insert(customer):
            campaign = customer.campaign
            from_phone = creds.TWILIO_PHONE_NUMBER
            to_phone = customer.phone
            cust_no = customer.cust_no
            name = customer.name
            category = customer.category
            body = customer.message
            media = customer.media
            sid = customer.sid
            error_code = customer.response_code
            error_message = customer.response_text

            username = "Mass Campaign"

            if body:
                body = body.replace("'", "''")
                body = body[:1000]  # Truncate body to 1000 characters

            if name is not None:
                name = name.replace("'", "''")

            to_phone = PhoneNumber(to_phone).to_cp()
            from_phone = PhoneNumber(from_phone).to_cp()

            if from_phone == PhoneNumber(creds.TWILIO_PHONE_NUMBER).to_cp():
                direction = "OUTBOUND"
            else:
                direction = "INBOUND"

            query = f"""
                INSERT INTO {creds.sms_table} (ORIGIN, CAMPAIGN, DIRECTION, TO_PHONE, FROM_PHONE, CUST_NO, NAME, BODY, 
                USERNAME, CATEGORY, MEDIA, SID, ERROR_CODE, ERROR_MESSAGE)
                VALUES ('{Database.SMS.ORIGIN}', {f"'{campaign}'" if campaign else 'NULL'}, '{direction}', '{to_phone}', '{from_phone}', 
                {f"'{cust_no}'" if cust_no else 'NULL'}, {f"'{name}'" if name else 'NULL'},'{body}', {f"'{username}'" if username else 'NULL'},
                {f"'{category}'" if category else 'NULL'}, {f"'{media}'" if media else 'NULL'}, {f"'{sid}'" if sid else 'NULL'}, 
                {f"'{error_code}'" if error_code else 'NULL'}, {f"'{error_message}'" if error_message else 'NULL'})
                """
            response = Database.query(query)
            if response["code"] == 200:
                if direction == "OUTBOUND":
                    SMSErrorHandler.logger.success(
                        f"SMS sent to {to_phone} added to Database."
                    )
                else:
                    SMSErrorHandler.logger.success(
                        f"SMS received from {from_phone} added to Database."
                    )
            else:
                error = f"Error adding SMS sent to {to_phone} to Middleware. \nQuery: {query}\nResponse: {response}"
                Database.error_handler.add_error_v(error=error, origin="insert_sms")

        @staticmethod
        def move_phone_1_to_landline(customer):
            cp_phone = PhoneNumber(customer.phone).to_cp()
            move_landline_query = f"""
                UPDATE AR_CUST
                SET MBL_PHONE_1 = '{cp_phone}', SET PHONE_1 = NULL
                WHERE PHONE_1 = '{cp_phone}'
            """
            response = Database.query(move_landline_query)

            if response["code"] == 200:
                query = f"""
                INSERT INTO {creds.sms_event_log} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
                VALUES ('{Database.SMS.ORIGIN}', '{customer.campaign}', '{customer.phone}', '{customer.cust_no}', '{customer.name}', '{customer.category}', 
                'Landline', 'SET MBL_PHONE_1 = {cp_phone}, SET PHONE_1 = NULL')"""

                response = Database.query(query)
                if response["code"] != 200:
                    Database.error_handler.add_error_v(
                        f"Error moving {customer.phone} to landline"
                    )

            else:
                Database.error_handler.add_error_v(
                    f"Error moving {customer.phone} to landline"
                )

        @staticmethod
        def subscribe(customer):
            phone = PhoneNumber(customer.phone).to_cp()
            query = f"""
            UPDATE AR_CUST
            SET {creds.sms_subscribe_status} = 'Y'
            WHERE PHONE_1 = '{phone}' OR PHONE_2 = '{phone}'
            """
            response = Database.query(query=query)
            if response["code"] == 200:
                query = f"""
                INSERT INTO {creds.sms_table} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
                VALUES ('{Database.SMS.ORIGIN}', '{customer.campaign}', '{phone}', '{customer.cust_no}', '{customer.name}', '{customer.category}',
                'Subscribe', 'SET {creds.sms_subscribe_status} = Y')"""
                response = Database.query(query)
                if response["code"] != 200:
                    Database.error_handler.add_error_v(
                        f"Error subscribing {phone} to SMS"
                    )
            else:
                Database.error_handler.add_error_v(f"Error subscribing {phone} to SMS")

        @staticmethod
        def unsubscribe(customer):
            phone = PhoneNumber(customer.phone).to_cp()
            query = f"""
            UPDATE AR_CUST
            SET {creds.sms_subscribe_status} = 'N'
            WHERE PHONE_1 = '{phone}' OR PHONE_2 = '{phone}'
            """
            response = Database.query(query=query)
            if response["code"] == 200:
                query = f"""
                INSERT INTO {creds.sms_table} (ORIGIN, CAMPAIGN, PHONE, CUST_NO, NAME, CATEGORY, EVENT_TYPE, MESSAGE)
                VALUES ('{Database.SMS.ORIGIN}', '{customer.campaign}', '{phone}', '{customer.cust_no}', '{customer.name}', '{customer.category}',
                'Unsubscribe', 'SET {creds.sms_subscribe_status} = N')"""
                response = Database.query(query)
                if response["code"] != 200:
                    Database.error_handler.add_error_v(
                        f"Error unsubscribing {phone} from SMS"
                    )
            else:
                Database.error_handler.add_error_v(
                    f"Error unsubscribing {phone} from SMS"
                )

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


if __name__ == "__main__":
    pass
