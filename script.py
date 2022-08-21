import copy
import datetime
import json
import os
import pathlib
import typing

import pytz
import requests

import helpers
import jynneos

WAYBACK_START = (2022, 7, 1)


def scrape_waybackpy(start=None, postprocess=True):
    start = start or WAYBACK_START
    year, month, day = start
    prev_data = None

    data = dict()

    while not helpers.in_future(year, month, day):
        new_data = jynneos.fetch_jynneos_table_near(year, month, day)

        if prev_data is None or [i for i in new_data if i not in prev_data] != []:
            for data_entry in new_data:
                data_key = data_entry.get(jynneos.KEY, "").strip()
                if data_key == "":
                    continue
                for key, value in data_entry.items():
                    if key == jynneos.KEY:
                        continue
                    data[data_key] = data.get(data_key, dict())
                    data[data_key][
                        "{} ({}-{:02}-{:02})".format(key, year, month, day)
                    ] = value

        year, month, day = helpers.next_day(year, month, day)
        prev_data = new_data

    new_data = jynneos.fetch_jynneos_table_now()
    if prev_data is None or [i for i in new_data if i not in prev_data] != []:
        for data_entry in new_data:
            data_key = data_entry.get(jynneos.KEY, "").strip()
            if data_key == "":
                continue

            for key, value in data_entry.items():
                if key == jynneos.KEY:
                    continue
                data[data_key] = data.get(data_key, dict())
                data[data_key][
                    "{} ({}-{:02}-{:02})".format(key, year, month, day)
                ] = value

    # post-process the data
    if postprocess:
        data = jynneos.post_process_jynneos_longitudinal_data(data)

    return data


# output something in "./data"
