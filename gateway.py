"""Gateway: simulated vehicle -> virtual CAN bus -> MQTT.   Run:  python gateway.py
With real hardware: remove the simulator part and change the can.Bus(...) settings."""
import json, random, struct, time
import logging

import can
import paho.mqtt.client as mqtt

from common import *

tx = can.Bus(interface="virtual", channel="vhm")
rx = can.Bus(interface="virtual", channel="vhm")
sim = {k: float(s["sim"]) for k, s in SENSORS.items()}
vals = {k: None for k in SENSORS}
state = dict(force=False, paused=False)
over = {}
spd_t, n, trip = 0, 0, 0.0


def on_message(c, u, msg):
    try:
        m = json.loads(msg.payload)
    except ValueError:
        return
    cmd = m.get("cmd")
    if cmd == "force": state["force"] = bool(m.get("value"))
    elif cmd == "pause": state["paused"] = not state["paused"]
    elif cmd == "clear": over.clear()
    elif cmd == "override":
        try:
            k, v = m["key"], float(m["value"])
            if k in SENSORS and 0 <= v <= SENSORS[k]["max"]:
                over[k] = v
        except (KeyError, ValueError, TypeError):
            pass


def targets():
    global spd_t
    if n % 80 == 0:
        spd_t = random.choice([0, 30, 50, 60, 80, 90])
    spd = sim["speed"]
    t = {"speed": spd_t, "rpm": 800 + spd * 30}
    t["throttle"] = min(100, max(0, 8 + (spd_t - spd) * 1.2 + spd * 0.2))
    t["load"] = 15 + t["throttle"] * 0.6
    t["temp"] = 86 + t["load"] * 0.08
    t["volt"], t["vib"] = 13.7, 0.1 + spd * 0.002
    t["oil"] = 1.5 + sim["rpm"] / 2500
    t["intake"] = 33 + t["load"] * 0.1
    t["fuel"] = sim["fuel"] - 0.01
    for k in ("tfl", "tfr", "trl", "trr"):
        t[k] = 32
    if state["force"]:
        t.update(FAULT)
    elif sim["fuel"] < 15:
        sim["fuel"] = 75.0
    return t


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway")
if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASS)
def on_connect(c, u, f, reason_code, p):
    if reason_code.is_failure:
        log.error("MQTT connection to %s:%s failed: %s", MQTT_HOST, MQTT_PORT, reason_code)
        return
    result, _ = c.subscribe(PREFIX + "/control")
    log.info("MQTT connected to %s:%s; subscribed to %s/control (result=%s)",
             MQTT_HOST, MQTT_PORT, PREFIX, result)


client.on_connect = on_connect
client.on_message = on_message
client.connect_async(MQTT_HOST, MQTT_PORT)  # retry while the broker starts
client.loop_start()
log.info("Gateway started; publishing to %s:%s topic %s/telemetry", MQTT_HOST, MQTT_PORT, PREFIX)

while True:
    if not state["paused"]:
        n += 1
        for k, v in targets().items():
            sim[k] += (v - sim[k]) * (0.03 if k == "speed" else (1 if k == "fuel" and not state["force"] else 0.1))
        trip += sim["speed"] / 3600 * 0.1
        for k, s in SENSORS.items():  # 1) put each reading on the CAN bus
            v = over.get(k, max(0.0, sim[k] + random.gauss(0, s["noise"])))
            raw = min(65535, max(0, int(round(v * s["scale"]))))
            tx.send(can.Message(arbitration_id=s["id"], data=struct.pack(">H", raw), is_extended_id=False))
        while (m := rx.recv(0)) is not None:  # 2) read the CAN frames back
            for k, s in SENSORS.items():
                if m.arbitration_id == s["id"]:
                    vals[k] = struct.unpack(">H", bytes(m.data[:2]))[0] / s["scale"]
    client.publish(PREFIX + "/telemetry", json.dumps(
        dict(vals=vals, force=state["force"], paused=state["paused"], over=list(over), trip=round(trip, 2))))
    time.sleep(0.1)
