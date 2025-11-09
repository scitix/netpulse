#!/usr/bin/env python3
"""
配置下发示例 - sudo权限

演示如何使用 sudo 权限执行配置命令
"""

from common import (
    API_KEY,
    BASE_URL,
    SUDO_PASSWORD,
    TEST_HOST,
    TEST_PASSWORD,
    TEST_PORT,
    TEST_USERNAME,
    NetPulseClient,
)


def main():
    """主函数"""
    print("=" * 60)
    print("配置下发示例 - sudo权限")
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
        "config": ["id", "whoami"],  # 示例命令(只读操作)
        "driver_args": {
            "sudo": True,
            "sudo_password": SUDO_PASSWORD,
        },
    }

    print(f"下发配置到: {TEST_USERNAME}@{TEST_HOST}:{TEST_PORT}")
    print("使用 sudo 权限执行")

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

        print("\n配置执行结果:")
        for cmd, output in result_data.items():
            print(f"\n命令: {cmd}")
            if output.get("output"):
                print(f"输出:\n{output['output']}")

    except Exception as e:
        print(f"✗ 测试异常: {e}")


if __name__ == "__main__":
    main()
