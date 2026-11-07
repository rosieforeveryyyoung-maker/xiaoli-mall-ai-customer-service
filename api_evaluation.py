import json

from fastapi.testclient import TestClient

from api import app
from database import get_all_tickets


client = TestClient(app)

passed_count = 0
test_count = 0
skipped_count = 0


def check_result(
    test_name,
    passed,
    status_code,
    response_data,
):
    global passed_count
    global test_count

    test_count += 1

    print("\n" + "=" * 60)
    print("测试：", test_name)
    print("HTTP状态码：", status_code)
    print(
        json.dumps(
            response_data,
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


# 测试1：健康检查
response = client.get("/health")
response_data = response.json()

check_result(
    "后端健康检查",
    (
        response.status_code == 200
        and response_data.get("status")
        == "ok"
    ),
    response.status_code,
    response_data,
)


# 测试2：查询存在的订单
response = client.get(
    "/api/orders/10004"
)
response_data = response.json()

check_result(
    "查询存在的订单",
    (
        response.status_code == 200
        and response_data.get(
            "data",
            {},
        ).get("order_id") == "10004"
    ),
    response.status_code,
    response_data,
)


# 测试3：查询不存在的订单
response = client.get(
    "/api/orders/99999"
)
response_data = response.json()

check_result(
    "查询不存在的订单",
    response.status_code == 404,
    response.status_code,
    response_data,
)


# 测试4：非法优先级
response = client.post(
    "/api/tickets",
    json={
        "conversation_id": "test",
        "issue_type": "物流问题",
        "title": "物流异常",
        "description": (
            "物流超过48小时没有更新"
        ),
        "priority": "非常紧急",
    },
)
response_data = response.json()

check_result(
    "非法工单优先级被拦截",
    response.status_code == 422,
    response.status_code,
    response_data,
)


# 测试5：不存在的咨询编号
response = client.post(
    "/api/tickets",
    json={
        "conversation_id": (
            "conversation_not_exists"
        ),
        "issue_type": "物流问题",
        "title": "物流异常",
        "description": (
            "物流超过48小时没有更新"
        ),
        "priority": "中",
    },
)
response_data = response.json()

check_result(
    "不存在的咨询不能创建工单",
    response.status_code == 400,
    response.status_code,
    response_data,
)


# 测试6：重复工单
existing_tickets = get_all_tickets()

if existing_tickets:
    conversation_id = (
        existing_tickets[0][
            "conversation_id"
        ]
    )

    response = client.post(
        "/api/tickets",
        json={
            "conversation_id": (
                conversation_id
            ),
            "issue_type": "物流问题",
            "title": "重复工单测试",
            "description": (
                "验证同一咨询不能重复创建工单"
            ),
            "priority": "中",
        },
    )
    response_data = response.json()

    check_result(
        "已有工单时返回冲突",
        response.status_code == 409,
        response.status_code,
        response_data,
    )

else:
    skipped_count += 1
    print(
        "\n没有已有工单，"
        "跳过重复工单测试。"
    )


response = client.get(
    "/api/orders"
)
response_data = response.json()

orders = response_data.get(
    "data",
    [],
)

check_result(
    "查询订单列表",
    (
        response.status_code == 200
        and response_data.get(
            "success"
        ) is True
        and len(orders) >= 4
    ),
    response.status_code,
    response_data,
)
response = client.get(
    "/api/conversations"
)
response_data = response.json()

conversations = response_data.get(
    "data",
    [],
)

check_result(
    "查询咨询列表",
    (
        response.status_code == 200
        and response_data.get(
            "success"
        ) is True
    ),
    response.status_code,
    response_data,
)
if conversations:
    conversation_id = (
        conversations[0][
            "conversation_id"
        ]
    )

    response = client.get(
        "/api/conversations/"
        f"{conversation_id}"
    )
    response_data = response.json()

    detail_data = response_data.get(
        "data",
        {},
    )

    check_result(
        "查询咨询详情",
        (
            response.status_code == 200
            and detail_data.get(
                "conversation_id"
            ) == conversation_id
            and isinstance(
                detail_data.get(
                    "messages"
                ),
                list,
            )
        ),
        response.status_code,
        response_data,
    )

else:
    skipped_count += 1
    print(
        "\n没有历史咨询，"
        "跳过咨询详情测试。"
    )

response = client.delete(
    "/api/conversations/"
    "conversation_not_exists_for_test"
)
response_data = response.json()

check_result(
    "删除不存在的咨询",
    response.status_code == 404,
    response.status_code,
    response_data,
)

print("\n" + "=" * 60)
print("FastAPI接口评测结果")
print(
    f"通过：{passed_count}/{test_count}"
)
print(f"跳过：{skipped_count}")