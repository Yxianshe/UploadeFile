
# 🚀 SFTP Pro - Python GUI Client (V37)

**SFTP Pro** 是一个基于 Python `tkinter` 和 `paramiko` 开发的高级 SFTP 文件传输客户端。

它专为复杂的网络环境设计，支持 **跳板机 (Jump Host)** 隧道连接、**MFA/OTP 交互式认证**，以及**断点续传/智能跳过**功能。V37 版本采用了现代化的暗色主题 UI，并针对大文件传输速度进行了优化。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

---

## ✨ 核心功能 (Key Features)

### 🔐 高级连接与认证

* **跳板机支持 (Bastion/Jump Host)**: 支持通过中间服务器建立 SSH 隧道连接目标服务器。
* **交互式 MFA/OTP 支持**: 完美处理需要动态验证码（Google Authenticator/短信/Microsoft）的登录场景。
* **多种认证方式**: 支持 密码、SSH 密钥 (PEM/RSA/Ed25519) 以及混合认证。
* **持久化会话**: 连接建立后保持 Keep-Alive，多次传输无需重复登录。

### 📂 智能传输系统

* **智能跳过 (Smart Skip)**: 自动检测远程文件，如果文件名和大小一致，自动跳过传输（实现秒传/断点续传效果）。
* **强制覆盖模式**: 提供复选框选项，可强制覆盖远程同名文件。
* **递归传输**: 支持整个文件夹（包含子目录）的上传与下载。
* **实时状态监控**: 显示实时传输速度 (MB/s)、已传输量以及当前正在处理的文件名。

### 🛠️ 实用工具箱

* **内置终端**: 提供轻量级交互式 Shell，可直接发送 Shell 命令（如 `ls`, `df -h`, `unzip` 等）。
* **配置管理**: 自动保存历史连接配置（密码除外），支持多环境快速切换。
* **暗色主题 UI**: 护眼配色，操作直观。

---

## ⚙️ 安装指南 (Installation)

### 前置要求

* Python 3.8 或更高版本
* `pip` 包管理器

### 1. 克隆或下载代码

将 `main_upload_fileV3.7.py` (或其它版本)下载到本地。

### 2. 安装依赖库

本项目主要依赖 `paramiko` 处理 SSH/SFTP 协议，`tkinter` 通常内置于 Python 安装包中。

```bash
pip install paramiko
```
