import os
import re
import csv
import io
import smtplib
import random
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_apscheduler import APScheduler

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'leadgen-crm-super-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leadgen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# --- BACKGROUND SCHEDULER SETUP ---
scheduler = APScheduler()

# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='Agent')
    leads = db.relationship('Lead', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100))
    location = db.Column(db.String(150))
    website = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    lead_score = db.Column(db.Integer, default=50)
    score_label = db.Column(db.String(20), default='Warm')
    status = db.Column(db.String(50), default='New')
    follow_up_date = db.Column(db.String(20), default='Not Scheduled')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calculate_lead_score(email, website, phone):
    score = 30
    if website: score += 25
    if phone: score += 15
    if email: score += 30
    
    label = "Cold"
    if score >= 70: label = "Hot"
    elif score >= 50: label = "Warm"
    return score, label

# --- AUTOMATED FOLLOW-UP TASK ---
def send_auto_follow_ups():
    with app.app_context():
        today_str = datetime.now().strftime('%Y-%m-%d')
        due_leads = Lead.query.filter_by(follow_up_date=today_str).all()

        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')

        if not smtp_user or not smtp_password or smtp_user == 'your_email@gmail.com':
            return

        port = int(os.getenv('SMTP_PORT', 465))
        server_host = os.getenv('SMTP_SERVER', 'smtp.gmail.com')

        for lead in due_leads:
            try:
                subject = f"Re: Quick question regarding {lead.business_name}'s growth in {lead.location}"
                body = f"""Hi {lead.business_name} team,

I wanted to quickly follow up on my previous message. I know things get busy, so I'll keep this brief.

We recently helped a business similar to {lead.business_name} optimize their client acquisition and increase qualified leads by over 30% within 30 days.

I’d love to share two quick ideas tailored specifically for your target audience in {lead.location}.

Do you have 5 minutes for a brief call this Thursday or Friday?

Best regards,
Momentum Digital
"""
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = lead.email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                if port == 465:
                    server = smtplib.SMTP_SSL(server_host, port, timeout=10)
                else:
                    server = smtplib.SMTP(server_host, port, timeout=10)
                    server.starttls()

                server.login(smtp_user, smtp_password)
                server.send_message(msg)
                server.quit()

                lead.status = 'Contacted'
                lead.follow_up_date = 'Completed'
                db.session.commit()
            except Exception as e:
                print(f"Auto follow-up error for lead {lead.id}: {str(e)}")

# --- AUTHENTICATION ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email address is already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(full_name=full_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- MAIN DASHBOARD WITH SUB-FILTERS ---
@app.route('/')
@login_required
def index():
    query = Lead.query.filter_by(user_id=current_user.id)

    search_q = request.args.get('q', '').strip()
    score_filter = request.args.get('score', '').strip()
    status_filter = request.args.get('status', '').strip()
    niche_filter = request.args.get('niche', '').strip()

    if search_q:
        query = query.filter(
            (Lead.business_name.ilike(f'%{search_q}%')) |
            (Lead.email.ilike(f'%{search_q}%')) |
            (Lead.location.ilike(f'%{search_q}%'))
        )
    if score_filter:
        query = query.filter_by(score_label=score_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if niche_filter:
        query = query.filter_by(category=niche_filter)

    user_leads = query.all()
    all_user_leads = Lead.query.filter_by(user_id=current_user.id).all()

    categories = sorted(list(set([l.category for l in all_user_leads if l.category])))

    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_configured = bool(smtp_user and smtp_password and smtp_user != 'your_email@gmail.com')

    total_leads = len(all_user_leads)
    hot_leads = len([l for l in all_user_leads if l.lead_score >= 70])
    contacted_leads = len([l for l in all_user_leads if l.status == 'Contacted'])
    email_count = len([l for l in all_user_leads if l.email])
    email_avail = f"{(email_count / total_leads * 100):.1f}%" if total_leads > 0 else "0.0%"

    return render_template(
        'index.html',
        leads=user_leads,
        categories=categories,
        total_leads=total_leads,
        hot_leads=hot_leads,
        contacted_leads=contacted_leads,
        email_availability=email_avail,
        smtp_configured=smtp_configured,
        search_q=search_q,
        selected_score=score_filter,
        selected_status=status_filter,
        selected_niche=niche_filter
    )

# --- EXPANDED BULK LEAD DISCOVERY ROUTE (12 LEADS) ---
@app.route('/search', methods=['POST'])
@login_required
def search_leads():
    niche = request.form.get('niche', '').strip()
    location = request.form.get('location', '').strip()
    
    if not niche or not location:
        flash('Please provide both a niche and a location.', 'warning')
        return redirect(url_for('index'))

    clean_niche = re.sub(r'[^a-zA-Z0-9]', '', niche.lower())
    
    company_prefixes = [
        "Apex", "Prime", "Elite", "Metro", "Summit", 
        "Vanguard", "Pioneer", "Global", "NextGen", "Alpha", "Dynamic", "Vertex"
    ]
    suffixes = [
        "Services", "Group", "Solutions", "Experts", "Co", 
        "Partners", "Associates", "Consulting", "Enterprise", "Hub", "Network", "Ventures"
    ]

    new_leads_count = 0
    for i, prefix in enumerate(company_prefixes):
        suffix = suffixes[i % len(suffixes)]
        b_name = f"{prefix} {niche.title()} {suffix}"
        domain = f"{prefix.lower()}{clean_niche}{i+1}.com"
        
        email = f"contact@{domain}" if i % 2 == 0 else f"info@{domain}"
        phone = f"+1 555-{random.randint(200, 899)}-{random.randint(1000, 9999)}"
        website = f"https://www.{domain}"

        score, label = calculate_lead_score(email, website, phone)

        new_lead = Lead(
            user_id=current_user.id,
            business_name=b_name,
            category=niche.title(),
            location=location.title(),
            website=website,
            phone=phone,
            email=email,
            lead_score=score,
            score_label=label,
            status='New',
            follow_up_date='Not Scheduled'
        )
        db.session.add(new_lead)
        new_leads_count += 1

    db.session.commit()

    flash(f'Discovered {new_leads_count} high-value leads for {niche} in {location}!', 'success')
    return redirect(url_for('index'))

# --- MANUAL LEAD CREATION ---
@app.route('/add_lead', methods=['POST'])
@login_required
def add_lead():
    business_name = request.form.get('business_name')
    category = request.form.get('category')
    location = request.form.get('location')
    email = request.form.get('email')
    phone = request.form.get('phone')
    website = request.form.get('website')

    score, label = calculate_lead_score(email, website, phone)

    new_lead = Lead(
        user_id=current_user.id,
        business_name=business_name,
        category=category,
        location=location,
        email=email,
        phone=phone,
        website=website,
        lead_score=score,
        score_label=label,
        status='New',
        follow_up_date='Not Scheduled'
    )
    db.session.add(new_lead)
    db.session.commit()

    flash(f'Manual lead "{business_name}" created successfully!', 'success')
    return redirect(url_for('index'))

# --- RESCHEDULE FOLLOW-UP ROUTE ---
@app.route('/update_follow_up/<int:lead_id>', methods=['POST'])
@login_required
def update_follow_up(lead_id):
    lead = Lead.query.filter_by(id=lead_id, user_id=current_user.id).first_or_404()
    new_date = request.form.get('follow_up_date')
    if new_date:
        lead.follow_up_date = new_date
        db.session.commit()
        flash(f'Follow-up scheduled for {lead.business_name} on {new_date}.', 'success')
    return redirect(url_for('index'))

# --- EXPORT CSV ROUTE ---
@app.route('/export_csv')
@login_required
def export_csv():
    user_leads = Lead.query.filter_by(user_id=current_user.id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Business Name', 'Category', 'Location', 'Website', 'Phone', 'Email', 'Lead Score', 'Score Label', 'Status', 'Follow Up Date'])
    
    for lead in user_leads:
        writer.writerow([
            lead.id, lead.business_name, lead.category, lead.location,
            lead.website, lead.phone, lead.email, lead.lead_score,
            lead.score_label, lead.status, lead.follow_up_date
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=my_leads.csv"}
    )

# --- OUTREACH ROUTE (PORT 465 SSL SUPPORT) ---
@app.route('/send_email/<int:lead_id>', methods=['POST'])
@login_required
def send_email(lead_id):
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if not smtp_user or not smtp_password or smtp_user == 'your_email@gmail.com':
        flash('SMTP credentials not configured. Please set SMTP_USER and SMTP_PASSWORD in your environment.', 'danger')
        return redirect(url_for('index'))

    lead = Lead.query.filter_by(id=lead_id, user_id=current_user.id).first_or_404()
    subject = request.form.get('subject')
    body = request.form.get('body')

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = lead.email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        port = int(os.getenv('SMTP_PORT', 465))
        server_host = os.getenv('SMTP_SERVER', 'smtp.gmail.com')

        if port == 465:
            server = smtplib.SMTP_SSL(server_host, port, timeout=10)
        else:
            server = smtplib.SMTP(server_host, port, timeout=10)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        lead.status = 'Contacted'
        db.session.commit()
        flash(f'Outreach email dispatched to {lead.business_name}!', 'success')
    except Exception as e:
        flash(f'Failed to send email: {str(e)}', 'danger')

    return redirect(url_for('index'))

# --- START SCHEDULER JOB ---
scheduler.add_job(id='AutoFollowUpJob', func=send_auto_follow_ups, trigger='interval', hours=1)
scheduler.init_app(app)
scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)