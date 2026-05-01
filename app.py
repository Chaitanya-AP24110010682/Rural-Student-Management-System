import os
import random
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
MATERIALS_DIR = os.path.join(UPLOAD_DIR, 'materials')
HOMEWORK_DIR = os.path.join(UPLOAD_DIR, 'homework')

# Ensure directories exist
os.makedirs(MATERIALS_DIR, exist_ok=True)
os.makedirs(HOMEWORK_DIR, exist_ok=True)

# Helper function to read csv
def read_csv(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            df = pd.read_csv(filepath)
            return df
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
    return pd.DataFrame()

# Helper function to write csv
def write_csv(df, filename):
    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register/teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        df = read_csv('teachers.csv')
        if not df.empty and email in df['email'].values:
            flash('Email already registered', 'error')
            return redirect(url_for('register_teacher'))
            
        teacher_id = str(random.randint(100000, 999999))
        new_row = pd.DataFrame([{'teacher_id': teacher_id, 'name': name, 'email': email, 'password': password}])
        df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
        write_csv(df, 'teachers.csv')
        
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login_teacher'))
        
    return render_template('teacher_register.html')

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    teachers_df = read_csv('teachers.csv')
    teachers = teachers_df.to_dict('records') if not teachers_df.empty else []
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        teacher_id = request.form['teacher_id']
        
        df = read_csv('students.csv')
        if not df.empty and email in df['email'].values:
            flash('Email already registered', 'error')
            return redirect(url_for('register_student'))
            
        student_id = str(random.randint(100000, 999999))
        new_row = pd.DataFrame([{'student_id': student_id, 'name': name, 'email': email, 'password': password, 'teacher_id': teacher_id}])
        df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
        write_csv(df, 'students.csv')
        
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login_student'))
        
    return render_template('student_register.html', teachers=teachers)

@app.route('/login/teacher', methods=['GET', 'POST'])
def login_teacher():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        df = read_csv('teachers.csv')
        if not df.empty:
            user = df[(df['email'] == email) & (df['password'].astype(str) == password)]
            if not user.empty:
                session['role'] = 'teacher'
                session['id'] = str(user.iloc[0]['teacher_id'])
                session['name'] = user.iloc[0]['name']
                return redirect(url_for('teacher_dashboard'))
                
        flash('Invalid credentials', 'error')
    return render_template('teacher_login.html')

@app.route('/login/student', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        df = read_csv('students.csv')
        if not df.empty:
            user = df[(df['email'] == email) & (df['password'].astype(str) == password)]
            if not user.empty:
                session['role'] = 'student'
                session['id'] = str(user.iloc[0]['student_id'])
                session['name'] = user.iloc[0]['name']
                session['teacher_id'] = str(user.iloc[0]['teacher_id'])
                return redirect(url_for('student_dashboard'))
                
        flash('Invalid credentials', 'error')
    return render_template('student_login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    teacher_id = session['id']
    
    # Get students
    students_df = read_csv('students.csv')
    students = students_df[students_df['teacher_id'].astype(str) == teacher_id].to_dict('records') if not students_df.empty else []
    
    # Get materials
    materials_df = read_csv('materials.csv')
    materials = materials_df[materials_df['teacher_id'].astype(str) == teacher_id].to_dict('records') if not materials_df.empty else []
    
    # Get messages
    messages_df = read_csv('messages.csv')
    messages = messages_df[messages_df['receiver_id'].astype(str) == teacher_id].to_dict('records') if not messages_df.empty else []
    for m in messages:
        if pd.isna(m.get('reply')):
            m['reply'] = ''
            
    # Get homeworks
    homework_df = read_csv('homework.csv')
    homeworks = homework_df[homework_df['teacher_id'].astype(str) == teacher_id].to_dict('records') if not homework_df.empty else []
    for hw in homeworks:
        if 'grade' not in hw or pd.isna(hw.get('grade')):
            hw['grade'] = ''

    # Get notices
    notices_df = read_csv('notices.csv')
    notices = notices_df[notices_df['teacher_id'].astype(str) == teacher_id].to_dict('records') if not notices_df.empty else []
    
    return render_template('teacher_dashboard.html', students=students, materials=materials, messages=messages, homeworks=homeworks, notices=notices)

@app.route('/dashboard/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    student_id = session['id']
    teacher_id = session.get('teacher_id')
    
    # Get attendance
    attendance_df = read_csv('attendance.csv')
    attendance = attendance_df[attendance_df['student_id'].astype(str) == student_id].to_dict('records') if not attendance_df.empty else []
    
    # Get materials
    materials_df = read_csv('materials.csv')
    materials = materials_df[materials_df['teacher_id'].astype(str) == teacher_id].to_dict('records') if not materials_df.empty else []
    
    # Get messages
    messages_df = read_csv('messages.csv')
    messages = messages_df[messages_df['sender_id'].astype(str) == student_id].to_dict('records') if not messages_df.empty else []
    for m in messages:
        if pd.isna(m.get('reply')):
            m['reply'] = ''
            
    # Get homeworks
    homework_df = read_csv('homework.csv')
    homeworks = homework_df[homework_df['student_id'].astype(str) == student_id].to_dict('records') if not homework_df.empty else []
    for hw in homeworks:
        if 'grade' not in hw or pd.isna(hw.get('grade')):
            hw['grade'] = ''

    # Get notices
    notices_df = read_csv('notices.csv')
    notices = notices_df[notices_df['teacher_id'].astype(str) == teacher_id].to_dict('records') if not notices_df.empty else []
            
    return render_template('student_dashboard.html', attendance=attendance, materials=materials, messages=messages, homeworks=homeworks, notices=notices)

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    date = request.form.get('date')
    student_ids = request.form.getlist('student_id[]')
    
    students_df = read_csv('students.csv')
    
    attendance_records = []
    for sid in student_ids:
        status = request.form.get(f'status_{sid}')
        if status:
            student_name = students_df[students_df['student_id'].astype(str) == sid].iloc[0]['name'] if not students_df.empty else 'Unknown'
            attendance_records.append({
                'date': date,
                'student_id': sid,
                'student_name': student_name,
                'status': status
            })
            
    if attendance_records:
        df = read_csv('attendance.csv')
        new_df = pd.DataFrame(attendance_records)
        df = pd.concat([df, new_df], ignore_index=True) if not df.empty else new_df
        write_csv(df, 'attendance.csv')
        flash('Attendance marked successfully!', 'success')
        
    return redirect(url_for('teacher_dashboard'))

@app.route('/upload_material', methods=['POST'])
def upload_material():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    subject = request.form.get('subject')
    file = request.files.get('file')
    
    if file and file.filename:
        filename = secure_filename(file.filename)
        filename = f"{random.randint(1000, 9999)}_{filename}"
        file.save(os.path.join(MATERIALS_DIR, filename))
        
        material_id = str(random.randint(100000, 999999))
        new_record = pd.DataFrame([{
            'material_id': material_id,
            'teacher_id': session['id'],
            'filename': filename,
            'subject': subject,
            'upload_date': datetime.now().strftime('%Y-%m-%d')
        }])
        
        df = read_csv('materials.csv')
        df = pd.concat([df, new_record], ignore_index=True) if not df.empty else new_record
        write_csv(df, 'materials.csv')
        flash('Material uploaded successfully!', 'success')
        
    return redirect(url_for('teacher_dashboard'))

@app.route('/download_material/<filename>')
def download_material(filename):
    return send_from_directory(MATERIALS_DIR, filename, as_attachment=True)

@app.route('/send_message', methods=['POST'])
def send_message():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    message = request.form.get('message')
    if message:
        message_id = str(random.randint(100000, 999999))
        new_record = pd.DataFrame([{
            'message_id': message_id,
            'sender_id': session['id'],
            'receiver_id': session['teacher_id'],
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'reply': ''
        }])
        
        df = read_csv('messages.csv')
        df = pd.concat([df, new_record], ignore_index=True) if not df.empty else new_record
        write_csv(df, 'messages.csv')
        flash('Message sent to teacher.', 'success')
        
    return redirect(url_for('student_dashboard'))

@app.route('/reply_message', methods=['POST'])
def reply_message():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    message_id = request.form.get('message_id')
    reply = request.form.get('reply')
    
    if message_id and reply:
        df = read_csv('messages.csv')
        if not df.empty:
            df.loc[df['message_id'].astype(str) == message_id, 'reply'] = reply
            write_csv(df, 'messages.csv')
            flash('Reply sent.', 'success')
            
    return redirect(url_for('teacher_dashboard'))

@app.route('/upload_homework', methods=['POST'])
def upload_homework():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    subject = request.form.get('subject')
    file = request.files.get('file')
    
    if file and file.filename:
        filename = secure_filename(file.filename)
        filename = f"{random.randint(1000, 9999)}_{filename}"
        file.save(os.path.join(HOMEWORK_DIR, filename))
        
        homework_id = str(random.randint(100000, 999999))
        new_record = pd.DataFrame([{
            'homework_id': homework_id,
            'student_id': session['id'],
            'teacher_id': session['teacher_id'],
            'filename': filename,
            'subject': subject,
            'upload_date': datetime.now().strftime('%Y-%m-%d')
        }])
        
        df = read_csv('homework.csv')
        df = pd.concat([df, new_record], ignore_index=True) if not df.empty else new_record
        write_csv(df, 'homework.csv')
        flash('Homework submitted successfully!', 'success')
        
    return redirect(url_for('student_dashboard'))

@app.route('/download_homework/<filename>')
def download_homework(filename):
    if not session.get('role'):
        return redirect(url_for('index'))
    return send_from_directory(HOMEWORK_DIR, filename, as_attachment=True)

@app.route('/post_notice', methods=['POST'])
def post_notice():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    title = request.form.get('title')
    content = request.form.get('content')
    
    if title and content:
        notice_id = str(random.randint(100000, 999999))
        new_record = pd.DataFrame([{
            'notice_id': notice_id,
            'teacher_id': session['id'],
            'title': title,
            'content': content,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }])
        
        df = read_csv('notices.csv')
        df = pd.concat([df, new_record], ignore_index=True) if not df.empty else new_record
        write_csv(df, 'notices.csv')
        flash('Notice posted successfully.', 'success')
        
    return redirect(url_for('teacher_dashboard'))

@app.route('/grade_homework', methods=['POST'])
def grade_homework():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    homework_id = request.form.get('homework_id')
    grade = request.form.get('grade')
    
    if homework_id and grade:
        df = read_csv('homework.csv')
        if not df.empty:
            df.loc[df['homework_id'].astype(str) == homework_id, 'grade'] = grade
            write_csv(df, 'homework.csv')
            flash('Grade assigned successfully.', 'success')
            
    return redirect(url_for('teacher_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
