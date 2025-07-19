FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create SSH config directory
RUN mkdir -p /root/.ssh

WORKDIR /app

RUN pip3 install --no-cache-dir --upgrade pip

COPY . .

# Copy SSH configuration file
COPY docker/ssh_config /root/.ssh/config
RUN chmod 600 /root/.ssh/config

RUN pip3 install --no-cache-dir -e "."

CMD ["python3", "worker.py", "fifo"]
