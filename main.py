import machine
import time


def getTemperature():
    adc = machine.ADC(4)
    voltage = adc.read_u16() * (3.3 / (65536))
    temperature_celcius = 27 - (voltage - 0.706) / 0.001721
    # For debugging purposes
    print(f"Temperature: {temperature_celcius}°C")
    return temperature_celcius


while True:
    getTemperature()
    time.sleep(0.5)
