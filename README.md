# Project Documentation
Author: Alex Powell
## Overview

This project is a Python-based SMS messaging application that allows users to send custom messages to different customer segments. The application uses the Twilio API for sending SMS messages and pyodbc for interacting with a SQL Server database.

## Dependencies

- Python
- pyodbc
- pandas
- tkinter
- twilio

## Files

- `main.py`: This is the main script that runs the application. It contains the GUI setup and the logic for sending SMS messages.
- `queries.py`: This file contains SQL queries that are used to fetch customer data from the database.
- `creds.py`: This file contains sensitive information such as database credentials and Twilio API keys.
- `custom.py`: This file contains custom configurations for the application.

## Features

- **Customer Segmentation**: The application allows users to send messages to different customer segments. The segments are defined in the `queries.py` file.
- **Custom Messages**: Users can create custom messages with placeholders for customer name and reward balance.
- **CSV Import**: Users can import a CSV file with customer data to send messages to.
- **Single Phone Number Messaging**: Users can send a message to a single phone number.
- **Test Mode**: Users can enable test mode to run the application without actually sending messages.
- **Log Viewing**: Users can view a log of sent messages.

## Usage

1. Run the `main.py` script to start the application.
2. Choose one of the options to select the recipients of the message:
   - Single Phone Number: Enter a phone number in the input field.
   - Use .csv File: Click the 'Import CSV' button and select a CSV file with customer data.
   - Use Customer Segment: Select a customer segment from the dropdown.
3. Enter your message in the 'Message' text box. You can use `{name}` and `{rewards}` as placeholders for the customer's name and reward balance respectively.
4. If you want to include a picture in the message, check the 'Include Picture Link?' checkbox and enter the URL of the picture in the input field.
5. Click the 'Send' button to send the messages.
6. You can view a log of sent messages by clicking the 'View Log' button.

## Note

Please ensure that you have the necessary permissions to send SMS messages and access the database. Also, make sure that your Twilio account is properly set up and funded.
