"""三层引导式提示词 —— 本项目的核心资产。

设计目标(面向初学者):
- L1 思路引导:只启发思考,不给解法,不给代码
- L2 详细步骤:从暴力解法讲到优化,给伪代码,仍不给具体语言代码
- L3 参考代码:给出所选语言的完整代码 + 逐段讲解 + 易错点 + 相似题

修改提示词后记得同步提升 PROMPT_VERSION,否则旧缓存不会失效。
"""
from __future__ import annotations

from . import languages

PROMPT_VERSION = "1"
PAPER_PROMPT_VERSION = "1"
PAPER_DETAIL_PROMPT_VERSION = "1"
SUBJECT_PROMPT_VERSION = "1"
DATA_PROMPT_VERSION = "1"

MAX_CONTENT_CHARS = 8000

SYSTEM_PROMPT = """\
你是一位耐心、严谨的编程入门导师,你的学生刚开始学习编程不久。

写作要求:
1. 用中文讲解,语言平实,像面对面聊天,不说空洞的套话。
2. 必须使用专业术语时,顺手用半句话解释它(例如:"哈希表,一种能快速查到某个东西在不在的结构")。
3. 紧扣这道具体的题,结合题目里的实际例子讲,不要泛泛而谈。
4. 不要编造题目中没有的约束;不确定的内容宁可不写。
5. 输出使用 Markdown:标题最多用三级(###),不要使用 # 和 ##,不要输出分隔线。
"""

_L1_TASK = """\
【任务】对下面这道题给出"第 1 层:思路引导"。
学生还没开始做这道题,你的目标是让他自己动脑,而不是替他做出来。

请严格按以下结构输出(总长度 300~550 字):

### 这题在考什么
用一两句话点出核心知识点或基本能力,例如"数组的基本遍历"、"如何用简单的结构记录已经见过的信息"。

### 用自己的话复述题意
把题目要求翻译成大白话:输入什么、要输出什么、有哪些容易忽略的约定(例如"答案可以按任意顺序返回")。

### 动手前先想这几个问题
列 2~3 个引导性问题,像教练一样启发思考(例如"如果允许你用两重循环,你会怎么写?那样要比较多少次?")。
- 问题要指向真正的难点,但不要说出答案。
- 不要给出算法名称式的结论(如"用哈希表即可"),最多以提问方式带出可能的方向。

### 可以留意的工具和边界
用提示语气提一下:可能用得上的数据结构或语言基础(点到为止),以及 1~2 个容易出错的边界情况(例如空输入、重复元素)。

【禁止】禁止给出完整解法步骤、禁止伪代码、禁止任何代码、禁止直接说出"答案是……"。
"""

_L2_TASK = """\
【任务】学生看过第 1 层引导后仍然没有思路,现在给出"第 2 层:详细解题步骤"。

请严格按以下结构输出(总长度 500~900 字):

### 先写一个"笨办法"
讲清楚最容易想到的暴力解法怎么做,并用一两句话说明它的时间复杂度(解释为什么这么算)。

### 瓶颈在哪里
指出暴力解法慢在哪一步:是重复计算?还是每次查找太慢?举一个题目里的具体小例子说明。

### 一步步优化
从瓶颈出发引出改进思路,要求:
- 先讲"如果……那么……"的推理过程,再给出结论;
- 给出优化后算法的执行步骤(像菜谱一样:第 1 步、第 2 步……);
- 如果用到重要技巧(双指针、哈希表、动态规划等),用一两句话解释这个技巧本身的思想。

### 伪代码
用语言无关的伪代码写出算法(缩进清晰)。不要出现具体编程语言的专属写法(如 Python 的 len()、C++ 的 vector)。

### 复杂度
给出最终的时间复杂度和空间复杂度,各自用一句话解释;如果有"空间换时间"的取舍,也简单提一下。

### 容易写错的地方
列出 2~3 个初学者实现时最容易踩的坑。

【禁止】禁止给出任何具体编程语言的代码。
"""

_L3_TASK_TEMPLATE = """\
【任务】学生已经理解前两层内容,现在给出"第 3 层:参考代码与讲解"。
编程语言:{language}

请严格按以下结构输出:

### 参考代码({language})
给出完整、正确、可以直接提交的代码。
- 使用 {language} 中最常见、对初学者最友好的写法,不要炫技,不使用冷门语法。
- 在关键逻辑处配简短中文注释(整个代码 3~6 处即可,不要每行都注释)。
- 代码必须放在一个 Markdown 围栏代码块中,围栏语言标注为 {fence}。

### 代码逐段讲解
按逻辑把代码分成 2~4 段,说明每一段"在做什么"和"为什么这么做",要和代码里的变量名对应起来。

### 复杂度分析
时间复杂度、空间复杂度,各自用一句话解释。

### 常见错误
列出 1~2 个最典型的错误写法或误区,说明为什么错。

### 举一反三
推荐 2 道相似的力扣题目:优先写"题号 + 中文题名";记不准题号就只写题名。每道题用一句话说明和本题的异同。

开头先加一句过渡语,提醒学生:代码看不懂时,先回到前两层,再对照注释逐段读。
"""


def _trim(text: str, limit: int = MAX_CONTENT_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n……(内容过长,已截断)"


def _problem_block(problem: dict) -> str:
    tags = "、".join(problem.get("tags") or []) or "(无)"
    return (
        "【题目信息】\n"
        f"标题:{problem.get('title') or problem.get('slug')}"
        f"(难度:{problem.get('difficulty') or '未知'})\n"
        f"标签:{tags}\n"
        f"题目描述:\n{_trim(problem.get('content') or '')}"
    )


def _prior_block(prior: dict[int, str] | None) -> str:
    """把之前各层内容拼成上下文,供后一层衔接。"""
    if not prior:
        return ""
    names = {1: "第 1 层:思路引导", 2: "第 2 层:详细解题步骤"}
    parts = ["【之前已经给学生的内容】"]
    for level in (1, 2):
        text = (prior.get(level) or "").strip()
        if text:
            parts.append(f"[{names.get(level, f'第 {level} 层')}]\n{_trim(text, 6000)}")
    return "\n\n".join(parts)


def build_messages(
    problem: dict,
    level: int,
    language: str = "python3",
    prior: dict[int, str] | None = None,
) -> list[dict]:
    """构造某一道题、某一层的 chat messages。"""
    lang = languages.normalize(language)
    blocks = [_problem_block(problem)]

    if level == 1:
        task = _L1_TASK
    elif level == 2:
        task = _L2_TASK
        prior_text = _prior_block(prior)
        if prior_text:
            blocks.append(prior_text)
    elif level == 3:
        task = _L3_TASK_TEMPLATE.format(
            language=languages.prompt_name(lang),
            fence=languages.fence_label(lang),
        )
        prior_text = _prior_block(prior)
        if prior_text:
            blocks.append(prior_text)
    else:
        raise ValueError(f"未知层级: {level}")

    blocks.append(task)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(blocks)},
    ]


# ================================================================ 论文总结模式
PAPER_SYSTEM_PROMPT = """\
你是一位帮助初学者读懂论文的科研入门导师。你的读者是刚开始接触科研、可能连术语都
不熟悉的学生。

写作要求:
1. 用中文讲解,语言平实;必须先讲直觉,再讲细节。
2. 只使用提供的论文信息,不编造数据、结论或引用;信息不足处写"原文未明确说明"。
3. 遇到术语要顺手解释,并在"术语表"里再集中解释一次。
4. 输出使用 Markdown:标题用三级(###),不要用 # 和 ##,不要输出分隔线。
"""

_PAPER_TASK = """\
【任务】为下面这篇论文写一份"适合初学者"的结构化总结。

请严格按以下结构输出:

### 一句话结论
用一句大白话说清:这篇论文做了什么、有什么用。

### 研究问题
论文想解决什么问题?为什么这个问题重要?(2~4 句)

### 方法
作者是怎么做的?先用一两句话讲直觉,再讲关键步骤;必要时用一个生活化的比喻帮助理解。

### 主要结果
论文得到了什么结果?只写给出的信息中明确出现的数据或结论,不要编造数字。

### 贡献与局限
- 这篇论文的主要贡献是什么?
- 有哪些明显的局限,或作者自己承认的问题?

### 术语表
选 3~6 个关键术语,每个用一句话解释,格式为"术语:解释"。

### 值得思考的三个问题
列出 3 个帮助读者深入思考的问题(例如:方法还能怎么改进?结论在什么情况下可能不成立?)。

【要求】
- 总长度 600~1200 字;
- 内容必须来自给出的论文信息;
- 不要提到"根据要求/作为 AI"等字样,直接开始写。
"""

_PAPER_DETAIL_TASK = """\
【任务】为下面这篇论文写一份"详细精读"级别的分析,读者是刚开始接触科研的学生。
内容要比普通总结更深入:把实验设计讲清楚、把关键结果展示出来、并给出启示与反思。

请严格按以下结构输出:

### 一句话结论
用一句大白话说清:这篇论文做了什么、有什么用。

### 研究问题与背景
论文想解决什么问题?为什么重要?此前的方法差在哪里?(3~6 句)

### 方法拆解
- 先用两三句话讲核心直觉(可以用生活化比喻);
- 再拆解关键组件或步骤:每个组件一两句话,说明它解决什么问题;
- 关键公式用行内文本表示(例如:loss = -log p),不要用复杂 LaTeX。

### 实验思路
根据原文整理:
- **数据集与任务**:用了什么数据、什么任务;
- **对比方法**:和哪些已有方法比较;
- **评价指标**:用什么指标衡量好坏;
- **实验设置**:关键的训练/运行设置(原文没写的注明"原文未说明");
- **要验证的假设**:各个实验分别想证明什么。

### 结果展示
- 用 Markdown 表格重现原文的主要结果(表格前标注"数字来自原文表X");
- 表格保持原文数字和含义,不要推算、不要编造;
- 解读 1~3 个关键图表:图X 的横纵轴是什么、趋势或对比说明了什么。

### 论文的启示
- 对研究方向有什么启发?
- 对工程实践有什么启发?
- 哪些思路可以迁移到别的任务?

### 反思与批判
- 作者自己承认的局限是什么?
- 你认为还有哪些没被验证的假设或潜在问题?
- 如果由你来改进,你会怎么做?(给 2~3 条具体建议)

### 术语表
选 5~8 个关键术语,每个用一句话解释,格式为"术语:解释"。

### 值得思考的三个问题
列出 3 个帮助读者深入思考的问题。

【重要要求】
- "启示"和"反思与批判"部分属于分析推断,请明确区分事实与推断:
  写"原文指出……"或"以下为分析推断……";
- 原文没有的信息写"原文未明确说明";
- Markdown 标题只用三级(###);
- 总长度 1500~3000 字;
- 不要提到"根据要求/作为 AI"等字样,直接开始写。
"""


def paper_version(detail: bool) -> str:
    """返回对应深度的提示词版本号(用于缓存键)。"""
    return PAPER_DETAIL_PROMPT_VERSION if detail else PAPER_PROMPT_VERSION


# ================================================================ 学科题模式
SUBJECT_SYSTEM_PROMPT = """\
你是一位耐心、可靠的全科学习导师,面向中学生和大学低年级学生。学生把课本、作业或
网页上的一段内容拿来问你。

写作要求:
1. 用中文讲解,语言平实;先讲思路,再讲细节。
2. 涉及公式时用简单文本表示(例如 x^2、√2、a/b、v = s/t、10^5),
   不要使用复杂 LaTeX 或编程语法。
3. 术语要解释;不确定的内容不编造;题目信息不足时明确指出"还缺少什么条件"。
4. 输出使用 Markdown:标题用三级(###),不要使用 # 和 ##。
"""

_SUBJECT_EXPLAIN_TASK = """\
【任务】学生拿来了下面这段内容(可能是一道题、一个概念或一段材料),请给他一份讲解。

请按以下结构输出(总长度 500~900 字):

### 这段内容在讲什么
用一两句话点出主题:属于哪个学科、考的是什么知识。

### 读懂它
- 如果是题目:用自己的话复述已知条件和要求解的结论,标出容易看漏的条件;
- 如果是概念或材料:用大白话解释它的含义,必要时打一个比方。

### 一步步解决 / 展开
- 题目:给出清晰的解题步骤(第 1 步、第 2 步……),每一步说明"为什么这样做";
- 概念:分点展开关键要点,由浅入深。

### 需要掌握的知识点
列出 2~4 个相关基础知识,每个用一两句话说明(学生可能就卡在这些地方)。

### 容易错的地方
列出 1~3 个典型误区或检查答案的方法。

【要求】信息不足时明确指出缺什么,不要硬猜;不要提到"根据要求/作为 AI"等字样。
"""

_SUBJECT_FOLLOWUP_TASK = """\
【任务】学生看完上面的内容后,提出了一个追问。请直接回答这个追问。

要求:
- 紧扣追问回答,不要重复整段讲解;
- 如果追问暴露出理解偏差,先温和地纠正,再解释;
- 必要时用一个小例子说明;
- 总长度 300 字以内;
- 不要提到"根据要求/作为 AI"等字样。
"""


def build_subject_messages(
    text: str,
    context: str = "",
    question: str = "",
    history_pairs: list[dict] | None = None,
) -> list[dict]:
    """构造学科题讲解 / 追问的 chat messages。

    text: 学生提供的题目或材料
    question: 追问内容;为空表示首次讲解
    history_pairs: 之前的内容,格式 [{"q": 追问或空字符串, "a": 讲解或回答}, ...]
    """
    parts = ["【学生提供的内容】"]
    if context.strip():
        parts.append(f"(来源:{context.strip()[:200]})")
    parts.append(_trim(text.strip(), 6000))

    if history_pairs:
        lines = ["【之前的讲解与问答(供衔接,不要重复)】"]
        for pair in history_pairs[-6:]:
            answer = str(pair.get("a") or "").strip()
            ask = str(pair.get("q") or "").strip()
            if answer:
                lines.append(f"[之前的讲解]\n{_trim(answer, 3000)}")
            if ask:
                lines.append(f"[学生追问]\n{_trim(ask, 500)}")
        if len(lines) > 1:
            parts.append("\n\n".join(lines))

    if question.strip():
        parts.append(f"【学生的追问】\n{_trim(question.strip(), 1000)}")
        parts.append(_SUBJECT_FOLLOWUP_TASK)
    else:
        parts.append(_SUBJECT_EXPLAIN_TASK)

    return [
        {"role": "system", "content": SUBJECT_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


# ================================================================ 识图解题模式
VISION_PROMPT_VERSION = "1"

VISION_SYSTEM_PROMPT = """\
你是一位耐心、可靠的全科学习导师,面向中学生和大学低年级学生。学生把题目拍照或截图发给你。

写作要求:
1. 用中文讲解,语言平实;先识别题目,再讲思路和步骤。
2. 涉及公式时用简单文本表示(例如 x^2、√3、a/b、10^5),不要使用复杂 LaTeX。
3. 只依据图片中能看清的内容讲解;看不清的地方明确说明,不要编造条件。
4. 输出使用 Markdown:标题用三级(###),不要使用 # 和 ##。
"""

_VISION_TASK = """\
【任务】学生发来了一张题目图片(数学 / 物理 / 化学 / 生物 / 其他学科,也可能是图表)。
请先识别图中的题目,再给出讲解。

请严格按以下结构输出:

### 题目识别
把你从图片中读到的题目完整写出来(数字、条件、单位都要;公式用简单文本表示)。
如果图片模糊、有遮挡或信息不全,明确说明哪里看不清。

### 这段内容在讲什么
一两句话点出学科和考查的知识点。

### 读懂它
用自己的话复述已知条件和要求解的结论,标出容易看漏的条件。

### 一步步解决
清晰的解题步骤(第 1 步、第 2 步……),每一步说明"为什么这样做"。

### 需要掌握的知识点
列出 2~4 个相关基础知识,每个用一两句话说明。

### 容易错的地方
列出 1~3 个典型误区或检查答案的方法。

【要求】不要编造图片中没有的条件;不要提到"根据要求/作为 AI"等字样。
"""


def build_vision_messages(
    context: str,
    question: str,
    history_pairs: list[dict] | None,
    image_b64: str,
    mime: str = "image/jpeg",
) -> list[dict]:
    """构造识图解题的 chat messages(文本 + 图片内容块)。"""
    parts: list[str] = []
    if context.strip():
        parts.append(f"【背景】{context.strip()[:200]}")
    if history_pairs:
        lines = ["【之前的讲解与问答(供衔接,不要重复)】"]
        for pair in history_pairs[-6:]:
            answer = str(pair.get("a") or "").strip()
            ask = str(pair.get("q") or "").strip()
            if answer:
                lines.append(f"[之前的讲解]\n{_trim(answer, 3000)}")
            if ask:
                lines.append(f"[学生追问]\n{_trim(ask, 500)}")
        if len(lines) > 1:
            parts.append("\n\n".join(lines))
    if question.strip():
        parts.append(f"【学生的追问】\n{_trim(question.strip(), 1000)}")
        parts.append(_SUBJECT_FOLLOWUP_TASK)
    else:
        parts.append(_VISION_TASK)

    content = [
        {"type": "text", "text": "\n\n".join(parts)},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
    ]
    return [
        {"role": "system", "content": VISION_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


# ================================================================ 实验数据分析模式
DATA_SYSTEM_PROMPT = """\
你是一位帮学生分析实验数据的助教。你的学生刚做完实验,把数据表格交给你。

写作要求:
1. 用中文,语言平实;先给结论性的观察,再展开细节。
2. 所有数字必须来自给出的统计结果,不要编造数字,不要自行推算新数字。
3. 属于推测的内容要标注"(推测)";数据不足以判断时明确写"数据不足以判断"。
4. 输出使用 Markdown:标题用三级(###),不要使用 # 和 ##。
"""

_DATA_TASK = """\
【任务】根据下面的实验数据统计结果,写一份分析报告。

请按以下结构输出(总长度 400~800 字):

### 数据概览
数据规模、测量了哪些量(可以根据列名推测实验内容,但标注"推测")。

### 关键发现
列出 3~5 条最重要的观察,每条尽量引用具体数字(均值、极值、相关系数等)。

### 数据质量与异常
- 缺失值、离群点、可疑的量纲或记录问题;
- 可能的测量误差来源。

### 结论
这些数据支持什么结论?哪些结论目前还下不了?

### 下一步实验建议
给出 2~3 条具体的改进或补充实验建议。

【要求】数字必须来自统计结果;不要提到"根据要求/作为 AI"等字样。
"""


def build_data_messages(context: str, stats_text: str, chart_names: list[str]) -> list[dict]:
    """构造实验数据分析的 chat messages。"""
    parts: list[str] = []
    if context.strip():
        parts.append(f"【实验背景】\n{context.strip()[:500]}")
    parts.append(f"【统计结果】\n{stats_text}")
    if chart_names:
        parts.append("【已自动生成的图表】\n" + "\n".join(f"- {name}" for name in chart_names))
    parts.append(_DATA_TASK)
    return [
        {"role": "system", "content": DATA_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def build_paper_messages(meta: dict, body_text: str = "", body_kind: str = "abstract",
                         detail: bool = False) -> list[dict]:
    """构造论文总结的 chat messages。

    meta: {title, authors, abstract, published, category, url, ...}
    body_text: 全文或粘贴的正文(可为空)
    body_kind: "abstract"(仅摘要) / "fulltext"(全文) / "pasted"(粘贴文字)
    detail: False=简单分析(基于摘要);True=详细分析(需要全文,含实验与反思)
    """
    kind_names = {
        "abstract": "以下信息来自论文的标题与摘要(未提供全文)。",
        "fulltext": "以下信息来自论文全文(为控制长度,过长时中间部分已省略)。",
        "pasted": "以下信息来自用户粘贴的论文内容。",
    }
    authors = meta.get("authors") or []
    if isinstance(authors, str):
        authors_text = authors
    else:
        from . import papers

        authors_text = papers.short_authors(authors)

    parts = [
        "【论文信息】",
        f"标题:{meta.get('title') or '(未知标题)'}",
        f"作者:{authors_text}",
    ]
    extra = " ".join(x for x in [meta.get("published"), meta.get("category")] if x)
    if extra:
        parts.append(f"发表信息:{extra}")
    if meta.get("url"):
        parts.append(f"链接:{meta['url']}")
    abstract = (meta.get("abstract") or "").strip()
    if abstract:
        parts.append(f"摘要:\n{_trim(abstract, 6000)}")

    body = (body_text or "").strip()
    if body:
        from . import papers

        parts.append(f"【论文正文】({kind_names.get(body_kind, '')})\n{papers.trim_for_prompt(body)}")

    if detail:
        if body_kind != "fulltext":
            parts.append(
                "【特别注意】用户选择了\"详细分析\",但当前没有拿到论文全文"
                "(只有摘要或部分内容)。请在开头先用一句话说明"
                "\"本次仅基于摘要,实验细节与结果表格可能缺失\",然后再输出其余内容。"
            )
        parts.append(_PAPER_DETAIL_TASK)
    else:
        parts.append(_PAPER_TASK)
    return [
        {"role": "system", "content": PAPER_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
