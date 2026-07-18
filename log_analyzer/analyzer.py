import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "monitor"))
from k8s_check import check_pod, check_service

from kubernetes import client, config


def find_nginx_pod(namespace="default"):
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        pods = v1.list_namespaced_pod(namespace=namespace)
        for pod in pods.items:
            if "nginx-demo" in pod.metadata.name and pod.status.phase == "Running":
                return pod.metadata.name
    except Exception:
        pass

    return None


def fetch_pod_logs(pod_name, namespace="default", tail_lines=500):
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        return v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
        )
    except Exception as e:
        print(f"从 Pod 拉取日志失败: {e}")
        return ""


def parse_logs(text):
    error_4xx = 0
    error_5xx = 0
    ip_count = Counter()
    url_count = Counter()
    url_time = defaultdict(list)

    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        data = line.split()
        if len(data) != 5:
            continue

        ip = data[0]
        url = data[2]
        status = int(data[3])
        cost = float(data[4])

        ip_count[ip] += 1
        url_count[url] += 1
        url_time[url].append(cost)

        if 400 <= status < 500:
            error_4xx += 1
        elif status >= 500:
            error_5xx += 1

    url_stats = {}
    for url, times in url_time.items():
        url_stats[url] = {
            "avg": round(sum(times) / len(times), 3),
            "max": round(max(times), 3),
            "min": round(min(times), 3),
        }

    return {
        "error_4xx": error_4xx,
        "error_5xx": error_5xx,
        "top_ip": [
            {"ip": ip, "count": count}
            for ip, count in ip_count.most_common(5)
        ],
        "top_url": [
            {"url": url, "count": count}
            for url, count in url_count.most_common(5)
        ],
        "url_avg_time": url_stats,
    }


# ====== 主流程 ======

pod_name = find_nginx_pod()
if not pod_name:
    print("未找到运行中的 nginx Pod")
    exit(1)

log_text = fetch_pod_logs(pod_name)
analysis = parse_logs(log_text)

report = {
    "time": str(datetime.now()),
    "pod": pod_name,
    "http_error": {
        "4xx": analysis["error_4xx"],
        "5xx": analysis["error_5xx"],
    },
    "top_ip": analysis["top_ip"],
    "top_url": analysis["top_url"],
    "url_avg_time": analysis["url_avg_time"],
    "pod_check": check_pod(),
    "service_check": check_service(),
}

with open("report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4, ensure_ascii=False)

print("日志分析完成")
print(f"  Pod: {pod_name}")
print(f"  4xx: {analysis['error_4xx']}, 5xx: {analysis['error_5xx']}")
