from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response, make_response, session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from database_setup import Base, Category, CategoryItem
import random, string
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2, json, requests
from functools import wraps

#Configuration
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog"
app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

def countItemTitle(title):
    results = session.query(CategoryItem).filter_by(title=title).all()
    return len(results)

#LOGIN
@app.route("/login")
def show_login():
    # Create state token.
    # Note: This shields user from Cross Site Request Forgery Attack.
    state = "".join(random.choice(string.ascii_uppercase + string.digits +
            string.ascii_lowercase) for x in xrange(32))
    login_session["state"] = state
    return render_template("login.html", state=login_session["state"],user=None)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    #login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id
    login_session['access_token'] = credentials.access_token

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    #login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/catalog/JSON')    
def getCatalog():
    output_json = []
    categories = session.query(Category).all()
    for category in categories:
        items = session.query(CategoryItem).filter_by(category_id=category.id)
        category_output = {}
        category_output["id"] = category.id
        category_output["name"] = category.name
        category_output["items"] = [i.serialize for i in items]
        output_json.append(category_output)
    return jsonify(Categories=output_json)

@app.route('/')
@app.route('/catalog')
def showCatalog():
    
    try:
        user = login_session['username']
    except KeyError:
        user = None
    
    categories = session.query(Category).all()
    latest_items = session.query(CategoryItem).order_by(
            desc(CategoryItem.id)).all()
    category_names = {}
    for category in categories:
            category_names[category.id] = category.name
    return render_template(
            'category.html', selected_category=None, selected_category_name='Latest Items', categories=categories, items=latest_items,
            category_names=category_names, user=user
        )
 

#Logout
@app.route('/gdisconnect')
def gdisconnect():    
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: ' 
    print login_session['username']
    if access_token is None:
 	print 'Access Token is None'
   	response = make_response(json.dumps('Current user not connected.'), 401)
    	response.headers['Content-Type'] = 'application/json'
    	return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
	del login_session['access_token'] 
    	del login_session['gplus_id']
    	del login_session['username']
    	#del login_session['email']
    	del login_session['picture']
    	response = make_response(json.dumps('Successfully disconnected.'), 200)
    	response.headers['Content-Type'] = 'application/json'
    	return response
    else:	
    	response = make_response(json.dumps('Failed to revoke token for given user.', 400))
    	response.headers['Content-Type'] = 'application/json'
    	return response
    

@app.route('/catalog/<category_name>/')
def getCategoryItems(category_name):
    categories = session.query(Category).all()
    category_names = {}
    for category in categories:
        category_names[category.id] = category.name
        if category.name==category_name:
            selected_category=category
            items = session.query(CategoryItem).filter_by(category_id=category.id)                
    try:
        user = login_session['username']
    except KeyError:
        user = None
    return render_template(
        'category.html', selected_category=selected_category,  selected_category_name=selected_category.name,user=user,
        items=items, categories=categories, category_names=category_names
    )


@app.route('/item/new', methods=['GET', 'POST'])
def newItem():
    if 'username' not in login_session:
        return redirect('/login')
    
    categories = session.query(Category).all()
    user = login_session['username']    
    if request.method == 'POST':
        title = request.form['title']
        if countItemTitle(title)>0:
            flash("Title Exist")
            return redirect(url_for('newItem'))
        newItem = CategoryItem(title,
            request.form['description'],
            request.form['category_id'])
        session.add(newItem)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template(
            'newItem.html', categories=categories, user=user
        )
    
@app.route('/item/<item_title>/view')
def getItemDetails(item_title):
    try:
        user = login_session['username']
    except KeyError:
        user = None
    
    item = session.query(CategoryItem).filter_by(title=item_title).one()
    category = session.query(Category).filter_by(id=item.category_id).one()
    return render_template(
        'viewItem.html', item=item, category=category,user=user
    )


@app.route('/item/<item_title>/edit', methods=['GET', 'POST'])
def editItem(item_title):
    if 'username' not in login_session:
        return redirect('/login')
        
    editedItem = session.query(CategoryItem).filter_by(title=item_title).one()
    category = session.query(Category).filter_by(id=editedItem.category_id).one()
    categories = session.query(Category).all()
    if request.method == 'POST':
        if request.form['title']:
            title = request.form['title']
            if countItemTitle(title)>1:
                flash("Title Exist")
                return redirect(url_for('editItem',item_title=item_title))
            editedItem.title = title
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['category_id']:
            editedItem.category_id = request.form['category_id']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        user = login_session['username']
        return render_template(
            'editItem.html', item=editedItem, category=category,
            categories=categories, user=user
        )

@app.route('/item/<item_title>/delete', methods=['GET', 'POST'])
def deleteItem(item_title):
    if 'username' not in login_session:
        return redirect('/login')
    
    if request.method == 'POST':
        itemToDelete = session.query(CategoryItem).filter_by(title=item_title).one()
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        user = login_session['username']
        return render_template(
            'deleteItem.html', item_title = item_title, user=user
        )

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
