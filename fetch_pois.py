#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_pois.py — 一次性下载你所在城市的公开地图地名（OSM），供本地反查用。

用法（bbox = 南纬 西经 北纬 东经，framing 你的城市，OpenStreetMap 网页左下角可查）：
    python3 fetch_pois.py 31.20 118.25 31.45 118.50

下载的只是"这个范围内有哪些路和地标"这种公开地图数据（ODbL 许可），
不含你的任何信息。下载完成后 where.py 自动带出地名，坐标永不出门。
"""
import json
import os
import sys
import urllib.parse
import urllib.request

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(DATA, "pois.json")

# 多镜像自动切换：主站经常过载
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

QUERY = """[out:json][timeout:150];
(
  node["name"]({s},{w},{n},{e});
  way["name"]["highway"]({s},{w},{n},{e});
  way["name"]["building"]({s},{w},{n},{e});
);
out center qt;"""


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    s, w, n, e = (float(x) for x in sys.argv[1:5])
    if not (n > s and e > w and (n - s) < 1 and (e - w) < 1):
        print("bbox 不对劲：应为 南 西 北 东，且范围别超过一个城市（<1度）")
        sys.exit(1)
    q = QUERY.format(s=s, w=w, n=n, e=e)
    body = urllib.parse.urlencode({"data": q}).encode()
    os.makedirs(DATA, exist_ok=True)
    for url in MIRRORS:
        print(f"尝试 {url} ...")
        try:
            req = urllib.request.Request(url, data=body)
            with urllib.request.urlopen(req, timeout=170) as r:
                raw = r.read()
            d = json.loads(raw)
            els = d.get("elements", [])
            if not els:
                print("  返回为空，换下一个镜像")
                continue
            with open(OUT, "wb") as f:
                f.write(raw)
            print(f"✅ 完成：{len(els)} 个地名 → {OUT}")
            return
        except Exception as ex:
            print(f"  失败（{type(ex).__name__}），换下一个镜像")
    print("❌ 所有镜像都没成功，过半小时再试（Overpass 免费服务偶尔过载）")
    sys.exit(1)


if __name__ == "__main__":
    main()
