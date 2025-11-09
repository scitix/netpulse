#!/usr/bin/env python3
"""
测试场景 1: 连接测试（密码认证）

测试基本的 SSH 连接功能，使用用户名和密码认证。
"""  # noqa: RUF002

from common import (
    API_KEY,
    BASE_URL,
    TEST_HOST,
    TEST_PASSWORD,
    TEST_PORT,
    TEST_USERNAME,
    NetPulseClient,
)


def main():
    """主函数"""
    print("=" * 60)
    print("测试场景 1: 连接测试(密码认证)")
    print("=" * 60)

    # 创建客户端
    client = NetPulseClient(base_url=BASE_URL, api_key=API_KEY)

    # 构建请求数据
    request_data = {
        "driver": "paramiko",
        "connection_args": {
            "host": TEST_HOST,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": TEST_PORT,
            "timeout": 30.0,
            "host_key_policy": "auto_add",
        },
    }

    print(f"测试连接到: {TEST_USERNAME}@{TEST_HOST}:{TEST_PORT}")

    try:
        # 发送连接测试请求
        result = client.request("POST", "/device/test-connection", request_data)

        if result.get("code") == 200:
            data = result.get("data", {})
            if data.get("success"):
                print("连接测试成功")
                device_info = data.get("device_info", {})
                print(f"  系统信息: {device_info.get('system_info', 'N/A')}")
                print(f"  连接时间: {data.get('connection_time', 0):.2f} 秒")
            else:
                print(f"连接测试失败: {data.get('error_message', 'Unknown error')}")
        else:
            print(f"请求失败: {result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
