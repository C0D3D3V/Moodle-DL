import json
from typing import Optional

import requests


class NtfyShooter:
    def __init__(self, topic: str, server: Optional[str] = None):
        self.topic = topic
        self.server = server or "https://ntfy.sh/"

    def send(self, title: str, message: str, source_url: Optional[str] = None):
        data = {"topic": self.topic, "title": title, "message": message}
        if source_url:
            data["click"] = source_url
            view_action = {"action": "view", "label": "View", "url": source_url}
            data.setdefault("actions", []).append(view_action)

        resp = requests.post(self.server, data=json.dumps(data))
        resp.raise_for_status()
