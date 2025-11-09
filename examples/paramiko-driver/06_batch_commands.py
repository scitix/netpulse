#!/usr/bin/env python3
"""
批量命令执行示例

演示如何同时对多台服务器执行命令
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

# 测试服务器列表
TEST_HOSTS = [
    TEST_HOST,
    # 可以添加更多服务器
    # "192.168.1.101",
    # "192.168.1.102",
]


def main():
    """主函数"""
    print("=" * 60)
    print("批量命令执行示例")
    print("=" * 60)

    # 创建客户端
    client = NetPulseClient(base_url=BASE_URL, api_key=API_KEY)

    # 构建设备列表
    devices = [{"host": host} for host in TEST_HOSTS]

    # 构建请求
    request_data = {
        "driver": "paramiko",
        "devices": devices,
        "connection_args": {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": TEST_PORT,
            "host_key_policy": "auto_add",
        },
        "command": ["uname -a", "hostname"],
    }

    print(f"批量执行命令到 {len(TEST_HOSTS)} 台服务器")
    print(f"服务器列表: {TEST_HOSTS}")

    try:
        # 提交批量任务
        result = client.request("POST", "/device/bulk", request_data)
        batch_data = result.get("data", {})

        if batch_data:
            succeeded = batch_data.get("succeeded", [])
            failed = batch_data.get("failed", [])

            print(f"\n批量执行完成")
            print(f"成功: {len(succeeded)} 台")
            print(f"失败: {len(failed)} 台")

            if succeeded:
                print("\n成功结果:")
                for idx, item in enumerate(succeeded):
                    job_id = item.get("id", "N/A")
                    host = TEST_HOSTS[idx] if idx < len(TEST_HOSTS) else f"服务器 {idx + 1}"
                    print(f"  - {host}: Job ID {job_id}")

            if failed:
                print("\n失败结果:")
                for item in failed:
                    print(f"  - {item.get('host', 'N/A')}: {item.get('error', 'Unknown error')}")
        else:
            print(f"✗ 批量任务提交失败: {result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"✗ 测试异常: {e}")


if __name__ == "__main__":
    main()
