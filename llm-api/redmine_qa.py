import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama

# === Step 1: Load Redmine tickets ===

def load_tickets(csv_path: str):
    df = pd.read_csv(csv_path)
    docs = []

    for _, row in df.iterrows():
        subject = str(row.get("subject", "")).strip()
        description = str(row.get("description", "")).strip()
        full_text = f"Subject: {subject}\nDescription: {description}"
        docs.append(full_text)

    return docs


# === Step 2: Create embeddings and vector store ===

def create_vectorstore(docs, persist_path=None):
    print("[+] Creating vectorstore...")

    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(docs, embedding_model)

    if persist_path:
        vectorstore.save_local(persist_path)
        print(f"[✓] Vectorstore saved to: {persist_path}")

    return vectorstore


# === Step 3: Connect Ollama and create QA chain ===

def setup_qa_chain(vectorstore):
    print("[+] Connecting to Ollama...")

    llm = Ollama(model="llama3")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        chain_type="stuff"
    )

    return qa_chain


# === Step 4: Main QA Loop ===

def main():
    csv_path = "llm-api/goodmark_tickets_export.csv"  # <-- change if needed
    persist_path = "faiss_index"

    docs = load_tickets(csv_path)

    try:
        vectorstore = FAISS.load_local(persist_path, HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
        print(f"[✓] Loaded existing vectorstore from {persist_path}")
    except:
        vectorstore = create_vectorstore(docs, persist_path)

    qa_chain = setup_qa_chain(vectorstore)

    print("\nAsk a question about your Redmine tickets (type 'exit' to quit):")
    while True:
        query = input(">> ")
        if query.lower() in ("exit", "quit"):
            break
        answer = qa_chain.run(query)
        print("\nAnswer:\n", answer, "\n")


if __name__ == "__main__":
    main()
