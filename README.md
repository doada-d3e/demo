1. Utworzenie tabel TERMINAL i EVENT. Zaimportowanie danych z plików CSV `data/terminals.csv` i `data/events.csv` (Dockerfile)

2. Utworzenie TIMELINE z kolumną DATE w której będą przechowywane daty kolejnych dni tygodnia z okresu w którym odberane są zdarzenia z terminali (Python)

```sql
create table if not exists timeline (
    date date primary key
);
```

3. Cross join EVENT z TIMELINE dla wybranych zdarzen (informacja o zakonczeniu uszkodzenia). Obliczenie czasu awarii (UNAVAILABLE_SEC) i czasu operacyjnosci (OPEN_SEC). W celu informacyjnym, na potrzeby sprawdzenia poprawnosci, dodano kolumnę SPAN. Kolumna SPAN przyjmuje następujące wartosci:
- SINGLE - awaria rozpoczęła i zakonczyła się tego samego dnia
- FIRST - awaria rozpoczęła się tego dnia i zakonczyła w dniu pózniejszym
- MID - awaria trwała cały dzien
- LAST - awaria rozpoczęła się w dniu wczesniejszym i zakonczyła tego dnia
W zależnoscisci od SPAN, pole UNAVAILABILITY_SEC jest wyliczane w inny sposób.

Tabela SLA zawiera kolumnę PARKNAME, w celu szybszego wyszukiwania terminali po nazwie parkingu.

```sql
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
```

4. Obliczenie sumy czasu awarii dla każdego terminala w każdym dniu.
```sql
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

insert or replace into sla_agg
select
    terminalID,
    year,
    month,
    day,
    parkName,
    sum(unavailable_sec),
    sum(open_sec)
from sla
group by parkName, terminalID, year, month, day
;
```

5. Obliczenie wskaźnika SLA dla parametrów podanych przez użytkownika.
```sql
select
    terminalID,
    CAST(sum(open_sec) - sum(unavailable_sec) AS REAL) / CAST(sum(open_sec) AS REAL)
from sla_agg
where parkName = \"{parking_name}\" and
    year >= {date_from.year} and month >= {date_from.month} and day >= {date_from.day} and
    year <= {date_to.year} and month <= {date_to.month} and day <= {date_to.day}
group by terminalID
;
```