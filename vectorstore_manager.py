import os
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

class VectorStoreManager:
    def __init__(self, persist_directory="db/chroma_store"):

        self.persist_directory = persist_directory
        self.embedding_fn = OpenAIEmbeddings()

        self.collection_name = "unisupport_docs"
        if os.path.exists(persist_directory):
            self.chroma_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_fn,
                persist_directory=self.persist_directory
            )
        else:
            self.chroma_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_fn,
                persist_directory=self.persist_directory
            )

    def add_texts(self, texts, metadatas=None):
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]
        self.chroma_store.add_texts(texts=texts, metadatas=metadatas)
        self.chroma_store.persist()

    def similarity_search(self, query, k=3):
        return self.chroma_store.similarity_search(query, k=k)
