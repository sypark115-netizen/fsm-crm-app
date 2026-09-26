import os, importlib
from builder import build
OUT = "out"
os.makedirs(OUT, exist_ok=True)
NAMES = {"sme": "중소기업_AI상품화아이디어100_V2.xlsx", "soho": "소상공인_AI상품화아이디어100_V2.xlsx", "sales": "영업사원_AI상품화아이디어100_V2.xlsx"}
for mod in ["data_sme", "data_soho", "data_sales"]:
    cfg = importlib.import_module(mod).CFG
    items = build(cfg, os.path.join(OUT, NAMES[cfg["key"]]))
    print(cfg["key"], "OK top3:", [it["name"] for it in items[:3]])
