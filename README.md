# PDF to Markdown Bilingual Converter

一个用于将PDF文档转换为Markdown格式，并支持中英双语对照的工具。

## ✨ 功能特点

- **PDF转Markdown**: 将PDF文档拆分为结构化的Markdown文件
- **智能分块翻译**: 支持大文件的智能分块，确保翻译完整性
- **中英双语对照**: 支持多种双语对照格式
- **格式美化**: 自动识别标题层级、列表、引用等格式
- **章节拆分**: 按照章节号+章节标题自动命名文件

## 📁 项目结构

```
├── main.py                    # 主程序入口
├── translator.py              # 翻译模块
├── bilingual_formatter.py     # 双语对照格式化模块
├── markdown_converter.py      # Markdown格式美化模块
├── config.py                  # 配置文件
├── requirements.txt           # 依赖列表
└── output/
    ├── chapters/
    │   ├── en/                # 英文版章节 (53章)
    │   ├── zh/                # 中文版章节 (53章)
    │   └── bilingual/         # 双语对照章节 (53章)
    ├── checkpoints/           # 翻译检查点
    └── full/                  # 完整双语文档
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 依赖库: 见 `requirements.txt`

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法

#### 1. 完整流程（PDF转换 + 翻译 + 双语对照）

```bash
python main.py --api-key YOUR_API_KEY --api-base YOUR_API_BASE --model YOUR_MODEL full
```

#### 2. 仅翻译

```bash
python main.py --api-key YOUR_API_KEY --api-base YOUR_API_BASE --model YOUR_MODEL translate
```

#### 3. 仅生成双语对照

```bash
python main.py bilingual
```

## 🔧 命令行参数

```bash
python main.py [COMMAND] [OPTIONS]

Commands:
  full         完整流程：转换 -> 翻译 -> 双语对照
  translate    仅执行翻译
  bilingual    仅生成双语对照

Options:
  --api-key TEXT       OpenAI API Key
  --api-base TEXT      API基础URL
  --model TEXT         模型名称
  --help               显示帮助信息
```

## 📄 输出格式

### 双语对照格式（方案一：段落级对照）

```markdown
## ## 章节标题

英文段落内容...

**中文:** 中文翻译内容...

## ## 下一个章节

英文段落内容...

**中文:** 中文翻译内容...
```

## 📊 统计信息

- **总章节数**: 53章
- **文档来源**: International GAAP 2025
- **翻译覆盖率**: 100%

## 📝 示例文件

| 章节 | 文件 |
|------|------|
| Chapter 01 | `output/chapters/bilingual/01_International_GAAP.md` |
| Chapter 28 | `output/chapters/bilingual/28_Revenue.md` |
| Chapter 53 | `output/chapters/bilingual/53_Climate-related_Disclosures_(IFRS_S2).md` |

## 📄 License

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！