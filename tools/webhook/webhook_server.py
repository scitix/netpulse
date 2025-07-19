#!/usr/bin/env python3
"""
NetPulse Webhook Test Server
Simple HTTP server for testing and debugging NetPulse webhook functionality
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NetPulse Webhook Test Server",
    description="Server for testing NetPulse webhook functionality",
    version="1.0.0",
)

# Store received webhook messages
webhook_messages = []
message_counter = 0


def parse_result_string(result_str: str) -> dict:
    """Try to parse result string and extract error information"""
    try:
        # Handle NetPulse's stringified tuple format
        if result_str.startswith("('") and result_str.endswith("')"):
            # Extract error type and message
            parts = result_str[2:-2].split("', '", 1)
            if len(parts) == 2:
                error_type = parts[0]
                error_message = parts[1].replace("\\n", "\n")  # Convert escape characters
                return {"type": error_type, "message": error_message}
        return {"raw": result_str}
    except Exception:
        return {"raw": result_str}


def format_json_pretty(data: dict, indent_level: int = 1) -> str:
    """Beautify JSON display"""
    lines = []
    indent = "    " * indent_level

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent}[{key}]:")
            lines.append(format_json_pretty(value, indent_level + 1))
        elif isinstance(value, str) and len(value) > 80:
            # Display long text line by line
            lines.append(f"{indent}[{key}]:")
            text_lines = value.split("\n")
            for text_line in text_lines:
                if text_line.strip():
                    lines.append(f"{indent}    {text_line}")
        else:
            lines.append(f"{indent}[{key}]: {value}")

    return "\n".join(lines)


def log_request_details(request: Request, body: Dict[str, Any]) -> None:
    """Log detailed request information"""
    logger.info("=" * 80)
    logger.info("NetPulse Webhook Request Details")
    logger.info("=" * 80)

    # Basic information
    logger.info(f"Received Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request URL: {request.url}")

    # Request headers
    logger.info("Request Headers:")
    for name, value in request.headers.items():
        # Hide sensitive information but keep parts for identification
        if name.lower() in ["authorization", "x-api-key"]:
            if len(value) > 20:
                value = f"{value[:12]}...{value[-8:]}"
            else:
                value = "***"
        logger.info(f"    {name}: {value}")

    # Parse and beautify request body display
    logger.info("Request Body Data:")
    if isinstance(body, dict):
        job_id = body.get("id", "Unknown")
        result = body.get("result", "")

        logger.info(f"    Job ID: {job_id}")

        # Parse result field
        if isinstance(result, str):
            parsed_result = parse_result_string(result)

            if "type" in parsed_result and "message" in parsed_result:
                logger.info("    Job Execution Failed")
                logger.info(f"    Error Type: {parsed_result['type']}")
                logger.info("    Error Details:")

                # Display error message line by line
                error_lines = parsed_result["message"].split("\n")
                for line in error_lines:
                    if line.strip():
                        logger.info(f"       {line}")
            else:
                logger.info("    Raw Result:")
                logger.info(f"       {parsed_result.get('raw', result)}")
        elif isinstance(result, dict):
            if result.get("error"):
                logger.info("    Job Execution Failed")
                error = result["error"]
                logger.info(f"    Error Type: {error.get('type', 'Unknown')}")
                logger.info("    Error Details:")
                message = error.get("message", "No message")
                for line in message.split("\n"):
                    if line.strip():
                        logger.info(f"       {line}")
            else:
                logger.info("    Job Execution Successful")
                logger.info("    Execution Result:")
                logger.info(format_json_pretty(result, 2))
        else:
            logger.info(f"    Result Data: {result}")

        # Display other fields
        other_fields = {k: v for k, v in body.items() if k not in ["id", "result"]}
        if other_fields:
            logger.info("    Other Information:")
            for key, value in other_fields.items():
                logger.info(f"       {key}: {value}")
    else:
        logger.info("    Raw Data:")
        logger.info(f"       {json.dumps(body, indent=6, ensure_ascii=False)}")

    logger.info("=" * 80)


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle NetPulse webhook requests"""
    global message_counter
    message_counter += 1

    try:
        # Read request body
        body = await request.json()
    except Exception as e:
        logger.error(f"JSON parsing failed: {e}")
        # Try to read raw data
        try:
            raw_body = await request.body()
            logger.error(f"Raw request body: {raw_body.decode('utf-8')}")
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Log detailed information
    log_request_details(request, body)

    # Save message
    message_data = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "headers": dict(request.headers),
        "body": body,
        "message_id": message_counter,
    }
    webhook_messages.append(message_data)

    # Return response
    response = {
        "status": "success",
        "message": f"NetPulse webhook message received (#{message_counter})",
        "timestamp": datetime.now().isoformat(),
        "job_id": body.get("id", "Unknown"),
        "total_messages": message_counter,
    }

    logger.info(f"Response: {response}")
    return JSONResponse(content=response)


@app.get("/webhook/status")
async def webhook_status():
    """Get webhook reception status"""
    return {
        "server_status": "running",
        "total_messages_received": message_counter,
        "latest_messages": webhook_messages[-5:] if webhook_messages else [],
        "server_time": datetime.now().isoformat(),
    }


@app.get("/webhook/messages")
async def get_all_messages():
    """Get all received webhook messages"""
    return {"total_count": message_counter, "messages": webhook_messages}


@app.delete("/webhook/clear")
async def clear_messages():
    """Clear message records"""
    global message_counter, webhook_messages
    old_count = message_counter
    message_counter = 0
    webhook_messages = []

    logger.info(f"Cleared {old_count} webhook message records")
    return {
        "status": "cleared",
        "cleared_count": old_count,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    """Root path information"""
    return {
        "service": "NetPulse Webhook Test Server",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "POST /webhook - Receive webhook requests",
            "status": "GET /webhook/status - Check reception status",
            "messages": "GET /webhook/messages - View all messages",
            "clear": "DELETE /webhook/clear - Clear message records",
        },
        "webhook_url": "http://localhost:8888/webhook",
        "total_messages": message_counter,
    }


if __name__ == "__main__":
    print("Starting NetPulse Webhook Test Server...")
    print("Webhook URL: http://localhost:8888/webhook")
    print("Status Query: http://localhost:8888/webhook/status")
    print("View Messages: http://localhost:8888/webhook/messages")
    print("Clear Records: DELETE http://localhost:8888/webhook/clear")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info", access_log=True) 