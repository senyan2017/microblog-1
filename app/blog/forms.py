from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, \
    SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional
from flask_babel import lazy_gettext as _l


class ArticleForm(FlaskForm):
    title = StringField(_l('Title'), validators=[
        DataRequired(), Length(min=1, max=200)])
    summary = TextAreaField(_l('Summary'), validators=[
        Optional(), Length(max=500)])
    content = TextAreaField(_l('Content'), validators=[DataRequired()])
    cover_image = StringField(_l('Cover Image URL'), validators=[
        Optional(), Length(max=300)])
    category_id = SelectField(_l('Category'), coerce=int,
                              validators=[Optional()])
    tags = StringField(_l('Tags (comma separated)'), validators=[Optional()])
    status = SelectField(_l('Status'), choices=[
        ('draft', 'Draft'), ('published', 'Published')])
    submit = SubmitField(_l('Submit'))


class CommentForm(FlaskForm):
    body = TextAreaField(_l('Comment'), validators=[
        DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField(_l('Submit'))


class CategoryForm(FlaskForm):
    name = StringField(_l('Category Name'), validators=[
        DataRequired(), Length(min=1, max=64)])
    description = TextAreaField(_l('Description'), validators=[
        Optional(), Length(max=500)])
    submit = SubmitField(_l('Submit'))
