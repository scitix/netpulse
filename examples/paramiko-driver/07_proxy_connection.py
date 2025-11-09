#!/usr/bin/env python3
"""
SSH代理连接示例

演示如何通过代理服务器(跳板机)连接到目标服务器
"""

from common import (
    API_KEY,
    BASE_URL,
    PROXY_HOST,
    PROXY_PASSWORD,
    PROXY_PORT,
    PROXY_USERNAME,
    TEST_HOST,
    TEST_PASSWORD,
    TEST_PORT,
    TEST_USERNAME,
    NetPulseClient,
)


def main():
    """主函数"""
    print("=" * 60)
    print("SSH代理连接示例")
    print("=" * 60)

    # 检查代理配置
    if not PROXY_HOST:
        print("✗ 未配置代理服务器, 请在 config.py 中设置 PROXY_HOST")
        return

    # 创建客户端
    client = NetPulseClient(base_url=BASE_URL, api_key=API_KEY)

    # 构建请求
    request_data = {
        "driver": "paramiko",
        "connection_args": {
            # 目标服务器配置
            "host": TEST_HOST,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "port": TEST_PORT,
            "host_key_policy": "auto_add",
            # 代理服务器配置
            "proxy_host": PROXY_HOST,
            "proxy_port": PROXY_PORT,
            "proxy_username": PROXY_USERNAME or TEST_USERNAME,
            "proxy_password": PROXY_PASSWORD or TEST_PASSWORD,
        },
        "command": ["uname -a", "hostname", "whoami"],
    }

    print(f"通过代理 {PROXY_USERNAME or TEST_USERNAME}@{PROXY_HOST}:{PROXY_PORT} 连接")
    print(f"目标服务器: {TEST_USERNAME}@{TEST_HOST}:{TEST_PORT}")

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

        print("\n命令执行结果:")
        for cmd, output in result_data.items():
            print(f"\n命令: {cmd}")
            if output.get("output"):
                print(f"输出:\n{output['output']}")

    except Exception as e:
        print(f"✗ 测试异常: {e}")


if __name__ == "__main__":
    main()
