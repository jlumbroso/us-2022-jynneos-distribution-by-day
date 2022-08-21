import datetime
import locale
import re
import typing

import bs4
import html2csv
import pytz
import requests
import waybackpy

#
TIMEZONE = pytz.timezone("US/Eastern")


# Characters to strip from numeric values
STRIP_NUMERIC_CHARS = "*\u200b"

# This will allow us to parse the numeric strings "1,234.00" from the scraped data.
locale.setlocale(locale.LC_NUMERIC, "en_US.UTF-8")


def get_tables_from_html(html: str) -> typing.List[typing.List[typing.List[str]]]:
    """
    Returns a list of parsed Python tables (lists of lists) from input HTML.

    :param html: HTML source code to parse
    :type html: str
    :return: A list of parsed Python tables (lists of lists) from input HTML
    :rtype: typing.List[typing.List[typing.List[str]]]
    """
    # NOTE: taken from html2csv library, because it currently outputs only
    # directly to the CSV format, whereas here, we need a Python object. Should
    # switch to using html2csv if pull request is accepted:
    # https://github.com/hanwentao/html2csv/pull/10

    soup = bs4.BeautifulSoup(html, "html.parser")
    tables = []
    for table_element in soup.find_all("table"):
        table = []
        for tr in table_element.find_all("tr"):
            row = ["".join(cell.stripped_strings) for cell in tr.find_all(["td", "th"])]
            table.append(row)
        tables.append(table)

    return tables


def convert_if_numeric(s: str) -> typing.Union[str, int]:
    """
    Returns a numeric version of the string if it is numeric, otherwise
    the original string.

    :param s: The string to convert.
    :type s: str
    :return: Either an integer or a string.
    :rtype: typing.Union[str, int]
    """
    try:
        stripped_s = re.sub("[\s*\u200b]+", "", s).strip(STRIP_NUMERIC_CHARS).strip()
        return locale.atoi(stripped_s)
    except ValueError:
        return s.strip()


def make_table_numeric(
    list_of_lists: typing.List[typing.List[str]],
) -> typing.List[typing.List[typing.Union[str, int]]]:
    """
    Returns a version of the table in which all numeric values have been
    converted to integers.

    :param list_of_lists: The table to convert
    :type list_of_lists: typing.List[typing.List[str]]
    :return: A version of the input table in which all numeric values have been converted to integers
    :rtype: typing.List[typing.List[typing.Union[str, int]]]
    """

    convd_list_of_lists = [
        [convert_if_numeric(cell) for cell in row] for row in list_of_lists
    ]

    return convd_list_of_lists


##


def time_now() -> datetime.datetime:
    return datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %I:%M%p")


def prev_day(year: int, month: int, day: int) -> typing.Tuple[int, int, int]:

    try:
        date = datetime.datetime(year=year, month=month, day=day)
    except ValueError:
        return

    date += datetime.timedelta(hours=-24)
    return (date.year, date.month, date.day)


def next_day(year: int, month: int, day: int) -> typing.Tuple[int, int, int]:

    try:
        date = datetime.datetime(year=year, month=month, day=day)
    except ValueError:
        return

    date += datetime.timedelta(hours=24)
    return (date.year, date.month, date.day)


def in_future(year: int, month: int, day: int) -> bool:

    try:
        date = datetime.datetime(year=year, month=month, day=day, tzinfo=TIMEZONE)
    except ValueError:
        return False

    return date > datetime.datetime.now(TIMEZONE)
