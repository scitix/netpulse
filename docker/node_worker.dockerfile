FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --upgrade pip

WORKDIR /app

COPY . .

# Copy SSH configuration file
RUN mkdir -p /root/.ssh \
    && cp docker/ssh_config /root/.ssh/config \
    && chmod 600 /root/.ssh/config

RUN pip3 install --no-cache-dir -e "."

CMD ["python3", "worker.py", "node"]
