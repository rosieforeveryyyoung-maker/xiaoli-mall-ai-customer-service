import json

from agent_tools import execute_tool
from database import get_all_tickets


passed_count = 0
test_count = 0
skipped_count = 0


def check_result(
    test_name,
    passed,
    result,
):
    """
    记录并打印一条测试结果。
    """

    global passed_count
    global test_count

    test_count += 1

    print("\n" + "=" * 60)
    print("测试：", test_name)
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )
    print(
        "结果：",
        "通过" if passed else "失败",
    )

    if passed:
        passed_count += 1


# 测试1：查询存在的订单
result = execute_tool(
    "query_order",
    {"order_id": "10004"},
)

check_result(
    "查询存在的订单",
    (
        result.get("success") is True
        and result.get("order", {}).get(
            "order_id"
        ) == "10004"
    ),
    result,
)


# 测试2：查询不存在的订单
result = execute_tool(
    "query_order",
    {"order_id": "99999"},
)

check_result(
    "查询不存在的订单",
    result.get("success") is False,
    result,
)


# 测试3：缺少订单号
result = execute_tool(
    "query_order",
    {},
)

check_result(
    "查询订单时缺少订单号",
    result.get("success") is False,
    result,
)


# 测试4：调用不存在的工具
result = execute_tool(
    "unknown_tool",
    {},
)

check_result(
    "调用不存在的工具",
    result.get("success") is False,
    result,
)


ticket_arguments = {
    "issue_type": "物流问题",
    "title": "物流长时间未更新",
    "description": (
        "订单物流信息超过48小时没有更新，"
        "需要人工客服核查。"
    ),
    "priority": "中",
}


# 测试5：没有用户确认，禁止创建
result = execute_tool(
    "create_support_ticket",
    ticket_arguments,
    runtime_context={
        "conversation_id": "test_conversation",
        "latest_user_message": "请帮我创建工单",
    },
)

check_result(
    "未明确确认时拦截创建工单",
    (
        result.get("success") is False
        and result.get(
            "requires_confirmation"
        ) is True
    ),
    result,
)


# 测试6：确认后仍然缺少必要参数
result = execute_tool(
    "create_support_ticket",
    {
        "issue_type": "物流问题",
    },
    runtime_context={
        "conversation_id": "test_conversation",
        "latest_user_message": "确认创建工单",
    },
)

check_result(
    "创建工单时缺少必要参数",
    (
        result.get("success") is False
        and "缺少必要参数"
        in result.get("message", "")
    ),
    result,
)


# 测试7：已有工单时禁止重复创建
existing_tickets = get_all_tickets()

if existing_tickets:
    existing_conversation_id = (
        existing_tickets[0][
            "conversation_id"
        ]
    )

    result = execute_tool(
        "create_support_ticket",
        ticket_arguments,
        runtime_context={
            "conversation_id": (
                existing_conversation_id
            ),
            "latest_user_message": (
                "确认创建工单"
            ),
        },
    )

    check_result(
        "已有工单时禁止重复创建",
        (
                result.get("success") is False
                and result.get("ticket") is not None
        ),
        result,
    )

else:
    skipped_count += 1
    print("\n没有已有工单，跳过防重复测试。")


print("\n" + "=" * 60)
print("Agent工具评测结果")
print(
    f"通过：{passed_count}/{test_count}"
)
print(f"跳过：{skipped_count}")