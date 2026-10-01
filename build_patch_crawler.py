from pathlib import Path

p = Path("/app/app.py")
s = p.read_text(encoding="utf-8")

if "_extract_27_from_visible_blocks" in s:
    raise SystemExit("crawler archive parser patch already present")

needle = """    @staticmethod
    def _build_consensus(results):
"""
method = r'''    @staticmethod
    def _extract_27_from_visible_blocks(soup):
        """Strict fallback for archive pages with split/nonuniform table DOM."""
        expected = [1, 1, 2, 6, 4, 6, 3, 4]
        labels = {
            "đặc biệt": 0,
            "giải đặc biệt": 0,
            "giải nhất": 1,
            "giải nhì": 2,
            "giải ba": 3,
            "giải tư": 4,
            "giải năm": 5,
            "giải sáu": 6,
            "giải bảy": 7,
        }
        date_re = re.compile(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b")
        number_re = re.compile(r"(?<!\d)\d{2,5}(?!\d)")
        lines = [
            re.sub(r"\s+", " ", str(x)).strip()
            for x in soup.stripped_strings
        ]
        results = {}
        current_date = None
        current = {}
        active_idx = None

        def flush():
            nonlocal current, active_idx
            if current_date is None:
                return
            if all(len(current.get(i, [])) == expected[i] for i in range(8)):
                ordered = [v for i in range(8) for v in current[i]]
                try:
                    results[current_date] = Forensic.canonical_tails(ordered)
                except Exception:
                    pass
            current = {}
            active_idx = None

        for line in lines:
            dm = date_re.search(line)
            if dm:
                if current_date is not None:
                    flush()
                res = Utils.chuan_hoa_ngay(dm.group(0))
                current_date = (
                    res[1]
                    if res and res[0].date() <= Utils.get_vn_time().date()
                    else None
                )
                continue

            if current_date is None:
                continue

            normalized = re.sub(r"\s+", " ", line).strip().lower()
            matched_idx = None
            remainder = ""
            for label, idx in sorted(
                labels.items(), key=lambda item: len(item[0]), reverse=True
            ):
                if normalized == label:
                    matched_idx = idx
                    break
                if normalized.startswith(label + " "):
                    matched_idx = idx
                    remainder = normalized[len(label):].strip()
                    break

            if matched_idx is not None:
                next_idx = len(current)
                if matched_idx != next_idx:
                    continue
                active_idx = matched_idx
                vals = number_re.findall(remainder)
                current[active_idx] = vals
                if len(vals) == expected[active_idx]:
                    active_idx = None
                continue

            if active_idx is not None:
                vals = number_re.findall(line)
                if vals:
                    current[active_idx].extend(vals)
                    if len(current[active_idx]) == expected[active_idx]:
                        active_idx = None
                    elif len(current[active_idx]) > expected[active_idx]:
                        current = {}
                        active_idx = None

        if current_date is not None:
            flush()
        return results

'''
if needle not in s:
    raise SystemExit("missing crawler insertion point")
s = s.replace(needle, method + needle, 1)

needle2 = """                    if tails is not None:
                        parsed[std] = tails
                        diag["valid_27_tail_dates"] += 1
                if not parsed and diag["parsed_dates"] == 0:
"""
replacement2 = """                    if tails is not None:
                        parsed[std] = tails
                        diag["valid_27_tail_dates"] += 1

                fallback_parsed = Crawler._extract_27_from_visible_blocks(soup)
                for std, tails in fallback_parsed.items():
                    if std not in parsed:
                        parsed[std] = tails
                        diag["valid_27_tail_dates"] += 1
                if fallback_parsed:
                    diag["parsed_dates"] = max(
                        diag["parsed_dates"], len(fallback_parsed)
                    )

                if not parsed and diag["parsed_dates"] == 0:
"""
if needle2 not in s:
    raise SystemExit("missing crawler parse insertion point")
s = s.replace(needle2, replacement2, 1)
p.write_text(s, encoding="utf-8")
print("[BUILD PATCH] strict archive full-prize -> 27-tail parser installed")
