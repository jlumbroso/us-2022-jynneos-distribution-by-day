import locale
import re
import typing

import bs4
import html2csv
import pytz
import requests
import waybackpy

import helpers

# User agent
USER_AGENT = (
    "Jynneos scraper [https://github.com/jlumbroso/us-2022-jynneos-distribution-by-day]"
)

# URL to the page containing the data we want to scrape
BASE_URL_JYNNEOS_US_DISTRIB = "https://aspr.hhs.gov/SNS/Pages/JYNNEOS-Distribution.aspx"

# Key name used for the table
KEY = "Jurisdiction"

# Substitutions for the column names
SUBSTITUTIONS_COLUMNS = {
    "Allocation 2022-06-29 To 2022-07-08": "Allocation 2022-06-29 to 2022-07-08",
    "Allocation 2022-07-08 To 2022-07-15": "Allocation 2022-07-08 to 2022-07-15",
    "Allocation 2022-07-16 To 2022-07-29": "Allocation 2022-07-16 to 2022-07-29",
    "Allocation 2022-07-29 To Onwards": "Allocation 2022-07-29 to onwards",
    "Allocation July 29": "Allocation 2022-07-29 to onwards",
    "AllocationJune 28-July 27": "Allocation 2022-06-28 to 2022-07-27",
    "Jurisdiction": "Jurisdiction",
    "Total    Allocation": "Total allocation",
    "Total Allocation": "Total allocation",
    "Total Distribution": "Total distribution",
    "Total Distribution (Doses)\u200b": "Total distribution",
    "Total Doses    Shipped or Deployedas of July 27, 8AM\u200b": "Total shipped as of 2022-07-27",
    "Total Requested": "Total requested",
    "Total Requested as of July 27 at 8AM": "Total requested as of 2022-07-27",
    "Total Requestedas of Aug 03 2022, 12pm": "Total requested as of 2022-08-03",
    "Total Requestedas of Aug 08 2022, 12pm": "Total requested as of 2022-08-08",
    "Total Requestedas of Aug 10 2022, 12pm": "Total requested as of 2022-08-10",
    "Total Requestedas of Aug 12\u200b 2022, 12pm": "Total requested as of 2022-08-12",
    "Total Shippedas of Aug 03 2022, 12pm": "Total shipped as of 2022-08-03",
    "Total Shippedas of Aug 08 2022, 12pm": "Total shipped as of 2022-08-08",
    "Total Shippedas of Aug 10 2022, 12pm": "Total shipped as of 2022-08-10",
    "Total Shippedas of Aug 12 2022, 12\u200bpm": "Total shipped as of 2022-08-12",
    "Total Shipped\xa0(Doses)\u200b": "Total shipped",
}

# Substitutions for the jurisdiction names
SUBSTITUTIONS_JURISDICTION = {
    "California": "California",
    "California - Los Angeles": "Los Angeles",
    "California - Other": "California",
    "Illinois": "Illinois",
    "Illinois - Chicago": "Chicago",
    "Illinois - Other": "Illinois",
    "New York": "New York",
    "New York - New York City": "New York City",
    "New York - Other": "New York",
    "New York City": "New York City",
    "New York- New York City": "New York City",
    "Pennsylvania": "Pennsylvania",
    "Pennsylvania - Other": "Pennsylvania",
    "Pennsylvania - Philadelphia": "Philadelphia",
    "Philadelphia": "Philadelphia",
    "Philadelphia - Other": "Pennsylvania",
    "Texas": "Texas",
    "Texas - Houston": "Houston",
    "Texas - Other": "Texas",
    "Tribal Entities": "Tribal entities",
    "Tribal entities": "Tribal entities",
}


def normalize_jynneos_table_data(
    table_data: typing.List[typing.Dict[str, str]]
) -> typing.List[typing.Dict[str, str]]:

    # Normalize the name of the jurisdictions (remove extraneous spacing)

    def norm_comp(s1, s2):
        return (
            re.sub(r"[\s\u200b*]+", "", s1).lower()
            == re.sub(r"[\s\u200b*]+", "", s2).lower()
        )

    for rowdata in table_data:

        # clean up the jurisdiction name
        if KEY in rowdata:
            keyname = rowdata[KEY]
            keyname = re.sub(r"[\s\u200b*]+", " ", keyname).strip()
            for old, new in SUBSTITUTIONS_JURISDICTION.items():
                if norm_comp(old, keyname):
                    keyname = new
                    break
            rowdata[KEY] = keyname

    return table_data


def parse_jynneos_table_data(
    html: typing.Union[str, bytes]
) -> typing.List[typing.List[str]]:
    s = bs4.BeautifulSoup(html, features="html.parser")

    table_element = s.find("div", {"class": "table-responsive"}).find("table")
    if table_element is None:
        return

    raw_tables = helpers.get_tables_from_html(str(table_element))

    # should always be false since table_element is not None
    assert len(raw_tables) > 0

    raw_table = raw_tables[0]
    num_table = helpers.make_table_numeric(raw_table)

    header_row = num_table[0]
    body_rows = num_table[1:]

    entries = [dict(zip(header_row, row)) for row in body_rows]

    # clean entries
    for entry in entries:

        # normalize the "All Jurisdiction" caption
        if "all " in entry["Jurisdiction"].lower():
            entry["Jurisdiction"] = "All"

        # substitute some key names
        for old, new in SUBSTITUTIONS_COLUMNS.items():
            if old == new:
                continue
            if old in entry:
                entry[new] = entry[old]
                del entry[old]

    # normalize the table data
    normalized_entries = normalize_jynneos_table_data(entries)

    return normalized_entries


def fetch_jynneos_table_near(year, month, day):

    # Use the Wayback Machine through the excellent waybackpy library to
    # get a past version of the webpage

    archive = waybackpy.WaybackMachineCDXServerAPI(
        url=BASE_URL_JYNNEOS_US_DISTRIB,
        user_agent=USER_AGENT,
    )

    near = archive.near(year=year, month=month, day=day)

    r = requests.get(near.archive_url)

    entries = parse_jynneos_table_data(r.content)

    return entries


def post_process_jynneos_longitudinal_data(table_data):
    def clean_key(key):
        tokens = key.split("(", 1)
        if len(tokens) != 2:
            return key

        ts = tokens[1].strip(" ()")
        year, month, day = ts.split("-")

        return ts

    cleaned_table_data = {
        rowkey: {
            clean_key(key): value
            for key, value in rowdata.items()
            if "total" in key.lower()
            and (
                "deployed" in key.lower()
                or "shipped" in key.lower()
                or "distribution" in key.lower()
            )
        }
        for rowkey, rowdata in table_data.items()
    }

    return cleaned_table_data
