# 🎬 批量视频合并 · 自动字幕 · BGM 混音

> 把一个文件夹里的零散片段按 1、2、3 的自然顺序拼成一条成片，顺手加上 Whisper 自动字幕和背景音乐闪避混音，双版本一次导出。

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Whisper](https://img.shields.io/badge/faster--whisper-local-brightgreen)](https://github.com/SYSTRAN/faster-whisper)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**中文** | [English](#-english)

---

## 解决什么痛点

拍完一条视频，素材是 `1.mp4`、`2.mp4`、`10.mp4` 这样散着的，剪辑软件里还得手动排序、逐条拖轨、加字幕、找 BGM——一条片子下来光拼装就半小时。

这个脚本面向"目录即工程"的工作流：**丢一个文件夹进去，出一条带字幕、带配乐的成片。**

## 核心能力

| 能力 | 说明 |
|---|---|
| **自然序排序** | `extract_numbers_key()` 按数字做自然排序，`1 < 2 < 10` 而不是字典序的 `1 < 10 < 2` |
| **自动跳过中间产物** | 忽略 `temp_*` / `merged_*` 前缀，重复运行不会把上次的成片又拼进去 |
| **本地 Whisper 字幕** | faster-whisper 生成 SRT，12 号 Calibri、紧凑快切、极限贴底（`MarginV=25`） |
| **BGM 智能混音** | 从 `music/` 目录随机选曲，支持"静音原声"和"原声+配乐"两种混音 |
| **画质预处理** | Lanczos 放大 + 细腻降噪 + 细节锐化 |
| **双版本同出** | 一次渲染同时导出【带字幕版】和【无字幕版】，各自适配不同平台 |
| **横竖屏切换** | 菜单里一键切 1080×1920 竖屏 / 1920×1080 横屏 |

## 菜单说明

```
1. 🚀 [双版齐发]  同时导出带字幕版 + 无字幕版（保留原声）
2. ⚡ [仅无字幕]  只输出原声无字幕版（跳过 AI 听写，最快）
3. 🔇 [静音配乐]  静音原声，从 music/ 选曲配乐并调音量
4. 🎶 [原声+配乐] 保留原声，配乐混音
5. 🔄 [切换画面]  竖屏 ⇄ 横屏
```

只想快速出片选 **2**；要发多平台选 **1**。

## 快速开始

```bash
git clone https://github.com/czh79/batch-video-merge.git
cd batch-video-merge
pip install -r requirements.txt
```

**准备目录**

```
你的素材目录/
├── merge.py
├── 1.mp4
├── 2.mp4
├── 10.mp4
└── music/          # 可选，放 mp3 即自动启用 BGM
    ├── bgm1.mp3
    └── bgm2.mp3
```

**运行**

```bash
python merge.py
```

默认扫描**当前目录**。要指定别的目录：

```bash
export VIDEO_INPUT_DIR="/path/to/footage"   # Windows: set VIDEO_INPUT_DIR=D:\footage
python merge.py
```

首次运行会自动下载 Whisper 模型（约 140MB）。想用本地已下好的模型：

```bash
export WHISPER_MODEL_EN="C:/models/faster-whisper-base.en"
```

## 配置项

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `VIDEO_INPUT_DIR` | 当前目录 | 素材目录 |
| `MUSIC_DIR` | `./music` | BGM 目录，不存在则跳过配乐 |
| `WHISPER_MODEL_EN` | `faster-whisper-base.en` | 本地模型路径或模型名 |

## 生效的字幕样式

```python
FontName   = Calibri
FontSize   = 12
MarginV    = 25      # 越贴底越不挡画面
渲染方式   = 烧录进视频（不依赖播放器字体）
```

要改字号/位置，改 `run_pipeline()` 里的 `force_style` 参数即可。

---

## 🇬🇧 English

> Merge a folder of numbered clips into one finished video, add Whisper-generated subtitles, and mix in background music — exporting subtitled and clean versions in a single run.

### What it does

- **Natural sort** — `1.mp4 < 2.mp4 < 10.mp4`, not lexicographic `1 < 10 < 2`.
- **Idempotent** — `temp_*` and `merged_*` artifacts are skipped, so re-running won't ingest its own output.
- **Local subtitles** — faster-whisper → SRT, burned in with a compact bottom-anchored style.
- **BGM mixing** — picks from `music/`, either muting the original audio or mixing on top of it.
- **Dual export** — subtitled and subtitle-free cuts from one render pass.
- **Orientation toggle** — 1080×1920 vertical / 1920×1080 horizontal from the menu.

### Usage

```bash
pip install -r requirements.txt
python merge.py                 # scans current directory
```

Extras: `VIDEO_INPUT_DIR`, `MUSIC_DIR`, `WHISPER_MODEL_EN`.

Requires FFmpeg / ffprobe on `PATH`.

---

<div align="center">

省下每次拼素材的半小时，**点个 Star** ⭐

</div>
