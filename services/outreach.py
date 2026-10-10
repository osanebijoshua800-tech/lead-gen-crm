import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def render_email_template(template_str, lead):
    """Replaces dynamic tags in email body templates with lead details."""
    rendered = template_str.replace("{{ business_name }}", lead.business_name)
    rendered = rendered.replace("{{ category }}", lead.category or "business")
    rendered = rendered.replace("{{ location }}", lead.location or "your area")
    return rendered


def send_lead_email(to_email, subject, body):
    """Sends an outbound email via SMTP configuration from environment variables."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        return (
            False,
            "SMTP credentials not configured. Please set SMTP_USER and"
            " SMTP_PASSWORD in your environment.",
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"