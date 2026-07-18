import json
from datetime import datetime

from k8s_check import check_pod
from url_check import check_url
from port_check import check_port



report={}


report["time"]=str(
    datetime.now()
)



# 检查Pod

report["pod_check"]=check_pod()



# 检查nginx服务

report["port_check"]=check_port(
    "127.0.0.1",
    80
)



# 检查网站

report["url_check"]=check_url(
    "http://127.0.0.1"
)



if (
    report["pod_check"]["status"]=="OK"
    and
    report["url_check"]["status"]=="OK"
):

    report["result"]="SUCCESS"

else:

    report["result"]="FAILED"



with open(
    "report.json",
    "w",
    encoding="utf-8"
) as f:


    json.dump(
        report,
        f,
        indent=4,
        ensure_ascii=False
    )


print("巡检完成")