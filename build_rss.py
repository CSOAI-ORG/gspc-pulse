#!/usr/bin/env python3
"""build_rss.py — regenerate rss.xml from alerts.jsonl (feed-reader surface).
Runs standalone or via engine build. Paths via pathlib from __file__."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "alerts.jsonl"
OUT = HERE / "rss.xml"


def build():
    items = []
    if SRC.exists():
        for line in SRC.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                a = json.loads(line)
                items.append((a.get("ts", ""), a.get("kind", "alert"),
                              json.dumps(a.get("changes", {}), sort_keys=True)[:200]))
            except ValueError:
                pass
    items.sort(reverse=True)
    rss = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0"><channel>',
           "<title>GSPC Live Pulse — alerts</title>",
           "<link>https://huggingface.co/datasets/csoai/evidence-index</link>",
           "<description>GSPC pulse alert stream — frozen deltas, KEV webhook events, curriculum freezes. Measurement, not endorsement.</description>",
           "<language>en</language>"]
    for ts, kind, detail in items[:10]:
        rss.append("<item><title>%s — %s</title><description>%s</description>"
                   "<pubDate>%s</pubDate><guid>%s-%s</guid></item>"
                   % (kind, ts[:10], detail[:150], ts, kind, ts))
    rss.append("</channel></rss>")
    OUT.write_text("\n".join(rss))
    print("rss.xml: %d items" % min(len(items), 10))
    return 0


if __name__ == "__main__":
    sys_exit = build()
    import sys
    sys.exit(sys_exit)
