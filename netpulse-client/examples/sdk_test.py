from netpulse_client import Device, NetPulseClient

# 配置信息
ENDPOINT = "http://localhost:9000"
API_KEY = "np_d2b6c6baab32ac4e4d9c3dc9ac522fb37c45a175d941a981a77271cdc0adc38c"


# 示例设备
device = Device(
    host="192.168.1.100",
    username="admin",
    password="admin",
    device_type="hp_comware",
    port=22,
    timeout=30,
)


def basic_operations():
    print("=== 基础操作示例 ===")

    with NetPulseClient(ENDPOINT, API_KEY) as np_client:
        # 1. 执行命令
        print("\n1. 执行命令")
        result = np_client.exec_command(device, "display version")
        print("命令执行成功")
        print(result[0])
        print(result.duration)
        print(result.output)
        print(result.success)
        print(result.error)
        print(result.command)
        print(result.device)
        print(result.request_id)


if __name__ == "__main__":
    basic_operations()
