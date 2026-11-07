from pathlib import Path

from langchain_core.documents import Document
from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma

from rag import (
    load_knowledge_documents,
    split_documents,
    CHROMA_DIR,
    CHROMA_COLLECTION_NAME,
)


LANGCHAIN_CHROMA_DIR = (
    Path(__file__).with_name(
        "chroma_langchain_db"
    )
)

LANGCHAIN_COLLECTION_NAME = (
    "xiaoli_mall_langchain_test"
)

EMBEDDING_MODEL_NAME = (
    "BAAI/bge-small-zh-v1.5"
)


#添加适配器类
class FastEmbedAdapter(Embeddings):
    """
    把FastEmbed提供的方法，
    它是LangChain和FastEmbed之间的翻译员)
    转换成LangChain要求的Embedding接口。
    """

    def __init__(self, model_name: str, cache_dir: str):
        self.model = TextEmbedding(
            model_name=model_name,
            cache_dir=cache_dir,
        )#创建模型

    def embed_documents(#负责把知识文档转换成向量。
        self,
        texts: list[str],
    ) -> list[list[float]]:
        vectors = self.model.passage_embed(texts)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:#负责把用户问题转换成向量。
        vectors = self.model.query_embed(text)
        return next(iter(vectors)).tolist()
#把字典转成LangChain Document
def create_langchain_documents():
    """
    读取商城政策，将知识块转换成
    LangChain的Document对象。
    """

    raw_documents = (
        load_knowledge_documents()
    )

    chunks = split_documents(
        raw_documents
    )

    langchain_documents = []

    for chunk in chunks:
        document = Document(
            page_content=chunk["content"],
            metadata={
                "source": chunk["source"],
                "document_title": (
                    chunk["document_title"]
                ),
                "section_title": (
                    chunk["section_title"]
                ),
            },
        )

        langchain_documents.append(
            document
        )

    return langchain_documents
#创建Embedding组件这个函数本身不生成向量，只是准备好一个可以随时生成向量的工具。
def create_langchain_embeddings():
    """
    创建符合LangChain统一接口的
    FastEmbed组件。
    """

    return FastEmbedAdapter(
        model_name=EMBEDDING_MODEL_NAME,
        cache_dir="C:/Temp/fastembed_cache",
    )

#这是正式客服使用的函数
def get_formal_langchain_vector_store():
    """
    使用LangChain打开正式的商城知识库。
    不重新建立知识库，只连接已有的chroma_db。
    创建FastEmbedAdapter
        ↓
找到正式chroma_db
        ↓
找到xiaoli_mall_knowledge集合
        ↓
返回LangChain Chroma对象
    """

    embeddings = create_langchain_embeddings()

    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        relevance_score_fn=lambda distance: 1 - distance,
    )

#建立LangChain版Chroma
def build_langchain_vector_store():
    """
    将LangChain Document写入测试用Chroma。
    """

    documents = (
        create_langchain_documents()
    )

    embeddings = (
        create_langchain_embeddings()
    )

    vector_store = Chroma(
        collection_name=(
            LANGCHAIN_COLLECTION_NAME
        ),
        embedding_function=embeddings,
        persist_directory=str(
            LANGCHAIN_CHROMA_DIR
        ),
        collection_configuration={
            "hnsw": {
                "space": "cosine",
            }
        },
        relevance_score_fn=(
            lambda distance: 1 - distance
        ),
    )

    vector_store.reset_collection()

    ids = [
        f"langchain_chunk_{index}"
        for index in range(
            len(documents)
        )
    ]

    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )

    return vector_store, documents

#它负责真正检索知识
def search_with_langchain(
    question,
    vector_store,
    top_k=3,
    min_score=0.55,
):
    """
    使用LangChain版Chroma进行检索。
    """

    search_results = (
        vector_store.similarity_search_with_relevance_scores(
            question,
            k=top_k,
         )#"""用户问题
        #     → 调用FastEmbedAdapter.embed_query()
        #     → 变成问题向量
        #     → 去Chroma比较知识向量
        #     → 返回最相似的Document和分数
        #     """
    )

    filtered_results = []

    for document, score in search_results:
        if score < min_score:
            continue

        filtered_results.append(
            {
                "content": (
                    document.page_content
                ),
                "source": document.metadata[
                    "source"
                ],
                "section_title": (
                    document.metadata[
                        "section_title"
                    ]
                ),
                "score": float(score),
            }
        )

    return filtered_results

def build_langchain_context(
    question,
    vector_store,
    top_k=2,
    min_score=0.55,
):
    """
    检索知识库，并将结果整理成
    大模型可以阅读的上下文。
    """

    results = search_with_langchain(
        question,
        vector_store,
        top_k=top_k,
        min_score=min_score,
    )

    if not results:
        return (
            """
知识库中没有检索到与用户问题相关的政策资料。
如果问题涉及商城规则，不要自行编造，应明确说明暂时无法确认。
""".strip(),
            [],
        )

    context_parts = []

    for result in results:
        context_parts.append(
            f"""
[资料来源：{result["source"]}]
[资料章节：{result["section_title"]}]
{result["content"]}
""".strip()
        )

    knowledge_text = "\n\n".join(context_parts)

    context = f"""
下面是从小丽商城知识库中检索到的参考资料：

{knowledge_text}

回答规则：
1. 涉及商城政策时，应优先依据以上资料回答；
2. 资料中没有说明的信息，不得自行编造；
3. 不要把检索分数告诉用户；
4. 必要时可以告诉用户参考了哪个政策章节。
""".strip()

    return context, results


if __name__ == "__main__":
    (
        vector_store,
        documents,
    ) = build_langchain_vector_store()

    print(
        f"已经写入 "
        f"{len(documents)} "
        f"个LangChain Document"
    )

    print(
        "LangChain Chroma位置：",
        LANGCHAIN_CHROMA_DIR,
    )

    while True:
        question = input(
            "\n请输入问题，输入exit结束："
        ).strip()

        if question.lower() in (
            "exit",
            "quit",
        ):
            break

        results = search_with_langchain(
            question,
            vector_store,
            top_k=3,
            min_score=0.55,
        )

        if not results:
            print(
                "没有检索到合格的知识。"
            )
            continue

        for index, result in enumerate(
            results,
            start=1,
        ):
            print("\n" + "-" * 50)
            print(f"第{index}名")
            print(
                "来源：",
                result["source"],
            )
            print(
                "章节：",
                result["section_title"],
            )
            print(
                f"相似度："
                f"{result['score']:.4f}"
            )
            print(result["content"])