import streamlit as st
from datetime import datetime
from backend_client import (
    send_chat_message,
    get_orders_from_api,
    get_conversations_from_api,
    get_conversation_detail_from_api,
    delete_conversation_from_api,
)




orders_result = (
    get_orders_from_api()
)

if orders_result.get("success"):
    order_list = orders_result.get(
        "data",
        [],
    )
    orders_error = None
else:
    order_list = []
    orders_error = orders_result.get(
        "message",
        "订单列表加载失败。",
    )

ORDERS_BY_ID = {
    order["order_id"]: order#建立以订单号为编号的字典
    for order in order_list
}

def save_session():
    """
    确保当前页面有咨询编号。
    咨询记录由聊天API创建。
    """

    if not st.session_state.current_session:
        st.session_state.current_session = (
            generate_session_name()
        )
#保存会话名字的方法
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

st.set_page_config(
    page_title="小丽商城智能客服",
    page_icon="🎧",  # win+.就有表情
    # 布局
    layout="wide",
    # 控制的是侧边栏的状态
    initial_sidebar_state="expanded",
    menu_items={}

)
st.title("AI智能客服")
if orders_error:
    st.error(orders_error)
st.logo("resourses/logo.png")


#默认欢迎语
WELCOME_MESSAGE = """
您好，我是小丽商城的智能客服欣欣 😊，我可以协助您处理商品咨询、订单、物流、退换货、退款和发票问题。请问您现在遇到了什么问题？
""".strip()



#加载所有会话信息
def load_sessions():
    """
    通过FastAPI加载历史咨询列表。
    """

    result = (
        get_conversations_from_api()
    )

    if not result.get("success"):
        st.error(
            result.get(
                "message",
                "咨询列表加载失败。",
            )
        )
        return []

    conversations = result.get(
        "data",
        [],
    )

    return [
        conversation["conversation_id"]
        for conversation in conversations
    ]
#加载指定会话信息
def load_session(session_name):
    """
    通过FastAPI加载聊天记录和关联订单。
    """

    result = (
        get_conversation_detail_from_api(
            session_name
        )
    )

    if not result.get("success"):
        st.error(
            result.get(
                "message",
                "加载咨询失败。",
            )
        )
        return

    data = result.get(
        "data",
        {},
    )

    st.session_state.messages = (
        data.get("messages", [])
    )

    st.session_state.current_session = (
        session_name
    )

    st.session_state.current_order = (
        data.get("order")
    )

def delete_session(session_name):
    """
    通过FastAPI删除咨询。
    """

    result = (
        delete_conversation_from_api(
            session_name
        )
    )

    if not result.get("success"):
        st.error(
            result.get(
                "message",
                "删除咨询失败。",
            )
        )
        return

    if (
        st.session_state.current_session
        == session_name
    ):
        st.session_state.messages = []
        st.session_state.current_session = (
            generate_session_name()
        )
        st.session_state.current_order = None





#初始化聊天信息
if "messages" not in st.session_state:
    st.session_state.messages = []


#只负责初始化订单
if "current_order" not in st.session_state:
    st.session_state.current_order = None

#初始化咨询
if (
    "current_session" not in st.session_state
    or not st.session_state.current_session
):
    st.session_state.current_session = generate_session_name()

#展示会话名称
st.text(f"当前会话名称：{st.session_state.current_session}")
current_order = st.session_state.current_order

if current_order:
    st.info(
        f"当前关联订单：{current_order['order_id']}\n\n"
        f"商品：{current_order['product_name']}\n\n"
        f"金额：¥{current_order['amount']:.2f}\n\n"
        f"状态：{current_order['status']}\n\n"
        f"物流：{current_order['logistics']}"
    )
else:
    st.info("当前是普通咨询，没有关联具体订单。")

# 展示聊天信息
for messages in st.session_state.messages:
    st.chat_message(messages["role"]).write(messages["content"])

if not st.session_state.messages:
    with st.chat_message("assistant"):st.write(WELCOME_MESSAGE)  # 如果没有聊天记录，显示欢迎语





#上下文管理器，下面的所有都是在左边的侧边栏
with st.sidebar:
    st.subheader("咨询服务台")
    selected_order_id = st.selectbox(
        "请选择本次咨询关联的订单：",
        options=[None, *ORDERS_BY_ID.keys()],
        format_func=lambda order_id: (
            "普通咨询（不关联订单）"
            if order_id is None
            else (
                f"订单 {order_id}｜"
                f"{ORDERS_BY_ID[order_id]["product_name"]}｜"
                f"{ORDERS_BY_ID[order_id]['status']}"
            )
        ),
    )
    if st.button("发起新咨询",width="stretch",icon="📝"):

        # 3. 创建新的空白会话，但暂时不保存
        st.session_state.messages = []
        st.session_state.current_session = generate_session_name()
        if selected_order_id is None:
            st.session_state.current_order = None
        else:
            st.session_state.current_order = ORDERS_BY_ID[
                selected_order_id
            ].copy()


        st.rerun()


    #加载会话
    st.text("咨询记录")
    session_list = load_sessions()
    for session in session_list:
        col1, col2 = st.columns([4,1])#这里的4和1是两个并列的栏分别占左边的多少
        with col1:
            if st.button(session,width="stretch",icon="📄",key=f"load_session_{session}",type="primary" if st.session_state.current_session==session else "secondary"):
                load_session(session)#加载指定会话
                st.rerun()#重新运行当前界面
        with col2:
            if st.button("",width="stretch",icon="❌",key=f"delete_session_{session}"):#这个key可以区分不同的叉叉
                delete_session(session)
                st.rerun()#重新运行当前界面

    #分割线
    st.divider()
    #我觉得客服是可以不要设置名字性格还有年龄什么什么的所以这里全部删除


prompt = st.chat_input(
    "请输入您的需求："
)

if prompt:
    st.chat_message("user").write(
        prompt
    )

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    save_session()

    order_id = None

    if st.session_state.current_order:
        order_id = (
            st.session_state
            .current_order["order_id"]
        )

    api_result = send_chat_message(
        conversation_id=(
            st.session_state.current_session
        ),
        message=prompt,
        order_id=order_id,
    )

    if api_result.get("success"):
        response_data = api_result.get(
            "data",
            {},
        )

        full_message = response_data.get(
            "reply",
            "暂时无法生成回复。",
        )

        knowledge_results = (
            response_data.get(
                "knowledge_results",
                [],
            )
        )

        tool_records = response_data.get(
            "tool_records",
            [],
        )

    else:
        full_message = api_result.get(
            "message",
            "AI客服服务暂时不可用。",
        )

        knowledge_results = []
        tool_records = []

    with st.chat_message("assistant"):
        st.write(full_message)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_message,
        }
    )

    if tool_records:
        with st.expander(
            "本次调用的系统工具"
        ):
            for record in tool_records:
                st.markdown(
                    f"**工具：** "
                    f"{record['name']}"
                )
                st.json(record)

    if knowledge_results:
        with st.expander(
            "本次回答参考的知识库资料"
        ):
            for result in knowledge_results:
                st.markdown(
                    f"**来源：** "
                    f"{result['source']}  \n"
                    f"**章节：** "
                    f"{result['section_title']}  \n"
                    f"**向量相似度：** "
                    f"{result['score']:.4f}"
                )
