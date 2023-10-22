import machine
import time


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
