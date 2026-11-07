from uuid import uuid4

from backend_client import (
    rebuild_knowledge_from_api,
)
from knowledge_service import (
    parse_quick_import_text,
)
from langchain_rag import (
    get_formal_langchain_vector_store,
    search_with_langchain,
)
from rag import KNOWLEDGE_DIR


evaluation_results = []


def record_result(
    test_name,
    passed,
    detail="",
):
    """
    保存并打印一条测试结果。
    """

    evaluation_results.append(
        {
            "name": test_name,
            "passed": passed,
            "detail": detail,
        }
    )

    print("\n" + "=" * 60)
    print(f"测试：{test_name}")
    print(f"结果：{'通过' if passed else '失败'}")

    if detail:
        print(f"说明：{detail}")


def rebuild_or_raise():
    """
    请求FastAPI重建知识库。
    失败时抛出异常，中止当前测试步骤。
    """

    result = rebuild_knowledge_from_api()

    if not result.get("success"):
        raise RuntimeError(
            result.get(
                "message",
                "知识库重建失败",
            )
        )

    return result.get("data", {})


def search_current_knowledge(question):
    """
    每次重新打开正式向量库，
    避免继续使用旧的Chroma连接。
    """

    vector_store = (
        get_formal_langchain_vector_store()
    )

    return search_with_langchain(
        question=question,
        vector_store=vector_store,
        top_k=20,
        min_score=-1.0,
    )


def run_parser_evaluation():
    """
    测试一键粘贴文本的解析和校验。
    """

    valid_text = """
文件名：evaluation_policy
# 自动评测规则

## 自动评测章节
这是自动评测内容。
""".strip()

    (
        file_name,
        markdown_content,
        error_message,
    ) = parse_quick_import_text(
        valid_text
    )

    record_result(
        "正确格式能够解析",
        (
            file_name == "evaluation_policy"
            and "## 自动评测章节"
            in markdown_content
            and error_message is None
        ),
    )

    invalid_file_name_text = """
文件名：../dangerous_file
# 自动评测规则

## 自动评测章节
这是自动评测内容。
""".strip()

    (
        _,
        _,
        error_message,
    ) = parse_quick_import_text(
        invalid_file_name_text
    )

    record_result(
        "危险文件名能够被拦截",
        error_message is not None,
        error_message or "",
    )

    missing_section_text = """
文件名：missing_section
# 自动评测规则

这里缺少二级章节。
""".strip()

    (
        _,
        _,
        error_message,
    ) = parse_quick_import_text(
        missing_section_text
    )

    record_result(
        "缺少二级章节能够被拦截",
        error_message is not None,
        error_message or "",
    )


def run_dynamic_knowledge_evaluation():
    """
    测试知识文档新增、修改、删除后，
    Chroma中的检索结果是否同步变化。
    """

    unique_id = uuid4().hex[:8]

    file_stem = (
        f"evaluation_policy_{unique_id}"
    )

    file_name = f"{file_stem}.md"

    file_path = (
        KNOWLEDGE_DIR / file_name
    )

    question = "自动评测暗号是什么？"

    dynamic_test_names = [
        "新增知识后能够检索",
        "修改知识后获得最新内容",
        "删除知识后旧向量消失",
    ]

    recorded_names = set()

    try:
        initial_content = """
# 自动评测临时规则

## 自动评测暗号

本次自动评测暗号是青鸟七号。
""".strip()

        file_path.write_text(
            initial_content + "\n",
            encoding="utf-8",
        )

        rebuild_or_raise()

        search_results = (
            search_current_knowledge(
                question
            )
        )

        create_passed = any(
            result["source"] == file_name
            and "青鸟七号"
            in result["content"]
            for result in search_results
        )

        record_result(
            dynamic_test_names[0],
            create_passed,
            (
                f"临时文件：{file_name}"
            ),
        )

        recorded_names.add(
            dynamic_test_names[0]
        )

        updated_content = """
# 自动评测临时规则

## 自动评测暗号

本次自动评测暗号已经修改为赤兔八号。
""".strip()

        file_path.write_text(
            updated_content + "\n",
            encoding="utf-8",
        )

        rebuild_or_raise()

        search_results = (
            search_current_knowledge(
                question
            )
        )

        test_file_results = [
            result
            for result in search_results
            if result["source"] == file_name
        ]

        update_passed = (
            any(
                "赤兔八号"
                in result["content"]
                for result
                in test_file_results
            )
            and not any(
                "青鸟七号"
                in result["content"]
                for result
                in test_file_results
            )
        )

        record_result(
            dynamic_test_names[1],
            update_passed,
        )

        recorded_names.add(
            dynamic_test_names[1]
        )

        file_path.unlink()

        rebuild_or_raise()

        search_results = (
            search_current_knowledge(
                question
            )
        )

        delete_passed = not any(
            result["source"] == file_name
            for result in search_results
        )

        record_result(
            dynamic_test_names[2],
            delete_passed,
        )

        recorded_names.add(
            dynamic_test_names[2]
        )

    except Exception as error:
        for test_name in dynamic_test_names:
            if test_name not in recorded_names:
                record_result(
                    test_name,
                    False,
                    str(error),
                )

    finally:
        # 即使中途报错，也删除临时文件。
        if file_path.exists():
            file_path.unlink()

        cleanup_result = (
            rebuild_knowledge_from_api()
        )

        if not cleanup_result.get(
            "success"
        ):
            print(
                "\n警告：测试文件已经删除，"
                "但知识库自动清理失败。"
                "请手动调用重建接口。"
            )


def print_summary():
    """
    输出最终评测汇总。
    """

    passed_count = sum(
        result["passed"]
        for result in evaluation_results
    )

    total_count = len(
        evaluation_results
    )

    print("\n" + "=" * 60)
    print("知识库管理自动化评测结果")
    print(
        f"通过：{passed_count}/{total_count}"
    )


if __name__ == "__main__":
    run_parser_evaluation()
    run_dynamic_knowledge_evaluation()
    print_summary()