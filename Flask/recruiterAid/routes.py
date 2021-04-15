import os
import secrets
import re
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
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
    global rfiles
    rfiles = []
    global row
    row = None
    form = UploadResumeForm()
    if form.validate_on_submit():
        global token
        child_id = db.session.execute("select id from child")
        for row in child_id:
            row = row['id']

        if row is None:
            token = 1
        else:
            token_no = db.session.execute("select token_id from child where id= " + str(row))
            for token in token_no:
                token = token['token_id']
            token = token + 1

        files = request.files.getlist('files[]')
        global nres
        nres = 0
        for file in files:
            nres = nres + 1
            rfiles.append(file.filename)
            newFile = FileContents(user_id=current_user.id, token_id=token, resume_name=file.filename, resume_file=file.read())
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
    return render_template('home.html', form=form, title='Home')


def listToString(s):
    str1 = ""

    for ele in s:
        str1 += ele + ', '
    return str1


@app.route("/ranking", methods=['GET', 'POST'])
def ranking():
    global skill_form_string
    global skill_form_list
    form = SetRankingPolicy()
    if form.validate_on_submit():
        skill_form_list = request.form.getlist('skill')
        skill_form_string = listToString(skill_form_list)
        user_policy = RankingPolicy(user_id=current_user.id, experience=form.experience.data,
                                    skill=skill_form_string, degree=form.degree.data)
        db.session.add(user_policy)
        db.session.commit()
        flash('Resume ranking policy is successfully set and basis on that Rank is allocated.', 'success')
        return redirect(url_for('result'))
    return render_template('ranking.html', title='Set Ranking Policy', form=form)


@app.route("/result")
def result():
    # extract data from pdf file and then storing it into result table
    for i in range(nres):
        data = ResumeParser(
            'C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/static/ResumeFiles/' + rfiles[i],
            skills_file='C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/static/skills.csv').get_extracted_data()

        # match the skills of candidate with the skills of the ranking policy
        count = 0
        for p in data['skills']:
            for q in skill_form_list:
                if p == q:
                    count += 1

        # extract skills from pdf file
        s = data['skills']
        skill = listToString(s)

        # to convert list type to string of degree
        r = data['degree']
        if r is None:
            degree = 'None'
        else:
            degree = listToString(r)

        # separate B.E. from B.E. in Computer Engineering
        match_degree = re.split(r'\s', degree)

        # store data in result table
        newFile = Result(user_id=current_user.id, token_id=token, resume_name=rfiles[i], applicant_name=data['name'],
                         email=data['email'], mobileno=data['mobile_number'], degree=match_degree[0], skills=skill,
                         count_skills=count, experience=data['total_experience'])
        db.session.add(newFile)
        db.session.commit()

    # extract latest entry of degree from the policy table
    policyDegree = db.session.execute("SELECT degree FROM policy WHERE id = (SELECT MAX(id) from policy)")
    for deg in policyDegree:
        deg = deg['degree']
    db.session.commit()

    # separate B.E. from B.Tech
    split_deg = re.split(r'\s', deg)


    crnt_user_id = str(current_user.id)
    # extracting experience from policy table
    experience = db.session.execute("SELECT experience FROM policy WHERE id = (SELECT MAX(id) from policy)")
    for exp in experience:
        exp = exp['experience']
    db.session.commit()

    # display the final rank in result tab
    result_tb = []
    result_table = db.session.execute(
        "select resume_name from result where user_id=" + crnt_user_id + " and token_id=" + str(token) +
        " and experience>=" + str(exp) + " and (degree='" + str(split_deg[0]) + "' or degree='"
        + str(split_deg[2]) + "') order by experience DESC, count_skills DESC")

    # send list of resume files by removing comma
    for row in result_table:
        result_tb.append(' '.join(row))

    db.session.commit()

    return render_template('result.html', title='Results', nres=nres, result_tb=result_tb)


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
