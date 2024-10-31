from datetime import datetime, date
from dateutil.relativedelta import relativedelta

now = datetime.now()

# ----------DATE PRESETS------------#
one_day_ago = date.today() + relativedelta(days=-1)
five_day_ago = date.today() + relativedelta(days=-5)
one_week_ago = date.today() + relativedelta(weeks=-1)
one_month_ago = date.today() + relativedelta(months=-1)
six_months_ago = date.today() + relativedelta(months=-6)
one_year_ago = date.today() + relativedelta(years=-1)
two_year_ago = date.today() + relativedelta(years=-2)

standard_filter = """
((SMS_1_IS_SUB = 'Y' AND PHONE_1 IS NOT NULL) or (SMS_2_IS_SUB = 'Y' and PHONE_2 IS NOT NULL))
"""

# SMS Test Group
test_group_1 = """
SELECT CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE IS_SMS_TESTER = 'Y'
"""

# All Retail Customers
retail_all = f"""
SELECT CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
"""
# All Wholesale Customers
wholesale_all = f"""
SELECT CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'WHOLESALE' AND 
{standard_filter}
"""

# Selects Most Recent Customers
retail_recent_1000 = f"""
SELECT TOP 1000 CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
retail_recent_2000 = f"""
SELECT TOP 2000 CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
retail_recent_3000 = f"""
SELECT TOP 3000 CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
retail_recent_4000 = f"""
SELECT TOP 4000 CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""

# Customers Who Have Not Made A Purchase In A Year
no_purchases_12_months = f"""
SELECT CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE FST_NAM != 'Change' AND FST_NAM IS NOT NULL AND PHONE_1 IS NOT NULL 
AND LST_SAL_DAT < '{one_year_ago} 00:00:00' AND {standard_filter}
"""
# Customers Who Have Not Made A Purchase In Six Months
no_purchases_6_months = f"""
SELECT CUST_NO, CUST_NAM_TYP, NAM, PHONE_1, CONTCT_2, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE FST_NAM != 'Change' AND FST_NAM IS NOT NULL AND PHONE_1 IS NOT NULL 
AND LST_SAL_DAT < '{six_months_ago} 00:00:00' AND {standard_filter}
"""
