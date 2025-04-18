from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
from app import db, bcrypt
from app.models import User, Sale, Stock, Product  # Ensure Stock is imported correctly
from app.forms import LoginForm, RegisterForm
from collections import defaultdict  # Ensure defaultdict is imported
from collections import OrderedDict
import calendar 
# Create blueprint
main = Blueprint('main', __name__)

# Context processor for footer year
@main.app_context_processor
def inject_now():
    return {'current_year': datetime.now().year}

# Home redirects to login
@main.route('/')
def home():
    return redirect(url_for('main.login'))

# Login Route
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html', form=form)

# Registration Route
@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/dashboard')
@login_required
def dashboard():
    # Fetch statistics
    total_sales_today = db.session.query(Sale).filter(Sale.date == datetime.today().date()).count()
    total_employees = User.query.count()
    total_receipts = db.session.query(Sale).count()

    # Calculate monthly revenue using Plotly-friendly format
    monthly_revenue_data = defaultdict(float)
    sales = Sale.query.all()
    for sale in sales:
        month = sale.date.strftime('%b')  # e.g., Jan, Feb
        monthly_revenue_data[month] += sale.amount

    # Ensure all months are included, even with zero sales
    months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    final_revenue = OrderedDict()
    for month in months_order:
        final_revenue[month] = round(monthly_revenue_data.get(month, 0), 2)

    return render_template('dashboard.html',
                           total_sales_today=total_sales_today,
                           total_employees=total_employees,
                           total_receipts=total_receipts,
                           monthly_revenue=final_revenue,
                           username=current_user.username)# Sales Route with Filters
@main.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    # Filter by date and amount if specified
    filter_date = request.args.get('filter_date')
    filter_amount = request.args.get('filter_amount')
    
    sales_query = Sale.query

    # Apply date filter if provided
    if filter_date:
        sales_query = sales_query.filter(Sale.date == filter_date)

    # Apply amount filter if provided
    if filter_amount:
        sales_query = sales_query.filter(Sale.amount == float(filter_amount))

    # Fetch filtered sales records
    sales_data = sales_query.all()

    return render_template('sales.html', sales=sales_data)



@main.route('/add_sale', methods=['GET', 'POST'])
@login_required
def add_sale():
    if request.method == 'POST':
        cashier_id = request.form['cashier_id']  # Get the selected cashier
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        date_str = request.form['date']

        # Fetch the selected cashier from the User table
        cashier = User.query.get_or_404(cashier_id)

        # Fetch the product
        product = Product.query.get_or_404(product_id)
        amount = product.price * quantity

        # Convert the date string to a datetime.date object
        try:
            sale_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('main.add_sale'))

        # Create the new sale
        new_sale = Sale(
            amount=amount,
            date=sale_date,
            user_id=cashier.id,  # Use cashier's ID as the user who made the sale
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(new_sale)
        db.session.commit()

        flash('Sale added successfully!', 'success')
        return redirect(url_for('main.sales'))

    # Fetch users (cashiers) and products for the form
    products = Product.query.all()
    users = User.query.filter_by(role='cashier').all()  # Fetch only cashiers
    return render_template('add_sale.html', products=products, users=users)

@main.route('/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def edit_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)

    if request.method == 'POST':
        # Get the form data
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        date_str = request.form['date']

        # Convert the string date to a datetime.date object
        try:
            sale_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('main.edit_sale', sale_id=sale.id))

        # Update sale details
        sale.product_id = product_id
        sale.quantity = quantity
        sale.date = sale_date  # Set the date as a datetime.date object

        # Recalculate the total amount
        product = Product.query.get_or_404(sale.product_id)
        sale.amount = product.price * sale.quantity

        # Commit the changes
        db.session.commit()
        
        flash('Sale updated successfully!', 'success')
        return redirect(url_for('main.sales'))

    products = Product.query.all()  # Fetch all products for selection
    return render_template('edit_sale.html', sale=sale, products=products)
# Delete Sale Route
@main.route('/delete_sale/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def delete_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    
    flash('Sale deleted successfully!', 'danger')
    return redirect(url_for('main.sales'))

# View Sale Route
@main.route('/view_sale/<int:sale_id>')
@login_required
def view_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template('view_sale.html', sale=sale)

# Products Route
@main.route('/products')
@login_required
def products():
    # Fetch all products
    products_data = Product.query.all()
    return render_template('products.html', products=products_data)

# Add Product Route
@main.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        quantity = request.form['quantity']
        
        new_product = Product(name=name, price=price, quantity=quantity)
        db.session.add(new_product)
        db.session.commit()

        flash('Product added successfully!', 'success')
        return redirect(url_for('main.products'))
    
    return render_template('add_product.html')

# View Product Route
@main.route('/product/<int:product_id>')
@login_required
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('view_product.html', product=product)

# Edit Product Route
@main.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = request.form['price']
        product.quantity = request.form['quantity']
        db.session.commit()

        flash('Product updated successfully!', 'success')
        return redirect(url_for('main.products'))

    return render_template('edit_product.html', product=product)

# Delete Product Route
@main.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()

    flash('Product deleted successfully!', 'danger')
    return redirect(url_for('main.products'))

# Stock Route
@main.route('/stock')
@login_required
def stock():
    # Fetch stock levels for all products
    stock_data = Stock.query.all()
    return render_template('stock.html', stock=stock_data)

# Receipts Route
@main.route('/receipts')
@login_required
def receipts():
    # Fetch all receipts (same as sales)
    receipts_data = Sale.query.all()
    return render_template('receipts.html', receipts=receipts_data)

@main.route('/revenue')
@login_required
def revenue():
    # Calculate the total revenue
    total_revenue = db.session.query(db.func.sum(Sale.amount)).scalar() or 0

    # Get monthly revenue data (assuming you want the last 6 months)
    monthly_revenue = []
    months = []
    current_month = datetime.now().month
    for i in range(6):
        month = (current_month - i - 1) % 12 + 1
        months.append(calendar.month_name[month])
        revenue = db.session.query(db.func.sum(Sale.amount)).filter(
            db.extract('month', Sale.date) == month).scalar() or 0
        monthly_revenue.append(revenue)

    # Get top 5 products sold by quantity and total revenue
    top_products = db.session.query(
        Product.name,
        db.func.sum(Sale.quantity).label('total_quantity'),
        db.func.sum(Sale.amount).label('total_revenue')
    ).join(Sale).group_by(Product.id).order_by(db.func.sum(Sale.quantity).desc()).limit(5).all()

    return render_template('revenue.html', 
                           total_revenue=total_revenue, 
                           monthly_revenue=monthly_revenue,
                           months=months, 
                           top_products=top_products)

# Logout
@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))
# Employees Route
@main.route('/employees')
@login_required
def employees():
    # Fetch all employees (you can adjust this query as per your database design)
    employees_data = User.query.all()  # Assuming you're using the User model for employees
    return render_template('employees.html', employees=employees_data)
# View Employee
@main.route('/employee/<int:user_id>')
@login_required
def view_employee(user_id):
    employee = User.query.get_or_404(user_id)
    return render_template('view_employee.html', employee=employee)

# Edit Employee
@main.route('/edit_employee/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(user_id):
    employee = User.query.get_or_404(user_id)
    if request.method == 'POST':
        employee.username = request.form['username']
        employee.email = request.form['email']
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('main.employees'))
    return render_template('edit_employee.html', employee=employee)

# Delete Employee
@main.route('/delete_employee/<int:user_id>', methods=['POST'])
@login_required
def delete_employee(user_id):
    employee = User.query.get_or_404(user_id)
    db.session.delete(employee)
    db.session.commit()
    flash('Employee deleted successfully!', 'danger')
    return redirect(url_for('main.employees'))


@main.route('/sales/records')
@login_required
def sales_records():
    # Get search term
    search_term = request.args.get('search', '')
    
    # Get the page number, default is 1
    page = request.args.get('page', 1, type=int)
    
    # Query Sales based on search term (filter by customer_name or date)
    if search_term:
        records = Sale.query.filter(
            Sale.customer_name.like(f'%{search_term}%') |
            Sale.date.like(f'%{search_term}%')
        ).paginate(page, per_page=10)
    else:
        records = Sale.query.paginate(page, per_page=10)
    
    return render_template('records.html', records=records)
