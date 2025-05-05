from flask import current_app
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from app.vectorstore_manager import VectorStoreManager

def get_llm():
    return ChatGroq(
        model_name=current_app.config["LLM_MODEL_NAME"],
        groq_api_key=current_app.config["GROQ_API_KEY"],
        temperature=0.7,
    )

def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name=current_app.config["EMBEDDING_MODEL_NAME"]
    )

def get_vector_store_manager():
    embedding_model = get_embedding_model()
    return VectorStoreManager(embedding_fn=embedding_model)