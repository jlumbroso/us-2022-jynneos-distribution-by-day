import copy
import datetime
import json
import os
import pathlib
import typing

import helpers
import jynneos

DATA_FILE = "data/index.json"


class Storage:
    def __init__(self, filename=None, data=None):
        self._data = dict()
        self._filename = None

        if data is not None:
            self._data = copy.deepcopy(data)

        if filename is not None:
            self.load(filename)

    def load(self, filename=None):
        filename = filename or self._filename
        if filename is None:
            raise ValueError("no filename available!")

        self._filename = filename

        try:
            with open(filename) as f:
                try:
                    data = json.loads(
                        f.read().replace("\u200b", "").replace(r"\u200b", "")
                    )
                    self._data = data
                    self._filename = filename
                    return True
                except:
                    return False
        except:
            return False

    def save(self, filename=None):
        filename = filename or self._filename
        if filename is None:
            raise ValueError("no filename available!")

        # ensure the folder where we output the file exists
        pathlib.Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)

        with open(filename, "w") as f:
            f.write(
                json.dumps(self._data, indent=2)
                .replace("\u200b", "")
                .replace(r"\u200b", "")
            )
            self._filename = filename

    @property
    def data(self):
        return copy.deepcopy(self._data)


# update
st = Storage(DATA_FILE)
if st.data is not None and len(st.data) > 0:
    current_data = st.data

    # get the last update
    last_timestamp = list(current_data["All"].keys())[-1]
    year, month, day = list(map(int, last_timestamp.split("-")))
    start = helpers.next_day(year, month, day)

    # fetch new data
    new_data = jynneos.scrape_longitudinal(start=start)

    # update the data
    for key, value in new_data.items():
        if key in current_data:
            current_data[key].update(value)
        else:
            current_data[key] = value

    st._data = current_data

else:
    st._data = jynneos.scrape_longitudinal()

st.save()


# output something in "./data"
