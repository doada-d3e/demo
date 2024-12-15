import sqlite3
from datetime import datetime
import pandas as pd

class db:
    def __init__(self, path: str):
        self.path = path
        self._connection = None

    def __del__(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self.path)
        return self._connection      

    @connection.setter
    def connection(self, value):
        self._connection = value

    def read(self, query: str):
        return self.connection.cursor().execute(query).fetchall()

    def get_parking_names(self):
        query = "select distinct parkName from terminal;"
        return self.read(query)
    
    def get_min_date(self):
        query = "select min(startTimestamp) from event;"
        return datetime.strptime(self.read(query)[0][0], '%Y-%m-%d %H:%M:%S').date()
    
    def get_max_date(self):
        query = "select max(endTimestamp) from event;"
        return datetime.strptime(self.read(query)[0][0], '%Y-%m-%d %H:%M:%S').date()
    
    def get_sla(self, parking_name: str, date_from, date_to):
        query = f"""
select
    terminalID,
    CAST(sum(open_sec) - sum(unavailable_sec) AS REAL) / CAST(sum(open_sec) AS REAL)
from sla_agg
where parkName = \"{parking_name}\" and
    year >= {date_from.year} and month >= {date_from.month} and day >= {date_from.day} and
    year <= {date_to.year} and month <= {date_to.month} and day <= {date_to.day}
group by terminalID
;
"""
        return pd.DataFrame(self.read(query), columns=["Terminal ID", "SLA"])