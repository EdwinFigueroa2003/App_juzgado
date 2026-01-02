from flask import Blueprint, render_template

menu = Blueprint('menu', __name__, template_folder='templates')

@menu.route('/')
def menu_view():
    return render_template('home.html') 