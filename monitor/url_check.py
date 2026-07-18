import requests
import time



def check_url(url):

    result={}


    try:

        start=time.time()


        r=requests.get(
            url,
            timeout=5
        )


        cost=round(
            time.time()-start,
            3
        )


        result["url"]=url
        result["code"]=r.status_code
        result["response_time"]=cost


        if r.status_code==200:

            result["status"]="OK"

        else:

            result["status"]="ERROR"



    except Exception as e:


        result["status"]="ERROR"
        result["error"]=str(e)


    return result