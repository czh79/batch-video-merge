import json
import os
import re
import subprocess
import sys
from pathlib import Path

# 本地 Whisper 模型目录
# 全部路径可通过环境变量覆盖，默认值适配“当前目录即素材目录”的用法
LOCAL_MODEL_PATH = os.environ.get("WHISPER_MODEL_EN", "faster-whisper-base.en")
MUSIC_DIR = os.environ.get("MUSIC_DIR", str(Path.cwd() / "music"))


def extract_numbers_key(filepath: Path):
    """自然数字排序：1.mp4 < 2.mp4 < 10.mp4"""
    stem = filepath.stem
    parts = re.split(r"(\d+)", stem)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def scan_and_sort_videos(input_dir: str):
    dir_path = Path(input_dir)
    if not dir_path.exists():
        print(f"❌ 目录不存在: {input_dir}")
        return None

    video_extensions = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".m4v"}
    video_files = [
        f
        for f in dir_path.iterdir()
        if f.is_file()
        and f.suffix.lower() in video_extensions
        and not f.name.startswith("temp_")
        and not f.name.startswith("merged_")
    ]

    if not video_files:
        print(f"⚠️ 目录 {input_dir} 下未找到任何素材视频！")
        return None

    video_files.sort(key=extract_numbers_key)
    return video_files


def scan_music_files(music_dir: str):
    """扫描音乐目录下的音频文件"""
    m_path = Path(music_dir)
    if not m_path.exists():
        m_path.mkdir(parents=True, exist_ok=True)
        print(f"⚠️ 目录 {music_dir} 不存在，已为你自动创建。请放入音频文件后重试！")
        return []

    audio_extensions = {".mp3", ".wav", ".aac", ".flflac", ".flac", ".m4a", ".ogg"}
    music_files = [
        f for f in m_path.iterdir()
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]
    return sorted(music_files, key=lambda x: x.name.lower())


def format_timestamp_srt(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def transcribe_english_audio(video_path: Path, output_srt_path: Path):
    """提取英文台词并输出标准 SRT 字幕（精确保留短促时长）"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("\n❌ 未检测到 faster-whisper 库！请运行: pip install faster-whisper")
        return False

    model_source = LOCAL_MODEL_PATH if os.path.exists(LOCAL_MODEL_PATH) else "base.en"
    try:
        model = WhisperModel(model_source, device="cpu", compute_type="int8")
    except Exception as e:
        print(f"❌ Whisper 模型加载失败: {e}")
        return False

    print("🎙️ 正在智能识别英文台词 (已开启单词级紧凑时间轴)...")
    try:
        segments, info = model.transcribe(
            str(video_path.resolve()),
            language="en",
            beam_size=5,
            vad_filter=False,
            word_timestamps=True,
        )
    except Exception as e:
        print(f"❌ 语音转录出错: {e}")
        return False

    srt_lines = []
    seg_count = 0
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue

        start_time = seg.start
        end_time = seg.end

        # 取最后一个单词念完的时间 + 0.15 秒缓冲，说完即隐
        if seg.words and len(seg.words) > 0:
            last_word_end = seg.words[-1].end
            end_time = min(end_time, last_word_end + 0.15)

        # 限制每句字幕最长展示不超过 1.8 秒
        if end_time - start_time > 1.8:
            end_time = start_time + 1.8

        seg_count += 1
        start_t = format_timestamp_srt(start_time)
        end_t = format_timestamp_srt(end_time)
        srt_lines.append(f"{seg_count}\n{start_t} --> {end_t}\n{text}\n\n")

    if seg_count == 0:
        print("⚠️ 未在视频中捕获到有效英文对话。")
        return False

    output_srt_path.write_text("".join(srt_lines), encoding="utf-8")
    print(f"✅ 成功捕获 {seg_count} 句英文台词 (时长已紧凑对齐)！")
    return True


def select_bgm_and_volume():
    """交互选择背景音乐及音量"""
    music_files = scan_music_files(MUSIC_DIR)
    if not music_files:
        print(f"❌ {MUSIC_DIR} 目录下没有找到任何音频文件（支持 .mp3, .wav, .aac, .m4a 等）！")
        return None, None

    print("\n" + "=" * 55)
    print(f"🎵 发现 {len(music_files)} 首背景音乐，请选择编号：")
    for idx, f in enumerate(music_files, 1):
        print(f"  [{idx}] -> {f.name}")
    print("=" * 55)

    while True:
        m_choice = input(f"请输入音乐编号 (1-{len(music_files)}): ").strip()
        if m_choice.isdigit() and 1 <= int(m_choice) <= len(music_files):
            selected_music = music_files[int(m_choice) - 1]
            break
        print(f"⚠️ 输入无效，请输入 1~{len(music_files)} 之间的数字。")

    print("\n请选择背景音乐音量档位：")
    print("  [1] 🔉 12% (微弱环境感，自媒体短视频推荐) [默认]")
    print("  [2] 🔊 30% (适中配乐)")
    print("  [3] 📢 45% (较强配乐)")
    vol_choice = input("请选择档位 (1/2/3，直接回车默认选 1): ").strip()

    vol_map = {
        "1": 0.12,
        "2": 0.30,
        "3": 0.45,
        "": 0.12,  # 回车默认 12%
    }
    selected_volume = vol_map.get(vol_choice, 0.12)
    print(f"✅ 已选择: {selected_music.name} | 音量: {int(selected_volume * 100)}%")
    return selected_music, selected_volume


def run_pipeline(
    input_dir: str = "",
    target_resolution: str = "1080x1920",
    mode: str = "dual",  # "dual": 双版本; "no_sub": 仅无字幕; "bgm_mute": 静音配乐; "bgm_keep": 保留原声配乐
    fps: int = 30,
):
    input_dir = input_dir or os.environ.get("VIDEO_INPUT_DIR", str(Path.cwd()))
    dir_path = Path(input_dir)
    video_files = scan_and_sort_videos(input_dir)
    if not video_files:
        return

    # 输出路径规划
    no_sub_path = dir_path / "merged_no_sub.mp4"
    with_sub_path = dir_path / "merged_with_sub.mp4"
    bgm_mute_path = dir_path / "merged_with_bgm.mp4"
    bgm_keep_path = dir_path / "merged_with_orig_and_bgm.mp4"
    temp_srt = dir_path / "temp_subtitles.srt"

    # 如果是模式 3 或 模式 4，先进行背景音乐选择
    selected_music = None
    music_volume = 0.12
    if mode in ["bgm_mute", "bgm_keep"]:
        selected_music, music_volume = select_bgm_and_volume()
        if not selected_music:
            return

    print("\n" + "=" * 55)
    print(f"📂 扫描到 {len(video_files)} 个素材视频，拼接顺序：")
    for idx, f in enumerate(video_files, 1):
        print(f"  [{idx}] -> {f.name}")
    print("=" * 55)

    width, height = target_resolution.split("x")
    inputs = []
    filter_parts = []
    scale_flag = "lanczos"  # CPU 顶级高质量插值算法

    # 是否需要提取并保留视频原声音频流
    include_orig_audio = (mode != "bgm_mute")
    for i, video in enumerate(video_files):
        inputs.extend(["-i", str(video.resolve())])

        v_chain = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags={scale_flag}",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "setsar=1",
            f"fps={fps}",
            "hqdn3d=2:1.5:3:2.5",
            "unsharp=5:5:1.0:5:5:0.0",
        ]

        if include_orig_audio:
            filter_parts.append(
                f"[{i}:v]{','.join(v_chain)}[v{i}];"
                f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];"
            )
        else:
            filter_parts.append(f"[{i}:v]{','.join(v_chain)}[v{i}];")

    # 构建视频画面基础拼接
    if include_orig_audio:
        concat_streams = "".join([f"[v{i}][a{i}]" for i in range(len(video_files))])
        concat_filter = f"{concat_streams}concat=n={len(video_files)}:v=1:a=1[outv][orig_a]"
    else:
        concat_streams = "".join([f"[v{i}]" for i in range(len(video_files))])
        concat_filter = f"{concat_streams}concat=n={len(video_files)}:v=1:a=0[outv]"

    # ==========================
    # 模式 3：静音原声 + 混入指定编号 BGM 并控制音量
    # ==========================
    if mode == "bgm_mute":
        filter_complex = "".join(filter_parts) + concat_filter
        print(f"\n🚀 正在以【CPU 顶级画质】拼接画面，并混入背景音乐: {selected_music.name} (音量: {int(music_volume*100)}%)...")
        cmd_bgm = [
            "ffmpeg", "-y",
            *inputs,
            "-stream_loop", "-1",       # 循环背景音乐
            "-i", str(selected_music.resolve()),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", f"{len(video_files)}:a",
            "-filter:a", f"volume={music_volume}",
            "-c:v", "libx264",
            "-crf", "17",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "256k",
            "-shortest",               # 严格对齐视频时长
            str(bgm_mute_path)
        ]
        res = subprocess.run(cmd_bgm, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if res.returncode != 0:
            print("❌ 视频渲染失败：\n", res.stderr)
            return

        print(f"\n🎉 处理大功告成！已成功输出配乐成片：\n👉 {bgm_mute_path.name} (原声已静音，已混入 {int(music_volume*100)}% 背景音乐)\n")
        return

    # ==========================
    # 模式 4：保留原声 + 混入指定编号 BGM 并控制音量
    # ==========================
    if mode == "bgm_keep":
        bgm_input_index = len(video_files)
        # 将原声与调节音量后的背景音乐进行 amix 混音合成
        mix_audio_filter = (
            f";[{bgm_input_index}:a]volume={music_volume}[bgma];"
            f"[orig_a][bgma]amix=inputs=2:duration=first:dropout_transition=2[final_a]"
        )
        filter_complex = "".join(filter_parts) + concat_filter + mix_audio_filter

        print(f"\n🚀 正在以【CPU 顶级画质】拼接，保留原声并混入背景音乐: {selected_music.name} (BGM音量: {int(music_volume*100)}%)...")
        cmd_mix = [
            "ffmpeg", "-y",
            *inputs,
            "-stream_loop", "-1",       # 循环背景音乐
            "-i", str(selected_music.resolve()),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[final_a]",
            "-c:v", "libx264",
            "-crf", "17",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "256k",
            "-shortest",               # 严格对齐视频时长
            str(bgm_keep_path)
        ]
        res = subprocess.run(cmd_mix, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if res.returncode != 0:
            print("❌ 视频渲染失败：\n", res.stderr)
            return

        print(f"\n🎉 处理大功告成！已成功输出混音成片：\n👉 {bgm_keep_path.name} (保留原声对话 + 叠加 {int(music_volume*100)}% 背景配乐)\n")
        return

    # ==========================
    # 模式 1 & 2：常规保留原声渲染
    # ==========================
    filter_complex = "".join(filter_parts) + concat_filter.replace("[orig_a]", "[outa]")
    print("\n🚀 [第 1 阶段] 正在以【CPU 顶级画质超分增强】渲染无字幕版...")
    cmd_no_sub = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264",
        "-crf", "17",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "256k",
        str(no_sub_path)
    ]

    res = subprocess.run(cmd_no_sub, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    if res.returncode != 0:
        print("❌ 视频渲染失败：\n", res.stderr)
        return

    print(f"✅ 无字幕超清版已输出 -> {no_sub_path.name}")

    if mode == "no_sub":
        print(f"\n🎉 处理大功告成！已成功输出：\n👉 {no_sub_path.name} (保留原声，无字幕)\n")
        return

    # 双版本模式：继续执行英文字幕识别与极限贴底压制
    print("\n🚀 [第 2 阶段] 开始提取英文台词...")
    has_sub = transcribe_english_audio(no_sub_path, temp_srt)

    if not has_sub:
        print("⚠️ 未能生成有效字幕，跳过字幕版生成。")
        return

    print("\n🚀 [第 3 阶段] 正在压制极限贴底字幕 (字号 12，MarginV=25)...")
    os.chdir(str(dir_path))

    sub_style = (
        "FontName=Calibri,"
        "FontSize=12,"
        "PrimaryColour=&H00F0F0F0,"
        "OutlineColour=&H80000000,"
        "BorderStyle=1,"
        "Outline=0.8,"
        "Shadow=0.5,"
        "Alignment=2,"
        "MarginV=25"
    )
    vf_arg = f"subtitles=temp_subtitles.srt:force_style='{sub_style}'"

    cmd_with_sub = [
        "ffmpeg", "-y",
        "-i", str(no_sub_path.name),
        "-vf", vf_arg,
        "-c:v", "libx264",
        "-crf", "17",
        "-preset", "medium",
        "-c:a", "copy",
        str(with_sub_path.name)
    ]

    res_sub = subprocess.run(cmd_with_sub, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")

    if temp_srt.exists():
        temp_srt.unlink()

    if res_sub.returncode != 0:
        print("❌ 字幕压制失败：\n", res_sub.stderr)
        return

    print(f"✅ 带英文字幕版已输出 -> {with_sub_path.name}")
    print("\n" + "=" * 55)
    print("🎉 处理完成！双版本均已就绪：")
    print(f" 1. 无字幕超清版 : {no_sub_path}")
    print(f" 2. 极限贴底字幕 : {with_sub_path}")
    print("=" * 55 + "\n")


def interactive_menu():
    input_dir = os.environ.get("VIDEO_INPUT_DIR", str(Path.cwd()))
    current_res = "1080x1920"  # 默认竖屏

    while True:
        is_vertical = (current_res == "1080x1920")
        res_display = "📱 竖屏 (1080x1920 - 短视频)" if is_vertical else "🖥️ 横屏 (1920x1080 - 长视频)"

        print("\n" + "=" * 65)
        print("        🎬 顶级画质视频拼接与自媒体多版本导出工具")
        print("=" * 65)
        print(f" 当前画面规格 : {res_display}")
        print(" 顶级画质方案 : 💎 Lanczos插值放大 + 细腻降噪 + 细节锐化")
        print(" 极致字幕方案 : ✨ 12号 Calibri | 紧凑快切 | 极限贴底 (MarginV=25)")
        print("-" * 65)
        print(" 1. 🚀 [双版齐发] 同时导出【带字幕版】与【无字幕版】 [保留原声]")
        print(" 2. ⚡ [仅无字幕] 只输出【原声·无字幕版】 (跳过AI听写，最快)")
        print(" 3. 🔇 [静音配乐] 静音原声，选择 C:\\video\\music 配乐并调音量")
        print(" 4. 🎶 [原声+配乐] 保留原声，选择 C:\\video\\music 配乐并混音")
        print(" 5. 🔄 [切换画面] 切换为 " + ("🖥️ 横屏 (1920x1080)" if is_vertical else "📱 竖屏 (1080x1920)"))
        print(" 0. 退出程序")
        print("=" * 65)

        choice = input("请输入选项 (0-5): ").strip()

        if choice == "1":
            run_pipeline(input_dir=input_dir, target_resolution=current_res, mode="dual")
            break
        elif choice == "2":
            run_pipeline(input_dir=input_dir, target_resolution=current_res, mode="no_sub")
            break
        elif choice == "3":
            run_pipeline(input_dir=input_dir, target_resolution=current_res, mode="bgm_mute")
            break
        elif choice == "4":
            run_pipeline(input_dir=input_dir, target_resolution=current_res, mode="bgm_keep")
            break
        elif choice == "5":
            current_res = "1920x1080" if is_vertical else "1080x1920"
        elif choice == "0":
            sys.exit(0)
        else:
            print("⚠️ 无效输入，请输入 0~5。")


if __name__ == "__main__":
    interactive_menu()