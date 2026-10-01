import os
import sys
import pandas as pd
import numpy as np
import math
import calendar
import re
import html
import shutil
import glob
from pathlib import Path
import json
import hmac
import hashlib
import uuid
import concurrent.futures
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bisect import bisect_left
import traceback
import gradio as gr
from bs4 import BeautifulSoup

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG
# ==============================================================================
class Config:
    VERSION = "V5.8 FIX FORENSIC CORE V4.2 — SINGLE FROZEN TRUTH / INTEGRITY + O(N) AUDIT" 
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    BACKUP_PREFIX = "Ket_Qua_Loto27_Backup_" 
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    BASE_PTS = 10.0
    LOOKBACK_DAYS = 21
    STORM_THRESHOLD = 0.35

    # FORENSIC QUANT CORE
    MIN_HISTORY_DAYS = 60
    OOS_TRAIN_RATIO = 0.60
    HMM_REFIT_INTERVAL = 14
    HMM_STATES = 3
    HMM_MAX_ITER = 25
    HMM_TOL = 1e-4
    HMM_MULTI_STARTS = 2
    MBB_BLOCK_SIZE = 5
    MBB_RUNS = 1000
    FDR_Q = 0.10
    MIN_OOS_TRADES = 30
    MIN_EXPECTANCY = 0.0
    MIN_BOOTSTRAP_P = 0.05
    RL_ALPHA = 0.10
    RL_GAMMA = 0.90
    RL_EPSILON = 0.05
    THOMPSON_MIN_PROB = 0.50
    MIN_RL_Q = 0.0
    KELLY_FRACTION = 0.25
    MAX_KELLY = 0.10
    
    STATE_FILE = 'v58_forensic_state.json'
    LEDGER_FILE = 'v58_forensic_ledger.jsonl'
    ANCHOR_FILE = '.v58_anchor.sys'
    REQUIRE_OOS_AUDIT = True
    MAX_AUDIT_DAYS = 5000
    CRAWL_MIN_QUORUM = 2
    CRAWL_FAST_TIMEOUT = 2
    CRAWL_HARD_DEADLINE = 12
    CRAWL_FAST_DOMAINS = ["ketqua16.net", "xsmb.com.vn"]
    ANCHOR_MAGIC = "V58_FORENSIC_ANCHOR_V1"
    CALENDAR_STATE_HEADER = "Calendar State"
    DRAW_CONFIRMED = "DRAW_CONFIRMED"
    LEGACY_CALENDAR_STATE = "LEGACY_PRESENT_TAIL_ONLY"
    
    ACTIVE_MODE = "🤖 [VERSION 5.8] V5.8 ROBUST TIERED QUANT ENGINE (RISK-PARITY ALLOCATION & TANH SLOPE)"
    
    MENU_OPTIONS = [
        "🔄 1. ĐỒNG BỘ & CẬP NHẬT DỮ LIỆU",
        "🎯 2. KHUYẾN NGHỊ LỆNH GIAO DỊCH",
        "🔍 3. KIỂM TOÁN CHUYÊN SÂU",
        "📈 4. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 5. BẢNG KẾT QUẢ LOTO TRUYỀN THỐNG",
        "🤖 6. BỘ NÃO AI (QUÉT LỊCH SỬ DB)"
    ]

# ==============================================================================
# 🛠️ BLOCK 2: UTILITIES
# ==============================================================================
class Utils:
    @staticmethod
    def get_vn_time():
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)

    @staticmethod
    def get_vn_time_aware():
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    @staticmethod
    def draw_cutoff_reached():
        now = Utils.get_vn_time_aware()
        return (now.hour, now.minute, now.second) >= (19, 0, 0)

    @staticmethod
    def chuan_hoa_ngay(ngay_raw):
        if pd.isna(ngay_raw) or not str(ngay_raw).strip() or str(ngay_raw).lower() == 'nan': return None
        ngay_str = str(ngay_raw).split(" ")[0] 
        match_ymd = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', ngay_str)
        if match_ymd:
            y, m, d = match_ymd.groups()
        else:
            match_dmy = re.search(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', ngay_str)
            if match_dmy: d, m, y = match_dmy.groups()
            else: return None
        if len(d) == 1: d = "0" + d
        if len(m) == 1: m = "0" + m
        str_chuan = f"{d}/{m}/{y}"
        try:
            dt_obj = datetime.strptime(str_chuan, "%d/%m/%Y")
            now_vn = Utils.get_vn_time()
            if dt_obj.year < 2000 or dt_obj > now_vn + timedelta(days=1): return None
            return dt_obj, str_chuan
        except Exception: return None

    @staticmethod
    def check_valid_number(val, name):
        if val is None or str(val).strip() == "": return False, f"🛑 LỖI: Nhập '{name}'."
        try:
            if float(val) <= 0: return False, f"🛑 LỖI: '{name}' > 0."
            return True, ""
        except (TypeError, ValueError): return False, f"🛑 LỖI: '{name}' sai định dạng."

# ==============================================================================
# 🛡️ V5.8 FIX CORE — FORENSIC DATA CONTRACT
# ==============================================================================
class Forensic:
    PARSER_VERSION = "V5.8-FIX-27TAIL-DOM-V4.2"
    NUMBER_RE = re.compile(r"(?<!\d)(\d{2,5})(?!\d)")

    @staticmethod
    def canonical_tails(values):
        if values is None:
            raise ValueError("STRICT_27_TAIL_FAIL: null values")
        tokens = list(values)
        if len(tokens) != 27:
            raise ValueError(f"STRICT_27_TAIL_FAIL: expected 27 prizes, got {len(tokens)}")
        tails = []
        for i, v in enumerate(tokens, 1):
            s = str(v).strip()
            if not re.fullmatch(r"\d{2,5}", s):
                raise ValueError(f"STRICT_PRIZE_TOKEN_FAIL: prize={i} value={v!r}")
            tails.append(int(s[-2:]))
        return tails

    @staticmethod
    def parse_raw_prizes(raw):
        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            raise ValueError("STRICT_27_TAIL_FAIL: empty raw result")
        text = str(raw).strip()
        tokens = re.findall(r"(?<!\d)\d{2,5}(?!\d)", text)
        if len(tokens) != 27 and re.fullmatch(r"\d{54}", re.sub(r"\s+", "", text)):
            compact = re.sub(r"\s+", "", text)
            tokens = [compact[i:i+2] for i in range(0, 54, 2)]
        if len(tokens) != 27:
            raise ValueError(f"STRICT_27_PRIZE_FAIL: expected exactly 27 prize values, got {len(tokens)}")
        return Forensic.canonical_tails(tokens), tokens

    @staticmethod
    def canonical_row(date_obj, tails):
        if len(tails) != 27:
            raise ValueError("CANONICAL_ROW_REQUIRES_27_TAILS")
        return {
            "Ngày": date_obj.strftime("%d/%m/%Y"),
            "Kết Quả Loto": " ".join(f"{x:02d}" for x in tails)
        }

    @staticmethod
    def dataset_hash(db):
        rows = []
        for d in sorted(db.values(), key=lambda x: x["date_obj"]):
            rows.append({
                "date": d["date_obj"].strftime("%Y-%m-%d"),
                "tails": [int(x) for x in d["prizes_int"]]
            })
        payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def prefix_hash(db, end_dt):
        subset = {k:v for k,v in db.items() if v["date_obj"] <= end_dt}
        return Forensic.dataset_hash(subset)

# ==============================================================================
# 🕸️ BLOCK 3: STRICT DOM-BOUND CRAWLER
# ==============================================================================
class Crawler:
    DOMAINS = [
        "ketqua16.net", "ketqua.net", "ketqua.vn", "ketquaxoso.net"
    ] + [f"ketqua{i}.net" for i in range(1, 51)]

    @staticmethod
    def _extract_27_from_table(table):
        """Strictly extracts 27 prizes from a single DOM <table> element."""
        expected = [1, 1, 2, 6, 4, 6, 3, 4]
        def cell_tokens(cell):
            vals = []
            for text in cell.stripped_strings:
                vals.extend(re.findall(r"(?<!\d)\d{2,5}(?!\d)", text))
            return vals

        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells: continue
            label = " ".join(cells[0].stripped_strings).strip()
            normalized = re.sub(r"\s+", " ", label).strip().lower()
            if normalized in {"đb", "g.đb", "g.db", "db", "đặc biệt", "g đặc biệt", "giải đặc biệt"}:
                idx = 0
            else:
                # Current source markup uses Vietnamese prize names
                # ("giải nhất" ... "giải bảy"), not G1/G2... labels.
                prize_names = {
                    "giải nhất": 1,
                    "giải nhì": 2,
                    "giải ba": 3,
                    "giải tư": 4,
                    "giải năm": 5,
                    "giải sáu": 6,
                    "giải bảy": 7,
                }
                if normalized in prize_names:
                    idx = prize_names[normalized]
                else:
                    m = re.search(r"(?:g|giải)\s*[.:]?\s*([1-7])\b", normalized)
                    if not m: continue
                    idx = int(m.group(1))
            vals = []
            for cell in cells[1:]:
                vals.extend(cell_tokens(cell))
            if not vals:
                all_tokens = cell_tokens(cells[0])
                vals = [x for x in all_tokens if x != label]
            if len(vals) == expected[idx]:
                rows.append((idx, vals))

        by_idx = {}
        for idx, vals in rows:
            if idx in by_idx and by_idx[idx] != vals: return None
            by_idx[idx] = vals
        if len(by_idx) == 8 and all(len(by_idx[i]) == expected[i] for i in range(8)):
            ordered = [v for i in range(8) for v in by_idx[i]]
            return Forensic.canonical_tails(ordered)
        return None

    @staticmethod
    def _build_consensus(results):
        """Build strict cross-source consensus without inventing or averaging data."""
        quorum = int(Config.CRAWL_MIN_QUORUM)
        if len(results) < quorum:
            return {}
        votes = {}
        for domain, data in results:
            if not isinstance(data, dict):
                continue
            for date_key, tails in data.items():
                try:
                    canonical = tuple(int(x) for x in Forensic.canonical_tails(tails))
                except Exception:
                    continue
                votes.setdefault(date_key, {}).setdefault(canonical, []).append(domain)

        consensus = {}
        for date_key, variants in votes.items():
            eligible = [
                (tails, domains)
                for tails, domains in variants.items()
                if len(set(domains)) >= quorum
            ]
            if len(eligible) == 1:
                tails, _domains = eligible[0]
                consensus[date_key] = list(tails)
            elif len(eligible) > 1:
                continue
        return consensus

    @staticmethod
    def _fetch_single_domain(domain):
        if not HAS_REQUESTS:
            print(f"[CRAWL] domain={domain} status=requests_missing", flush=True)
            return False, {}, "requests_missing"

        urls = [
            f"https://{domain}/xsmb-ngay-{Utils.get_vn_time().strftime('%d-%m-%Y')}.html",
            f"https://{domain}/so-ket-qua",
            f"https://{domain}/so-ket-qua-truyen-thong/300",
            f"https://{domain}/"
        ]
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/xhtml+xml"}
        date_pattern = re.compile(r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b')

        def fetch_and_parse(url):
            parsed = {}
            started_url = time.perf_counter()
            diag = {
                "domain": domain,
                "url": url,
                "http_status": None,
                "content_bytes": 0,
                "parsed_dates": 0,
                "valid_27_tail_dates": 0,
                "failure_reason": None,
            }
            try:
                r = requests.get(url, headers=headers, timeout=Config.CRAWL_FAST_TIMEOUT)
                diag["http_status"] = r.status_code
                diag["content_bytes"] = len(r.content or b"")
                if r.status_code != 200:
                    diag["failure_reason"] = f"HTTP_{r.status_code}"
                    return parsed
                soup = BeautifulSoup(r.text, "html.parser")
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
                    dt_obj, std = res
                    if dt_obj.date() > Utils.get_vn_time().date():
                        continue
                    diag["parsed_dates"] += 1
                    tails = Crawler._extract_27_from_table(table)
                    if tails is not None:
                        parsed[std] = tails
                        diag["valid_27_tail_dates"] += 1
                if not parsed and diag["parsed_dates"] == 0:
                    diag["failure_reason"] = "NO_PARSEABLE_DATE_TABLE"
                elif not parsed:
                    diag["failure_reason"] = "NO_VALID_27_TAIL"
                return parsed
            except requests.RequestException as exc:
                diag["failure_reason"] = f"{type(exc).__name__}:{exc}"
                return {}
            except Exception as exc:
                diag["failure_reason"] = f"{type(exc).__name__}:{exc}"
                return {}
            finally:
                diag["elapsed_ms"] = round((time.perf_counter() - started_url) * 1000)
                print(
                    "[CRAWL SOURCE] "
                    f"domain={diag['domain']} url={diag['url']} "
                    f"status={diag['http_status'] if diag['http_status'] is not None else 'NA'} "
                    f"elapsed_ms={diag['elapsed_ms']} bytes={diag['content_bytes']} "
                    f"dates={diag['parsed_dates']} valid_27={diag['valid_27_tail_dates']} "
                    f"reason={diag['failure_reason'] or 'OK'}",
                    flush=True,
                )

        # Race all candidate URLs for this source. Do not use a context manager:
        # ThreadPoolExecutor.__exit__ waits for every running request.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(urls))
        futures = [executor.submit(fetch_and_parse, url) for url in urls]
        try:
            for fut in concurrent.futures.as_completed(futures):
                try:
                    parsed = fut.result()
                    if parsed:
                        executor.shutdown(wait=False, cancel_futures=True)
                        print(f"[CRAWL DOMAIN] domain={domain} result=VALID", flush=True)
                        return True, parsed, domain
                except Exception as exc:
                    print(f"[CRAWL DOMAIN] domain={domain} worker_error={type(exc).__name__}:{exc}", flush=True)
            print(f"[CRAWL DOMAIN] domain={domain} result=NO_VALID_DATA", flush=True)
            return False, {}, domain
        finally:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)    @staticmethod
    def fetch_ketqua_radar():
        """Authoritative forensic crawl: ketqua16 + xsmb, exact FULL_27 quorum."""
        if not HAS_REQUESTS: return False, {}, "Thiếu requests"
        try:
            from data.ingestion.forensic_crawler_v2 import crawl, reconcile
            today = Utils.get_vn_time().date()
            days = [today - timedelta(days=i) for i in range(8)]
            records, errors = crawl(days, sources=("ketqua16", "xsmb"), workers=4, timeout=8)
            consensus, conflicts = reconcile(records, quorum=2)
            data = {}
            for row in consensus:
                tails = [int(v[-2:]) for v in row["full_27"]]
                key = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
                data[key] = {"tails": tails, "source_set": row["sources"]}
            msg = f"STRICT-27-TAIL 2-SOURCE OK | records={len(records)} | dates={len(data)} | conflicts={len(conflicts)} | errors={len(errors)}"
            print(f"[FORENSIC CRAWLER] {msg}", flush=True)
            return bool(data), data, msg
        except Exception as exc:
            print(f"[FORENSIC CRAWLER] FAIL {type(exc).__name__}:{exc}", flush=True)
            return False, {}, f"FORENSIC_CRAWLER_FAIL:{type(exc).__name__}:{exc}"


    @staticmethod
    def get_boundaries(db):
        now = Utils.get_vn_time()
        today = datetime(now.year, now.month, now.day)
        confirmed = [x["date_obj"] for x in db.values() if x["date_obj"] <= today and (x.get("calendar_state") == Config.DRAW_CONFIRMED or set(x.get("source_set", [])) == {"ketqua16", "xsmb"})]
        if not confirmed: return None, None, today
        latest = max(confirmed)
        if latest == today and not Utils.draw_cutoff_reached():
            prior = [d for d in confirmed if d < today]
            latest = max(prior) if prior else None
        target = (latest + timedelta(days=1)) if latest else today
        print("[CALENDAR MERGED] confirmed_dates={} latest={} next={}".format(len(confirmed), latest.strftime("%d/%m/%Y") if latest else "-", target.strftime("%d/%m/%Y")), flush=True)
        return min(confirmed), latest, target

# ==============================================================================
# 🧠 BLOCK 5: FORENSIC MULTI-SENSOR QUANT CORE
# ==============================================================================
class GaussianHMM:
    def __init__(self, n_states=3, max_iter=40, tol=1e-4, seed=42):
        self.n_states, self.max_iter, self.tol, self.seed = n_states, max_iter, tol, seed
        self.fitted = False

    @staticmethod
    def _lse(x, axis=None):
        m = np.max(x, axis=axis, keepdims=True)
        out = m + np.log(np.sum(np.exp(x-m), axis=axis, keepdims=True))
        return np.squeeze(out, axis=axis) if axis is not None else out

    def _emission(self, z):
        out = np.zeros((len(z), self.n_states))
        for k in range(self.n_states):
            v = np.maximum(self.vars_[k], 1e-5)
            d = z - self.means_[k]
            out[:, k] = -0.5*(np.sum(np.log(2*np.pi*v)) + np.sum(d*d/v, axis=1))
        return out

    def _fb(self, z):
        T,K=len(z),self.n_states
        if T <= 0:
            raise RuntimeError("HMM_EMPTY_SEQUENCE")
        e=self._emission(z)
        ls=np.log(np.maximum(self.startprob_,1e-300))
        lt=np.log(np.maximum(self.transmat_,1e-300))
        a=np.empty((T,K),dtype=float)
        a[0]=ls+e[0]
        for t in range(1,T):
            a[t]=e[t] + np.logaddexp.reduce(a[t-1][:,None] + lt, axis=0)
        b=np.zeros((T,K),dtype=float)
        for t in range(T-2,-1,-1):
            b[t]=np.logaddexp.reduce(lt + e[t+1][None,:] + b[t+1][None,:], axis=1)
        ll=float(np.logaddexp.reduce(a[-1]))
        g=np.exp(a+b-ll)
        g/=np.maximum(g.sum(1,keepdims=True),1e-300)
        if T == 1:
            return g,np.zeros((0,K,K)),ll
        log_xi=(a[:-1,:,None] + lt[None,:,:] + e[1:,None,:] + b[1:,None,:] - ll)
        xi=np.exp(log_xi)
        den=xi.sum(axis=(1,2),keepdims=True)
        xi=np.divide(xi, np.maximum(den,1e-300), out=np.zeros_like(xi), where=den>0)
        return g,xi,ll

    def fit(self,X):
        X=np.asarray(X,float)
        self.mean_scale_=X.mean(0); self.std_scale_=np.maximum(X.std(0),1e-6); z=(X-self.mean_scale_)/self.std_scale_
        best=(-np.inf,None)
        for s in range(Config.HMM_MULTI_STARTS):
            rng=np.random.default_rng(self.seed+s)
            idx=rng.choice(len(z),self.n_states,replace=False)
            means=z[idx].copy(); gv=np.maximum(np.var(z,0),0.1); vars_=np.tile(gv,(self.n_states,1))
            self.means_,self.vars_=means,vars_
            self.startprob_=np.ones(self.n_states)/self.n_states
            self.transmat_=np.eye(self.n_states)*0.8 + np.ones((self.n_states,self.n_states))*0.2/self.n_states
            self.transmat_/=self.transmat_.sum(1,keepdims=True)
            prev=-np.inf
            for _ in range(self.max_iter):
                g,xi,ll=self._fb(z)
                self.startprob_=(g[0]+1e-8)/(g[0]+1e-8).sum()
                tc=xi.sum(0)+1e-8; self.transmat_=tc/tc.sum(1,keepdims=True)
                w=g.sum(0)
                for k in range(self.n_states):
                    den=max(w[k],1e-8); self.means_[k]=(g[:,k,None]*z).sum(0)/den
                    d=z-self.means_[k]; self.vars_[k]=np.maximum((g[:,k,None]*d*d).sum(0)/den,1e-4)
                if abs(ll-prev)<self.tol: break
                prev=ll
            if ll>best[0]: best=(ll,(self.means_.copy(),self.vars_.copy(),self.startprob_.copy(),self.transmat_.copy()))
        self.means_,self.vars_,self.startprob_,self.transmat_=best[1]
        order=np.argsort(self.means_[:,0])
        self.means_=self.means_[order]; self.vars_=self.vars_[order]
        self.startprob_=self.startprob_[order]; self.transmat_=self.transmat_[order][:,order]
        self.loglik_=best[0]; self.fitted=True
        return self

    def _forward(self,X):
        if not self.fitted: raise RuntimeError("HMM_NOT_FITTED")
        z=(np.asarray(X,float)-self.mean_scale_)/self.std_scale_
        if len(z) == 0: raise RuntimeError("HMM_EMPTY_SEQUENCE")
        e=self._emission(z); T,K=len(z),self.n_states
        ls=np.log(np.maximum(self.startprob_,1e-300)); lt=np.log(np.maximum(self.transmat_,1e-300))
        a=np.empty((T,K),dtype=float); a[0]=ls+e[0]
        for t in range(1,T):
            a[t]=e[t]+np.logaddexp.reduce(a[t-1][:,None]+lt,axis=0)
        p=np.exp(a-np.logaddexp.reduce(a,axis=1)[:,None])
        return p

    def filtered_regime(self,X): return int(np.argmax(self._forward(X)[-1]))
    def filtered_probs(self,X): return self._forward(X)[-1]
    def to_dict(self):
        return {"n_states":self.n_states,"mean_scale_":self.mean_scale_.tolist(),"std_scale_":self.std_scale_.tolist(),
                "means_":self.means_.tolist(),"vars_":self.vars_.tolist(),"startprob_":self.startprob_.tolist(),
                "transmat_":self.transmat_.tolist(),"loglik_":float(self.loglik_),"fitted":True}
    @classmethod
    def from_dict(cls,d):
        m=cls(int(d["n_states"])); 
        for k in ["mean_scale_","std_scale_","means_","vars_","startprob_","transmat_"]:
            setattr(m,k,np.array(d[k],dtype=float))
        m.loglik_=float(d.get("loglik_",0)); m.fitted=True
        return m

def build_features(matrix):
    X=np.asarray(matrix,float); b=(X>0).astype(float)
    hit=b.mean(1); dispersion=b.std(1); counts=X.sum(1)
    entropy=[]
    for row in b:
        p=row/max(row.sum(),1.0); p=p[p>0]; entropy.append(float(-np.sum(p*np.log(p))) if len(p) else 0.0)
    s=pd.Series(hit); r7=s.rolling(7,min_periods=1).mean(); r30=s.rolling(30,min_periods=1).mean()
    return np.column_stack([hit,dispersion,counts,np.asarray(entropy),r7.values-r30.values])

class ThompsonSelector:
    def __init__(self,seed=42):
        self.strategies=["bayesian","momentum","mean_reversion"]; self.a={s:1.0 for s in self.strategies}; self.b={s:1.0 for s in self.strategies}; self.rng=np.random.default_rng(seed)
    def update(self,s,r): self.a[s]+=1 if r>0 else 0; self.b[s]+=1 if r<=0 else 0
    def best_prob(self,n=500):
        w={s:0 for s in self.strategies}
        for _ in range(n):
            z={s:self.rng.beta(self.a[s],self.b[s]) for s in self.strategies}; w[max(z,key=z.get)]+=1
        return {s:w[s]/n for s in w}
    def to_dict(self): return {"a":self.a,"b":self.b}
    def load(self,d): self.a={s:float(d.get("a",{}).get(s,1)) for s in self.strategies}; self.b={s:float(d.get("b",{}).get(s,1)) for s in self.strategies}

class QLearningSelector:
    MAP={"bayesian":{0,1,2},"momentum":{1,2},"mean_reversion":{0,2}}
    def __init__(self,seed=42):
        self.strategies=list(self.MAP); self.q=np.zeros((3,3)); self.rng=np.random.default_rng(seed)
    def valid(self,r): return [s for s in self.strategies if r in self.MAP[s]]
    def select(self,r,explore=False):
        v=self.valid(r) or self.strategies
        if explore and self.rng.random()<0.05: return str(self.rng.choice(v))
        return max(v,key=lambda s:self.q[r,self.strategies.index(s)])
    def update(self,r,s,reward,nr):
        i=self.strategies.index(s); nv=self.valid(nr)
        nxt=max((self.q[nr,self.strategies.index(x)] for x in nv),default=0)
        self.q[r,i]+=0.10*(reward+0.90*nxt-self.q[r,i])
    def to_dict(self): return {"q":self.q.tolist()}
    def load(self,d):
        q=d.get("q"); 
        if q is not None: self.q=np.array(q,float)

def mbb_pvalue(returns,block=5,runs=500,seed=42):
    r=np.asarray(returns,float); r=r[np.isfinite(r)]
    if len(r)<10 or r.mean()<=0: return 1.0
    centered=r-r.mean(); starts=max(1,len(r)-block+1); blocks=np.array([centered[i:i+block] for i in range(starts)])
    rng=np.random.default_rng(seed); means=[]
    for _ in range(runs):
        idx=rng.integers(0,len(blocks),size=math.ceil(len(r)/block)); means.append(blocks[idx].ravel()[:len(r)].mean())
    return float((1+np.sum(np.array(means)>=r.mean()))/(runs+1))

def bh_fdr(pvalues,q=0.10):
    items=sorted(pvalues.items(),key=lambda x:x[1]); m=len(items); cutoff=None
    for rank,(_,p) in enumerate(items,1):
        if p <= rank*q/m: cutoff=p
    rej={k:(cutoff is not None and p<=cutoff) for k,p in items}
    adj={}; prev=1.0
    for rank,(k,p) in reversed(list(enumerate(items,1))):
        prev=min(prev,p*m/rank); adj[k]=prev
    return rej,adj

class ManifestStore:
    _lock = threading.RLock()
    """Single forensic truth store.

    Invariants:
      1) Ledger is append-only and HMAC chained.
      2) State MUST equal the authenticated ledger tip.
      3) Anchor MUST equal the ledger tip sequence and is authenticated.
      4) Any mismatch is fail-closed.

    NOTE: a local anchor cannot defeat an attacker who can restore/replace
    *all* files including the anchor. It detects rollback when the anchor
    remains at a newer floor; a truly hostile filesystem needs an external
    monotonic counter/WORM storage.
    """
    @staticmethod
    def _secret():
        s = os.environ.get("VCORE_HMAC_SECRET", "").strip()
        if not s:
            raise RuntimeError("HARD FAIL: VCORE_HMAC_SECRET is required in production environment.")
        return s.encode("utf-8")

    @staticmethod
    def sign(payload):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hmac.new(ManifestStore._secret(), raw, hashlib.sha256).hexdigest()

    @staticmethod
    def _atomic_json_write(path, payload):
        path = str(path)
        tmp = path + f".tmp.{os.getpid()}.{uuid.uuid4().hex}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, sort_keys=True, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)

    @staticmethod
    def _ledger_records():
        if not os.path.exists(Config.LEDGER_FILE): return []
        out=[]
        with open(Config.LEDGER_FILE, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip(): continue
                try: out.append(json.loads(line))
                except Exception as e: raise RuntimeError(f"LEDGER_JSON_CORRUPT: line={lineno}") from e
        return out

    @staticmethod
    def _verify_chain(records):
        prev_sig = "GENESIS"
        expected_seq = 1
        for rec in records:
            supplied = rec.get("hmac_signature", "")
            body = dict(rec); body.pop("hmac_signature", None)
            if not hmac.compare_digest(supplied, ManifestStore.sign(body)):
                raise RuntimeError("LEDGER_HMAC_INVALID")
            if int(rec.get("sequence_id", -1)) != expected_seq:
                raise RuntimeError("LEDGER_SEQUENCE_GAP_OR_REPLAY")
            if rec.get("parent_manifest_hash", "GENESIS") != prev_sig:
                raise RuntimeError("LEDGER_PARENT_CHAIN_BROKEN")
            prev_sig = supplied
            expected_seq += 1
        return prev_sig, expected_seq-1

    @staticmethod
    def _read_anchor():
        if not os.path.exists(Config.ANCHOR_FILE):
            return 0, "GENESIS"
        try:
            with open(Config.ANCHOR_FILE, encoding="utf-8") as f: a=json.load(f)
            body={"magic":a.get("magic"),"sequence_id":int(a.get("sequence_id",-1)),"tip_hash":a.get("tip_hash")}
            supplied=a.get("hmac_signature","")
            if body["magic"] != Config.ANCHOR_MAGIC:
                raise RuntimeError("ANCHOR_MAGIC_INVALID")
            if body["sequence_id"] < 0 or not body["tip_hash"]:
                raise RuntimeError("ANCHOR_SCHEMA_INVALID")
            if not hmac.compare_digest(supplied, ManifestStore.sign(body)):
                raise RuntimeError("ANCHOR_HMAC_INVALID")
            return body["sequence_id"], body["tip_hash"]
        except RuntimeError: raise
        except Exception as e:
            raise RuntimeError("ANCHOR_CORRUPT") from e

    @staticmethod
    def _write_anchor(sequence_id, tip_hash):
        body={"magic":Config.ANCHOR_MAGIC,"sequence_id":int(sequence_id),"tip_hash":str(tip_hash)}
        payload=dict(body); payload["hmac_signature"]=ManifestStore.sign(body)
        ManifestStore._atomic_json_write(Config.ANCHOR_FILE, payload)

    @staticmethod
    def save(payload, path=None):
        with ManifestStore._lock:
            if path is None: path = Config.STATE_FILE
            payload = dict(payload)
            if payload.get("config_sha256") != config_sha256():
                raise RuntimeError("SAVE_CONFIG_HASH_MISMATCH")
            source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            if payload.get("source_sha256") != source_hash:
                raise RuntimeError("SAVE_SOURCE_HASH_MISMATCH")
            records = ManifestStore._ledger_records()
            tip, seq = ManifestStore._verify_chain(records) if records else ("GENESIS", 0)
            anchor_seq, anchor_tip = ManifestStore._read_anchor()
            if anchor_seq > seq:
                raise RuntimeError(f"PHYSICAL_ROLLBACK_DETECTED: anchor={anchor_seq}, ledger={seq}")
            if anchor_seq and anchor_seq != seq:
                raise RuntimeError(f"ANCHOR_LEDGER_DIVERGENCE: anchor={anchor_seq}, ledger={seq}")
            if anchor_seq and anchor_tip != tip:
                raise RuntimeError("ANCHOR_TIP_MISMATCH")

            payload["sequence_id"] = seq + 1
            payload["manifest_id"] = str(uuid.uuid4())
            payload["parent_manifest_hash"] = tip
            payload["hmac_signature"] = ManifestStore.sign(payload)

            line=json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
            with open(Config.LEDGER_FILE, "a", encoding="utf-8") as lf:
                lf.write(line); lf.flush(); os.fsync(lf.fileno())
            ManifestStore._atomic_json_write(path, payload)
            ManifestStore._write_anchor(payload["sequence_id"], payload["hmac_signature"])

    @staticmethod
    def load(path=None):
        with ManifestStore._lock:
            if path is None: path = Config.STATE_FILE
            if not os.path.exists(path): raise RuntimeError("STATE_NOT_FOUND")
            records = ManifestStore._ledger_records()
            if not records: raise RuntimeError("LEDGER_NOT_FOUND")
            tip, tip_seq = ManifestStore._verify_chain(records)
            anchor_seq, anchor_tip = ManifestStore._read_anchor()
            if anchor_seq != tip_seq or anchor_tip != tip:
                if anchor_seq > tip_seq:
                    raise RuntimeError(f"PHYSICAL_ROLLBACK_DETECTED: anchor={anchor_seq}, ledger={tip_seq}")
                raise RuntimeError("ANCHOR_LEDGER_TIP_MISMATCH")
            with open(path, encoding="utf-8") as f: payload=json.load(f)
            supplied=payload.get("hmac_signature", "")
            body=dict(payload); body.pop("hmac_signature", None)
            if not hmac.compare_digest(supplied, ManifestStore.sign(body)):
                raise RuntimeError("HMAC_AUTHENTICATION_FAILED")
            if supplied != tip or int(payload.get("sequence_id", -1)) != tip_seq:
                raise RuntimeError("MANIFEST_REPLAY_OR_LEDGER_TIP_MISMATCH")
            payload["hmac_signature"] = supplied
            return payload

    @staticmethod
    def verify_for_target(db, target_dt=None):
        state=ManifestStore.load()
        if state.get("config_sha256") != config_sha256():
            raise RuntimeError("CONFIG_HASH_MISMATCH")
        source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if state.get("source_sha256") != source_hash:
            raise RuntimeError("SOURCE_HASH_MISMATCH")
        train_end=datetime.strptime(state["train_end"], "%Y-%m-%d")
        if Forensic.prefix_hash(db, train_end) != state.get("train_prefix_sha256"):
            raise RuntimeError("TRAIN_PREFIX_MODIFIED_OR_DATA_REWRITTEN")
        # The manifest also freezes every historical OOS row that existed when
        # the manifest was created. New rows after oos_end are allowed; edits,
        # deletions, or substitutions inside the frozen snapshot are not.
        oos_end=datetime.strptime(state["oos_end"], "%Y-%m-%d")
        frozen_snapshot_hash=state.get("dataset_sha256")
        if not frozen_snapshot_hash:
            raise RuntimeError("MANIFEST_OOS_SNAPSHOT_HASH_MISSING")
        if Forensic.prefix_hash(db, oos_end) != frozen_snapshot_hash:
            raise RuntimeError("OOS_SNAPSHOT_MODIFIED_OR_ROLLED_BACK")
        contract=state.get("frozen_policy_contract", {})
        if contract.get("live_must_use_manifest") is not True:
            raise RuntimeError("FROZEN_POLICY_CONTRACT_INVALID")
        if contract.get("score_function") != "QuantEngine.strategy_scores":
            raise RuntimeError("FROZEN_SCORE_FUNCTION_MISMATCH")
        if contract.get("legacy_score_path_forbidden") is not True:
            raise RuntimeError("LEGACY_PATH_NOT_EXPLICITLY_FORBIDDEN")
        if contract.get("mm_formula") != "WR21 tier: >=0.50=>1.00x; >=0.35=>0.50x; else 0.20x; 4-loss circuit=>0.00x":
            raise RuntimeError("MM_POLICY_CONTRACT_MISMATCH")
        if contract.get("candidate_top_k") != 20 or contract.get("final_audit_top_k") != 5:
            raise RuntimeError("FROZEN_RANKING_CONTRACT_MISMATCH")
        if contract.get("allocation_tiers") != [1.30, 1.15, 0.85]:
            raise RuntimeError("ALLOCATION_TIER_CONTRACT_MISMATCH")
        if contract.get("audit_context_version") != "A1":
            raise RuntimeError("AUDIT_CONTEXT_CONTRACT_MISMATCH")
        if int(contract.get("crawler_quorum", 0)) != Config.CRAWL_MIN_QUORUM:
            raise RuntimeError("CRAWLER_QUORUM_CONTRACT_MISMATCH")
        if not state.get("edge_confirmed", False):
            raise RuntimeError("FROZEN_PURE_OOS_EDGE_NOT_CONFIRMED")
        if target_dt is not None:
            oos_start=datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if target_dt < oos_start:
                raise RuntimeError("FORENSIC_TARGET_IN_TRAINING_WINDOW")
        return state

def canonical_config_dict():
    out = {}
    for k in sorted(Config.__dict__):
        if k.startswith("_") or callable(getattr(Config, k)): continue
        v = getattr(Config, k)
        if k in {"HMAC_SECRET"}: continue
        if isinstance(v, dict): out[k] = {str(a): (sorted(b) if isinstance(b, set) else b) for a, b in sorted(v.items(), key=lambda z: str(z[0]))}
        elif isinstance(v, set): out[k] = sorted(v)
        elif isinstance(v, (str, int, float, bool, list, tuple)): out[k] = list(v) if isinstance(v, tuple) else v
    return out

def config_sha256():
    raw = json.dumps(canonical_config_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class AuditContext:
    """Request-scoped immutable forensic execution context.

    Performance contract:
      - DB/manifest are verified once per audit request.
      - The canonical 100-column prize matrix is materialized once.
      - HMM/RL objects are materialized once.
      - signal/prediction/MM results are memoized only inside this request.

    Security contract:
      - Context is NEVER persisted to disk.
      - It is bound to the exact db object + manifest sequence/id.
      - It cannot bypass ManifestStore.verify_for_target().
    """
    def __init__(self, db, state_manifest):
        if not isinstance(db, dict) or not db:
            raise RuntimeError("AUDIT_CONTEXT_DB_INVALID")
        if state_manifest is None:
            raise RuntimeError("AUDIT_CONTEXT_MANIFEST_REQUIRED")
        required = {"sequence_id", "manifest_id", "hmm", "rl", "oos_start", "oos_end", "train_end", "dataset_sha256"}
        if not required.issubset(state_manifest):
            raise RuntimeError("AUDIT_CONTEXT_MANIFEST_INCOMPLETE")
        self.db = db
        self.state = state_manifest
        self.db_identity = id(db)
        self.sequence_id = int(state_manifest["sequence_id"])
        self.manifest_id = str(state_manifest["manifest_id"])
        self.dates = sorted(x["date_obj"] for x in db.values())
        self.date_keys = [d.strftime("%d/%m/%Y") for d in self.dates]
        self.matrix = QuantEngine._matrix(db, self.dates)
        self.hmm = GaussianHMM.from_dict(state_manifest["hmm"])
        self.rl = QLearningSelector(); self.rl.load(state_manifest.get("rl", {}))
        # Prefix-safe feature/HMM precomputation: each row only depends on
        # current/past observations, so the full-prefix forward pass is exactly
        # equivalent to refitting the filter on every historical prefix.
        self.features_full = build_features(self.matrix)
        self.probs_full = self.hmm._forward(self.features_full)
        self.regime_full = np.argmax(self.probs_full, axis=1).astype(int)
        self.signal_cache = {}
        self.prediction_cache = {}
        self.mm_cache = {}

    def index_before(self, target_dt):
        return bisect_left(self.dates, target_dt)

    def matrix_before(self, target_dt):
        idx = self.index_before(target_dt)
        if idx < 21:
            return idx, None
        return idx, self.matrix[:idx]

    def regime_before(self, target_dt):
        idx = self.index_before(target_dt)
        if idx < 21:
            return idx, None, None
        row = idx - 1
        return idx, int(self.regime_full[row]), self.probs_full[row]

class QuantEngine:
    _sig_cache={}; _mm_cache={}; _research_cache={}

    @staticmethod
    def clear_cache():
        QuantEngine._sig_cache.clear(); QuantEngine._mm_cache.clear(); QuantEngine._research_cache.clear()

    @staticmethod
    def _matrix(db,dates):
        rows = []
        for d in dates:
            tails = db[d.strftime("%d/%m/%Y")]["prizes_int"]
            if len(tails) != 27: raise ValueError(f"MATRIX_27_TAIL_INVARIANT_FAIL: {d}")
            vec = np.zeros(100, dtype=float)
            for n in tails: vec[int(n)] += 1.0
            rows.append(vec)
        return np.asarray(rows, dtype=float)

    @staticmethod
    def strategy_scores(M, strategy):
        M = np.asarray(M, dtype=float)
        if len(M) < 21: return np.full(100, 0.5, dtype=float)
        b = (M > 0).astype(float)
        f21 = b[-21:].mean(axis=0)
        f7 = b[-7:].mean(axis=0)
        if strategy == "bayesian": return f21
        if strategy == "momentum": return f7 - f21
        if strategy == "mean_reversion": return f21 - f7
        raise ValueError(f"UNKNOWN_STRATEGY: {strategy}")

    @staticmethod
    def _rank_strategy(M, strategy, top_k=20):
        scores = QuantEngine.strategy_scores(M, strategy)
        idx = np.argsort(scores, kind="stable")[-top_k:][::-1]
        return [int(x) for x in idx], scores

    @staticmethod
    def get_signal(target_dt, db, state_manifest, context=None):
        """Canonical frozen-policy signal. No legacy fallback is permitted."""
        if state_manifest is None:
            raise RuntimeError("STRICT_FORENSIC: MUST_USE_MANIFEST")
        required = {"hmm", "rl", "train_end", "oos_start", "frozen_policy_contract"}
        if not required.issubset(state_manifest):
            raise RuntimeError("STRICT_FORENSIC: MANIFEST_SCHEMA_INCOMPLETE")
        contract = state_manifest.get("frozen_policy_contract", {})
        if contract.get("live_must_use_manifest") is not True or contract.get("score_function") != "QuantEngine.strategy_scores":
            raise RuntimeError("STRICT_FORENSIC: FROZEN_POLICY_CONTRACT_BREACH")
        if context is not None:
            if context.db is not db or context.sequence_id != int(state_manifest.get("sequence_id", -1)) or context.manifest_id != str(state_manifest.get("manifest_id")):
                raise RuntimeError("STRICT_FORENSIC: AUDIT_CONTEXT_BINDING_BREACH")
            cache_key = target_dt.strftime("%Y-%m-%d")
            if cache_key in context.signal_cache:
                return context.signal_cache[cache_key]
            past_count, M = context.matrix_before(target_dt)
            if M is None:
                return None, "[THIẾU LỊCH SỬ >=21 NGÀY]"
            _, regime, _ = context.regime_before(target_dt)
            strategy = context.rl.select(regime, explore=False)
            candidates, scores = QuantEngine._rank_strategy(M, strategy, top_k=20)
        else:
            key = (target_dt, Forensic.dataset_hash(db), state_manifest.get("manifest_id"), state_manifest.get("sequence_id"))
            if key in QuantEngine._sig_cache: return QuantEngine._sig_cache[key]
            past = sorted([x["date_obj"] for x in db.values() if x["date_obj"] < target_dt], reverse=True)
            if len(past) < 21: return None, "[THIẾU LỊCH SỬ >=21 NGÀY]"
            M = QuantEngine._matrix(db, list(reversed(past)))
            hmm = GaussianHMM.from_dict(state_manifest["hmm"])
            rl = QLearningSelector(); rl.load(state_manifest.get("rl", {}))
            features = build_features(M); regime = hmm.filtered_regime(features); strategy = rl.select(regime, explore=False)
            candidates, scores = QuantEngine._rank_strategy(M, strategy, top_k=20)
        trace = f"[FORENSIC FROZEN POLICY] regime={regime} | strategy={strategy} | score_source={strategy} | candidates={len(candidates)}"
        if context is not None:
            idx = context.index_before(target_dt)
            t1_key = context.date_keys[idx-1]; t2_key = context.date_keys[idx-2]; t3_key = context.date_keys[idx-3]
        else:
            t1_key = past[0].strftime("%d/%m/%Y"); t2_key = past[1].strftime("%d/%m/%Y"); t3_key = past[2].strftime("%d/%m/%Y")
        t1 = set(db[t1_key]["prizes_int"])
        recent = set(db[t2_key]["prizes_int"]) | set(db[t3_key]["prizes_int"])
        dan = [n for n in candidates if n in recent or n in t1 or ((n%10)*10+n//10) in t1]
        if len(dan) < 5: dan = candidates[:5]
        res = (sorted(dan), trace)
        if context is not None: context.signal_cache[cache_key] = res
        else: QuantEngine._sig_cache[key] = res
        return res

    @staticmethod
    def get_full_prediction(target_dt, db, state_manifest, context=None):
        """Fix 2: Propagating mandatory state_manifest."""
        dan, trace = QuantEngine.get_signal(target_dt, db, state_manifest, context=context)
        if dan is None: return None, trace
        
        if context is not None:
            idx, M = context.matrix_before(target_dt)
            if M is None: return None, "[THIẾU LỊCH SỬ >=21 NGÀY]"
            _, regime, _ = context.regime_before(target_dt)
            strategy = context.rl.select(regime, explore=False)
        else:
            past = sorted([x["date_obj"] for x in db.values() if x["date_obj"] < target_dt], reverse=True)
            M = QuantEngine._matrix(db, list(reversed(past)))
            hmm = GaussianHMM.from_dict(state_manifest["hmm"])
            rl = QLearningSelector(); rl.load(state_manifest.get("rl", {}))
            regime = hmm.filtered_regime(build_features(M))
            strategy = rl.select(regime, explore=False)
        raw_scores = QuantEngine.strategy_scores(M, strategy)
        
        score = {n: float(raw_scores[n]) for n in dan}
        final = sorted(dan, key=lambda n: (score[n], n), reverse=True)
        best = final[0] if final else 0
        mirror = (best%10)*10 + best//10
        stl = (final[1] if len(final)>1 else mirror, final[2] if len(final)>2 else ((best+11)%100))
        return {
            "btl": f"{best:02d}", "stl": f"{stl[0]:02d} - {stl[1]:02d}",
            "xien2": f"{best:02d} - {stl[0]:02d} | {best:02d} - {stl[1]:02d}",
            "cang3d": "[KHÔNG CÓ FULL 3-SỐ — FAIL CLOSED]",
            "kep": " - ".join(f"{x:02d}" for x in sorted([x for x in range(0,100,11)], key=lambda x:(x not in final,-score.get(x,0)))[:2]),
            "dan_de_10": ", ".join(f"{x:02d}" for x in sorted(final[:10])),
            "sorted_dan_scored": final,
            "strategy_scores": {str(k): score[k] for k in final},
            "selected_strategy": strategy,
            "regime": regime,
            "sig_trace": trace + " | LIVE/OOS CANONICAL SCORE PATH"
        }, "OK"

    @staticmethod
    def get_mm_multiplier(target_dt, db, state_manifest, context=None):
        """Frozen-policy risk sizing; request-scoped memoization only."""
        if state_manifest is None:
            raise RuntimeError("STRICT_FORENSIC: MM_REQUIRES_MANIFEST")
        if context is not None:
            if (context.db is not db or
                    context.sequence_id != int(state_manifest.get("sequence_id", -1)) or
                    context.manifest_id != str(state_manifest.get("manifest_id"))):
                raise RuntimeError("STRICT_FORENSIC: AUDIT_CONTEXT_BINDING_BREACH")
            key = target_dt.strftime("%Y-%m-%d")
            if key in context.mm_cache: return context.mm_cache[key]
        else:
            key = (target_dt, state_manifest.get("manifest_id"), state_manifest.get("sequence_id"))
            if key in QuantEngine._mm_cache: return QuantEngine._mm_cache[key]
        oos_start=datetime.strptime(state_manifest["oos_start"], "%Y-%m-%d")
        if context is not None:
            idx = context.index_before(target_dt)
            if idx < 21: result=(0.0,"[RISK GATE] <21 OOS-ELIGIBLE DAYS => 0.00x")
            else:
                if target_dt > datetime.strptime(state_manifest["train_end"], "%Y-%m-%d"):
                    lookback_dates = context.dates[max(0,idx-21):idx]
                    if any(d < oos_start for d in lookback_dates):
                        result=(0.0,"[RISK GATE] OOS LOOKBACK <21 DAYS => 0.00x")
                    else: result=None
                else: result=None
                if result is None:
                    daily=[]; streak=0
                    for dt in reversed(context.dates[max(0,idx-21):idx]):
                        dan,_=QuantEngine.get_signal(dt, db, state_manifest, context=context)
                        if not dan: continue
                        prizes=db[dt.strftime("%d/%m/%Y")]["prizes_int"]
                        pnl=sum(prizes.count(x)*Config.WIN_PER_NHAY for x in dan)-len(dan)*Config.BASE_PTS*Config.COST_PER_POINT
                        daily.append(pnl); streak = 0 if pnl>0 else streak+1
                    if not daily: result=(0.0,"[RISK GATE] NO_VALID_POLICY_OUTCOMES => 0.00x")
                    elif streak>=4: result=(0.0,"[CIRCUIT BREAKER] 4 consecutive losses => 0.00x")
                    else:
                        wr=sum(x>0 for x in daily)/len(daily); mult=1.0 if wr>=0.50 else (0.50 if wr>=0.35 else 0.20)
                        result=(mult,f"[FROZEN POLICY RISK] WR21={wr:.1%} | streak={streak} | multiplier={mult:.2f}x")
        else:
            past=sorted([x["date_obj"] for x in db.values() if x["date_obj"] < target_dt], reverse=True)
            if len(past)<21: result=(0.0,"[RISK GATE] <21 OOS-ELIGIBLE DAYS => 0.00x")
            elif target_dt > datetime.strptime(state_manifest["train_end"], "%Y-%m-%d") and any(d < oos_start for d in past[:21]):
                result=(0.0,"[RISK GATE] OOS LOOKBACK <21 DAYS => 0.00x")
            else:
                daily=[]; streak=0
                for dt in past[:21]:
                    dan,_=QuantEngine.get_signal(dt, db, state_manifest)
                    if not dan: continue
                    prizes=db[dt.strftime("%d/%m/%Y")]["prizes_int"]
                    pnl=sum(prizes.count(x)*Config.WIN_PER_NHAY for x in dan)-len(dan)*Config.BASE_PTS*Config.COST_PER_POINT
                    daily.append(pnl); streak = 0 if pnl>0 else streak+1
                if not daily: result=(0.0,"[RISK GATE] NO_VALID_POLICY_OUTCOMES => 0.00x")
                elif streak>=4: result=(0.0,"[CIRCUIT BREAKER] 4 consecutive losses => 0.00x")
                else:
                    wr=sum(x>0 for x in daily)/len(daily); mult=1.0 if wr>=0.50 else (0.50 if wr>=0.35 else 0.20)
                    result=(mult,f"[FROZEN POLICY RISK] WR21={wr:.1%} | streak={streak} | multiplier={mult:.2f}x")
        if context is not None: context.mm_cache[key]=result
        else: QuantEngine._mm_cache[key]=result
        return result

    @staticmethod
    def backtest_forensic(db):
        dates = sorted(x["date_obj"] for x in db.values())
        N = len(dates)
        if N < 80: return {"status":"BLOCKED","reason":"NEED_80_DAYS"}
        split = max(Config.MIN_HISTORY_DAYS, int(N*Config.OOS_TRAIN_RATIO))
        if split >= N-10: return {"status":"BLOCKED","reason":"OOS_TOO_SHORT"}

        strategies=["bayesian","momentum","mean_reversion"]
        returns={s:[] for s in strategies}; th=ThompsonSelector(seed=42); rl=QLearningSelector(seed=42)
        hmm_cache=None; prev_regime=None; prev_strategy=None

        full_M = QuantEngine._matrix(db, dates)
        full_features = build_features(full_M)
        for t in range(Config.MIN_HISTORY_DAYS, split):
            history=dates[:t]; M=full_M[:t]; features=full_features[:t]
            if hmm_cache is None or (t % Config.HMM_REFIT_INTERVAL == 0):
                hmm_cache=GaussianHMM(Config.HMM_STATES,Config.HMM_MAX_ITER,Config.HMM_TOL,42).fit(features)
            regime=hmm_cache.filtered_regime(features)
            if prev_strategy is not None:
                prev_history=dates[:t-1]; prev_M=full_M[:t-1]
                prev_scores=QuantEngine.strategy_scores(prev_M, prev_strategy)
                top=np.argsort(prev_scores,kind="stable")[-5:]
                actual=db[dates[t-1].strftime("%d/%m/%Y")]["prizes_int"]
                hits=sum(actual.count(int(n)) for n in top)
                cost=5*Config.BASE_PTS*Config.COST_PER_POINT; rev=hits*Config.BASE_PTS*Config.WIN_PER_NHAY
                reward=(rev-cost)/cost
                th.update(prev_strategy,reward); rl.update(prev_regime,prev_strategy,reward,regime)
            prev_regime=regime; prev_strategy=rl.select(regime,explore=True)

        if hmm_cache is None: return {"status":"BLOCKED","reason":"HMM_NOT_FIT"}
        frozen_hmm=hmm_cache
        oos_policy=[]
        frozen_probs=frozen_hmm._forward(full_features)
        for t in range(split,N):
            M=full_M[:t]; regime=int(np.argmax(frozen_probs[t-1]))
            strategy=rl.select(regime,explore=False)
            actual=db[dates[t].strftime("%d/%m/%Y")]["prizes_int"]
            for sname in strategies:
                scores=QuantEngine.strategy_scores(M,sname); top=np.argsort(scores,kind="stable")[-5:]
                hits=sum(actual.count(int(n)) for n in top); cost=5*Config.BASE_PTS*Config.COST_PER_POINT; rev=hits*Config.BASE_PTS*Config.WIN_PER_NHAY
                returns[sname].append((rev-cost)/cost)
            scores=QuantEngine.strategy_scores(M,strategy); top=np.argsort(scores,kind="stable")[-5:]
            hits=sum(actual.count(int(n)) for n in top); cost=5*Config.BASE_PTS*Config.COST_PER_POINT; rev=hits*Config.BASE_PTS*Config.WIN_PER_NHAY
            oos_policy.append((rev-cost)/cost)

        p={s:mbb_pvalue(v,Config.MBB_BLOCK_SIZE,Config.MBB_RUNS,42) for s,v in returns.items()}
        rej,qv=bh_fdr(p,Config.FDR_Q); policy=np.asarray(oos_policy,float); policy_p=mbb_pvalue(policy,Config.MBB_BLOCK_SIZE,Config.MBB_RUNS,42)
        eligible=[s for s in strategies if len(returns[s])>=Config.MIN_OOS_TRADES and np.mean(returns[s])>Config.MIN_EXPECTANCY and rej[s]]
        edge=bool(eligible and policy_p<Config.MIN_BOOTSTRAP_P and np.mean(policy)>0)
        train_end=dates[split-1]
        train_M=QuantEngine._matrix(db, dates[:split])
        frozen_hmm=GaussianHMM(Config.HMM_STATES, Config.HMM_MAX_ITER, Config.HMM_TOL, 42).fit(build_features(train_M))
        payload={
            "version":Config.VERSION,"config_sha256":config_sha256(),"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "parser_version":Forensic.PARSER_VERSION,"train_start":dates[0].strftime("%Y-%m-%d"),"train_end":train_end.strftime("%Y-%m-%d"),
            "oos_start":dates[split].strftime("%Y-%m-%d"),"oos_end":dates[-1].strftime("%Y-%m-%d"),"train_rows":split,"oos_rows":N-split,"split_idx":split,
            "train_prefix_sha256":Forensic.prefix_hash(db,train_end),"dataset_sha256":Forensic.dataset_hash(db),
            "strategy_pvalues":p,"strategy_fdr_q":qv,
            "strategy_stats":{s:{"trades":len(returns[s]),"expectancy":float(np.mean(returns[s])) if returns[s] else 0.0,"fdr_rejected":bool(rej[s])} for s in strategies},
            "policy_oos_pvalue":policy_p,"policy_oos_expectancy":float(np.mean(policy)) if len(policy) else 0.0,
            "eligible_strategies":eligible,"edge_confirmed":edge,
            "frozen_policy_contract":{
                "score_function":"QuantEngine.strategy_scores",
                "strategies":strategies,
                "candidate_top_k":20,
                "final_audit_top_k":5,
                "live_must_use_manifest":True,
                "legacy_score_path_forbidden":True,
                "mm_formula":"WR21 tier: >=0.50=>1.00x; >=0.35=>0.50x; else 0.20x; 4-loss circuit=>0.00x",
                "allocation_tiers":[1.30,1.15,0.85],
                "audit_context_version":"A1",
                "crawler_quorum":Config.CRAWL_MIN_QUORUM
            },
            "hmm":frozen_hmm.to_dict(),"thompson":th.to_dict(),"rl":rl.to_dict(),
        }
        ManifestStore.save(payload); return payload

# ==============================================================================
# 📊 BLOCK 6: AUDIT & REPORTING MANAGER
# ==============================================================================
class Auditor:
    @staticmethod
    def _verify_forensic_state(db, latest_dt, target_dt=None):
        return ManifestStore.verify_for_target(db, target_dt=target_dt)

    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = "ℹ️ Chế độ Offline. Bấm nút cập nhật để kích hoạt Radar."
        db = None
        if auto_crawl:
            crawl_msg, db = DatabaseManager.auto_heal_history()
        if db is None:
            db, msg = DatabaseManager.load_db()
        else:
            msg = "🟢 DB đã được nạp trong cùng phiên AUTO-HEAL; bỏ qua lần đọc lại Google Sheets."
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        latest_str = latest_dt.strftime('%d/%m/%Y') if latest_dt else "⚠️ CHƯA CÓ DỮ LIỆU!"
        lines = [
            "📑 BÁO CÁO ĐỒNG BỘ CƠ SỞ DỮ LIỆU TOÀN MẠNG",
            "=================================================================================",
            f"• Phiên bản hệ thống : {Config.VERSION}",
            f"• Trạng thái Dữ liệu : {msg}",
            f"• Báo cáo Crawler    : {crawl_msg}",
            "---------------------------------------------------------------------------------",
            f"• Dữ liệu cập nhật đến ngày : 📅 [{latest_str}]",
            f"• Sẵn sàng tính toán cho kỳ : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
        ]
        return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"

    @staticmethod
    def process_manual_input(date_str, num_str):
        save_msg = DatabaseManager.save_manual_data(date_str, num_str)
        report, title = Auditor.phan_he_1_sync(auto_crawl=False)
        return f"{save_msg}\n\n{report}", title

    @staticmethod
    def phan_he_2_predict(pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, next_dt = DatabaseManager.get_boundaries(db)
            if latest_dt is None: return "🛑 NO_TRADE: DATABASE_EMPTY"
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 NO_TRADE: {e}"
            
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn Cơ sở")
            if not valid: return err

            hmm = GaussianHMM.from_dict(state["hmm"])
            th = ThompsonSelector(); th.load(state.get("thompson", {}))
            rl = QLearningSelector(); rl.load(state.get("rl", {}))
            dates = sorted(x["date_obj"] for x in db.values() if x["date_obj"] <= latest_dt)
            M = QuantEngine._matrix(db, dates)
            features = build_features(M)
            regime = hmm.filtered_regime(features)
            probs = hmm.filtered_probs(features)
            strategy = rl.select(regime, explore=False)
            th_probs = th.best_prob(1000)
            q = rl.q[regime, rl.strategies.index(strategy)]
            allowed = strategy in rl.valid(regime)
            policy_pass = allowed and th_probs[strategy] >= Config.THOMPSON_MIN_PROB and q > Config.MIN_RL_Q

            pred_data, status = QuantEngine.get_full_prediction(next_dt, db, state)
            if pred_data is None: return f"🛑 CẢNH BÁO: {status}"
            sorted_dan = pred_data["sorted_dan_scored"]
            multiplier, mm_trace = QuantEngine.get_mm_multiplier(next_dt, db, state)
            base_pts = float(pts_per_code_base)
            if not policy_pass: multiplier = 0.0
            alloc=[]; total=0.0
            for i, code in enumerate(sorted_dan):
                tier = 1.30 if i == 0 else (1.15 if i in (1,2) else 0.85)
                pts = int(round(base_pts*multiplier*tier))
                cost = pts*Config.COST_PER_POINT
                total += cost
                alloc.append(f"   + [{code:02d}] {'BẠCH THỦ' if i==0 else ('SONG THỦ' if i in (1,2) else 'Lót dàn')} | {pts}đ | {cost:,.0f} VNĐ")
            return "\n".join([
                "📑 BÁO CÁO KHUYẾN NGHỊ GIAO DỊCH FORENSIC V5.8",
                "="*60, f"🎯 TARGET: {next_dt.strftime('%d/%m/%Y')}",
                f"🔗 MANIFEST: seq={state.get('sequence_id')} id={state.get('manifest_id', 'UNKNOWN')}",
                f"🧊 FROZEN HMM: regime={regime} | probs=" + ", ".join(f"{x:.3f}" for x in probs),
                f"🧠 POLICY: {strategy} | Thompson={th_probs[strategy]:.3f} | Q={q:.4f} | allowed={allowed}",
                f"🛡️ POLICY GATE: {'PASS' if policy_pass else 'NO_TRADE'}",
                f"📋 DÀN: {' '.join(f'{x:02d}' for x in sorted_dan)}",
                "💰 PHÂN BỔ:", *(alloc or ["   [ĐỨNG NGOÀI]"]),
                f"💰 TỔNG VỐN: {total:,.0f} VNĐ", mm_trace, pred_data["sig_trace"],
                "⚠️ CÀNG 3: [KHÔNG CÓ FULL 3-SỐ — FAIL CLOSED]"
            ])
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_router(audit_type, date_raw, month_raw, pts_per_code_base):
        if audit_type == "Kiểm toán 1 Ngày": return Auditor.phan_he_3_single(date_raw, pts_per_code_base)
        else: return Auditor.phan_he_3_monthly_detail(month_raw, pts_per_code_base)

    @staticmethod
    def phan_he_3_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, _ = DatabaseManager.get_boundaries(db)
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."
            
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            try: state = Auditor._verify_forensic_state(db, latest_dt, target_dt=d_obj)
            except RuntimeError as e: return f"🛑 LỖI FORENSIC WINDOW: {e}"
            context = AuditContext(db, state)
            if ngay_str not in db: return f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên {ngay_str} chưa cập nhật."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            
            lines = [
                "📑 BÁO CÁO KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN (SINGLE FROZEN TRUTH)",
                "========================================================================",
                f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str}",
                "========================================================================"
            ]
            pred_data, msg = QuantEngine.get_full_prediction(d_obj, db, state, context=context)
            mode_name = Config.ACTIVE_MODE.split(']')[1].strip()
            if pred_data is None: 
                lines.extend([f"🛑 [{mode_name}]: Thiếu dữ liệu", f"   > Lý do truy vết: {msg}"])
            else: 
                mult, mm_trace = QuantEngine.get_mm_multiplier(d_obj, db, state, context=context)
                sorted_dan = pred_data["sorted_dan_scored"]
                sl = len(sorted_dan)
                if sl == 0:
                    lines.append(f"🛑 [{mode_name}] 👉 KHÔNG CÓ MÃ ĐẠT CHUẨN (ĐỨNG NGOÀI)")
                else:
                    prizes_today = db[ngay_str]["prizes_int"]
                    day_cost, day_rev = 0.0, 0.0
                    hit_details = []
                    for idx_code, code_val in enumerate(sorted_dan):
                        k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                        pts_code = int(round(float(pts_per_code_base) * mult * k_tier))
                        if pts_code > 0:
                            c_code = pts_code * Config.COST_PER_POINT
                            nhay_code = prizes_today.count(code_val)
                            r_code = nhay_code * pts_code * Config.WIN_PER_NHAY
                            day_cost += c_code
                            day_rev += r_code
                            if nhay_code > 0: hit_details.append(f"[{code_val:02d}] nổ {nhay_code} nháy = +{r_code:,.0f} đ")
                    lai = day_rev - day_cost
                    st = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                    lines.extend([
                        f"📌 [{mode_name}]",
                        f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in sorted_dan]),
                        f" • Chi tiết trúng: " + (", ".join(hit_details) if hit_details else "🚫 Không trúng mã nào"),
                        f" • Tổng vốn dồn: {day_cost/1000:,.0f}k | Thu thưởng: {day_rev/1000:,.0f}k",
                        f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})\n"
                    ])
                lines.extend(["   --- LOG TRUY VẾT CẢM BIẾN & ĐI VỐN ---", "   " + pred_data['sig_trace'].replace("\n", "\n   "), "   " + mm_trace.replace("\n", "\n   ")])
            lines.append("------------------------------------------------------------------------")
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_monthly_detail(month_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, _ = DatabaseManager.get_boundaries(db)
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."
            
            m = re.match(r'^(\d{1,2})[-/.](\d{4})$', str(month_raw).strip())
            if not m: return "🛑 LỖI ĐỊNH DẠNG: Vui lòng nhập tháng dạng MM/YYYY."
            thang, nam = int(m.group(1)), int(m.group(2))
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = float(pts_per_code_base)
            start_dt = datetime(nam, thang, 1)
            max_day = calendar.monthrange(nam, thang)[1]
            end_dt = datetime(nam, thang, max_day)
            
            lines = [
                f"📑 BÁO CÁO CHI TIẾT TỪNG NGÀY: THÁNG {thang:02d}/{nam}",
                f"🎚️ LÕI ĐỘC TÔN: V5.8 FORENSIC VERIFIED CORE",
                "=============================================================================================================================",
                f"{'NGÀY':<6} | {'MÃ ĐÁNH':<26} | {'VỐN DỒN (k)':<12} | {'THU (k)':<8} | {'LÃI/LỖ (k)':<11} | {'ROI':<8}",
                "-----------------------------------------------------------------------------------------------------------------------------"
            ]
            oos_start=datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if Config.REQUIRE_OOS_AUDIT and end_dt < oos_start:
                return "🛑 FORENSIC AUDIT BLOCKED: tháng nằm hoàn toàn trong TRAINING WINDOW."
            context = AuditContext(db, state)
            curr = max(start_dt, oos_start) if Config.REQUIRE_OOS_AUDIT else start_dt
            tot_von, tot_thu, tot_lai = 0, 0, 0
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                short_date = curr.strftime("%d/%m")
                if ngay_str in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db, state, context=context)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db, state, context=context)
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        sl = len(sorted_dan)
                        dan_str = " ".join([f"{x:02d}" for x in sorted_dan])
                        if len(dan_str) > 20: dan_str = dan_str[:17] + "..."
                        d_list = f"{sl:>2} mã: {dan_str}"
                        prizes_today = db[ngay_str]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(base_pts * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c; day_rev += r_c
                        if day_cost <= 0:
                            lines.append(f"{short_date:<6} | {d_list:<26} | {'0':<12} | {'0':<8} | {'[ĐỨNG NGOÀI]':<11} | {'-':<8}")
                        else:
                            lai = day_rev - day_cost
                            roi = (lai / day_cost * 100) if day_cost > 0 else 0
                            tot_von += day_cost; tot_thu += day_rev; tot_lai += lai
                            lines.append(f"{short_date:<6} | {d_list:<26} | {day_cost/1000:>12,.0f} | {day_rev/1000:>8,.0f} | {lai/1000:>+11,.0f} | {roi:>+6.1f}%")
                    else: lines.append(f"{short_date:<6} | {'🚫 [ĐỨNG NGOÀI]':<26} | {'-':<12} | {'-':<8} | {'-':<11} | {'-':<8}")
                else: lines.append(f"{short_date:<6} | ⚪ Chưa có dữ liệu DB{'':<1} | {'-':<12} | {'-':<8} | {'-':<11} | {'-':<8}")
                curr += timedelta(days=1)
            tot_roi = (tot_lai / tot_von * 100) if tot_von > 0 else 0
            lines.extend(["=============================================================================================================================", f"📝 TỔNG KẾT THÁNG {thang:02d}/{nam}:", f"💰 TỔNG VỐN DỒN TIERED   : {tot_von:,.0f} VNĐ", f"💵 TỔNG DOANH THU THƯỞNG  : {tot_thu:,.0f} VNĐ", f"🚀 LỢI NHUẬN RÒNG          : {tot_lai:+,.0f} VNĐ", f"📈 TỶ SUẤT R.O.I           : {tot_roi:+.2f} %"])
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_4_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, _ = DatabaseManager.get_boundaries(db)
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."

            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI THÔNG SỐ."
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            if (end_dt - start_dt).days + 1 > Config.MAX_AUDIT_DAYS:
                return f"🛑 AUDIT_RANGE_TOO_LARGE: tối đa {Config.MAX_AUDIT_DAYS} ngày/lần."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = float(pts_per_code_base)
            oos_start=datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if Config.REQUIRE_OOS_AUDIT:
                if end_dt < oos_start:
                    return "🛑 FORENSIC AUDIT BLOCKED: range nằm hoàn toàn trong TRAINING WINDOW."
                start_dt=max(start_dt, oos_start)
            context = AuditContext(db, state)
            lines = [
                "📑 BÁO CÁO ĐẠI KẾ TOÁN QUÉT CHU KỲ TỔNG HỢP",
                "===================================================================================================================",
                f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (LÕI V5.8 FORENSIC VERIFIED)",
                "==================================================================================================================="
            ]
            curr = start_dt
            daily_records = []
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                if ngay_str in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db, state, context=context)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db, state, context=context)
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        prizes_today = db[ngay_str]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(base_pts * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c; day_rev += r_c
                        if day_cost > 0:
                            sl = len(sorted_dan)
                            lai = day_rev - day_cost
                            daily_records.append({
                                "dt": curr, "year": curr.year, "month_str": curr.strftime("%m/%Y"),
                                "codes": sl, "chi": day_cost, "lai": lai,
                                "win": 1 if lai > 0 else 0, "loss": 1 if lai <= 0 else 0,
                            })
                curr += timedelta(days=1)
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO XUẤT LỆNH THỰC TẾ."
            df_rec = pd.DataFrame(daily_records)
            lines.extend(["", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG", "-------------------------------------------------------------------------------------------------------------------", f"{'THÁNG/NĂM':<10} | {'PHIÊN':<7} | {'WIN/LOSS':<10} | {'VỐN ĐẦU TƯ':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}", "-------------------------------------------------------------------------------------------------------------------"])
            for m_str, g_m in df_rec.groupby("month_str", sort=False):
                m_chi, m_lai = g_m["chi"].sum(), g_m["lai"].sum()
                m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
                lines.append(f"Tháng {m_str:<5} | {len(g_m):<7} | {g_m['win'].sum()}W/{g_m['loss'].sum()}L | {m_chi:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%")
                
            tot_chi, tot_lai = df_rec["chi"].sum(), df_rec["lai"].sum()
            tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
            df_rec['cum_pnl'] = df_rec['lai'].cumsum()
            df_rec['peak'] = df_rec['cum_pnl'].cummax()
            max_dd = (df_rec['cum_pnl'] - df_rec['peak']).min()
            lines.extend(["===================================================================================================================", f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN):", f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ", f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ", f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %", f"• SỤT GIẢM VỐN LỚN NHẤT (Max Drawdown) : {abs(max_dd):,.0f} VNĐ", "==================================================================================================================="])
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_5_raw(ngay_raw):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            _, ngay_str = res
            if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại trên hệ thống."
            prizes = db[ngay_str]["prizes_int"]
            if len(prizes) < 27: return "🛑 LỖI DỮ LIỆU: Bảng kết quả không đủ 27 giải."
            lines = [
                "📑 BẢNG KẾT QUẢ XỔ SỐ MIỀN BẮC",
                "=======================================================",
                f"📅 KẾT QUẢ PHIÊN GIAO DỊCH: {ngay_str}",
                "-------------------------------------------------------",
                f"🔴 Đặc Biệt  :  {prizes[0]:02d}", f"🟢 Giải Nhất :  {prizes[1]:02d}", f"🔵 Giải Nhì  :  {prizes[2]:02d} - {prizes[3]:02d}",
                f"🟣 Giải Ba   :  {prizes[4]:02d} - {prizes[5]:02d} - {prizes[6]:02d} - {prizes[7]:02d} - {prizes[8]:02d} - {prizes[9]:02d}",
                f"🟤 Giải Tư   :  {prizes[10]:02d} - {prizes[11]:02d} - {prizes[12]:02d} - {prizes[13]:02d}",
                f"🟠 Giải Năm  :  {prizes[14]:02d} - {prizes[15]:02d} - {prizes[16]:02d} - {prizes[17]:02d} - {prizes[18]:02d} - {prizes[19]:02d}",
                f"🟡 Giải Sáu  :  {prizes[20]:02d} - {prizes[21]:02d} - {prizes[22]:02d}",
                f"⚪ Giải Bảy  :  {prizes[23]:02d} - {prizes[24]:02d} - {prizes[25]:02d} - {prizes[26]:02d}",
                "-------------------------------------------------------", "⚠️ Lưu ý: Bảng hiển thị Loto 2 số (Dữ liệu do Crawler phục vụ thuật toán Quant).", "======================================================="
            ]
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_6_master_diagnostic_prompt():
        try:
            db, msg = DatabaseManager.load_db()
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if not min_dt or not max_dt: return "🛑 HỆ THỐNG RỖNG: Chưa có dữ liệu."
            
            try: state = Auditor._verify_forensic_state(db, max_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."
            
            oos_start = datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if Config.REQUIRE_OOS_AUDIT and max_dt < oos_start:
                return "🛑 FORENSIC AUDIT BLOCKED: DB chưa có dữ liệu OOS sau train_end."
            context = AuditContext(db, state)
            scan_start = max(min_dt, oos_start) if Config.REQUIRE_OOS_AUDIT else min_dt
            total_days_scanned = (max_dt - scan_start).days + 1
            forensic_state = f"🛡️ FROZEN STATE: VERIFIED | train_end={state.get('train_end')} | oos_start={state.get('oos_start')} | edge={state.get('edge_confirmed')}"
            prompt_lines = [
                f"[HỒ SƠ SINH HỌC TOÀN HỆ THỐNG V5.8 ROBUST - DÀNH CHO BÁO CÁO ĐỊNH LƯỢNG CHUẨN TRUY VẾT]",
                forensic_state,
                f"1. PHIÊN BẢN HỆ THỐNG: {Config.VERSION}",
                f"2. QUÉT TRỌN VẸN LỊCH SỬ {total_days_scanned} NGÀY QUA ({min_dt.strftime('%d/%m/%Y')} ĐẾN {max_dt.strftime('%d/%m/%Y')})\n",
                "📊 [BÁO CÁO HIỆU SUẤT ĐỘC TÔN V5.8]"
            ]
            
            curr = scan_start
            wins, losses, total_chi, total_thu = 0, 0, 0, 0
            daily_pnls = []
            
            while curr <= max_dt:
                str_dt = curr.strftime("%d/%m/%Y")
                if str_dt in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db, state, context=context)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db, state, context=context)
                    
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        prizes_today = db[str_dt]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(Config.BASE_PTS * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c; day_rev += r_c
                                
                        if day_cost > 0:
                            lai = day_rev - day_cost
                            total_chi += day_cost; total_thu += day_rev; daily_pnls.append(lai)
                            if lai > 0: wins += 1
                            else: losses += 1
                curr += timedelta(days=1)

            roi = ((total_thu - total_chi) / total_chi * 100) if total_chi > 0 else 0
            cum_pnl = np.cumsum(daily_pnls) if daily_pnls else []
            peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else []
            drawdowns = cum_pnl - peak if len(cum_pnl) > 0 else []
            max_dd = abs(min(drawdowns)) if len(drawdowns) > 0 else 0

            prompt_lines.extend([
                f"➤ LÕI DUY NHẤT: {Config.ACTIVE_MODE}",
                f"   - Total PnL: {(total_thu - total_chi):+,.0f} VNĐ | ROI: {roi:.2f}% | Max Drawdown: {max_dd:,.0f} VNĐ",
                f"   - Win/Loss: {wins}W / {losses}L | Vốn đầu tư: {total_chi:,.0f} VNĐ | Doanh thu: {total_thu:,.0f} VNĐ",
                "-" * 65, "\n⚠️ XÁC NHẬN BÁO CÁO V5.8 FORENSIC VERIFIED CORE:",
                "1. Tích hợp cơ chế Dồn vốn Bậc thang Risk-Parity chuẩn hóa: Bạch Thủ Lô (1.30x), Song Thủ Lô (1.15x), Lô Dàn Lót (0.85x).",
                "2. HỆ THỐNG CHỈ SỬ DỤNG DUY NHẤT 1 SỰ THẬT: FROZEN POLICY TỪ MANIFEST CHO OOS VÀ LIVE; LEGACY PATH BỊ CẤM.",
                "3. Immutable Append-Only Ledger có Monotonic Anchor chống Rollback Vật Lý."
            ])
            return "\n".join(prompt_lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

# ==============================================================================
# 🖥️ BLOCK 7: GRADIO WEB UI (RENDER READY)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    min_dt_init, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title=Config.VERSION, theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 XSMB QUANT ENGINE {Config.VERSION}")
        with gr.Row(): nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (QUÉT RADAR CRAWLER ĐA LUỒNG)", variant="primary")
            gr.Markdown("---")
            gr.Markdown("✍️ **NHẬP KẾT QUẢ BẰNG TAY (DÀNH CHO NGÀY WEB CRAWLER BỊ KHÓA IP)**")
            with gr.Row():
                manual_date = gr.Textbox(label="Ngày (DD/MM/YYYY)", placeholder="Ví dụ: 01/08/2026")
                manual_numbers = gr.Textbox(label="27 GIẢI", placeholder="Ví dụ: 5 số / 4 số / 3 số / 2 số — đúng 27 giải")
            btn_manual_save = gr.Button("📥 LƯU DỮ LIỆU VÀO DATABASE", variant="primary")
            gr.Markdown("---")
            out_1 = gr.Textbox(label="Biên bản Báo cáo Hệ thống", lines=8)
            title_2 = gr.Markdown(f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt_init.strftime('%d/%m/%Y')}")
            
        with gr.Column(visible=False) as col_2:
            with gr.Row(): pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
            btn_2 = gr.Button("🔍 XUẤT LỆNH GIAO DỊCH CAO CẤP", variant="primary")
            out_2 = gr.Textbox(label="Hồ sơ Lệnh Tác Chiến", lines=25)
            btn_2.click(lambda pts: Auditor.phan_he_2_predict(pts), inputs=[pts_2], outputs=out_2)
            
        with gr.Column(visible=False) as col_3:
            gr.Markdown("### 🔍 MODULE KIỂM TOÁN CHUYÊN SÂU & TRUY VẾT")
            audit_type = gr.Radio(choices=["Kiểm toán 1 Ngày", "Kiểm toán Cả Tháng"], value="Kiểm toán 1 Ngày", label="Loại Kiểm toán")
            with gr.Column(visible=True) as row_audit_day: date_3 = gr.Textbox(label="Ngày Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            with gr.Column(visible=False) as row_audit_month: month_3 = gr.Textbox(label="Tháng Truy xuất (MM/YYYY)", value=latest_dt_init.strftime('%m/%Y') if latest_dt_init else "")
            pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_3 = gr.Button("📡 THỰC THI KIỂM TOÁN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Kiểm toán", lines=24)
            def toggle_audit(choice): return gr.Column(visible=(choice == "Kiểm toán 1 Ngày")), gr.Column(visible=(choice != "Kiểm toán 1 Ngày"))
            audit_type.change(fn=toggle_audit, inputs=audit_type, outputs=[row_audit_day, row_audit_month])
            btn_3.click(Auditor.phan_he_3_router, inputs=[audit_type, date_3, month_3, pts_3], outputs=out_3)

        with gr.Column(visible=False) as col_4:
            with gr.Row():
                t1_4 = gr.Textbox(label="Từ ngày", value=min_dt_init.strftime('%d/%m/%Y') if min_dt_init else "")
                t2_4 = gr.Textbox(label="Đến ngày", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Dòng Tiền", lines=22)
            btn_4.click(lambda t1, t2, pts: Auditor.phan_he_4_range(t1, t2, pts), inputs=[t1_4, t2_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            date_5 = gr.Textbox(label="Phiên Giao dịch", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_5 = gr.Button("💾 TRUY XUẤT KẾT QUẢ", variant="primary")
            out_5 = gr.Textbox(label="Bảng Kết Quả Loto", lines=15)
            btn_5.click(Auditor.phan_he_5_raw, inputs=date_5, outputs=out_5)

        with gr.Column(visible=False) as col_6:
            gr.Markdown("### 🤖 BỘ NÃO AI - QUÉT TOÀN BỘ LỊCH SỬ DB")
            btn_6 = gr.Button("🧬 BẮT ĐẦU QUÉT TOÀN DB", variant="primary")
            out_6 = gr.Textbox(label="Báo cáo Tổng hợp V5.8", lines=25)
            btn_6.click(Auditor.phan_he_6_master_diagnostic_prompt, inputs=[], outputs=out_6)

        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])
        btn_manual_save.click(Auditor.process_manual_input, inputs=[manual_date, manual_numbers], outputs=[out_1, title_2])

        def update_visibility(choice):
            return [gr.Column(visible=(choice == Config.MENU_OPTIONS[i])) for i in range(6)]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6])
    return demo

def _render_forensic_bootstrap():
    """
    Render-safe startup:
    - NEVER block the web server waiting for the first Frozen Manifest.
    - Build the manifest exactly once in a background thread when absent.
    - Ordinary restarts never rebuild an existing manifest.
    """
    if os.path.exists(Config.STATE_FILE):
        print("[FORENSIC BOOTSTRAP] Frozen Manifest already exists; startup rebuild skipped.")
        return

    print("[FORENSIC BOOTSTRAP] STATE_NOT_FOUND -> starting one-time background bootstrap...")
    try:
        db, msg = DatabaseManager.load_db()
        print(f"[FORENSIC BOOTSTRAP] {msg}")
        if not db:
            print("[FORENSIC BOOTSTRAP] BLOCKED: DATABASE_EMPTY")
            return

        result = QuantEngine.backtest_forensic(db)
        if isinstance(result, dict) and result.get("status") == "BLOCKED":
            print(f"[FORENSIC BOOTSTRAP] BLOCKED: {result.get('reason', 'UNKNOWN')}")
            return

        # backtest_forensic() is responsible for the authenticated,
        # append-only Frozen Manifest write.
        if os.path.exists(Config.STATE_FILE):
            print("[FORENSIC BOOTSTRAP] Frozen Manifest created successfully.")
        else:
            print("[FORENSIC BOOTSTRAP] HARD FAIL: backtest returned but STATE_FILE was not created.")
    except Exception as e:
        print(f"[FORENSIC BOOTSTRAP] HARD FAIL: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    # Explicit forensic rebuild remains a manual/destructive operation.
    # It is intentionally NOT part of normal Render startup.
    if '--rebuild-manifest' in sys.argv:
        db, msg = DatabaseManager.load_db()
        print(msg)
        if not db:
            raise SystemExit('REBUILD_BLOCKED: DATABASE_EMPTY')
        result = QuantEngine.backtest_forensic(db)
        print(json.dumps(result if isinstance(result, dict) else {'status':'OK'},
                         ensure_ascii=False, indent=2, default=str))
        raise SystemExit(0)

    # IMPORTANT:
    # The web server must bind its Render PORT before the potentially expensive
    # forensic bootstrap runs. Otherwise Render kills the service because no
    # listening socket is visible during the port-scan window.
    #
    # The daemon thread performs the one-time manifest creation in the
    # background. The UI/audit remains available while it is being built.
    bootstrap_thread = threading.Thread(
        target=_render_forensic_bootstrap,
        name="forensic-bootstrap",
        daemon=True,
    )
    bootstrap_thread.start()

    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    print(f"[RENDER] Starting Gradio on 0.0.0.0:{port}")
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
    @staticmethod
    def get_boundaries(db):
        now = Utils.get_vn_time()
        today = datetime(now.year, now.month, now.day)
        valid = [x["date_obj"] for x in db.values() if x["date_obj"] <= today]
        if not valid: return None, None, today
        latest = max(valid)
        if latest == today and now.hour < 19:
            prior = [d for d in valid if d < today]
            latest = max(prior) if prior else None
        target = (latest + timedelta(days=1)) if latest else today
        return min(valid), latest, target

# ==============================================================================
# 🧠 BLOCK 5: FORENSIC MULTI-SENSOR QUANT CORE
# ==============================================================================
class GaussianHMM:
    def __init__(self, n_states=3, max_iter=40, tol=1e-4, seed=42):
        self.n_states, self.max_iter, self.tol, self.seed = n_states, max_iter, tol, seed
        self.fitted = False

    @staticmethod
    def _lse(x, axis=None):
        m = np.max(x, axis=axis, keepdims=True)
        out = m + np.log(np.sum(np.exp(x-m), axis=axis, keepdims=True))
        return np.squeeze(out, axis=axis) if axis is not None else out

    def _emission(self, z):
        out = np.zeros((len(z), self.n_states))
        for k in range(self.n_states):
            v = np.maximum(self.vars_[k], 1e-5)
            d = z - self.means_[k]
            out[:, k] = -0.5*(np.sum(np.log(2*np.pi*v)) + np.sum(d*d/v, axis=1))
        return out

    def _fb(self, z):
        T,K=len(z),self.n_states
        if T <= 0:
            raise RuntimeError("HMM_EMPTY_SEQUENCE")
        e=self._emission(z)
        ls=np.log(np.maximum(self.startprob_,1e-300))
        lt=np.log(np.maximum(self.transmat_,1e-300))
        a=np.empty((T,K),dtype=float)
        a[0]=ls+e[0]
        for t in range(1,T):
            a[t]=e[t] + np.logaddexp.reduce(a[t-1][:,None] + lt, axis=0)
        b=np.zeros((T,K),dtype=float)
        for t in range(T-2,-1,-1):
            b[t]=np.logaddexp.reduce(lt + e[t+1][None,:] + b[t+1][None,:], axis=1)
        ll=float(np.logaddexp.reduce(a[-1]))
        g=np.exp(a+b-ll)
        g/=np.maximum(g.sum(1,keepdims=True),1e-300)
        if T == 1:
            return g,np.zeros((0,K,K)),ll
        log_xi=(a[:-1,:,None] + lt[None,:,:] + e[1:,None,:] + b[1:,None,:] - ll)
        xi=np.exp(log_xi)
        den=xi.sum(axis=(1,2),keepdims=True)
        xi=np.divide(xi, np.maximum(den,1e-300), out=np.zeros_like(xi), where=den>0)
        return g,xi,ll

    def fit(self,X):
        X=np.asarray(X,float)
        self.mean_scale_=X.mean(0); self.std_scale_=np.maximum(X.std(0),1e-6); z=(X-self.mean_scale_)/self.std_scale_
        best=(-np.inf,None)
        for s in range(Config.HMM_MULTI_STARTS):
            rng=np.random.default_rng(self.seed+s)
            idx=rng.choice(len(z),self.n_states,replace=False)
            means=z[idx].copy(); gv=np.maximum(np.var(z,0),0.1); vars_=np.tile(gv,(self.n_states,1))
            self.means_,self.vars_=means,vars_
            self.startprob_=np.ones(self.n_states)/self.n_states
            self.transmat_=np.eye(self.n_states)*0.8 + np.ones((self.n_states,self.n_states))*0.2/self.n_states
            self.transmat_/=self.transmat_.sum(1,keepdims=True)
            prev=-np.inf
            for _ in range(self.max_iter):
                g,xi,ll=self._fb(z)
                self.startprob_=(g[0]+1e-8)/(g[0]+1e-8).sum()
                tc=xi.sum(0)+1e-8; self.transmat_=tc/tc.sum(1,keepdims=True)
                w=g.sum(0)
                for k in range(self.n_states):
                    den=max(w[k],1e-8); self.means_[k]=(g[:,k,None]*z).sum(0)/den
                    d=z-self.means_[k]; self.vars_[k]=np.maximum((g[:,k,None]*d*d).sum(0)/den,1e-4)
                if abs(ll-prev)<self.tol: break
                prev=ll
            if ll>best[0]: best=(ll,(self.means_.copy(),self.vars_.copy(),self.startprob_.copy(),self.transmat_.copy()))
        self.means_,self.vars_,self.startprob_,self.transmat_=best[1]
        order=np.argsort(self.means_[:,0])
        self.means_=self.means_[order]; self.vars_=self.vars_[order]
        self.startprob_=self.startprob_[order]; self.transmat_=self.transmat_[order][:,order]
        self.loglik_=best[0]; self.fitted=True
        return self

    def _forward(self,X):
        if not self.fitted: raise RuntimeError("HMM_NOT_FITTED")
        z=(np.asarray(X,float)-self.mean_scale_)/self.std_scale_
        if len(z) == 0: raise RuntimeError("HMM_EMPTY_SEQUENCE")
        e=self._emission(z); T,K=len(z),self.n_states
        ls=np.log(np.maximum(self.startprob_,1e-300)); lt=np.log(np.maximum(self.transmat_,1e-300))
        a=np.empty((T,K),dtype=float); a[0]=ls+e[0]
        for t in range(1,T):
            a[t]=e[t]+np.logaddexp.reduce(a[t-1][:,None]+lt,axis=0)
        p=np.exp(a-np.logaddexp.reduce(a,axis=1)[:,None])
        return p

    def filtered_regime(self,X): return int(np.argmax(self._forward(X)[-1]))
    def filtered_probs(self,X): return self._forward(X)[-1]
    def to_dict(self):
        return {"n_states":self.n_states,"mean_scale_":self.mean_scale_.tolist(),"std_scale_":self.std_scale_.tolist(),
                "means_":self.means_.tolist(),"vars_":self.vars_.tolist(),"startprob_":self.startprob_.tolist(),
                "transmat_":self.transmat_.tolist(),"loglik_":float(self.loglik_),"fitted":True}
    @classmethod
    def from_dict(cls,d):
        m=cls(int(d["n_states"])); 
        for k in ["mean_scale_","std_scale_","means_","vars_","startprob_","transmat_"]:
            setattr(m,k,np.array(d[k],dtype=float))
        m.loglik_=float(d.get("loglik_",0)); m.fitted=True
        return m

def build_features(matrix):
    X=np.asarray(matrix,float); b=(X>0).astype(float)
    hit=b.mean(1); dispersion=b.std(1); counts=X.sum(1)
    entropy=[]
    for row in b:
        p=row/max(row.sum(),1.0); p=p[p>0]; entropy.append(float(-np.sum(p*np.log(p))) if len(p) else 0.0)
    s=pd.Series(hit); r7=s.rolling(7,min_periods=1).mean(); r30=s.rolling(30,min_periods=1).mean()
    return np.column_stack([hit,dispersion,counts,np.asarray(entropy),r7.values-r30.values])

class ThompsonSelector:
    def __init__(self,seed=42):
        self.strategies=["bayesian","momentum","mean_reversion"]; self.a={s:1.0 for s in self.strategies}; self.b={s:1.0 for s in self.strategies}; self.rng=np.random.default_rng(seed)
    def update(self,s,r): self.a[s]+=1 if r>0 else 0; self.b[s]+=1 if r<=0 else 0
    def best_prob(self,n=500):
        w={s:0 for s in self.strategies}
        for _ in range(n):
            z={s:self.rng.beta(self.a[s],self.b[s]) for s in self.strategies}; w[max(z,key=z.get)]+=1
        return {s:w[s]/n for s in w}
    def to_dict(self): return {"a":self.a,"b":self.b}
    def load(self,d): self.a={s:float(d.get("a",{}).get(s,1)) for s in self.strategies}; self.b={s:float(d.get("b",{}).get(s,1)) for s in self.strategies}

class QLearningSelector:
    MAP={"bayesian":{0,1,2},"momentum":{1,2},"mean_reversion":{0,2}}
    def __init__(self,seed=42):
        self.strategies=list(self.MAP); self.q=np.zeros((3,3)); self.rng=np.random.default_rng(seed)
    def valid(self,r): return [s for s in self.strategies if r in self.MAP[s]]
    def select(self,r,explore=False):
        v=self.valid(r) or self.strategies
        if explore and self.rng.random()<0.05: return str(self.rng.choice(v))
        return max(v,key=lambda s:self.q[r,self.strategies.index(s)])
    def update(self,r,s,reward,nr):
        i=self.strategies.index(s); nv=self.valid(nr)
        nxt=max((self.q[nr,self.strategies.index(x)] for x in nv),default=0)
        self.q[r,i]+=0.10*(reward+0.90*nxt-self.q[r,i])
    def to_dict(self): return {"q":self.q.tolist()}
    def load(self,d):
        q=d.get("q"); 
        if q is not None: self.q=np.array(q,float)

def mbb_pvalue(returns,block=5,runs=500,seed=42):
    r=np.asarray(returns,float); r=r[np.isfinite(r)]
    if len(r)<10 or r.mean()<=0: return 1.0
    centered=r-r.mean(); starts=max(1,len(r)-block+1); blocks=np.array([centered[i:i+block] for i in range(starts)])
    rng=np.random.default_rng(seed); means=[]
    for _ in range(runs):
        idx=rng.integers(0,len(blocks),size=math.ceil(len(r)/block)); means.append(blocks[idx].ravel()[:len(r)].mean())
    return float((1+np.sum(np.array(means)>=r.mean()))/(runs+1))

def bh_fdr(pvalues,q=0.10):
    items=sorted(pvalues.items(),key=lambda x:x[1]); m=len(items); cutoff=None
    for rank,(_,p) in enumerate(items,1):
        if p <= rank*q/m: cutoff=p
    rej={k:(cutoff is not None and p<=cutoff) for k,p in items}
    adj={}; prev=1.0
    for rank,(k,p) in reversed(list(enumerate(items,1))):
        prev=min(prev,p*m/rank); adj[k]=prev
    return rej,adj

class ManifestStore:
    _lock = threading.RLock()
    """Single forensic truth store.

    Invariants:
      1) Ledger is append-only and HMAC chained.
      2) State MUST equal the authenticated ledger tip.
      3) Anchor MUST equal the ledger tip sequence and is authenticated.
      4) Any mismatch is fail-closed.

    NOTE: a local anchor cannot defeat an attacker who can restore/replace
    *all* files including the anchor. It detects rollback when the anchor
    remains at a newer floor; a truly hostile filesystem needs an external
    monotonic counter/WORM storage.
    """
    @staticmethod
    def _secret():
        s = os.environ.get("VCORE_HMAC_SECRET", "").strip()
        if not s:
            raise RuntimeError("HARD FAIL: VCORE_HMAC_SECRET is required in production environment.")
        return s.encode("utf-8")

    @staticmethod
    def sign(payload):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hmac.new(ManifestStore._secret(), raw, hashlib.sha256).hexdigest()

    @staticmethod
    def _atomic_json_write(path, payload):
        path = str(path)
        tmp = path + f".tmp.{os.getpid()}.{uuid.uuid4().hex}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, sort_keys=True, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)

    @staticmethod
    def _ledger_records():
        if not os.path.exists(Config.LEDGER_FILE): return []
        out=[]
        with open(Config.LEDGER_FILE, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip(): continue
                try: out.append(json.loads(line))
                except Exception as e: raise RuntimeError(f"LEDGER_JSON_CORRUPT: line={lineno}") from e
        return out

    @staticmethod
    def _verify_chain(records):
        prev_sig = "GENESIS"
        expected_seq = 1
        for rec in records:
            supplied = rec.get("hmac_signature", "")
            body = dict(rec); body.pop("hmac_signature", None)
            if not hmac.compare_digest(supplied, ManifestStore.sign(body)):
                raise RuntimeError("LEDGER_HMAC_INVALID")
            if int(rec.get("sequence_id", -1)) != expected_seq:
                raise RuntimeError("LEDGER_SEQUENCE_GAP_OR_REPLAY")
            if rec.get("parent_manifest_hash", "GENESIS") != prev_sig:
                raise RuntimeError("LEDGER_PARENT_CHAIN_BROKEN")
            prev_sig = supplied
            expected_seq += 1
        return prev_sig, expected_seq-1

    @staticmethod
    def _read_anchor():
        if not os.path.exists(Config.ANCHOR_FILE):
            return 0, "GENESIS"
        try:
            with open(Config.ANCHOR_FILE, encoding="utf-8") as f: a=json.load(f)
            body={"magic":a.get("magic"),"sequence_id":int(a.get("sequence_id",-1)),"tip_hash":a.get("tip_hash")}
            supplied=a.get("hmac_signature","")
            if body["magic"] != Config.ANCHOR_MAGIC:
                raise RuntimeError("ANCHOR_MAGIC_INVALID")
            if body["sequence_id"] < 0 or not body["tip_hash"]:
                raise RuntimeError("ANCHOR_SCHEMA_INVALID")
            if not hmac.compare_digest(supplied, ManifestStore.sign(body)):
                raise RuntimeError("ANCHOR_HMAC_INVALID")
            return body["sequence_id"], body["tip_hash"]
        except RuntimeError: raise
        except Exception as e:
            raise RuntimeError("ANCHOR_CORRUPT") from e

    @staticmethod
    def _write_anchor(sequence_id, tip_hash):
        body={"magic":Config.ANCHOR_MAGIC,"sequence_id":int(sequence_id),"tip_hash":str(tip_hash)}
        payload=dict(body); payload["hmac_signature"]=ManifestStore.sign(body)
        ManifestStore._atomic_json_write(Config.ANCHOR_FILE, payload)

    @staticmethod
    def save(payload, path=None):
        with ManifestStore._lock:
            if path is None: path = Config.STATE_FILE
            payload = dict(payload)
            if payload.get("config_sha256") != config_sha256():
                raise RuntimeError("SAVE_CONFIG_HASH_MISMATCH")
            source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            if payload.get("source_sha256") != source_hash:
                raise RuntimeError("SAVE_SOURCE_HASH_MISMATCH")
            records = ManifestStore._ledger_records()
            tip, seq = ManifestStore._verify_chain(records) if records else ("GENESIS", 0)
            anchor_seq, anchor_tip = ManifestStore._read_anchor()
            if anchor_seq > seq:
                raise RuntimeError(f"PHYSICAL_ROLLBACK_DETECTED: anchor={anchor_seq}, ledger={seq}")
            if anchor_seq and anchor_seq != seq:
                raise RuntimeError(f"ANCHOR_LEDGER_DIVERGENCE: anchor={anchor_seq}, ledger={seq}")
            if anchor_seq and anchor_tip != tip:
                raise RuntimeError("ANCHOR_TIP_MISMATCH")

            payload["sequence_id"] = seq + 1
            payload["manifest_id"] = str(uuid.uuid4())
            payload["parent_manifest_hash"] = tip
            payload["hmac_signature"] = ManifestStore.sign(payload)

            line=json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
            with open(Config.LEDGER_FILE, "a", encoding="utf-8") as lf:
                lf.write(line); lf.flush(); os.fsync(lf.fileno())
            ManifestStore._atomic_json_write(path, payload)
            ManifestStore._write_anchor(payload["sequence_id"], payload["hmac_signature"])

    @staticmethod
    def load(path=None):
        with ManifestStore._lock:
            if path is None: path = Config.STATE_FILE
            if not os.path.exists(path): raise RuntimeError("STATE_NOT_FOUND")
            records = ManifestStore._ledger_records()
            if not records: raise RuntimeError("LEDGER_NOT_FOUND")
            tip, tip_seq = ManifestStore._verify_chain(records)
            anchor_seq, anchor_tip = ManifestStore._read_anchor()
            if anchor_seq != tip_seq or anchor_tip != tip:
                if anchor_seq > tip_seq:
                    raise RuntimeError(f"PHYSICAL_ROLLBACK_DETECTED: anchor={anchor_seq}, ledger={tip_seq}")
                raise RuntimeError("ANCHOR_LEDGER_TIP_MISMATCH")
            with open(path, encoding="utf-8") as f: payload=json.load(f)
            supplied=payload.get("hmac_signature", "")
            body=dict(payload); body.pop("hmac_signature", None)
            if not hmac.compare_digest(supplied, ManifestStore.sign(body)):
                raise RuntimeError("HMAC_AUTHENTICATION_FAILED")
            if supplied != tip or int(payload.get("sequence_id", -1)) != tip_seq:
                raise RuntimeError("MANIFEST_REPLAY_OR_LEDGER_TIP_MISMATCH")
            payload["hmac_signature"] = supplied
            return payload

    @staticmethod
    def verify_for_target(db, target_dt=None):
        state=ManifestStore.load()
        if state.get("config_sha256") != config_sha256():
            raise RuntimeError("CONFIG_HASH_MISMATCH")
        source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if state.get("source_sha256") != source_hash:
            raise RuntimeError("SOURCE_HASH_MISMATCH")
        train_end=datetime.strptime(state["train_end"], "%Y-%m-%d")
        if Forensic.prefix_hash(db, train_end) != state.get("train_prefix_sha256"):
            raise RuntimeError("TRAIN_PREFIX_MODIFIED_OR_DATA_REWRITTEN")
        # The manifest also freezes every historical OOS row that existed when
        # the manifest was created. New rows after oos_end are allowed; edits,
        # deletions, or substitutions inside the frozen snapshot are not.
        oos_end=datetime.strptime(state["oos_end"], "%Y-%m-%d")
        frozen_snapshot_hash=state.get("dataset_sha256")
        if not frozen_snapshot_hash:
            raise RuntimeError("MANIFEST_OOS_SNAPSHOT_HASH_MISSING")
        if Forensic.prefix_hash(db, oos_end) != frozen_snapshot_hash:
            raise RuntimeError("OOS_SNAPSHOT_MODIFIED_OR_ROLLED_BACK")
        contract=state.get("frozen_policy_contract", {})
        if contract.get("live_must_use_manifest") is not True:
            raise RuntimeError("FROZEN_POLICY_CONTRACT_INVALID")
        if contract.get("score_function") != "QuantEngine.strategy_scores":
            raise RuntimeError("FROZEN_SCORE_FUNCTION_MISMATCH")
        if contract.get("legacy_score_path_forbidden") is not True:
            raise RuntimeError("LEGACY_PATH_NOT_EXPLICITLY_FORBIDDEN")
        if contract.get("mm_formula") != "WR21 tier: >=0.50=>1.00x; >=0.35=>0.50x; else 0.20x; 4-loss circuit=>0.00x":
            raise RuntimeError("MM_POLICY_CONTRACT_MISMATCH")
        if contract.get("candidate_top_k") != 20 or contract.get("final_audit_top_k") != 5:
            raise RuntimeError("FROZEN_RANKING_CONTRACT_MISMATCH")
        if contract.get("allocation_tiers") != [1.30, 1.15, 0.85]:
            raise RuntimeError("ALLOCATION_TIER_CONTRACT_MISMATCH")
        if contract.get("audit_context_version") != "A1":
            raise RuntimeError("AUDIT_CONTEXT_CONTRACT_MISMATCH")
        if int(contract.get("crawler_quorum", 0)) != Config.CRAWL_MIN_QUORUM:
            raise RuntimeError("CRAWLER_QUORUM_CONTRACT_MISMATCH")
        if not state.get("edge_confirmed", False):
            raise RuntimeError("FROZEN_PURE_OOS_EDGE_NOT_CONFIRMED")
        if target_dt is not None:
            oos_start=datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if target_dt < oos_start:
                raise RuntimeError("FORENSIC_TARGET_IN_TRAINING_WINDOW")
        return state

def canonical_config_dict():
    out = {}
    for k in sorted(Config.__dict__):
        if k.startswith("_") or callable(getattr(Config, k)): continue
        v = getattr(Config, k)
        if k in {"HMAC_SECRET"}: continue
        if isinstance(v, dict): out[k] = {str(a): (sorted(b) if isinstance(b, set) else b) for a, b in sorted(v.items(), key=lambda z: str(z[0]))}
        elif isinstance(v, set): out[k] = sorted(v)
        elif isinstance(v, (str, int, float, bool, list, tuple)): out[k] = list(v) if isinstance(v, tuple) else v
    return out

def config_sha256():
    raw = json.dumps(canonical_config_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class AuditContext:
    """Request-scoped immutable forensic execution context.

    Performance contract:
      - DB/manifest are verified once per audit request.
      - The canonical 100-column prize matrix is materialized once.
      - HMM/RL objects are materialized once.
      - signal/prediction/MM results are memoized only inside this request.

    Security contract:
      - Context is NEVER persisted to disk.
      - It is bound to the exact db object + manifest sequence/id.
      - It cannot bypass ManifestStore.verify_for_target().
    """
    def __init__(self, db, state_manifest):
        if not isinstance(db, dict) or not db:
            raise RuntimeError("AUDIT_CONTEXT_DB_INVALID")
        if state_manifest is None:
            raise RuntimeError("AUDIT_CONTEXT_MANIFEST_REQUIRED")
        required = {"sequence_id", "manifest_id", "hmm", "rl", "oos_start", "oos_end", "train_end", "dataset_sha256"}
        if not required.issubset(state_manifest):
            raise RuntimeError("AUDIT_CONTEXT_MANIFEST_INCOMPLETE")
        self.db = db
        self.state = state_manifest
        self.db_identity = id(db)
        self.sequence_id = int(state_manifest["sequence_id"])
        self.manifest_id = str(state_manifest["manifest_id"])
        self.dates = sorted(x["date_obj"] for x in db.values())
        self.date_keys = [d.strftime("%d/%m/%Y") for d in self.dates]
        self.matrix = QuantEngine._matrix(db, self.dates)
        self.hmm = GaussianHMM.from_dict(state_manifest["hmm"])
        self.rl = QLearningSelector(); self.rl.load(state_manifest.get("rl", {}))
        # Prefix-safe feature/HMM precomputation: each row only depends on
        # current/past observations, so the full-prefix forward pass is exactly
        # equivalent to refitting the filter on every historical prefix.
        self.features_full = build_features(self.matrix)
        self.probs_full = self.hmm._forward(self.features_full)
        self.regime_full = np.argmax(self.probs_full, axis=1).astype(int)
        self.signal_cache = {}
        self.prediction_cache = {}
        self.mm_cache = {}

    def index_before(self, target_dt):
        return bisect_left(self.dates, target_dt)

    def matrix_before(self, target_dt):
        idx = self.index_before(target_dt)
        if idx < 21:
            return idx, None
        return idx, self.matrix[:idx]

    def regime_before(self, target_dt):
        idx = self.index_before(target_dt)
        if idx < 21:
            return idx, None, None
        row = idx - 1
        return idx, int(self.regime_full[row]), self.probs_full[row]

class QuantEngine:
    _sig_cache={}; _mm_cache={}; _research_cache={}

    @staticmethod
    def clear_cache():
        QuantEngine._sig_cache.clear(); QuantEngine._mm_cache.clear(); QuantEngine._research_cache.clear()

    @staticmethod
    def _matrix(db,dates):
        rows = []
        for d in dates:
            tails = db[d.strftime("%d/%m/%Y")]["prizes_int"]
            if len(tails) != 27: raise ValueError(f"MATRIX_27_TAIL_INVARIANT_FAIL: {d}")
            vec = np.zeros(100, dtype=float)
            for n in tails: vec[int(n)] += 1.0
            rows.append(vec)
        return np.asarray(rows, dtype=float)

    @staticmethod
    def strategy_scores(M, strategy):
        M = np.asarray(M, dtype=float)
        if len(M) < 21: return np.full(100, 0.5, dtype=float)
        b = (M > 0).astype(float)
        f21 = b[-21:].mean(axis=0)
        f7 = b[-7:].mean(axis=0)
        if strategy == "bayesian": return f21
        if strategy == "momentum": return f7 - f21
        if strategy == "mean_reversion": return f21 - f7
        raise ValueError(f"UNKNOWN_STRATEGY: {strategy}")

    @staticmethod
    def _rank_strategy(M, strategy, top_k=20):
        scores = QuantEngine.strategy_scores(M, strategy)
        idx = np.argsort(scores, kind="stable")[-top_k:][::-1]
        return [int(x) for x in idx], scores

    @staticmethod
    def get_signal(target_dt, db, state_manifest, context=None):
        """Canonical frozen-policy signal. No legacy fallback is permitted."""
        if state_manifest is None:
            raise RuntimeError("STRICT_FORENSIC: MUST_USE_MANIFEST")
        required = {"hmm", "rl", "train_end", "oos_start", "frozen_policy_contract"}
        if not required.issubset(state_manifest):
            raise RuntimeError("STRICT_FORENSIC: MANIFEST_SCHEMA_INCOMPLETE")
        contract = state_manifest.get("frozen_policy_contract", {})
        if contract.get("live_must_use_manifest") is not True or contract.get("score_function") != "QuantEngine.strategy_scores":
            raise RuntimeError("STRICT_FORENSIC: FROZEN_POLICY_CONTRACT_BREACH")
        if context is not None:
            if context.db is not db or context.sequence_id != int(state_manifest.get("sequence_id", -1)) or context.manifest_id != str(state_manifest.get("manifest_id")):
                raise RuntimeError("STRICT_FORENSIC: AUDIT_CONTEXT_BINDING_BREACH")
            cache_key = target_dt.strftime("%Y-%m-%d")
            if cache_key in context.signal_cache:
                return context.signal_cache[cache_key]
            past_count, M = context.matrix_before(target_dt)
            if M is None:
                return None, "[THIẾU LỊCH SỬ >=21 NGÀY]"
            _, regime, _ = context.regime_before(target_dt)
            strategy = context.rl.select(regime, explore=False)
            candidates, scores = QuantEngine._rank_strategy(M, strategy, top_k=20)
        else:
            key = (target_dt, Forensic.dataset_hash(db), state_manifest.get("manifest_id"), state_manifest.get("sequence_id"))
            if key in QuantEngine._sig_cache: return QuantEngine._sig_cache[key]
            past = sorted([x["date_obj"] for x in db.values() if x["date_obj"] < target_dt], reverse=True)
            if len(past) < 21: return None, "[THIẾU LỊCH SỬ >=21 NGÀY]"
            M = QuantEngine._matrix(db, list(reversed(past)))
            hmm = GaussianHMM.from_dict(state_manifest["hmm"])
            rl = QLearningSelector(); rl.load(state_manifest.get("rl", {}))
            features = build_features(M); regime = hmm.filtered_regime(features); strategy = rl.select(regime, explore=False)
            candidates, scores = QuantEngine._rank_strategy(M, strategy, top_k=20)
        trace = f"[FORENSIC FROZEN POLICY] regime={regime} | strategy={strategy} | score_source={strategy} | candidates={len(candidates)}"
        if context is not None:
            idx = context.index_before(target_dt)
            t1_key = context.date_keys[idx-1]; t2_key = context.date_keys[idx-2]; t3_key = context.date_keys[idx-3]
        else:
            t1_key = past[0].strftime("%d/%m/%Y"); t2_key = past[1].strftime("%d/%m/%Y"); t3_key = past[2].strftime("%d/%m/%Y")
        t1 = set(db[t1_key]["prizes_int"])
        recent = set(db[t2_key]["prizes_int"]) | set(db[t3_key]["prizes_int"])
        dan = [n for n in candidates if n in recent or n in t1 or ((n%10)*10+n//10) in t1]
        if len(dan) < 5: dan = candidates[:5]
        res = (sorted(dan), trace)
        if context is not None: context.signal_cache[cache_key] = res
        else: QuantEngine._sig_cache[key] = res
        return res

    @staticmethod
    def get_full_prediction(target_dt, db, state_manifest, context=None):
        """Fix 2: Propagating mandatory state_manifest."""
        dan, trace = QuantEngine.get_signal(target_dt, db, state_manifest, context=context)
        if dan is None: return None, trace
        
        if context is not None:
            idx, M = context.matrix_before(target_dt)
            if M is None: return None, "[THIẾU LỊCH SỬ >=21 NGÀY]"
            _, regime, _ = context.regime_before(target_dt)
            strategy = context.rl.select(regime, explore=False)
        else:
            past = sorted([x["date_obj"] for x in db.values() if x["date_obj"] < target_dt], reverse=True)
            M = QuantEngine._matrix(db, list(reversed(past)))
            hmm = GaussianHMM.from_dict(state_manifest["hmm"])
            rl = QLearningSelector(); rl.load(state_manifest.get("rl", {}))
            regime = hmm.filtered_regime(build_features(M))
            strategy = rl.select(regime, explore=False)
        raw_scores = QuantEngine.strategy_scores(M, strategy)
        
        score = {n: float(raw_scores[n]) for n in dan}
        final = sorted(dan, key=lambda n: (score[n], n), reverse=True)
        best = final[0] if final else 0
        mirror = (best%10)*10 + best//10
        stl = (final[1] if len(final)>1 else mirror, final[2] if len(final)>2 else ((best+11)%100))
        return {
            "btl": f"{best:02d}", "stl": f"{stl[0]:02d} - {stl[1]:02d}",
            "xien2": f"{best:02d} - {stl[0]:02d} | {best:02d} - {stl[1]:02d}",
            "cang3d": "[KHÔNG CÓ FULL 3-SỐ — FAIL CLOSED]",
            "kep": " - ".join(f"{x:02d}" for x in sorted([x for x in range(0,100,11)], key=lambda x:(x not in final,-score.get(x,0)))[:2]),
            "dan_de_10": ", ".join(f"{x:02d}" for x in sorted(final[:10])),
            "sorted_dan_scored": final,
            "strategy_scores": {str(k): score[k] for k in final},
            "selected_strategy": strategy,
            "regime": regime,
            "sig_trace": trace + " | LIVE/OOS CANONICAL SCORE PATH"
        }, "OK"

    @staticmethod
    def get_mm_multiplier(target_dt, db, state_manifest, context=None):
        """Frozen-policy risk sizing; request-scoped memoization only."""
        if state_manifest is None:
            raise RuntimeError("STRICT_FORENSIC: MM_REQUIRES_MANIFEST")
        if context is not None:
            if (context.db is not db or
                    context.sequence_id != int(state_manifest.get("sequence_id", -1)) or
                    context.manifest_id != str(state_manifest.get("manifest_id"))):
                raise RuntimeError("STRICT_FORENSIC: AUDIT_CONTEXT_BINDING_BREACH")
            key = target_dt.strftime("%Y-%m-%d")
            if key in context.mm_cache: return context.mm_cache[key]
        else:
            key = (target_dt, state_manifest.get("manifest_id"), state_manifest.get("sequence_id"))
            if key in QuantEngine._mm_cache: return QuantEngine._mm_cache[key]
        oos_start=datetime.strptime(state_manifest["oos_start"], "%Y-%m-%d")
        if context is not None:
            idx = context.index_before(target_dt)
            if idx < 21: result=(0.0,"[RISK GATE] <21 OOS-ELIGIBLE DAYS => 0.00x")
            else:
                if target_dt > datetime.strptime(state_manifest["train_end"], "%Y-%m-%d"):
                    lookback_dates = context.dates[max(0,idx-21):idx]
                    if any(d < oos_start for d in lookback_dates):
                        result=(0.0,"[RISK GATE] OOS LOOKBACK <21 DAYS => 0.00x")
                    else: result=None
                else: result=None
                if result is None:
                    daily=[]; streak=0
                    for dt in reversed(context.dates[max(0,idx-21):idx]):
                        dan,_=QuantEngine.get_signal(dt, db, state_manifest, context=context)
                        if not dan: continue
                        prizes=db[dt.strftime("%d/%m/%Y")]["prizes_int"]
                        pnl=sum(prizes.count(x)*Config.WIN_PER_NHAY for x in dan)-len(dan)*Config.BASE_PTS*Config.COST_PER_POINT
                        daily.append(pnl); streak = 0 if pnl>0 else streak+1
                    if not daily: result=(0.0,"[RISK GATE] NO_VALID_POLICY_OUTCOMES => 0.00x")
                    elif streak>=4: result=(0.0,"[CIRCUIT BREAKER] 4 consecutive losses => 0.00x")
                    else:
                        wr=sum(x>0 for x in daily)/len(daily); mult=1.0 if wr>=0.50 else (0.50 if wr>=0.35 else 0.20)
                        result=(mult,f"[FROZEN POLICY RISK] WR21={wr:.1%} | streak={streak} | multiplier={mult:.2f}x")
        else:
            past=sorted([x["date_obj"] for x in db.values() if x["date_obj"] < target_dt], reverse=True)
            if len(past)<21: result=(0.0,"[RISK GATE] <21 OOS-ELIGIBLE DAYS => 0.00x")
            elif target_dt > datetime.strptime(state_manifest["train_end"], "%Y-%m-%d") and any(d < oos_start for d in past[:21]):
                result=(0.0,"[RISK GATE] OOS LOOKBACK <21 DAYS => 0.00x")
            else:
                daily=[]; streak=0
                for dt in past[:21]:
                    dan,_=QuantEngine.get_signal(dt, db, state_manifest)
                    if not dan: continue
                    prizes=db[dt.strftime("%d/%m/%Y")]["prizes_int"]
                    pnl=sum(prizes.count(x)*Config.WIN_PER_NHAY for x in dan)-len(dan)*Config.BASE_PTS*Config.COST_PER_POINT
                    daily.append(pnl); streak = 0 if pnl>0 else streak+1
                if not daily: result=(0.0,"[RISK GATE] NO_VALID_POLICY_OUTCOMES => 0.00x")
                elif streak>=4: result=(0.0,"[CIRCUIT BREAKER] 4 consecutive losses => 0.00x")
                else:
                    wr=sum(x>0 for x in daily)/len(daily); mult=1.0 if wr>=0.50 else (0.50 if wr>=0.35 else 0.20)
                    result=(mult,f"[FROZEN POLICY RISK] WR21={wr:.1%} | streak={streak} | multiplier={mult:.2f}x")
        if context is not None: context.mm_cache[key]=result
        else: QuantEngine._mm_cache[key]=result
        return result

    @staticmethod
    def backtest_forensic(db):
        dates = sorted(x["date_obj"] for x in db.values())
        N = len(dates)
        if N < 80: return {"status":"BLOCKED","reason":"NEED_80_DAYS"}
        split = max(Config.MIN_HISTORY_DAYS, int(N*Config.OOS_TRAIN_RATIO))
        if split >= N-10: return {"status":"BLOCKED","reason":"OOS_TOO_SHORT"}

        strategies=["bayesian","momentum","mean_reversion"]
        returns={s:[] for s in strategies}; th=ThompsonSelector(seed=42); rl=QLearningSelector(seed=42)
        hmm_cache=None; prev_regime=None; prev_strategy=None

        full_M = QuantEngine._matrix(db, dates)
        full_features = build_features(full_M)
        for t in range(Config.MIN_HISTORY_DAYS, split):
            history=dates[:t]; M=full_M[:t]; features=full_features[:t]
            if hmm_cache is None or (t % Config.HMM_REFIT_INTERVAL == 0):
                hmm_cache=GaussianHMM(Config.HMM_STATES,Config.HMM_MAX_ITER,Config.HMM_TOL,42).fit(features)
            regime=hmm_cache.filtered_regime(features)
            if prev_strategy is not None:
                prev_history=dates[:t-1]; prev_M=full_M[:t-1]
                prev_scores=QuantEngine.strategy_scores(prev_M, prev_strategy)
                top=np.argsort(prev_scores,kind="stable")[-5:]
                actual=db[dates[t-1].strftime("%d/%m/%Y")]["prizes_int"]
                hits=sum(actual.count(int(n)) for n in top)
                cost=5*Config.BASE_PTS*Config.COST_PER_POINT; rev=hits*Config.BASE_PTS*Config.WIN_PER_NHAY
                reward=(rev-cost)/cost
                th.update(prev_strategy,reward); rl.update(prev_regime,prev_strategy,reward,regime)
            prev_regime=regime; prev_strategy=rl.select(regime,explore=True)

        if hmm_cache is None: return {"status":"BLOCKED","reason":"HMM_NOT_FIT"}
        frozen_hmm=hmm_cache
        oos_policy=[]
        frozen_probs=frozen_hmm._forward(full_features)
        for t in range(split,N):
            M=full_M[:t]; regime=int(np.argmax(frozen_probs[t-1]))
            strategy=rl.select(regime,explore=False)
            actual=db[dates[t].strftime("%d/%m/%Y")]["prizes_int"]
            for sname in strategies:
                scores=QuantEngine.strategy_scores(M,sname); top=np.argsort(scores,kind="stable")[-5:]
                hits=sum(actual.count(int(n)) for n in top); cost=5*Config.BASE_PTS*Config.COST_PER_POINT; rev=hits*Config.BASE_PTS*Config.WIN_PER_NHAY
                returns[sname].append((rev-cost)/cost)
            scores=QuantEngine.strategy_scores(M,strategy); top=np.argsort(scores,kind="stable")[-5:]
            hits=sum(actual.count(int(n)) for n in top); cost=5*Config.BASE_PTS*Config.COST_PER_POINT; rev=hits*Config.BASE_PTS*Config.WIN_PER_NHAY
            oos_policy.append((rev-cost)/cost)

        p={s:mbb_pvalue(v,Config.MBB_BLOCK_SIZE,Config.MBB_RUNS,42) for s,v in returns.items()}
        rej,qv=bh_fdr(p,Config.FDR_Q); policy=np.asarray(oos_policy,float); policy_p=mbb_pvalue(policy,Config.MBB_BLOCK_SIZE,Config.MBB_RUNS,42)
        eligible=[s for s in strategies if len(returns[s])>=Config.MIN_OOS_TRADES and np.mean(returns[s])>Config.MIN_EXPECTANCY and rej[s]]
        edge=bool(eligible and policy_p<Config.MIN_BOOTSTRAP_P and np.mean(policy)>0)
        train_end=dates[split-1]
        train_M=QuantEngine._matrix(db, dates[:split])
        frozen_hmm=GaussianHMM(Config.HMM_STATES, Config.HMM_MAX_ITER, Config.HMM_TOL, 42).fit(build_features(train_M))
        payload={
            "version":Config.VERSION,"config_sha256":config_sha256(),"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "parser_version":Forensic.PARSER_VERSION,"train_start":dates[0].strftime("%Y-%m-%d"),"train_end":train_end.strftime("%Y-%m-%d"),
            "oos_start":dates[split].strftime("%Y-%m-%d"),"oos_end":dates[-1].strftime("%Y-%m-%d"),"train_rows":split,"oos_rows":N-split,"split_idx":split,
            "train_prefix_sha256":Forensic.prefix_hash(db,train_end),"dataset_sha256":Forensic.dataset_hash(db),
            "strategy_pvalues":p,"strategy_fdr_q":qv,
            "strategy_stats":{s:{"trades":len(returns[s]),"expectancy":float(np.mean(returns[s])) if returns[s] else 0.0,"fdr_rejected":bool(rej[s])} for s in strategies},
            "policy_oos_pvalue":policy_p,"policy_oos_expectancy":float(np.mean(policy)) if len(policy) else 0.0,
            "eligible_strategies":eligible,"edge_confirmed":edge,
            "frozen_policy_contract":{
                "score_function":"QuantEngine.strategy_scores",
                "strategies":strategies,
                "candidate_top_k":20,
                "final_audit_top_k":5,
                "live_must_use_manifest":True,
                "legacy_score_path_forbidden":True,
                "mm_formula":"WR21 tier: >=0.50=>1.00x; >=0.35=>0.50x; else 0.20x; 4-loss circuit=>0.00x",
                "allocation_tiers":[1.30,1.15,0.85],
                "audit_context_version":"A1",
                "crawler_quorum":Config.CRAWL_MIN_QUORUM
            },
            "hmm":frozen_hmm.to_dict(),"thompson":th.to_dict(),"rl":rl.to_dict(),
        }
        ManifestStore.save(payload); return payload

# ==============================================================================
# 📊 BLOCK 6: AUDIT & REPORTING MANAGER
# ==============================================================================
class Auditor:
    @staticmethod
    def _verify_forensic_state(db, latest_dt, target_dt=None):
        return ManifestStore.verify_for_target(db, target_dt=target_dt)

    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = "ℹ️ Chế độ Offline. Bấm nút cập nhật để kích hoạt Radar."
        db = None
        if auto_crawl:
            crawl_msg, db = DatabaseManager.auto_heal_history()
        if db is None:
            db, msg = DatabaseManager.load_db()
        else:
            msg = "🟢 DB đã được nạp trong cùng phiên AUTO-HEAL; bỏ qua lần đọc lại Google Sheets."
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        latest_str = latest_dt.strftime('%d/%m/%Y') if latest_dt else "⚠️ CHƯA CÓ DỮ LIỆU!"
        lines = [
            "📑 BÁO CÁO ĐỒNG BỘ CƠ SỞ DỮ LIỆU TOÀN MẠNG",
            "=================================================================================",
            f"• Phiên bản hệ thống : {Config.VERSION}",
            f"• Trạng thái Dữ liệu : {msg}",
            f"• Báo cáo Crawler    : {crawl_msg}",
            "---------------------------------------------------------------------------------",
            f"• Dữ liệu cập nhật đến ngày : 📅 [{latest_str}]",
            f"• Sẵn sàng tính toán cho kỳ : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
        ]
        return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"

    @staticmethod
    def process_manual_input(date_str, num_str):
        save_msg = DatabaseManager.save_manual_data(date_str, num_str)
        report, title = Auditor.phan_he_1_sync(auto_crawl=False)
        return f"{save_msg}\n\n{report}", title

    @staticmethod
    def phan_he_2_predict(pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, next_dt = DatabaseManager.get_boundaries(db)
            if latest_dt is None: return "🛑 NO_TRADE: DATABASE_EMPTY"
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 NO_TRADE: {e}"
            
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn Cơ sở")
            if not valid: return err

            hmm = GaussianHMM.from_dict(state["hmm"])
            th = ThompsonSelector(); th.load(state.get("thompson", {}))
            rl = QLearningSelector(); rl.load(state.get("rl", {}))
            dates = sorted(x["date_obj"] for x in db.values() if x["date_obj"] <= latest_dt)
            M = QuantEngine._matrix(db, dates)
            features = build_features(M)
            regime = hmm.filtered_regime(features)
            probs = hmm.filtered_probs(features)
            strategy = rl.select(regime, explore=False)
            th_probs = th.best_prob(1000)
            q = rl.q[regime, rl.strategies.index(strategy)]
            allowed = strategy in rl.valid(regime)
            policy_pass = allowed and th_probs[strategy] >= Config.THOMPSON_MIN_PROB and q > Config.MIN_RL_Q

            pred_data, status = QuantEngine.get_full_prediction(next_dt, db, state)
            if pred_data is None: return f"🛑 CẢNH BÁO: {status}"
            sorted_dan = pred_data["sorted_dan_scored"]
            multiplier, mm_trace = QuantEngine.get_mm_multiplier(next_dt, db, state)
            base_pts = float(pts_per_code_base)
            if not policy_pass: multiplier = 0.0
            alloc=[]; total=0.0
            for i, code in enumerate(sorted_dan):
                tier = 1.30 if i == 0 else (1.15 if i in (1,2) else 0.85)
                pts = int(round(base_pts*multiplier*tier))
                cost = pts*Config.COST_PER_POINT
                total += cost
                alloc.append(f"   + [{code:02d}] {'BẠCH THỦ' if i==0 else ('SONG THỦ' if i in (1,2) else 'Lót dàn')} | {pts}đ | {cost:,.0f} VNĐ")
            return "\n".join([
                "📑 BÁO CÁO KHUYẾN NGHỊ GIAO DỊCH FORENSIC V5.8",
                "="*60, f"🎯 TARGET: {next_dt.strftime('%d/%m/%Y')}",
                f"🔗 MANIFEST: seq={state.get('sequence_id')} id={state.get('manifest_id', 'UNKNOWN')}",
                f"🧊 FROZEN HMM: regime={regime} | probs=" + ", ".join(f"{x:.3f}" for x in probs),
                f"🧠 POLICY: {strategy} | Thompson={th_probs[strategy]:.3f} | Q={q:.4f} | allowed={allowed}",
                f"🛡️ POLICY GATE: {'PASS' if policy_pass else 'NO_TRADE'}",
                f"📋 DÀN: {' '.join(f'{x:02d}' for x in sorted_dan)}",
                "💰 PHÂN BỔ:", *(alloc or ["   [ĐỨNG NGOÀI]"]),
                f"💰 TỔNG VỐN: {total:,.0f} VNĐ", mm_trace, pred_data["sig_trace"],
                "⚠️ CÀNG 3: [KHÔNG CÓ FULL 3-SỐ — FAIL CLOSED]"
            ])
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_router(audit_type, date_raw, month_raw, pts_per_code_base):
        if audit_type == "Kiểm toán 1 Ngày": return Auditor.phan_he_3_single(date_raw, pts_per_code_base)
        else: return Auditor.phan_he_3_monthly_detail(month_raw, pts_per_code_base)

    @staticmethod
    def phan_he_3_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, _ = DatabaseManager.get_boundaries(db)
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."
            
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            try: state = Auditor._verify_forensic_state(db, latest_dt, target_dt=d_obj)
            except RuntimeError as e: return f"🛑 LỖI FORENSIC WINDOW: {e}"
            context = AuditContext(db, state)
            if ngay_str not in db: return f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên {ngay_str} chưa cập nhật."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            
            lines = [
                "📑 BÁO CÁO KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN (SINGLE FROZEN TRUTH)",
                "========================================================================",
                f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str}",
                "========================================================================"
            ]
            pred_data, msg = QuantEngine.get_full_prediction(d_obj, db, state, context=context)
            mode_name = Config.ACTIVE_MODE.split(']')[1].strip()
            if pred_data is None: 
                lines.extend([f"🛑 [{mode_name}]: Thiếu dữ liệu", f"   > Lý do truy vết: {msg}"])
            else: 
                mult, mm_trace = QuantEngine.get_mm_multiplier(d_obj, db, state, context=context)
                sorted_dan = pred_data["sorted_dan_scored"]
                sl = len(sorted_dan)
                if sl == 0:
                    lines.append(f"🛑 [{mode_name}] 👉 KHÔNG CÓ MÃ ĐẠT CHUẨN (ĐỨNG NGOÀI)")
                else:
                    prizes_today = db[ngay_str]["prizes_int"]
                    day_cost, day_rev = 0.0, 0.0
                    hit_details = []
                    for idx_code, code_val in enumerate(sorted_dan):
                        k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                        pts_code = int(round(float(pts_per_code_base) * mult * k_tier))
                        if pts_code > 0:
                            c_code = pts_code * Config.COST_PER_POINT
                            nhay_code = prizes_today.count(code_val)
                            r_code = nhay_code * pts_code * Config.WIN_PER_NHAY
                            day_cost += c_code
                            day_rev += r_code
                            if nhay_code > 0: hit_details.append(f"[{code_val:02d}] nổ {nhay_code} nháy = +{r_code:,.0f} đ")
                    lai = day_rev - day_cost
                    st = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                    lines.extend([
                        f"📌 [{mode_name}]",
                        f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in sorted_dan]),
                        f" • Chi tiết trúng: " + (", ".join(hit_details) if hit_details else "🚫 Không trúng mã nào"),
                        f" • Tổng vốn dồn: {day_cost/1000:,.0f}k | Thu thưởng: {day_rev/1000:,.0f}k",
                        f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})\n"
                    ])
                lines.extend(["   --- LOG TRUY VẾT CẢM BIẾN & ĐI VỐN ---", "   " + pred_data['sig_trace'].replace("\n", "\n   "), "   " + mm_trace.replace("\n", "\n   ")])
            lines.append("------------------------------------------------------------------------")
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_monthly_detail(month_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, _ = DatabaseManager.get_boundaries(db)
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."
            
            m = re.match(r'^(\d{1,2})[-/.](\d{4})$', str(month_raw).strip())
            if not m: return "🛑 LỖI ĐỊNH DẠNG: Vui lòng nhập tháng dạng MM/YYYY."
            thang, nam = int(m.group(1)), int(m.group(2))
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = float(pts_per_code_base)
            start_dt = datetime(nam, thang, 1)
            max_day = calendar.monthrange(nam, thang)[1]
            end_dt = datetime(nam, thang, max_day)
            
            lines = [
                f"📑 BÁO CÁO CHI TIẾT TỪNG NGÀY: THÁNG {thang:02d}/{nam}",
                f"🎚️ LÕI ĐỘC TÔN: V5.8 FORENSIC VERIFIED CORE",
                "=============================================================================================================================",
                f"{'NGÀY':<6} | {'MÃ ĐÁNH':<26} | {'VỐN DỒN (k)':<12} | {'THU (k)':<8} | {'LÃI/LỖ (k)':<11} | {'ROI':<8}",
                "-----------------------------------------------------------------------------------------------------------------------------"
            ]
            oos_start=datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if Config.REQUIRE_OOS_AUDIT and end_dt < oos_start:
                return "🛑 FORENSIC AUDIT BLOCKED: tháng nằm hoàn toàn trong TRAINING WINDOW."
            context = AuditContext(db, state)
            curr = max(start_dt, oos_start) if Config.REQUIRE_OOS_AUDIT else start_dt
            tot_von, tot_thu, tot_lai = 0, 0, 0
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                short_date = curr.strftime("%d/%m")
                if ngay_str in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db, state, context=context)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db, state, context=context)
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        sl = len(sorted_dan)
                        dan_str = " ".join([f"{x:02d}" for x in sorted_dan])
                        if len(dan_str) > 20: dan_str = dan_str[:17] + "..."
                        d_list = f"{sl:>2} mã: {dan_str}"
                        prizes_today = db[ngay_str]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(base_pts * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c; day_rev += r_c
                        if day_cost <= 0:
                            lines.append(f"{short_date:<6} | {d_list:<26} | {'0':<12} | {'0':<8} | {'[ĐỨNG NGOÀI]':<11} | {'-':<8}")
                        else:
                            lai = day_rev - day_cost
                            roi = (lai / day_cost * 100) if day_cost > 0 else 0
                            tot_von += day_cost; tot_thu += day_rev; tot_lai += lai
                            lines.append(f"{short_date:<6} | {d_list:<26} | {day_cost/1000:>12,.0f} | {day_rev/1000:>8,.0f} | {lai/1000:>+11,.0f} | {roi:>+6.1f}%")
                    else: lines.append(f"{short_date:<6} | {'🚫 [ĐỨNG NGOÀI]':<26} | {'-':<12} | {'-':<8} | {'-':<11} | {'-':<8}")
                else: lines.append(f"{short_date:<6} | ⚪ Chưa có dữ liệu DB{'':<1} | {'-':<12} | {'-':<8} | {'-':<11} | {'-':<8}")
                curr += timedelta(days=1)
            tot_roi = (tot_lai / tot_von * 100) if tot_von > 0 else 0
            lines.extend(["=============================================================================================================================", f"📝 TỔNG KẾT THÁNG {thang:02d}/{nam}:", f"💰 TỔNG VỐN DỒN TIERED   : {tot_von:,.0f} VNĐ", f"💵 TỔNG DOANH THU THƯỞNG  : {tot_thu:,.0f} VNĐ", f"🚀 LỢI NHUẬN RÒNG          : {tot_lai:+,.0f} VNĐ", f"📈 TỶ SUẤT R.O.I           : {tot_roi:+.2f} %"])
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_4_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, latest_dt, _ = DatabaseManager.get_boundaries(db)
            try: state = Auditor._verify_forensic_state(db, latest_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."

            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI THÔNG SỐ."
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            if (end_dt - start_dt).days + 1 > Config.MAX_AUDIT_DAYS:
                return f"🛑 AUDIT_RANGE_TOO_LARGE: tối đa {Config.MAX_AUDIT_DAYS} ngày/lần."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = float(pts_per_code_base)
            oos_start=datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if Config.REQUIRE_OOS_AUDIT:
                if end_dt < oos_start:
                    return "🛑 FORENSIC AUDIT BLOCKED: range nằm hoàn toàn trong TRAINING WINDOW."
                start_dt=max(start_dt, oos_start)
            context = AuditContext(db, state)
            lines = [
                "📑 BÁO CÁO ĐẠI KẾ TOÁN QUÉT CHU KỲ TỔNG HỢP",
                "===================================================================================================================",
                f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (LÕI V5.8 FORENSIC VERIFIED)",
                "==================================================================================================================="
            ]
            curr = start_dt
            daily_records = []
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                if ngay_str in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db, state, context=context)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db, state, context=context)
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        prizes_today = db[ngay_str]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(base_pts * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c; day_rev += r_c
                        if day_cost > 0:
                            sl = len(sorted_dan)
                            lai = day_rev - day_cost
                            daily_records.append({
                                "dt": curr, "year": curr.year, "month_str": curr.strftime("%m/%Y"),
                                "codes": sl, "chi": day_cost, "lai": lai,
                                "win": 1 if lai > 0 else 0, "loss": 1 if lai <= 0 else 0,
                            })
                curr += timedelta(days=1)
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO XUẤT LỆNH THỰC TẾ."
            df_rec = pd.DataFrame(daily_records)
            lines.extend(["", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG", "-------------------------------------------------------------------------------------------------------------------", f"{'THÁNG/NĂM':<10} | {'PHIÊN':<7} | {'WIN/LOSS':<10} | {'VỐN ĐẦU TƯ':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}", "-------------------------------------------------------------------------------------------------------------------"])
            for m_str, g_m in df_rec.groupby("month_str", sort=False):
                m_chi, m_lai = g_m["chi"].sum(), g_m["lai"].sum()
                m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
                lines.append(f"Tháng {m_str:<5} | {len(g_m):<7} | {g_m['win'].sum()}W/{g_m['loss'].sum()}L | {m_chi:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%")
                
            tot_chi, tot_lai = df_rec["chi"].sum(), df_rec["lai"].sum()
            tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
            df_rec['cum_pnl'] = df_rec['lai'].cumsum()
            df_rec['peak'] = df_rec['cum_pnl'].cummax()
            max_dd = (df_rec['cum_pnl'] - df_rec['peak']).min()
            lines.extend(["===================================================================================================================", f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN):", f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ", f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ", f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %", f"• SỤT GIẢM VỐN LỚN NHẤT (Max Drawdown) : {abs(max_dd):,.0f} VNĐ", "==================================================================================================================="])
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_5_raw(ngay_raw):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            _, ngay_str = res
            if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại trên hệ thống."
            prizes = db[ngay_str]["prizes_int"]
            if len(prizes) < 27: return "🛑 LỖI DỮ LIỆU: Bảng kết quả không đủ 27 giải."
            lines = [
                "📑 BẢNG KẾT QUẢ XỔ SỐ MIỀN BẮC",
                "=======================================================",
                f"📅 KẾT QUẢ PHIÊN GIAO DỊCH: {ngay_str}",
                "-------------------------------------------------------",
                f"🔴 Đặc Biệt  :  {prizes[0]:02d}", f"🟢 Giải Nhất :  {prizes[1]:02d}", f"🔵 Giải Nhì  :  {prizes[2]:02d} - {prizes[3]:02d}",
                f"🟣 Giải Ba   :  {prizes[4]:02d} - {prizes[5]:02d} - {prizes[6]:02d} - {prizes[7]:02d} - {prizes[8]:02d} - {prizes[9]:02d}",
                f"🟤 Giải Tư   :  {prizes[10]:02d} - {prizes[11]:02d} - {prizes[12]:02d} - {prizes[13]:02d}",
                f"🟠 Giải Năm  :  {prizes[14]:02d} - {prizes[15]:02d} - {prizes[16]:02d} - {prizes[17]:02d} - {prizes[18]:02d} - {prizes[19]:02d}",
                f"🟡 Giải Sáu  :  {prizes[20]:02d} - {prizes[21]:02d} - {prizes[22]:02d}",
                f"⚪ Giải Bảy  :  {prizes[23]:02d} - {prizes[24]:02d} - {prizes[25]:02d} - {prizes[26]:02d}",
                "-------------------------------------------------------", "⚠️ Lưu ý: Bảng hiển thị Loto 2 số (Dữ liệu do Crawler phục vụ thuật toán Quant).", "======================================================="
            ]
            return "\n".join(lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_6_master_diagnostic_prompt():
        try:
            db, msg = DatabaseManager.load_db()
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if not min_dt or not max_dt: return "🛑 HỆ THỐNG RỖNG: Chưa có dữ liệu."
            
            try: state = Auditor._verify_forensic_state(db, max_dt)
            except RuntimeError as e: return f"🛑 LỖI KIỂM TOÁN: Không thể nạp Forensic Manifest ({e})."
            
            oos_start = datetime.strptime(state["oos_start"], "%Y-%m-%d")
            if Config.REQUIRE_OOS_AUDIT and max_dt < oos_start:
                return "🛑 FORENSIC AUDIT BLOCKED: DB chưa có dữ liệu OOS sau train_end."
            context = AuditContext(db, state)
            scan_start = max(min_dt, oos_start) if Config.REQUIRE_OOS_AUDIT else min_dt
            total_days_scanned = (max_dt - scan_start).days + 1
            forensic_state = f"🛡️ FROZEN STATE: VERIFIED | train_end={state.get('train_end')} | oos_start={state.get('oos_start')} | edge={state.get('edge_confirmed')}"
            prompt_lines = [
                f"[HỒ SƠ SINH HỌC TOÀN HỆ THỐNG V5.8 ROBUST - DÀNH CHO BÁO CÁO ĐỊNH LƯỢNG CHUẨN TRUY VẾT]",
                forensic_state,
                f"1. PHIÊN BẢN HỆ THỐNG: {Config.VERSION}",
                f"2. QUÉT TRỌN VẸN LỊCH SỬ {total_days_scanned} NGÀY QUA ({min_dt.strftime('%d/%m/%Y')} ĐẾN {max_dt.strftime('%d/%m/%Y')})\n",
                "📊 [BÁO CÁO HIỆU SUẤT ĐỘC TÔN V5.8]"
            ]
            
            curr = scan_start
            wins, losses, total_chi, total_thu = 0, 0, 0, 0
            daily_pnls = []
            
            while curr <= max_dt:
                str_dt = curr.strftime("%d/%m/%Y")
                if str_dt in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db, state, context=context)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db, state, context=context)
                    
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        prizes_today = db[str_dt]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(Config.BASE_PTS * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c; day_rev += r_c
                                
                        if day_cost > 0:
                            lai = day_rev - day_cost
                            total_chi += day_cost; total_thu += day_rev; daily_pnls.append(lai)
                            if lai > 0: wins += 1
                            else: losses += 1
                curr += timedelta(days=1)

            roi = ((total_thu - total_chi) / total_chi * 100) if total_chi > 0 else 0
            cum_pnl = np.cumsum(daily_pnls) if daily_pnls else []
            peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else []
            drawdowns = cum_pnl - peak if len(cum_pnl) > 0 else []
            max_dd = abs(min(drawdowns)) if len(drawdowns) > 0 else 0

            prompt_lines.extend([
                f"➤ LÕI DUY NHẤT: {Config.ACTIVE_MODE}",
                f"   - Total PnL: {(total_thu - total_chi):+,.0f} VNĐ | ROI: {roi:.2f}% | Max Drawdown: {max_dd:,.0f} VNĐ",
                f"   - Win/Loss: {wins}W / {losses}L | Vốn đầu tư: {total_chi:,.0f} VNĐ | Doanh thu: {total_thu:,.0f} VNĐ",
                "-" * 65, "\n⚠️ XÁC NHẬN BÁO CÁO V5.8 FORENSIC VERIFIED CORE:",
                "1. Tích hợp cơ chế Dồn vốn Bậc thang Risk-Parity chuẩn hóa: Bạch Thủ Lô (1.30x), Song Thủ Lô (1.15x), Lô Dàn Lót (0.85x).",
                "2. HỆ THỐNG CHỈ SỬ DỤNG DUY NHẤT 1 SỰ THẬT: FROZEN POLICY TỪ MANIFEST CHO OOS VÀ LIVE; LEGACY PATH BỊ CẤM.",
                "3. Immutable Append-Only Ledger có Monotonic Anchor chống Rollback Vật Lý."
            ])
            return "\n".join(prompt_lines)
        except Exception: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

# ==============================================================================
# 🖥️ BLOCK 7: GRADIO WEB UI (RENDER READY)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    min_dt_init, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title=Config.VERSION, theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 XSMB QUANT ENGINE {Config.VERSION}")
        with gr.Row(): nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (QUÉT RADAR CRAWLER ĐA LUỒNG)", variant="primary")
            gr.Markdown("---")
            gr.Markdown("✍️ **NHẬP KẾT QUẢ BẰNG TAY (DÀNH CHO NGÀY WEB CRAWLER BỊ KHÓA IP)**")
            with gr.Row():
                manual_date = gr.Textbox(label="Ngày (DD/MM/YYYY)", placeholder="Ví dụ: 01/08/2026")
                manual_numbers = gr.Textbox(label="27 GIẢI", placeholder="Ví dụ: 5 số / 4 số / 3 số / 2 số — đúng 27 giải")
            btn_manual_save = gr.Button("📥 LƯU DỮ LIỆU VÀO DATABASE", variant="primary")
            gr.Markdown("---")
            out_1 = gr.Textbox(label="Biên bản Báo cáo Hệ thống", lines=8)
            title_2 = gr.Markdown(f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt_init.strftime('%d/%m/%Y')}")
            
        with gr.Column(visible=False) as col_2:
            with gr.Row(): pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
            btn_2 = gr.Button("🔍 XUẤT LỆNH GIAO DỊCH CAO CẤP", variant="primary")
            out_2 = gr.Textbox(label="Hồ sơ Lệnh Tác Chiến", lines=25)
            btn_2.click(lambda pts: Auditor.phan_he_2_predict(pts), inputs=[pts_2], outputs=out_2)
            
        with gr.Column(visible=False) as col_3:
            gr.Markdown("### 🔍 MODULE KIỂM TOÁN CHUYÊN SÂU & TRUY VẾT")
            audit_type = gr.Radio(choices=["Kiểm toán 1 Ngày", "Kiểm toán Cả Tháng"], value="Kiểm toán 1 Ngày", label="Loại Kiểm toán")
            with gr.Column(visible=True) as row_audit_day: date_3 = gr.Textbox(label="Ngày Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            with gr.Column(visible=False) as row_audit_month: month_3 = gr.Textbox(label="Tháng Truy xuất (MM/YYYY)", value=latest_dt_init.strftime('%m/%Y') if latest_dt_init else "")
            pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_3 = gr.Button("📡 THỰC THI KIỂM TOÁN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Kiểm toán", lines=24)
            def toggle_audit(choice): return gr.Column(visible=(choice == "Kiểm toán 1 Ngày")), gr.Column(visible=(choice != "Kiểm toán 1 Ngày"))
            audit_type.change(fn=toggle_audit, inputs=audit_type, outputs=[row_audit_day, row_audit_month])
            btn_3.click(Auditor.phan_he_3_router, inputs=[audit_type, date_3, month_3, pts_3], outputs=out_3)

        with gr.Column(visible=False) as col_4:
            with gr.Row():
                t1_4 = gr.Textbox(label="Từ ngày", value=min_dt_init.strftime('%d/%m/%Y') if min_dt_init else "")
                t2_4 = gr.Textbox(label="Đến ngày", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Dòng Tiền", lines=22)
            btn_4.click(lambda t1, t2, pts: Auditor.phan_he_4_range(t1, t2, pts), inputs=[t1_4, t2_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            date_5 = gr.Textbox(label="Phiên Giao dịch", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_5 = gr.Button("💾 TRUY XUẤT KẾT QUẢ", variant="primary")
            out_5 = gr.Textbox(label="Bảng Kết Quả Loto", lines=15)
            btn_5.click(Auditor.phan_he_5_raw, inputs=date_5, outputs=out_5)

        with gr.Column(visible=False) as col_6:
            gr.Markdown("### 🤖 BỘ NÃO AI - QUÉT TOÀN BỘ LỊCH SỬ DB")
            btn_6 = gr.Button("🧬 BẮT ĐẦU QUÉT TOÀN DB", variant="primary")
            out_6 = gr.Textbox(label="Báo cáo Tổng hợp V5.8", lines=25)
            btn_6.click(Auditor.phan_he_6_master_diagnostic_prompt, inputs=[], outputs=out_6)

        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])
        btn_manual_save.click(Auditor.process_manual_input, inputs=[manual_date, manual_numbers], outputs=[out_1, title_2])

        def update_visibility(choice):
            return [gr.Column(visible=(choice == Config.MENU_OPTIONS[i])) for i in range(6)]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6])
    return demo

def _render_forensic_bootstrap():
    """
    Render-safe startup:
    - NEVER block the web server waiting for the first Frozen Manifest.
    - Build the manifest exactly once in a background thread when absent.
    - Ordinary restarts never rebuild an existing manifest.
    """
    if os.path.exists(Config.STATE_FILE):
        print("[FORENSIC BOOTSTRAP] Frozen Manifest already exists; startup rebuild skipped.")
        return

    print("[FORENSIC BOOTSTRAP] STATE_NOT_FOUND -> starting one-time background bootstrap...")
    try:
        db, msg = DatabaseManager.load_db()
        print(f"[FORENSIC BOOTSTRAP] {msg}")
        if not db:
            print("[FORENSIC BOOTSTRAP] BLOCKED: DATABASE_EMPTY")
            return

        result = QuantEngine.backtest_forensic(db)
        if isinstance(result, dict) and result.get("status") == "BLOCKED":
            print(f"[FORENSIC BOOTSTRAP] BLOCKED: {result.get('reason', 'UNKNOWN')}")
            return

        # backtest_forensic() is responsible for the authenticated,
        # append-only Frozen Manifest write.
        if os.path.exists(Config.STATE_FILE):
            print("[FORENSIC BOOTSTRAP] Frozen Manifest created successfully.")
        else:
            print("[FORENSIC BOOTSTRAP] HARD FAIL: backtest returned but STATE_FILE was not created.")
    except Exception as e:
        print(f"[FORENSIC BOOTSTRAP] HARD FAIL: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    # Explicit forensic rebuild remains a manual/destructive operation.
    # It is intentionally NOT part of normal Render startup.
    if '--rebuild-manifest' in sys.argv:
        db, msg = DatabaseManager.load_db()
        print(msg)
        if not db:
            raise SystemExit('REBUILD_BLOCKED: DATABASE_EMPTY')
        result = QuantEngine.backtest_forensic(db)
        print(json.dumps(result if isinstance(result, dict) else {'status':'OK'},
                         ensure_ascii=False, indent=2, default=str))
        raise SystemExit(0)

    # IMPORTANT:
    # The web server must bind its Render PORT before the potentially expensive
    # forensic bootstrap runs. Otherwise Render kills the service because no
    # listening socket is visible during the port-scan window.
    #
    # The daemon thread performs the one-time manifest creation in the
    # background. The UI/audit remains available while it is being built.
    bootstrap_thread = threading.Thread(
        target=_render_forensic_bootstrap,
        name="forensic-bootstrap",
        daemon=True,
    )
    bootstrap_thread.start()

    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    print(f"[RENDER] Starting Gradio on 0.0.0.0:{port}")
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
