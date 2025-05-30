import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Load CSV
df = pd.read_csv("goodmark_tickets_export.csv")

# Combine title and description for better context
texts = (df["subject"].fillna("") + " - " + df["description"].fillna("")).tolist()

# Extract IDs for metadata
ids = df["id"].tolist()

# Create embedding model
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Create FAISS vectorstore with texts and metadata
vectorstore = FAISS.from_texts(
    texts,
    embedding,
    metadatas=[{"id": i} for i in ids]
)

# Save index
vectorstore.save_local("faiss_index")
