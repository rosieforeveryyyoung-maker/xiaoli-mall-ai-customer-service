import json

from backend_client import (
    get_order_from_api,
    create_ticket_from_api,
)


AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": (
                "根据订单号查询小丽商城订单的"
                "商品、金额、状态和物流信息。"
                "当用户询问具体订单时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": (
                            "需要查询的商城订单号，"
                            "例如10004。"
                        ),
                    }
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": (
                "为当前客服咨询创建人工处理工单。"
                "只有用户明确回复“确认创建工单”后"
                "才能调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "enum": [
                            "物流问题",
                            "退款问题",
                            "退换货问题",
                            "商品问题",
                            "发票问题",
                            "其他问题",
                        ],
                        "description": "工单问题类型。",
                    },
                    "title": {
                        "type": "string",
                        "description": (
                            "简短、清晰的工单标题。"
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "用户遇到的问题和必要背景。"
                        ),
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["低", "中", "高"],
                        "description": "工单处理优先级。",
                    },
                },
                "required": [
                    "issue_type",
                    "title",
                    "description",
                    "priority",
                ],
                "additionalProperties": False,
            },
        },
    },
]



def query_order(order_id):
    """
    通过FastAPI后端查询订单。
    """

    api_result = get_order_from_api(
        order_id
    )

    if not api_result.get("success"):
        return api_result

    return {
        "success": True,
        "order": api_result["data"],
    }


def create_support_ticket(
    conversation_id,
    issue_type,
    title,
    description,
    priority,
):
    """
    通过FastAPI后端创建人工客服工单。
    """

    return create_ticket_from_api(
        conversation_id=conversation_id,
        issue_type=issue_type,
        title=title,
        description=description,
        priority=priority,
    )#把这些职责都交给fastapi

def execute_tool(
    tool_name,
    arguments,
    runtime_context=None,
):
    """
    根据工具名称，将调用分发给对应的Python函数。
    """
    runtime_context = runtime_context or {}
    if tool_name == "query_order":
        order_id = arguments.get("order_id")

        if not order_id:
            return {
                "success": False,
                "message": "缺少订单号，无法查询。",
            }

        return query_order(order_id)
    if tool_name == "create_support_ticket":
        latest_user_message = (
            runtime_context.get(
                "latest_user_message",
                "",
            )
        )

        if (
            "确认创建工单"
            not in latest_user_message
        ):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": (
                    "创建工单前必须获得用户确认。"
                    "请先向用户展示工单摘要，"
                    "并让用户明确回复：确认创建工单"
                ),
            }

        conversation_id = (
            runtime_context.get(
                "conversation_id"
            )
        )

        required_fields = (
            "issue_type",
            "title",
            "description",
            "priority",
        )

        missing_fields = [
            field
            for field in required_fields
            if not arguments.get(field)
        ]

        if missing_fields:
            return {
                "success": False,
                "message": (
                    "创建工单缺少必要参数："
                    + ", ".join(missing_fields)
                ),
            }

        return create_support_ticket(
            conversation_id=conversation_id,
            issue_type=arguments["issue_type"],
            title=arguments["title"],
            description=arguments["description"],
            priority=arguments["priority"],
        )
    return {
        "success": False,
        "message": f"不支持的工具：{tool_name}",
    }


if __name__ == "__main__":
    result = execute_tool(
        "query_order",
        {"order_id": "10004"},
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )