import os
from flask import Flask, render_template, request, redirect, url_for, g, session, flash
import sqlite3
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  

# Database connection helper function
def get_db():
    DATABASE = 'attendance.db'
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    DATABASE = 'attendance.db'
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Home page to select role
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        
        # Validate student ID
        conn = get_db()
        student = conn.execute('SELECT * FROM Students WHERE id = ?', (student_id,)).fetchone()
        conn.close()
        
        if student:
            session['student_id'] = student_id
            return redirect(url_for('student_options'))
        else:
            flash('Invalid Student ID. Please try again.')
    
    return render_template('student_login.html')


@app.route('/student_options')
def student_options():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    return render_template('student_options.html')


@app.route('/view_student_attendance')
def view_student_attendance():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    db = get_db()
    cursor = db.cursor()

    # Retrieve attendance records for the logged-in student, including the excuse status
    cursor.execute("""
        SELECT date, status, excuse, excuse_status 
        FROM AttendanceRecord 
        WHERE student_id = ? 
        ORDER BY date DESC
    """, (student_id,))
    attendance_records = cursor.fetchall()

    return render_template('view_student_attendance.html', attendance_records=attendance_records)



@app.route('/submit_excuse', methods=['GET', 'POST'])
def submit_excuse():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        date = request.form['date']
        excuse = request.form['excuse']

        # Update the excuse and set the status to "wait to approve"
        cursor.execute("""
            UPDATE AttendanceRecord 
            SET excuse = ?, excuse_status = 'wait to approve'
            WHERE student_id = ? AND date = ? AND status = 'Absent'
        """, (excuse, student_id, date))
        db.commit()
        flash('Excuse submitted successfully and is waiting for approval.')
        return redirect(url_for('view_student_attendance'))

    # Get dates where the student was absent
    cursor.execute("""
        SELECT date 
        FROM AttendanceRecord 
        WHERE student_id = ? AND status = 'Absent'
    """, (student_id,))
    absent_dates = cursor.fetchall()

    return render_template('submit_excuse.html', absent_dates=absent_dates)



@app.route('/logout')
def logout():
    # Remove 'student_id' or 'instructor_id' from the session
    session.pop('student_id', None)
    session.pop('instructor_id', None)
    
    # Redirect to the role selection or home page
    return redirect(url_for('index'))



# Instructor login page
@app.route('/instructor_login', methods=['GET', 'POST'])
def instructor_login():
    if request.method == 'POST':
        instructor_id = request.form.get('instructor_id')
        
        # Validate instructor ID
        conn = get_db()
        instructor = conn.execute('SELECT * FROM Instructors WHERE id = ?', (instructor_id,)).fetchone()
        conn.close()
        
        if instructor:
            session['instructor_id'] = instructor_id
            return redirect(url_for('instructor_page'))
        else:
            flash('Invalid Instructor ID. Please try again.')
            return redirect(url_for('instructor_login'))
    return render_template('instructor_login.html')
# Instructor page - View classes
@app.route('/instructor')
def instructor_page():
    instructor_id = session.get('instructor_id')
    if not instructor_id:
        return redirect(url_for('instructor_login'))
    
    db = get_db()
    cursor = db.cursor()
    # Query classes for the instructor
    cursor.execute("SELECT id, name FROM Classes WHERE instructor_id = ?", (instructor_id,))
    classes = cursor.fetchall()
    
    return render_template('instructor_page.html', classes=classes)

@app.route('/class/<int:class_id>/view_attendance')
def view_attendance(class_id):
    if 'instructor_id' not in session:
        return redirect(url_for('instructor_login'))

    db = get_db()
    cursor = db.cursor()

    # Fetch attendance records for the selected class, including excuse status
    cursor.execute("""
        SELECT Students.name, AttendanceRecord.date, AttendanceRecord.status, AttendanceRecord.excuse_status
        FROM AttendanceRecord
        JOIN Students ON AttendanceRecord.student_id = Students.id
        WHERE Students.class_id = ?
    """, (class_id,))
    records = cursor.fetchall()

    return render_template('view_attendance.html', records=records)



@app.route('/class/<int:class_id>/mark_attendance', methods=['GET', 'POST'])
def mark_attendance(class_id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        student_ids = request.form.getlist('student_id')
        statuses = request.form.getlist('status')
        for student_id, status in zip(student_ids, statuses):
            cursor.execute("""
                INSERT INTO AttendanceRecord (student_id, date, status, class_id) 
                VALUES (?, ?, ?, ?)
            """, (student_id, request.form['date'], status, class_id))
        
        db.commit()
        return redirect(url_for('view_attendance', class_id=class_id))

    # Retrieve students for the class and print for verification
    cursor.execute("SELECT id, name FROM Students WHERE class_id = ?", (class_id,))
    students = cursor.fetchall()
    print("Retrieved students:", students)  # Debugging line

    # Convert to dictionary format if not already
    students = [{"id": row[0], "name": row[1]} for row in students]

    return render_template('mark_attendance.html', students=students, class_id=class_id)




@app.route('/instructor/<int:instructor_id>/classes')
def view_classes(instructor_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM Classes WHERE instructor_id = ?", (instructor_id,))
    classes = cursor.fetchall()
    return render_template('instructor_classes.html', classes=classes)



@app.route('/advisor_login', methods=['GET', 'POST'])
def advisor_login():
    if request.method == 'POST':
        advisor_id = request.form.get('advisor_id')
        
        # Validate advisor ID
        conn = get_db()
        advisor = conn.execute('SELECT * FROM Advisors WHERE id = ?', (advisor_id,)).fetchone()
        conn.close()
        
        if advisor:
            session['advisor_id'] = advisor_id
            return redirect(url_for('advisor_options'))
        else:
            flash('Invalid Advisor ID. Please try again.')
            return redirect(url_for('advisor_login'))
    return render_template('advisor_login.html')


@app.route('/advisor_options')
def advisor_options():
    if 'advisor_id' not in session:
        return redirect(url_for('advisor_login'))
    
    advisor_id = session['advisor_id']
    db = get_db()
    cursor = db.cursor()

    # Fetch classes assigned to this advisor
    cursor.execute("""
        SELECT id, name FROM Classes
        WHERE instructor_id = ?
    """, (advisor_id,))
    classes = cursor.fetchall()

    return render_template('advisor_options.html', classes=classes)



@app.route('/view_all_attendance/<int:class_id>')
def view_all_attendance(class_id):
    if 'advisor_id' not in session:
        return redirect(url_for('advisor_login'))

    advisor_id = session['advisor_id']
    db = get_db()
    cursor = db.cursor()

    # Fetch attendance records only for students assigned to this advisor
    cursor.execute("""
        SELECT Students.name, AttendanceRecord.date, AttendanceRecord.status, AttendanceRecord.excuse, AttendanceRecord.excuse_status
        FROM AttendanceRecord
        JOIN Students ON AttendanceRecord.student_id = Students.id
        WHERE Students.advisor_id = ?
    """, (advisor_id,))
    records = cursor.fetchall()

    return render_template('view_all_attendance.html', records=records)


@app.route('/review_excuses', methods=['GET', 'POST'])
def review_excuses():
    if 'advisor_id' not in session:
        return redirect(url_for('advisor_login'))

    advisor_id = session['advisor_id']
    db = get_db()
    cursor = db.cursor()

    # Fetch excuses only for students assigned to this advisor
    cursor.execute("""
        SELECT Students.id, AttendanceRecord.date, AttendanceRecord.excuse
        FROM AttendanceRecord
        JOIN Students ON AttendanceRecord.student_id = Students.id
        WHERE Students.advisor_id = ? AND AttendanceRecord.excuse IS NOT NULL AND AttendanceRecord.excuse_status = 'wait to approve'
    """, (advisor_id,))
    excuses = cursor.fetchall()

    # Debugging: Print the fetched data
    print("Fetched excuses:", excuses)  # Check if data is being fetched

    if request.method == 'POST':
        student_id = request.form['student_id']
        date = request.form['date']
        action = request.form['action']

        if action == 'approve':
            status = 'approved'
        elif action == 'reject':
            status = 'rejected'
        else:
            return "Invalid action", 400

        cursor.execute("""
            UPDATE AttendanceRecord
            SET excuse_status = ?
            WHERE student_id = ? AND date = ?
        """, (status, student_id, date))

        db.commit()

        flash(f'Excuse for student ID {student_id} has been {status}.')
        return redirect(url_for('review_excuses'))

    return render_template('review_excuses.html', excuses=excuses)

@app.route('/logout')
def logout1():
    session.clear()
    return redirect(url_for('index'))


# Run the app
if __name__ == '__main__':
    
    app.run(debug=True)

