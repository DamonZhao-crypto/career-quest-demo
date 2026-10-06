# Career Quest · 游戏化语音面试

基于 Streamlit 的四关职业面试练习 Demo。面试官根据岗位、经历和上一轮回答提问，用户录音后通过服务器上的开源 faster-whisper 转成文字，校对后提交并获得训练反馈。

## 部署到 Streamlit Community Cloud

1. 将本目录的源文件放在 GitHub 仓库根目录。保留 `assets`、`.streamlit`、`tests` 等目录结构。
2. 打开 <https://share.streamlit.io/>，关联 GitHub，选择 **Create app → Yup, I have an app**。
3. 选择自己的仓库，分支 `main`，**Main file path 填 `cloud_app.py`**。
4. 在 Advanced settings 中选择 Python **3.12**。
5. Secrets 中粘贴本机已验证可用的 `[career_quest]` 配置，再添加 `[hosting]` 配置。格式见 `.streamlit/secrets.toml.example`。真实密钥仅填入平台 Secrets，不上传 GitHub。
6. 点击 Deploy，构建成功后分享平台给出的 HTTPS 地址。

**公开部署必须使用 `cloud_app.py`。** `app.py` 保留了本机配置模式，不能作为本部署包的公开入口。

完整中文教程见 [部署教程.md](部署教程.md)。

## 公开 Demo 的行为

- API Key 由后台统一提供，页面没有访客密钥输入框；未配置后台密钥时不会开放面试。
- 当前会话使用随机存档标识，不提供按任意编号查找其他人的记录。此方式不是账号系统，关闭或刷新会话前请导出成长记录。
- Whisper 默认使用多语言 `base`、CPU int8；第一次识别下载模型到 `data/models`。每次只识别一份录音，繁忙时提示重试。
- 如需 `small`，在 Secrets 的 `[hosting]` 中修改 `whisper_model`，保存并重启。须根据实际服务器内存验证。
- 默认全站每天最多 **200 次**模型请求（UTC 日期），每会话最多 60 次，最多同时处理两次请求。失败的外部请求也计入，自动重试关闭；朗读请求如启用也计入。这是请求数量限制，不是金额或 token 预算。
- 平台重建可能清空本地 SQLite 数据及请求计数。长期档案和严格费用控制需要持久数据库、账号和模型平台额度限制。
- API 费用仍由网站管理员承担。可在模型平台设置额度用完停止；网站托管免费不代表文字模型调用免费。

## 数据

不在数据库保存原始简历、录音或 API Key。SQLite 记录关卡分数、岗位和反馈；反馈可能引用经历。录音在服务器识别，临时文件识别结束后删除。简历文字与经校对的回答发送到管理员配置的文字模型服务，因此建议使用脱敏简历。

## 本机测试

```powershell
py -3.12 -m venv .venv_cloud
.\.venv_cloud\Scripts\python.exe -m pip install -r requirements.txt
.\.venv_cloud\Scripts\python.exe -m unittest discover -s tests
```

要预览公开版，可在本机创建 `.streamlit/secrets.toml`，然后运行：

```powershell
.\.venv_cloud\Scripts\python.exe -m streamlit run cloud_app.py
```

## 部署验收

主页能加载；访客无需填写密钥；创建挑战；录制短音频、识别并校对；提交两题获得关卡结算；成长记录能导出；另一个无痕窗口看不到前一个窗口的记录。测试通过后再把链接发给同学。

本包已在 GitHub Actions 的 Linux/Python 3.12/Streamlit 1.65.0 环境通过依赖安装、7 项离线功能检查及语音后端导入检查。实际网站访问、模型下载与识别速度、麦克风权限和 API 调用仍需在部署后验证。
