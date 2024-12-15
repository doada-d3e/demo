create table terminal(
    terminalID text primary key,
    parkName text not null,
    startTime time not null,
    endTime time not null
);


create table event(
    terminalID text not null,
    type text not null,
    state text,
    startTimestamp datetime not null,
    endTimestamp datetime
);