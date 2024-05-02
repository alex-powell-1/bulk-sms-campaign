import csv
import subprocess
import sys
import tkinter
from idlelib.redirector import WidgetRedirector
from tkinter import Listbox, IntVar, Checkbutton, messagebox, END, filedialog
from tkinter.messagebox import showinfo

import pandas
import pyodbc
import twilio.base.exceptions
from pyodbc import OperationalError
from twilio.rest import Client

import creds
import custom
import queries
from creds import SERVER, DATABASE, USERNAME, PASSWORD, account_sid, auth_token


#   ___ __  __ ___    ___   _   __  __ ___  _   ___ ___ _  _ ___
#  / __|  \/  / __|  / __| /_\ |  \/  | _ \/_\ |_ _/ __| \| / __|
#  \__ | |\/| \__ \ | (__ / _ \| |\/| |  _/ _ \ | | (_ | .` \__ \
#  |___|_|  |_|___/  \___/_/ \_|_|  |_|_|/_/ \_|___\___|_|\_|___/
#
# Author: Alex Powell
# GUI version. To run on schedule, please use CLIVersion.py


TEST_MODE = False

csv_data_dict = {}


def select_file():
    """File Selector for importing CSVs"""
    filetypes = (
        ('csv files', '*.csv'),
        ('All files', '*.*')
    )

    cp_data = filedialog.askopenfilename(
        title='Open a CSV',
        initialdir=creds.initial_directory,
        filetypes=filetypes)

    # Read file
    csv_data = pandas.read_csv(cp_data)
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

    # Show first person's info
    try:
        showinfo(
            title='Selected File',
            message=f"First Entry:\n{csv_data_dict[0]["FST_NAM"]}, {csv_data_dict[0]["PHONE_1"]}, "
                    f"{csv_data_dict[0]["LOY_PTS_BAL"]}\n\n"
                    f"Total messages to send: {len(csv_data_dict)}")
        return csv_data_dict

    # Show Error If CSV doesn't include Name and Phone
    except KeyError:
        showinfo(
            title='Selected File',
            message="Invalid File. CSV to contain CUST_NO, FST_NAM, PHONE_1, LOY_PTS_BAL"
        )


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
        messagebox.showerror(title="Network Error", message="Cannot connect to server. Check VPN settings.")


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


# ----------------------Calculate size of segment------------------------------ #
def segment_length():
    # global segment
    try:
        segment = listbox.get(listbox.curselection())
        sql_query = segment_dict[segment]
        messages_to_send = len(query_db(sql_query))
        if messages_to_send < 1:
            list_size.config(text=f"List is empty.")
        elif messages_to_send == 1:
            # Because, grammar.
            list_size.config(text=f"{messages_to_send} message will be sent.")
        else:
            list_size.config(text=f"{messages_to_send} messages will be sent.")
    except tkinter.TclError:
        list_size.config(text="Please select an option")


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
def send_text():
    # Get Listbox Value, Present Message Box with Segment
    segment = ""
    message_script = custom.header_text + message_box.get("1.0", END)
    single_phone = ""
    cp_data = {}

    # ------- Validate User Inputs -------- #

    if segment_checkbutton_used() == 1:
        # global segment
        try:
            segment = listbox.get(listbox.curselection())
        except tkinter.TclError:
            messagebox.showerror(title="Error!", message="You did not pick a selection. Try again.")
            confirm_box = False
        else:
            confirm_box = messagebox.askokcancel(title="Ready to Send?", message=f"These are the details entered:"
                                                                                 f" \n\nMessage: {message_script}\n\n"
                                                                                 f"Sent to: {segment}")
    elif single_number_checkbutton_used() == 1:
        original_number = single_number_input.get()
        single_phone = format_phone(original_number, prefix=True)
        if len(single_phone) == 12:
            confirm_box = messagebox.askokcancel(title="Ready to Send?", message=f"These are the details entered:"
                                                                                 f" \n\nMessage: {message_script}\n\n"
                                                                                 f"Sent to: {original_number}")
        else:
            messagebox.showerror(title="error", message="Invalid phone number. Please try again.")
            confirm_box = False

    elif csv_checkbutton_used() == 1:
        if csv_data_dict == {}:
            messagebox.showerror(title="CSV Error", message="Please select a csv file with the following header:\n"
                                                            "CUST_NO,FST_NAM,PHONE_1,LOY_PTS_BAL\n"
                                                            "(No spaces allowed!)")
            confirm_box = False

        else:
            confirm_box = messagebox.askokcancel(title="Ready to Send?", message=f"These are the details entered:"
                                                                                 f" \n\nMessage: {message_script}\n\n"
                                                                                 f"Sent to: CSV List\n"
                                                                                 f"Total Messages to Send: "
                                                                                 f"{len(csv_data_dict)}")
    else:
        confirm_box = messagebox.showinfo(title="Error", message="You did not choose a selection. Try again.")

    if confirm_box and (segment_checkbutton_used() == 1 or
                        single_number_checkbutton_used() == 1 or
                        csv_checkbutton_used() == 1):

        # ----------GET DATA FROM SQL------------#
        if segment_checkbutton_used() == 1:
            sql_query = segment_dict[segment]
            cp_data = query_db(sql_query)

        # ------------------OR-------------------#

        # -------GET DATA FROM CSV---------#
        elif csv_checkbutton_used() == 1:
            cp_data = csv_data_dict

        # ----------DATA FOR SINGLE PHONE---------#
        elif single_number_checkbutton_used() == 1:
            cp_data = [{"CUST_NO": '', "FST_NAM": '', "PHONE_1": single_phone,
                        "LOY_PTS_BAL": '', "message": '', 'response_code': ''}]

        # total_messages_sent will track successful messages
        total_messages_sent = 0
        # count will track all iterations through loop, successful or not
        count = 0

        client = Client(account_sid, auth_token)
        # BEGIN ITERATING THROUGH SUBSCRIBERS
        for customer in cp_data:
            custom_message = create_custom_message(customer, message_script)

            # Message format for log
            customer["message"] = f"{custom_message.strip().replace('"', '')}"

            # Filter out any phone errors
            if customer["PHONE_1"] == "error":
                customer['response_code'] = 'Invalid phone'
                write_log(customer)
                continue

            elif test_mode():
                customer["response_code"] = "test mode"
                total_messages_sent += 1

            else:
                try:
                    if photo_checkbutton_used():
                        photo_url = photo_input.get()
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
                    print(f'Error: {err}', file=creds.error_log)
                    customer['response_code'] = str(err)

                # Success
                else:
                    customer['response_code'] = twilio_message.sid
                    total_messages_sent += 1

            count += 1
            customer['count'] = f"{count}/{len(cp_data)}"
            write_log(customer)

            progress_text_label.config(text=f"Messages Sent: {count}/{len(cp_data)}")
            canvas.update()

        completed_message = (f"Process complete!\n"
                             f"{total_messages_sent} messages sent. \n"
                             f"{len(cp_data) - total_messages_sent} messages failed. \n\n"
                             f"Would you like to see the log?")

        if messagebox.askyesno(title="Completed", message=completed_message):
            view_log()


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


# ---------------------------- UI SETUP ------------------------------- #
window = tkinter.Tk()
window.title(custom.application_title)
window.config(padx=30, pady=10, background=custom.BACKGROUND_COLOR)


def center_window(width=410, height=950):
    # get screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # calculate position x and y coordinates
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    window.geometry('%dx%d+%d+%d' % (width, height, x, y - 40))


center_window()


def my_insert(*args):
    original_insert(*args)
    update_label()


def my_delete(*args):
    original_delete(*args)
    update_label()


def my_replace(*args):
    original_replace(*args)
    update_label()


def update_label():
    number_of_chars = len(message_box.get("1.0", "end")) + 19
    if number_of_chars <= 160:
        user_label.config(text=f"Message Length: {number_of_chars}", fg="green")
    else:
        user_label.config(text=f"Message Length: {number_of_chars}", fg="red")


def photo_checkbutton_used() -> bool:
    # Prints 1 if On button checked, otherwise 0.
    check = checked_state.get()
    if check == 0:
        photo_input.config(state="disabled")
        photo_link_help_text.config(state="disabled")
        return False
    else:
        photo_input.config(state="normal")
        photo_link_help_text.config(state="normal", fg="black")
        return True


def segment_checkbutton_used():
    check = segment_checkbox_state.get()
    if check == 0:
        listbox.selection_clear(0, END)
        listbox.config(state="disabled")
        list_size.config(state="disabled")
        calculate_size_button.config(state="disabled")
        csv_checkbox.config(state="normal")
        open_csv_file_button.config(state="disabled")
        list_size.config(text="")
        single_number_input.config(state="disabled")
        single_number_checkbox.config(state="normal")

        return 0
    else:
        listbox.config(state="normal")
        list_size.config(state="normal")
        calculate_size_button.config(state="normal")
        csv_checkbox.config(state="disabled")
        open_csv_file_button.config(state="disabled")
        single_number_input.config(state="disabled")
        single_number_checkbox.config(state="disabled")
        return 1


def csv_checkbutton_used():
    check = csv_checkbox_state.get()
    if check == 0:
        open_csv_file_button.config(state="disabled")
        single_number_checkbox.config(state="normal")
        single_number_input.config(state="disabled")
        listbox.selection_clear(0, END)
        segment_checkbox.config(state="normal")
        listbox.config(state="disabled")
        list_size.config(state="disabled")
        calculate_size_button.config(state="disabled")
        return 0
    else:
        open_csv_file_button.config(state="normal")
        single_number_checkbox.config(state="disabled")
        single_number_input.config(state="disabled")
        listbox.selection_clear(0, END)
        segment_checkbox.config(state="disabled")
        listbox.config(state="disabled")
        list_size.config(state="disabled")
        calculate_size_button.config(state="disabled")
        list_size.config(text="")
        return 1


def single_number_checkbutton_used():
    check = single_number_checkbox_state.get()
    if check == 0:
        single_number_input.delete(0, END)
        single_number_input.config(state="disabled")
        csv_checkbox.config(state="normal")
        open_csv_file_button.config(state="disabled")
        listbox.selection_clear(0, END)
        segment_checkbox.config(state="normal")
        listbox.config(state="disabled")
        list_size.config(state="disabled")
        calculate_size_button.config(state="disabled")
        return 0
    else:
        single_number_input.config(state="normal")
        csv_checkbox.config(state="disabled")
        open_csv_file_button.config(state="disabled")
        listbox.selection_clear(0, END)
        segment_checkbox.config(state="disabled")
        listbox.config(state="disabled")
        list_size.config(state="disabled")
        calculate_size_button.config(state="disabled")
        list_size.config(text="")
        return 1


def test_mode() -> bool:
    check = test_mode_checkbox_state.get()
    if check == 1:
        return True


def view_log():
    subprocess.Popen(f'explorer /select, {creds.log_directory}')


# Logo
canvas = tkinter.Canvas(width=350, height=172, background=custom.BACKGROUND_COLOR,
                        highlightcolor=custom.BACKGROUND_COLOR, highlightthickness=0)

logo = tkinter.PhotoImage(file=custom.logo)

canvas.create_image(175, 86, image=logo)
canvas.grid(column=0, row=0, pady=3, columnspan=3)

# SMS Text Messaging Sub Title
website_label = tkinter.Label(text="SMS Text Messaging",
                              font=("Arial", 12), fg=custom.MEDIUM_DARK_GREEN, background=custom.BACKGROUND_COLOR)
website_label.grid(column=0, row=1, columnspan=3, pady=5)

# Individual Phone Number Used Checkbox
single_number_checkbox_state = IntVar()
single_number_checkbox = Checkbutton(text="Option #1 - Single Phone Number",
                                     font=("Arial", 10), variable=single_number_checkbox_state,
                                     command=single_number_checkbutton_used, fg="black",
                                     background=custom.BACKGROUND_COLOR)
single_number_checkbox_state.get()
single_number_checkbox.grid(column=0, row=2, columnspan=3, pady=0)

single_number_input = tkinter.Entry(width=25, justify="center")
single_number_input.config(state="disabled")
single_number_input.grid(row=3, column=0, columnspan=3, pady=10)

# CSV Checkbox
csv_checkbox_state = IntVar()
csv_checkbox = Checkbutton(text="Option #2 - Use .csv File", font=("Arial", 10), variable=csv_checkbox_state,
                           command=csv_checkbutton_used, fg="black", background=custom.BACKGROUND_COLOR)
csv_checkbox_state.get()
csv_checkbox.grid(column=0, row=4, columnspan=3, pady=0)

# File open dialog
open_csv_file_button = tkinter.Button(text='Import CSV', font=("Arial", 10), command=select_file,
                                      highlightbackground=custom.BACKGROUND_COLOR)
open_csv_file_button.config(state="disabled")
open_csv_file_button.grid(row=5, column=0, columnspan=3, pady=3)

# Use Customer Segment
segment_checkbox_state = IntVar()
segment_checkbox = Checkbutton(text="Option #3 - Use Customer Segment", font=("Arial", 10),
                               variable=segment_checkbox_state,
                               command=segment_checkbutton_used, fg="black", background=custom.BACKGROUND_COLOR)
segment_checkbox_state.get()
segment_checkbox.grid(column=0, row=6, columnspan=3, pady=3)

# Create Listbox with Choices
listbox = Listbox(height=6, width=25, highlightcolor="green", exportselection=False,
                  font=("Arial", 10), justify="center")
segment_dict = {'Single Test': queries.test_group_1,
                "Management Test Group": queries.test_group_2,
                'Wholesale Customers': queries.wholesale_all,
                'Retail Customers: All': queries.retail_all,
                "Yesterday's Shoppers": queries.yesterday_purchases,
                '5-Day Follow Up': queries.five_days_ago_purchases,
                '1-Week Follow Up': queries.one_week_ago_purchases,
                'Retail Most Recent 1000': queries.retail_recent_1000,
                'Retail Most Recent 2000': queries.retail_recent_2000,
                'Retail Most Recent 3000': queries.retail_recent_3000,
                'Retail Most Recent 4000': queries.retail_recent_4000,
                'Spring Annual Shoppers': queries.spring_annual_shoppers,
                'Fall Mum Shoppers': queries.fall_mum_shoppers,
                'Christmas Shoppers': queries.christmas_shoppers,
                'No Purchases: 6 Months': queries.no_purchases_6_months,
                'No Purchases: 12 Months': queries.no_purchases_12_months,
                'Birthday: January': queries.january_bday,
                'Birthday: February': queries.february_bday,
                'Birthday: March': queries.march_bday,
                'Birthday: April': queries.april_bday,
                'Birthday: May': queries.may_bday,
                'Birthday: June': queries.june_bday,
                'Birthday: July': queries.july_bday,
                'Birthday: August': queries.august_bday,
                'Birthday: September': queries.september_bday,
                'Birthday: October': queries.october_bday,
                'Birthday: November': queries.november_bday,
                'Birthday: December': queries.december_bday
                }
segments = list(segment_dict.keys())
for item in segments:
    listbox.insert(segments.index(item), item)
listbox.bind("<<ListboxSelect>>")
listbox.config(state="disabled")
listbox.grid(row=7, column=0, columnspan=3)

# Calculate and Show List Size
calculate_size_button = tkinter.Button(text="Calculate List Size", command=segment_length, font=("Arial", 10),
                                       background=custom.BACKGROUND_COLOR, highlightbackground=custom.BACKGROUND_COLOR)
calculate_size_button.config(state="disabled")
calculate_size_button.grid(row=8, column=0, columnspan=3, pady=5)

list_size = tkinter.Label(text="", font=("Arial", 9), fg=custom.MEDIUM_GREEN, background=custom.BACKGROUND_COLOR)
list_size.grid(column=0, row=9, columnspan=3, pady=2)

# Header Text Label
header_text_label = tkinter.Label(text="Header Text", font=("Arial", 9),
                                  fg=custom.MEDIUM_DARK_GREEN, background=custom.BACKGROUND_COLOR)
header_text_label.grid(column=0, row=10, columnspan=3, pady=0)

# Header Label
header_text_label = tkinter.Label(text=custom.header_label_text, font=("Arial", 10), background=custom.BACKGROUND_COLOR)
header_text_label.grid(column=0, row=11, columnspan=3, pady=0)

# Message Box
message_label = tkinter.Label(text="Message: ", font=("Arial", 10), fg=custom.MEDIUM_DARK_GREEN,
                              background=custom.BACKGROUND_COLOR)
message_label.grid(column=0, row=12, columnspan=3, pady=3)
message_box = tkinter.Text(window, width=35, height=4, wrap="word", font=("Arial", 12), fg="black")
message_box.insert("end", "Replace this text with the SMS message."
                          "\nUse curly braces around {name} for first name and {rewards} for reward balance.")
message_box.grid(row=13, column=0, columnspan=3, pady=2)

# Length of Message
user_label = tkinter.Label(text="Message Length: 20", font=("Arial", 12), background=custom.BACKGROUND_COLOR)
user_label.grid(column=0, row=14, columnspan=3, pady=3)

# Picture Checkbox
# variable to hold on to checked state, 0 is off, 1 is on.
checked_state = IntVar()
picture_checkbox = Checkbutton(text="Include Picture Link?", font=("Arial", 10), variable=checked_state,
                               command=photo_checkbutton_used,
                               fg="black", background=custom.BACKGROUND_COLOR)
checked_state.get()
picture_checkbox.grid(column=0, row=15, columnspan=3, pady=10)
photo_link_help_text = tkinter.Label(text="Must be a publicly visible link.", state="disabled",
                                     font=("Arial", 10, "italic"), fg="grey", background=custom.BACKGROUND_COLOR)
photo_link_help_text.grid(column=0, row=16, columnspan=3, pady=0)

# Photo Link
photo_input = tkinter.Entry(width=48, justify="center")
photo_input.insert("0", string="Replace with link to Photo")
photo_input.config(state="disabled")
photo_input.grid(row=17, column=0, columnspan=3, pady=10)

# Send Button
send_button = tkinter.Button(text="Send", command=send_text, font=("Arial", 14), fg=custom.DARK_GREEN,
                             highlightbackground=custom.BACKGROUND_COLOR)
send_button.grid(row=18, column=0, columnspan=3, pady=5)

# Test Mode Checkbox
test_mode_checkbox_state = IntVar()
test_mode_checkbox = Checkbutton(text="Test Mode", font=("Arial", 10), variable=test_mode_checkbox_state,
                                 command=test_mode, fg="black", background=custom.BACKGROUND_COLOR)
test_mode_checkbox_state.get()
test_mode_checkbox.grid(column=0, row=19, columnspan=1, pady=0)

# View Log
log_button = tkinter.Button(text="View Log", command=view_log, font=("Arial", 10),
                            highlightbackground=custom.BACKGROUND_COLOR)
log_button.grid(row=19, column=1, columnspan=1, pady=3)

progress_text_label = tkinter.Label(text="", font=("Arial", 10), background=custom.BACKGROUND_COLOR,
                                    fg=custom.MEDIUM_DARK_GREEN)
progress_text_label.grid(column=0, row=21, columnspan=3, pady=0)

# Version Number
header_text_label = tkinter.Label(text="      Version 1.1", font=("Arial", 9),
                                  fg=custom.MEDIUM_DARK_GREEN, background=custom.BACKGROUND_COLOR)
header_text_label.grid(column=2, row=19, columnspan=1, pady=0)

redir = WidgetRedirector(message_box)
original_insert = redir.register("insert", my_insert)
original_delete = redir.register("delete", my_delete)
original_replace = redir.register("replace", my_replace)

window.mainloop()
