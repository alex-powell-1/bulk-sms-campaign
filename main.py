import subprocess
import sys
import tkinter
from idlelib.redirector import WidgetRedirector
from tkinter import Listbox, IntVar, Checkbutton, messagebox, END, filedialog
from tkinter.messagebox import showinfo
from datetime import datetime
from error_handler import logger
import pandas
import twilio.base.exceptions
from twilio.rest import Client

import creds
import custom
import queries
from creds import account_sid, auth_token
from database import Database
from utilities import PhoneNumber
from traceback import print_exc as tb


#   ___ __  __ ___    ___   _   __  __ ___  _   ___ ___ _  _ ___
#  / __|  \/  / __|  / __| /_\ |  \/  | _ \/_\ |_ _/ __| \| / __|
#  \__ | |\/| \__ \ | (__ / _ \| |\/| |  _/ _ \ | | (_ | .` \__ \
#  |___|_|  |_|___/  \___/_/ \_|_|  |_|_|/_/ \_|___\___|_|\_|___/
#
# Author: Alex Powell
# GUI version. To run on schedule, please use CLIVersion.py
version = 1.3
# Release Notes: This version adds writing to database for each message sent.
# Need to add sending to CONTCT_1 (if exists).

TEST_MODE = False
ORIGIN = creds.origin
csv_data_dict = {}


def select_file():
    """File Selector for importing CSVs"""
    filetypes = (('csv files', '*.csv'), ('All files', '*.*'))

    cp_data = filedialog.askopenfilename(
        title='Open a CSV', initialdir=creds.initial_directory, filetypes=filetypes
    )

    # Read file
    csv_data = pandas.read_csv(cp_data)
    global csv_data_dict
    csv_data_dict = csv_data.to_dict('records')
    # Format phone number
    for customer in csv_data_dict:
        phone_1 = customer['PHONE_1']
        customer['PHONE_1'] = PhoneNumber(str(phone_1)).to_twilio()
        phone_2 = customer['PHONE_2']
        customer['PHONE_2'] = PhoneNumber(str(phone_2)).to_twilio()

    # Show first person's info
    try:
        showinfo(
            title='Selected File',
            message=f"First Entry:\n{csv_data_dict[0]["NAM"]}, {csv_data_dict[0]["PHONE_1"]}, "
            f"{csv_data_dict[0]["LOY_PTS_BAL"]}{csv_data_dict[0]["CATEG_COD"]}\n\n"
            f"Total messages to send: {len(csv_data_dict)}",
        )
        return csv_data_dict

    # Show Error If CSV doesn't include Name and Phone
    except KeyError:
        showinfo(
            title='Selected File',
            message='Invalid File. CSV to contain CUST_NO, NAM, PHONE_1, LOY_PTS_BAL, CATEG_COD',
        )


def segment_length():
    """Calculate the number of messages to be sent"""
    try:
        segment = listbox.get(listbox.curselection())
        sql_query = segment_dict[segment]
        messages_to_send = len(Database.query(sql_query))
        if messages_to_send < 1:
            list_size.config(text='List is empty.')
        elif messages_to_send == 1:
            # Because, grammar.
            list_size.config(text=f'{messages_to_send} message will be sent.')
        else:
            list_size.config(text=f'{messages_to_send} messages will be sent.')
    except tkinter.TclError:
        list_size.config(text='Please select an option')


def create_custom_message(customer: Database.SMS.CustomerText, message):
    # Get Customer Name
    name = customer.name
    # Get Customer Reward Points
    rewards = '$' + str(customer.points)

    # If message has name variable
    if '{name}' in message:
        first_name = name.split(' ')[0].title()
        message = message.replace('{name}', first_name)

    # If message has rewards variable
    if '{rewards}' in message:
        message = message.replace('{rewards}', rewards)

    return message


# ---------------------------- TWILIO TEXT API ------------------------------ #
def send_text():
    # Get Listbox Value, Present Message Box with Segment
    segment = ''
    message_script = custom.header_text + message_box.get('1.0', END)
    single_phone = ''
    cp_data = [
        {'CUST_NO': None, 'NAM': None, 'PHONE_1': None, 'PHONE_2': None, 'LOY_PTS_BAL': None, 'CATEG_COD': None}
    ]

    # ------- Validate User Inputs -------- #

    if segment_checkbutton_used() == 1:
        # global segment
        try:
            segment = listbox.get(listbox.curselection())
        except tkinter.TclError:
            messagebox.showerror(title='Error!', message='You did not pick a selection. Try again.')
            confirm_box = False
        else:
            confirm_box = messagebox.askokcancel(
                title='Ready to Send?',
                message=f'These are the details entered:'
                f' \n\nMessage: {message_script}\n\n'
                f'Sent to: {segment}',
            )

    elif single_number_checkbutton_used() == 1:
        original_number = single_number_input.get()
        single_phone = PhoneNumber(original_number).to_twilio()
        if len(single_phone) == 12:
            confirm_box = messagebox.askokcancel(
                title='Ready to Send?',
                message=f'These are the details entered:'
                f' \n\nMessage: {message_script}\n\n'
                f'Sent to: {original_number}',
            )
        else:
            messagebox.showerror(title='error', message='Invalid phone number. Please try again.')
            confirm_box = False

    elif csv_checkbutton_used() == 1:
        if csv_data_dict == {}:
            messagebox.showerror(
                title='CSV Error',
                message='Please select a csv file with the following header:\n'
                'CUST_NO,NAM,PHONE_1,LOY_PTS_BAL,CATEG_COD\n'
                '(No spaces allowed!)',
            )
            confirm_box = False

        else:
            confirm_box = messagebox.askokcancel(
                title='Ready to Send?',
                message=f'These are the details entered:'
                f' \n\nMessage: {message_script}\n\n'
                f'Sent to: CSV List\n'
                f'Total Messages to Send: '
                f'{len(csv_data_dict)}',
            )
    else:
        confirm_box = messagebox.showinfo(title='Error', message='You did not choose a selection. Try again.')

    if confirm_box and (
        segment_checkbutton_used() == 1 or single_number_checkbutton_used() == 1 or csv_checkbutton_used() == 1
    ):
        # ----------GET DATA FROM SQL------------#
        if segment_checkbutton_used() == 1:
            sql_query = segment_dict[segment]
            cp_data = Database.query(sql_query)
            if cp_data is None:
                messagebox.showerror(
                    title='Error!', message='There was an error with the SQL query. Please try again.'
                )
                return
            else:
                cp_data = [
                    {
                        'CUST_NO': customer[0],
                        'NAM': customer[1],
                        'PHONE_1': PhoneNumber(customer[2]).to_twilio(),
                        'PHONE_2': PhoneNumber(customer[3]).to_twilio() if customer[3] else '',
                        'LOY_PTS_BAL': customer[4],
                        'CATEG_COD': customer[5],
                    }
                    for customer in cp_data
                ]

        # ------------------OR-------------------#

        # -------GET DATA FROM CSV---------#
        elif csv_checkbutton_used() == 1:
            cp_data = csv_data_dict

        # ----------DATA FOR SINGLE PHONE---------#
        elif single_number_checkbutton_used() == 1:
            cp_data['PHONE_1'] = single_phone

        # total_messages_sent will track successful messages
        total_messages_sent = 0
        # count will track all iterations through loop, successful or not
        global count
        count = 0

        client = Client(account_sid, auth_token)

        campaign = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # BEGIN ITERATING THROUGH SUBSCRIBERS
        for customer in cp_data:
            cust_no = customer['CUST_NO']
            name = customer['NAM']
            ph_1 = customer['PHONE_1']
            ph_2 = customer['PHONE_2']
            pts = customer['LOY_PTS_BAL']
            cat = customer['CATEG_COD']

            cust_txt = Database.SMS.CustomerText(phone=ph_1, cust_no=cust_no, points=pts, category=cat, name=name)

            def send_customer_text(cust_txt):
                cust_txt.message = create_custom_message(cust_txt, message_script)
                cust_txt.campaign = campaign

                # Filter out any phone errors
                if cust_txt.phone == 'error':
                    cust_txt.response_text = 'Invalid phone'
                    Database.SMS.insert(customer_text=cust_txt)
                    return

                elif test_mode():
                    cust_txt.sid = 'TEST'
                    total_messages_sent += 1

                else:
                    try:
                        if photo_checkbutton_used():
                            cust_txt.media = photo_input.get()
                            twilio_message = client.messages.create(
                                from_=creds.TWILIO_PHONE_NUMBER,
                                media_url=[cust_txt.media],
                                to=cust_txt.phone,
                                body=cust_txt.message,
                            )
                        else:
                            twilio_message = client.messages.create(
                                from_=creds.TWILIO_PHONE_NUMBER, to=cust_txt.phone, body=cust_txt.message
                            )

                    # Catch Errors
                    except twilio.base.exceptions.TwilioRestException as err:
                        logger.error(
                            error=f'Phone Number: {cust_txt.phone}, Code: {err.code}, Message:{err.msg}',
                            origin='SMS-Campaigns->send_text()',
                        )
                        cust_txt.response_code = err.code
                        cust_txt.response_text = err.msg

                        if err.code == 21614:
                            # From Twilio: You have attempted to send a SMS with a 'To' number that is not a valid
                            # mobile number. It is likely that the number is a landline number or is an invalid number.
                            Database.SMS.move_phone_1_to_landline(customer_text=cust_txt)

                        elif err.code == 21610:  # Previously unsubscribed
                            Database.SMS.unsubscribe(cust_txt)

                    except KeyboardInterrupt:
                        sys.exit()

                    except Exception as err:
                        logger.error(
                            error=f'Uncaught Exception: {err}', origin='SMS-Campaigns->send_text()', traceback=tb()
                        )
                        cust_txt.response_text = str(err)

                    # Success
                    else:
                        cust_txt.sid = twilio_message.sid
                        total_messages_sent += 1

                global count
                count += 1

                cust_txt.count = f'{count}/{len(cp_data)}'

                try:
                    Database.SMS.insert(cust_txt)
                except Exception as err:
                    with open(creds.error_log, 'a') as error_log:
                        print(f'Log Error: {err}', file=error_log)
                finally:
                    progress_text_label.config(text=f'Messages Sent: {count}/{len(cp_data)}')
                    canvas.update()

            send_customer_text(cust_txt)
            if ph_2:
                send_customer_text(
                    Database.SMS.CustomerText(phone=ph_2, cust_no=cust_no, points=pts, category=cat, name=name)
                )

        completed_message = (
            f'Process complete!\n'
            f'{total_messages_sent} messages sent. \n'
            f'{len(cp_data) - total_messages_sent} messages failed. \n\n'
            f'Would you like to see the log?'
        )

        if messagebox.askyesno(title='Completed', message=completed_message):
            view_log()


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
    number_of_chars = len(message_box.get('1.0', 'end')) + 19
    if number_of_chars <= 160:
        user_label.config(text=f'Message Length: {number_of_chars}', fg='green')
    else:
        user_label.config(text=f'Message Length: {number_of_chars}', fg='red')


def photo_checkbutton_used() -> bool:
    # Prints 1 if On button checked, otherwise 0.
    check = checked_state.get()
    if check == 0:
        photo_input.config(state='disabled')
        photo_link_help_text.config(state='disabled')
        return False
    else:
        photo_input.config(state='normal')
        photo_link_help_text.config(state='normal', fg='black')
        return True


def segment_checkbutton_used():
    check = segment_checkbox_state.get()
    if check == 0:
        listbox.selection_clear(0, END)
        listbox.config(state='disabled')
        list_size.config(state='disabled')
        calculate_size_button.config(state='disabled')
        csv_checkbox.config(state='normal')
        open_csv_file_button.config(state='disabled')
        list_size.config(text='')
        single_number_input.config(state='disabled')
        single_number_checkbox.config(state='normal')

        return 0
    else:
        listbox.config(state='normal')
        list_size.config(state='normal')
        calculate_size_button.config(state='normal')
        csv_checkbox.config(state='disabled')
        open_csv_file_button.config(state='disabled')
        single_number_input.config(state='disabled')
        single_number_checkbox.config(state='disabled')
        return 1


def csv_checkbutton_used():
    check = csv_checkbox_state.get()
    if check == 0:
        open_csv_file_button.config(state='disabled')
        single_number_checkbox.config(state='normal')
        single_number_input.config(state='disabled')
        listbox.selection_clear(0, END)
        segment_checkbox.config(state='normal')
        listbox.config(state='disabled')
        list_size.config(state='disabled')
        calculate_size_button.config(state='disabled')
        return 0
    else:
        open_csv_file_button.config(state='normal')
        single_number_checkbox.config(state='disabled')
        single_number_input.config(state='disabled')
        listbox.selection_clear(0, END)
        segment_checkbox.config(state='disabled')
        listbox.config(state='disabled')
        list_size.config(state='disabled')
        calculate_size_button.config(state='disabled')
        list_size.config(text='')
        return 1


def single_number_checkbutton_used():
    check = single_number_checkbox_state.get()
    if check == 0:
        single_number_input.delete(0, END)
        single_number_input.config(state='disabled')
        csv_checkbox.config(state='normal')
        open_csv_file_button.config(state='disabled')
        listbox.selection_clear(0, END)
        segment_checkbox.config(state='normal')
        listbox.config(state='disabled')
        list_size.config(state='disabled')
        calculate_size_button.config(state='disabled')
        return 0
    else:
        single_number_input.config(state='normal')
        csv_checkbox.config(state='disabled')
        open_csv_file_button.config(state='disabled')
        listbox.selection_clear(0, END)
        segment_checkbox.config(state='disabled')
        listbox.config(state='disabled')
        list_size.config(state='disabled')
        calculate_size_button.config(state='disabled')
        list_size.config(text='')
        return 1


def test_mode() -> bool:
    check = test_mode_checkbox_state.get()
    if check == 1:
        return True


def view_log():
    subprocess.Popen(f'explorer /open, {creds.log_directory}')


# Logo
canvas = tkinter.Canvas(
    width=350,
    height=172,
    background=custom.BACKGROUND_COLOR,
    highlightcolor=custom.BACKGROUND_COLOR,
    highlightthickness=0,
)

logo = tkinter.PhotoImage(file=custom.logo)

canvas.create_image(175, 86, image=logo)
canvas.grid(column=0, row=0, pady=3, columnspan=3)

# SMS Text Messaging Sub Title
website_label = tkinter.Label(
    text='SMS Text Messaging', font=('Arial', 12), fg=custom.MEDIUM_DARK_GREEN, background=custom.BACKGROUND_COLOR
)
website_label.grid(column=0, row=1, columnspan=3, pady=5)

# Individual Phone Number Used Checkbox
single_number_checkbox_state = IntVar()
single_number_checkbox = Checkbutton(
    text='Option #1 - Single Phone Number',
    font=('Arial', 10),
    variable=single_number_checkbox_state,
    command=single_number_checkbutton_used,
    fg='black',
    background=custom.BACKGROUND_COLOR,
)
single_number_checkbox_state.get()
single_number_checkbox.grid(column=0, row=2, columnspan=3, pady=0)

single_number_input = tkinter.Entry(width=25, justify='center')
single_number_input.config(state='disabled')
single_number_input.grid(row=3, column=0, columnspan=3, pady=10)

# CSV Checkbox
csv_checkbox_state = IntVar()
csv_checkbox = Checkbutton(
    text='Option #2 - Use .csv File',
    font=('Arial', 10),
    variable=csv_checkbox_state,
    command=csv_checkbutton_used,
    fg='black',
    background=custom.BACKGROUND_COLOR,
)
csv_checkbox_state.get()
csv_checkbox.grid(column=0, row=4, columnspan=3, pady=0)

# File open dialog
open_csv_file_button = tkinter.Button(
    text='Import CSV', font=('Arial', 10), command=select_file, highlightbackground=custom.BACKGROUND_COLOR
)
open_csv_file_button.config(state='disabled')
open_csv_file_button.grid(row=5, column=0, columnspan=3, pady=3)

# Use Customer Segment
segment_checkbox_state = IntVar()
segment_checkbox = Checkbutton(
    text='Option #3 - Use Customer Segment',
    font=('Arial', 10),
    variable=segment_checkbox_state,
    command=segment_checkbutton_used,
    fg='black',
    background=custom.BACKGROUND_COLOR,
)
segment_checkbox_state.get()
segment_checkbox.grid(column=0, row=6, columnspan=3, pady=3)

# Create Listbox with Choices
listbox = Listbox(
    height=6, width=25, highlightcolor='green', exportselection=False, font=('Arial', 10), justify='center'
)
segment_dict = {
    'Single Test': queries.test_group_1,
    'Management Test Group': queries.test_group_2,
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
    'Birthday: December': queries.december_bday,
}
segments = list(segment_dict.keys())
for item in segments:
    listbox.insert(segments.index(item), item)
listbox.bind('<<ListboxSelect>>')
listbox.config(state='disabled')
listbox.grid(row=7, column=0, columnspan=3)

# Calculate and Show List Size
calculate_size_button = tkinter.Button(
    text='Calculate List Size',
    command=segment_length,
    font=('Arial', 10),
    background=custom.BACKGROUND_COLOR,
    highlightbackground=custom.BACKGROUND_COLOR,
)
calculate_size_button.config(state='disabled')
calculate_size_button.grid(row=8, column=0, columnspan=3, pady=5)

list_size = tkinter.Label(text='', font=('Arial', 9), fg=custom.MEDIUM_GREEN, background=custom.BACKGROUND_COLOR)
list_size.grid(column=0, row=9, columnspan=3, pady=2)

# Header Text Label
header_text_label = tkinter.Label(
    text='Header Text', font=('Arial', 9), fg=custom.MEDIUM_DARK_GREEN, background=custom.BACKGROUND_COLOR
)
header_text_label.grid(column=0, row=10, columnspan=3, pady=0)

# Header Label
header_text_label = tkinter.Label(
    text=custom.header_label_text, font=('Arial', 10), background=custom.BACKGROUND_COLOR
)
header_text_label.grid(column=0, row=11, columnspan=3, pady=0)

# Message Box
message_label = tkinter.Label(
    text='Message: ', font=('Arial', 10), fg=custom.MEDIUM_DARK_GREEN, background=custom.BACKGROUND_COLOR
)
message_label.grid(column=0, row=12, columnspan=3, pady=3)
message_box = tkinter.Text(window, width=35, height=4, wrap='word', font=('Arial', 12), fg='black')
message_box.insert(
    'end',
    'Replace this text with the SMS message.'
    '\nUse curly braces around {name} for first name and {rewards} for reward balance.',
)
message_box.grid(row=13, column=0, columnspan=3, pady=2)

# Length of Message
user_label = tkinter.Label(text='Message Length: 20', font=('Arial', 12), background=custom.BACKGROUND_COLOR)
user_label.grid(column=0, row=14, columnspan=3, pady=3)

# Picture Checkbox
# variable to hold on to checked state, 0 is off, 1 is on.
checked_state = IntVar()
picture_checkbox = Checkbutton(
    text='Include Picture Link?',
    font=('Arial', 10),
    variable=checked_state,
    command=photo_checkbutton_used,
    fg='black',
    background=custom.BACKGROUND_COLOR,
)
checked_state.get()
picture_checkbox.grid(column=0, row=15, columnspan=3, pady=10)
photo_link_help_text = tkinter.Label(
    text='Must be a publicly visible link.',
    state='disabled',
    font=('Arial', 10, 'italic'),
    fg='grey',
    background=custom.BACKGROUND_COLOR,
)
photo_link_help_text.grid(column=0, row=16, columnspan=3, pady=0)

# Photo Link
photo_input = tkinter.Entry(width=48, justify='center')
photo_input.insert('0', string='Replace with link to Photo')
photo_input.config(state='disabled')
photo_input.grid(row=17, column=0, columnspan=3, pady=10)

# Send Button
send_button = tkinter.Button(
    text='Send',
    command=send_text,
    font=('Arial', 14),
    fg=custom.DARK_GREEN,
    highlightbackground=custom.BACKGROUND_COLOR,
)
send_button.grid(row=18, column=0, columnspan=3, pady=5)

# Test Mode Checkbox
test_mode_checkbox_state = IntVar()
test_mode_checkbox = Checkbutton(
    text='Test Mode',
    font=('Arial', 10),
    variable=test_mode_checkbox_state,
    command=test_mode,
    fg='black',
    background=custom.BACKGROUND_COLOR,
)
test_mode_checkbox_state.get()
test_mode_checkbox.grid(column=0, row=19, columnspan=1, pady=0)

# View Log
log_button = tkinter.Button(
    text='View Log', command=view_log, font=('Arial', 10), highlightbackground=custom.BACKGROUND_COLOR
)
log_button.grid(row=19, column=1, columnspan=1, pady=3)

progress_text_label = tkinter.Label(
    text='', font=('Arial', 10), background=custom.BACKGROUND_COLOR, fg=custom.MEDIUM_DARK_GREEN
)
progress_text_label.grid(column=0, row=21, columnspan=3, pady=0)

# Version Number
header_text_label = tkinter.Label(
    text=f'      Version {version}',
    font=('Arial', 9),
    fg=custom.MEDIUM_DARK_GREEN,
    background=custom.BACKGROUND_COLOR,
)
header_text_label.grid(column=2, row=19, columnspan=1, pady=0)

redir = WidgetRedirector(message_box)
original_insert = redir.register('insert', my_insert)
original_delete = redir.register('delete', my_delete)
original_replace = redir.register('replace', my_replace)

window.mainloop()
