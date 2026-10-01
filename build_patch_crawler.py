from pathlib import Path
import re

p = Path("/app/app.py")
s = p.read_text(encoding="utf-8")

# Keep the forensic layer intact, but make the live crawler deliberately small:
# exactly two trusted sources, one archive endpoint per source, bounded timeout.
s = s.replace('CRAWL_MIN_QUORUM = 2', 'CRAWL_MIN_QUORUM = 2')
s = s.replace('CRAWL_FAST_TIMEOUT = 2', 'CRAWL_FAST_TIMEOUT = 4')
s = s.replace('CRAWL_HARD_DEADLINE = 12', 'CRAWL_HARD_DEADLINE = 8')
s = re.sub(
    r'CRAWL_FAST_DOMAINS = \[[^\n]+\]',
    'CRAWL_FAST_DOMAINS = ["ketqua16.net", "ketqua.net"]',
    s,
    count=1,
)

start = s.index('    @staticmethod\n    def _fetch_single_domain(domain):')
end = s.index('    @staticmethod\n    def fetch_ketqua_radar():', start)

single = r'''    @staticmethod
    def _fetch_single_domain(domain):
        """Fetch one trusted source and extract strict 27-tail rows."""
        if not HAS_REQUESTS:
            return False, {}, "requests_missing"

        url = f"https://{domain}/so-ket-qua-truyen-thong"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml",
        }
        started = time.perf_counter()
        try:
            r = requests.get(url, headers=headers, timeout=Config.CRAWL_FAST_TIMEOUT)
            if r.status_code != 200:
                print(
                    f"[CRAWL SOURCE] domain={domain} status={r.status_code} "
                    f"elapsed_ms={(time.perf_counter()-started)*1000:.0f} "
                    f"reason=HTTP_{r.status_code}",
                    flush=True,
                )
                return False, {}, domain

            soup = BeautifulSoup(r.text, "html.parser")
            parsed = Crawler._extract_27_from_visible_blocks(soup)

            # Some pages still expose the prize rows in a conventional table.
            if not parsed:
                date_pattern = re.compile(r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b')
                for table in soup.find_all("table"):
                    date_node = table.find_previous(string=date_pattern)
                    if not date_node:
                        continue
                    matches = date_pattern.findall(str(date_node))
                    if len(matches) != 1:
                        continue
                    res = Utils.chuan_hoa_ngay(matches[0])
                    if not res:
                        continue
                    _, std = res
                    tails = Crawler._extract_27_from_table(table)
                    if tails is not None:
                        parsed[std] = tails

            print(
                f"[CRAWL SOURCE] domain={domain} status=200 "
                f"elapsed_ms={(time.perf_counter()-started)*1000:.0f} "
                f"dates={len(parsed)} valid_27={len(parsed)} "
                f"reason={'OK' if parsed else 'NO_VALID_27_TAIL'}",
                flush=True,
            )
            if parsed:
                print(f"[CRAWL DOMAIN] domain={domain} result=VALID", flush=True)
                return True, parsed, domain
            return False, {}, domain
        except Exception as exc:
            print(
                f"[CRAWL SOURCE] domain={domain} status=NA "
                f"elapsed_ms={(time.perf_counter()-started)*1000:.0f} "
                f"reason={type(exc).__name__}:{exc}",
                flush=True,
            )
            return False, {}, domain

'''
s = s[:start] + single + s[end:]

start = s.index('    @staticmethod\n    def fetch_ketqua_radar():')
end = s.index('\n# ==============================================================================' + '\n# 📊 BLOCK 4: GOOGLE SHEETS & DATABASE MANAGER', start)

radar = r'''    @staticmethod
    def fetch_ketqua_radar():
        """Fast live sync: exactly two trusted sources, strict 27-tail consensus."""
        if not HAS_REQUESTS:
            return False, {}, "Thiếu requests"

        started = time.perf_counter()
        domains = ["ketqua16.net", "ketqua.net"]
        results = []

        print(
            f"[CRAWL RADAR START] deadline_s={Config.CRAWL_HARD_DEADLINE} "
            f"trusted_domains={','.join(domains)}",
            flush=True,
        )

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        futures = [executor.submit(Crawler._fetch_single_domain, d) for d in domains]
        try:
            try:
                for fut in concurrent.futures.as_completed(
                    futures, timeout=Config.CRAWL_HARD_DEADLINE
                ):
                    try:
                        ok, data, domain = fut.result()
                        if ok and data:
                            results.append((domain, data))
                    except Exception as exc:
                        print(
                            f"[CRAWL DOMAIN] worker_error={type(exc).__name__}:{exc}",
                            flush=True,
                        )
            except concurrent.futures.TimeoutError:
                print("[CRAWL RADAR] deadline reached", flush=True)
        finally:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)

        consensus = Crawler._build_consensus(results)
        elapsed = (time.perf_counter() - started) * 1000

        if consensus:
            msg = (
                f"STRICT 27-TAIL 2-SOURCE OK | crawl_ms={elapsed:.0f} "
                f"| sources={len(results)} | quorum=2 | dates={len(consensus)}"
            )
            print(f"[CRAWL FINAL] status=OK sources={len(results)} dates={len(consensus)} elapsed_ms={elapsed:.0f}", flush=True)
            return True, consensus, msg

        msg = (
            f"CRAWL FAIL-CLOSED | crawl_ms={elapsed:.0f} "
            f"| sources={len(results)} | quorum=2"
        )
        print(f"[CRAWL FINAL] status=FAIL_CLOSED sources={len(results)} elapsed_ms={elapsed:.0f}", flush=True)
        return False, {}, msg
'''
s = s[:start] + radar + s[end:]

# Install the visible-block parser directly into the runtime class.
marker = '    @staticmethod\n    def _build_consensus(results):'
if '_extract_27_from_visible_blocks' not in s:
    parser = r'''    @staticmethod
    def _extract_27_from_visible_blocks(soup):
        expected = [1, 1, 2, 6, 4, 6, 3, 4]
        labels = {
            "đặc biệt": 0, "giải đặc biệt": 0,
            "giải nhất": 1, "giải nhì": 2, "giải ba": 3,
            "giải tư": 4, "giải năm": 5, "giải sáu": 6, "giải bảy": 7,
        }
        date_re = re.compile(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b")
        number_re = re.compile(r"(?<!\d)\d{2,5}(?!\d)")
        lines = [re.sub(r"\s+", " ", str(x)).strip() for x in soup.stripped_strings]
        results, current_date, current, active_idx = {}, None, {}, None

        def flush():
            nonlocal current, active_idx
            if current_date is not None and all(len(current.get(i, [])) == expected[i] for i in range(8)):
                ordered = [v for i in range(8) for v in current[i]]
                try:
                    results[current_date] = Forensic.canonical_tails(ordered)
                except Exception:
                    pass
            current, active_idx = {}, None

        for line in lines:
            dm = date_re.search(line)
            if dm:
                if current_date is not None:
                    flush()
                res = Utils.chuan_hoa_ngay(dm.group(0))
                current_date = res[1] if res and res[0].date() <= Utils.get_vn_time().date() else None
                continue
            if current_date is None:
                continue
            normalized = line.lower()
            matched_idx, remainder = None, ""
            for label, idx in sorted(labels.items(), key=lambda x: len(x[0]), reverse=True):
                if normalized == label:
                    matched_idx = idx
                    break
                if normalized.startswith(label + " "):
                    matched_idx, remainder = idx, normalized[len(label):].strip()
                    break
            if matched_idx is not None:
                if matched_idx != len(current):
                    continue
                active_idx = matched_idx
                current[active_idx] = number_re.findall(remainder)
                if len(current[active_idx]) == expected[active_idx]:
                    active_idx = None
                continue
            if active_idx is not None:
                vals = number_re.findall(line)
                if vals:
                    current[active_idx].extend(vals)
                    if len(current[active_idx]) == expected[active_idx]:
                        active_idx = None
                    elif len(current[active_idx]) > expected[active_idx]:
                        current, active_idx = {}, None

        if current_date is not None:
            flush()
        return results

'''
    if marker not in s:
        raise SystemExit("missing consensus marker")
    s = s.replace(marker, parser + marker, 1)

p.write_text(s, encoding="utf-8")
print("[BUILD PATCH] live crawler reduced to ketqua16.net + ketqua.net, strict 27-tail consensus")
