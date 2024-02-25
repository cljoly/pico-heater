# Pico Heater

MicroPython program to remotely turn heating on and off.
- Listens on MQTT topic `/heater/status` for commands
  - `ON` turns the heating ON, untill OFF is received
  - `OFF` turns the heating OFF
- Will broadcast the current status (ID of the pico board and whether heating is turned ON or OFF) on MQTT after every change and every 40 seconds

Thus, the pico becomes a small component meant to be interfaced with:
- a control system (either your own script or [home assistant][ha])
- a relay to actually send the commands to a boiler

## Cert generation

See https://security.stackexchange.com/a/93712/

[ha]: https://www.home-assistant.io/
