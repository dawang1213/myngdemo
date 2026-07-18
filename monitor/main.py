import json
import subprocess
import time
from datetime import datetime

from k8s_check import check_pod, check_service, get_node_addresses
from url_check import check_url
from port_check import check_port


def try_kubectl_port_forward(local_port=8080, service_name="nginx-demo-service", namespace="default"):
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as e:
        return None, None, None, str(e)

    start = time.time()
    while time.time() - start < 10:
        result = check_port("127.0.0.1", local_port)
        if result["status"] == "OPEN":
            return "127.0.0.1", local_port, proc, None
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode(errors="ignore")
            proc.wait()
            return None, None, None, stderr or "kubectl port-forward exited early"
        time.sleep(0.5)

    proc.terminate()
    proc.wait(timeout=5)
    return None, None, None, "kubectl port-forward timeout"


def find_service_endpoint(service_check):
    candidates = []

    if service_check.get("node_port"):
        candidates.append(("127.0.0.1", service_check["node_port"]))

        node_addresses = get_node_addresses()
        if node_addresses.get("status") == "OK":
            for addr in node_addresses.get("addresses", []):
                candidates.append((addr, service_check["node_port"]))

    if service_check.get("cluster_ip") and service_check.get("port"):
        candidates.append((service_check["cluster_ip"], service_check["port"]))

    seen = set()
    for host, port in candidates:
        if (host, port) in seen:
            continue
        seen.add((host, port))

        result = check_port(host, port)
        if result["status"] == "OPEN":
            return host, port

    return None, None


def resolve_service_endpoint(service_check):
    host, port = find_service_endpoint(service_check)
    if host and port:
        return host, port, None, None

    fw_host, fw_port, proc, fw_error = try_kubectl_port_forward()
    if fw_host and fw_port:
        return fw_host, fw_port, proc, None

    return None, None, None, fw_error


report = {}

report["time"] = str(datetime.now())

report["pod_check"] = check_pod()
report["service_check"] = check_service()

service_host, service_port, port_forward_proc, port_forward_error = resolve_service_endpoint(report["service_check"])

if service_host and service_port:
    service_url = f"http://{service_host}:{service_port}"

    report["service_endpoint"] = {
        "host": service_host,
        "port": service_port,
        "url": service_url,
    }
    if port_forward_error:
        report["service_endpoint"]["port_forward_error"] = port_forward_error

    report["port_check"] = check_port(service_host, service_port)
    report["url_check"] = check_url(service_url)
else:
    report["service_endpoint"] = {"error": port_forward_error or "无法连接服务"}
    report["port_check"] = {"status": "SKIPPED"}
    report["url_check"] = {"status": "SKIPPED"}

if (
    report["pod_check"]["status"] == "OK"
    and report["service_check"].get("status") == "OK"
    and report["url_check"]["status"] == "OK"
):
    report["result"] = "SUCCESS"
else:
    report["result"] = "FAILED"

with open("report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4, ensure_ascii=False)

if port_forward_proc is not None:
    port_forward_proc.terminate()
    try:
        port_forward_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        port_forward_proc.kill()

print("巡检完成")
