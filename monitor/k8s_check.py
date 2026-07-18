from kubernetes import client, config


def check_pod():

    result = {}

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        pods = v1.list_namespaced_pod(namespace="default")

        running = 0
        total = 0

        for pod in pods.items:
            if "nginx-demo" in pod.metadata.name:
                total += 1
                if pod.status.phase == "Running":
                    running += 1

        result["pod_total"] = total
        result["pod_running"] = running

        if total == running:
            result["status"] = "OK"
        else:
            result["status"] = "ERROR"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


def check_service():

    result = {}

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        service = v1.read_namespaced_service(
            name="nginx-demo-service",
            namespace="default"
        )

        port = service.spec.ports[0]

        result["status"] = "OK"
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

    result = {}

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        nodes = v1.list_node()
        addresses = []

        for node in nodes.items:
            for addr in node.status.addresses:
                if addr.type in ("InternalIP", "ExternalIP"):
                    addresses.append(addr.address)

        result["status"] = "OK"
        result["addresses"] = list(dict.fromkeys(addresses))

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result
