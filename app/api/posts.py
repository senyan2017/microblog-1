import sqlalchemy as sa
from flask import request, url_for, abort
from langdetect import detect, LangDetectException
from app import db
from app.models import Post, User
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request


@bp.route('/posts/<int:id>', methods=['GET'])
@token_auth.login_required
def get_post(id):
    return db.get_or_404(Post, id).to_dict()


@bp.route('/posts', methods=['GET'])
@token_auth.login_required
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=per_page, error_out=False)
    data = {
        'items': [post.to_dict() for post in posts.items],
        '_meta': {
            'page': page,
            'per_page': per_page,
            'total_pages': posts.pages,
            'total_items': posts.total
        },
        '_links': {
            'self': url_for('api.get_posts', page=page, per_page=per_page),
            'next': url_for('api.get_posts', page=page + 1,
                            per_page=per_page) if posts.has_next else None,
            'prev': url_for('api.get_posts', page=page - 1,
                            per_page=per_page) if posts.has_prev else None
        }
    }
    return data


@bp.route('/posts', methods=['POST'])
@token_auth.login_required
def create_post():
    data = request.get_json()
    if 'body' not in data or not data['body'].strip():
        return bad_request('must include a non-empty body field')
    if len(data['body']) > 140:
        return bad_request('body must be 140 characters or fewer')
    post = Post(author=token_auth.current_user())
    post.from_dict(data)
    try:
        post.language = detect(data['body'])
    except LangDetectException:
        post.language = ''
    db.session.add(post)
    db.session.commit()
    return post.to_dict(), 201, {'Location': url_for('api.get_post',
                                                      id=post.id)}


@bp.route('/posts/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_post(id):
    post = db.get_or_404(Post, id)
    if post.author != token_auth.current_user():
        abort(403)
    data = request.get_json()
    if 'body' not in data or not data['body'].strip():
        return bad_request('must include a non-empty body field')
    if len(data['body']) > 140:
        return bad_request('body must be 140 characters or fewer')
    post.from_dict(data)
    try:
        post.language = detect(data['body'])
    except LangDetectException:
        post.language = ''
    db.session.commit()
    return post.to_dict()


@bp.route('/posts/<int:id>', methods=['DELETE'])
@token_auth.login_required
def delete_post(id):
    post = db.get_or_404(Post, id)
    if post.author != token_auth.current_user():
        abort(403)
    db.session.delete(post)
    db.session.commit()
    return '', 204


@bp.route('/users/<int:id>/posts', methods=['GET'])
@token_auth.login_required
def get_user_posts(id):
    user = db.get_or_404(User, id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=per_page, error_out=False)
    data = {
        'items': [post.to_dict() for post in posts.items],
        '_meta': {
            'page': page,
            'per_page': per_page,
            'total_pages': posts.pages,
            'total_items': posts.total
        },
        '_links': {
            'self': url_for('api.get_user_posts', id=id, page=page,
                            per_page=per_page),
            'next': url_for('api.get_user_posts', id=id, page=page + 1,
                            per_page=per_page) if posts.has_next else None,
            'prev': url_for('api.get_user_posts', id=id, page=page - 1,
                            per_page=per_page) if posts.has_prev else None
        }
    }
    return data
