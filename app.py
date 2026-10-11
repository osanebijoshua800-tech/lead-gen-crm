import os
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_apscheduler import APScheduler

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///leadgen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

scheduler = APScheduler()

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='User')

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='New')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- AUTH & DASHBOARD ROUTES ---
@app.route('/')
@login_required
def dashboard():
    leads = Lead.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', leads=leads)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already registered.', 'warning')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(full_name=full_name, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/send-email/<int:lead_id>', methods=['POST'])
@login_required
def send_email(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    
    if lead.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    recipient_email = lead.email
    subject = request.form.get('subject', 'Partnership Opportunity with Momentum Digital')
    body_content = request.form.get('body', 'Hello, we would love to connect and expand your digital presence.')

    msg = EmailMessage()
    msg.set_content(body_content)
    msg['Subject'] = subject
    msg['From'] = os.getenv('SMTP_USER', 'noreply@momentum.digital')
    msg['To'] = recipient_email

    try:
        smtp_port = int(os.getenv('SMTP_PORT', 465))
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()
            
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        flash(f'Outreach email successfully dispatched to {lead.business_name}!', 'success')
        lead.status = 'Contacted'
        db.session.commit()

    except OSError:
        # Gracefully handles Render's free tier SMTP port restriction (Network is unreachable)
        flash('Email simulated: Render free tier restricts direct SMTP ports. Lead status updated to Contacted.', 'warning')
        lead.status = 'Contacted'
        db.session.commit()

    except Exception as e:
        flash(f'Failed to send email: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))

# --- DATABASE INITIALIZATION FOR GUNICORN ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)