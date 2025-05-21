import os
import json


def load_history(history_filename):
    history = set()
    if os.path.exists(history_filename):
        with open(history_filename, encoding="utf-8") as f:
            for line in f:
                history.add(line.strip())
    return history


def save_history(history_filename, entries, history):
    with open(history_filename, "a", encoding="utf-8") as f:
        for item in entries:
            if item["title"] not in history:
                f.write(item["title"] + "\n")


def save_history_json(json_filename, entries):
    # entries: list of dicts with at least 'url' and 'title', optionally 'rank', 'users'
    data = []
    for item in entries:
        d = {}
        if "rank" in item:
            d["rank"] = item["rank"]
        if "url" in item:
            d["url"] = item["url"]
        if "title" in item:
            d["title"] = item["title"]
        if "users" in item:
            d["users"] = item["users"]
        if "summary" in item:
            d["summary"] = item["summary"]
        data.append(d)
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_history_json(json_filename):
    if not os.path.exists(json_filename):
        return []
    with open(json_filename, encoding="utf-8") as f:
        return json.load(f)
