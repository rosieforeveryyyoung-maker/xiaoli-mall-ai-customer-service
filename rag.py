import re
from pathlib import Path
import numpy as np
from fastembed import TextEmbedding
import chromadb
#设置模型
KNOWLEDGE_DIR = Path(__file__).with_name("knowledge")
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

CHROMA_DIR = Path(__file__).with_name(
    "chroma_db"
)

CHROMA_COLLECTION_NAME = (
    "xiaoli_mall_knowledge"
)
_embedding_model = None

def get_embedding_model():
    """
    第一次调用时加载Embedding模型，
    后续调用继续使用同一个模型。
    """

    global _embedding_model

    if _embedding_model is None:
        print("正在加载Embedding模型……")

        _embedding_model = TextEmbedding(
            model_name=EMBEDDING_MODEL_NAME,
        )

    return _embedding_model

def load_knowledge_documents():#读取文档
    documents = []

    for file_path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")

        documents.append(
            {
                "source": file_path.name,
                "content": content,
            }
        )

    return documents

def split_documents(documents):#文档切块函数
    chunks = []

    for document in documents:
        content = document["content"].strip()
        lines = content.splitlines()

        document_title = lines[0].lstrip("#").strip()

        sections = re.split(
            r"^##\s+",
            content,
            flags=re.MULTILINE,
        )

        for section in sections[1:]:
            section_lines = section.strip().splitlines()

            if not section_lines:
                continue

            section_title = section_lines[0].strip()

            section_content = "\n".join(
                section_lines[1:]
            ).strip()

            chunks.append(
                {
                    "source": document["source"],
                    "document_title": document_title,
                    "section_title": section_title,
                    "content": (
                        f"{document_title}\n"
                        f"{section_title}\n"
                        f"{section_content}"
                    ),
                }
            )

    return chunks

def create_knowledge_vectors(chunks):
    """
    将所有知识块转换成向量。
    """

    if not chunks:
        return np.empty((0, 0))

    model = get_embedding_model()

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    vectors = list(
        model.passage_embed(texts)
    )

    return np.array(vectors)

def get_chroma_collection():
    """
    打开本地Chroma数据库，
    获取或创建商城知识库集合。
    """

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = (
        client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            configuration={
                "hnsw": {
                    "space": "cosine",
                }
            },
            embedding_function=None,
        )
    )

    return collection

def save_chunks_to_chroma(
    chunks,
    knowledge_vectors,
):
    """
    将知识块、向量和来源信息写入Chroma。
    """

    collection = get_chroma_collection()

    existing_data = collection.get(
        include=[]
    )

    existing_ids = existing_data["ids"]


    ids = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(
            f"knowledge_chunk_{index}"
        )

        documents.append(
            chunk["content"]
        )

        metadatas.append(
            {
                "source": chunk["source"],
                "document_title": (
                    chunk["document_title"]
                ),
                "section_title": (
                    chunk["section_title"]
                ),
            }
        )

    collection.upsert(
        ids=ids,
        embeddings=knowledge_vectors.tolist(),
        documents=documents,
        metadatas=metadatas,
    )
    stale_ids = list(
        set(existing_ids) - set(ids)
    )

    if stale_ids:
        collection.delete(
            ids=stale_ids
        )

    return collection

def rebuild_knowledge_base():
    """
    重新读取知识文档、切块、生成向量，
    并同步到Chroma。
    """

    documents = load_knowledge_documents()

    chunks = split_documents(
        documents
    )

    knowledge_vectors = (
        create_knowledge_vectors(
            chunks
        )
    )

    collection = save_chunks_to_chroma(
        chunks,
        knowledge_vectors,
    )

    return (
        collection,
        len(documents),
        len(chunks),
    )#这是把原来的四步封装起来

def search_knowledge_with_chroma(
    query,
    collection,
    top_k=3,
    min_score=0.55,
):
    """
    使用Chroma进行语义向量检索。
    """

    if not query.strip():
        return []

    query_vector = create_query_vector(
        query
    )

    query_result = collection.query(
        query_embeddings=[
            query_vector.tolist()
        ],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = query_result["documents"][0]
    metadatas = query_result["metadatas"][0]
    distances = query_result["distances"][0]

    results = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        similarity = 1 - float(distance)

        if similarity < min_score:
            continue

        results.append(
            {
                "source": metadata["source"],
                "document_title": metadata[
                    "document_title"
                ],
                "section_title": metadata[
                    "section_title"
                ],
                "content": document,
                "score": similarity,
            }
        )

    return results

def create_query_vector(query):
    """
    将用户问题转换成向量。
    """

    model = get_embedding_model()

    vectors = list(
        model.query_embed(query)
    )

    return np.array(vectors[0])

def calculate_cosine_similarities(
    query_vector,
    knowledge_vectors,
):
    """
    计算问题向量与所有知识向量的余弦相似度。
    """

    dot_products = (
        knowledge_vectors @ query_vector#这几部分对应余弦相似度公式计算向量点积
    )

    query_length = np.linalg.norm(#计算向量长度。
        query_vector
    )

    knowledge_lengths = np.linalg.norm(
        knowledge_vectors,
        axis=1,
    )

    similarities = (#点积 ÷ 两个向量的长度=余弦相似度)
        dot_products
        / (knowledge_lengths * query_length)
    )

    return similarities

def search_knowledge_by_vector(
    query,
    chunks,
    knowledge_vectors,
    top_k=3,
    min_score=0.55,
):
    """
    使用Embedding向量检索最相关的知识块。
    np.argsort()：根据相似度排列知识块编号；
[::-1]：将顺序反过来，让相似度最高的排在前面。
    """

    if not query.strip():
        return []

    query_vector = create_query_vector(
        query
    )

    similarities = (
        calculate_cosine_similarities(
            query_vector,
            knowledge_vectors,
        )
    )

    ranked_indices = np.argsort(
        similarities
    )[::-1]

    results = []

    for index in ranked_indices:
        score = float(
            similarities[index]
        )

        if score < min_score:
            continue

        result = chunks[index].copy()
        result["score"] = score

        results.append(result)

        if len(results) >= top_k:
            break

    return results


def normalize_text(text):
    """
    去掉标点符号和空格，并将英文字母转成小写。
    """

    return re.sub(
        r"[^\u4e00-\u9fffa-z0-9]",
        "",
        text.lower(),
    )


def create_bigrams(text):
    """
    把文字拆成连续的两个字符。
    例如：退款到账 -> 退款、款到、到账
    """

    normalized_text = normalize_text(text)

    if not normalized_text:
        return set()

    if len(normalized_text) == 1:
        return {normalized_text}

    return {
        normalized_text[index:index + 2]
        for index in range(len(normalized_text) - 1)
    }


def calculate_relevance_score(query, content):
    """
    计算用户问题和知识块之间的相关分数。
    """

    normalized_query = normalize_text(query)
    normalized_content = normalize_text(content)

    query_characters = set(normalized_query)
    content_characters = set(normalized_content)

    shared_characters = (
        query_characters & content_characters
    )

    query_bigrams = create_bigrams(query)
    content_bigrams = create_bigrams(content)

    shared_bigrams = query_bigrams & content_bigrams

    score = (
        len(shared_bigrams) * 3#两个连续字符比单个相同字符更有意义
        + len(shared_characters)
    )

    return score


def search_knowledge(query, chunks, top_k=3):
    """
    从全部知识块中找出最相关的几个。
    """

    if not query.strip():
        return []

    results = []

    for chunk in chunks:
        score = calculate_relevance_score(
            query,
            chunk["content"],
        )

        if score < 2:
            continue

        result = chunk.copy()
        result["score"] = score
        results.append(result)

    results.sort(
        key=lambda result: result["score"],
        reverse=True,
    )

    return results[:top_k]

def build_knowledge_context(
        query,
        collection,
        top_k=2,
        min_score=0.55,
):
    """
    检索知识库，并将结果整理成大模型能使用的上下文。
    """

    results = search_knowledge_with_chroma(
        query,
        collection,
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
        collection,
        document_count,
        chunk_count,
    ) = rebuild_knowledge_base()

    print(
        "Chroma数据库位置：",
        CHROMA_DIR,
    )

    print(
        "Chroma集合名称：",
        collection.name,
    )

    print(
        "Chroma中共有",
        collection.count(),
        "条知识记录",
    )

    print(
        f"读取到 {document_count} 个文档"
    )

    print(
        f"切分出 {chunk_count} 个知识块"
    )
    while True:
        query = input(
            "\n请输入问题，输入 exit 结束："
        ).strip()

        if query.lower() in ("exit", "quit"):
            break

        results = search_knowledge_with_chroma(
            query,
            collection,
            top_k=3,
            min_score=0.55,
        )

        if not results:
            print("知识库中没有找到相关内容。")
            continue

        print("\n检索结果：")

        for index, result in enumerate(
            results,
            start=1,
        ):
            print("\n" + "-" * 50)
            print(f"第 {index} 名")
            print(
                f"向量相似度："
                f"{result['score']:.4f}"
            )
            print(f"来源：{result['source']}")
            print(f"章节：{result['section_title']}")
            print(result["content"])