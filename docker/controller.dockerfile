FROM python:3.12-slim

WORKDIR /app

RUN pip3 install --no-cache-dir --upgrade pip

COPY . .
RUN pip3 install --no-cache-dir -e ".[api]"

CMD ["gunicorn", "-p", "controller.pid", "-c", "gunicorn.conf.py", "netpulse.controller:app"]
