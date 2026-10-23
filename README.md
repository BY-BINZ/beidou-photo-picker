# 摄影师一键选图 · 北斗 Photo Picker

[![Tests](https://github.com/BY-BINZ/beidou-photo-picker/actions/workflows/tests.yml/badge.svg)](https://github.com/BY-BINZ/beidou-photo-picker/actions/workflows/tests.yml)

**[下载 Windows 免费测试版 v0.1.0](https://github.com/BY-BINZ/beidou-photo-picker/releases/tag/v0.1.0)** · [查看开发路线](ROADMAP.md)

**给电商摄影师和摄影工作室的小图找原图工具：按文件名或编号匹配 JPG / RAW，并保留客户已经整理好的文件夹结构。**

[免费版功能](#免费版现在能做什么) · [使用方法](#开始使用) · [版本区别](docs/EDITIONS.md) · [开发路线](ROADMAP.md) · [反馈问题](../../issues)

本项目来自已有 **PicKing 选图王** 的基础文件匹配工作流，独立发布为免费、开源社区版。现有付费产品继续维护；它的授权、AI 模型与专业代码不在这个仓库中。

## 免费版现在能做什么

- 按不含扩展名的文件名匹配客户小图与高清原图。
- 同名匹配不到时，使用完整尾号查找，避免把 `BR5_7539` 中的 `5` 当作照片编号。
- 同编号多候选明确标记“需核对”，不自动拿第一张凑数。
- 同名商家目录优先；保留小图端多层目录结构。
- 支持 JPG、PNG、TIFF 选片；可查找并复制 JPG、CR3、CR2、NEF、ARW、DNG 等文件。
- 只复制已匹配文件，不移动、不删除原图、不覆盖已有输出。
- 每次导出生成逐项 JSONL 清单，记录成功、失败、未匹配和 SHA-256 校验结果。
- 本地处理，不上传照片、不收集使用数据；无需注册或激活。

**边界：** 当前免费版只比较文件名，不解码或预览 RAW，不检测照片内容。没有高清对应文件的吊牌会列为未找到，不会自行补齐。JPG 与 RAW 同名并存时也要求核对，尚无格式优先选项。导出所在磁盘需支持硬链接，Windows 推荐 NTFS；不支持时会记录失败，不降低为覆盖写入。0.1.0 是首个测试发布，建议先用副本样本体验。

## 开始使用

### Windows 桌面版

从 [v0.1.0 发布页](https://github.com/BY-BINZ/beidou-photo-picker/releases/tag/v0.1.0) 下载 Windows ZIP，解压后运行 `BeidouPhotoPicker-Free.exe`。发布页附有校验值。不需要安装 Python；源码运行方式见下文。

### 从源码启动

需要 Python 3.12 或更高版本，桌面界面使用随 Python 安装的 Tkinter，不需要安装大模型、PyQt 或显卡运行库。

```powershell
python -m picking
```

1. 选择客户选好的小图目录。
2. 选择高清原图或 RAW 目录。
3. 选择独立输出目录。
4. 点击“查找并预览”，检查“未找到 / 需核对”。
5. 点击“保留目录导出”，查看结果和输出清单。

输出、小图、原图目录不能相同或互相包含。免费版目前导出全部已匹配项；如需精确控制选片，请在小图目录中先整理好要交付的文件。

### 命令行

```powershell
# 只预览和生成清单，不复制照片
python -m picking --selected "D:\选好的小图" --originals "E:\原图" --report "D:\匹配清单.json"

# 保留小图目录结构导出
python -m picking --selected "D:\选好的小图" --originals "E:\原图" --output "F:\本次交付"
```

退出码：0 为全部成功；2 表示存在未找到、冲突或复制失败；1 为目录或运行错误。清单含本机路径，向他人反馈问题前请先去除客户名称和私人路径。

## 免费版与专业版

免费版提供长期可用的基础匹配和可靠导出。专业版沿用既有选图王产品，计划逐步整合吊牌 OCR、图片质量筛选、分款和千问图片识别命名。**这些专业功能不在当前免费版中；新版整合包尚未发布，不承诺自动识别准确率。**

详细边界见 [版本说明](docs/EDITIONS.md)。现有付费用户的具体购买权益以原约定为准，不因免费版发布而自动改变。

## 开发与贡献

```powershell
python -m unittest discover -s tests -v
```

参见 [贡献指南](CONTRIBUTING.md)、[开发路线](ROADMAP.md) 和 [安全说明](SECURITY.md)。请使用合成测试数据，不提交客户照片、授权码、机器码、商业模型或支付资料。

## 许可与名称

本仓库代码采用 [MIT License](LICENSE)，允许在遵守许可证的前提下使用、修改和再分发；这不代表授权冒用北斗品牌或现有付费产品身份。图片、模型和第三方产品不随本仓库授权。原产品名称为“选图王 PicKing”，本社区版由北斗摄影维护。

检索描述：摄影师选图软件、小图找原图、RAW 匹配、照片按编号查找、保留文件夹结构导出、摄影素材整理。
