#!/usr/bin/env python3
"""
快速测试 - 连接测试

最简单的示例: 测试 SSH 连接是否正常
"""

from common import API_KEY, BASE_URL, TEST_HOST, TEST_PASSWORD, TEST_USERNAME, NetPulseClient


def main():
    """主函数"""
    print("=" * 60)
    print("快速测试: SSH 连接测试")
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
            "port": 22,
            "host_key_policy": "auto_add",
        },
    }

    print(f"测试连接到: {TEST_USERNAME}@{TEST_HOST}")

    try:
        # 发送连接测试请求
        result = client.request("POST", "/device/test-connection", request_data)

        if result.get("code") == 200:
            data = result.get("data", {})
            if data.get("success"):
                print("✓ 连接测试成功")
                device_info = data.get("device_info", {})
                print(f"  系统信息: {device_info.get('system_info', 'N/A')}")
            else:
                print(f"✗ 连接测试失败: {data.get('error_message', 'Unknown error')}")
        else:
            print(f"✗ 请求失败: {result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"✗ 测试异常: {e}")


if __name__ == "__main__":
    main()
