import sqlite3
from typing import Literal
from chat_service import (
    generate_customer_reply,
    clear_knowledge_vector_store_cache,
)
from rag import rebuild_knowledge_base
from pydantic import (
    BaseModel,
    Field,
)

from fastapi import (
    FastAPI,
    HTTPException,
)

from database import (
    init_database,
    get_order_by_id,
    create_ticket,
    get_ticket_by_conversation,
    create_conversation,
    save_message,
    get_all_orders,
    get_all_conversations,
    get_conversation_messages,
    get_conversation_order,
    delete_conversation_data,
)

class TicketCreateRequest(BaseModel):
    """
    创建工单接口接收的JSON数据。
    """

    conversation_id: str = Field(
        min_length=1,
    )

    issue_type: Literal[
        "物流问题",
        "退款问题",
        "退换货问题",
        "商品问题",
        "发票问题",
        "其他问题",
    ]

    title: str = Field(
        min_length=2,
        max_length=100,
    )

    description: str = Field(
        min_length=5,
        max_length=1000,
    )

    priority: Literal[
        "低",
        "中",
        "高",
    ] = "中"

class ChatRequest(BaseModel):
    """
    客服聊天接口接收的数据。
    """

    conversation_id: str = Field(
        min_length=1,
        max_length=100,
    )

    message: str = Field(
        min_length=1,
        max_length=2000,
    )

    order_id: str | None = None

init_database()


app = FastAPI(
    title="小丽商城智能客服API",
    description=(
        "为商城客服前端提供订单、"
        "知识库、Agent和工单接口。"
    ),
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """
    检查后端服务是否正常运行。
    """

    return {
        "status": "ok",
        "service": "xiaoli-customer-service",
    }

@app.post("/api/knowledge/rebuild")
def rebuild_knowledge_api():
    """
    重新读取知识文档、生成向量、
    同步Chroma并清除旧的检索缓存。
    """

    try:
        (
            collection,
            document_count,
            chunk_count,
        ) = rebuild_knowledge_base()

        clear_knowledge_vector_store_cache()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "知识库重建失败："
                f"{error}"
            ),
        ) from error

    return {
        "success": True,
        "data": {
            "document_count": document_count,
            "chunk_count": chunk_count,
        },
        "message": "知识库重建成功。",
    }

@app.get("/api/orders")
def read_orders():
    """
    查询商城订单列表。
    """

    orders = get_all_orders()

    return {
        "success": True,
        "data": orders,
    }

@app.get("/api/orders/{order_id}")
def read_order(order_id: str):
    """
    根据订单号查询订单。
    """

    order = get_order_by_id(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="没有找到这个订单。",
        )

    return {
        "success": True,
        "data": order,
    }

#增加工单接口
@app.post(
    "/api/tickets",
    status_code=201,
)
def create_ticket_api(
    request: TicketCreateRequest,
):
    """
    为一次客服咨询创建工单。
    """

    existing_ticket = (
        get_ticket_by_conversation(
            request.conversation_id
        )
    )

    if existing_ticket:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "当前咨询已经存在工单。"
                ),
                "ticket": existing_ticket,
            },
        )

    try:
        ticket_id = create_ticket(
            conversation_id=(
                request.conversation_id
            ),
            issue_type=request.issue_type,
            title=request.title,
            description=request.description,
            priority=request.priority,
        )

    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "咨询编号不存在，"
                "或数据关联不合法。"
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    if ticket_id is None:
        raise HTTPException(
            status_code=409,
            detail="当前咨询已经存在工单。",
        )

    return {
        "success": True,
        "data": {
            "ticket_id": ticket_id,
            "conversation_id": (
                request.conversation_id
            ),
            "status": "待处理",
        },
    }

@app.post("/api/chat")
def chat_api(request: ChatRequest):
    """
    接收用户消息，调用RAG和Agent，
    返回智能客服回答。
    """

    try:
        create_conversation(
            conversation_id=(
                request.conversation_id
            ),
            order_id=request.order_id,
        )

        save_message(
            request.conversation_id,
            "user",
            request.message,
        )

    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "订单编号不存在，"
                "或咨询数据关联不合法。"
            ),
        ) from error

    try:
        result = generate_customer_reply(
            conversation_id=(
                request.conversation_id
            ),
            message=request.message,
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI客服服务暂时不可用，"
                "请稍后重试。"
            ),
        ) from error

    save_message(
        request.conversation_id,
        "assistant",
        result["reply"],
    )

    return {
        "success": True,
        "data": result,
    }

@app.get("/api/conversations")
def read_conversations():
    """
    查询有聊天消息的咨询列表。
    """

    conversations = (
        get_all_conversations()
    )

    return {
        "success": True,
        "data": conversations,
    }

@app.get(
    "/api/conversations/{conversation_id}"
)
def read_conversation_detail(
    conversation_id: str,
):
    """
    查询一次咨询的聊天记录和关联订单。
    """

    messages = (
        get_conversation_messages(
            conversation_id
        )
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail="没有找到这次咨询。",
        )

    order = get_conversation_order(
        conversation_id
    )

    return {
        "success": True,
        "data": {
            "conversation_id": (
                conversation_id
            ),
            "messages": messages,
            "order": order,
        },
    }

@app.delete(
    "/api/conversations/{conversation_id}"
)
def delete_conversation(
    conversation_id: str,
):
    """
    删除一次咨询及其关联消息和工单。
    """

    deleted = delete_conversation_data(
        conversation_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="没有找到这次咨询。",
        )

    return {
        "success": True,
        "message": "咨询已经删除。",
    }