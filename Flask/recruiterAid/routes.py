import os
import sqlite3
from sqlite3 import Error
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from sqlalchemy.dialects import sqlite
from werkzeug.utils import secure_filename

from recruiterAid import app, db, bcrypt, mail
from recruiterAid.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                                RequestResetForm, ResetPasswordForm, UploadResumeForm, SetRankingPolicy)
from recruiterAid.models import User, FileContents, RankingPolicy, Result
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from pyresparser import ResumeParser

UPLOAD_FOLDER = 'C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/static/ResumeFiles/'
ALLOWED_EXTENSIONS = set(['pdf'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
@app.route("/home", methods=['GET', 'POST'])
def home():
    global nres
    global rfiles
    rfiles = []
    form = UploadResumeForm()
    if form.validate_on_submit():
        files = request.files.getlist('files[]')
        nres = 0
        for file in files:
            nres = nres+1
            rfiles.append(file.filename)
            newFile = FileContents(user_id=current_user.id, resume_name=file.filename, resume_file=file.read())
            db.session.add(newFile)
            db.session.commit()
            file.seek(0)
        # print(nres)

    if request.method == 'POST':
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        files = request.files.getlist('files[]')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # To rename file to store unique copy in project ResumeFiles folder
                # os.rename(UPLOAD_FOLDER + filename, UPLOAD_FOLDER+ newFileName)

        flash('File(s) successfully uploaded and now select one of the policy to rank the resumes.', 'success')
        return redirect(url_for('ranking'))
    return render_template('home.html', form=form)


def listToString(s):
    str1 = ""

    for ele in s:
        str1 += ele+', '
    return str1


@app.route("/ranking", methods=['GET', 'POST'])
def ranking():
    form = SetRankingPolicy()
    if form.validate_on_submit():
        s = request.form.getlist('skill')
        skill = listToString(s)
        user_policy = RankingPolicy(user_id=current_user.id, experience=form.experience.data,
                                    skill=skill, degree=form.degree.data)
        db.session.add(user_policy)
        db.session.commit()
        flash('Resume ranking policy is successfully set.', 'success')
        return redirect(url_for('result'))
    return render_template('ranking.html', title='Set Ranking Policy', form=form)


@app.route("/result")
def result():
    # Number of resumes uploaded
    # print('ghavan',nres)
    for i in range(nres):
        data = ResumeParser(
            'C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/static/ResumeFiles/'+rfiles[i],
            skills_file='C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/static/skills.csv').get_extracted_data()

        s = data['skills']
        skill = listToString(s)

        r = data['degree']
        if r is None:
            degree = 'None'
        else:
            degree = listToString(r)

        newFile = Result(user_id=current_user.id, resume_name=rfiles[i], applicant_name=data['name'], email=data['email'],
                         mobileno=data['mobile_number'], degree=degree, skills=skill,
                         experience=data['total_experience'])
        db.session.add(newFile)
        db.session.commit()

    result_tb = []
    user = str(current_user.id)
    result_table = db.session.execute("select resume_name from result where user_id="+user+ " order by experience DESC ")

    for row in result_table:
        result_tb.append(' '.join(row))

    return render_template('result.html', title='result', nres=nres, result_tb=result_tb)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


