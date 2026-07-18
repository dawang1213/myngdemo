import requests
import time



def check_url(url):
    """检查指定 URL 的 HTTP 可访问性。"""
    result = {
        "url": url,
    }

    try:
        start = time.time()

        r = requests.get(url, timeout=5)

        cost = round(time.time() - start, 3)

        result["code"] = r.status_code
        result["response_time"] = cost

        if r.status_code == 200:
            result["status"] = "OK"
        else:
            result["status"] = "ERROR"
            result["error"] = f"HTTP 状态码异常: {r.status_code}"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result