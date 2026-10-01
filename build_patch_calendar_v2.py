from pathlib import Path

p = Path("/app/app.py")
s = p.read_text(encoding="utf-8")
if "from zoneinfo import ZoneInfo" not in s:
    s = s.replace("from datetime import datetime, timedelta", "from datetime import datetime, timedelta\nfrom zoneinfo import ZoneInfo")

# Calendar state is persisted in a third workbook column. Legacy two-column
# rows remain readable but are not treated as confirmed draw dates.
s = s.replace(
    '    ANCHOR_MAGIC = "V58_FORENSIC_ANCHOR_V1"',
    '    ANCHOR_MAGIC = "V58_FORENSIC_ANCHOR_V1"\n'
    '    CALENDAR_STATE_HEADER = "Calendar State"\n'
    '    DRAW_CONFIRMED = "DRAW_CONFIRMED"\n'
    '    LEGACY_CALENDAR_STATE = "LEGACY_PRESENT_TAIL_ONLY"',
)

old = '''    @staticmethod
    def get_vn_time():
        return datetime.utcnow() + timedelta(hours=7)
'''
new = '''    @staticmethod
    def get_vn_time():
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)

    @staticmethod
    def get_vn_time_aware():
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    @staticmethod
    def draw_cutoff_reached():
        now = Utils.get_vn_time_aware()
        return (now.hour, now.minute, now.second) >= (19, 0, 0)
'''
s = s.replace(old, new)

old = '''    def _parse_row(date_raw, raw):
        res = Utils.chuan_hoa_ngay(date_raw)
        if not res: return None
        dt_obj, std = res
        tails, source_tokens = Forensic.parse_raw_prizes(raw)
        return std, {
            "date_obj": dt_obj,
            "prizes_int": tails,
            "raw_str": " ".join(f"{x:02d}" for x in tails),
            "source_prizes": tuple(source_tokens),
        }
'''
new = '''    def _parse_row(date_raw, raw, calendar_state=None):
        res = Utils.chuan_hoa_ngay(date_raw)
        if not res: return None
        dt_obj, std = res
        tails, source_tokens = Forensic.parse_raw_prizes(raw)
        state = calendar_state if calendar_state in {
            Config.DRAW_CONFIRMED, Config.LEGACY_CALENDAR_STATE
        } else Config.LEGACY_CALENDAR_STATE
        return std, {
            "date_obj": dt_obj,
            "prizes_int": tails,
            "raw_str": " ".join(f"{x:02d}" for x in tails),
            "source_prizes": tuple(source_tokens),
            "calendar_state": state,
            "source_set": [],
        }
'''
s = s.replace(old, new)

s = s.replace(
    'DatabaseManager._parse_row(row[0], row[1])',
    'DatabaseManager._parse_row(row[0], row[1], row[2] if len(row) >= 3 else None)'
)

s = s.replace(
    'rows.append({"Ngày": info["date_obj"].strftime("%d/%m/%Y"), "Kết Quả Loto": info["raw_str"]})',
    'rows.append({"Ngày": info["date_obj"].strftime("%d/%m/%Y"), "Kết Quả Loto": info["raw_str"], Config.CALENDAR_STATE_HEADER: info.get("calendar_state", Config.LEGACY_CALENDAR_STATE)})',
    1,
)

s = s.replace(
    'rows.append({"Ngày": info["date_obj"].strftime("%d/%m/%Y"), "Kết Quả Loto": " ".join(f"{x:02d}" for x in info["prizes_int"])})',
    'rows.append({"Ngày": info["date_obj"].strftime("%d/%m/%Y"), "Kết Quả Loto": " ".join(f"{x:02d}" for x in info["prizes_int"]), Config.CALENDAR_STATE_HEADER: info.get("calendar_state", Config.LEGACY_CALENDAR_STATE)})',
    1,
)

s = s.replace(
    'matrix = [["Ngày", "Kết Quả Loto"]] + [[r["Ngày"], r["Kết Quả Loto"]] for r in rows]',
    'matrix = [["Ngày", "Kết Quả Loto", Config.CALENDAR_STATE_HEADER]] + [[r["Ngày"], r["Kết Quả Loto"], r.get(Config.CALENDAR_STATE_HEADER, Config.LEGACY_CALENDAR_STATE)] for r in rows]',
)

s = s.replace(
    'db[std] = {"date_obj": dt_obj, "prizes_int": tails, "raw_str": " ".join(f"{x:02d}" for x in tails), "source_prizes": tuple(source_tokens)}',
    'existing_state = db.get(std, {}).get("calendar_state")\n        db[std] = {"date_obj": dt_obj, "prizes_int": tails, "raw_str": " ".join(f"{x:02d}" for x in tails), "source_prizes": tuple(source_tokens), "calendar_state": existing_state if existing_state == Config.DRAW_CONFIRMED else Config.LEGACY_CALENDAR_STATE, "source_set": db.get(std, {}).get("source_set", [])}',
)

s = s.replace(
    'if dt.date() == now.date() and now.hour < 19: continue',
    'if dt.date() == now.date() and not Utils.draw_cutoff_reached(): continue',
)
s = s.replace(
    'rec = {"date_obj": dt, "prizes_int": tails, "raw_str": " ".join(f"{x:02d}" for x in tails)}',
    'rec = {"date_obj": dt, "prizes_int": tails, "raw_str": " ".join(f"{x:02d}" for x in tails), "calendar_state": Config.DRAW_CONFIRMED, "source_set": ["ketqua16.net", "ketqua.net"]}',
)

s = s.replace(
    'def get_boundaries(db):\n        now = Utils.get_vn_time()\n        today = datetime(now.year, now.month, now.day)\n        valid = [x["date_obj"] for x in db.values() if x["date_obj"] <= today]\n        if not valid: return None, None, today\n        latest = max(valid)\n        if latest == today and now.hour < 19:\n            prior = [d for d in valid if d < today]\n            latest = max(prior) if prior else None\n        target = (latest + timedelta(days=1)) if latest else today\n        return min(valid), latest, target',
    'def get_boundaries(db):\n        now = Utils.get_vn_time()\n        today = datetime(now.year, now.month, now.day)\n        confirmed = [x["date_obj"] for x in db.values() if x["date_obj"] <= today and (x.get("calendar_state") == Config.DRAW_CONFIRMED or set(x.get("source_set", [])) == {"ketqua16.net", "ketqua.net"})]\n        if not confirmed: return None, None, today\n        latest = max(confirmed)\n        if latest == today and not Utils.draw_cutoff_reached():\n            prior = [d for d in confirmed if d < today]\n            latest = max(prior) if prior else None\n        target = (latest + timedelta(days=1)) if latest else today\n        print(f"[CALENDAR MERGED] confirmed_dates={len(confirmed)} latest={latest.strftime("%d/%m/%Y") if latest else "-"} next={target.strftime("%d/%m/%Y")}", flush=True)\n        return min(confirmed), latest, target',
)

p.write_text(s, encoding="utf-8")
print("[BUILD CALENDAR PATCH] applied")
