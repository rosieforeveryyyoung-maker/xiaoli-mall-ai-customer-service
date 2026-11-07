from langchain_core.documents import Document
from langchain_community.embeddings import (
    FastEmbedEmbeddings,
)


document = Document(#使用Document对象
    page_content=(
        "退款审核通过后，款项通常在"
        "一至三个工作日内原路退回。"
    ),
    metadata={
        "source": "refund_policy.md",
        "document_title": "小丽商城退换货规则",
        "section_title": "退款到账时间",
    },
)


print("文档正文：")
print(document.page_content)

print("\n文档元数据：")
print(document.metadata)

#第二部分：使用LangChain的Embedding接口
embedding_model = FastEmbedEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir="C:/Temp/fastembed_cache",
    doc_embed_type="passage",
)

document_vectors = (
    embedding_model.embed_documents(
        [document.page_content]
    )
)

query_vector = (
    embedding_model.embed_query(
        "钱什么时候可以退回来"
    )
)


print(
    "\n知识向量数量：",
    len(document_vectors),
)

print(
    "每个知识向量的维度：",
    len(document_vectors[0]),
)

print(
    "问题向量的维度：",
    len(query_vector),
)

print(
    "知识向量前10个数字：",
    document_vectors[0][:10],
)

print(
    "问题向量前10个数字：",
    query_vector[:10],
)