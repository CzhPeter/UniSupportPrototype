import os
from pypdf import PdfReader
import docx

from langchain.text_splitter import RecursiveCharacterTextSplitter
from vectorstore_manager import VectorStoreManager


vector_store_manager = VectorStoreManager(persist_directory="db/chroma_store")

def process_and_insert_into_store(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        raw_text = parse_pdf(file_path)
    elif ext == ".docx":
        raw_text = parse_docx(file_path)
    elif ext == ".txt":
        raw_text = parse_txt(file_path)
    else:
        print("Unsupported file format:", ext)
        return


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    docs = text_splitter.split_text(raw_text)


    metadatas = [{"source": os.path.basename(file_path)} for _ in docs]


    vector_store_manager.add_texts(docs, metadatas=metadatas)

def parse_pdf(file_path):
    reader = PdfReader(file_path)
    text_list = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_list.append(text)
    return "\n".join(text_list)

def parse_docx(file_path):
    doc = docx.Document(file_path)
    text_list = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(text_list)

def parse_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
