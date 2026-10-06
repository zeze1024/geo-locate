---
name: geo-locate
description: 照片拍摄地点定位（看图找地点/网络迷踪/where was this taken）。视觉优先+工具验证：先看图直觉缩到3-5个候选城市/湖泊，再用山脊线匹配、卫星图、街景逐一核验。适合纯风景照、无EXIF、无路牌的"好看但没辨识度"的照片。Use when user shares a photo and asks 这是哪 / 在哪拍的 / 帮我定位 / 网络迷踪 / where was this taken.
---

# geo-locate（视觉优先版）

给一张照片，快速找到拍摄位置。**先看图猜，再工具验**，不要拿脚本硬啃全国。

## ★ 核心原则

| | 传统OSINT | 本版 geo-locate |
|---|---|---|
| 起点 | 跑全量采集脚本 | 先看图，模型直接给视觉判断 |
| 搜索范围 | 全国 → 逐级缩小 | 先视觉缩到 3-5 个候选 → 工具只验短名单 |
| 工具角色 | 决策依赖工具 | 工具只做验证，不做发现 |
| 失败时 | 继续跑更多脚本 | 停，问用户要提示 |
| 适合 | 有路牌/车牌/独特地标的照片 | 纯风景照、无文字、无独特地标 |

## 流程

### 第 0 步：快赢（30秒内）

```bash
uv run scripts/exif.py photo.jpg
```

- 有 GPS → 直接给坐标，跳到第 4 步用画面核对
- 无 GPS → 继续

### 第 1 步：视觉判断（你直接看图，不跑脚本）

**这是最关键的一步。** 直接看照片回答：

1. **气候带**：植被是常绿阔叶/落叶阔叶/针叶/荒漠？→ 华南/华中/华北/东北/西北/西南
2. **山形**：喀斯特尖峰？花岗岩圆丘？黄土高原？雪山？低矮丘陵？→ 缩小到特定地貌区
3. **水体**：海？大湖？水库？江？河？池塘？
4. **建筑密度**：一线天际线？郊区小区？县城？农村自建房？
5. **你的视觉记忆**：这画面让你想起哪个城市/湖泊？

**把以上写成 3-5 个候选地点**（地级市+具体湖泊/江边段），写下来。

> ⚠️ 这步不靠脚本，靠模型的视觉记忆。如果脑子里已经蹦出"这看着像杭州湘湖"，就直接写下来当候选。不要跳过这步直接跑脚本。

### 第 2 步：OCR 补刀（可选，1分钟）

```bash
uv run scripts/ocr.py photo.jpg
```

读出任何路牌/招牌/车牌 → 查表（`clues.py lookup`）缩范围，更新候选名单。

### 第 3 步：工具验证短名单

**只在第 1 步选出的 3-5 个候选上跑工具**，不要全国扫。

#### 3a. 山脊线匹配（有远山时）

```bash
# 提取照片山脊线
uv run scripts/terrain.py ridge photo.jpg --x0 100 --x1 1100 --step 15 --flat 0:400 --out ridge.json --png ridge_check.jpg

# 对每个候选点渲染山形，和照片山脊叠图比
uv run scripts/terrain.py view --at <候选lat,lon> --heading <朝向> --hfov <水平视角> --range 20000 --out cmp_<候选名>.jpg --photo photo.jpg
```

**人眼比叠图**：左边是照片山脊，右边是渲染山脊。轮廓对上的留，对不上的划掉。

#### 3b. 卫星图比对

```bash
# 拉候选湖/江段的卫星图
uv run scripts/tiles.py fetch <候选lat,lon> --zoom 16 --radius 2 --source esri --out sat_<候选名>.jpg
```

看卫星图：对岸有没有那排树？那簇楼在哪？水面宽度对不对？

#### 3c. 街景确认（最后一步）

```bash
uv run scripts/baidu_pano.py scan <候选lat,lon> --radius 500 --out panos_<候选名>.json
uv run scripts/match.py rank --query photo.jpg --panos panos_<候选名>.json --toward <远处地标lat,lon> --spread 20 --top 5 --out m_<候选名>.json --sheet m_<候选名>.jpg
```

打开前 5 张比：步道样式、护坡材质、对岸轮廓对不对。

### 第 4 步：输出

对了就给坐标（WGS84 + GCJ-02），带误差半径。

```bash
uv run scripts/geo.py convert --from wgs --to gcj <lat> <lon>
```

## ★ 硬停止规则

以下任一情况出现，**立刻停，问用户**，不要继续猜：

1. 第 1 步视觉判断给不出 3 个以上候选（画面太 generic）
2. 第 3 步山脊匹配 + 卫星图都对不上任何候选
3. 工具跑了 10 分钟还没收敛
4. 候选之间差太远（比如同时是杭州和昆明），没有进一步区分手段

**问用户时这样说**："我看到的是 [X特征]，猜了 [A/B/C] 几个地方都不太对，你给个省/市提示？"

## 不做什么

- ❌ 不做全国范围扫描
- ❌ 不在没有视觉候选时跑全流程候选管理
- ❌ 不跑重型全量采集（2分钟起步，纯风景照不需要）
- ❌ 不猜第二次还不对就换省瞎试
- ❌ 不编"大概在XX附近"的结论

## 脚本速查

| 脚本 | 什么时候用 |
|---|---|
| `exif.py` | 第 0 步，有没有 GPS |
| `ocr.py` | 第 2 步，有没有文字 |
| `terrain.py ridge/view` | 第 3a 步，远山轮廓匹配 |
| `tiles.py fetch` | 第 3b 步，拉卫星图看岸线 |
| `baidu_pano.py + match.py` | 第 3c 步，街景确认 |
| `geo.py convert` | 第 4 步，坐标转换 |
| `clues.py lookup` | 第 2 步，车牌/区号查表 |

## 运行

Python 3.10+，`uv run scripts/xxx.py`。坐标一律 (lat, lon)。
