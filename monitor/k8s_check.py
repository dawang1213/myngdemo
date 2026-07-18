from kubernetes import client, config

# 模块级别延迟加载 Kubernetes 配置，避免每个函数重复调用
_k8s_loaded = False


def _ensure_kube_config():
    """确保 Kubernetes 配置已加载（只加载一次）。"""
    global _k8s_loaded
    if not _k8s_loaded:
        config.load_kube_config()
        _k8s_loaded = True


def check_pod(namespace="default", name_filter="nginx-demo"):
    """检查指定命名空间中名称包含过滤条件的 Pod 运行状态。"""
    result = {}

    try:
        _ensure_kube_config()
        v1 = client.CoreV1Api()

        pods = v1.list_namespaced_pod(namespace=namespace)

        running = 0
        total = 0
        pod_details = []

        for pod in pods.items:
            if name_filter in pod.metadata.name:
                total += 1
                status = pod.status.phase

                if status == "Running":
                    running += 1

                pod_details.append({
                    "name": pod.metadata.name,
                    "status": status,
                    "ready": all(
                        cs.ready for cs in (pod.status.container_statuses or [])
                    ),
                })

        result["pod_total"] = total
        result["pod_running"] = running
        result["namespace"] = namespace

        if total == 0:
            result["status"] = "ERROR"
            result["error"] = f"未找到名称包含 '{name_filter}' 的 Pod"
        elif total == running:
            result["status"] = "OK"
        else:
            result["status"] = "ERROR"
            result["error"] = f"{total - running} 个 Pod 未在运行"

        result["pods"] = pod_details

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


def check_service(name="nginx-demo-service", namespace="default"):
    """检查指定 Service 的配置信息。"""
    result = {}

    try:
        _ensure_kube_config()
        v1 = client.CoreV1Api()

        service = v1.read_namespaced_service(name=name, namespace=namespace)

        port = service.spec.ports[0]

        result["status"] = "OK"
        result["name"] = name
        result["namespace"] = namespace
        result["type"] = service.spec.type
        result["port"] = port.port
        result["target_port"] = port.target_port
        result["node_port"] = getattr(port, "node_port", None)
        result["cluster_ip"] = service.spec.cluster_ip

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


def get_node_addresses():
    """获取集群节点的 InternalIP 和 ExternalIP 地址。"""
    result = {}

    try:
        _ensure_kube_config()
        v1 = client.CoreV1Api()

        nodes = v1.list_node()
        addresses = []

        for node in nodes.items:
            for addr in node.status.addresses:
                if addr.type in ("InternalIP", "ExternalIP"):
                    addresses.append(addr.address)

        result["status"] = "OK"
        result["addresses"] = list(dict.fromkeys(addresses))  # 去重保序

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result
