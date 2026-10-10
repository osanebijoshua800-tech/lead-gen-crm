from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Email, URL, Length

class LeadForm(FlaskForm):
    business_name = StringField(
        "Business Name", 
        validators=[DataRequired(message="Business Name is required."), Length(max=150)]
    )
    category = StringField("Category", validators=[Optional(), Length(max=100)])
    location = StringField("Location", validators=[Optional(), Length(max=100)])
    website = StringField(
        "Website URL", 
        validators=[Optional(), URL(message="Please enter a valid URL (e.g. https://example.com)."), Length(max=255)]
    )
    phone = StringField("Phone Number", validators=[Optional(), Length(max=50)])
    email = StringField("Email Address", validators=[Optional(), Email(message="Please enter a valid email address."), Length(max=120)])
    social_media = StringField("Social Handles", validators=[Optional(), Length(max=255)])
    status = SelectField(
        "Pipeline Status", 
        choices=[
            ("New", "New"),
            ("Contacted", "Contacted"),
            ("Interested", "Interested"),
            ("Converted", "Converted"),
            ("Rejected", "Rejected")
        ],
        default="New"
    )
    notes = TextAreaField("Notes & Activity Log", validators=[Optional()])
    submit = SubmitField("Save Lead")