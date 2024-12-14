import machine
import network
import time
import ubinascii
from machine import WDT

from umqtt.simple import MQTTClient

HUB_PORT = 4444
PICO_ID = ubinascii.hexlify(machine.unique_id())
OUTPUT_TOPIC = b"/heater/status"

ON_SAFETY_COUNTER_FREQ = 1 / 60
ON_SAFETY_COUNTER_INIT = 3600 * ON_SAFETY_COUNTER_FREQ


def load_file(filename: str, mode: str = "br"):
    with open(filename, mode) as f:
        return f.read()


heater_pin = None
wdt = None

on_safety_counter = ON_SAFETY_COUNTER_INIT

led_pin = machine.Pin("LED", machine.Pin.OUT)
button_on_pin = machine.Pin(20, machine.Pin.IN, machine.Pin.PULL_DOWN)
button_off_pin = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_DOWN)


def main() -> None:
    global heater_pin
    global wdt
    # Ensure we restart if we lose WIFI connection or some other issue (max
    # value: about 8.3s)
    wdt = WDT(timeout=8300)

    led_blink_timer = machine.Timer()
    led_blink_timer.init(
        freq=2, mode=machine.Timer.PERIODIC, callback=lambda t: led_pin.toggle()
    )
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

        wdt.feed()
        time.sleep(1)

    wdt.feed()
    print("Connecting to hub…", end="")
    c = MQTTClient(
        "umqtt_client",
        hub_addr,
        user=mqtt_user,
        password=mqtt_password,
    )
    # Make sure status is reset on disconnect. Must be done before connect
    c.set_last_will(
        OUTPUT_TOPIC,
        craft_status(),
        retain=True,
    )
    c.connect()
    print(" connected.")
    led_blink_timer.deinit()
    led_pin.value(1)

    cmd_topic = b"/heater/cmd"
    c.set_callback(mqtt_callback)
    c.subscribe(cmd_topic)

    timer_on_safety_counter = machine.Timer()
    timer_on_safety_counter.init(
        freq=ON_SAFETY_COUNTER_FREQ,
        mode=machine.Timer.PERIODIC,
        callback=lambda t: watch_on_for_safety(c),
    )

    timer = machine.Timer()
    timer.init(
        freq=0.0003,  # About 1 hour
        mode=machine.Timer.PERIODIC,
        callback=lambda t: status(c),
    )
    status(c)

    try:
        while True:
            print("Check for any command")
            # Will execute any pending command or return immediately
            op = c.check_msg()
            wdt.feed()  # check_msg would have failed if we could not reach MQTT
            if op is not None:
                # We likely need to update the status
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
    global on_safety_counter
    if on:
        heater_pin.low()
        on_safety_counter = ON_SAFETY_COUNTER_INIT
        print("Turned heater on.")
    else:
        heater_pin.high()
        print("Turned heater off.")


def button_pressed(pin, active_value, action) -> None:
    value = pin.value()
    if value != active_value:
        return

    action()


ON_IRQ = lambda p: button_pressed(p, 1, lambda: set_heating(True))
OFF_IRQ = lambda p: button_pressed(p, 1, lambda: set_heating(False))

button_on_pin.irq(ON_IRQ)
button_off_pin.irq(OFF_IRQ)


def craft_status():
    on_off = b"ON" if heater_pin.value() == 0 else b"OFF"
    return b"".join((b'{"status":"', on_off, b'","id":"', PICO_ID, b'"}'))


def status(c):
    msg = craft_status()
    c.publish(
        OUTPUT_TOPIC,
        msg,
        retain=True,
    )
    print("Feed the watch dog")
    wdt.feed()


# Turn off if we don’t receive ON in a while (for instance, an hour). This ensures the heater
# doesn’t remain ON by mistake
def watch_on_for_safety(c):
    global on_safety_counter
    if on_safety_counter > 0:
        on_safety_counter -= 1
        print(f"{on_safety_counter=}")
    else:
        set_heating(0)
        print("No message received in a while, turning off")
        status(c)


main()
