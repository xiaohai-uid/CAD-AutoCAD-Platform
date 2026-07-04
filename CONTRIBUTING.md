# Contributing to CAD Direct Control Platform

First off, thank you for considering contributing to CAD Direct Control Platform! It's people like you that make open source such a fantastic tool.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include:

- **Use a clear, descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead**
- **Include your environment details**:
  - Python version
  - AutoCAD version
  - Operating system
  - Service endpoint (port)

### Suggesting Enhancements

- **Use a clear, descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and explain which behavior you expected to see instead**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Ensure all tests pass (38 tests should all pass)
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature/your-feature`
8. Submit a pull request

#### Pull Request Guidelines

- **Follow the existing code style**: PEP8 with type annotations
- **Add tests for new functionality**
- **Update documentation** (README.md, OpenSpec specs) as needed
- **Keep PRs focused**: one feature or bug fix per PR
- **Write meaningful commit messages** following conventional commits:
  - `feat: add new feature`
  - `fix: fix bug`
  - `docs: update documentation`
  - `refactor: refactor code`
  - `test: add tests`
  - `chore: update dependencies`

### Development Setup

```powershell
# Clone the repository
git clone https://github.com/your-username/cad-direct-control-platform.git
cd cad-direct-control-platform

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Project Structure

```
├── cad_mcp_bridge/     CAD COM 桥接层
├── config/             配置文件
├── docs/               文档和规格说明
├── openspec/           OpenSpec 规格文档
├── services/           9 个微服务
│   ├── intake/         NLP 解析引擎
│   ├── vision/         OpenCV 图像识别引擎
│   ├── cadplan/        CAD 执行计划生成
│   ├── validation/     4 类图纸校验
│   ├── cad_com/        COM 执行引擎
│   ├── preview/        预览/截图引擎
│   ├── dwg_scan/       DWG 文件扫描
│   ├── artifacts/      工件持久化管理
│   └── gateway/        编排网关
├── shared/             共享模型和配置
├── tests/              38 个单元测试
└── skill/              Reasonix Subagent Skill
```

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.
