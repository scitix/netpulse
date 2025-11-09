#!/usr/bin/env python3
"""
命令执行示例 - 密钥文件认证

演示如何使用密钥文件进行认证
"""

from common import (
    API_KEY,
    BASE_URL,
    KEY_FILE,
    KEY_PASSPHRASE,
    TEST_HOST,
    TEST_PORT,
    TEST_USERNAME,
    NetPulseClient,
)


def main():
    """主函数"""
    print("=" * 60)
    print("命令执行示例 - 密钥文件认证")
    print("=" * 60)

    # 创建客户端
    client = NetPulseClient(base_url=BASE_URL, api_key=API_KEY)

    # 构建请求
    request_data = {
        "driver": "paramiko",
        "connection_args": {
            "host": TEST_HOST,
            "username": TEST_USERNAME,
            "key_filename": KEY_FILE,
            "passphrase": KEY_PASSPHRASE,
            "port": TEST_PORT,
            "host_key_policy": "auto_add",
        },
        "command": ["whoami", "pwd"],
    }

    print(f"执行命令到: {TEST_USERNAME}@{TEST_HOST}:{TEST_PORT}")
    print(f"使用密钥文件: {KEY_FILE}")

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
