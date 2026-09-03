#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地反查地名：坐标 → 附近的POI/道路名。零出站请求。
数据源：data/pois.json（先跑 fetch_pois.py 下载你城市的公开地图）。
可选：data/amap.key 放一把高德「Web服务」key，可精确到店名门牌（见 README）。
用法：python3 placename.py <lat> <lon>；或被 where.py 调用。
"""
import os, json, math, sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pois.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(DATA) as f:
            raw = json.load(f)
        pois, roads = [], []
        for e in raw.get("elements", []):
            name = (e.get("tags") or {}).get("name")
            if not name:
                continue
            if e["type"] == "node":
                la, lo = e.get("lat"), e.get("lon")
            else:
                c = e.get("center") or {}
                la, lo = c.get("lat"), c.get("lon")
            if la is None:
                continue
            if (e.get("tags") or {}).get("highway"):
                roads.append((name, la, lo))
            else:
                pois.append((name, la, lo))
        _cache = (pois, roads)
    return _cache


def _dist(lat1, lon1, lat2, lon2):
    """米。小范围内用等距圆柱近似足够。"""
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 110540
    return math.hypot(dx, dy)


def nearby(lat, lon, k=3):
    """返回 (POI名, 距离米) 列表 + 最近道路名。数据没覆盖时返回 ([], None)。"""
    try:
        pois, roads = _load()
    except Exception:
        return [], None
    ps = sorted(((n, _dist(lat, lon, la, lo)) for n, la, lo in pois), key=lambda x: x[1])[:k]
    rd = min(((n, _dist(lat, lon, la, lo)) for n, la, lo in roads), key=lambda x: x[1], default=None)
    ps = [(n, d) for n, d in ps if d < 2000]
    road = rd[0] if rd and rd[1] < 1000 else None
    return ps, road


AMAP_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "amap.key")


def _wgs2gcj(lat, lon):
    """WGS-84(GPS原始) → GCJ-02(高德用的国测局坐标)。不转会偏几百米。"""
    if not (72.004 < lon < 137.8347 and 0.8293 < lat < 55.8271):
        return lat, lon  # 中国境外不偏移
    a, ee = 6378245.0, 0.00669342162296594323
    x, y = lon - 105.0, lat - 35.0

    def tlat(x, y):
        r = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
        r += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
        r += (20.0*math.sin(y*math.pi) + 40.0*math.sin(y/3.0*math.pi)) * 2.0/3.0
        r += (160.0*math.sin(y/12.0*math.pi) + 320*math.sin(y*math.pi/30.0)) * 2.0/3.0
        return r

    def tlon(x, y):
        r = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
        r += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
        r += (20.0*math.sin(x*math.pi) + 40.0*math.sin(x/3.0*math.pi)) * 2.0/3.0
        r += (150.0*math.sin(x/12.0*math.pi) + 300.0*math.sin(x/30.0*math.pi)) * 2.0/3.0
        return r

    dlat, dlon = tlat(x, y), tlon(x, y)
    rad = lat / 180.0 * math.pi
    magic = 1 - ee * math.sin(rad) ** 2
    sq = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sq) * math.pi)
    dlon = (dlon * 180.0) / (a / sq * math.cos(rad) * math.pi)
    return lat + dlat, lon + dlon


def amap_regeo(lat, lon):
    """高德逆地理编码补刀。强制直连（绕过一切代理，风控红线）。失败返回 None。"""
    try:
        with open(AMAP_KEY_FILE) as f:
            key = f.read().strip()
    except Exception:
        return None
    if not key:
        return None
    try:
        import urllib.request
        glat, glon = _wgs2gcj(lat, lon)
        url = (f"https://restapi.amap.com/v3/geocode/regeo?key={key}"
               f"&location={glon:.6f},{glat:.6f}&extensions=all&radius=300")
        # ProxyHandler({}) = 无视环境变量里的代理，永远家宽直连
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=8) as r:
            d = json.loads(r.read().decode())
        rg = d.get("regeocode") or {}
        addr = rg.get("formatted_address") or ""
        pois = rg.get("pois") or []
        best = None
        if pois:
            p = min(pois, key=lambda p: float(p.get("distance") or 9999))
            if float(p.get("distance") or 9999) < 300:
                best = f"{p.get('name')}({int(float(p['distance']))}米)"
        out = []
        if best:
            out.append(best)
        if addr and isinstance(addr, str):
            out.append(addr)
        return " · ".join(out) if out else None
    except Exception:
        return None


def describe(lat, lon):
    bits = []
    precise = amap_regeo(lat, lon)
    if precise:
        bits.append(precise)
    ps, road = nearby(lat, lon)
    if not precise:  # 高德没答上来才用本地粗地名兜底
        if ps:
            bits.append("、".join(f"{n}({int(d)}米)" for n, d in ps))
        if road:
            bits.append(f"{road}一带")
    return " · ".join(bits) if bits else None


if __name__ == "__main__":
    la, lo = float(sys.argv[1]), float(sys.argv[2])
    print(describe(la, lo) or "地图数据没覆盖这里")
