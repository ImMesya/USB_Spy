import win32com.client
import time
import socket
"""
Client for USB_SPY
PORT_UDP for echo client send self ip address to USB_SPY and
PORT_TCP_SERVER for connected SERVER USB_SPY received IP_ADDRESS_SERVER_USB and PORT_SERVER_USB
"""
PORT_UDP=4545
PORT_TCP_SERVER=5000
IP_ADDRESS_SERVER_USB=None
PORT_SERVER_USB=None

#searching logical_disk and return SerialNumber, Name of Logical Disk
def get_devices():
    wmi=win32com.client.GetObject("winmgmts:")
    return {item.VolumeSerialNumber:(item.Name,item.VolumeName) for item in wmi.InstancesOf("Win32_LogicalDisk")}

#create udp socket for broadcast
def create_broadcast():
    udp_s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
    udp_s.settimeout(5)
    return udp_s

#send my ip to server and receive server's ip and port
def server_ip():
    ip_=None
    port_=None
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((socket.gethostbyname(socket.gethostname()), PORT_TCP_SERVER))
    s.settimeout(2)
    s.listen(1)
    try:
        c,a=s.accept()
        data=c.recv(512)
        if data.decode('utf-8').find('show'):
            port_=((data.decode('utf-8').split(' ')[-1]))
            ip_=a[0]
            c.send("Ok".encode('utf-8'))
            c.close()
    except:
        pass
    s.close()
    return ip_,port_

#echo broadcast and waiting connection to server
def update_ip():
    while True:
        with create_broadcast() as flood:
            flood.sendto("give_ip {}".format(socket.gethostbyname(socket.gethostname())).encode('utf-8'),('192.168.3.255',PORT_UDP))
            ip_, port_ =server_ip()
            if ip_ is not None:
                return ip_, port_

#waiting for connected or disconnected devices
def main():
    before=get_devices()
    while True:
        after=get_devices()
        if len(after)>len(before):
            drives = [(item, after[item]) for item in after if item not in before]
            flag=True
        elif len(before)>len(after):
            drives=[(item, before[item]) for item in before if item not in after]
            flag=False
        else:
            drives=[]
        if drives:
            for disk in drives:
                if flag:
                    g_client((disk, "connect"))
                else:
                    g_client((disk, "disconnect"))
            before=after
        time.sleep(3)

#check connection to server
def g_client(message):
    try:
        client(message)
    except:
        global IP_ADDRESS_SERVER_USB
        global PORT_SERVER_USB
        IP_ADDRESS_SERVER_USB, PORT_SERVER_USB=update_ip()
        client(message)

#send message to server
def client(message):
    #global IP, PORT
    s=socket.socket()
    name=socket.gethostname()
    s.connect((IP_ADDRESS_SERVER_USB,int(PORT_SERVER_USB)))
    message=("{}||{}||{}||{}||{}||".format(name,s.getsockname()[0], message[1], (message[0][1][0]+message[0][1][1]), message[0][0]))
    s.sendall(message.encode("utf-8"))
    s.close()

if __name__ == '__main__':
    main()
