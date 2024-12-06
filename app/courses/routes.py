from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from app import db
from app.courses import bp
from app.models import Course, Enrollment
from app.courses.forms import CourseForm
from datetime import datetime

@bp.route('/browse')
def browse():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Course.query.filter_by(is_published=True)
    if search:
        query = query.filter(Course.title.ilike(f'%{search}%'))
    
    courses = query.order_by(Course.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False)
    
    return render_template('courses/browse.html', 
                         title='Browse Courses',
                         courses=courses,
                         search=search)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role not in ['admin', 'instructor']:
        abort(403)
    
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            instructor_id=current_user.id
        )
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully!', 'success')
        return redirect(url_for('courses.manage', course_id=course.id))
    
    return render_template('courses/create.html', 
                         title='Create Course',
                         form=form)

@bp.route('/<int:course_id>/manage', methods=['GET', 'POST'])
@login_required
def manage(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id and current_user.role != 'admin':
        abort(403)
    
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.price = form.price.data
        db.session.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('courses.manage', course_id=course.id))
    
    return render_template('courses/manage.html',
                         title=f'Manage {course.title}',
                         course=course,
                         form=form)

@bp.route('/<int:course_id>')
def view(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    
    if current_user.is_authenticated:
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        if enrollment:
            is_enrolled = True
    
    return render_template('courses/view.html',
                         title=course.title,
                         course=course,
                         is_enrolled=is_enrolled)

@bp.route('/<int:course_id>/enroll')
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    if Enrollment.query.filter_by(student_id=current_user.id, course_id=course.id).first():
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('courses.view', course_id=course.id))
    
    enrollment = Enrollment(student_id=current_user.id, course_id=course.id)
    db.session.add(enrollment)
    db.session.commit()
    flash('Successfully enrolled in the course!', 'success')
    return redirect(url_for('courses.view', course_id=course.id))

@bp.route('/my-courses')
@login_required
def my_courses():
    if current_user.role in ['admin', 'instructor']:
        created_courses = Course.query.filter_by(instructor_id=current_user.id).all()
    else:
        created_courses = []
    
    enrolled_courses = [
        enrollment.course for enrollment in current_user.enrolled_courses
    ]
    
    return render_template('courses/my_courses.html',
                         title='My Courses',
                         created_courses=created_courses,
                         enrolled_courses=enrolled_courses)

@bp.route('/<int:course_id>/toggle-publish', methods=['POST'])
@login_required
def toggle_publish(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id and current_user.role != 'admin':
        abort(403)
    
    course.is_published = not course.is_published
    db.session.commit()
    
    status = 'published' if course.is_published else 'unpublished'
    flash(f'Course {status} successfully!', 'success')
    return redirect(url_for('courses.manage', course_id=course.id))
