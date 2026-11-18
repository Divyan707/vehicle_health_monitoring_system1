"""Vehicle Health Monitor: local simulated dashboard, with optional MQTT input.
Run locally: uvicorn app:app --host 127.0.0.1 --port 8000
Set MQTT_ENABLED=1 to use an external MQTT gateway instead of the built-in simulation.
"""
import asyncio, io, csv, json, os, queue, sqlite3, time, math, random
import logging
from collections import deque
from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from common import *

log = logging.getLogger("uvicorn.error")

DB_FILE = os.getenv("DB_FILE", "vehicle_health.db")
MQTT_ENABLED = os.getenv("MQTT_ENABLED", "0").lower() in ("1", "true", "yes")
DEBOUNCE, STALE_S = 3, 1.0

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS readings (ts REAL, " + ", ".join(f"{k} REAL" for k in SENSORS) + ")")
db.execute("CREATE INDEX IF NOT EXISTS ix_readings_ts ON readings(ts)")
db.execute("CREATE TABLE IF NOT EXISTS alerts (ts REAL, t TEXT, sensor TEXT, level TEXT, value TEXT)")
db.commit()


class Monitor:
    def __init__(self):
        self.clients, self.q = set(), queue.Queue()
        self.val = {k: None for k in SENSORS}
        self.lvl = {k: 0 for k in SENSORS}
        self.cand, self.cnt = dict(self.lvl), dict(self.lvl)
        self.paused = self.force = False
        self.over, self.trip, self.count, self.last_msg = [], 0.0, 0, 0.0
        self.demo_n, self.demo_speed = 0, 0.0
        self.demo_overrides = {}
        self.stamps, self.pending = deque(), []
        rows = db.execute("SELECT t, sensor, level, value FROM alerts ORDER BY ts DESC LIMIT 50").fetchall()
        self.alerts = deque((dict(t=r[0], sensor=r[1], level=r[2], value=r[3]) for r in rows), maxlen=50)
        self.cli = None
        if MQTT_ENABLED:
            self.cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if MQTT_USER:
                self.cli.username_pw_set(MQTT_USER, MQTT_PASS)
            self.cli.on_connect = self.on_connect
            self.cli.on_disconnect = self.on_disconnect
            self.cli.on_message = lambda c, u, msg: self.q.put(msg.payload)
            self.cli.connect_async(MQTT_HOST, MQTT_PORT)
            self.cli.loop_start()
        else:
            log.info("Using built-in vehicle simulation (MQTT disabled)")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection to %s:%s failed: %s", MQTT_HOST, MQTT_PORT, reason_code)
            return
        result, _ = client.subscribe(PREFIX + "/telemetry")
        log.info("MQTT connected to %s:%s; subscribed to %s/telemetry (result=%s)",
                 MQTT_HOST, MQTT_PORT, PREFIX, result)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if reason_code.is_failure:
            log.warning("MQTT disconnected: %s", reason_code)

    def drain(self):
        while True:
            try:
                p = self.q.get_nowait()
                m = json.loads(p)
            except queue.Empty:
                return
            except ValueError:
                continue
            now = time.time()
            self.last_msg = now
            self.stamps.append(now)
            self.paused, self.force = m.get("paused", False), m.get("force", False)
            self.over, self.trip = m.get("over", []), m.get("trip", 0.0)
            if self.paused:
                continue
            for k, v in m.get("vals", {}).items():
                if k in SENSORS and v is not None:
                    self.val[k] = v
                    self.debounce(k, v)
            self.count += 1
            if self.count % 10 == 0:  # save one row per second
                db.execute(f"INSERT INTO readings VALUES ({','.join('?' * (len(SENSORS) + 1))})",
                           [now] + [self.val[k] for k in SENSORS])
                db.commit()

    def debounce(self, k, v):
        raw = level_of(v, SENSORS[k])
        if raw == self.cand[k]:
            self.cnt[k] += 1
        else:
            self.cand[k], self.cnt[k] = raw, 1
        if self.cnt[k] >= DEBOUNCE and self.cand[k] != self.lvl[k]:
            self.lvl[k] = self.cand[k]
            s = SENSORS[k]
            a = dict(t=time.strftime("%H:%M:%S"), sensor=s["name"],
                     level="RECOVERED" if self.lvl[k] == 0 else LEVELS[self.lvl[k]],
                     value=f"{v:.{s['dec']}f} {s['unit']}")
            self.alerts.appendleft(a)
            self.pending.append(a)
            db.execute("INSERT INTO alerts VALUES (?,?,?,?,?)", (time.time(), a["t"], a["sensor"], a["level"], a["value"]))
            db.commit()

    def state(self):
        now = time.time()
        while self.stamps and now - self.stamps[0] > 1:
            self.stamps.popleft()
        offline = self.last_msg and now - self.last_msg > STALE_S
        st = dict(type="state", vals=self.val, lvl=self.lvl, stale=list(SENSORS) if offline else [],
                  overall=max(self.lvl.values()), paused=self.paused, force=self.force, over=self.over,
                  fps=len(self.stamps) * len(SENSORS), age=(now - self.last_msg) if self.last_msg else None,
                  trip=self.trip, new_alerts=self.pending)
        self.pending = []
        return st

    def command(self, m):
        if m.get("cmd") in ("force", "pause", "clear", "override"):
            if self.cli:
                self.cli.publish(PREFIX + "/control", json.dumps(m))
                return
            cmd = m["cmd"]
            if cmd == "force":
                self.force = bool(m.get("value"))
            elif cmd == "pause":
                self.paused = not self.paused
            elif cmd == "clear":
                self.demo_overrides.clear()
            elif cmd == "override":
                try:
                    key, value = m["key"], float(m["value"])
                    if key in SENSORS and 0 <= value <= SENSORS[key]["max"]:
                        self.demo_overrides[key] = value
                except (KeyError, TypeError, ValueError):
                    pass

    def demo_frame(self):
        self.demo_n += 1
        target_speed = 35 + 30 * math.sin(self.demo_n / 150)
        self.demo_speed += (target_speed - self.demo_speed) * 0.03
        speed = self.demo_speed
        throttle = min(100, max(0, 8 + (target_speed - speed) * 1.2 + speed * 0.2))
        load = 15 + throttle * 0.6
        vals = {
            "speed": speed, "rpm": 800 + speed * 30, "throttle": throttle,
            "load": load, "temp": 86 + load * 0.08, "volt": 13.7,
            "vib": 0.1 + speed * 0.002, "oil": 1.5 + (800 + speed * 30) / 2500,
            "intake": 33 + load * 0.1, "fuel": max(15, 75 - self.demo_n * 0.001),
            "tfl": 32, "tfr": 32, "trl": 32, "trr": 32,
        }
        if self.force:
            vals.update(FAULT)
        for key, value in vals.items():
            value += random.gauss(0, SENSORS[key]["noise"])
            vals[key] = max(0, self.demo_overrides.get(key, value))
        self.trip += speed / 36000
        return json.dumps(dict(vals=vals, force=self.force, paused=self.paused,
                               over=list(self.demo_overrides), trip=round(self.trip, 2))).encode()

    async def run(self):
        while True:
            if not self.cli:
                self.q.put(self.demo_frame())
            self.drain()
            st = self.state()
            for ws in list(self.clients):
                try:
                    await ws.send_json(st)
                except Exception:
                    self.clients.discard(ws)
            await asyncio.sleep(0.1)


mon = Monitor()


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(mon.run())
    yield
    task.cancel()
    if mon.cli:
        mon.cli.loop_stop()
        mon.cli.disconnect()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_json(dict(type="init", sensors=SENSORS, alerts=list(mon.alerts)))
    mon.clients.add(ws)
    try:
        while True:
            mon.command(await ws.receive_json())
    except (WebSocketDisconnect, Exception):
        mon.clients.discard(ws)


@app.get("/api/meta")
async def meta():
    return SENSORS


@app.get("/api/history")
async def history(sensor: str, minutes: int = 10):
    if sensor not in SENSORS:
        return {"t": [], "v": []}
    rows = db.execute(f"SELECT ts, {sensor} FROM readings WHERE ts > ? AND {sensor} IS NOT NULL ORDER BY ts",
                      (time.time() - minutes * 60,)).fetchall()
    rows = rows[::max(1, len(rows) // 600)]
    return {"t": [r[0] for r in rows], "v": [r[1] for r in rows]}


@app.get("/api/alerts")
async def alerts(limit: int = 100):
    rows = db.execute("SELECT t, sensor, level, value FROM alerts ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [dict(t=r[0], sensor=r[1], level=r[2], value=r[3]) for r in rows]


@app.get("/api/export.csv")
async def export(minutes: int = 60):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["time"] + list(SENSORS))
    for r in db.execute("SELECT * FROM readings WHERE ts > ? ORDER BY ts", (time.time() - minutes * 60,)):
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r[0]))] + list(r[1:]))
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=vehicle_history.csv"})


@app.get("/")
async def index():
    return FileResponse("static/html.txt", media_type="text/html")


@app.get("/history")
async def history_page():
    return FileResponse("static/history.html")


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "mqtt" if mon.cli else "simulation",
            "mqtt_connected": mon.cli.is_connected() if mon.cli else False}


app.mount("/static", StaticFiles(directory="static"), name="static")
