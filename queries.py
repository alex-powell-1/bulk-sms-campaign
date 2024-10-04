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
(SMS_1_IS_SUB = 'Y' AND PHONE_1 IS NOT NULL) or (SMS_2_IS_SUB = 'Y' and PHONE_2 IS NOT NULL)
"""

# Alex Powell Only
test_group_1 = """
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PHONE_1 = '828-234-1265'
"""
# Alex Powell, Brandon Settlemyre, Michelle Settlemyre, Beth Lane
test_group_2 = """
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PHONE_1 = '828-234-1265' OR PHONE_1 = '828-390-8030' OR PHONE_1 = '828-403-3317' OR PHONE_1 = '704-488-8239'
"""
# All Retail Customers
retail_all = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
"""
# All Wholesale Customers
wholesale_all = f"""
SELECT CUST_NO, (FST_NAM + ' ' + LST_NAM) as NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'WHOLESALE' AND 
{standard_filter}
"""

# Selects Most Recent Customers
retail_recent_1000 = f"""
SELECT TOP 1000 CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
retail_recent_2000 = f"""
SELECT TOP 2000 CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
retail_recent_3000 = f"""
SELECT TOP 3000 CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
retail_recent_4000 = f"""
SELECT TOP 4000 CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE CATEG_COD = 'RETAIL' AND 
{standard_filter}
ORDER BY LST_SAL_DAT DESC
"""
# Anyone Who Have Purchased Spring Annuals Over The Past Two Years
spring_annual_shoppers = f"""
SELECT
"VI_PS_TKT_HIST"."CUST_NO", "AR_CUST"."NAM", "AR_CUST"."PHONE_1", "AR_CUST"."PHONE_2", "AR_CUST"."LOY_PTS_BAL", "AR_CUST"."CATEG_COD"
FROM
  (("Settlemyre"."dbo"."VI_PS_TKT_HIST" "VI_PS_TKT_HIST"
LEFT OUTER JOIN
  "Settlemyre"."dbo"."AR_CUST" "AR_CUST"
ON
  "VI_PS_TKT_HIST"."CUST_NO"="AR_CUST"."CUST_NO") 
INNER JOIN
  "Settlemyre"."dbo"."VI_PS_TKT_HIST_LIN" "VI_PS_TKT_HIST_LIN"
ON
  ("VI_PS_TKT_HIST"."BUS_DAT"="VI_PS_TKT_HIST_LIN"."BUS_DAT") AND ("VI_PS_TKT_HIST"."DOC_ID"="VI_PS_TKT_HIST_LIN"."DOC_ID"))
LEFT OUTER JOIN
  "Settlemyre"."dbo"."IM_ITEM" "IM_ITEM"
ON
  "VI_PS_TKT_HIST_LIN"."ITEM_NO"="IM_ITEM"."ITEM_NO"
WHERE
 "IM_ITEM"."ITEM_NO"='45' and (VI_PS_TKT_HIST_LIN.TKT_DAT between '{two_year_ago}-03-01 00:00:00' and 
 '{two_year_ago}-5-31 00:00:00' or VI_PS_TKT_HIST_LIN.TKT_DAT between '{one_year_ago}-03-01 00:00:00' and 
 '{one_year_ago}-5-31 00:00:00') AND 
{standard_filter}

ORDER BY
  VI_PS_TKT_HIST.TKT_DAT DESC
"""
# Anyone Who Have Purchased Fall Mums Over The Past Two Years
fall_mum_shoppers = f"""
SELECT
"VI_PS_TKT_HIST"."CUST_NO", "AR_CUST"."NAM", "AR_CUST"."PHONE_1", "AR_CUST"."PHONE_2", "AR_CUST"."LOY_PTS_BAL", "AR_CUST"."CATEG_COD"
FROM
  (("Settlemyre"."dbo"."VI_PS_TKT_HIST" "VI_PS_TKT_HIST"
LEFT OUTER JOIN
  "Settlemyre"."dbo"."AR_CUST" "AR_CUST"
ON
  "VI_PS_TKT_HIST"."CUST_NO"="AR_CUST"."CUST_NO") 
INNER JOIN
  "Settlemyre"."dbo"."VI_PS_TKT_HIST_LIN" "VI_PS_TKT_HIST_LIN"
ON
  ("VI_PS_TKT_HIST"."BUS_DAT"="VI_PS_TKT_HIST_LIN"."BUS_DAT") AND ("VI_PS_TKT_HIST"."DOC_ID"="VI_PS_TKT_HIST_LIN"."DOC_ID"))
LEFT OUTER JOIN
  "Settlemyre"."dbo"."IM_ITEM" "IM_ITEM"
ON
  "VI_PS_TKT_HIST_LIN"."ITEM_NO"="IM_ITEM"."ITEM_NO"
WHERE
 "IM_ITEM"."SUBCAT_COD"='MUM' and (VI_PS_TKT_HIST_LIN.TKT_DAT between '{two_year_ago}-08-01 00:00:00' and 
 '{two_year_ago}-11-15 00:00:00' or VI_PS_TKT_HIST_LIN.TKT_DAT between '{one_year_ago}-08-01 00:00:00' and 
 '{one_year_ago}-11-15 00:00:00') and {standard_filter}
ORDER BY
  VI_PS_TKT_HIST.TKT_DAT DESC
"""
# Anyone Who Have Purchased Christmas Items Over The Past Two Years
christmas_shoppers = f"""
SELECT
"VI_PS_TKT_HIST"."CUST_NO", "AR_CUST"."NAM", "AR_CUST"."PHONE_1", "AR_CUST"."PHONE_2", "AR_CUST"."LOY_PTS_BAL", "AR_CUST"."CATEG_COD"
FROM
  (("Settlemyre"."dbo"."VI_PS_TKT_HIST" "VI_PS_TKT_HIST"
LEFT OUTER JOIN
  "Settlemyre"."dbo"."AR_CUST" "AR_CUST"
ON
  "VI_PS_TKT_HIST"."CUST_NO"="AR_CUST"."CUST_NO") 
INNER JOIN
  "Settlemyre"."dbo"."VI_PS_TKT_HIST_LIN" "VI_PS_TKT_HIST_LIN"
ON
  ("VI_PS_TKT_HIST"."BUS_DAT"="VI_PS_TKT_HIST_LIN"."BUS_DAT") AND ("VI_PS_TKT_HIST"."DOC_ID"="VI_PS_TKT_HIST_LIN"."DOC_ID"))
LEFT OUTER JOIN
  "Settlemyre"."dbo"."IM_ITEM" "IM_ITEM"
ON
  "VI_PS_TKT_HIST_LIN"."ITEM_NO"="IM_ITEM"."ITEM_NO"
WHERE
 "IM_ITEM"."CATEG_COD"='Christmas' and VI_PS_TKT_HIST_LIN.TKT_DAT between '{two_year_ago}-11-15 00:00:00' and 
 '{one_year_ago}-12-25 00:00:00' and {standard_filter}
ORDER BY
  VI_PS_TKT_HIST.TKT_DAT DESC
"""
# Customers Who Have Not Made A Purchase In A Year
no_purchases_12_months = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE FST_NAM != 'Change' AND FST_NAM IS NOT NULL AND PHONE_1 IS NOT NULL 
AND LST_SAL_DAT < '{one_year_ago} 00:00:00' AND {standard_filter}
"""
# Customers Who Have Not Made A Purchase In Six Months
no_purchases_6_months = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE FST_NAM != 'Change' AND FST_NAM IS NOT NULL AND PHONE_1 IS NOT NULL 
AND LST_SAL_DAT < '{six_months_ago} 00:00:00' AND {standard_filter}
"""

yesterday_purchases = f"""
SELECT CUST_NO, BILL_NAM, BILL_PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM VI_PS_TKT_HIST
WHERE BILL_FST_NAM != 'Change' AND BILL_FST_NAM IS NOT NULL AND BILL_PHONE_1 IS NOT NULL AND 
TKT_DAT = '{one_day_ago} 00:00:00'
"""

five_days_ago_purchases = f"""
SELECT CUST_NO, BILL_NAM, BILL_PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM VI_PS_TKT_HIST
WHERE BILL_FST_NAM != 'Change' AND BILL_FST_NAM IS NOT NULL AND BILL_PHONE_1 IS NOT NULL AND 
TKT_DAT = '{five_day_ago} 00:00:00'
"""

one_week_ago_purchases = f"""
SELECT CUST_NO, BILL_NAM, BILL_PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM VI_PS_TKT_HIST
WHERE BILL_FST_NAM != 'Change' AND BILL_FST_NAM IS NOT NULL AND BILL_PHONE_1 IS NOT NULL AND 
TKT_DAT = '{one_week_ago} 00:00:00'
"""
# Birthday Queries
january_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '1' AND 
{standard_filter}
"""

february_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '2' AND 
{standard_filter}
"""

march_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '3' AND 
{standard_filter}
"""

april_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '4' AND 
{standard_filter}
"""

may_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '5' AND 
{standard_filter}
"""

june_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '6' AND 
{standard_filter}
"""
july_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '7' AND 
{standard_filter}
"""

august_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '8' AND 
{standard_filter}
"""

september_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '9' AND 
{standard_filter}
"""

october_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '10' AND 
{standard_filter}
"""

november_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '11' AND 
{standard_filter}
"""

december_bday = f"""
SELECT CUST_NO, NAM, PHONE_1, PHONE_2, LOY_PTS_BAL, CATEG_COD
FROM AR_CUST
WHERE PROF_COD_4 = 'Y' AND PROF_COD_2 = '12' AND 
{standard_filter}
"""
