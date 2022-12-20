from datetime import datetime
from flask import Flask,redirect,render_template,request,session,jsonify,render_template_string
import json
from flask_dropzone import Dropzone
import os
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import flask_excel as excel
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
import json
import smtplib

basedir=os.path.abspath(os.path.dirname(__file__))

filename='config.json'

with open(filename,'r', encoding='utf-8') as f:
    params = json.load(f)['params']
    #print(params)

#if run on localhost , set local_server=True
local_server=True

app = Flask(__name__)

#define upload parameters
app.config.update(
    UPLOADED_PATH=os.path.join(basedir,'static/uploads'),
    #30 minutes
    DROPZONE_TIMEOUT=60000*30 ,
    #max file size in megabytes
    DROPZONE_MAX_FILE_SIZE=1024,
    DROPZONE_ALLOWED_FILE_CUSTOM=True,
    DROPZONE_ALLOWED_FILE_TYPE='image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt,.py,.php,.mp4',
    DROPZONE_MAX_FILES=100000,
    DROPZONE_ENABLE_CSRF=True,
    DROPZONE_REDIRECT_VIEW='display',
    DROPZONE_INVALID_FILE_TYPE='Extension not allowed',
)
#connect based on localhost or production environment
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

#make connection to DB
db = SQLAlchemy(app)

#to receive email in mail as well
server=smtplib.SMTP('smtp.gmail.com',587)
server.starttls()
server.login(params['gmail-user'],params['gmail-pass'])

#create structure same as backend DB for 'user' table
class User(db.Model):
   serial = db.Column( db.Integer, primary_key = True)
   source_ip = db.Column(db.String(20),nullable=False)
   Location = db.Column(db.String(50),nullable=True)  
   date = db.Column(db.String(10),nullable=True)

#create structure same as backend DB for 'contact' table
class Contact(db.Model):
   serial = db.Column( db.Integer, primary_key = True)
   name = db.Column(db.String(20),nullable=False)
   subject = db.Column(db.String(50),nullable=False)
   email = db.Column(db.String(50),nullable=False)  
   message = db.Column(db.String(1000),nullable=False)
   date = db.Column(db.String(10),nullable=True)

@app.route("/contactInfo",methods=['GET','POST'])
def contactInfo():
    #to send encrypted string to email
    if(request.method == 'POST'):
        """Add entry to database"""
        name=request.form.get('name')
        email=request.form.get('email')
        subject=request.form.get('subject')
        msg=request.form.get('message')
        """ Insert into database
            LHS : database columns
            RHS: local variable
        """
        #contact table insertion
       
        entry=Contact(name=name,subject=subject,email=email,message=msg,date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        data=name+'\n'+email+'\n'+subject+'\n'+msg+'\n'
        server.sendmail(params['gmail-user'],params['send_to'],data)
        print('Mail sent')
        server.sendmail(params['gmail-user'],str(email),'You email is received.')
        return redirect('/message')

@app.route('/message')
def successMsg():
        return render_template('message.html')

dropzone=Dropzone(app)
csrf = CSRFProtect(app)
app.secret_key=params['secret-key']

#define routes
@app.route("/")
def Index():    
    sourceIP=request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    print(sourceIP)
    #user table insertion
    entry2=User(source_ip=sourceIP,date=datetime.now())
    db.session.add(entry2)
    db.session.commit()
    #to send encrypted string to email
    return render_template('index.html')

@app.route("/upload",methods=['GET','POST'])
def upload():
    global uploaded_file_path,uploaded_file_name
    msg='The file extenstion associated with your document is not supported or file is too large to handle.'
    if request.method == 'POST':
        file = request.files['file']
        print(file.content_type)
        if file.content_type in ['image/png','image/jpeg','image/jpg','image/gif','application/pdf','application/x-php','text/plain','text/x-python','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','application/vnd.ms-excel','video/mp4']:
            file.filename=secure_filename(file.filename)
            print(file.filename)
            file.save(os.path.join(app.config['UPLOADED_PATH'],file.filename))
            uploaded_file_path=os.path.join(app.config['UPLOADED_PATH'],file.filename)
            print('uploaded file ',uploaded_file_path)
            uploaded_file_name=file.filename
            return redirect("/display")
        else:
            return render_template('error.html',msg=msg)
    return render_template('dragndrop.html')

@app.route("/remove",methods=['GET','POST'])
def remove():
    global uploaded_file_path
    os.remove(uploaded_file_path)
    return redirect('/upload')

@app.route("/display")
def display():
    global uploaded_file_path,uploaded_file_name
    msg="File is not uploaded"
    try:
        filename, file_extension = os.path.splitext(uploaded_file_path)
    except :
        return render_template('error.html',msg=msg)
    if file_extension in ['.csv','.txt','.py','.php']:
        f = open(uploaded_file_path, 'r',errors='ignore')
        file_contents= f.readlines()
        return render_template('text.html',file_contents=file_contents)
    elif file_extension in ['.jpg','.png','.jpeg','.gif']:
        return render_template('image.html',filename=uploaded_file_name)
    elif file_extension in ['.pdf']:
        return render_template('pdf.html',filename=uploaded_file_name)
    elif file_extension in ['.xlsx','.xls']:
        df = pd.read_excel(uploaded_file_path)
        #render dataframe as html
        html = df.to_html()
        #write html to file
        text_file = open('/home/sidharth/render.dev/templates/xmlData.html', "w")
        text_file.write(html)
        text_file.close()
        return render_template('xmlData.html')
    elif file_extension in ['.mp4']:
        return render_template('video.html',filename=uploaded_file_name)
    else:
        return render_template('error.html')
    
@app.route('/contact')
def contactForm():
    return render_template('contact.html')

if __name__ == '__main__':
    excel.init_excel(app)
    app.run(debug=True,port=params['flask_port'])