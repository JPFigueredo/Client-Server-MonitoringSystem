import platform
import pickle
import socket
import sys
import threading
import time
from queue import Queue

import cpuinfo
import nmap
import psutil

gb = 1024 * 1024 * 1024


def get_plataform_info():
    return {
        "name": platform.node(),
        "system": platform.system(),
        "plataform": platform.platform(),
        "realese": platform.release(),
        "version": platform.version(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_compiler": platform.python_compiler(),
    }


def get_cpu_info():
    cpu_info = cpuinfo.get_cpu_info()
    cpu_freq = psutil.cpu_freq()

    return {
        "name": cpu_info["brand_raw"],
        "architecture": cpu_info["arch"],
        "bits": cpu_info["bits"],
        "min_frequency": round(cpu_freq.min, 2),
        "max_frequency": round(cpu_freq.max, 2),
        "current_frequency": round(cpu_freq.current, 2),
        "physical_cores_number": psutil.cpu_count(logical=False),
        "cores_number": psutil.cpu_count(logical=True),
        "usage": psutil.cpu_percent(interval=1),
        "cores_usage": psutil.cpu_percent(interval=1, percpu=True),
    }


def get_ram_info():
    ram_info = psutil.virtual_memory()

    return {
        "total_gb": round(ram_info.total / gb, 2),
        "used_gb": round(ram_info.used / gb, 2),
        "available_gb": round(ram_info.available / gb, 2),
        "percent_usage": ram_info.percent,
        "percent_available": round(100 - ram_info.percent, 1),
    }


def get_disk_info():
    disk_usage = psutil.disk_usage(".")

    return {
        "gize_gb": round(disk_usage.total / gb, 2),
        "used_gb": round(disk_usage.used / gb, 2),
        "available_gb": round(disk_usage.free / gb, 2),
        "used_percent": disk_usage.percent,
        "available_percent": round(100 - disk_usage.percent, 1),
    }


def get_network_info():
    interfaces = []

    for interface_name, interface_addresses in psutil.net_if_addrs().items():
        for address in interface_addresses:
            if address.family == socket.AF_INET:
                interfaces.append({
                    "interface": interface_name,
                    "address": address.address,
                    "netmask": address.netmask if address.netmask is not None else "Ausente",
                })

    nm = nmap.PortScanner()
    nm.scan("127.0.0.1", "22-443")
    nm.command_line()
    nm.scaninfo()

    hosts = []

    for host in nm.all_hosts():
        host_info = {
            "host": host, 
            "name": nm[host].hostname(),
            "state": nm[host].state(), 
            "protocols": []
        }

        for protocol in nm[host].all_protocols():
            protocol = {"protocol": protocol, "ports": []}

            ports_list = nm[host][protocol["protocol"]].keys()
            list(ports_list).sort()
            for port in ports_list:
                protocol["ports"].append({"port": port, "state": nm[host][protocol["protocol"]][port]["state"]})

            host_info["protocols"].append(protocol)

    return {"interfaces": interfaces, "hosts": hosts}


def get_processes():
    processes = []

    pids = psutil.pids()
    pids.reverse()

    for pid in pids:
        process = psutil.Process(pid)
        try:
            process_data = {
                "name": process.name(),
                "used_memory": process.memory_info().rss / 1024 / 1024,
                "memory_use_percent": process.memory_percent(),
                "used_threads": process.num_threads(),
                "created_time": process.cpu_times().user,
                "created_date": time.ctime(process.create_time()),
            }
            processes.append(process_data)
        except:
            pass

    return processes


queue_data = Queue()


def get_data(data_name: str, request_uuid: str):
    get_info = {
        "system": get_plataform_info,
        "cpu": get_cpu_info,
        "ram": get_ram_info,
        "disk": get_disk_info,
        "network": get_network_info,
        "processes": get_processes,
    }

    queue_data.put({"uuid": request_uuid, "data": get_info[data_name]()})


socket_object = socket.socket()
host = socket.gethostname()
print()
port = int(input("Informe a porta do servidor: "))
socket_object.bind((host, port))

print()

print("Servidor iniciado")

socket_object.listen(5)
connection, addr = socket_object.accept()

print(f"Conexão estabelecida com {addr[0]}:{addr[1]}")

while True:
    if queue_data.empty():
        received_data = connection.recv(1024)

        if not received_data:
            print("Servidor encerrado")
            break

        formatted_data = pickle.loads(received_data)

        get_data_thread = threading.Thread(target=get_data, args=(formatted_data["data"], formatted_data["uuid"]))
        get_data_thread.start()

    else:
        connection.send(pickle.dumps(queue_data.get()))

connection.close()
socket.close(0)
sys.exit()
