import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set in the .env file")


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

KNOWLEDGE_BASE_DIR = Path("knowledge_base")
VECTOR_STORE_DIR = Path("rag/faiss_index")


# ---------------------------------------------------------
# Load knowledge documents
# ---------------------------------------------------------

print("Loading knowledge documents...")

loader = DirectoryLoader(
    str(KNOWLEDGE_BASE_DIR),
    glob="**/*.md",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)

documents = loader.load()

if not documents:
    raise ValueError(
        f"No markdown files found in: {KNOWLEDGE_BASE_DIR}"
    )

print(f"Loaded {len(documents)} document(s).")


# ---------------------------------------------------------
# Split documents into chunks
# ---------------------------------------------------------

print("Splitting documents into chunks...")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)

chunks = text_splitter.split_documents(documents)

print(f"Created {len(chunks)} chunks.")


# ---------------------------------------------------------
# Create OpenAI embeddings
# ---------------------------------------------------------

print("Creating OpenAI embeddings...")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


# ---------------------------------------------------------
# Create FAISS vector store
# ---------------------------------------------------------

print("Building FAISS vector store...")

vector_store = FAISS.from_documents(
    chunks,
    embeddings,
)


# ---------------------------------------------------------
# Save FAISS index
# ---------------------------------------------------------

VECTOR_STORE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

vector_store.save_local(
    str(VECTOR_STORE_DIR)
)

print()
print("========================================")
print("FAISS vector store created successfully")
print("========================================")
print(f"Location: {VECTOR_STORE_DIR}")
print(f"Documents: {len(documents)}")
print(f"Chunks: {len(chunks)}")