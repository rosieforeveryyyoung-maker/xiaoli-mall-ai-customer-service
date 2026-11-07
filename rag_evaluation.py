from rag import (
    get_chroma_collection,
    search_knowledge_with_chroma,
)
from langchain_rag import (
    build_langchain_vector_store,
    search_with_langchain,
)

TEST_CASES = [
    {
        "question": "退款审核通过后多久能到账",
        "expected_section": "退款到账时间",
    },
    {
        "question": "钱什么时候可以退回来",
        "expected_section": "退款到账时间",
    },
    {
        "question": "商品有质量问题怎么办",
        "expected_section": "商品质量问题",
    },
    {
        "question": "普通商品多久可以发货",
        "expected_section": "发货时间",
    },
    {
        "question": "物流超过48小时没有更新怎么办",
        "expected_section": "物流异常",
    },
    {
        "question": "商品发货以后还能修改地址吗",
        "expected_section": "修改收货地址",
    },
    {
        "question": "申请电子发票需要提供什么资料",
        "expected_section": "发票申请",
    },
    {
        "question": "电子发票多久可以开出来",
        "expected_section": "开票时间",
    },
    {
        "question": "发票开具以后还能修改抬头吗",
        "expected_section": "发票修改",
    },
    {
        "question": "今天天气怎么样",
        "expected_section": None,
    },
    {
        "question": "给我讲一个笑话",
        "expected_section": None,
    },
    {
        "question": "怎么学习Python",
        "expected_section": None,
    },
]
def extract_top_result(results):
    """
    提取检索结果第一名的章节和分数。
    """

    if not results:
        return None, None

    return (
        results[0]["section_title"],
        results[0]["score"],
    )

def evaluate_retrieval():
    """
    自动评测知识库检索结果。
    """

    collection = get_chroma_collection()

    passed_count = 0

    for index, test_case in enumerate(
        TEST_CASES,
        start=1,
    ):
        question = test_case["question"]

        expected_section = (
            test_case["expected_section"]
        )

        results = search_knowledge_with_chroma(
            question,
            collection,
            top_k=1,
            min_score=0.55,
        )

        if results:
            actual_section = (
                results[0]["section_title"]
            )

            score = results[0]["score"]

        else:
            actual_section = None
            score = None

        passed = (
            actual_section
            == expected_section
        )

        if passed:
            passed_count += 1

        print("\n" + "=" * 60)
        print(f"测试 {index}")
        print(f"问题：{question}")
        print(f"期望章节：{expected_section}")
        print(f"实际章节：{actual_section}")

        if score is not None:
            print(f"相似度：{score:.4f}")
        else:
            print("相似度：没有合格结果")

        print(
            "结果：",
            "通过" if passed else "失败",
        )

    total_count = len(TEST_CASES)

    accuracy = (
        passed_count / total_count
    )

    print("\n" + "=" * 60)
    print(
        f"通过数量："
        f"{passed_count}/{total_count}"
    )
    print(
        f"检索准确率："
        f"{accuracy:.2%}"
    )

def compare_retrieval_versions():
    """
    对比手写Chroma和LangChain Chroma。
    """

    manual_collection = (
        get_chroma_collection()
    )

    (
        langchain_vector_store,
        langchain_documents,
    ) = build_langchain_vector_store()

    print(
        "LangChain知识文档数：",
        len(langchain_documents),
    )

    manual_passed_count = 0
    langchain_passed_count = 0
    same_result_count = 0

    for index, test_case in enumerate(
        TEST_CASES,
        start=1,
    ):
        question = test_case["question"]

        expected_section = (
            test_case["expected_section"]
        )

        manual_results = (
            search_knowledge_with_chroma(
                question,
                manual_collection,
                top_k=1,
                min_score=0.55,
            )
        )

        langchain_results = (
            search_with_langchain(
                question,
                langchain_vector_store,
                top_k=1,
                min_score=0.55,
            )
        )

        (
            manual_section,
            manual_score,
        ) = extract_top_result(
            manual_results
        )

        (
            langchain_section,
            langchain_score,
        ) = extract_top_result(
            langchain_results
        )

        manual_passed = (
            manual_section
            == expected_section
        )

        langchain_passed = (
            langchain_section
            == expected_section
        )

        same_result = (
            manual_section
            == langchain_section
        )

        if manual_passed:
            manual_passed_count += 1

        if langchain_passed:
            langchain_passed_count += 1

        if same_result:
            same_result_count += 1

        print("\n" + "=" * 60)
        print(f"测试 {index}")
        print(f"问题：{question}")
        print(f"期望章节：{expected_section}")

        print(
            "手写版本章节：",
            manual_section,
        )

        if manual_score is not None:
            print(
                f"手写版本分数："
                f"{manual_score:.4f}"
            )
        else:
            print(
                "手写版本分数：没有合格结果"
            )

        print(
            "LangChain章节：",
            langchain_section,
        )

        if langchain_score is not None:
            print(
                f"LangChain分数："
                f"{langchain_score:.4f}"
            )
        else:
            print(
                "LangChain分数：没有合格结果"
            )

        print(
            "章节是否一致：",
            "是" if same_result else "否",
        )

        print(
            "LangChain测试结果：",
            "通过"
            if langchain_passed
            else "失败",
        )

    total_count = len(TEST_CASES)

    manual_accuracy = (
        manual_passed_count
        / total_count
    )

    langchain_accuracy = (
        langchain_passed_count
        / total_count
    )

    same_result_rate = (
        same_result_count
        / total_count
    )

    print("\n" + "=" * 60)
    print("最终对比结果")

    print(
        f"手写版本："
        f"{manual_passed_count}/{total_count}，"
        f"准确率 {manual_accuracy:.2%}"
    )

    print(
        f"LangChain版本："
        f"{langchain_passed_count}/{total_count}，"
        f"准确率 {langchain_accuracy:.2%}"
    )

    print(
        f"两个版本章节一致："
        f"{same_result_count}/{total_count}，"
        f"一致率 {same_result_rate:.2%}"
    )
if __name__ == "__main__":
    compare_retrieval_versions()