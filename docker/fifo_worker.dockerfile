FROM python:3.12-slim

WORKDIR /app

RUN pip3 install --no-cache-dir --upgrade pip

COPY . .
RUN pip3 install --no-cache-dir -e "."

CMD ["python3", "worker.py", "fifo"]
