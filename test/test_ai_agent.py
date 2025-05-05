import os
import openai
from pypdf import PdfReader
import docx
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import HumanMessage


embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


class VectorStoreManager:
    def __init__(self, embedding_fn, persist_directory="db/faiss_store"):
        self.persist_directory = persist_directory
        self.embedding_fn = embedding_fn

        # 尝试加载已有向量库，否则初始化
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


# 初始化
vector_store_manager = VectorStoreManager(embedding_fn=embedding_model)
llm = ChatGroq(model_name="llama3-70b-8192", temperature=0.7, groq_api_key="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")


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


prompt_template = """You are an AI teaching assistant. Below is a question from a student along with the retrieved reference documents.
Please answer the question based strictly on the information from the documents. 
If the documents do not contain relevant information, reply with "No relevant information found."

Reference Documents:
{context}

Student's Question: {question}
Answer:"""


PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)


def ask_ai(question: str) -> str:
    docs = vector_store_manager.similarity_search(question, k=3)
    if not docs:
        return "未检索到相关文档"
    context_text = "\n---\n".join([doc.page_content for doc in docs])
    final_prompt = PROMPT.format(context=context_text, question=question)
    return llm([HumanMessage(content=final_prompt)]).content


def upload_doc(file_path: str):
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    print(f"正在处理文件: {file_path}")
    process_and_insert_into_store(file_path)
    print("文件已成功处理并插入向量数据库。")


if __name__ == "__main__":
    print("== AI Agent 本地测试 ==")
    print("命令：")
    print("  upload [文件路径]    上传文档并生成知识库")
    print("  ask                  提问")
    print("  exit                 退出")

    while True:
        cmd = input("\n>>> ").strip()
        if cmd == "exit":
            break
        elif cmd.startswith("upload "):
            _, path = cmd.split(" ", 1)
            upload_doc(path.strip())
        elif cmd == "ask":
            question = input("请输入你的问题：\n> ")
            answer = ask_ai(question)
            print("\nAI 回答：\n", answer)
        else:
            print("未知命令。请输入 upload [path]、ask 或 exit")