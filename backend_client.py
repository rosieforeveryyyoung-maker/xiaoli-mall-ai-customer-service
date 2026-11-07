import os

import httpx
#这个文件是是前端与FastAPI之间的HTTP客户端。

BACKEND_API_URL = os.environ.get(
    "BACKEND_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

def _request_backend(
    method,
    path,
    timeout=10.0,
):
    """
    向FastAPI发送通用HTTP请求，
    统一处理连接、JSON和错误状态。
    """

    url = (
        f"{BACKEND_API_URL}"
        f"{path}"
    )

    try:
        response = httpx.request(
            method=method,
            url=url,
            timeout=timeout,
            trust_env=False,
        )

    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "后端服务响应超时。",
        }

    except httpx.RequestError:
        return {
            "success": False,
            "message": (
                "无法连接商城后端服务，"
                "请确认FastAPI已经启动。"
            ),
        }

    try:
        response_data = response.json()

    except ValueError:
        return {
            "success": False,
            "message": "后端返回的数据不是有效JSON。",
        }

    if 200 <= response.status_code < 300:
        return response_data

    detail = response_data.get(
        "detail",
        "后端请求失败。",
    )

    if isinstance(detail, dict):
        message = detail.get(
            "message",
            str(detail),
        )
    else:
        message = str(detail)

    return {
        "success": False,
        "message": message,
        "status_code": response.status_code,
    }

def get_order_from_api(order_id):
    """
    通过FastAPI后端查询订单。
    """

    url = (
        f"{BACKEND_API_URL}"
        f"/api/orders/{order_id}"
    )

    try:
        response = httpx.get(
            url,
            timeout=5.0,
            trust_env=False,#这个请求不要使用系统代理，直接访问本机FastAPI。
        )

    except httpx.RequestError:
        return {
            "success": False,
            "message": (
                "暂时无法连接商城后端服务，"
                "请稍后重试。"
            ),
        }

    if response.status_code == 404:
        return {
            "success": False,
            "message": f"没有找到订单{order_id}。",
        }

    if response.status_code != 200:
        return {
            "success": False,
            "message": (
                "商城后端服务返回异常，"
                f"状态码：{response.status_code}"
            ),
        }

    try:
        return response.json()

    except ValueError:
        return {
            "success": False,
            "message": "后端返回的数据不是有效JSON。",
        }

def create_ticket_from_api(
    conversation_id,
    issue_type,
    title,
    description,
    priority,
):
    """
    通过FastAPI后端创建工单。
    """

    url = (
        f"{BACKEND_API_URL}"
        "/api/tickets"
    )

    request_data = {
        "conversation_id": conversation_id,
        "issue_type": issue_type,
        "title": title,
        "description": description,
        "priority": priority,
    }

    try:
        response = httpx.post(
            url,
            json=request_data,
            timeout=5.0,
            trust_env=False,
        )

    except httpx.RequestError:
        return {
            "success": False,
            "message": (
                "暂时无法连接商城后端服务，"
                "工单没有创建，请稍后重试。"
            ),
        }

    try:
        response_data = response.json()

    except ValueError:
        return {
            "success": False,
            "message": "后端返回的数据不是有效JSON。",
        }

    if response.status_code == 201:
        ticket_data = response_data.get(
            "data",
            {},
        )

        return {
            "success": True,
            "message": "人工客服工单创建成功。",
            "ticket_id": ticket_data.get(
                "ticket_id"
            ),
            "status": ticket_data.get(
                "status"
            ),
        }

    if response.status_code == 409:
        detail = response_data.get(
            "detail",
            {},
        )

        if isinstance(detail, dict):
            return {
                "success": False,
                "message": detail.get(
                    "message",
                    "当前咨询已经存在工单。",
                ),
                "ticket": detail.get("ticket"),
            }

        return {
            "success": False,
            "message": str(detail),
        }

    if response.status_code == 422:
        return {
            "success": False,
            "message": "工单参数校验失败。",
            "errors": response_data.get(
                "detail",
                [],
            ),
        }

    if response.status_code == 400:
        return {
            "success": False,
            "message": str(
                response_data.get(
                    "detail",
                    "工单请求不合法。",
                )
            ),
        }

    return {
        "success": False,
        "message": (
            "商城后端服务返回异常，"
            f"状态码：{response.status_code}"
        ),
    }

def send_chat_message(
    conversation_id,
    message,
    order_id=None,
):
    """
    通过FastAPI发送一条客服消息。
    """

    url = (
        f"{BACKEND_API_URL}"
        "/api/chat"
    )

    request_data = {
        "conversation_id": conversation_id,
        "message": message,
        "order_id": order_id,
    }

    try:
        response = httpx.post(
            url,
            json=request_data,
            timeout=90.0,
            trust_env=False,
        )

    except httpx.TimeoutException:
        return {
            "success": False,
            "message": (
                "AI客服响应超时，"
                "请稍后重新发送。"
            ),
        }

    except httpx.RequestError:
        return {
            "success": False,
            "message": (
                "暂时无法连接商城后端服务，"
                "请确认FastAPI已经启动。"
            ),
        }

    try:
        response_data = response.json()

    except ValueError:
        return {
            "success": False,
            "message": "后端返回的数据不是有效JSON。",
        }

    if response.status_code == 200:
        return response_data

    if response.status_code == 422:
        return {
            "success": False,
            "message": "聊天请求参数校验失败。",
            "errors": response_data.get(
                "detail",
                [],
            ),
        }

    detail = response_data.get(
        "detail",
        "AI客服服务暂时不可用。",
    )

    if not isinstance(detail, str):
        detail = str(detail)

    return {
        "success": False,
        "message": detail,
        "status_code": response.status_code,
    }

def get_orders_from_api():
    """
    通过FastAPI获取订单列表。
    """

    return _request_backend(
        method="GET",
        path="/api/orders",
    )

def get_conversations_from_api():
    """
    通过FastAPI获取历史咨询列表。
    """

    return _request_backend(
        method="GET",
        path="/api/conversations",
    )

def get_conversation_detail_from_api(
    conversation_id,
):
    """
    获取咨询的聊天记录和关联订单。
    """

    return _request_backend(
        method="GET",
        path=(
            "/api/conversations/"
            f"{conversation_id}"
        ),
    )

def delete_conversation_from_api(
    conversation_id,
):
    """
    通过FastAPI删除一次咨询。
    """

    return _request_backend(
        method="DELETE",
        path=(
            "/api/conversations/"
            f"{conversation_id}"
        ),
    )
def rebuild_knowledge_from_api():
    """
    请求FastAPI重新构建知识库，
    并清除后端旧的向量库缓存。
    """

    return _request_backend(
        method="POST",
        path="/api/knowledge/rebuild",
        timeout=60.0,
    )