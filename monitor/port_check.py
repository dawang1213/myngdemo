import socket



def check_port(host,port):


    result={}


    s=socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )


    s.settimeout(3)


    try:

        s.connect(
            (host,port)
        )

        result["status"]="OPEN"



    except Exception as e:

        result["status"]="CLOSED"
        result["error"]=str(e)



    finally:

        s.close()



    result["host"]=host
    result["port"]=port


    return result