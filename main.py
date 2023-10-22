import machine
import network
import time
import socket
import ssl

HUB_PORT = 4444


def load_file(filename: str, mode: str = "br"):
    with open(filename, mode) as f:
        return f.read()


def main() -> None:
    heater_pin = machine.Pin(22, machine.Pin.OUT)
    heater_pin.high()

    client_cert = load_file("client.crt.der")
    client_key = load_file("client.key.der")
    server_ca = load_file("server.crt.der")
    hub_addr, wifi_ap, wifi_password = (
        load_file("config", "r").strip().split("\n")
    )

    wlan = network.WLAN()
    wlan.active(True)
    wlan.connect(wifi_ap, wifi_password)

    while True:
        wlan_status = wlan.status()
        if wlan_status == network.STAT_GOT_IP:
            print(f"Connected to {wifi_ap}.")
            break

        print("No connection yet. Code:", wlan_status)
        print("Waiting for network.")
        time.sleep(1)

    print("Connecting to hub.")
    s = socket.socket()
    addr_info = socket.getaddrinfo(hub_addr, HUB_PORT)[0][-1]
    s.connect(addr_info)

    ssls = ssl.wrap_socket(
        s,
        key=client_key,
        cert=client_cert,
        cadata=server_ca,
        cert_reqs=ssl.CERT_REQUIRED,
    )

    while True:
        d = ssls.read(512)
        if not d:
            return
        print("Got:", d)


# Utils
def readTemperatureSensor() -> float:
    adc = machine.ADC(4)
    voltage = adc.read_u16() * (3.3 / (65536))
    temperature_celcius = 27 - (voltage - 0.706) / 0.001721
    # For debugging purposes
    print(f"Temperature: {temperature_celcius}°C")
    return temperature_celcius


# RPC
def setHeating(on: bool) -> bool:
    return False


def getTemperature() -> float:
    return readTemperatureSensor()


# A tuple of:
# 1. struct schema for arguments
# 2. struct schema for return type
# 3. a function to pass the arguments to
rpc_table = (("!?", "!?", setHeating), ("", "!f", getTemperature))

# Establish mTLS connection

while True:
    # Read the TLS socket for RPC commands, decode and call the right function
    time.sleep(0.5)
