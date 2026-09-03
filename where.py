#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读最新位置（人话版）：只读本地 latest.json，零出站请求。
用法：python3 where.py
"""
import os, json, time

LATEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "latest.json")


def main():
    if not os.path.exists(LATEST):
        print("还没收到任何定位点。手机 App 上报后再看。")
        return
    with open(LATEST) as f:
        r = json.load(f)
    lat, lon = r.get("lat"), r.get("lon")
    tst = int(r.get("tst", r.get("_recv", time.time())))
    age = int(time.time()) - tst
    print("📍 最新定位")
    print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tst))}（{age//60} 分 {age%60} 秒前）")
    print(f"   坐标：{lat}, {lon}")
    if "acc" in r:
        print(f"   精度：±{r['acc']} 米")
    if "batt" in r:
        print(f"   手机电量：{r['batt']}%")
    if "vel" in r:
        print(f"   速度：{r['vel']} km/h")
    try:
        from placename import describe
        desc = describe(float(lat), float(lon))
        if desc:
            print(f"   附近：{desc}")
    except Exception:
        pass
    print(f"   高德看地名：https://uri.amap.com/marker?position={lon},{lat}")
    print(f"   谷歌看地名：https://maps.google.com/?q={lat},{lon}")


if __name__ == "__main__":
    main()
