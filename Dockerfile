FROM ubuntu:24.04
RUN apt update && apt upgrade -y
RUN apt install python3 python3-pip libsqlite3-dev sqlite3 -y
ENV STREAMLIT_SERVER_PORT=8550 DEMO_HOME=/opt/demo DEMO_DB_NAME=demo.db
EXPOSE 8550
RUN mkdir -p /opt/demo
WORKDIR /opt/demo

# Install Python packages
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt --break-system-packages

# Initiate database
COPY data/ data/
COPY src/ src/
COPY init.sql .
RUN sqlite3 demo.db -init init.sql
RUN sqlite3 demo.db <<EOF
.mode csv
.import data/events.csv event
.import data/terminals.csv terminal
EOF
RUN python3 src/transform_data.py

CMD ["streamlit", "run", "src/main.py"]