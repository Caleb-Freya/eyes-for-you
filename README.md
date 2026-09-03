# 一双看见你的眼睛 · eyes-for-you

*[English version → README.en.md](README.en.md)*

自托管定位后端（OwnTracks 兼容）。手机把你的位置上报到**你自己的**服务器——不经过任何第三方公司，数据只在你自己的机器里躺着。

给你的 AI（或你自己）一双随时能看见对方在哪的眼睛。

> 为什么造它：市面上的位置共享都要把你的行踪交给别人的云。这个不用——一个 Python 文件、零依赖、只存本地。搭完以后，你的 AI 伴侣/助手读一个本地文件就知道你在哪，一个出站请求都不用发。

## 适用范围（先看这个）

| 你的情况 | 能不能用 |
|---|---|
| iPhone | ✅ OwnTracks 有 iOS 版（App Store） |
| 安卓 | ✅ 有安卓版：Google Play 可装；**没谷歌框架**的国产手机，去 [F-Droid](https://f-droid.org/packages/org.owntracks.android/) 或 [GitHub Releases](https://github.com/owntracks/android/releases) 下 APK 直接装 |
| AI 是 Claude | ✅ 读本地文件 `python3 where.py` 即可 |
| AI 是 GPT / 其他 | ✅ 不挑 AI——能联网的直接 `GET /latest?token=钥匙` 拿 JSON；自定义 GPT 配个 Action 指向这个网址；都没有就把 `where.py` 的输出贴给它 |
| 只有 API 中转站、**没有自己的服务器** | ⚠️ 用不了。这套的前提是有一台自己的机器（VPS 小鸡 / 小主机 / 树莓派，几十块的都够）——它的全部意义就是"位置只落自己手里"，没有自己的机器就没有"自己的手"。不建议找人代托管：行踪会躺在别人机器上 |

## 特性

- **零第三方**：位置只写本地文件（`data/latest.json` + `data/history.jsonl`），后端不向外发任何请求
- **零依赖**：只用 Python 标准库，能跑 Python 3 的机器都行（VPS / 小主机 / 树莓派）
- **只绑 127.0.0.1**：公网入口交给隧道/反代，一层 HTTPS 一层钥匙
- **鉴权双通道**：URL `?token=` 或 Basic-Auth 密码，任一命中即放行（常量时间比较，防时序攻击）
- **OwnTracks 兼容**：手机端用开源的 [OwnTracks](https://owntracks.org/)（iOS/Android），后台自动上报，省电模式是苹果官方认可的方式
- **本地地名反查**：坐标 → "XX路一带、XX大厦(120米)" 在**你自己的机器上**完成——下载一次你城市的公开地图（OSM），以后查地名坐标也不出门；可选接高德 key 精确到店名门牌

## 架构

```
📱 手机 OwnTracks ──HTTPS──▶ 🔒 隧道/反代 ──▶ 🗄️ server.py (127.0.0.1:8098) ──▶ 👁️ 你 / 你的AI 读本地
```

## 快速开始（约 20 分钟）

### 1. 后端（约 10 分钟）

```bash
git clone https://github.com/45694354xm/eyes-for-you.git ~/geo-track
cd ~/geo-track
bash start.sh

# 首次启动自动生成钥匙，记下它（填手机要用）：
cat data/token.txt
```

### 2. 公网入口（约 5 分钟）

后端只绑本机，需要一个带 HTTPS 的入口。两条路挑一条：

**A · Cloudflare Tunnel（最省事）**：Zero Trust → Tunnels → Public Hostname 加一条：
- 子域名 `track`，Service 类型选 **HTTP**（不是 HTTPS，否则 502），地址 `127.0.0.1:8098`

**B · 有公网 IP**：Caddy 两行反代自动 HTTPS：
```
track.你的域名.com { reverse_proxy 127.0.0.1:8098 }
```

验证：手机浏览器打开 `https://track.你的域名.com/health`，看到 `{"ok":true}` 就通了。

### 3. 手机（关键一步，含 3 个坑）

装 [OwnTracks](https://owntracks.org/)（免费开源），进设置：

| 项 | 填什么 |
|---|---|
| 模式 Mode | **HTTP**（不是 MQTT） |
| URL | `https://track.你的域名.com/pub?token=你的钥匙` |
| 用户 ID | 随便（如 `me`） |

**⚠️ 三个坑（我们替你踩过了）：**

1. **「密钥」栏必须留空** —— 那一栏不是密码，是端到端加密的钥匙。填了值，定位会被加密成 `_type:encrypted` 发出去，服务器解不开。鉴权交给 URL 的 `?token=` 就够了。
2. **鉴权走 URL，别跟 Basic-Auth 较劲** —— 「认证/密码」开关开关着都行，URL 带 `?token=` 后端就放行。
3. **别停在「手动」模式** —— 地图页顶上那排 `安静/手动/重要/移动` 里，停在「手动」= 永不自动上报。点 **「移动」(Move)** 才会定时发（对应专家模式 `monitoring=2`、`locatorInterval=300` 秒、`locatorDisplacement=100` 米）。左侧蓝箭头只是"回到我的位置"，右上角方块是系统分享，都不发位置。

填完去地图页点「移动」，或走两步，第一个点就进来了。

### 4. 读出「TA 在哪」

```bash
python3 where.py
```

```
📍 最新定位
   时间：2026-09-03 12:23:05（0 分 43 秒前）
   坐标：39.9087, 116.3975
   精度：±8 米
   手机电量：50%
   附近：天安门广场(120米) · 北京市东城区东长安街天安门广场
   地图：https://maps.google.com/?q=39.9087,116.3975
```

想让 AI 主动读：把 `python3 where.py` 的输出喂给它，或 `GET /latest?token=你的钥匙` 拿 JSON。

## 地名反查（推荐装上，5 分钟）

光有经纬度像看天书。两层方案，按需取用：

**第一层 · 本地地图（免费，零泄露，必装）**

下载一次你所在城市的公开地图地名（OpenStreetMap，ODbL 许可），以后反查全在本地：

```bash
# 参数是城市范围 bbox：南纬 西经 北纬 东经（openstreetmap.org 网页「导出」页可查）
python3 fetch_pois.py 39.80 116.20 40.05 116.60
```

下载的只是"这个城市有哪些路和地标"，**不含你的任何信息**；查询时坐标只跟本地文件比对。脚本内置三个镜像自动切换（Overpass 主站经常过载）。效果：能报出街道、地标、大建筑；小店铺不一定全（OSM 在国内数据偏瘦）。

**第二层 · 高德补刀（可选，精确到店名门牌）**

想要"XX奶茶店(30米)"级别的精度，去 [lbs.amap.com](https://lbs.amap.com) 免费注册开发者，创建应用 → 添加 Key → 服务平台选 **「Web服务」**（选错用不了），IP 白名单**留空**（家宽 IP 是动态的，填了会莫名失效）。然后：

```bash
echo "你的key" > data/amap.key && chmod 600 data/amap.key
```

`where.py` 会自动带上精确地名。注意代价：**高德会看到被查询的坐标**（来自你服务器 IP 的零星点，不是完整轨迹）。介意就只用第一层。技术细节：代码已处理 WGS-84→GCJ-02 坐标系转换（不处理会偏几百米），并强制直连不走任何代理。

## API

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| POST | `/pub` | ✅ | OwnTracks 上报入口，返回 `[]` |
| GET | `/latest` | ✅ | 最新一个定位点（JSON） |
| GET | `/health` | — | 健康检查 `{"ok":true}` |

## 安全须知（不是可选项）

- **钥匙就是命门**：token 别发群里、别进公开仓库、别留在截图里。泄了就换——删掉 `data/token.txt` 重启即重新生成
- **永远别让后端裸奔公网**：只绑 127.0.0.1，对外只经隧道 + token
- **`data/` 目录就是行踪本身**：注意文件权限，别把它同步进任何公开仓库
- 省电是设计不是缺陷：Move 模式静止不发、移动才发（默认 5 分钟 / 100 米）

## License

MIT

---

*made with 📍 by Caleb · for Freya，也给每一个想被自己的宝宝看见的你*
