#!/usr/bin/env python3
"""
NetPulse Webhook Test Server
Simple HTTP server for testing and debugging NetPulse webhook functionality
"""

import argparse
import asyncio
import csv
import json
import logging
from collections import deque
from datetime import datetime, timedelta
from io import StringIO
from threading import Lock
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

_message_lock = Lock()


class WebhookConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEBHOOK_")

    max_messages: int = 100000
    retention_hours: int = 24
    server_port: int = 8888
    server_host: str = "0.0.0.0"
    enable_cors: bool = True
    verbose_logging: bool = False
    cleanup_interval: int = 1000


config = WebhookConfig()

app = FastAPI(
    title="NetPulse Webhook Test Server",
    description="Server for testing NetPulse webhook functionality",
    version="1.0.0",
)

webhook_messages: deque = deque(maxlen=config.max_messages)
message_counter = 0
success_count = 0
failure_count = 0
_last_cleanup_counter = 0


def parse_result_string(result_str: str) -> dict:
    try:
        if result_str.startswith("('") and result_str.endswith("')"):
            parts = result_str[2:-2].split("', '", 1)
            if len(parts) == 2:
                return {
                    "type": parts[0],
                    "message": parts[1].replace("\\n", "\n"),
                }
        return {"raw": result_str}
    except Exception:
        return {"raw": result_str}


def determine_success_status(body: Dict[str, Any]) -> Optional[bool]:
    result = body.get("result", "")
    if isinstance(result, str):
        parsed = parse_result_string(result)
        if "type" in parsed and "message" in parsed:
            return False
        return True
    elif isinstance(result, dict):
        return not bool(result.get("stderr"))
    return None


def cleanup_old_messages() -> int:
    if config.retention_hours <= 0:
        return 0

    cutoff = datetime.now() - timedelta(hours=config.retention_hours)
    removed = 0

    with _message_lock:
        if not webhook_messages:
            return 0

        filtered = []
        for msg in webhook_messages:
            try:
                msg_time = datetime.fromisoformat(msg["timestamp"])
                if msg_time >= cutoff:
                    filtered.append(msg)
                else:
                    removed += 1
            except (ValueError, KeyError):
                filtered.append(msg)

        if removed > 0:
            webhook_messages.clear()
            webhook_messages.extend(filtered)

    return removed


async def async_cleanup_old_messages():
    removed = cleanup_old_messages()
    if removed > 0:
        log.info(f"Cleaned up {removed} old messages")


def filter_messages(
    job_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    is_success: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[Dict[str, Any]], int]:
    with _message_lock:
        filtered = list(webhook_messages)

    if job_id:
        filtered = [msg for msg in filtered if msg.get("job_id") == job_id]

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            filtered = [
                msg
                for msg in filtered
                if datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00")) >= start_dt
            ]
        except (ValueError, KeyError):
            pass

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            filtered = [
                msg
                for msg in filtered
                if datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00")) <= end_dt
            ]
        except (ValueError, KeyError):
            pass

    if is_success is not None:
        filtered = [msg for msg in filtered if msg.get("is_success") == is_success]

    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(filtered)
    paginated = filtered[offset : offset + limit]
    return paginated, total


def format_json_pretty(data: dict, indent_level: int = 1) -> str:
    lines = []
    indent = "    " * indent_level

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent}[{key}]:")
            lines.append(format_json_pretty(value, indent_level + 1))
        elif isinstance(value, str) and len(value) > 80:
            lines.append(f"{indent}[{key}]:")
            for text_line in value.split("\n"):
                if text_line.strip():
                    lines.append(f"{indent}    {text_line}")
        else:
            lines.append(f"{indent}[{key}]: {value}")

    return "\n".join(lines)


def log_request_details(request: Request, body: Dict[str, Any]) -> None:
    if not config.verbose_logging:
        job_id = body.get("id", "Unknown") if isinstance(body, dict) else "Unknown"
        log.info(f"Webhook received: job_id={job_id}, method={request.method}")
        return

    log.info("=" * 80)
    log.info("NetPulse Webhook Request Details")
    log.info("=" * 80)
    log.info(f"Received Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Request Method: {request.method}")
    log.info(f"Request URL: {request.url}")

    log.info("Request Headers:")
    for name, value in request.headers.items():
        if name.lower() in ["authorization", "x-api-key"]:
            if len(value) > 20:
                value = f"{value[:12]}...{value[-8:]}"
            else:
                value = "***"
        log.info(f"    {name}: {value}")

    log.info("Request Body Data:")
    if isinstance(body, dict):
        job_id = body.get("id", "Unknown")
        result = body.get("result", "")
        log.info(f"    Job ID: {job_id}")

        if isinstance(result, str):
            parsed = parse_result_string(result)
            if "type" in parsed and "message" in parsed:
                log.info("    Job Execution Failed")
                log.info(f"    Error Type: {parsed['type']}")
                log.info("    Error Details:")
                for line in parsed["message"].split("\n"):
                    if line.strip():
                        log.info(f"       {line}")
            else:
                log.info("    Raw Result:")
                log.info(f"       {parsed.get('raw', result)}")
        elif isinstance(result, dict):
            error = result.get("stderr")
            if error:
                log.info("    Job Execution Failed")
                if isinstance(error, dict):
                    log.info(f"    Error Type: {error.get('type', 'Unknown')}")
                    log.info("    Error Details:")
                    for line in error.get("message", "No message").split("\n"):
                        if line.strip():
                            log.info(f"       {line}")
                else:
                    log.info(f"    Error: {error}")
            else:
                log.info("    Job Execution Successful")
                log.info("    Execution Result:")
                log.info(format_json_pretty(result, 2))
        else:
            log.info(f"    Result Data: {result}")

        other_fields = {k: v for k, v in body.items() if k not in ["id", "result"]}
        if other_fields:
            log.info("    Other Information:")
            for key, value in other_fields.items():
                log.info(f"       {key}: {value}")
    else:
        log.info("    Raw Data:")
        log.info(f"       {json.dumps(body, indent=6, ensure_ascii=False)}")

    log.info("=" * 80)


@app.post("/webhook")
async def webhook_handler(request: Request):
    global message_counter, success_count, failure_count, _last_cleanup_counter

    try:
        body = await request.json()
    except Exception as e:
        log.error(f"JSON parsing failed: {e}")
        try:
            raw_body = await request.body()
            log.error(f"Raw request body: {raw_body.decode('utf-8')}")
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Invalid JSON")

    log_request_details(request, body)

    is_success = determine_success_status(body)
    if is_success is True:
        success_count += 1
    elif is_success is False:
        failure_count += 1

    job_id = body.get("id") if isinstance(body, dict) else None

    message_data = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "body": body,
        "message_id": message_counter + 1,
        "job_id": job_id,
        "is_success": is_success,
    }

    with _message_lock:
        message_counter += 1
        message_data["message_id"] = message_counter
        webhook_messages.append(message_data)

    if message_counter - _last_cleanup_counter >= config.cleanup_interval:
        _last_cleanup_counter = message_counter
        asyncio.create_task(async_cleanup_old_messages())  # noqa: RUF006

    response = {
        "status": "success",
        "message": f"NetPulse webhook message received (#{message_counter})",
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id or "Unknown",
        "total_messages": message_counter,
        "is_success": is_success,
    }

    if config.verbose_logging:
        log.info(f"Response: {response}")

    return JSONResponse(content=response)


@app.get("/webhook/status")
async def webhook_status(background_tasks: BackgroundTasks):
    background_tasks.add_task(async_cleanup_old_messages)

    with _message_lock:
        latest = list(webhook_messages)[-5:] if webhook_messages else []

    return {
        "server_status": "running",
        "total_messages_received": message_counter,
        "messages_in_memory": len(webhook_messages),
        "success_count": success_count,
        "failure_count": failure_count,
        "unknown_count": message_counter - success_count - failure_count,
        "latest_messages": latest,
        "server_time": datetime.now().isoformat(),
        "max_messages": config.max_messages,
        "retention_hours": config.retention_hours,
    }


@app.get("/webhook/messages")
async def get_all_messages(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    start_time: Optional[str] = Query(None, description="Filter by start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="Filter by end time (ISO format)"),
    is_success: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    messages, total = filter_messages(
        job_id=job_id,
        start_time=start_time,
        end_time=end_time,
        is_success=is_success,
        limit=limit,
        offset=offset,
    )

    return {
        "total_count": total,
        "returned_count": len(messages),
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(messages) < total,
        "messages": messages,
    }


@app.delete("/webhook/clear")
async def clear_messages():
    global message_counter, success_count, failure_count

    with _message_lock:
        old_count = message_counter
        message_counter = 0
        success_count = 0
        failure_count = 0
        webhook_messages.clear()

    log.info(f"Cleared {old_count} webhook message records")
    return {
        "status": "cleared",
        "cleared_count": old_count,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/webhook/stats")
async def get_statistics(background_tasks: BackgroundTasks):
    background_tasks.add_task(async_cleanup_old_messages)

    total_classified = success_count + failure_count
    success_rate = (success_count / total_classified * 100) if total_classified > 0 else 0.0

    with _message_lock:
        messages_list = list(webhook_messages)

    success_msgs = sum(1 for msg in messages_list if msg.get("is_success") is True)
    failure_msgs = sum(1 for msg in messages_list if msg.get("is_success") is False)
    unknown_msgs = sum(1 for msg in messages_list if msg.get("is_success") is None)

    return {
        "total_received": message_counter,
        "in_memory": len(webhook_messages),
        "success": {
            "total": success_count,
            "in_memory": success_msgs,
        },
        "failure": {
            "total": failure_count,
            "in_memory": failure_msgs,
        },
        "unknown": {
            "total": message_counter - success_count - failure_count,
            "in_memory": unknown_msgs,
        },
        "success_rate": round(success_rate, 2),
        "server_time": datetime.now().isoformat(),
    }


@app.get("/webhook/export")
async def export_messages(
    format: str = Query("json", pattern="^(json|csv)$", description="Export format"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    start_time: Optional[str] = Query(None, description="Filter by start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="Filter by end time (ISO format)"),
    is_success: Optional[bool] = Query(None, description="Filter by success status"),
):
    messages, total = filter_messages(
        job_id=job_id,
        start_time=start_time,
        end_time=end_time,
        is_success=is_success,
        limit=100000,
        offset=0,
    )

    if format == "csv":
        output = StringIO()
        if messages:
            fieldnames = set()
            for msg in messages:
                fieldnames.update(msg.keys())
                if "body" in msg and isinstance(msg["body"], dict):
                    fieldnames.update(f"body.{k}" for k in msg["body"].keys())

            writer = csv.DictWriter(output, fieldnames=sorted(fieldnames))
            writer.writeheader()

            for msg in messages:
                row = {}
                for key, value in msg.items():
                    if key == "body" and isinstance(value, dict):
                        for k, v in value.items():
                            row[f"body.{k}"] = json.dumps(v) if isinstance(v, (dict, list)) else v
                    else:
                        row[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
                writer.writerow(row)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=webhook_messages.csv"},
        )
    else:
        return {
            "export_time": datetime.now().isoformat(),
            "total_messages": total,
            "exported_count": len(messages),
            "format": format,
            "messages": messages,
        }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "NetPulse Webhook Test Server",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "service": "NetPulse Webhook Test Server",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "POST /webhook - Receive webhook requests",
            "status": "GET /webhook/status - Check reception status",
            "messages": "GET /webhook/messages - View messages (with filtering & pagination)",
            "stats": "GET /webhook/stats - Get detailed statistics",
            "export": "GET /webhook/export - Export messages (JSON/CSV)",
            "clear": "DELETE /webhook/clear - Clear message records",
            "health": "GET /health - Health check",
        },
        "webhook_url": f"http://{config.server_host}:{config.server_port}/webhook",
        "total_messages": message_counter,
        "configuration": {
            "max_messages": config.max_messages,
            "retention_hours": config.retention_hours,
            "cors_enabled": config.enable_cors,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NetPulse Webhook Test Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.server_host,
        help=f"Server host address (default: {config.server_host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.server_port,
        help=f"Server port (default: {config.server_port})",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=config.max_messages,
        help=f"Maximum messages to store (default: {config.max_messages})",
    )
    parser.add_argument(
        "--retention-hours",
        type=int,
        default=config.retention_hours,
        help=f"Message retention time in hours (default: {config.retention_hours})",
    )
    parser.add_argument(
        "--no-cors",
        action="store_true",
        help="Disable CORS (default: enabled)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (default: disabled)",
    )
    parser.add_argument(
        "--cleanup-interval",
        type=int,
        default=config.cleanup_interval,
        help=f"Cleanup interval in messages (default: {config.cleanup_interval})",
    )

    args = parser.parse_args()

    config.server_host = args.host
    config.server_port = args.port
    config.max_messages = args.max_messages
    config.retention_hours = args.retention_hours
    config.enable_cors = not args.no_cors
    config.verbose_logging = args.verbose
    config.cleanup_interval = args.cleanup_interval

    if webhook_messages.maxlen != config.max_messages:
        old_messages = list(webhook_messages)
        new_deque = deque(old_messages, maxlen=config.max_messages)
        globals()["webhook_messages"] = new_deque

    if config.enable_cors and not any(isinstance(m, CORSMiddleware) for m in app.user_middleware):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    print("Starting NetPulse Webhook Test Server...")
    print(f"Webhook URL: http://{config.server_host}:{config.server_port}/webhook")
    print(f"Status Query: http://{config.server_host}:{config.server_port}/webhook/status")
    print(f"View Messages: http://{config.server_host}:{config.server_port}/webhook/messages")
    print(f"Statistics: http://{config.server_host}:{config.server_port}/webhook/stats")
    print(f"Export Messages: http://{config.server_host}:{config.server_port}/webhook/export")
    print(f"Health Check: http://{config.server_host}:{config.server_port}/health")
    print(f"Clear Records: DELETE http://{config.server_host}:{config.server_port}/webhook/clear")
    print("=" * 60)
    print("Configuration:")
    print(f"  Host: {config.server_host}")
    print(f"  Port: {config.server_port}")
    print(f"  Max Messages: {config.max_messages}")
    print(f"  Retention Hours: {config.retention_hours}")
    print(f"  CORS Enabled: {config.enable_cors}")
    print(f"  Verbose Logging: {config.verbose_logging}")
    print(f"  Cleanup Interval: {config.cleanup_interval}")
    print("=" * 60)

    uvicorn.run(
        app, host=config.server_host, port=config.server_port, log_level="info", access_log=True
    )
