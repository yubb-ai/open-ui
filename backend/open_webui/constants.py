from enum import Enum


class MESSAGES(str, Enum):
    DEFAULT = lambda msg="": f"{msg if msg else ''}"
    MODEL_ADDED = lambda model="": f"The model '{model}' has been added successfully."
    MODEL_DELETED = (
        lambda model="": f"The model '{model}' has been deleted successfully."
    )


class WEBHOOK_MESSAGES(str, Enum):
    DEFAULT = lambda msg="": f"{msg if msg else ''}"
    USER_SIGNUP = lambda username="": (
        f"New user signed up: {username}" if username else "New user signed up"
    )


class ERROR_MESSAGES(str, Enum):
    def __str__(self) -> str:
        return super().__str__()

    DEFAULT = lambda err="": f"出错了 :/\n{err if err else ''}"
    ENV_VAR_NOT_FOUND = "找不到必需的环境变量，程序即将终止。"
    CREATE_USER_ERROR = (
        "糟糕！创建账户时出现问题。请稍后再试。如果问题仍然存在，请联系客服寻求帮助。"
    )
    DELETE_USER_ERROR = "糟糕！删除用户时遇到问题。请再试一次。"
    EMAIL_MISMATCH = "哎呀！此邮箱与您提供商注册的邮箱不匹配。请检查您的邮箱并重试。"
    EMAIL_TAKEN = "哎呀！此邮箱已被注册。请使用现有账户登录或选择另一个邮箱重新开始。"
    USERNAME_TAKEN = "哎呀！此用户名已被注册。请选择另一个用户名。"
    COMMAND_TAKEN = "哎呀！此命令已被注册。请选择另一个命令字符串。"
    FILE_EXISTS = "哎呀！此文件已注册。请选择另一个文件。"

    ID_TAKEN = "哎呀！此ID已被注册。请选择另一个ID字符串。"
    MODEL_ID_TAKEN = "哎呀！此模型ID已被注册。请选择另一个模型ID字符串。"
    NAME_TAG_TAKEN = "哎呀！此名称标签已被注册。请选择另一个名称标签字符串。"

    INVALID_TOKEN = "您的会话已过期或令牌无效。请重新登录。"
    INVALID_CRED = "提供的邮箱或密码不正确。请检查是否有拼写错误并尝试重新登录。"
    INVALID_EMAIL_FORMAT = "管理员已关闭注册，请联系管理员吧！"
    INVALID_CUSTOMER_EMAIL_FORMAT = (
        "您输入的邮箱格式无效。请仔细检查并确保您使用的是有效的邮箱地址。"
    )
    TURNSTILE_ERROR = "请完成验证码验证以继续操作！"
    INVALID_PASSWORD = "提供的密码不正确。请检查是否有拼写错误并重试。"
    INVALID_TRUSTED_HEADER = "您的提供商未提供受信任的标头。请联系您的管理员寻求帮助。"

    EXISTING_USERS = "由于存在现有用户，您无法关闭身份验证。如果您想禁用 WEBUI_AUTH，请确保您的 Web 界面没有任何现有用户，并且是全新安装。"

    UNAUTHORIZED = "401 未经授权"
    ACCESS_PROHIBITED = "您没有权限访问此资源。请联系您的管理员寻求帮助。"
    ACTION_PROHIBITED = "作为安全措施，请求的操作已被限制。"

    FILE_NOT_SENT = "文件未发送"
    FILE_NOT_SUPPORTED = "糟糕！您尝试上传的文件格式不受支持。请上传支持格式的文件（例如 JPG、PNG、PDF、TXT）并重试。"

    NOT_FOUND = "我们找不到您要查找的内容 :/"
    USER_NOT_FOUND = "我们找不到您要查找的用户 :/"
    API_KEY_NOT_FOUND = (
        "糟糕！好像出错了。API 密钥丢失。请确保提供有效的 API 密钥以访问此功能。"
    )

    MALICIOUS = "检测到异常活动，请稍后再试。"

    PANDOC_NOT_INSTALLED = "服务器上未安装 Pandoc。请联系您的管理员寻求帮助。"
    INCORRECT_FORMAT = lambda err="": f"格式无效。请使用正确的格式{err}"
    RATE_LIMIT_EXCEEDED = "API 速率限制已超出"

    MODEL_NOT_FOUND = lambda name="": f"找不到模型 '{name}'"
    OPENAI_NOT_FOUND = lambda name="": "未找到 OpenAI API"
    OLLAMA_NOT_FOUND = "WebUI 无法连接到 Ollama"
    CREATE_API_KEY_ERROR = "糟糕！创建 API 密钥时出现问题。请稍后再试。如果问题仍然存在，请联系客服寻求帮助。"

    EMPTY_CONTENT = "提供的内容为空。请确保在继续操作之前存在文本或数据。"

    DB_NOT_SQLITE = "此功能仅在运行 SQLite 数据库时可用。"

    INVALID_URL = "糟糕！您提供的 URL 无效。请仔细检查并重试。"

    WEB_SEARCH_ERROR = (
        lambda err="": f"{err if err else '糟糕！在搜索网络时出现问题。'}"
    )

    OLLAMA_API_DISABLED = "Ollama API 已禁用。请启用它以使用此功能。"

    FILE_TOO_LARGE = (
        lambda size="": f"糟糕！您尝试上传的文件太大。请上传小于 {size} 的文件。"
    )

    DUPLICATE_CONTENT = "检测到重复内容。请提供唯一的内容以继续操作。"
    FILE_NOT_PROCESSED = "此文件无法提取内容。请确保在继续操作之前已处理该文件。"


class TASKS(str, Enum):
    def __str__(self) -> str:
        return super().__str__()

    DEFAULT = lambda task="": f"{task if task else 'generation'}"
    TITLE_GENERATION = "title_generation"
    EMOJI_GENERATION = "emoji_generation"
    QUERY_GENERATION = "query_generation"
    FUNCTION_CALLING = "function_calling"
    MOA_RESPONSE_GENERATION = "moa_response_generation"
