import subprocess
import tkinter
from idlelib.redirector import WidgetRedirector
from tkinter import Listbox, IntVar, Checkbutton, messagebox, END, filedialog
from tkinter.messagebox import showinfo
from datetime import datetime
import os
import pandas
import queries
from database import Database
from traceback import print_exc as tb
from creds import Company, Logs
from error_handler import logger
import threading
from models.customers import Customers, Customer
from models.campaign import Campaign
from models.texts import Text
from twilio.rest import Client
from creds import Twilio
import concurrent.futures
import sys
import time
from tkinter import ttk
import twilio.base.exceptions


# Author: Alex Powell
# Release Notes
# 1.4 - Added threading

version = 1.4
DARK_GREEN = '#3A4D39'
MEDIUM_DARK_GREEN = '#4F6F52'
MEDIUM_GREEN = '#739072'
BACKGROUND_COLOR = '#ECE3CE'
application_title = f'{Company.name} Text Messaging'
header_label_text = f'{Company.name}: '
header_text = f'{Company.name}: '
logo = './images/logo.png'
TEST_MODE = False
ORIGIN = 'MASS_CAMPAIGN'
art = rf"""
   ___ __  __ ___    ___   _   __  __ ___  _   ___ ___ _  _ ___
  / __|  \/  / __|  / __| /_\ |  \/  | _ \/_\ |_ _/ __| \| / __|
  \__ | |\/| \__ \ | (__ / _ \| |\/| |  _/ _ \ | | (_ | .` \__ \
  |___|_|  |_|___/  \___/_/ \_|_|  |_|_|/_/ \_|___\___|_|\_|___/

  Version: {version}
"""
print(art)


def is_test() -> bool:
    return test_mode_checkbox_state.get() == 1


def get_input_text() -> str:
    return message_box.get('1.0', END).strip()


def get_media_url() -> str:
    return photo_input.get() if photo_checkbutton_used() else None


def get_campaign_name() -> str:
    return f'{datetime.now():%Y-%m-%d %H:%M:%S}'


def send_twilio_text(cust_txt: Text, client: Client):
    try:
        if cust_txt.media_url:
            response = client.messages.create(
                from_=Twilio.phone_number,
                media_url=[cust_txt.media_url],
                to=cust_txt.phone,
                body=cust_txt.custom_message,
            )
        else:
            response = client.messages.create(
                from_=Twilio.phone_number, to=cust_txt.phone, body=cust_txt.custom_message
            )
    # Catch Errors
    except twilio.base.exceptions.TwilioRestException as err:
        logger.error(f'Twilio Error: {err.code} - {err.msg} - {cust_txt.phone} - {cust_txt.custom_message}')
        cust_txt.response_code = err.code
        cust_txt.response_text = err.msg

        if err.code == 21614:
            Database.SMS.move_phone_to_landline(cust_txt)

        elif err.code == 21610:  # Previously unsubscribed
            Database.SMS.unsubscribe(cust_txt)

    return response


class MessageSender:
    def __init__(self, campaign: Campaign):
        self.client = Client(Twilio.sid, Twilio.token)
        self.campaign: Campaign = campaign
        self.success_count: int = 0  # Successful messages
        self.count: int = 0  # All message attempts
        self.completed_message: str = ''

    def send_texts(self):
        def send_helper(cust_txt: Text):
            print(f'Sending to {cust_txt.phone}')

            if self.campaign.test_mode:
                cust_txt.sid = 'TEST'
                self.success_count += 1
            else:
                try:
                    response = send_twilio_text(cust_txt, self.client)
                except Exception as err:
                    logger.error(f'General Error: {tb()}')
                    cust_txt.response_text = str(err)
                else:
                    cust_txt.sid = response.sid
                    self.success_count += 1

            self.count += 1
            cust_txt.count = f'{self.count}/{self.campaign.customers.total_messages}'
            Database.SMS.insert(cust_txt)

        progress_bar.place(x=30, y=100, width=200)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []

            for i, text in enumerate(self.campaign.texts):
                print(text)
                progress.set(i / len(self.campaign.texts) * 100)
                futures.append(executor.submit(send_helper, text))

                # Rate limit to 20 tasks per second
                if (i + 1) % 20 == 0:
                    time.sleep(1)

            # Wait for all futures to complete
            concurrent.futures.wait(futures)

            self.completed_message = (
                f'Process complete!\n'
                f'{self.success_count} messages sent. \n'
                f'{self.campaign.customers.total_messages - self.success_count} messages failed.'
            )


csv_customers = None


def get_customers() -> Customers:
    # ----------GET DATA FROM SQL------------#
    if segment_checkbutton_used() == 1:
        segment = listbox.get(listbox.curselection())
        sql_query = segment_dict[segment]
        customers: Customers = Database.get_customers(sql_query)
        if not customers:
            messagebox.showerror(title='Error!', message='There was an error with the SQL query. Please try again.')
            return

        return customers

    # ------------------OR-------------------#

    # -------GET DATA FROM CSV---------#
    elif csv_checkbutton_used() == 1:
        return select_file()

    # ----------DATA FOR SINGLE PHONE---------#
    elif single_number_checkbutton_used() == 1:
        return Customers(
            [
                {
                    'CUST_NO': None,
                    'NAM': None,
                    'CUST_NAM_TYP': None,
                    'PHONE_1': single_number_input.get(),
                    'CONTCT_2': None,
                    'PHONE_2': None,
                    'LOY_PTS_BAL': None,
                    'CATEG_COD': None,
                }
            ]
        )


def select_file() -> Customers:
    """File Selector for importing CSVs"""
    filetypes = (('csv files', '*.csv'), ('All files', '*.*'))

    cp_data = filedialog.askopenfilename(
        title='Open a CSV', initialdir=f'{os.path.expanduser('~')}/Desktop', filetypes=filetypes
    )

    # Read file
    csv_data = pandas.read_csv(cp_data)

    # Show first person's info
    try:
        csv_customers: Customers = Customers(csv_data.to_dict('records'))

        preview = Campaign(is_test(), 'Preview', get_input_text(), csv_customers, get_media_url())
        print(preview)

        show_customer: Customer = csv_customers.list[0]
        message = f"""
        First Entry:
        Name: {show_customer.name}
        Type: {show_customer.type}
        Phone 1: {show_customer.phone_1}
        Contact 2: {show_customer.contact_2}
        Phone 2: {show_customer.phone_2}
        Loyalty Points: {show_customer.points}
        Category Code: {show_customer.category}
        Total messages to send: {csv_customers.total_messages}
        """

        showinfo(title='Selected File', message=message)

        return csv_customers

    # Show Error If CSV doesn't include Name and Phone
    except TypeError as e:
        logger.error(f'Error in select_file: {e} {tb()}')
        showinfo(
            title='Selected File',
            message='Invalid File. CSV to contain CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD',
        )


def segment_length():
    """Calculate the number of messages to be sent"""
    try:
        segment = listbox.get(listbox.curselection())
        sql_query = segment_dict[segment]
        customers: Customers = Database.get_customers(sql_query)
        preview = Campaign(is_test(), get_campaign_name(), get_input_text(), customers, get_media_url())
        print(preview)
        if customers.total_messages < 1:
            list_size.config(text='List is empty.')

        elif customers.total_messages == 1:
            # Because, grammar.
            list_size.config(text=f'{customers.total_messages} message will be sent.')
        else:
            list_size.config(text=f'{customers.total_messages} messages will be sent.')

    except tkinter.TclError:
        list_size.config(text='Please select an option')


def validate(input_text: str, media_url: str):
    """Validate the input before sending"""
    if not input_text and not media_url:
        # If there is no message or photo, show an error
        logger.error('No message or photo entered. Cannot send.')
        messagebox.showerror(title='Error', message='Please enter a message to send.')
        return False
    if not input_text and media_url:
        # If there is no message, but there is a photo, ask if they want to continue
        logger.warning('No message entered, but photo link present.')
        if not messagebox.askyesno(
            title='Warning', message='You have not entered a message. Do you want to continue?'
        ):
            return False
    return True


def send_text():
    customers = get_customers()
    input_text = get_input_text()
    message_script = header_text + input_text
    media_url = get_media_url()

    if not validate(input_text, media_url):
        return

    campaign = Campaign(is_test(), get_campaign_name(), message_script, customers, media_url)
    sender = MessageSender(campaign)

    def send_text_thread():
        try:
            sender.send_texts()

        except Exception as e:
            logger.error(f'Error in send_text_thread: {e} {tb()}')
            messagebox.showerror(
                title='Error', message='An error occurred while sending texts. Please check the log.'
            )

        else:
            # Remove the progress bar
            progress_bar.place_forget()

            # Show a message box when the process is complete
            messagebox.showinfo(title='Completed', message=sender.completed_message)

    try:
        threading.Thread(target=send_text_thread).start()
    except KeyboardInterrupt:
        sys.exit()


# ---------------------------- UI SETUP ------------------------------- #
window = tkinter.Tk()
window.title(application_title)
window.config(padx=30, pady=10, background=BACKGROUND_COLOR)


def center_window(width=400, height=760):
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


def view_log():
    subprocess.Popen(f'explorer /open, {Logs.sms}')


canvas = tkinter.Canvas(
    width=350, height=172, background=BACKGROUND_COLOR, highlightcolor=BACKGROUND_COLOR, highlightthickness=0
)

# logo = tkinter.PhotoImage(file=logo)

# canvas.create_image(175, 86, image=logo)
# canvas.grid(column=0, row=0, pady=3, columnspan=3)

# SMS Text Messaging Sub Title
website_label = tkinter.Label(
    text='Create Campaign', font=('Arial', 12), fg=MEDIUM_DARK_GREEN, background=BACKGROUND_COLOR
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
    background=BACKGROUND_COLOR,
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
    background=BACKGROUND_COLOR,
)
csv_checkbox_state.get()
csv_checkbox.grid(column=0, row=4, columnspan=3, pady=0)

# File open dialog
open_csv_file_button = tkinter.Button(
    text='Import CSV', font=('Arial', 10), command=select_file, highlightbackground=BACKGROUND_COLOR
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
    background=BACKGROUND_COLOR,
)
segment_checkbox_state.get()
segment_checkbox.grid(column=0, row=6, columnspan=3, pady=3)

# Create Listbox with Choices
listbox = Listbox(
    height=6, width=25, highlightcolor='green', exportselection=False, font=('Arial', 10), justify='center'
)
segment_dict = {
    'SMS Test Group': queries.test_group_1,
    'Wholesale Customers': queries.wholesale_all,
    'Retail Customers: All': queries.retail_all,
    'Retail Most Recent 1000': queries.retail_recent_1000,
    'Retail Most Recent 2000': queries.retail_recent_2000,
    'Retail Most Recent 3000': queries.retail_recent_3000,
    'Retail Most Recent 4000': queries.retail_recent_4000,
    'No Purchases: 6 Months': queries.no_purchases_6_months,
    'No Purchases: 12 Months': queries.no_purchases_12_months,
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
    background=BACKGROUND_COLOR,
    highlightbackground=BACKGROUND_COLOR,
)
calculate_size_button.config(state='disabled')
calculate_size_button.grid(row=8, column=0, columnspan=3, pady=5)

list_size = tkinter.Label(text='', font=('Arial', 9), fg=MEDIUM_GREEN, background=BACKGROUND_COLOR)
list_size.grid(column=0, row=9, columnspan=3, pady=2)

# Header Text Label
header_text_label = tkinter.Label(
    text='Header Text', font=('Arial', 9), fg=MEDIUM_DARK_GREEN, background=BACKGROUND_COLOR
)
header_text_label.grid(column=0, row=10, columnspan=3, pady=0)

# Header Label
header_text_label = tkinter.Label(text=header_label_text, font=('Arial', 10), background=BACKGROUND_COLOR)
header_text_label.grid(column=0, row=11, columnspan=3, pady=0)

# Message Box
message_label = tkinter.Label(
    text='Message: ', font=('Arial', 10), fg=MEDIUM_DARK_GREEN, background=BACKGROUND_COLOR
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
user_label = tkinter.Label(text='Message Length: 20', font=('Arial', 12), background=BACKGROUND_COLOR)
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
    background=BACKGROUND_COLOR,
)
checked_state.get()
picture_checkbox.grid(column=0, row=15, columnspan=3, pady=10)
photo_link_help_text = tkinter.Label(
    text='Must be a publicly visible link.',
    state='disabled',
    font=('Arial', 10, 'italic'),
    fg='grey',
    background=BACKGROUND_COLOR,
)
photo_link_help_text.grid(column=0, row=16, columnspan=3, pady=0)

# Photo Link
photo_input = tkinter.Entry(width=48, justify='center')
photo_input.insert('0', string='Replace with link to Photo')
photo_input.config(state='disabled')
photo_input.grid(row=17, column=0, columnspan=3, pady=10)

# Send Button
send_button = tkinter.Button(
    text='Send', command=send_text, font=('Arial', 14), fg=DARK_GREEN, highlightbackground=BACKGROUND_COLOR
)
send_button.grid(row=18, column=0, columnspan=3, pady=5)

# Test Mode Checkbox
test_mode_checkbox_state = IntVar()
test_mode_checkbox = Checkbutton(
    text='Test Mode',
    font=('Arial', 10),
    variable=test_mode_checkbox_state,
    command=is_test,
    fg='black',
    background=BACKGROUND_COLOR,
)
test_mode_checkbox_state.get()
test_mode_checkbox.grid(column=0, row=19, columnspan=1, pady=0)

# View Log
log_button = tkinter.Button(
    text='View Log', command=view_log, font=('Arial', 10), highlightbackground=BACKGROUND_COLOR
)
log_button.grid(row=19, column=1, columnspan=1, pady=3)


progress = tkinter.IntVar()
progress_bar = ttk.Progressbar(variable=progress, maximum=100, mode='determinate')


# Version Number
header_text_label = tkinter.Label(
    text=f'      Version {version}', font=('Arial', 9), fg=MEDIUM_DARK_GREEN, background=BACKGROUND_COLOR
)
header_text_label.grid(column=2, row=19, columnspan=1, pady=0)

redir = WidgetRedirector(message_box)
original_insert = redir.register('insert', my_insert)
original_delete = redir.register('delete', my_delete)
original_replace = redir.register('replace', my_replace)

window.mainloop()
