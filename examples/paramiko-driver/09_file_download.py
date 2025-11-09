#!/usr/bin/env python3
"""
文件下载示例

演示如何使用 Paramiko 驱动从远程服务器下载文件
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
REMOTE_FILE = "/etc/hostname"  # 远程文件路径
LOCAL_FILE = "/tmp/test_downloaded.txt"  # 本地文件路径


def main():
    """主函数"""
    print("=" * 60)
    print("文件下载示例")
    print("=" * 60)

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
                "operation": "download",
                "local_path": LOCAL_FILE,
                "remote_path": REMOTE_FILE,
                "resume": True,  # 支持断点续传
                "chunk_size": 32768,
            }
        },
    }

    print(f"下载文件: {REMOTE_FILE} -> {LOCAL_FILE}")
    print(f"源服务器: {TEST_USERNAME}@{TEST_HOST}:{TEST_PORT}")

    try:
        # 提交任务
        result = client.request("POST", "/device/execute", request_data)
        job_id = result.get("data", {}).get("id")

        if not job_id:
            print(f"✗ 任务提交失败: {result.get('message', 'Unknown error')}")
            return

        print(f"任务已提交, Job ID: {job_id}")

        # 等待任务完成
        job_result = client.wait_for_job(job_id)
        result_data = job_result.get("result", {}).get("retval", {})

        # 检查文件传输结果
        if result_data:
            # 文件传输的结果格式: {"file_transfer_download": {"transfer_result": {...}}}
            found = False
            for key, value in result_data.items():
                if key.startswith("file_transfer_"):
                    found = True
                    transfer_result = value.get("transfer_result", {})
                    if transfer_result and transfer_result.get("success"):
                        print("✓ 文件下载成功")
                        print(f"  传输字节数: {transfer_result.get('bytes_transferred', 0)}")
                        if transfer_result.get("resumed"):
                            print("  (已恢复中断的传输)")
                    else:
                        error_msg = value.get("error", "Unknown error")
                        print(f"✗ 文件下载失败: {error_msg}")

            if not found:
                print("⚠ 未找到文件传输结果, 可能文件传输未正确触发")
                print(f"返回数据: {result_data}")

    except Exception as e:
        print(f"✗ 测试异常: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
