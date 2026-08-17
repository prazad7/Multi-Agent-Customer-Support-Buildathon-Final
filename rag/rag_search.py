import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set in the .env file")


# ---------------------------------------------------------
# FAISS configuration
# ---------------------------------------------------------

VECTOR_STORE_DIR = "rag/faiss_index"


# ---------------------------------------------------------
# Load FAISS vector store
# ---------------------------------------------------------

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vector_store = FAISS.load_local(
    VECTOR_STORE_DIR,
    embeddings,
    allow_dangerous_deserialization=True
)


# ---------------------------------------------------------
# RAG Search Function
# ---------------------------------------------------------

def search_knowledge_base(
    query: str,
    top_k: int = 5
) -> list[dict]:

    results = vector_store.similarity_search_with_score(
        query,
        k=top_k
    )

    formatted_results = []

    for document, score in results:

        formatted_results.append(
            {
                "content": document.page_content,
                "source": document.metadata.get(
                    "source",
                    "unknown"
                ),
                "score": float(score)
            }
        )

    return formatted_results


# ---------------------------------------------------------
# Local test
# ---------------------------------------------------------

if __name__ == "__main__":

    query = input(
        "Enter a QE/API testing question: "
    ).strip()

    if not query:
        print("Query cannot be empty.")
        exit()

    results = search_knowledge_base(query)

    print()
    print("=" * 70)
    print("RAG SEARCH RESULTS")
    print("=" * 70)

    for index, result in enumerate(results, start=1):

        print()
        print(f"Result {index}")
        print("-" * 70)

        print(
            f"Source: {result['source']}"
        )

        print(
            f"Similarity score: {result['score']}"
        )

        print()
        print(result["content"])

    print()
    print("=" * 70)