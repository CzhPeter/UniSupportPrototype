import os.path
import random
import csv
import io

from flask import render_template, redirect, url_for, flash, request, send_file, send_from_directory
from werkzeug.utils import secure_filename
from app import app
from app.docs_ingest import process_and_insert_into_store
from app.models import User,AnswerRecord,Question, Topic, Notification
from app.forms import ChooseForm, LoginForm, RegisterForm, UploadForm, ChangePasswordForm, RegisterForm
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


def calculate_conclusion(score):
    if score <= 14:
        return "Mentally Healthy"
    elif score <= 24:
        return "Mild Psychological Issues"
    elif score <= 34:
        return "Moderate Psychological Issues"
    else:
        return "Severe Psychological Issues"


@app.route("/MentalHealthSurvey")
def mental_health_survey():
    return render_template('mental_health_survey.html', title="MentalHealthSurvey")


@app.route('/questionnaire1', methods=['GET', 'POST'])
@login_required
def questionnaire1():
    questions = Question.query.filter_by(questionnaire_name='Questionnaire 1').order_by(Question.id).all()
    if request.method == 'POST':
        score = sum(int(request.form.get(f'q{q.id}', 0)) for q in questions)
        conclusion = calculate_conclusion(score)
        record = AnswerRecord(
            user_id=current_user.id,
            questionnaire_name='Questionnaire 1',
            score=score,
            conclusion=conclusion
        )
        db.session.add(record)
        db.session.commit()
        return redirect(url_for('result', score=score, source='Questionnaire 1'))
    return render_template('questionnaire.html', title="Psychological Survey 1", questions=questions, action_url=url_for('questionnaire1'))


@app.route('/questionnaire2', methods=['GET', 'POST'])
@login_required
def questionnaire2():
    questions = Question.query.filter_by(questionnaire_name='Questionnaire 2').order_by(Question.id).all()
    if request.method == 'POST':
        score = sum(int(request.form.get(f'q{q.id}', 0)) for q in questions)
        conclusion = calculate_conclusion(score)
        record = AnswerRecord(
            user_id=current_user.id,
            questionnaire_name='Questionnaire 2',
            score=score,
            conclusion=conclusion
        )
        db.session.add(record)
        db.session.commit()
        return redirect(url_for('result', score=score, source='Questionnaire 2'))
    return render_template('questionnaire.html', title="Psychological Survey 2", questions=questions, action_url=url_for('questionnaire2'))


@app.route('/result')
@login_required
def result():
    score = int(request.args.get('score', 0))
    source = request.args.get('source', 'Survey')
    conclusion = calculate_conclusion(score)
    return render_template('result.html', title="Assessment Result", score=score, conclusion=conclusion, source=source)


@app.route('/account')
@login_required
def account():
    records = AnswerRecord.query.filter_by(user_id=current_user.id).order_by(AnswerRecord.timestamp.desc()).all()
    return render_template('account.html', title="Account", records=records)


@app.route('/delete_record/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    record = AnswerRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        flash("You are not authorized to delete this record.", "danger")
        return redirect(url_for('account'))
    db.session.delete(record)
    db.session.commit()
    flash("Record deleted successfully.", "success")
    return redirect(url_for('account'))


@app.route("/admin")
@login_required
def admin():
    if current_user.role != "Admin":
        return redirect(url_for('home'))
    form = ChooseForm()
    q = db.select(User)
    user_lst = db.session.scalars(q)
    return render_template('admin.html', title="Admin", user_lst=user_lst, form=form)


@app.route('/select_questionnaire')
@login_required
def select_questionnaire():
    if current_user.role != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('select_questionnaire.html', title="Select Questionnaire")


@app.route('/manage_questionnaire1', methods=['GET', 'POST'])
@login_required
def manage_questionnaire1():
    if current_user.role != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    questions = Question.query.filter_by(questionnaire_name='Questionnaire 1').order_by(Question.id).all()
    if request.method == 'POST':
        for q in questions:
            new_content = request.form.get(f'q{q.id}')
            if new_content:
                q.content = new_content
        db.session.commit()
        flash('Questionnaire 1 updated successfully.', 'success')
        return redirect(url_for('manage_questionnaire1'))
    return render_template('manage_questionnaire.html', title="Manage Questionnaire 1", questions=questions, action_url=url_for('manage_questionnaire1'))


@app.route('/manage_questionnaire2', methods=['GET', 'POST'])
@login_required
def manage_questionnaire2():
    if current_user.role != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    questions = Question.query.filter_by(questionnaire_name='Questionnaire 2').order_by(Question.id).all()
    if request.method == 'POST':
        for q in questions:
            new_content = request.form.get(f'q{q.id}')
            if new_content:
                q.content = new_content
        db.session.commit()
        flash('Questionnaire 2 updated successfully.', 'success')
        return redirect(url_for('manage_questionnaire2'))
    return render_template('manage_questionnaire.html', title="Manage Questionnaire 2", questions=questions, action_url=url_for('manage_questionnaire2'))


@app.route('/delete_user', methods=['POST'])
def delete_user():
    form = ChooseForm()
    if form.validate_on_submit():
        u = db.session.get(User, int(form.choice.data))
        q = db.select(User).where((User.role == "Admin") & (User.id != u.id))
        first = db.session.scalars(q).first()
        if not first:
            flash("You can't delete your own account if there are no other admin users!", "danger")
        elif u.id == current_user.id:
            logout_user()
            db.session.delete(u)
            db.session.commit()
            return redirect(url_for('home'))
        else:
            db.session.delete(u)
            db.session.commit()
    return redirect(url_for('admin'))


@app.route('/toggle_user_role', methods=['POST'])
def toggle_user_role():
    form = ChooseForm()
    if form.validate_on_submit():
        u = db.session.get(User, int(form.choice.data))
        q = db.select(User).where((User.role == "Admin") & (User.id != u.id))
        first = db.session.scalars(q).first()
        if not first:
            flash("You can't drop your admin role if there are no other admin users!", "danger")
        elif u.id == current_user.id:
                logout_user()
                u.role = "Normal"
                db.session.commit()
                return redirect(url_for('home'))
        else:
            u.role = "Normal" if u.role == "Admin" else "Admin"
            db.session.commit()
    return redirect(url_for('admin'))


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


@app.route('/change_pw', methods=['GET', 'POST'])
@fresh_login_required
def change_pw():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully', 'success')
        return redirect(url_for('home'))
    return render_template('generic_form.html', title='Change Password', form=form)


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
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/SmartLearningSystem')
@login_required
def smart_learning_system():
    if current_user.is_authenticated:
        if current_user.role == "Admin":
            return redirect(url_for('upload'))
        return redirect(url_for('chat'))
    else:
        flash("Please login first", "danger")
    return redirect(url_for('home'))


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


from flask import jsonify
from app.debug_utils import reset_db
@app.route("/test/reset")
def test_reset():
    """Reset & seed database."""
    reset_db()
    return "Database has been reset and seeded.", 200


@app.route("/test/users")
def test_users():
    """List all users."""
    return "<br>".join(repr(u) for u in User.query.all())


@app.route("/test/topics")
def test_topics():
    """List all topics and their subscribers/posters."""
    lines = []
    for t in Topic.query.all():
        subs    = [u.username for u in t.subscribers]
        posters = [u.username for u in t.posters]
        lines.append(f"{t.name} — subscribers: {subs}, posters: {posters}")
    return "<br>".join(lines)


@app.route("/test/subscribe")
def test_subscribe():
    """
    Subscribe a user to a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    t.add_subscriber(u)
    db.session.commit()
    return f"{username} subscribed to {topic_name}", 200


@app.route("/test/unsubscribe")
def test_unsubscribe():
    """
    Unsubscribe a user from a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    t.remove_subscriber(u)
    db.session.commit()
    return f"{username} unsubscribed from {topic_name}", 200


@app.route("/test/grant_post")
def test_grant_post():
    """
    Grant a user posting rights on a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    t.add_poster(u)
    db.session.commit()
    return f"Granted posting rights on '{topic_name}' to {username}", 200


@app.route("/test/revoke_post")
def test_revoke_post():
    """
    Revoke a user's posting rights on a topic.
    GET params: user=<username>&topic=<topicname>
    """
    username   = request.args.get('user')
    topic_name = request.args.get('topic')
    u = User.query.filter_by(username=username).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "User or Topic not found", 404

    if u in t.posters:
        t.posters.remove(u)
        db.session.commit()
        return f"Revoked posting rights on '{topic_name}' from {username}", 200
    else:
        return f"{username} had no posting rights on '{topic_name}'", 400


@app.route("/test/post")
def test_post():
    """
    Post a notification in a topic.
    GET params: poster=<username>&topic=<topicname>&content=<text>
    """
    poster_name = request.args.get('poster')
    topic_name  = request.args.get('topic')
    content     = request.args.get('content', "Test notification")
    u = User.query.filter_by(username=poster_name).first()
    t = Topic.query.filter_by(name=topic_name).first()
    if not u or not t:
        return "Poster or Topic not found", 404
    try:
        notif = t.post_notification(u, content)
    except PermissionError as e:
        return str(e), 403
    return (
        f"Posted notification:<br>"
        f"ID: {notif.id}<br>"
        f"Topic: {notif.topic.name}<br>"
        f"Content: {notif.content}<br>"
        f"From: {notif.poster.username}<br>"
        f"Date: {notif.date.isoformat()}"
    ), 200


@app.route("/test/notifications/<username>")
def test_notifications(username):
    """
    List all notifications received by a user.
    URL param: <username>
    """

    u = User.query.filter_by(username=username).first_or_404()
    lines = [
        f"{n.date.isoformat()} — {n.content} (from {n.poster.username})"
        for n in u.received_notifications
    ]
    return "<br>".join(lines)


@app.route("/test/posted/<username>")
def test_posted(username):
    """
    List all notifications posted by a user.
    URL param: <username>
    """
    u = User.query.filter_by(username=username).first()
    if not u:
        return "User not found", 404
    lines = [
        f"{n.date.isoformat()} — {n.content} (in topic {n.topic.name})"
        for n in u.posted_notifications
    ]
    return "<br>".join(lines)


@app.route("/test/delete_notification")
def test_delete_notification():
    """
    Delete a notification by its ID.
    GET params: id=<notification_id>
    """
    nid = request.args.get('id', type=int)
    n = Notification.query.get(nid)
    if not n:
        return "Notification not found", 404
    db.session.delete(n)
    db.session.commit()
    return f"Deleted notification {nid}", 200


@app.route("/test/all")
def test_all():
    """Dump all data as JSON, now with users' received notifications."""
    users = []
    for u in User.query.all():
        users.append({
            'username': u.username,
            'role':     u.role,
            'subscriptions': sorted(t.name for t in u.subscriptions),
            'posting_topics': sorted(t.name for t in u.posting_topics),
            'received_notifications': [
                {
                    'id':      n.id,
                    'content': n.content,
                    'topic':   n.topic.name,
                    'poster':  n.poster.username,
                    'date':    n.date.isoformat()
                }
                for n in u.received_notifications
            ]
        })

    topics = [{
        'name':        t.name,
        'description': t.description,
        'subscribers': sorted(u.username for u in t.subscribers),
        'posters':     sorted(u.username for u in t.posters),
    } for t in Topic.query.all()]

    notifications = [{
        'id':         n.id,
        'content':    n.content,
        'topic':      n.topic.name,
        'poster':     n.poster.username,
        'recipients': sorted(u.username for u in n.recipients),
        'date':       n.date.isoformat(),
    } for n in Notification.query.all()]

    return jsonify({
        'users': users,
        'topics': topics,
        'notifications': notifications
    })


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