import os
import openai
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from docs_ingest import process_and_insert_into_store, vector_store_manager
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/uploaded_docs'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

#Please export the key in the readme before running it.
openai.api_key = os.environ.get("OPENAI_API_KEY")


ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#此备注请前端同学注意 以下两个函数需要前端输入 需要老师上传文件框和学生提问框
##Attention front-end programmers.
#The following two functions require front-end input: a teacher uploading a file box and a student asking a question box.
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)


        process_and_insert_into_store(save_path)

        return jsonify({"message": "File uploaded and processed successfully"}), 200
    else:
        return jsonify({"error": "File type not allowed"}), 400



@app.route('/ask', methods=['POST'])
def ask_ai():
    data = request.get_json()
    question = data.get('question', '')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    llm = OpenAI(temperature=0.7)


    def retrieval_fn(query):
        return vector_store_manager.similarity_search(query, k=3)

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


    docs = retrieval_fn(question)
    context_text = "\n---\n".join([doc.page_content for doc in docs])


    final_prompt = PROMPT.format(context=context_text, question=question)
    answer = llm(final_prompt)

    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
