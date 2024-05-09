import csv
import sys

import pandas
import pyodbc
import twilio.base.exceptions
from pyodbc import OperationalError
from twilio.rest import Client

import creds
import custom
from creds import SERVER, DATABASE, USERNAME, PASSWORD, account_sid, auth_token


#   ___ __  __ ___    ___   _   __  __ ___  _   ___ ___ _  _ ___
#  / __|  \/  / __|  / __| /_\ |  \/  | _ \/_\ |_ _/ __| \| / __|
#  \__ | |\/| \__ \ | (__ / _ \| |\/| |  _/ _ \ | | (_ | .` \__ \
#  |___|_|  |_|___/  \___/_/ \_|_|  |_|_|/_/ \_|___\___|_|\_|___/
#
# Author: Alex Powell
# Script version for running from .bat file on schedule


csv_data_dict = {}


def read_csv(path):
    """File Selector for importing CSVs"""
    # Read file
    csv_data = pandas.read_csv(path)
    global csv_data_dict
    csv_data_dict = csv_data.to_dict('records')
    # Format phone number
    for customer in csv_data_dict:
        customer_phone_from_csv = customer["PHONE_1"]
        try:
            customer["PHONE_1"] = format_phone(customer_phone_from_csv, prefix=True)
        except Exception as err:
            print(err)
            customer["PHONE_1"] = "error"
            continue

    return csv_data_dict


# ---------------------------- SQL DB------------------------------ #
def query_db(sql_query):
    try:
        connection = pyodbc.connect(
            f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};PORT=1433;DATABASE={DATABASE};'
            f'UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;timeout=3')
        cursor = connection.cursor()
        response = cursor.execute(sql_query).fetchall()
        cp_data = []
        start_code = "+1"
        for x in response:
            cp_data.append({
                "CUST_NO": x[0],
                "FST_NAM": x[1],
                "PHONE_1": start_code + x[2].replace("-", ""),
                "LOY_PTS_BAL": x[3]
            })
        # Close Connection
        cursor.close()
        connection.close()
        # Remove Duplicates
        cp_data = [i for n, i in enumerate(cp_data) if i not in cp_data[:n]]
        return cp_data

    except OperationalError:
        print("Cannot connect to server. Check VPN settings.")


def move_phone_1_to_mbl_phone_1(phone_number):
    cp_phone = format_phone(phone_number, mode="Counterpoint")
    move_landline_query = f"""
        UPDATE AR_CUST
        SET MBL_PHONE_1 = '{cp_phone}'
        WHERE PHONE_1 = '{cp_phone}'

        UPDATE AR_CUST
        SET PHONE_1 = NULL
        WHERE MBL_PHONE_1 = '{cp_phone}'
    """
    connection = pyodbc.connect(
        f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};PORT=1433;DATABASE={DATABASE};'
        f'UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;timeout=3')

    cursor = connection.cursor()
    cursor.execute(move_landline_query)
    connection.commit()
    cursor.close()


def unsubscribe_customer_from_sms(customer):
    customer_number = customer['CUST_NO']
    unsubscribe_sms_query = f"""
            UPDATE AR_CUST
            SET INCLUDE_IN_MARKETING_MAILOUTS = 'N'
            WHERE CUST_NO = '{customer_number}'
        """

    connection = pyodbc.connect(
        f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};PORT=1433;DATABASE={DATABASE};'
        f'UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;timeout=3')

    cursor = connection.cursor()
    cursor.execute(unsubscribe_sms_query)
    connection.commit()
    cursor.close()


def create_custom_message(customer, message):
    # Get Customer Name
    name = customer["FST_NAM"]
    # Get Customer Reward Points
    rewards = "$" + str(customer["LOY_PTS_BAL"])

    # If message has name variable
    if "{name}" in message:
        if name == 'Change':
            message = message.replace("{name}", "")
        else:
            message = message.replace("{name}", name)

    # If message has rewards variable
    if "{rewards}" in message:
        message = message.replace("{rewards}", rewards)

    return message


# ---------------------------- TWILIO TEXT API ------------------------------ #
def send_text(recipients, sms_message, error_log, test_mode=False, photo_message=False, photo_url=""):
    message_script = custom.header_text + sms_message

    # total_messages_sent will track successful messages
    # count will track all iterations through loop, successful or not
    total_messages_sent = 0
    count = 0

    client = Client(account_sid, auth_token)

    # BEGIN ITERATING THROUGH SUBSCRIBERS
    for customer in recipients:
        custom_message = create_custom_message(customer, message_script)

        # Message format for log
        customer["message"] = f"{custom_message.strip().replace('"', '')}"

        # Filter out any phone errors
        if customer["PHONE_1"] == "error":
            customer['response_code'] = 'Invalid phone'
            write_log(customer)
            continue

        elif test_mode:
            customer["response_code"] = "test mode"
            total_messages_sent += 1

        else:
            try:
                if photo_message:
                    twilio_message = client.messages.create(
                        from_=creds.TWILIO_PHONE_NUMBER,
                        media_url=[photo_url],
                        to=customer["PHONE_1"],
                        body=custom_message)
                else:
                    twilio_message = client.messages.create(
                        from_=creds.TWILIO_PHONE_NUMBER,
                        to=customer["PHONE_1"],
                        body=custom_message)

            # Catch Errors
            except twilio.base.exceptions.TwilioRestException as err:
                if str(err)[-22:] == "is not a mobile number":
                    customer["response_code"] = f"Code: {err.code} - landline"
                    move_phone_1_to_mbl_phone_1(customer["PHONE_1"])

                elif str(err)[0:112] == ("HTTP 400 error: Unable to create record: "
                                         "Permission to send an SMS has not been enabled "
                                         "for the region indicated"):
                    customer["response_code"] = f"Code: {err.code} - No Permission to send SMS"

                elif err == ("HTTP 400 error: Unable to create record: "
                             "Attempt to send to unsubscribed recipient"):
                    customer["response_code"] = f"Code: {err.code} - Unsubscribed"
                    unsubscribe_customer_from_sms(customer)

                elif err.code == 20003:
                    customer["response_code"] = f"Code: {err.code} - Permission Denied. Check Auth Token"
                else:
                    customer['response_code'] = f"Code: {err.code} - Unknown TwilioRestException"
            except KeyboardInterrupt:
                sys.exit()
            except Exception as err:
                print(f'Error: {err}', file=error_log)
                customer['response_code'] = str(err)

            # Success
            else:
                customer['response_code'] = twilio_message.sid
                total_messages_sent += 1

        count += 1
        progress = f"{count}/{len(recipients)}"
        print(progress)
        customer['count'] = progress

        try:
            write_log(customer)
        except Exception as err:
            print(f'Log Error: {err}', file=creds.error_log)


def write_log(customer):
    # Create Log
    header_list = ['CUST_NO', 'FST_NAM', 'PHONE_1', 'LOY_PTS_BAL', 'message', 'response_code', 'count']

    try:
        open(creds.log_file_path, 'r')

    except FileNotFoundError:
        log_file = open(creds.log_file_path, 'a')
        w = csv.DictWriter(log_file, delimiter=',', fieldnames=header_list)
        w.writeheader()

    else:
        log_file = open(creds.log_file_path, 'a')
        w = csv.DictWriter(log_file, delimiter=',', fieldnames=header_list)

    w.writerow(customer)
    log_file.close()


def format_phone(phone_number, mode="Twilio", prefix=False):
    """Cleanses input data and returns masked phone for either Twilio or Counterpoint configuration"""
    phone_number_as_string = str(phone_number)
    # Strip away extra symbols
    formatted_phone = phone_number_as_string.replace(" ", "")  # Remove Spaces
    formatted_phone = formatted_phone.replace("-", "")  # Remove Hyphens
    formatted_phone = formatted_phone.replace("(", "")  # Remove Open Parenthesis
    formatted_phone = formatted_phone.replace(")", "")  # Remove Close Parenthesis
    formatted_phone = formatted_phone.replace("+1", "")  # Remove +1
    formatted_phone = formatted_phone[-10:]  # Get last 10 characters
    if mode == "Counterpoint":
        # Masking ###-###-####
        cp_phone = formatted_phone[0:3] + "-" + formatted_phone[3:6] + "-" + formatted_phone[6:10]
        return cp_phone
    else:
        if prefix:
            formatted_phone = "+1" + formatted_phone
        return formatted_phone


def mass_sms_campaign():
    message = ("Use this coupon to save $5 on any hanging baskets Thursday - Saturday! "
               "NO LIMIT. Your reward balance is: {rewards}.")

    photo_link = ""

    contact_list = "./csv_data/test.csv"

    send_text(recipients=read_csv(contact_list),
              sms_message=message,
              test_mode=True,
              photo_message=True,
              photo_url=photo_link,
              error_log=creds.error_log)
