import sqlite3
from datetime import datetime, timedelta
from os import environ
from os.path import join

query_time_bounds = """
select
    min(startTimestamp),
    max(endTimestamp)
from event;
"""

sttm_create_timeline = """
create table if not exists timeline (
    date date primary key
);
"""

sttm_create_sla = """
create table if not exists sla (
    eventID integer,
    year integer,
    month integer,
    day integer,
    terminalID text,
    parkName text,
    span text,
    unavailable_sec integer,
    open_sec integer,
    primary key (eventID, year, month, day)
);
"""

sttm_create_sla_agg = """
create table if not exists sla_agg (
    terminalID text,
    year integer,
    month integer,
    day integer,
    parkName text,
    unavailable_sec integer,
    open_sec integer,
    primary key (terminalID, year, month, day)
);
"""

sttm_populate_sla = """
insert or replace into sla
select
    event.rowid,
    strftime("%Y", timeline.date),
    strftime("%m", timeline.date),
    strftime("%d", timeline.date),
    event.terminalID,
    terminal.parkName,
    case 
        -- failure on single day
        when date(event.startTimestamp) == timeline.date and date(event.startTimestamp) == date(event.endTimestamp) then 'SINGLE'
        -- first day of failure
        when date(event.startTimestamp) == timeline.date and date(event.endTimestamp) > timeline.date then 'FIRST'
        -- whole day failure
        when date(event.startTimestamp) < timeline.date and date(event.endTimestamp) > timeline.date then 'MID'
        -- last day of failure
        when date(event.startTimestamp) < timeline.date and date(event.endTimestamp) == timeline.date then 'LAST'
        else NULL
    end,
    case 
        -- failure on single day
        when date(event.startTimestamp) == timeline.date and date(event.startTimestamp) == date(event.endTimestamp) then iif(
            time(event.startTimestamp) < terminal.endTime AND time(event.endTimestamp) > terminal.startTime,
            unixepoch(min(time(event.endTimestamp), terminal.endTime)) - unixepoch(max(time(event.startTimestamp), terminal.startTime)),
            0
        )
        -- first day of failure
        when date(event.startTimestamp) == timeline.date and date(event.endTimestamp) > timeline.date then iif(
            time(event.startTimestamp) < terminal.endTime,
            unixepoch(terminal.endTime) - unixepoch(max(time(event.startTimestamp), terminal.startTime)),
            0
        )
        -- whole day failure
        when date(event.startTimestamp) < timeline.date and date(event.endTimestamp) > timeline.date then
            unixepoch(terminal.endTime) - unixepoch(terminal.startTime)
        -- last day of failure
        when date(event.startTimestamp) < timeline.date and date(event.endTimestamp) == timeline.date then iif(
            time(event.endTimestamp) > terminal.startTime,
            unixepoch(min(time(event.endTimestamp), terminal.endTime)) -unixepoch(terminal.startTime),
            0
        )
        else 0
    end,
    unixepoch(terminal.endTime) - unixepoch(terminal.startTime)
from event
join timeline
left join terminal on event.terminalID = terminal.terminalID
where event.type = "FAILURE" and 
    event.state = "CLOSED" and 
    event.endTimestamp is not null
;
"""

sttm_populate_sla_agg = """
insert or replace into sla_agg
select
    terminalID,
    year,
    month,
    day,
    parkName,
    sum(unavailable_sec),
    min(open_sec)
from sla
group by parkName, terminalID, year, month, day
;
"""

def parse_timestamp(timestamp: str, format='%Y-%m-%d %H:%M:%S') -> datetime:
    return datetime.strptime(timestamp, format)

try:
    connection = sqlite3.connect(str(join(
        environ.get("DEMO_HOME"), 
        environ.get("DEMO_DB_NAME")
        ))
    )
    cursor = connection.cursor()

    # create 'timeline' table
    cursor.execute(sttm_create_timeline)

    # populate 'timeline' table
    min_timestamp, max_timestamp = cursor.execute(query_time_bounds).fetchone()
    min = parse_timestamp(min_timestamp)
    max = parse_timestamp(max_timestamp)
    timeline = [min + timedelta(days=i) for i in range(0, (max - min).days)]
    sttm_populate_timeline = f"""
insert or replace into timeline values
    {",".join([f"(\"{item.strftime('%Y-%m-%d')}\")" for item in timeline])};
"""
    cursor.execute(sttm_populate_timeline)

    # create 'sla' table
    cursor.execute(sttm_create_sla)

    # populate 'sla' table
    cursor.execute(sttm_populate_sla)

    # create 'sla_agg' table
    cursor.execute(sttm_create_sla_agg)

    # populate 'sla_agg' table
    cursor.execute(sttm_populate_sla_agg)

    cursor.execute("""
create index sla_agg_index on sla_agg(parkName, year, month, day);
""")

    connection.commit()
    connection.close()

except Exception as e:
    print(e)