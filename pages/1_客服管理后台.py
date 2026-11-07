import streamlit as st

from database import (
    init_database,
    get_all_orders,
    get_all_conversations,
    get_all_messages,
    get_conversation_messages,
    get_conversation_order,
    create_ticket,
    get_all_tickets,
    get_ticket_by_conversation,
    update_ticket_status,
)
from rag import (
    load_knowledge_documents,
    split_documents,
    get_chroma_collection,
    rebuild_knowledge_base,
)


st.set_page_config(
    page_title="小丽商城客服管理后台",
    page_icon="📊",
    layout="wide",
)

init_database()

orders = get_all_orders()
conversations = get_all_conversations()
messages = get_all_messages()
tickets = get_all_tickets()


st.title("小丽商城客服管理后台")
st.caption("查看商城订单、有效客服咨询和聊天消息")


col1, col2, col3, col4 = st.columns(4)

col1.metric("订单数量", len(orders))
col2.metric("有效咨询数量", len(conversations))
col3.metric("消息数量", len(messages))
col4.metric("工单数量", len(tickets))

st.divider()
st.subheader("知识库管理")

knowledge_documents = (
    load_knowledge_documents()
)

knowledge_chunks = split_documents(
    knowledge_documents
)

knowledge_collection = (
    get_chroma_collection()
)

document_count = len(
    knowledge_documents
)

chunk_count = len(
    knowledge_chunks
)

if st.button(
    "重新建立知识索引",
    type="primary",
    key="rebuild_knowledge_index",
):
    try:
        with st.spinner(
            "正在读取文档、生成向量并更新Chroma……"
        ):
            (
                knowledge_collection,
                document_count,
                chunk_count,
            ) = rebuild_knowledge_base()

        st.success(
            "知识索引重新建立成功。"
        )

    except Exception as error:
        st.error(
            f"知识索引更新失败：{error}"
        )

record_count = (
    knowledge_collection.count()
)

knowledge_col1, knowledge_col2, knowledge_col3 = (
    st.columns(3)
)

knowledge_col1.metric(
    "知识文档数",
    document_count,
)

knowledge_col2.metric(
    "知识块数",
    chunk_count,
)

knowledge_col3.metric(
    "Chroma记录数",
    record_count,
)

if chunk_count == record_count:
    st.success(
        "Markdown知识块与Chroma记录数量一致。"
    )
else:
    st.warning(
        "知识块数量与Chroma记录数量不一致，"
        "请重新建立知识索引。"
    )

st.caption(
    "修改knowledge目录中的Markdown政策后，"
    "请点击“重新建立知识索引”。"
)

st.divider()
st.subheader("咨询详情")

if not conversations:
    st.info("目前还没有产生有效咨询。")

else:
    conversation_by_id = {
        conversation["conversation_id"]: conversation
        for conversation in conversations
    }

    selected_conversation_id = st.selectbox(
        "请选择要查看的咨询：",
        options=list(conversation_by_id.keys()),
        format_func=lambda conversation_id: (
            f"{conversation_id}｜"
            f"订单："
            f"{conversation_by_id[conversation_id]['order_id'] or '未关联'}"
        ),
    )

    selected_order = get_conversation_order(
        selected_conversation_id
    )

    selected_messages = get_conversation_messages(
        selected_conversation_id
    )

    if selected_order:
        st.info(
            f"关联订单：{selected_order['order_id']}\n\n"
            f"商品：{selected_order['product_name']}\n\n"
            f"金额：¥{selected_order['amount']:.2f}\n\n"
            f"状态：{selected_order['status']}\n\n"
            f"物流：{selected_order['logistics']}"
        )
    else:
        st.info("这是普通咨询，没有关联订单。")

    st.caption(
        f"本次咨询共有 {len(selected_messages)} 条消息"
    )

    for message in selected_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    st.divider()
    st.subheader("工单处理")

    existing_ticket = get_ticket_by_conversation(
        selected_conversation_id
    )

    if existing_ticket:
        st.success(
            f"本次咨询已创建工单："
            f"#{existing_ticket['ticket_id']}"
        )

        ticket_col1, ticket_col2, ticket_col3 = st.columns(3)

        ticket_col1.markdown(
            f"**问题类型：** {existing_ticket['issue_type']}"
        )

        ticket_col2.markdown(
            f"**优先级：** {existing_ticket['priority']}"
        )

        ticket_col3.markdown(
            f"**状态：** {existing_ticket['status']}"
        )

        st.markdown(
            f"**标题：** {existing_ticket['title']}"
        )

        st.markdown(
            f"**问题描述：** {existing_ticket['description']}"
        )
        status_options = [
            "待处理",
            "处理中",
            "已解决",
            "已关闭",
        ]

        current_status_index = status_options.index(
            existing_ticket["status"]
        )

        with st.form(
            key=f"update_ticket_{existing_ticket['ticket_id']}"
        ):
            new_status = st.selectbox(
                "修改工单状态",
                options=status_options,
                index=current_status_index,
            )

            update_submitted = st.form_submit_button(
                "保存工单状态"
            )

            if update_submitted:
                if new_status == existing_ticket["status"]:
                    st.info("工单状态没有发生变化。")

                else:
                    updated = update_ticket_status(
                        existing_ticket["ticket_id"],
                        new_status,
                    )

                    if updated:
                        st.success("工单状态更新成功。")
                        st.rerun()
                    else:
                        st.error("没有找到需要更新的工单。")

    else:
        st.info(
            "如果AI无法解决本次咨询，可以创建工单，"
            "转交人工客服继续处理。"
        )

        with st.form(
                key=f"create_ticket_{selected_conversation_id}"
        ):
            issue_type = st.selectbox(
                "问题类型",
                options=[
                    "退款问题",
                    "退换货问题",
                    "物流异常",
                    "商品问题",
                    "支付问题",
                    "发票问题",
                    "用户投诉",
                    "其他问题",
                ],
            )

            title = st.text_input(
                "工单标题",
                placeholder="例如：订单长时间未发货",
            )

            description = st.text_area(
                "问题描述",
                placeholder=(
                    "请填写问题经过，以及需要人工客服"
                    "继续处理的事项。"
                ),
            )

            priority = st.selectbox(
                "优先级",
                options=["低", "中", "高"],
                index=1,
            )

            submitted = st.form_submit_button(
                "创建工单",
                type="primary",
            )

            if submitted:
                if not title.strip():
                    st.error("请填写工单标题。")

                elif not description.strip():
                    st.error("请填写问题描述。")

                else:
                    ticket_id = create_ticket(
                        conversation_id=selected_conversation_id,
                        issue_type=issue_type,
                        title=title.strip(),
                        description=description.strip(),
                        priority=priority,
                    )

                    if ticket_id is None:
                        st.warning("本次咨询已经存在工单。")
                    else:
                        st.success(
                            f"工单 #{ticket_id} 创建成功。"
                        )
                        st.rerun()
st.subheader("订单数据")

st.dataframe(
    orders,
    use_container_width=True,
    hide_index=True,
)


st.subheader("有效咨询记录")

st.dataframe(
    conversations,
    use_container_width=True,
    hide_index=True,
)


st.subheader("聊天消息")

st.dataframe(
    messages,
    use_container_width=True,
    hide_index=True,
)

st.subheader("工单数据")

if tickets:
    st.dataframe(
        tickets,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("目前还没有工单。")