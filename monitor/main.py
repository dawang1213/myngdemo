import json
import subprocess
import sys
import time
from datetime import datetime

from k8s_check import check_pod, check_service, get_node_addresses
from url_check import check_url
from port_check import check_port


def try_kubectl_port_forward(local_port=8080, service_name="nginx-demo-service", namespace="default"):
    """尝试通过 kubectl port-forward 建立端口转发。

    返回: (host, port, proc, error_msg)
    """
    try:
        proc = subprocess.Popen(
            [
                "kubectl",
                "port-forward",
                f"svc/{service_name}",
                f"{local_port}:80",
                "-n",
                namespace,
            ],
            stdout=subprocess.DEVNULL,   # 避免 PIPE 缓冲区满导致死锁
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return None, None, None, "kubectl 命令未找到，请确认已安装 kubectl 并加入 PATH"
    except Exception as e:
        return None, None, None, f"启动 kubectl port-forward 失败: {e}"

    start = time.time()
    # 等待最多 15 秒，给 port-forward 足够的启动时间
    while time.time() - start < 15:
        result = check_port("127.0.0.1", local_port)
        if result["status"] == "OPEN":
            return "127.0.0.1", local_port, proc, None

        # 检查进程是否异常退出
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode(errors="ignore") if proc.stderr else ""
            proc.wait()
            error_msg = stderr.strip() or "kubectl port-forward 异常退出"
            return None, None, None, error_msg

        time.sleep(0.5)

    # 超时：终止进程
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    # 读取 stderr 以便诊断
    stderr = ""
    if proc.stderr:
        try:
            stderr = proc.stderr.read().decode(errors="ignore")
        except Exception:
            pass

    return None, None, None, stderr.strip() or "kubectl port-forward 超时"


def find_service_endpoint(service_check):
    """尝试通过直接连接找到可用的服务端点。"""
    candidates = []

    if service_check.get("node_port"):
        # 先试 localhost
        candidates.append(("127.0.0.1", service_check["node_port"]))

        # 再试各节点 IP
        node_addresses = get_node_addresses()
        if node_addresses.get("status") == "OK":
            for addr in node_addresses.get("addresses", []):
                if addr != "127.0.0.1":
                    candidates.append((addr, service_check["node_port"]))

    # 尝试 ClusterIP（仅集群内部可达，但对某些环境可能有效）
    if service_check.get("cluster_ip") and service_check.get("port"):
        candidates.append((service_check["cluster_ip"], service_check["port"]))

    seen = set()
    for host, port in candidates:
        key = (host, port)
        if key in seen:
            continue
        seen.add(key)

        result = check_port(host, port)
        if result["status"] == "OPEN":
            return host, port

    return None, None


def resolve_service_endpoint(service_check):
    """解析服务端点：先尝试直接连接，失败则回退到 kubectl port-forward。"""
    host, port = find_service_endpoint(service_check)
    if host and port:
        return host, port, None, None

    # 直接访问失败时，尝试 kubectl port-forward
    fw_host, fw_port, proc, fw_error = try_kubectl_port_forward()
    if fw_host and fw_port:
        return fw_host, fw_port, proc, None

    # 所有方式均失败，返回空并附上错误信息
    return None, None, None, f"无法连接到服务: 直接连接和 kubectl port-forward 均失败。port-forward 错误: {fw_error}"


# ==================== 主流程 ====================

report = {}

report["time"] = str(datetime.now())

# 检查 Pod
report["pod_check"] = check_pod()

# 检查 Kubernetes Service
report["service_check"] = check_service()

# 解析服务端点
service_host, service_port, port_forward_proc, port_forward_error = resolve_service_endpoint(
    report["service_check"]
)

if service_host and service_port:
    service_url = f"http://{service_host}:{service_port}"

    report["service_endpoint"] = {
        "host": service_host,
        "port": service_port,
        "url": service_url,
    }
    if port_forward_error:
        report["service_endpoint"]["port_forward_error"] = port_forward_error

    # 检查端口连通性
    report["port_check"] = check_port(service_host, service_port)

    # 检查网站
    report["url_check"] = check_url(service_url)
else:
    # 无法找到可用端点时，跳过端口和 URL 检查
    report["service_endpoint"] = {
        "host": None,
        "port": None,
        "url": None,
        "error": port_forward_error or "未能解析到可用的服务端点",
    }
    report["port_check"] = {
        "status": "SKIPPED",
        "reason": "未找到可用端点",
    }
    report["url_check"] = {
        "status": "SKIPPED",
        "reason": "未找到可用端点",
    }
    print(f"[警告] {report['service_endpoint']['error']}", file=sys.stderr)

# 综合判断结果
if (
    report["pod_check"].get("status") == "OK"
    and report["service_check"].get("status") == "OK"
    and report["url_check"].get("status") == "OK"
):
    report["result"] = "SUCCESS"
else:
    report["result"] = "FAILED"

# 输出报告
with open("report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4, ensure_ascii=False)

# 清理 port-forward 进程（避免后台残留）
if port_forward_proc is not None:
    port_forward_proc.terminate()
    try:
        port_forward_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        port_forward_proc.kill()
        port_forward_proc.wait()

print("巡检完成")
print(f"结果: {report['result']}")
print(f"报告已写入 report.json")
