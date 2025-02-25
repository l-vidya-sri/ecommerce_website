from flask import Flask,render_template,url_for,request,redirect,flash,session
from otp import genotp
from cmail import sendmail
from flask_session import Session
from stoken import encode,decode
import mysql.connector
import os
#import razorpay
import re

app=Flask(__name__)
app.secret_key='codegnan@2018'      #secret_key to prevent tampering
app.config['SESSION_TYPE']='filesystem'    #Session data is stored in files on the server.
Session(app)
RAZORPAY_KEY_ID='rzp_test_BdYxoi5GaEITjc'
RAZORPAY_KEY_SECRET='H0FUH2n4747ZSYBRyCn2D6rc'
#client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
#mydb=mysql.connector.connect(host='localhost',user='root',password='root',db='ecommi')
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,port=port,db=db,password=password,user=user) as conn:
    cursor=conn.cursor()
    cursor.execute("CREATE TABLE if not exists usercreate ( username varchar(50) NOT NULL,user_email varchar(100) NOT NULL,address text NOT NULL,password varbinary(20) NOT NULL,gender enum('Male','Female') DEFAULT NULL,PRIMARY KEY (user_email),UNIQUE KEY username (username))")
    cursor.execute("CREATE TABLE if not exists admincreate (email varchar(50) NOT NULL,username varchar(100) NOT NULL,password varbinary(10) NOT NULL,address text NOT NULL,accept enum('on','off') DEFAULT NULL,dp_image varchar(50) DEFAULT NULL, PRIMARY KEY (email))")
    cursor.execute("CREATE TABLE if not exists items (item_id binary(16) NOT NULL,item_name varchar(255) NOT NULL,quantity int unsigned DEFAULT NULL,price decimal(14,4) NOT NULL,category enum('Home_appliances','Electronics','Fashion','Grocery') DEFAULT NULL,image_name varchar(255) NOT NULL,added_by varchar(50) DEFAULT NULL,description longtext,PRIMARY KEY (item_id),KEY added_by (added_by),CONSTRAINT items_ibfk_1 FOREIGN KEY (added_by) REFERENCES admincreate (email) ON DELETE CASCADE ON UPDATE CASCADE)")
    cursor.execute("CREATE TABLE if not exists orders (orderid bigint NOT NULL AUTO_INCREMENT,itemid binary(16) DEFAULT NULL,item_name longtext,qty int DEFAULT NULL,total_price bigint DEFAULT NULL,user varchar(100) DEFAULT NULL,PRIMARY KEY (orderid),KEY user (user),KEY itemid (itemid),CONSTRAINT orders_ibfk_1 FOREIGN KEY (user) REFERENCES usercreate (user_email),CONSTRAINT orders_ibfk_2 FOREIGN KEY (itemid) REFERENCES items (item_id))")
    cursor.execute("CREATE TABLE if not exists reviews(username varchar(30) NOT NULL,itemid binary(16) NOT NULL,title tinytext,review text,rating int DEFAULT NULL,date datetime DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY (itemid,username),KEY username (username),CONSTRAINT reviews_ibfk_1 FOREIGN KEY (itemid)REFERENCES items (item_id) ON DELETE CASCADE ON UPDATE CASCADE,CONSTRAINT reviews_ibfk_2 FOREIGN KEY (username) REFERENCES usercreate (user_email) ON DELETE CASCADE ON UPDATE CASCADE)")
    cursor.execute("CREATE TABLE if not exists contactus(name varchar(100) DEFAULT NULL,email varchar(100) DEFAULT NULL,message text)")
mydb=mysql.connector.connect(host=host,user=user,port=port,db=db,password=password)
@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/index')
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items')
        item_data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('Could not fetch data')
        return redirect(url_for('home'))
    else:
        return render_template("index.html",item_data=item_data)

@app.route("/admincreate",methods=["POST","GET"])
def admincreate():
    if request.method=='POST':
        # print(request.form)      #ImmutableMultiDict([('username', 'viddu'), ('email', 'viddu@gmail.com'), ('password', '123456789'), ('address', 'tyuio'), ('agree', 'on')])
        aname=request.form["username"]
        aemail=request.form["email"]
        password=request.form["password"]
        address=request.form["address"]
        status_accept=request.form['agree'] 
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[aemail])
        c=cursor.fetchone()
        if c[0]==0:
            gotp=genotp()
            udata={'aname':aname,'aemail':aemail,'password':password,'address':address,'status':status_accept,'aotp':gotp}
            subject="BuyRoute"
            body=f"{gotp} is yout OTP to access BuyRoute.OTP is confidential"
            sendmail(to=aemail,subject=subject,body=body)
            flash('OTP has send to your mail')
            return redirect(url_for('otp',endata=encode(data=udata))) 
        elif c[0]==1:
            flash("Email Already Register please check!!!")
            return redirect(url_for('adminlogin'))
    return render_template("admincreate.html")

@app.route("/otp/<endata>",methods=['GET','POST'])
def otp(endata):
    if request.method=='POST':
        aotp=request.form['otp']
        try:
            dudata=decode(data=endata)
        except Exception as e:
            print(e)
        else:
            if aotp==dudata['aotp']:
                cursor=mydb.cursor()
                cursor.execute('insert into admincreate(email,username,password,address,accept) values(%s,%s,%s,%s,%s)',[dudata['aemail'],dudata['aname'],dudata['password'],dudata['address'],dudata['status']])
                mydb.commit()
                return redirect(url_for('adminlogin'))
            else:
                flash("OTP is invalid")
        finally:
            cursor.close()        
    return render_template("adminotp.html")

@app.route("/adminlogin",methods=['POST','GET'])
def adminlogin():
    if not session.get('admin'):
        if request.method=='POST':
            try:
                email=request.form['email']
                password=request.form['password']
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(email) from admincreate where email=%s',[email])
                c=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('Connection failed')
                return redirect(url_for('adminlogin'))
            else:
                if c[0]==0:
                    flash("Invalid Email ")
                    return redirect(url_for("adminlogin"))
                elif c[0]==1:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('select password from admincreate where email=%s',[email])
                    bpassword=cursor.fetchone()
                    if bpassword[0].decode('utf-8')==password:
                        session['admin']=email
                        if not session.get('admin'):
                            session['admin']={}
                        return redirect(url_for('adminpanel')) 
                    else:
                        flash("Wrong password")
                        return redirect(url_for("adminlogin"))
                else:
                    flash("Something went wrong")
                    return redirect(url_for("index"))
            finally:
                cursor.close() 
        return render_template("adminlogin.html")
    else:
        flash("U have already login!!!")
        return redirect(url_for('adminpanel'))
    
@app.route("/adminforget",methods=['POST','GET'])
def adminforget():
    if request.method=='POST':
        forgot_email=request.form['email']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(email) from admincreate where email=%s',[forgot_email])
            c=cursor.fetchone()
            cursor.close()
            if c[0]==1:
                subject='Admin reset Link for BuyRoute'
                body=f"Click on the link for update your password:{url_for('ad_password_update',token=encode(data=forgot_email),_external=True)}"
                sendmail(to=forgot_email,subject=subject,body=body)
                flash("Email is sent your mail please check!!")
            elif c[0]==0:
                flash("Details are not exist please login first!!!")
                return redirect(url_for('adminlogin'))
            else:
                flash("Something went please try again!!")
                return redirect(url_for("index"))
        except Exception as e:
            print(e)
            flash('Connectionis failed')
    return render_template("forgot.html")

@app.route('/ad_password_update/<token>',methods=['POST','GET'])
def ad_password_update(token):
    if request.method=='POST':
        try:
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            ntoken=decode(data=token)
        except Exception as e:
            print(e)
            flash("Something went Wrong")
            return redirect(url_for("adminlogin"))
        else:
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admincreate set password = %s where email=%s',[npassword,ntoken])
                mydb.commit()
                cursor.close()
                flash("password is successfully updated")
                return redirect(url_for("adminlogin"))
            else:
                flash("Please enter same password in both the fields")
                return redirect(url_for("ad_password_update",token=token))    
    return render_template('newpassword.html')

@app.route("/adminpanel")
def adminpanel():
    if session.get('admin'):
        return render_template("adminpanel.html")
    else:
        flash("Please Login First")
        return redirect(url_for('adminlogin'))

@app.route("/additem",methods=['POST','GET'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            title=request.form['title']
            Discription=request.form['Discription']
            quantity=request.form['quantity']
            price=request.form['price']
            category=request.form['category']
            img_file=request.files['file']
            fname=genotp()+'.'+img_file.filename.split(".")[-1]
            drname=os.path.dirname(os.path.abspath(__file__))     #os.path.abspath(__file__) gives file name of current working file (app.py) and os.path.dirname give directory of app.py (C:\Users\vidya\OneDrive\Desktop\flask_class\ecommerce)
            static_path=os.path.join(drname,'static')
            img_file.save(os.path.join(static_path,fname))    
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into items(item_id,item_name,quantity,price,category,image_name,added_by,description) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[title,quantity,price,category,fname,session.get('admin'),Discription])
                mydb.commit()
            except Exception as e:
                print(e)
                flash("Can't add item Please try again")
            else:
                flash(f'{title[:10]}.. added successfully')
            finally:
                cursor.close() 
        return render_template("additem.html")
    
    else:
        flash("Please login first")
        return redirect(url_for('adminlogin'))

@app.route("/viewall_items")
def viewall_items():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,image_name from items where added_by =%s',[session.get('admin')])
            item_data=cursor.fetchall()
        except Exception as e:
            print(e)
            flash("Something is wrong")
            return redirect(url_for("adminpanel")) 
        else:
            return render_template("viewall_items.html",item_data=item_data)
        finally:
            cursor.close()
    else:
        flash("Please login first")
        return redirect(url_for('adminlogin'))
    
@app.route("/view_item/<item_id>")
def view_item(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash("You Can't view the product please try again!!!")
            return redirect(url_for(adminpanel))
        else:
            return render_template("view_item.html",item_data=item_data)
    else:
        flash("Please login first")
        return redirect(url_for('adminlogin'))
    
@app.route("/update_item/<item_id>",methods=['POST','GET'])
def update_item(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone()
            print(item_data)
        except Exception as e:
            print(e)
            flash("Something is wrong")
            return redirect(url_for("adminpanel")) 
        else:
            if request.method=='POST':
                title=request.form['title']
                Discription=request.form['Discription']
                quantity=request.form['quantity']
                price=request.form['price']
                category=request.form['category']
                img_file=request.files['file']
                filename=img_file.filename
                if filename == '':
                    img_name=item_data[6]
                else:
                    img_name=genotp()+'.'+filename.split('.')[-1]
                    drname=os.path.dirname(os.path.abspath(__file__))     #os.path.abspath(__file__) gives file name of current working file (app.py) and os.path.dirname give directory of app.py (C:\Users\vidya\OneDrive\Desktop\flask_class\ecommerce)
                    static_path=os.path.join(drname,'static')
                    if item_data[6] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,item_data[6]))
                    img_file.save(os.path.join(static_path,img_name))
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update items set item_name=%s,description=%s,price=%s,quantity=%s,category=%s,image_name=%s where item_id=uuid_to_bin(%s)',[title,Discription,price,quantity,category,img_name,item_id])
                mydb.commit()
                cursor.close()
                flash("Item updated successfully")
                return redirect(url_for("view_item",item_id=item_id))
        return render_template("update_item.html",item_data=item_data)
    else:
        flash("Please login first")
        return redirect(url_for('adminlogin'))
    
@app.route("/delete_item/<itemid>")
def delete_item(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select image_name from items where item_id=uuid_to_bin(%s)',[itemid])
            stored_image=cursor.fetchone()
            drname=os.path.dirname(os.path.abspath(__file__))
            static_path=os.path.join(drname,'static')
            if stored_image[0] in os.listdir(static_path):
                os.remove(os.path.join(static_path,stored_image[0]))
            cursor.execute('delete from items where item_id=uuid_to_bin(%s)',[itemid])
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(e)
            flash("Couldn't delete item")
            return redirect(url_for('adminpanel'))
        else:
            flash("deleted successfully")
            return redirect(url_for("adminpanel"))     
    else:
        flash("Please login first")
        return redirect(url_for('adminlogin'))
        
@app.route("/adminprofile_update",methods=['POST','GET'])
def adminprofile_update():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select * from admincreate where email=%s',[session.get('admin')])
            admin_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('connection Error')
            return redirect(url_for('adminpanel'))
        else:
            if request.method=='POST':
                adminname=request.form['adminname']
                address=request.form['address']
                profile_file=request.files['file']
                filename=profile_file.filename
                if filename == '':
                    profile_name=admin_data[5]
                else:
                    profile_name=genotp()+'.'+filename.split('.')[-1]
                    drname=os.path.dirname(os.path.abspath(__file__))    
                    static_path=os.path.join(drname,'static')
                    if admin_data[5] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,admin_data[5]))
                    profile_file.save(os.path.join(static_path,profile_name))
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admincreate set username=%s,address=%s,dp_image=%s where email=%s',[adminname,address,profile_name,session.get('admin')]) 
                mydb.commit()
                cursor.close() 
                flash("Profile updated successfully")
                return redirect(url_for('adminpanel'))    
        return render_template("adminupdate.html",admin_data=admin_data)
    else:
        flash("Please login first")
        return redirect(url_for('adminlogin'))

@app.route("/search",methods=['POST','GET'])
def search():
    if request.method=='POST':
        search=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}',re.IGNORECASE)
        try:
            if pattern.match(search):
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select *from items where item_id like %s or item_name like %s or price like %s or description like %s',[search+'%',search+'%',search+'%',search+'%'])
                item_data=cursor.fetchall()
                cursor.close()
                print("data:",item_data)
                if item_data:
                    return render_template("dashboard.html",items_data=item_data)
                else:
                    flash("No data found.....")
                    return redirect(url_for("index"))         
            else:
                flash("No data found")
                return redirect(url_for("index"))
        except Exception as e:
            print(e)
            flash("Can't find anything")
            return redirect(url_for("index"))  

@app.route("/adminlogout")
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for("index"))  
    else:
        flash("please login first")
        return redirect(url_for("adminlogin")) 
    
@app.route("/usercreate",methods=['POST',"GET"])
def usercreate():
    if request.method=='POST':
        uname=request.form['name']
        uemail=request.form['email']
        password=request.form["password"]
        address=request.form["address"]
        usergender=request.form['usergender'] 
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[uemail])
        c=cursor.fetchone()
        if c[0]==0:
            gotp=genotp()
            udata={'aname':uname,'aemail':uemail,'password':password,'address':address,'gender':usergender,'uotp':gotp}
            subject="BuyRoute"
            body=f"{gotp} is yout OTP to access BuyRoute.OTP is confidential"
            sendmail(to=uemail,subject=subject,body=body)
            flash('OTP has send to your mail')
            return redirect(url_for('userotp',endata=encode(data=udata))) 
        elif c[0]==1:
            flash("Email Already Register please check!!!")
            return redirect(url_for('userlogin'))
    return render_template("usersignup.html")

@app.route("/userotp/<endata>",methods=['POST','GET'])
def userotp(endata):
    if request.method=='POST':
        aotp=request.form['otp']
        try:
            dudata=decode(data=endata)
        except Exception as e:
            print(e)
        else:
            if aotp==dudata['uotp']:
                cursor=mydb.cursor()
                cursor.execute('insert into usercreate(username,user_email,password,address,gender) values(%s,%s,%s,%s,%s)',[dudata['aname'],dudata['aemail'],dudata['password'],dudata['address'],dudata['gender']])
                mydb.commit()
                return redirect(url_for('userlogin'))
            else:
                flash("OTP is invalid")
        finally:
            cursor.close()  
    return render_template("userotp.html")

@app.route("/userlogin",methods=['POST','GET'])
def userlogin():
    if request.method=='POST':
        try:
            email=request.form['email']
            password=request.form['password']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(user_email) from usercreate where user_email=%s',[email])
            c=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Connection failed')
            return redirect(url_for('adminlogin'))
        else:
            if c[0]==0:
                flash("Invalid Email ")
                return redirect(url_for("userlogin"))
            elif c[0]==1:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select password from usercreate where user_email=%s',[email])
                bpassword=cursor.fetchone()
                if bpassword[0].decode('utf-8')==password:
                    session['useremail']=email
                    if not session.get('email'):
                        session[email]={}
                    return redirect(url_for('index')) 
                else:
                    flash("Wrong password")
                    return redirect(url_for("userlogin"))
            else:
                flash("Something went wrong")
                return redirect(url_for("index"))
        finally:
            cursor.close()      
    return render_template("userlogin.html")

@app.route("/addcart/<itemid>/<name>/<price>/<image>/<quantity>/<category>")
def addcart(itemid,name,price,image,quantity,category):
    if session.get('useremail'):
        if itemid not in session['useremail']:
            session[session.get('useremail')][itemid]=[name,price,1,image,category,quantity]
            session.modified=True
            flash(f'{name} added to cart')
            return redirect(url_for('index'))
        session[session.get('useremail')][itemid][2]+=1 
        flash('item already in cart')
        return redirect(url_for('index')) 
    else:
        flash("Please login first!!!!")
        return redirect(url_for('userlogin'))

'''@app.route("/pay/<itemid>/<name>/<float:price>",methods=['POST','GET'])
def pay(itemid,name,price):
    try:
        print("price:",price)
        qyt=int(request.form['qyt'])
        amount=price*100
        total_price=amount*qyt
        print(amount,qyt,total_price)
        print(f"Creating payment for items: {itemid},name:{name},price:{total_price}")
        #create Razorpay order
        order=client.order.create({
            'amount':total_price,
            'currency':'INR',
            'payment_capture':'1'
        })
        print(f"order created: {order}")
        return render_template('pay.html',order=order,itemid=itemid,name=name,price=total_price,qyt=qyt)
    except Exception as e:
        print(f'Error creating order: {str(e)}')
        flash('Error in payment')
        return redirect(url_for('index'))
    
@app.route('/success',methods=['POST'])
def success():
    #extract payment details from the form
    payment_id=request.form.get('razorpay_payment_id')
    order_id=request.form.get('razorpay_order_id')
    signature=request.form.get('razorpay_signature')
    name=request.form.get('name')
    itemid=request.form.get('itemid')
    price=request.form.get('total_price')
    qyt=request.form.get('qyt')
    param_dict={
        'razorpay_order_id':order_id,
        'razorpay_payment_id':payment_id,
        'razorpay_signature':signature
    }
    try:
        client.utility.verify_payment_signature(param_dict)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into orders(itemid,item_name,total_price,user,qty) values (uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,price,session.get('useremail'),qyt])
        mydb.commit()
        cursor.close()
        flash('Order placed successfully')
        return redirect(url_for('orders'))
    except razorpay.errors.SignatureVerificationError:
        return 'Payment verification failed!',400'''
    
@app.route("/orders")
def orders():
    if session.get('useremail'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select orderid,bin_to_uuid(itemid),item_name,total_price,user,qty from orders where user=%s',[session.get('useremail')])
            user_orders=cursor.fetchall()
        except Exception as e:
            print(e)
            flash('cannot fetch data')
            return redirect(url_for('index'))
        else:
            return render_template("orders.html",user_orders=user_orders)
    else:
        flash('please login first....')
        return redirect(url_for('userlogin'))
    
    
@app.route('/remove/<itemid>')
def remove(itemid):
    if not session.get('useremail'):
        return redirect(url_for('userlogin'))
    else:
        session.get(session.get('useremail')).pop(itemid)
        session.modified=True
        print(session)
        flash('item removes sussfully from cart')
        return redirect(url_for('viewcart'))
    
@app.route("/contactus",methods=['POST','GET'])
def contactus():
    if request.method=='POST':
        title=request.form['title']
        email=request.form['email']     
        description=request.form['description']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into contactus values(%s,%s,%s)',[title,email,description])
        except Exception as e:
            print(e)
            flash("Connection Failed.....!!!")
            return redirect(url_for('index'))
        else:
            flash("Successfully added the query")
            return redirect(url_for("index"))
        finally:
            mydb.commit()
            cursor.close()      
    return render_template("contact.html")

@app.route('/category/<type>')
def category(type):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items where category=%s',[type])
        items_data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('Could not fetch data')
        return redirect(url_for('index'))
    else:
        return render_template('dashboard.html',items_data=items_data)
    
@app.route('/viewcart')
def viewcart():
    if session.get('useremail'):
        if session.get(session.get('useremail')):
            items=session[session.get('useremail')]
            print(items)
        else:
            items='empty'
        if items=='empty':
            flash('no product added to cart')
            return redirect(url_for('index'))
        return render_template('cart.html',items=items)
    else:
        flash("Please login first!!!!")
        return redirect(url_for('userlogin'))
        
@app.route("/description/<itemid>")
def description(itemid): 
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,description,quantity,price,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
    except Exception as e:
        print(e)
        flash('could not fetach data')
        return redirect(url_for('index'))
    finally:
        cursor.close()
    return render_template("description.html",item_data=item_data)

@app.route("/addreview/<itemid>",methods=['POST','GET'])
def addreview(itemid):
    if session.get('useremail'):
        if request.method=='POST':
            title=request.form['title']
            review=request.form['review']
            rate=request.form['rate']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into reviews(username,itemid,title,review,rating) values(%s,uuid_to_bin(%s),%s,%s,%s)',[session.get('useremail'),itemid,title,review,rate])
            except Exception as e:
                print(e)
                flash('connection is failed')
                return redirect(url_for('description',itemid=itemid))
            else:
                flash("Review added successfully")
                return redirect(url_for('description',itemid=itemid))
            finally:
                mydb.commit()
                cursor.close()
    else:
        flash("Please login first!!!!")
        return redirect(url_for('userlogin'))    
    return render_template('review.html')

@app.route("/readreview/<itemid>")
def readreview(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,description,quantity,price,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
        cursor.execute('select * from reviews where itemid=uuid_to_bin(%s)',[itemid])
        data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('could not fetach data')
        return redirect(url_for('index'))
    finally:
        cursor.close()
    return render_template('readreview.html',item_data=item_data,data=data)

@app.route("/userlogout")
def userlogout():
    if session.get('useremail'):
        session.pop('useremail')
        return redirect(url_for("index"))  
    else:
        flash("please login first")
        return redirect(url_for("userlogin")) 

if __name__=='__main__':
    app.run()
