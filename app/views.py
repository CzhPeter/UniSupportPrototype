from flask import render_template, redirect, url_for, flash, request, send_file, send_from_directory
from app import app
from app.models import User,AnswerRecord,Question
from app.forms import ChooseForm, LoginForm, ChangePasswordForm, RegisterForm
from flask_login import current_user, login_user, logout_user, login_required, fresh_login_required
import sqlalchemy as sa
from app import db
from urllib.parse import urlsplit
import random
import csv
import io


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