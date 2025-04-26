from flask import render_template, redirect, url_for, flash, request, send_file, send_from_directory
from app import app
from app.models import User,AnswerRecord
from app.forms import ChooseForm, LoginForm, ChangePasswordForm, RegisterForm
from flask_login import current_user, login_user, logout_user, login_required, fresh_login_required
import sqlalchemy as sa
from app import db
from urllib.parse import urlsplit
import random
import csv
import io

QUESTIONNAIRE1 = [
    {"question": "Do you often feel tired?"},
    {"question": "Do you frequently have trouble sleeping?"},
    {"question": "Do you often feel sad or depressed?"},
    {"question": "Do you feel anxious easily?"},
    {"question": "Have you lost interest in activities you used to enjoy?"},
    {"question": "Do you find it hard to concentrate?"},
    {"question": "Do you feel overwhelmed by small matters?"},
    {"question": "Do you experience frequent mood swings?"},
    {"question": "Do you feel isolated even when around others?"},
    {"question": "Do you often feel hopeless about the future?"}
]

QUESTIONNAIRE2 = [
    {"question": "Do you often feel lonely?"},
    {"question": "Do you feel that life has no meaning?"},
    {"question": "Do you frequently feel helpless?"},
    {"question": "Do you get angry easily over trivial matters?"},
    {"question": "Do you find it difficult to enjoy your daily activities?"},
    {"question": "Do you often experience a loss of appetite?"},
    {"question": "Do you feel exhausted even after resting?"},
    {"question": "Do you worry excessively about the future?"},
    {"question": "Do you often feel worthless?"},
    {"question": "Do you find it hard to make decisions?"}
]

def calculate_conclusion(score):
    if score <= 14:
        return "Mentally Healthy"
    elif score <= 24:
        return "Mild Psychological Issues"
    elif score <= 34:
        return "Moderate Psychological Issues"
    else:
        return "Severe Psychological Issues"

@app.route("/")
def home():
    return render_template('home.html', title="Home")

@app.route('/questionnaire1', methods=['GET', 'POST'])
@login_required
def questionnaire1():
    if request.method == 'POST':
        score = sum(int(request.form.get(f'q{i}', 0)) for i in range(10))
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
    return render_template('questionnaire.html', title="Psychological Survey 1", questions=QUESTIONNAIRE1, action_url=url_for('questionnaire1'))

@app.route('/questionnaire2', methods=['GET', 'POST'])
@login_required
def questionnaire2():
    if request.method == 'POST':
        score = sum(int(request.form.get(f'q{i}', 0)) for i in range(10))
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
    return render_template('questionnaire.html', title="Psychological Survey 2", questions=QUESTIONNAIRE2, action_url=url_for('questionnaire2'))

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
    return render_template('generic_form.html', title='Sign In', form=form)

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('generic_form.html', title='Register', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


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