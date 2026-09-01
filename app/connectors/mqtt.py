from __future__ import annotations

def mqtt_available() -> bool:
    try:
        import paho.mqtt.client  # noqa
        return True
    except Exception:
        return False

def publish_json(host: str, topic: str, payload: str, port: int = 1883) -> None:
    import paho.mqtt.publish as publish
    publish.single(topic, payload=payload, hostname=host, port=port)
