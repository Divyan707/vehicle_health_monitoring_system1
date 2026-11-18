"""Shared settings used by both gateway.py and app.py."""
import os

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
PREFIX = os.getenv("MQTT_PREFIX", "vehicle/01")  # topics: <PREFIX>/telemetry and <PREFIX>/control


def S(id, name, unit, scale, dec, wl, cl, wh, ch, rng, grp, sim, noise=0.0, mx=None):
    return dict(id=id, name=name, unit=unit, scale=scale, dec=dec, wl=wl, cl=cl, wh=wh, ch=ch,
                rng=rng, grp=grp, sim=sim, noise=noise, max=mx or rng[1])


SENSORS = {
    "speed":  S(0x103, "Vehicle speed", "km/h", 10, 0, None, None, 110, 140, [0, 200], "drive", 0, 0.3, 250),
    "rpm":    S(0x104, "Engine speed", "rpm", 1, 0, None, None, 5500, 6500, [0, 8000], "drive", 800, 8, 8000),
    "throttle": S(0x105, "Throttle position", "%", 10, 0, None, None, None, None, [0, 100], "drive", 8, 0.3),
    "load":   S(0x106, "Engine load", "%", 10, 0, None, None, 90, 98, [0, 100], "drive", 15, 0.4),
    "temp":   S(0x100, "Engine temperature", "°C", 10, 1, None, None, 100, 110, [0, 150], "engine", 88, 0.15, 200),
    "oil":    S(0x107, "Oil pressure", "bar", 100, 2, 1.2, 0.8, 5.0, 6.0, [0, 6], "engine", 1.8, 0.02),
    "intake": S(0x109, "Intake air temp", "°C", 10, 0, None, None, 60, 80, [0, 100], "engine", 35, 0.2),
    "fuel":   S(0x108, "Fuel level", "%", 10, 0, 20, 10, None, None, [0, 100], "engine", 75, 0),
    "volt":   S(0x101, "Battery voltage", "V", 100, 2, 12.0, 11.0, 14.8, 15.5, [9, 17], "engine", 13.7, 0.02, 30),
    "vib":    S(0x102, "Engine vibration", "g", 1000, 3, None, None, 0.5, 1.0, [0, 1.5], "engine", 0.12, 0.01, 10),
    "tfl":    S(0x10A, "Tyre front-left", "psi", 10, 1, 28, 24, 40, 45, [20, 50], "chassis", 32, 0.05),
    "tfr":    S(0x10B, "Tyre front-right", "psi", 10, 1, 28, 24, 40, 45, [20, 50], "chassis", 32, 0.05),
    "trl":    S(0x10C, "Tyre rear-left", "psi", 10, 1, 28, 24, 40, 45, [20, 50], "chassis", 32, 0.05),
    "trr":    S(0x10D, "Tyre rear-right", "psi", 10, 1, 28, 24, 40, 45, [20, 50], "chassis", 32, 0.05),
}
LEVELS = ["NORMAL", "WARNING", "CRITICAL"]
FAULT = dict(temp=115, volt=10.8, vib=1.2, oil=0.7, fuel=8, tfl=22)


def level_of(v, s):
    if (s["ch"] is not None and v >= s["ch"]) or (s["cl"] is not None and v <= s["cl"]):
        return 2
    if (s["wh"] is not None and v >= s["wh"]) or (s["wl"] is not None and v <= s["wl"]):
        return 1
    return 0
