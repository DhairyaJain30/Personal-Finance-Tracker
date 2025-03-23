from flask import Flask,render_template,flash,redirect,url_for,request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_wtf import FlaskForm
from wtforms import StringField,SelectField,IntegerField,SubmitField
from wtforms.validators import DataRequired
from flask_login import UserMixin,LoginManager,login_user,login_required,logout_user,current_user
from werkzeug.security import generate_password_hash,check_password_hash
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class UserInput(FlaskForm):
    type = SelectField('Type',validators=[DataRequired()],
                       choices=[('','Select Type'),('1','Income'),('2','Expense')])
    
    category = SelectField('Category',validators=[DataRequired()],
                       choices=[('','Select Category'),('1','Food'),('2','Entertainment'),('3','Travel'),('4','Rent'),('5','Salary'),('6','Side Income'),('7','Others_Income'),('8','Others_Expense')])
    
    name = StringField('Name')
    
    amount = IntegerField('Amount',validators=[DataRequired()])
    
    submit = SubmitField("Add")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expensesDB.db'
app.config['SECRET_KEY'] = 'dhairya30904@secretkey'
db = SQLAlchemy(app)

class User(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key =True)
    username = db.Column(db.String(150),nullable =False,unique =True)
    email = db.Column(db.String(40),nullable =False,unique =True)
    password_hash = db.Column(db.String(100),nullable =False)
    transcations = db.relationship('Transcation',backref ='user',lazy=True)
    
    def set_password(self,password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self,password):
        return check_password_hash(self.password_hash,password)
    

class Transcation(db.Model):
    id = db.Column(db.Integer,primary_key =True)
    type = db.Column(db.String(100),nullable =False)
    category = db.Column(db.String(100),nullable= False)
    name = db.Column(db.String(100),nullable =False)
    amount = db.Column(db.Float,nullable = False)
    date = db.Column(db.DateTime,nullable = False,default = datetime.now(timezone.utc))
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'),nullable =False)
    def __repr__(self):
        return f"<Transcation{self.name},{self.type},{self.amount}>"

@app.route('/')
def home():
    return render_template('home.html',title = 'home')

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method =='POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('User Already Exist')
            return redirect(url_for('login'))
        
        new_user = User(username =username,email = email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration Succesfull')
        return redirect(url_for('login'))
    return render_template('signup.html')
    
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login Successful')
            return redirect(url_for('index'))
        else:
            flash('Invalid UserName or Password')
    return render_template('login.html',title = 'login')

@app.route('/logout')
def logout():
    logout_user()
    flash("Logged Out Successfully")
    return redirect(url_for('home'))

@app.route('/index')
def index():
    entries = Transcation.query.filter_by(user_id=current_user.id).order_by(Transcation.date.desc()).all()
    return render_template('index.html',entries = entries,title='index')

@app.route('/add',methods =["GET","POST"])
@login_required
def add_expense():
    form = UserInput()
    type_dict = {'1': 'Income', '2': 'Expense'}
    category_dict = {
        '1': 'Food', '2': 'Entertainment', '3': 'Travel', 
        '4': 'Rent', '5': 'Salary', '6': 'Side Income', '7': 'Others_Income','8':'Others_Expense'
    }
    if form.validate_on_submit():
        entry = Transcation(type =type_dict.get(form.type.data,'Unknown'),category = category_dict.get(form.category.data,'Unknown'),name = form.name.data,amount = form.amount.data,user_id=current_user.id)
        db.session.add(entry)
        db.session.commit()
        flash("Entry Successful",'success')
        return redirect(url_for('index'))
    return render_template('add.html',form=form)
    
@app.route('/delete/<int:entry_id>')
def delete(entry_id):
    entry = Transcation.query.get_or_404(int(entry_id))
    db.session.delete(entry)
    db.session.commit()
    flash("Deletion Successful",'success')
    return redirect(url_for('index'))

@app.route('/expense_sum')
def expense_sum():
    entries = Transcation.query.filter_by(user_id = current_user.id)
    
    income_tot =0
    expense_tot =0
    categories_expense =['Food','Entertainment','Travel','Rent','Others_Expense']
    categories_income =['Salary','Side Income','Others_Income']
    category_i ={}
    category_e ={}
    
    for entry in entries:
        if entry.type =='Income':
            income_tot += entry.amount
        elif entry.type =='Expense':
            expense_tot += entry.amount
        
        
        if entry.category in categories_income:
            if entry.category in category_i:
                category_i[entry.category] +=entry.amount
            else:
                category_i[entry.category] = entry.amount
        elif entry.category in categories_expense:
            if entry.category in category_i:
                category_e[entry.category] +=entry.amount
            else:
                category_e[entry.category] = entry.amount
    
    # Bar chart for income-expense
    bar_labels = ['Income', 'Expense']
    bar_values = [income_tot, expense_tot]
    
    fig1, ax1 = plt.subplots()
    ax1.bar(bar_labels, bar_values,color=['green', 'red'])
    ax1.set_xlabel("Type")
    ax1.set_ylabel("Amount")
    ax1.set_title("Income Vs Expenses")
    
    img_bar = BytesIO()
    plt.savefig(img_bar, format='png')
    img_bar.seek(0)
    bar_plot_url = base64.b64encode(img_bar.getvalue()).decode('utf8')
    
    # Create the Category-wise Breakdown Pie Chart for Income 
    pie_labels_i = list(category_i.keys())  # Categories (e.g., Food, Travel, etc.)
    pie_values_i = list(category_i.values())  # Corresponding amounts for each category

    fig2, ax2 = plt.subplots()
    ax2.pie(pie_values_i, labels=pie_labels_i, autopct='%1.1f%%', startangle=90, colors=['green', 'red','blue'])
    ax2.axis('equal')
    
    img_pie_i = BytesIO()
    plt.savefig(img_pie_i, format='png')
    img_pie_i.seek(0)
    pie_plot_url_i = base64.b64encode(img_pie_i.getvalue()).decode('utf8')
    
    # Create the Category-wise Breakdown Pie Chart for Expense 
    pie_labels_e = list(category_e.keys())  # Categories (e.g., Food, Travel, etc.)
    pie_values_e = list(category_e.values())  # Corresponding amounts for each category

    fig2, ax2 = plt.subplots()
    ax2.pie(pie_values_e, labels=pie_labels_e, autopct='%1.1f%%', startangle=90, colors=['green', 'red','blue','yellow','orange'])
    ax2.axis('equal')
    
    img_pie_e = BytesIO()
    plt.savefig(img_pie_e, format='png')
    img_pie_e.seek(0)
    pie_plot_url_e = base64.b64encode(img_pie_e.getvalue()).decode('utf8')

    return render_template('expense_sum.html', pie_plot_url_i=pie_plot_url_i,pie_plot_url_e=pie_plot_url_e, bar_plot_url=bar_plot_url)
    
if __name__ == '__main__':  
    app.run(debug=True)