#!/usr/bin/env python3
"""
文件上传示例

演示如何使用 Paramiko 驱动上传文件到远程服务器
"""

from common import (
    API_KEY,
    BASE_URL,
    TEST_HOST,
    TEST_PASSWORD,
    TEST_PORT,
    TEST_USERNAME,
    NetPulseClient,
)

# 文件路径
LOCAL_FILE = "/tmp/test_upload.txt"  # 本地文件路径
REMOTE_FILE = "/tmp/test_uploaded.txt"  # 远程文件路径


def main():
    """主函数"""
    print("=" * 60)
    print("文件上传示例")
    print("=" * 60)

    # 创建测试文件（如果不存在）
    import os

    if not os.path.exists(LOCAL_FILE):
        with open(LOCAL_FILE, "w") as f:
            f.write("Hello from NetPulse!\n")
        print(f"创建测试文件: {LOCAL_FILE}")

    # 创建客户端
    client = NetPulseClient(base_url=BASE_URL, api_key=API_KEY)

    # 构建请求
    request_data = {
        "driver": "paramiko",
        "connection_args": {
            "host": TEST_HOST,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": TEST_PORT,
            "host_key_policy": "auto_add",
        },
        "command": ["__FILE_TRANSFER__"],  # 文件传输占位符
        "driver_args": {
            "file_transfer": {
                "operation": "upload",
                "local_path": LOCAL_FILE,
                "remote_path": REMOTE_FILE,
                "resume": False,
                "chunk_size": 32768,
            }
        },
    }

    print(f"上传文件: {LOCAL_FILE} -> {REMOTE_FILE}")
    print(f"目标服务器: {TEST_USERNAME}@{TEST_HOST}:{TEST_PORT}")

    try:
        # 提交任务
        result = client.request("POST", "/device/execute", request_data)
        job_id = result.get("data", {}).get("id")

        if not job_id:
            print(f"✗ 任务提交失败: {result.get('message', 'Unknown error')}")
            return

        print(f"任务已提交，Job ID: {job_id}")

        # 等待任务完成
        job_result = client.wait_for_job(job_id)
        result_data = job_result.get("result", {}).get("retval", {})

        # 检查文件传输结果
        if result_data:
            # 文件传输的结果格式: {"file_transfer_upload": {"transfer_result": {...}}}
            found = False
            for key, value in result_data.items():
                if key.startswith("file_transfer_"):
                    found = True
                    transfer_result = value.get("transfer_result", {})
                    if transfer_result and transfer_result.get("success"):
                        print("✓ 文件上传成功")
                        print(f"  传输字节数: {transfer_result.get('bytes_transferred', 0)}")
                    else:
                        error_msg = value.get('error', 'Unknown error')
                        print(f"✗ 文件上传失败: {error_msg}")
            
            if not found:
                print("⚠ 未找到文件传输结果，可能文件传输未正确触发")
                print(f"返回数据: {result_data}")

    except Exception as e:
        print(f"✗ 测试异常: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

