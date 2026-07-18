from kubernetes import client, config


def check_pod():

    result={}

    try:

        # 使用本地kubeconfig
        config.load_kube_config()

        v1 = client.CoreV1Api()


        pods = v1.list_namespaced_pod(
            namespace="default"
        )


        running=0
        total=0


        for pod in pods.items:

            if "nginx-demo" in pod.metadata.name:

                total += 1


                if pod.status.phase=="Running":
                    running += 1


        result["pod_total"]=total
        result["pod_running"]=running


        if total==running:

            result["status"]="OK"

        else:

            result["status"]="ERROR"



    except Exception as e:

        result["status"]="ERROR"
        result["error"]=str(e)


    return result