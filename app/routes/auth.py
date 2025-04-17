from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User
from app import db
from werkzeug.security import generate_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard.index'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@auth.route('/users', methods=['GET'])
@login_required
def user_list():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    users = User.query.all()
    return render_template('auth/users.html', users=users)

@auth.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
        else:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=is_admin
            )
            db.session.add(user)
            db.session.commit()
            flash('User created successfully.', 'success')
            return redirect(url_for('auth.user_list'))
            
    return render_template('auth/add_user.html')

@auth.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        is_admin = request.form.get('is_admin') == 'on'
        new_password = request.form.get('new_password')
        
        # Check if username exists and is not the current user's username
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash('Username already exists.', 'danger')
            return render_template('auth/edit_user.html', user=user)
        
        # Check if email exists and is not the current user's email
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user.id:
            flash('Email already exists.', 'danger')
            return render_template('auth/edit_user.html', user=user)
        
        # Update user information
        user.username = username
        user.email = email
        user.is_admin = is_admin
        
        # Update password if provided
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('auth.user_list'))
            
    return render_template('auth/edit_user.html', user=user)

@auth.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('auth.user_list'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('auth.user_list'))