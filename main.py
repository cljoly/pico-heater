import machine
import network
import time
import socket
import ssl
import struct
from collections import namedtuple

HUB_PORT = 4444


def load_file(filename: str, mode: str = "br"):
    with open(filename, mode) as f:
        return f.read()


heater_pin = None


def main() -> None:
    global heater_pin
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
    reader = Reader(ssls)

    while True:
        print("Waiting for a command")
        run_command(reader, ssls)


class Reader:
    def __init__(self, reader):
        self.reader = reader
        self.buffer = b""

    def _ensure_buffer_size(self, n: int):
        while len(self.buffer) < n:
            # A bigger size causes the client to hang
            b = self.reader.read(1)
            if len(b) == 0:
                time.sleep(0.1)
            else:
                self.buffer += b

    def peak(self, n: int):
        self._ensure_buffer_size(n)
        return self.buffer[:n]

    def read(self, n: int):
        self._ensure_buffer_size(n)
        b = self.buffer[:n]
        self.buffer = self.buffer[n:]
        return b


# Utils
def read_temperature_sensor() -> float:
    adc = machine.ADC(4)
    voltage = adc.read_u16() * (3.3 / (65536))
    temperature_celcius = 27 - (voltage - 0.706) / 0.001721
    # For debugging purposes
    print(f"Temperature: {temperature_celcius}°C")
    return temperature_celcius


# RPC
def set_heating(on: int) -> tuple[bool]:
    if on:
        heater_pin.low()
        print("Turned heater on.")
    else:
        heater_pin.high()
        print("Turned heater off.")
    return (1,)


def getTemperature() -> tuple[float]:
    return (read_temperature_sensor(),)


Command = namedtuple("Command", ["arg_schema", "arg_return", "fn"])
commands = (
    # Command ID: 0
    Command(arg_schema="!B", arg_return="!B", fn=set_heating),
    # Command ID: 1
    Command(arg_schema="", arg_return="!f", fn=getTemperature),
)


def run_command(reader: Reader, writer) -> None:
    (command_id,) = reader.read(1)
    if not 0 <= command_id < len(commands):
        print("Invalid Command ID, ignoring")
        return
    command = commands[command_id]
    print("Got command", command)
    arg_size = struct.calcsize(command.arg_schema)
    raw_args = reader.read(arg_size)
    args = struct.unpack(command.arg_schema, raw_args)
    print("with args:", args)
    ret = command.fn(*args)
    print("return:", ret)
    if not isinstance(ret, tuple):
        raise Exception("Should return tuple")
    raw_ret = struct.pack(command.arg_return, *ret)
    writer.write(raw_ret)


main()
