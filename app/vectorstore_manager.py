import os
from langchain_community.vectorstores import FAISS

class VectorStoreManager:
    def __init__(self, embedding_fn, persist_directory="app/data/db/faiss_store"):
        self.persist_directory = persist_directory
        self.embedding_fn = embedding_fn

        if os.path.exists(os.path.join(persist_directory, "index.faiss")):
            self.faiss_store = FAISS.load_local(persist_directory, self.embedding_fn, allow_dangerous_deserialization=True)
        else:
            self.faiss_store = None

    def add_texts(self, texts, metadatas=None):
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]
        if self.faiss_store:
            self.faiss_store.add_texts(texts=texts, metadatas=metadatas)
        else:
            self.faiss_store = FAISS.from_texts(texts=texts, embedding=self.embedding_fn, metadatas=metadatas)
        self.faiss_store.save_local(self.persist_directory)

    def similarity_search(self, query, k=3):
        if not self.faiss_store:
            return []
        return self.faiss_store.similarity_search(query, k=k)
