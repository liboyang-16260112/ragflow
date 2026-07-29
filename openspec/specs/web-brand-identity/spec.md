# web-brand-identity Specification

## Purpose

定义 Web 界面的 FMoss-RAG 品牌名称、图标、宣传语以及响应式和可访问性要求，同时保留必要的技术标识。

## Requirements

### Requirement: 登录页展示新的 FMoss 品牌图标
系统 SHALL 将指定的方形 FMoss PNG 作为仓库内静态资源提供给登录页，并在登录页品牌区使用该资源替代 `/logo.svg`。图标元素 SHALL 保留 `className="size-8 mr-[12] cursor-pointer"`，且运行时不得依赖开发机绝对路径。

#### Scenario: 登录页加载品牌图标
- **WHEN** 用户访问登录或注册页面
- **THEN** 页面从可部署的 Web 静态资源路径加载 FMoss 图标，并以现有 32×32 图标尺寸和间距显示

#### Scenario: 构建环境不具备桌面文件
- **WHEN** 前端在容器或其他不含原始桌面文件的环境中构建和运行
- **THEN** 登录页仍能成功加载已纳入仓库的 FMoss 图标

### Requirement: 全局页头和浏览器标签使用 FMoss 品牌图标
系统 SHALL 在全局页头、移动端导航抽屉和浏览器标签页复用 `/fmoss-logo.png`，不得继续在这些用户可见入口加载 `/logo.svg`。全局页头的品牌外链 SHALL 指向 `https://www.zqykj.com/#/home`，并使用网站语义图标和可访问性名称。

#### Scenario: 已登录用户查看全局页头
- **WHEN** 用户进入包含全局页头的应用页面
- **THEN** 页头显示 FMoss 图标，企业官网链接显示网站语义图标并在新标签页打开指定网址

#### Scenario: 用户查看浏览器标签页
- **WHEN** 浏览器加载 Web 应用入口文档
- **THEN** 标签页使用 FMoss PNG 作为 favicon，而不是旧的 `/logo.svg`

### Requirement: 所有 Web 可见品牌名称统一为 FMoss-RAG
Web 前端 SHALL 在页面文本、浏览器标题、应用名称配置、管理入口、嵌入界面、placeholder、进度提示、可访问性文本和国际化文案中使用 `FMoss-RAG`，且不得向用户显示旧的 `RAGFlow` 品牌名称。

#### Scenario: 使用任一受支持语言浏览产品页面
- **WHEN** 用户选择任一受支持语言并访问包含产品名称的 Web 页面
- **THEN** 所有可见产品名称均显示为 `FMoss-RAG`，不显示旧品牌名称

#### Scenario: 浏览器和嵌入界面展示应用名称
- **WHEN** 用户查看浏览器标签、嵌入页面或管理端登录入口
- **THEN** 页面元信息和可见应用名称使用 `FMoss-RAG`

### Requirement: 品牌替换不得改变技术契约
系统 MUST 保留内部组件名、类型名、枚举及序列化值、缓存键、OAuth 消息类型、服务进程名、有效域名、外部 URL 和上游仓库引用中的 RAGFlow 技术标识，除非该值仅用于用户可见展示。

#### Scenario: 品牌残留扫描发现技术标识
- **WHEN** 实施后的残留扫描命中内部标识、协议值或有效外部链接
- **THEN** 审核将该命中记录为允许保留，并验证其不会作为旧品牌文字直接展示给用户

#### Scenario: 品牌残留扫描发现可见文案
- **WHEN** 实施后的残留扫描命中会渲染给用户的旧品牌文字
- **THEN** 该检查失败，且该文案必须在发布前替换为 `FMoss-RAG`

### Requirement: 登录页展示分层主副标题
登录页 SHALL 以两行层级展示品牌宣传语：简体中文主标题为“FMoss 智能知识增强引擎”，副标题为“打通非结构化数据与 LLM 之间的精准检索链路”。主标题 SHALL 使用较大字号，副标题 SHALL 使用较小字号，两者保持居中、清晰行距和现有视觉风格。

#### Scenario: 简体中文登录页显示宣传语
- **WHEN** 当前语言为 `zh-Hans` 且用户访问登录页
- **THEN** 页面在上方显示指定中文主标题，并在下方显示指定中文副标题

#### Scenario: 英文回退显示宣传语
- **WHEN** 当前语言需要使用英文回退文案
- **THEN** 主标题显示 `FMoss intelligent knowledge augmentation engine`，副标题显示 `Connecting unstructured data to precise retrieval for LLMs`

### Requirement: 登录品牌区保持响应式和可访问
登录页品牌区 SHALL 在窄屏、平板和桌面宽度下保持无水平溢出，允许长标题合理换行，不得遮挡登录卡片，并 SHALL 为品牌图标提供描述 FMoss-RAG 的替代文本。

#### Scenario: 窄屏显示双层宣传语
- **WHEN** 登录页在典型手机宽度下渲染
- **THEN** 主副标题在可用宽度内居中换行，图标和品牌名称保持可见，登录卡片不被宣传区遮挡

#### Scenario: 图标无法加载
- **WHEN** 浏览器无法加载品牌图片资源
- **THEN** 辅助技术和替代内容仍能识别该图片为 FMoss-RAG 品牌图标
