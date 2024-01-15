import machine
import network
import time
import ubinascii

from umqtt.simple import MQTTClient

HUB_PORT = 4444
PICO_ID = ubinascii.hexlify(machine.unique_id())
OUTPUT_TOPIC = b"/heater/status"


def load_file(filename: str, mode: str = "br"):
    with open(filename, mode) as f:
        return f.read()


heater_pin = None


def main() -> None:
    global heater_pin
    heater_pin = machine.Pin(22, machine.Pin.OUT)
    heater_pin.high()  # Turn off heater

    wifi_ap, wifi_password, hub_addr, mqtt_user, mqtt_password = (
        load_file("config_mqtt", "r").strip().split("\n")
    )

    wlan = network.WLAN()
    wlan.active(True)
    wlan.connect(wifi_ap, wifi_password)
    connect_attempts = 0

    while True:
        wlan_status = wlan.status()
        if wlan_status == network.STAT_GOT_IP:
            print(f"Connected to {wifi_ap}.")
            break

        print(f"No connection yet (code: {wlan_status}).")
        print("Waiting for network.")

        connect_attempts += 1
        if connect_attempts % 10 == 0:
            wlan.connect(wifi_ap, wifi_password)

        time.sleep(1)

    print("Connecting to hub…", end="")
    c = MQTTClient(
        "umqtt_client", hub_addr, user=mqtt_user, password=mqtt_password
    )
    c.connect()
    print(" connected.")

    cmd_topic = b"/heater/cmd"
    c.set_callback(mqtt_callback)
    c.subscribe(cmd_topic)

    timer = machine.Timer()
    timer.init(
        freq=0.025, mode=machine.Timer.PERIODIC, callback=lambda t: status(c)
    )
    status(c)

    try:
        while True:
            print("Waiting for a command")
            c.wait_msg()
            status(c)
            time.sleep(1)
    finally:
        c.disconnect()


# Utils
def read_temperature_sensor() -> float:
    adc = machine.ADC(4)
    voltage = adc.read_u16() * (3.3 / (65536))
    temperature_celcius = 27 - (voltage - 0.706) / 0.001721
    # For debugging purposes
    print(f"Temperature: {temperature_celcius}°C")
    return temperature_celcius


# RPC
def mqtt_callback(topic: bytes, msg: bytes) -> None:
    print("Received command:", msg)
    if msg == b"ON":
        set_heating(1)
    elif msg == b"OFF":
        set_heating(0)


def set_heating(on: int) -> tuple[bool]:
    if on:
        heater_pin.low()
        print("Turned heater on.")
    else:
        heater_pin.high()
        print("Turned heater off.")


def status(c):
    on_off = b"ON" if heater_pin.value() == 0 else b"OFF"
    c.publish(
        OUTPUT_TOPIC,
        b"".join((b'{"status": "', on_off, b'", "id": "', PICO_ID, b'"}')),
    )


main()
