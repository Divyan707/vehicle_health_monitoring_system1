Vehicle Health Monitor (local mode)

Folder layout:
  app.py
  common.py
  requirements.txt
  static\html.txt

To run in Windows PowerShell from this folder:
  py -m pip install -r requirements.txt
  py -m uvicorn app:app --host 127.0.0.1 --port 8000

Open http://localhost:8000. The dashboard uses the built-in simulator by default,
so no MQTT broker or separate gateway is required. Set MQTT_ENABLED=1 only when
using a running MQTT broker and gateway.
