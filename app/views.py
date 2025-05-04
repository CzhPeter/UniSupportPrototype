import os.path

from flask import render_template, redirect, url_for, flash, request, send_file, send_from_directory
from werkzeug.utils import secure_filename
from app import app
from app.docs_ingest import process_and_insert_into_store
from app.models import User
from app.forms import ChooseForm, LoginForm, RegisterForm, UploadForm
from flask_login import current_user, login_user, logout_user, login_required, fresh_login_required
import sqlalchemy as sa
from app import db
from urllib.parse import urlsplit
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from app.llm_rag_config import get_llm, get_vector_store_manager


@app.route("/")
def home():
    return render_template('home.html', title="Home")


@app.route("/account")
@login_required
def account():
    return render_template('account.html', title="Account")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data  # 添加这行
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)



@app.route('/upload', methods=['GET', 'POST'])
def upload():
    form = UploadForm()
    message = None
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        process_and_insert_into_store(save_path)
        message = f"{filename} is uploaded successfully and add into the knowledge base"
    return render_template('upload.html', title='Upload files', form=form, message=message)


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
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    llm = get_llm()
    vector_store_manager = get_vector_store_manager()
    question = None
    answer = None
    if request.method == 'POST':
        question = request.form['question']
        if question:
            docs = vector_store_manager.similarity_search(question, k=3)
            if not docs:
                flash("No related knowledge context", "danger")
            context_text = "\n---\n".join([doc.page_content for doc in docs])
            final_prompt = PROMPT.format(context=context_text, question=question)
            answer = llm([HumanMessage(content=final_prompt)]).content
    return render_template('chat.html', title='Smart Learning AI Chatbot', question=question, answer=answer)


# Error handlers
# See: https://en.wikipedia.org/wiki/List_of_HTTP_status_codes

# Error handler for 403 Forbidden
@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html', title='Error'), 403

# Handler for 404 Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='Error'), 404

@app.errorhandler(413)
def error_413(error):
    return render_template('errors/413.html', title='Error'), 413

# 500 Internal Server Error
@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html', title='Error'), 500