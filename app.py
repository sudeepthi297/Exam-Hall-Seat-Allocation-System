from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import math
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "exam_secret_key"

# Helper to read/write CSV
CSV_FILE = 'students.csv'

def get_df():
    return pd.read_csv(CSV_FILE)

def save_df(df):
    df.to_csv(CSV_FILE, index=False)

# Conflict Detection Logic
def is_safe(grid, row, col, student, cols):
    if col > 0 and grid[row][col-1]:
        left = grid[row][col-1]
        if left['Branch'] == student['Branch'] or left['Subject'] == student['Subject']:
            return False
    if row > 0 and grid[row-1][col]:
        front = grid[row-1][col]
        if front['Branch'] == student['Branch'] or front['Subject'] == student['Subject']:
            return False
    return True

def allocate_seats(df):
    students = df.to_dict('records')
    cols = 4
    rows = math.ceil(len(students) / cols)
    grid = [[None for _ in range(cols)] for _ in range(rows)]
    allocated_list = []
    student_pool = students.copy()

    for r in range(rows):
        for c in range(cols):
            for i, student in enumerate(student_pool):
                if is_safe(grid, r, c, student, cols):
                    grid[r][c] = student
                    seat_id = f"R{r+1}-S{c+1}"
                    allocated_list.append({**student, 'Seat': seat_id})
                    student_pool.pop(i)
                    break
    return allocated_list

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/<user_type>', methods=['GET', 'POST'])
def login(user_type):
    if request.method == 'POST':
        user_id = request.form.get('id')
        password = request.form.get('password')
        
        if user_type == 'admin' and user_id == 'admin' and password == 'admin123':
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        
        elif user_type == 'student':
            df = get_df()
            # Verify both ID and Password
            user_row = df[(df['Student_ID'].astype(str) == user_id) & (df['password'].astype(str) == password)]
            if not user_row.empty:
                session['role'] = 'student'
                session['user_id'] = user_id
                return redirect(url_for('student_dashboard'))
        
        return "Invalid Credentials. <a href='/'>Try again</a>"
    return render_template('login_form.html', user_type=user_type)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user_id = request.form.get('id').strip()
        df = get_df()

        #cleanup: remove any accidental spaces from columns
        df.columns = df.columns.str.strip()

        #cleanup values (remove spaces around '101', '111', etc.)
        # This ensures "101 " becomes "101"
        df['Student_ID'] = df['Student_ID'].astype('str').str.strip()

        
        if user_id in df['Student_ID'].astype(str).values or user_id == 'admin':
            #generate otp
            otp = str(random.randint(100000, 999999))

            # Configuration
            sender_email = "sudeepthi297@gmail.com"
            sender_password = "tlez ecqn coyl dzbw"
            receiver_email = "sudeepthiammulu@gmail.com"

            #create email content
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = "Your password reset OTP"

            body = f"Hello, Your OTP for resetting your password is: {otp}."
            msg.attach(MIMEText(body, "plain"))

            #printing the msg
            print(msg.as_string())

            try:
                #connect to gmail's stp server
                server = smtplib.SMTP("smtp.gmail.com",587)
                server.starttls()   #secure connection
                server.login(sender_email, sender_password)

                #send msg and close
                server.send_message(msg)
                server.quit()
                print(f"OTP sent successfully to receiver: {receiver_email}")

            #error occurred in during smtp connection and sending msg.    
            except Exception as e:
                print(f"Error : {e}")


            session['reset_otp'] = otp
            session['reset_user_id'] = user_id
            print(f"--- DEBUG OTP: {otp} ---") # Simulated SMS/Email
            return render_template('reset_password.html', step='otp')
        
        return "User ID not found."
    return render_template('reset_password.html', step='request')


@app.route('/reset_password', methods=['POST'])
def reset_password():
    input_otp = request.form.get('otp')
    new_password = request.form.get('new_password')
    
    
    if input_otp == session.get('reset_otp'):
        user_id = session.get('reset_user_id')
        
        if user_id != 'admin':
            df = get_df()
            df.loc[df['Student_ID'].astype(str) == user_id, 'password'] = new_password
            save_df(df)
        
        session.pop('reset_otp', None)
        return "Password updated! <a href='/'>Login</a>"
    
    return "Invalid OTP."

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    df = get_df()
    data = allocate_seats(df)
    return render_template('admin.html', allocation=data)

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student': return redirect(url_for('index'))
    df = get_df()
    all_seats = allocate_seats(df)
    student_data = next((s for s in all_seats if str(s['Student_ID']) == session.get('user_id')), None)
    return render_template('student.html', data=student_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)