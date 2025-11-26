# API Examples

Sample end-to-end patterns for common NetPulse use cases. All examples assume `BASE_URL=http://localhost:9000` and `X-API-KEY` is set.

## Scenario 1: Network discovery
- Test reachability (POST `/device/test`)
- Collect facts with a few show commands (POST `/device/exec`)
- Poll job results via GET `/job`

```python
import requests, time

HEADERS = {"X-API-KEY": "your_api_key"}
BASE = "http://localhost:9000"

def wait_job(job_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{BASE}/job", params={"id": job_id}, headers=HEADERS)
        job = r.json()["data"][0]
        if job["status"] in {"finished", "failed"}:
            return job
        time.sleep(1)
    raise TimeoutError(f"Job {job_id} timed out")

def discover(device):
    # 1) connection test
    test = requests.post(f"{BASE}/device/test", json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": device["device_type"],
            "host": device["host"],
            "username": device["username"],
            "password": device["password"]
        }
    }, headers=HEADERS).json()["data"]
    if not test["success"]:
        return {"device": device, "error": test["error_message"]}

    # 2) collect basic info
    info = {}
    for cmd in ["show version", "show ip interface brief"]:
        resp = requests.post(f"{BASE}/device/exec", json={
            "driver": "netmiko",
            "connection_args": device,
            "command": cmd,
            "queue_strategy": "pinned",
            "ttl": 300
        }, headers=HEADERS).json()
        job = wait_job(resp["data"]["id"])
        info[cmd] = job["result"].get("output") if job["status"] == "finished" else job["result"].get("error")
    return {"device": device, "info": info}
```

## Scenario 2: Bulk config backup
- Use `/device/exec` to run `show running-config`
- Store results to disk
- Run in batches (10–50 devices) for stability

```python
import os, json

def backup_device(device, backup_dir="backups"):
    os.makedirs(backup_dir, exist_ok=True)
    resp = requests.post(f"{BASE}/device/exec", json={
        "driver": "netmiko",
        "connection_args": device,
        "command": "show running-config",
        "queue_strategy": "pinned",
        "ttl": 300
    }, headers=HEADERS).json()
    job = wait_job(resp["data"]["id"])
    if job["status"] == "finished":
        path = os.path.join(backup_dir, f"{device['host']}.txt")
        with open(path, "w") as f:
            f.write(job["result"]["output"])
        return {"device": device["host"], "saved": path}
    return {"device": device["host"], "error": job["result"].get("error")}
```

## Scenario 3: Safe config change with rollback
- Backup running config
- Push change with `config` and `driver_args.save=true`
- On failure, revert using the backup content

```python
def push_config(device, commands):
    resp = requests.post(f"{BASE}/device/exec", json={
        "driver": "netmiko",
        "connection_args": {**device, "enable_mode": True},
        "config": commands,
        "driver_args": {"save": True, "exit_config_mode": True},
        "queue_strategy": "pinned",
        "ttl": 300
    }, headers=HEADERS).json()
    return wait_job(resp["data"]["id"])

def rollback(device, backup_text):
    return push_config(device, backup_text.splitlines())
```

> For more patterns, combine these building blocks: `/device/bulk` for fleet ops, `/template/render` for templated configs, and webhooks for async notifications.
