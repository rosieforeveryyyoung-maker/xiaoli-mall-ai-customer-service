import re


def parse_quick_import_text(raw_text):
    """
    解析一键粘贴的知识文档。

    第一行必须填写英文文件名，
    后面的内容必须是Markdown知识内容。
    """

    raw_text = raw_text.strip()

    if not raw_text:
        return (
            None,
            None,
            "粘贴内容不能为空。",
        )

    lines = raw_text.splitlines()

    first_line = lines[0].strip()

    file_name_match = re.fullmatch(
        r"文件名\s*[：:]\s*([A-Za-z0-9_-]+)",
        first_line,
    )

    if not file_name_match:
        return (
            None,
            None,
            "第一行格式不正确，"
            "应当类似：文件名：payment_policy",
        )

    file_name = file_name_match.group(1)

    markdown_content = "\n".join(
        lines[1:]
    ).strip()

    if not markdown_content:
        return (
            None,
            None,
            "文件名后面没有知识内容。",
        )

    if not re.search(
        r"^#\s+.+",
        markdown_content,
        flags=re.MULTILINE,
    ):
        return (
            None,
            None,
            "知识内容必须包含一级标题，"
            "例如：# 小丽商城支付规则",
        )

    if not re.search(
        r"^##\s+.+",
        markdown_content,
        flags=re.MULTILINE,
    ):
        return (
            None,
            None,
            "知识内容必须至少包含一个二级章节，"
            "例如：## 支持的支付方式",
        )

    return (
        file_name,
        markdown_content,
        None,
    )