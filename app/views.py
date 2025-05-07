import os.path
import random
import csv
import io

from flask import render_template, redirect, url_for, flash, request, send_file, send_from_directory
from werkzeug.utils import secure_filename
from app import app
from app.docs_ingest import process_and_insert_into_store
from app.models import User,AnswerRecord,Question, Topic, Notification, NotificationRecipient
from app.forms import ChooseForm, LoginForm, RegisterForm, UploadForm, ChangePasswordForm, RegisterForm
from flask_login import current_user, login_user, logout_user, login_required, fresh_login_required
import sqlalchemy as sa
from app import db
from app.forms import NotificationForm
from app.forms import TopicForm
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


# Smart Learning System
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


# Social System
@app.route("/SocialSystem",methods=['GET', 'POST'])
def social_system():
    form = TopicForm()
    if form.validate_on_submit():
        # If the submission is valid, create a new Topic and refresh the page
        new_topic = Topic(name=form.name.data, description=form.description.data)
        # By default, the creator also becomes a poster (host) and a subscriber
        new_topic.add_poster(current_user)
        new_topic.add_subscriber(current_user)
        db.session.add(new_topic)
        db.session.commit()
        flash(f'Topic "{new_topic.name}" created successfully!', 'success')
        return redirect(url_for('social_system'))

    all_topics = Topic.query.all()
    # Separate hosts and non-hosts
    host_topics = [t for t in all_topics if t in current_user.posting_topics]
    other_topics = [t for t in all_topics if t not in current_user.posting_topics]
    # Merge so that host topics appear first
    topics = host_topics + other_topics
    return render_template("socialSystem/social_system.html",topics = topics,form=form )


@app.route('/subscribe/<int:topic_id>')
@login_required
def subscribe(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user not in topic.subscribers:
        topic.add_subscriber(current_user)
        db.session.commit()
        flash(f'You have subscribed to "{topic.name}".', 'success')
    else:
        flash(f'You are already subscribed to "{topic.name}".', 'warning')
    return redirect(url_for('social_system'))


@app.route('/unsubscribe/<int:topic_id>')
@login_required
def unsubscribe(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if topic in current_user.subscriptions:
        topic.remove_subscriber(current_user)
        db.session.commit()
        flash(f'Unsubscribed from "{topic.name}".', 'warning')
    return redirect(url_for('social_system'))


@app.route('/topic/<int:topic_id>', methods=['GET', 'POST'])
@login_required
def topic_detail(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    # Determine whether the current user is a Host for the given topic
    is_host = current_user in topic.posters

    # If the user is a Host, instantiate the notification publishing form and handle its submission
    form = NotificationForm() if is_host else None
    if is_host and form.validate_on_submit():
        # Create and dispatch notifications using the method defined in models.py
        try:
            topic.post_notification(poster=current_user, content=form.content.data)
            flash('Notification posted to all subscribers.', 'success')
        except PermissionError as e:
            flash(str(e), 'danger')
        return redirect(url_for('topic_detail', topic_id=topic.id))

    # Retrieve all NotificationRecipient links for the current user under the given topic, ordered by time in descending order
    recips = (NotificationRecipient.query.join(Notification)
              .filter(Notification.topic_id == topic.id, NotificationRecipient.user_id == current_user.id)
              .order_by(Notification.date.desc()).all())

    return render_template(
        'socialSystem/topic_detail.html',
        topic=topic,
        is_host=is_host,
        form=form,
        recips = recips
    )


@app.route('/topic/<int:topic_id>/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(topic_id, notification_id):
    link = NotificationRecipient.query.filter_by(
        notification_id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    link.is_read = True
    db.session.commit()
    return redirect(url_for('topic_detail', topic_id=topic_id))


@app.route('/topic/<int:topic_id>/delete', methods=['POST'])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    # Allow deletion only by Hosts
    if current_user not in topic.posters:
        flash('You do not have permission to delete this topic.', 'danger')
        return redirect(url_for('topic_detail', topic_id=topic_id))

    db.session.delete(topic)
    db.session.commit()
    flash(f'Topic "{topic.name}" has been deleted.', 'warning')
    return redirect(url_for('social_system'))


from collections import defaultdict
@app.route('/notifications')
@login_required
def notifications():
    # Retrieve all NotificationRecipient records for the current user

    recips = (NotificationRecipient.query
              .join(NotificationRecipient.notification)
              .filter(NotificationRecipient.user_id == current_user.id)
              .order_by(Notification.date.desc())
              .all())

    # Group by topic
    grouped: dict[Topic, list[NotificationRecipient]] = defaultdict(list)
    for link in recips:
        grouped[link.notification.topic].append(link)

    # Within each group, sort first by is_read, then by date
    for topic, links in grouped.items():
        links.sort(key=lambda l: (l.is_read, -l.notification.date.timestamp()))

    return render_template(
        'socialSystem/notifications.html',
        grouped_notifications=grouped
    )


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