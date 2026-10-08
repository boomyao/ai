# 《宁可错放》视频工程

法律科普视频《宁可错放》的完整制作工程：旁白稿、配音、动画、配乐、音效与混音全部由代码生成。

## 环境准备

```bash
npm install                                   # 字体（思源宋体/黑体、霞鹜文楷、马善政、EB Garamond）
pip install edge-tts numpy scipy soundfile pyloudnorm pypinyin sherpa-onnx
pip install --no-deps tinysoundfont
# 音色库（MIT 许可）
curl -o assets/sf2/MuseScore_General.sf2 https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf2
# 读音校对用的中文语音识别模型
curl -L https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-paraformer-zh-2024-03-09.tar.bz2 | tar -xj -C assets/asr
```

渲染使用预装的 Playwright Chromium 和 ffmpeg。

## 流程

| 步骤 | 命令 | 产出 |
| --- | --- | --- |
| 解析旁白稿 | `python3 tools/parse_script.py --stats` | `build/lines.json` |
| 合成配音 | `python3 tools/tts.py` | `build/vo/*.wav`、`build/data.js`（逐词时间戳） |
| 校对读音 | `python3 tools/asr_check.py`、`python3 tools/poly_scan.py` | 识别差异、多音字读法报告 |
| 生成音效 | `python3 tools/sfx.py` | `build/sfx/*.wav` |
| 导出时间线 | `node render.mjs info` | `out/cues.json`（配音、音效、配乐、字幕） |
| 混音 | `cd tools && python3 mix.py` | `out/mix.wav` |
| 关键帧 | `node render.mjs stills 3 21.6 27` | `out/stills/*.png` |
| 渲染画面 | `node render.mjs video --workers 4` | `out/video.mp4`（无声） |

`script.md` 是唯一的文稿来源：`say=` 用同音字纠正 TTS 的多音字读法，`+0.8` 控制句后停顿。
画面在 `src/scenes/` 中按配音的逐字时间卡点（`s.say(id)` 返回的 `w('词')` 即该词开口的时刻）。
