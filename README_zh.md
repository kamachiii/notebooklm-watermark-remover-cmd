# NotebookLM 水印去除工具

![项目功能截图](public/screenshot.jpg)

一款强大的工具，使用先进的计算机视觉技术，可干净地移除 PDF 幻灯片、图片及信息图（PNG、JPG）中的「NotebookLM」水印。

## 功能说明

**智能去除（图像修复）：**
本工具不采用简单用纯色方块覆盖水印（在渐变或纹理背景上效果很差），而是使用 **基于 AI 的图像修复（计算机视觉）**。
- **检测** 水印：通过分析局部对比度和模糊差异。
- **重建** 水印下方的背景：保留渐变、纹理和幻灯片边框。
- **智能过滤**：智能忽略靠近水印区域的幻灯片内容（文字、线条），确保只去除 Logo/文字。

**支持格式：**
- **PDF 文档**：在每一页上无缝去除水印。
- **图片**：支持 PNG（含透明通道）、JPG、JPEG 和 WEBP。

**特性：**
- 批量处理：一次性清理整个文件夹。
- 进度条：便于跟踪大型任务。
- 预览模式（PDF）：可在第一页上测试效果。
- 智能自动识别文件类型。

## 快速开始

1. **环境准备：**
```bash
python3 -m venv venv
source venv/bin/activate  # Windows 用户: venv\Scripts\activate
```

2. **安装依赖：**
```bash
pip install -r requirements.txt
```

## 运行 EXE（Windows）

在完成构建（见下方 **构建 EXE**）后，运行：
```bash
dist\NotebookLM-Watermark-Remover.exe presentation.pdf
dist\NotebookLM-Watermark-Remover.exe .\my_folder\
dist\NotebookLM-Watermark-Remover.exe file.pdf -o output.pdf
dist\NotebookLM-Watermark-Remover.exe file.pdf --preview
```

## 使用方法

### 单文件处理（PDF 或图片）
```bash
python3 remover.py presentation.pdf
# 或
python3 remover.py slide.png
```
将在同一目录下生成 `presentation_cleaned.pdf` 或 `slide_cleaned.png`。

### 批量处理文件夹
```bash
python3 remover.py ./my_folder/
```
自动检测并清理目录中所有支持的文件（`.pdf`、`.png`、`.jpg` 等）。

### 先预览再处理（仅 PDF）
仅对第一页查看效果：
```bash
python3 remover.py file.pdf --preview
```

## 构建 EXE（Windows）

```bash
pip install -r requirements.txt -r requirements-build.txt
python -m PyInstaller remover.spec --noconfirm
```

生成的可执行文件位于 `dist\NotebookLM-Watermark-Remover.exe`。

## 项目结构

- `remover.py` - 核心逻辑，使用 PyMuPDF 和 OpenCV。
- `remover.spec` - 用于构建 Windows exe 的 PyInstaller 配置。
- `requirements.txt` - 依赖：`pymupdf`、`tqdm`、`Pillow`、`opencv-python-headless`、`numpy`。
- `requirements-build.txt` - PyInstaller（仅用于构建 exe）。
- `LICENSE` - MIT 开源协议

## 参与贡献

欢迎提交 Pull Request。如有问题可提 Issue 或通过其他方式联系。
