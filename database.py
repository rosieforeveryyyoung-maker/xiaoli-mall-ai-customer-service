import sqlite3#这是python自带的数据库工具
from pathlib import Path#为了避免以后从其他目录启动时生成另一个 shop.db，需要使用文件自己的位置。


DATABASE_PATH = Path(__file__).with_name("shop.db")
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)#表示连接 shop.db。如果文件不存在，SQLite 会自动创建。
    connection.row_factory = sqlite3.Row#让查询结果可以按照字段名读取，而不只是按照位置读取。
    connection.execute("PRAGMA foreign_keys = ON")
    #这句话表示启用表之间的关联检查。
#例如，消息必须属于一个真实存在的咨询，不能随便写一个不存在的咨询编号。
    return connection

def init_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                logistics TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO orders (
                order_id,
                product_name,
                amount,
                status,
                logistics
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "10001",
                    "小丽降噪蓝牙耳机",
                    299.00,
                    "待发货",
                    "商家暂未发货",
                ),
                (
                    "10002",
                    "小丽机械键盘",
                    399.00,
                    "运输中",
                    "商品已到达广州转运中心",
                ),
                (
                    "10003",
                    "27英寸高清显示器",
                    1299.00,
                    "已完成",
                    "商品已于2026-10-12签收",
                ),
                (
                    "10004",
                    "小丽智能手表",
                    599.00,
                    "待收货",
                    "商品正在派送中",
                ),
            ],


        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                order_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            )
            """
        )#咨询
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
                    ON DELETE CASCADE
            )
            """
        )#最后一句表示删除一条咨询时，属于它的所有消息一起删除，避免留下没有归属的消息。
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL UNIQUE,
                issue_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT '中',
                status TEXT NOT NULL DEFAULT '待处理',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
                    ON DELETE CASCADE
            )
            """
        )#创建ticket表，是用来弄工单的，就是处理不了的问题就转人工


def get_all_orders():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                order_id,
                product_name,
                amount,
                status,
                logistics
            FROM orders
            ORDER BY order_id
            """
        ).fetchall()

#获取全部订单并且转换成Python字典
    return [dict(row) for row in rows]

def get_order_by_id(order_id):
    """
    根据订单号查询一条订单。
    找到时返回订单字典，找不到时返回None。
    """

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                order_id,
                product_name,
                amount,
                status,
                logistics
            FROM orders
            WHERE order_id = ?
            """,
            (str(order_id),),
        ).fetchone()

    if row is None:
        return None

    return dict(row)

def create_conversation(conversation_id, order_id=None):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations (
                conversation_id,
                order_id
            )
            VALUES (?, ?)
            """,
            (conversation_id, order_id),
        )#咨询

def save_message(conversation_id, role, content):
    if role not in ("user", "assistant"):
        raise ValueError("消息角色只能是 user 或 assistant")

    with get_connection() as connection:
        connection.execute(#保存消息
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (conversation_id, role, content),
        )

        connection.execute(#更新咨询时间
            """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )

def get_all_conversations():#查询有消息的咨询
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                conversation_id,
                order_id,
                created_at,
                updated_at
            FROM conversations
            WHERE EXISTS (
                SELECT 1
                FROM messages
                WHERE messages.conversation_id =
                      conversations.conversation_id
            )
            ORDER BY updated_at DESC
            """
        ).fetchall()#表示只显示至少有一条信息的咨询
    return [dict(row) for row in rows]

def get_conversation_messages(conversation_id):#查询某次咨询的全部消息
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                role,
                content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY message_id
            """,
            (conversation_id,),
        ).fetchall()

    return [dict(row) for row in rows]



def get_conversation_order(conversation_id):#查询咨询关联的订单
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                orders.order_id,
                orders.product_name,
                orders.amount,
                orders.status,
                orders.logistics
            FROM conversations
            LEFT JOIN orders
                ON conversations.order_id = orders.order_id
            WHERE conversations.conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()

    if row is None or row["order_id"] is None:
        return None

    return dict(row)

#删除咨询函数
def delete_conversation_data(
    conversation_id,
):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM conversations
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )

    return cursor.rowcount > 0

def get_all_messages():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                message_id,
                conversation_id,
                role,
                content,
                created_at
            FROM messages
            ORDER BY message_id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]

def create_ticket(
    conversation_id,
    issue_type,
    title,
    description,
    priority,
):
    if priority not in ("低", "中", "高"):
        raise ValueError("工单优先级只能是低、中或高")

    with get_connection() as connection:
        existing_ticket = connection.execute(
            """
            SELECT ticket_id
            FROM tickets
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()

        if existing_ticket:
            return None

        cursor = connection.execute(
            """
            INSERT INTO tickets (
                conversation_id,
                issue_type,
                title,
                description,
                priority
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                issue_type,
                title,
                description,
                priority,
            ),
        )

        return cursor.lastrowid

def get_all_tickets():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                tickets.ticket_id,
                tickets.conversation_id,
                conversations.order_id,
                tickets.issue_type,
                tickets.title,
                tickets.description,
                tickets.priority,
                tickets.status,
                tickets.created_at,
                tickets.updated_at
            FROM tickets
            JOIN conversations
                ON tickets.conversation_id =
                   conversations.conversation_id
            ORDER BY tickets.created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows] #这里用join把订单和工单关联
def get_ticket_by_conversation(conversation_id):#获取工单
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                ticket_id,
                conversation_id,
                issue_type,
                title,
                description,
                priority,
                status,
                created_at,
                updated_at
            FROM tickets
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)

def update_ticket_status(ticket_id, new_status):#更新状态
    allowed_statuses = (
        "待处理",
        "处理中",
        "已解决",
        "已关闭",
    )

    if new_status not in allowed_statuses:
        raise ValueError("不支持这个工单状态")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tickets
            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
            """,
            (new_status, ticket_id),
        )

    return cursor.rowcount > 0
if __name__ == "__main__":
    init_database()

    orders = get_all_orders()

    for order in orders:
        print(
            order["order_id"],
            order["product_name"],
            order["status"],
        )