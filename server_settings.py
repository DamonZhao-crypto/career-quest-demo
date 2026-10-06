"""Server-only model configuration; never pass credentials to UI widgets."""

from dataclasses import dataclass, field
from collections.abc import Mapping


PROVIDERS = ["阿里云百炼（免费额度）", "Ollama 本机免费", "DeepSeek", "OpenAI"]
ALIASES = dict(zip(("bailian", "ollama", "deepseek", "openai"), PROVIDERS))


class SettingsError(ValueError):
    """A static, safe configuration message suitable for displaying to the user."""


@dataclass(frozen=True)
class ServerSettings:
    shared: bool = False
    provider: str = PROVIDERS[0]
    api_key: str = field(default="", repr=False)
    voice_api_key: str = field(default="", repr=False)
    model: str = ""
    base_url: str = ""


def resolve_settings(options, environ):
    """Environment overrides [career_quest] secrets. Empty configuration fails closed."""
    if not isinstance(options, Mapping):
        raise SettingsError("服务器模型配置格式有误，请管理员检查 career_quest 配置。")

    names = ("provider", "api_key", "voice_api_key", "model", "base_url")
    shared = bool(options) or any(f"CAREER_QUEST_{name.upper()}" in environ for name in names)
    if not shared:
        return ServerSettings()

    values = {}
    for name in names:
        value = environ.get(f"CAREER_QUEST_{name.upper()}", options.get(name, ""))
        if not isinstance(value, str):
            raise SettingsError("服务器模型配置须使用字符串，请管理员检查配置。")
        values[name] = value.strip()
    provider = values["provider"] or "bailian"
    values["provider"] = ALIASES.get(provider.lower(), provider)
    if values["provider"] not in PROVIDERS:
        raise SettingsError("服务器文字模型设置有误，请管理员检查 provider。")
    if values["provider"] != "Ollama 本机免费" and not values["api_key"]:
        raise SettingsError("网站尚未配置文字模型密钥，请管理员完成配置后重启。")
    for name in ("api_key", "voice_api_key"):
        key = values[name]
        if key and (not key.isascii() or any(character.isspace() for character in key)
                    or "YOUR_API_KEY" in key.upper()):
            label = "文字模型" if name == "api_key" else "朗读"
            raise SettingsError(
                f"{label}密钥仍是示例文字，或含空格、换行等无效字符。"
                "请在 secrets.toml 填入完整密钥，按 Ctrl+S 保存，再重启网站。"
            )
    if values["base_url"] and not values["base_url"].startswith("https://"):
        if values["provider"] != "Ollama 本机免费":
            raise SettingsError("服务器模型地址须使用 HTTPS，请管理员检查 base_url。")
    return ServerSettings(shared=True, **values)


def public_error(action, error):
    """API exceptions can contain credentials; expose only known, static messages."""
    status = getattr(error, "status_code", None)
    if status in (401, 403):
        detail = "模型服务认证失败，请管理员检查密钥、服务地址和访问权限。"
    elif status == 429:
        detail = "模型服务暂时达到调用限制或额度不足，请稍后重试或联系管理员。"
    else:
        detail = "服务暂时未能完成请求，请稍后重试；持续失败请联系管理员。"
    return f"{action}：{detail}"
