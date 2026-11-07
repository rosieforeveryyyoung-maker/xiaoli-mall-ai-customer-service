import re #用来检查文件名是否合法

import streamlit as st

from rag import KNOWLEDGE_DIR

from backend_client import (
    rebuild_knowledge_from_api,
)
from knowledge_service import (
    parse_quick_import_text,
)

st.set_page_config(
    page_title="知识库管理",
    page_icon="📚",
    layout="wide",
)

st.title("📚 小丽商城知识库管理")
success_message = st.session_state.pop(
    "knowledge_success_message",
    None,
)

if success_message:
    st.success(success_message)
st.info(
    "这里管理小丽商城的原始知识文档，"
    "支持分项新增、一键导入、编辑、删除，"
    "并在内容变化后自动同步到Chroma向量库。"
)

st.subheader("新增知识文档")

with st.form(
    "create_knowledge_document",
    clear_on_submit=True,
):
    file_name = st.text_input(
        "文件名",
        placeholder="例如：payment_policy",
        help="只填写文件名，不需要填写 .md",
    )

    document_title = st.text_input(
        "文档标题",
        placeholder="例如：小丽商城支付规则",
    )

    section_title = st.text_input(
        "章节标题",
        placeholder="例如：支持的支付方式",
    )

    section_content = st.text_area(
        "知识内容",
        placeholder="请输入这一章节的具体规则",
        height=160,
    )

    submitted = st.form_submit_button(
        "保存并更新知识库"
    )


if submitted:
    file_name = file_name.strip()
    document_title = document_title.strip()
    section_title = section_title.strip()
    section_content = section_content.strip()

    if not all(
        [
            file_name,
            document_title,
            section_title,
            section_content,
        ]
    ):
        st.error("所有内容都必须填写。")

    elif not re.fullmatch(
        r"[A-Za-z0-9_-]+",
        file_name,
    ):
        st.error(
            "文件名只能包含英文字母、数字、下划线和短横线。"
        )

    else:
        target_path = (
            KNOWLEDGE_DIR / f"{file_name}.md"
        )

        if target_path.exists():
            st.error(
                f"文件 {target_path.name} 已经存在。"
            )

        else:
            document_content = (
                f"# {document_title}\n\n"
                f"## {section_title}\n"
                f"{section_content}\n"
            )

            target_path.write_text(
                document_content,
                encoding="utf-8",
            )

            api_result = (
                rebuild_knowledge_from_api()
            )

            if not api_result.get("success"):
                target_path.unlink(
                    missing_ok=True
                )

                # 文件已经回滚，再通知后端尝试恢复旧知识库
                rebuild_knowledge_from_api()

                st.error(
                    "知识文档保存失败："
                    f"{api_result.get('message', '后端更新失败')}"
                )

            else:
                result_data = api_result.get(
                    "data",
                    {},
                )

                document_count = result_data.get(
                    "document_count",
                    0,
                )

                chunk_count = result_data.get(
                    "chunk_count",
                    0,
                )

                st.success(
                    "知识文档创建成功，"
                    f"当前共有 {document_count} 个文档、"
                    f"{chunk_count} 个知识块。"
                )
st.subheader("一键粘贴导入")

st.caption(
    "第一行填写文件名，后面粘贴完整的Markdown知识内容。"
)

with st.form(
    "quick_import_knowledge",
):
    quick_import_text = st.text_area(
        "完整知识内容",
        height=320,
        placeholder=(
            "文件名：payment_policy\n"
            "# 小丽商城支付规则\n\n"
            "## 支持的支付方式\n"
            "支持支付宝、微信支付和银行卡支付。"
        ),
    )

    quick_import_submitted = (
        st.form_submit_button(
            "解析、保存并更新知识库"
        )
    )


if quick_import_submitted:
    (
        quick_file_name,
        quick_markdown_content,
        quick_error,
    ) = parse_quick_import_text(
        quick_import_text
    )

    if quick_error:
        st.error(quick_error)

    else:
        quick_target_path = (
            KNOWLEDGE_DIR
            / f"{quick_file_name}.md"
        )

        if quick_target_path.exists():
            st.error(
                f"文件 {quick_target_path.name} 已经存在，"
                "请修改文件名或使用编辑功能。"
            )

        else:
            quick_target_path.write_text(
                quick_markdown_content + "\n",
                encoding="utf-8",
            )

            api_result = (
                rebuild_knowledge_from_api()
            )

            if not api_result.get("success"):
                quick_target_path.unlink(
                    missing_ok=True
                )

                rebuild_knowledge_from_api()

                st.error(
                    "导入失败："
                    f"{api_result.get('message', '后端更新失败')}"
                )

            else:
                result_data = api_result.get(
                    "data",
                    {},
                )

                document_count = (
                    result_data.get(
                        "document_count",
                        0,
                    )
                )

                chunk_count = (
                    result_data.get(
                        "chunk_count",
                        0,
                    )
                )

                st.session_state[
                    "knowledge_success_message"
                ] = (
                    f"{quick_target_path.name} 导入成功。"
                    f"当前共有 {document_count} 个文档、"
                    f"{chunk_count} 个知识块。"
                )

                st.rerun()
# 找到 knowledge 文件夹中的所有 Markdown 文档
knowledge_files = sorted(
    KNOWLEDGE_DIR.glob("*.md")
)


# 展示知识库基本信息
column1, column2 = st.columns(2)

with column1:
    st.metric(
        label="知识文档数量",
        value=len(knowledge_files),
    )

with column2:
    st.write("知识库目录")
    st.code(str(KNOWLEDGE_DIR))


st.subheader("当前知识文档")


if not knowledge_files:
    st.warning("知识库中暂时没有 Markdown 文档。")
else:
    for file_path in knowledge_files:
        content = file_path.read_text(
            encoding="utf-8"
        )

        with st.expander(file_path.name):
            st.caption(
                f"文件大小：{file_path.stat().st_size} 字节"
            )

            st.code(
                content,
                language="markdown",
            )
            with st.form(
                key=f"edit_form_{file_path.name}"
            ):
                edited_content = st.text_area(
                    "编辑文档内容",
                    value=content,
                    height=300,
                    key=(
                        f"edit_content_"
                        f"{file_path.name}"
                    ),
                )

                save_edit_clicked = (
                    st.form_submit_button(
                        "保存修改并更新知识库"
                    )
                )


            if save_edit_clicked:
                edited_content = (
                    edited_content.strip()
                )

                if not edited_content:
                    st.error(
                        "知识文档内容不能为空。"
                    )

                elif not re.search(
                    r"^#\s+.+",
                    edited_content,
                    flags=re.MULTILINE,
                ):
                    st.error(
                        "文档必须包含一级标题，"
                        "例如：# 小丽商城支付规则"
                    )

                elif not re.search(
                    r"^##\s+.+",
                    edited_content,
                    flags=re.MULTILINE,
                ):
                    st.error(
                        "文档必须至少包含一个二级章节，"
                        "例如：## 支持的支付方式"
                    )

                elif (
                    edited_content
                    == content.strip()
                ):
                    st.info(
                        "文档内容没有发生变化。"
                    )

                else:
                    backup_content = content

                    try:
                        file_path.write_text(
                            edited_content + "\n",
                            encoding="utf-8",
                        )

                        api_result = (
                            rebuild_knowledge_from_api()
                        )

                        if not api_result.get(
                            "success"
                        ):
                            raise RuntimeError(
                                api_result.get(
                                    "message",
                                    "后端知识库更新失败",
                                )
                            )

                    except Exception as error:
                        file_path.write_text(
                            backup_content,
                            encoding="utf-8",
                        )

                        # 恢复文件后重新同步旧知识
                        rebuild_knowledge_from_api()

                        st.error(
                            "修改失败，已经恢复原内容："
                            f"{error}"
                        )

                    else:
                        result_data = (
                            api_result.get(
                                "data",
                                {},
                            )
                        )

                        document_count = (
                            result_data.get(
                                "document_count",
                                0,
                            )
                        )

                        chunk_count = (
                            result_data.get(
                                "chunk_count",
                                0,
                            )
                        )

                        st.session_state[
                            "knowledge_success_message"
                        ] = (
                            f"{file_path.name} 修改成功。"
                            f"当前共有 {document_count} 个文档、"
                            f"{chunk_count} 个知识块。"
                        )

                        st.rerun()
            st.divider()

            confirm_delete = st.checkbox(
                "我确认要删除这个知识文档",
                key=f"confirm_delete_{file_path.name}",
            )

            delete_clicked = st.button(
                "删除文档",
                key=f"delete_document_{file_path.name}",
                type="secondary",
            )

            if delete_clicked:
                if not confirm_delete:
                    st.warning(
                        "请先勾选删除确认。"
                    )

                else:
                    backup_content = content

                    try:
                        file_path.unlink()

                        api_result = (
                            rebuild_knowledge_from_api()
                        )

                        if not api_result.get("success"):
                            raise RuntimeError(
                                api_result.get(
                                    "message",
                                    "后端知识库更新失败",
                                )
                            )

                    except Exception as error:
                        file_path.write_text(
                            backup_content,
                            encoding="utf-8",
                        )

                        # 文件恢复后，让后端重新同步恢复后的知识库
                        rebuild_knowledge_from_api()

                        st.error(
                            "删除失败，已经恢复原文件："
                            f"{error}"
                        )

                    else:
                        result_data = api_result.get(
                            "data",
                            {},
                        )

                        document_count = result_data.get(
                            "document_count",
                            0,
                        )

                        chunk_count = result_data.get(
                            "chunk_count",
                            0,
                        )

                        st.session_state[
                            "knowledge_success_message"
                        ] = (
                            f"{file_path.name} 删除成功。"
                            f"当前共有 {document_count} 个文档、"
                            f"{chunk_count} 个知识块。"
                        )

                        st.rerun()