import socket



def check_port(host, port):
    """检查指定主机和端口的 TCP 连通性。"""
    result = {
        "host": host,
        "port": port,
    }

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)

    try:
        s.connect((host, port))
        result["status"] = "OPEN"
    except Exception as e:
        result["status"] = "CLOSED"
        result["error"] = str(e)
    finally:
        s.close()

    return result