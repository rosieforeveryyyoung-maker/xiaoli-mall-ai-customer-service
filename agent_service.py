import json

from agent_tools import (
    AGENT_TOOLS,
    execute_tool,
)


def run_agent(
    client,
    model,
    messages,
    runtime_context=None,
    max_tool_rounds=3,
):
    """
    循环执行大模型请求和工具调用，
    直到模型生成最终回答，
    或达到最大工具调用轮数。
    """

    working_messages = list(messages)
    tool_records = []
    tool_rounds = 0

    while True:
        response = client.chat.completions.create(
            model=model,
            messages=working_messages,
            tools=AGENT_TOOLS,
            tool_choice="auto",
        )

        assistant_message = (
            response.choices[0].message
        )

        working_messages.append(
            assistant_message
        )

        if not assistant_message.tool_calls:
            return (
                assistant_message.content or
                "暂时无法生成回复。",
                tool_records,
            )

        if tool_rounds >= max_tool_rounds:
            return (
                "工具调用次数过多，"
                "本次请求已停止，请联系人工客服。",
                tool_records,
            )

        tool_rounds += 1

        for tool_call in (
            assistant_message.tool_calls
        ):
            tool_name = (
                tool_call.function.name
            )

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )

                if not isinstance(
                    arguments,
                    dict,
                ):
                    raise ValueError(
                        "工具参数必须是JSON对象"
                    )

                tool_result = execute_tool(
                    tool_name,
                    arguments,
                    runtime_context=runtime_context,
                )

            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as error:
                arguments = {}

                tool_result = {
                    "success": False,
                    "message": (
                        f"工具调用失败：{error}"
                    ),
                }

            tool_records.append(
                {
                    "round": tool_rounds,
                    "name": tool_name,
                    "arguments": arguments,
                    "result": tool_result,
                }
            )

            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": (
                        tool_call.id
                    ),
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                    ),
                }
            )