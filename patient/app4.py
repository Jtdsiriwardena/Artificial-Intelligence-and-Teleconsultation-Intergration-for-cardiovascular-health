from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response, flash
import random
import json
import pickle
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model
import mysql.connector
import pymysql
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import datetime
import joblib

app4 = Flask(__name__)
app4.secret_key = 'session@21117'


# Connect to MySQL database--------------------------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="admin"
)
cursor = db.cursor()



# make appointments----------------------------------------------------
@app4.route('/make_appointment', methods=['GET', 'POST'])
def make_appointment():
    if request.method == 'POST':
        nic_number = request.form['nic_number']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        age = request.form['age']
        telephone = request.form['telephone']
        email = request.form['email']
        date = request.form['date']
        time = request.form['time']

        sql = "INSERT INTO appointments (nic_number, first_name, last_name, gender, age, telephone, email, date, time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (nic_number, first_name, last_name, gender, age, telephone, email, date, time)
        cursor.execute(sql, val)
        db.commit()

        return redirect('/make_appointment')
    return render_template('dashboard.html')



#fetch patients details based on NIC Number---------------------------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'admin'
}

@app4.route('/fetch_patient_details', methods=['POST'])
def fetch_patient_details():
    data = request.json
    nic_number = data.get('nic_number')
    
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        cursor.execute("SELECT first_name, last_name, gender, age, telephone, email FROM patients WHERE nic_number = %s", (nic_number,))
        patient_details = cursor.fetchone()
    except Exception as e:
        print("Error fetching patient details:", e)
        patient_details = None
    finally:
        cursor.close()
        conn.close()
    
    return jsonify(patient_details)



# Retrieve prescription based on logged-in patients email-------------------------------
def get_user_feedback(email):
    try:
        cursor.execute("SELECT * FROM feedback WHERE email = %s ORDER BY date DESC LIMIT 1", (email,))
        feedback = cursor.fetchall()
        return feedback
    except mysql.connector.Error as err:
        print(err)
        return None
    


# Retrieve appointments for the logged-in patients email------------------------------------
def get_user_appointment(email):
    try:
        
        cursor.execute("SELECT * FROM appointments WHERE email = %s", (email,))
        appointments = cursor.fetchall()
        return appointments
    except mysql.connector.Error as err:
        print(err)
        return None



# patient signin-----------------------------------------------------------
@app4.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        nic_number = request.form['nic_number']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        age = request.form['age']
        telephone = request.form['telephone']
        email = request.form['email']
        password = request.form['password']

        current_month = datetime.datetime.now().strftime("%B")

        cursor.execute("SELECT * FROM patients WHERE email = %s", (email,))
        result = cursor.fetchone()
        if result:
            return 'User already exists!'

        sql = "INSERT INTO patients (nic_number, first_name, last_name, gender, age, telephone, email, password, current_month) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (nic_number, first_name, last_name, gender, age, telephone, email, password, current_month)
        cursor.execute(sql, val)
        db.commit()

        return redirect('/login')
    else:
        return render_template('signin.html')

    

#patient login----------------------------------------------------
@app4.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            cursor.execute("SELECT * FROM patients WHERE email = %s AND password = %s", (email, password))
            result = cursor.fetchone()

            if result:
                session['logged_user_email'] = email
                session['logged_user_first_name'] = result[2]

                return redirect('/dashboard')

            else:
                return 'Invalid email or password!'

        except mysql.connector.Error as err:
            print(err)
            return 'Error occurred while processing your request. Please try again later.'

    return render_template('login.html')



#retrive user profile details--------------------------------------------------
@app4.route('/profile')
def profile():
    if 'logged_user_email' in session:
        email = session.get('logged_user_email')
        cursor.execute("SELECT last_name, gender, age, telephone, password FROM patients WHERE email = %s", (email,))
        user_info = cursor.fetchone()

        if user_info:
            return render_template('profile.html',
                                   logged_user_first_name=session.get('logged_user_first_name'),
                                   logged_user_email=session.get('logged_user_email'),
                                   last_name=user_info[0],
                                   gender=user_info[1],
                                   age=user_info[2],
                                   telephone=user_info[3],
                                   password=user_info[4])
        else:
            return 'User information not found!'
    else:
        return redirect('/login')



#update password-------------------------------------------------
@app4.route('/update_password', methods=['POST'])
def update_password():
    if 'logged_user_email' in session:
        new_password = request.form['new_password']
        email = session['logged_user_email']
        
        try:
            cursor.execute("UPDATE patients SET password = %s WHERE email = %s", (new_password, email))
            db.commit()
            return redirect('/profile')
        except mysql.connector.Error as err:
            print(err)
            return 'Error occurred while updating password. Please try again later.'
    else:
        return redirect('/login')
    


#logout----------------------------------------------
@app4.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.clear()
        return redirect(url_for('login'))
    return redirect(url_for('login'))

@app4.route('/dashboard')
def dashboard():
    if 'logged_user_email' in session:
        email = session['logged_user_email']
        feedback = get_user_feedback(email)
        appointments = get_user_appointment(email)
        return render_template('dashboard.html', feedback=feedback, appointments=appointments)
    else:
        return redirect('/login')


#route for display prescription for logged in user--------------------------------
@app4.route('/prescription')
def prescription():
    if 'logged_user_email' in session:
        email = session['logged_user_email']
        feedback = get_user_feedback(email)
        return render_template('prescription.html', feedback=feedback)
    else:
        return redirect('/login')


#route for display current appointments for logged in user------------------------------------
@app4.route('/my_appointment')
def view_appointment():
    if 'logged_user_email' in session:
        email = session['logged_user_email']
        appointments = get_user_appointment(email)
        return render_template('my_appointment.html', appointments=appointments)
    else:
        return redirect('/login')


#route for cancel appointments----------------------------------------
@app4.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    try:
        cursor.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
        appointment = cursor.fetchone()

        if appointment:
            cursor.execute("INSERT INTO cancelled (nic_number, first_name, last_name, gender, age, telephone, email, date, time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           (appointment[1], appointment[2], appointment[3], appointment[4], appointment[5], appointment[6], appointment[7], appointment[8], appointment[9]))
            db.commit()

            cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
            db.commit()

            return redirect('/dashboard')
        else:
            return "Appointment not found"
    except mysql.connector.Error as err:
        print(err)
        return "Error occurred while cancelling appointment"




#routes----------------------------------------------------------------
@app4.route('/')
def index():
    return render_template('index.html')

@app4.route('/appointment')
def appointment():
    return render_template('appointment.html')

@app4.route('/my_appointment')
def my_appointment():
    return render_template('my_appointment.html')

@app4.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app4.route('/consultation')
def consultation():
    return render_template('consultation.html')



#Risk Predictor------------------------------------------------------

# Load the trained model
model = joblib.load('random_forest_model.pkl')

@app4.route('/')
def home():
    return render_template('index.html')

@app4.route('/predict', methods=['POST'])
def predict():
    # Get the input data from the form
    gender = float(request.form['gender'])
    age = float(request.form['age'])
    cigs_per_day = float(request.form['cigs_per_day'])
    bp_meds = float(request.form['bp_meds'])
    prevalent_hyp = float(request.form['prevalent_hyp'])
    bmi = float(request.form['BMI'])
    tot_chol = float(request.form['tot_chol'])
    sys_bp = float(request.form['sys_bp'])
    dia_bp = float(request.form['dia_bp'])
    glucose = float(request.form['glucose'])
    
    # Make prediction
    prediction = model.predict([[age, gender, cigs_per_day, bp_meds, prevalent_hyp, bmi, tot_chol, sys_bp, dia_bp, glucose]])
    
    # final output
    if prediction[0] == 1:
        result = 'There is a risk of cardiovascular disease'
    else:
        result = 'You are safe from cardiovascular disease'
    
    return jsonify({'result': result})


if __name__ == '__main__':
    app4.run(debug=True, port=5004)
