#!/usr/bin/env python3
"""
GitHub Actions: Update data.json from Rapaport API bulk list endpoint.
"""

import os, requests, json, time
from pathlib import Path

AUTH_URL  = "https://authztoken.api.rapaport.com/api/get"
LIST_URL = "https://technet.rapnetapis.com/pricelist/api/Prices/list"
DATA_JSON = Path(__file__).parent.parent / "data.json"

def get_token():
    r = requests.post(AUTH_URL, json={
        "client_id": os.environ["RAPAPORT_CLIENT_ID"],
        "client_secret": os.environ["RAPAPORT_CLIENT_SECRET"]
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_csv(shape, token):
    for attempt in range(5):
        r = requests.get(LIST_URL, params={"shape": shape, "csvnormalized": "true"},
                        headers={"Authorization": f"Bearer {token}"}, timeout=60)
        if r.status_code == 429:
            time.sleep((attempt + 1) * 10)
            continue
        r.raise_for_status()
        return r.text
    raise RuntimeError("Rate limited")

def parse_csv(text):
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    headers = [h.strip().lower() for h in lines[0].split(',')]
    rows = []
    for line in lines[1:]:
        vals = [v.strip() for v in line.split(',')]
        rows.append(dict(zip(headers, vals)))
    return rows

def main():
    print("Fetching Round list...")
    token = get_token()
    csv_round = fetch_csv("Round", token)
    print("Fetching Pear list...")
    csv_pear = fetch_csv("Pear", token)

    updated = {"round": {}, "pear": {}}

    for shape_key, csv_text in [("round", csv_round), ("pear", csv_pear)]:
        rows = parse_csv(csv_text)
        grouped = {}
        for row in rows:
            cr = row.get('carat_range', '').strip()
            if not cr:
                continue
            grouped.setdefault(cr, {})
            color = row.get('color', '').upper().strip()
            if not color:
                continue
            grouped[cr][color] = {}
            for k, v in row.items():
                if k in ('carat_range', 'color', 'shape'):
                    continue
                grouped[cr][color][k.upper()] = v

        updated[shape_key] = grouped

    from datetime import date
    updated["date"] = date.today().strftime("%m/%d/%y")

    with open(DATA_JSON, "w") as f:
        json.dump(updated, f, indent=2)

    print(f"Written {DATA_JSON} dated {updated['date']}")

if __name__ == "__main__":
    main()
