SMS Campaigns

Author: Alex Powell

This cross platform Tkinter/Python application queries a Counterpoint POS associated SQL database for customer data and sends programmatic text (through Twilio API) based on 1) single phone number entry or 2) .csv upload or 3) customer data.

The application can send standard SMS messages or MMS with pictures.

CLIVersion.py allows for running from bat file on schedule.

If the application receives an API response that the number is actually a landline, it will automatically move the customer's phone number over to the established landline field in SQL. In this regard, the application helps clean the database.

GUI Contact Selection Methods:

1) Single Phone - just enter a single phone number and it will send it directly to this number

2) .csv upload - select a csv file with the following four columns 1)CUST_NO, FST_NAM, PHONE_1, LOY_PTS_BAL

LOY_PTS_BAL is a balance of reward points

3) Customer Segment

Currently, texts can be sent for several segments, including:

Management Test Group
Wholesale Customers
Retail Customers: All
Yesterday's Shoppers
5 Day follow-up
1 week follow-up
Retail: Most recent 1000 customers
Retail: Most recent 2000 customers
Retail: Most recent 3000 customers
Retail: Most recent 4000 customers
Spring Annual Shoppers
Fall Mum Shoppers
Christmas Shoppers
No purchases in 6 months
No purchases in 12 months
By Birthday Month

The application logs the sent message history to a desired path.

The application has a test mode that allows you to run the process without actually sending the messages through the API so you can check recipients in log before sending.
