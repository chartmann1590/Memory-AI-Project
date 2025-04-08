# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, current_user
from app.models import User
from app import db
from authlib.integrations.flask_client import OAuth

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def get_oauth_client(app):
    oauth = OAuth(app)
    authentik = oauth.register(
        name='authentik',
        client_id=app.config['AUTHENTIK_CLIENT_ID'],
        client_secret=app.config['AUTHENTIK_CLIENT_SECRET'],
        server_metadata_url=f"{app.config['AUTHENTIK_SSO_URL']}/.well-known/openid-configuration",
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    return authentik

# ----- Local Registration -----
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))  # Update to your landing page
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        # Validate form fields
        if not username or not email or not password:
            flash('Please fill in all fields.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            # Check if user already exists
            existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
            if existing_user:
                flash('A user with that email or username already exists.', 'danger')
            else:
                new_user = User(username=username, email=email)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('auth.login'))
    return render_template('register.html')

# ----- Local Login -----
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Update to your landing page
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))  # Change to your main route
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

# ----- Logout -----
@auth_bp.route('/logout')
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for('auth.login'))

# ----- SSO Login -----
@auth_bp.route('/sso/login')
def sso_login():
    # Redirect the user to the Authentik SSO login page
    authentik = get_oauth_client(current_app)
    redirect_uri = current_app.config['AUTHENTIK_REDIRECT_URI']
    return authentik.authorize_redirect(redirect_uri)

# ----- SSO Callback -----
@auth_bp.route('/sso/callback')
def sso_callback():
    authentik = get_oauth_client(current_app)
    token = authentik.authorize_access_token()  # Exchange code for token
    user_info = authentik.parse_id_token(token)
    email = user_info.get('email')

    if not email:
        flash("SSO did not return an email.", 'danger')
        return redirect(url_for('auth.login'))

    # Check if local user exists; create one if not (username is optional)
    user = User.query.filter_by(email=email).first()
    if not user:
        # Optionally derive a username from the email or set it to None.
        user = User(username=None, email=email)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in via SSO successfully!", "success")
    return redirect(url_for('main.index'))  # Adjust to your landing page route
