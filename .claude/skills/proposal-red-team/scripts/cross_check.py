#!/usr/bin/env python3
"""Deterministic cross-unit consistency candidates (no LLM).

Usage:
    python3 cross_check.py <workdir> [--customer "OO은행"] [--alias "OO,OO뱅크"] [--anchors extra1,extra2]

Writes <workdir>/cross_check.json and cross_check.md with CANDIDATES only:
  1. number_conflicts  same anchor (투입인력, 사업기간, RTO ...) + unit with different values
  2. other_customers   names of other financial institutions (copy-paste from past proposals?)
  3. customer_variants spelling variants of the customer name
  4. term_variants     the same term written differently (GenAI / Gen AI, DR센터 / DR 센터)
  5. duplicate_gm      identical Governing Messages on different slides
  6. kt_naming         KT / kt / 케이티 / KT Cloud 표기 혼용

The model decides which candidates are real issues — e.g. 단계별 42명 vs 전체 45명 is not a conflict.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ANCHORS = [
    "투입인력", "투입 인력", "총 인력", "상주인력", "전담인력", "인력", "PM", "PL", "M/M", "MM",
    "사업기간", "수행기간", "사업 기간", "구축기간", "기간", "착수", "완료", "종료", "오픈", "개통", "전환", "이관", "Cutover",
    "사업비", "사업금액", "총액", "제안금액", "비용", "절감",
    "가용성", "SLA", "RTO", "RPO", "응답시간", "TPS", "처리량", "장애",
    "서버", "VM", "랙", "Rack", "회선", "대역폭", "스토리지", "GPU", "데이터센터", "센터",
    "고객", "레퍼런스", "구축사례", "사례", "실적", "전문인력", "인증",
]

NUM = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
UNITS = [
    ("억원", r"억\s?원|억"), ("만원", r"만\s?원"), ("원", r"원"),
    ("%", r"%|퍼센트"), ("명", r"명|인"), ("MM", r"M/M|MM|인월"),
    ("개월", r"개월"), ("주", r"주(?!요|관|간|식)"), ("일", r"일(?!정|부|반|괄|원|환|관|체)"),
    ("년", r"년(?!도)"), ("분", r"분(?!석|야|산|리)"), ("시간", r"시간"), ("초", r"초(?!기|과)"),
    ("대", r"대(?!상|응|비|형|규모|표|학|한|외)"), ("개", r"개(?!선|발|요|별|월|념|편|방|최)"), ("식", r"식(?!별)"),
    ("건", r"건"), ("곳", r"곳"), ("TB", r"TB|PB|GB"), ("Gbps", r"Gbps|Mbps|G"), ("kW", r"kW|MW"), ("ms", r"ms"),
]
NUM_RE = re.compile(NUM + r"\s?(" + "|".join(f"(?:{p})" for _, p in UNITS) + r")")
DATE_RE = re.compile(r"(20\d{2})\s?[.\-/년]\s?(\d{1,2})(?:\s?[.\-/월]\s?(\d{1,2}))?")

FIN = [
    "KB국민은행", "국민은행", "신한은행", "하나은행", "우리은행", "NH농협은행", "농협은행", "IBK기업은행", "기업은행",
    "카카오뱅크", "케이뱅크", "토스뱅크", "SC제일은행", "씨티은행", "수협은행", "산업은행", "KDB산업은행", "수출입은행",
    "부산은행", "BNK부산은행", "경남은행", "iM뱅크", "대구은행", "광주은행", "전북은행", "제주은행",
    "KB금융", "신한금융", "하나금융", "우리금융", "NH농협금융", "BNK금융", "DGB금융", "JB금융",
    "삼성생명", "한화생명", "교보생명", "신한라이프", "NH농협생명", "미래에셋생명", "동양생명", "흥국생명", "KB라이프", "라이나생명", "메트라이프",
    "삼성화재", "현대해상", "DB손해보험", "DB손보", "KB손해보험", "KB손보", "메리츠화재", "한화손해보험", "롯데손해보험", "흥국화재", "NH농협손해보험",
    "미래에셋증권", "한국투자증권", "NH투자증권", "삼성증권", "KB증권", "신한투자증권", "키움증권", "하나증권", "대신증권", "메리츠증권", "토스증권",
    "신한카드", "삼성카드", "현대카드", "KB국민카드", "국민카드", "롯데카드", "우리카드", "하나카드", "BC카드", "비씨카드", "NH농협카드",
    "현대캐피탈", "KB캐피탈", "신한캐피탈", "하나캐피탈", "롯데캐피탈", "우리금융캐피탈", "BNK캐피탈", "JB우리캐피탈",
    "SBI저축은행", "OK저축은행", "웰컴저축은행", "페퍼저축은행",
    "금융결제원", "코스콤", "한국거래소", "예탁결제원", "한국예탁결제원", "금융보안원", "신용보증기금", "기술보증기금",
    "예금보험공사", "주택금융공사", "한국주택금융공사", "서민금융진흥원", "우체국", "우정사업본부", "새마을금고", "신협",
]


JOSA = {"으로", "에서", "에게", "까지", "부터", "보다", "처럼", "이다", "이며", "입니다", "합니다", "하고", "하여", "으로서",
        "으로써", "에는", "에도", "과의", "와의", "이라", "라는", "이라는", "에서의", "으로의", "등을", "등의", "등과", "하는", "되는"}


def unit_texts(units):
    for u in units:
        parts = [u.get("gm") or ""]
        parts += [b.get("text", "") for b in u.get("blocks", [])]
        for t in u.get("tables", []):
            parts += [" | ".join(r) for r in t]
        for c in u.get("charts", []):
            parts.append(json.dumps(c, ensure_ascii=False))
        parts.append(u.get("notes") or "")
        yield u["uid"], "\n".join(p for p in parts if p)


def norm_unit(raw: str) -> str:
    for name, pat in UNITS:
        if re.fullmatch(pat, raw):
            return name
    return raw


def number_conflicts(texts, anchors):
    facts = defaultdict(lambda: defaultdict(list))  # key -> value -> [uid, ctx]
    for uid, txt in texts:
        for line in txt.splitlines():
            for m in NUM_RE.finditer(line):
                val = m.group(1).replace(",", "")
                unit = norm_unit(m.group(2))
                before = line[max(0, m.start() - 18):m.start()]
                # an anchor only owns the first number after it: "투입인력 45명 (이전 22명" -> 22 is not 투입인력
                prev_num = list(re.finditer(r"\d", before))
                if prev_num:
                    before = before[prev_num[-1].end():]
                hits = [a for a in anchors if a.lower() in before.lower()]
                if not hits:
                    continue
                anchor = max(hits, key=len)  # most specific
                key = f"{anchor}|{unit}"
                ctx = line[max(0, m.start() - 30):m.end() + 15].strip()
                facts[key][val].append({"uid": uid, "context": ctx})
    out = []
    for key, vals in facts.items():
        if len(vals) > 1:
            anchor, unit = key.split("|")
            out.append({"anchor": anchor, "unit": unit,
                        "values": {v: locs[:6] for v, locs in vals.items()},
                        "n_values": len(vals)})
    out.sort(key=lambda x: (-x["n_values"], x["anchor"]))
    return out


def date_facts(texts):
    dates = defaultdict(list)
    for uid, txt in texts:
        for line in txt.splitlines():
            for m in DATE_RE.finditer(line):
                y, mo = m.group(1), int(m.group(2))
                if not 1 <= mo <= 12:
                    continue
                before = line[max(0, m.start() - 15):m.start()]
                hit = [a for a in ("착수", "완료", "종료", "오픈", "개통", "전환", "이관", "Cutover", "가동", "구축") if a in before]
                if hit:
                    dates[hit[-1]].append({"date": f"{y}.{mo:02d}", "uid": uid, "context": line[max(0, m.start()-25):m.end()+10].strip()})
    out = []
    for k, items in dates.items():
        if len({i["date"] for i in items}) > 1:
            out.append({"anchor": k, "occurrences": items[:12]})
    return out


def other_customers(texts, customer, aliases):
    own = {customer.replace(" ", "")} | {a.replace(" ", "") for a in aliases if a}
    found = defaultdict(list)
    for uid, txt in texts:
        flat = txt.replace(" ", "")
        for name in FIN:
            if name in flat and not any(name in o or o in name for o in own if o):
                i = flat.find(name)
                found[name].append({"uid": uid, "context": flat[max(0, i - 25):i + len(name) + 25]})
    # collapse names contained in longer found names (국민은행 inside KB국민은행)
    names = sorted(found, key=len, reverse=True)
    keep = {}
    for n in names:
        if not any(n != k and n in k and {x["uid"] for x in found[n]} <= {x["uid"] for x in found[k]} for k in keep):
            keep[n] = found[n][:10]
    return [{"name": k, "count": len(found[k]), "occurrences": v} for k, v in keep.items()]


def customer_variants(texts, customer):
    if not customer:
        return []
    core = re.escape(customer.replace(" ", ""))
    pat = re.compile(r"\s?".join(core))
    forms = defaultdict(list)
    for uid, txt in texts:
        for m in pat.finditer(txt):
            if "\n" in m.group(0):
                continue  # line wrap, not a spelling variant
            forms[m.group(0)].append(uid)
    return [{"form": f, "count": len(u), "uids": sorted(set(u))[:10]} for f, u in forms.items()] if len(forms) > 1 else []


def term_variants(texts):
    latin = defaultdict(lambda: defaultdict(set))
    ko_tokens = defaultdict(set)
    ko_bigrams = defaultdict(set)
    for uid, txt in texts:
        for m in re.finditer(r"[A-Za-z][A-Za-z0-9]*(?:[ \-][A-Za-z0-9]+){0,2}", txt):
            surf = m.group(0)
            if len(surf) < 3:
                continue
            key = re.sub(r"[ \-]", "", surf).lower()
            latin[key][surf].add(uid)
        toks = re.findall(r"[가-힣A-Za-z0-9]+", txt)
        for t in toks:
            ko_tokens[t].add(uid)
        for a, b in zip(toks, toks[1:]):
            if re.match(r"^[가-힣A-Za-z]{2,}$", a) and re.match(r"^[가-힣]{2,}$", b) and b not in JOSA:
                ko_bigrams[(a, b)].add(uid)
    out = []
    for key, forms in latin.items():
        if len(forms) > 1 and len(key) >= 3:
            # ignore pure prefix overlaps (e.g., "Cloud" vs "Cloud Native")
            out.append({"term": key, "forms": {f: sorted(u)[:6] for f, u in forms.items()}})
    for (a, b), uids in ko_bigrams.items():
        joined = a + b
        if joined in ko_tokens and len(joined) <= 12:
            out.append({"term": joined, "forms": {f"{a} {b}": sorted(uids)[:6], joined: sorted(ko_tokens[joined])[:6]}})
    return out[:80]


def duplicate_gm(units):
    seen = defaultdict(list)
    for u in units:
        g = (u.get("gm") or "").strip()
        if len(g) >= 8:
            seen[re.sub(r"\s+", " ", g)].append(u["uid"])
    return [{"gm": g, "uids": v} for g, v in seen.items() if len(v) > 1]


def kt_naming(texts):
    forms = defaultdict(set)
    for uid, txt in texts:
        for m in re.finditer(r"(?<![A-Za-z])(KT|kt|Kt|케이티)(?:\s?(?:클라우드|cloud|Cloud|DS|ds|엠하우스|IDC|AI))?(?![A-Za-z])", txt):
            forms[m.group(0)].add(uid)
    return {f: len(u) for f, u in forms.items()} if len(forms) > 1 else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--customer", default="")
    ap.add_argument("--alias", default="", help="comma separated other names of the customer")
    ap.add_argument("--anchors", default="", help="extra comma separated anchor words")
    ap.add_argument("--files", help="limit to file ids, e.g. F1,F2")
    args = ap.parse_args()

    wd = Path(args.workdir).resolve()
    units = json.loads((wd / "docmodel.json").read_text(encoding="utf-8"))["units"]
    if args.files:
        keep = set(args.files.split(","))
        units = [u for u in units if u["file_id"] in keep]
    texts = list(unit_texts(units))
    anchors = ANCHORS + [a for a in args.anchors.split(",") if a]
    res = {
        "customer": args.customer,
        "number_conflicts": number_conflicts(texts, anchors),
        "date_conflicts": date_facts(texts),
        "other_customers": other_customers(texts, args.customer, args.alias.split(",")),
        "customer_variants": customer_variants(texts, args.customer),
        "term_variants": term_variants(texts),
        "duplicate_gm": duplicate_gm(units),
        "kt_naming": kt_naming(texts),
    }
    (wd / "cross_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# Cross-check candidates (판정 전 후보 — 맥락 확인 필요)\n"]
    md.append(f"## 1. 숫자 불일치 후보 ({len(res['number_conflicts'])})")
    for c in res["number_conflicts"]:
        md.append(f"- **{c['anchor']} ({c['unit']})**: " + "; ".join(
            f"`{v}` @ {', '.join(l['uid'] for l in locs)} — “{locs[0]['context']}”" for v, locs in c["values"].items()))
    md.append(f"\n## 2. 일정 불일치 후보 ({len(res['date_conflicts'])})")
    for c in res["date_conflicts"]:
        md.append(f"- **{c['anchor']}**: " + "; ".join(f"`{o['date']}` @ {o['uid']}" for o in c["occurrences"]))
    md.append(f"\n## 3. 다른 금융사명 등장 ({len(res['other_customers'])}) — Reference 장표가 아니라면 복사·붙여넣기 오류 의심")
    for c in res["other_customers"]:
        md.append(f"- **{c['name']}** ×{c['count']}: " + "; ".join(f"{o['uid']} “{o['context']}”" for o in c["occurrences"][:4]))
    md.append(f"\n## 4. 고객명 표기 변형 ({len(res['customer_variants'])})")
    for c in res["customer_variants"]:
        md.append(f"- `{c['form']}` ×{c['count']} @ {', '.join(c['uids'])}")
    md.append(f"\n## 5. 용어 표기 변형 ({len(res['term_variants'])})")
    for c in res["term_variants"][:40]:
        md.append("- " + " / ".join(f"`{f}`({len(u)})" for f, u in c["forms"].items()))
    md.append(f"\n## 6. 중복 GM ({len(res['duplicate_gm'])})")
    for c in res["duplicate_gm"]:
        md.append(f"- “{c['gm']}” @ {', '.join(c['uids'])}")
    if res["kt_naming"]:
        md.append("\n## 7. KT 표기 혼용\n- " + ", ".join(f"`{k}`×{v}" for k, v in res["kt_naming"].items()))
    (wd / "cross_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in res.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
