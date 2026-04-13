import json
import asyncio
import aiohttp
import os
import threading
import tkinter as tk
from tkinter import ttk

JSON_PATH = "instagram.json"
TIMEOUT = 5
RETRIES = 2
CONCURRENT_REQUESTS = 100

headers = {
    "User-Agent": "Mozilla/5.0"
}

working_urls = []

stats = {
    "ok": 0,
    "warn": 0,
    "error": 0
}


class App:
    def __init__(self, root, total):
        self.root = root
        self.root.title("Scanner URLs")
        self.root.geometry("500x220")

        self.label = tk.Label(root, text="Scan en cours...", font=("Arial", 12))
        self.label.pack(pady=10)

        self.progress = ttk.Progressbar(root, length=400, mode="determinate")
        self.progress.pack(pady=10)
        self.progress["maximum"] = total

        self.status = tk.Label(root, text="0 / 0", font=("Arial", 10))
        self.status.pack()

        self.stats_label = tk.Label(root, text="", font=("Arial", 10))
        self.stats_label.pack(pady=5)

        self.current = 0

    def update(self):
        self.current += 1
        self.progress["value"] = self.current
        self.status.config(text=f"{self.current} / {int(self.progress['maximum'])}")

        self.stats_label.config(
            text=f"OK: {stats['ok']} | WARN: {stats['warn']} | ERROR: {stats['error']}"
        )

        self.root.update_idletasks()

    def done(self, count, path):
        self.label.config(text=f"✅ Terminé : {count} valides")
        self.status.config(text=f"Fichier : {path}")


async def check_url(session, entry):
    domain = entry.get("subdomain")

    urls = [
        f"http://{domain}",
        f"https://{domain}"
    ]

    for url in urls:
        for attempt in range(RETRIES):
            try:
                timeout = aiohttp.ClientTimeout(total=TIMEOUT)

                async with session.get(url, timeout=timeout) as response:
                    status = response.status

                    if status < 400:
                        print(f"[OK {status}] {url}")
                        stats["ok"] += 1
                        return url

                    elif status < 500:
                        print(f"[WARN {status}] {url}")
                        stats["warn"] += 1

                    else:
                        print(f"[ERROR {status}] {url}")
                        stats["error"] += 1

            except asyncio.TimeoutError:
                print(f"[TIMEOUT] {url} (try {attempt+1})")
                await asyncio.sleep(1)

            except Exception:
                print(f"[ERROR] {url}")
                stats["error"] += 1
                await asyncio.sleep(0.5)

    return None


async def scan(data, app):
    global working_urls

    connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS, ssl=False)

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [check_url(session, entry) for entry in data]

        for future in asyncio.as_completed(tasks):
            result = await future

            if result:
                working_urls.append(result)

            app.update()

    output_path = os.path.join(os.path.dirname(JSON_PATH), "working_urls.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        for url in working_urls:
            f.write(url + "\n")

    app.done(len(working_urls), output_path)


def start_scan(app, data):
    asyncio.run(scan(data, app))


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    root = tk.Tk()
    app = App(root, len(data))

    threading.Thread(target=start_scan, args=(app, data), daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()
