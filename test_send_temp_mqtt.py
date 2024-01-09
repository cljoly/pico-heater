import machine
import network
import time
import ubinascii

from umqtt.simple import MQTTClient

HUB_PORT = 4444
PICO_ID = ubinascii.hexlify(machine.unique_id())

def load_file(filename: str, mode: str = "br"):
    with open(filename, mode) as f:
        return f.read()


def main() -> None:
    wifi_ap, wifi_password, hub_addr, mqtt_user, mqtt_password = (
        load_file("config_mqtt", "r").strip().split("\n")
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
        # time.sleep(1)
        machine.lightsleep(1000)

    print("Connecting to hub.")
    c = MQTTClient("umqtt_client", hub_addr, user=mqtt_user, password=mqtt_password)
    c.connect()
    topic = b"".join((b"/pico/", PICO_ID, b"/temp"))
    listen_topic = b"".join((b"/pico/", PICO_ID, b"/get_temp"))
    c.set_callback(lambda topic, msg: print(f"Received: {msg} on topic: {topic}"))
    c.subscribe(listen_topic)

    try:
        while True:
            c.wait_msg()
            c.publish(topic, bytes(str(getTemperature()[0]), "utf-8"))
            print(f"Published to topic: {topic}")
            time.sleep(1000)
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


def getTemperature() -> tuple[float]:
    return (read_temperature_sensor(),)


main()
