import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login

# for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'SCning149192'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT email from Users")
    return cursor.fetchall()


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'></input>
                <input type='password' name='password' id='password' placeholder='password'></input>
                <input type='submit' name='submit'></input>
               </form></br>
           <a href='/'>Home</a>
               '''
    # The request method is POST (page is recieving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    # check if email is registered
    if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
        data = cursor.fetchall()
        pwd = str(data[0][0])
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user)  # okay login in user
            return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

    # information did not match
    return "<a href='/login'>Try again</a>\
            </br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('hello.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        hometown = request.form.get('hometown')

    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute(
            "INSERT INTO Users (fname, lname, email, password, gender, dob, hometown) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(
                fname, lname, email, password, gender, dob, hometown)))
        conn.commit()
        # log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        return render_template('hello.html', name=email, message='Account Created!')
    else:
        print("couldn't find all tokens")
        return flask.redirect(flask.url_for('register'))


# ------------------- HELPER -------------------
def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
    return cursor.fetchall()  # NOTE return a list of tuples, [(imgdata, pid, caption), ...]


def getAllPhotos(data):
    ret = []
    # add count of likes for each photo
    for i in data:
        cursor1 = conn.cursor()
        cursor1.execute("SELECT user_id FROM Likes WHERE picture_id = '{0}'".format(i[1]))
        like = cursor1.fetchall()
        like = ', '.join([str(i[0]) for i in like])

        cursor2 = conn.cursor()
        cursor2.execute("SELECT COUNT(*) FROM Likes WHERE picture_id = '{0}'".format(i[1]))
        like_count = cursor2.fetchone()[0]

        # get comment
        cursor3 = conn.cursor()
        cursor3.execute("SELECT user_id, text, date FROM Comments WHERE picture_id = '{0}'".format(i[1]))

        # get tags
        cursor4 = conn.cursor()
        cursor4.execute("SELECT Tags.name FROM Tags\
                        JOIN Tagged ON Tags.tag_id = Tagged.tag_id \
                        WHERE Tagged.picture_id = '{0}'".format(i[1]))

        ret.append((i[0], i[1], i[2], like, like_count, cursor3.fetchall(), cursor4.fetchall()))

    return ret  # NOTE return a list of tuples, [(imgdata, pid, caption, like, like_count, comments, tags), ...]


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
    return cursor.fetchone()[0]


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


def getAlbumIDfromName(name):
    cursor = conn.cursor()
    cursor.execute("SELECT album_id FROM Albums WHERE Name = '{0}'".format(name))
    return cursor.fetchone()[0]


def getUserNameFromID(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT fname, lname FROM Users WHERE user_id = '{0}'".format(uid))
    return cursor.fetchone()


# --------------------- FRIEND --------------------- #

@app.route('/friend', methods=['GET', 'POST'])
@flask_login.login_required
def add_friend():
    if flask.request.method == 'GET':
        return '''
        <h2>Add a new friend:</h2>
               <form action='friend' method='POST'>
                <input type='email' name='friendemail' id='friendemail' placeholder='friend email'></input>
                <input type='submit' name='submit'></input>
               </form></br>
               <h2>Search for a friend:</h2>
               <form action='friend_search' method='POST'>
                <input type='email' name='friendemail' id='friendemail' placeholder='friend email'></input>
                <input type='submit' name='submit'></input>
               </form></br>
               <h2>List all friends:</h2>
               <form action='friend_list' method='POST'>
                <input type='submit' name='submit'></input>
               </form></br>
                <h2> Friend Recommendations: </h2>
                <form action='friend_recommendation' method='POST'>
                <input type='submit' name='submit'></input>
                               </form></br>
            <button onclick="history.back()">Go Back</button>
           <a href='/'>Home</a>
               '''
    # The request method is POST (page is recieving data)
    friendEmail = flask.request.form['friendemail']
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    if cursor.execute("SELECT email FROM Users WHERE email = '{0}'".format(friendEmail)):
        cursor.execute("SELECT user_id FROM Users WHERE email = '{0}'".format(friendEmail))
        friendID = cursor.fetchall()[0][0]
        cursor.execute("SELECT UID2 FROM Friendship WHERE UID1 = '{0}' ".format(uid))
        UID2 = cursor.fetchall()
        if friendID not in UID2:
            cursor.execute("INSERT INTO Friendship (UID1, UID2) VALUES ('{0}', '{1}')".format(uid, friendID))
            conn.commit()
            return "You are now friends with: {0}".format(friendEmail)
        else:
            return "You already friend with {0}".format(friendEmail)
    else:
        return "No user with ID {0} found".format(friendEmail)


@app.route('/friend_search', methods=['POST'])
@flask_login.login_required
def search_friend():
    friendID = flask.request.form['friendID']
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    if cursor.execute("SELECT user_id FROM Users WHERE user_id = '{0}'".format(friendID)):
        return "User with ID {0} found".format(friendID)
    else:
        return "No user with ID {0} found".format(friendID)


@app.route('/friend_list', methods=['POST'])
@flask_login.login_required
def list_friend():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    cursor.execute("SELECT UID2 FROM Friendship WHERE UID1 = '{0}' OR UID2 = '{0}'".format(uid))
    data = cursor.fetchall()
    # data= [x[0] for x in data]
    # data= ', '.join(data)
    return "You are friends with {0}".format(data)


@app.route('/friend_recommendation', methods=['GET', 'POST'])
@flask_login.login_required
def friend_recommendation():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    recommendations = {}  # dictionary of {uid: count}

    # First, get all friends
    cursor = conn.cursor()
    cursor.execute("SELECT UID2 FROM Friendship WHERE UID1 = '{0}' OR UID2 = '{0}'".format(uid))

    data = cursor.fetchall()
    friends = []  # list of user's friends
    for friend in data:
        friends.append(friend[0])

    # Then find friends of friends
    for friend in friends:
        cursor.execute("SELECT UID2 FROM Friendship WHERE UID1 = '{0}' OR UID2 = '{0}'".format(friend))
        data = cursor.fetchall()
        for friend2 in data:
            if friend2[0] == uid:
                continue
            if friend2[0] not in friends:  # add to dict
                if friend2[0] not in recommendations:
                    recommendations[friend2[0]] = 1
                else:
                    recommendations[friend2[0]] += 1

    sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

    return "You should be friends with {0}".format([getUserNameFromID(i[0]) for i in sorted_recommendations])


# ------------------- PHOTO ------------------- #
def photo_count(email):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM Pictures P, Users U WHERE U.email = '{0}' AND P.user_id = U.user_id".format(email))
    count = cursor.fetchall()
    count = count[0][0]
    return count


def comment_count(email):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM Comments C, Users U WHERE U.email = '{0}' AND C.user_id = U.user_id".format(email))
    count = cursor.fetchall()
    count = count[0][0]
    return count


@app.route('/top_users')
def user_activity():
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users")
    data = cursor.fetchall()

    scores = {}
    for user in data:
        each_score = photo_count(user[0]) + comment_count(user[0])
        scores[user[0]] = each_score
    sort = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_10 = sort[:10]
    return render_template('top_users.html', users=top_10, scores=scores)


@app.route('/album', methods=['GET', 'POST'])
def album():
    if flask.request.method == 'GET':
        return '''
        <h2>Create a new album:</h2>
               <form action='album' method='POST'>
                <input type='text' name='albumName' id='albumName' placeholder='album name'></input>
                <input type='submit' name='submit'></input>
               </form></br>
               <h2>List all albums:</h2>
               <form action='album_list' method='POST'>
                <input type='submit' name='submit'></input>
               </form></br>
                <h2> delete an album:</h2>
               <form action='album_delete' method='POST'>
                            <input type='text' name='deleteName' id='deleteName' placeholder='album name'></input>
                                            <input type='submit' name='submit'></input>
               </form></br>
               <h2> View all photos in an album:</h2>
               <form action='album_view' method='POST'>
                            <input type='text' name='viewName' id='viewName' placeholder='album name'></input>
                                            <input type='submit' name='submit'></input>
               </form></br>
               <button onclick="history.back()">Go Back</button>
           <a href='/'>Home</a>
               '''
    # The request method is POST (page is recieving data)
    albumName = flask.request.form['albumName']
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor.execute("INSERT INTO Albums (Name, user_id) VALUES ('{0}', '{1}')".format(albumName, uid))
    conn.commit()
    return "Album {0} created".format(albumName)


@app.route('/album_list', methods=['POST'])
def list_album():
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM Albums")
    data = cursor.fetchall()
    data = [x[0] for x in data]
    data = ", ".join(data)
    return "You have the following albums: {0}".format(data)


@app.route('/album_view', methods=['POST'])
def view_album():
    aname = flask.request.form['viewName']
    aid = getAlbumIDfromName(aname)
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE album_id = '{0}'".format(aid))
    data = cursor.fetchall()
    photo = getAllPhotos(data)
    return render_template('hello.html', photos=photo, base64=base64)


# delete album
@app.route('/album_delete', methods=['POST'])
@flask_login.login_required
def delete_album():
    albumName = flask.request.form['deleteName']
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Albums WHERE Name = '{0}'".format(albumName))
    conn.commit()
    return "Album {0} deleted".format(albumName)


@app.route('/profile')
@flask_login.login_required
def protected():
    return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")


# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        imgfile = request.files['photo']
        album_id = getAlbumIDfromName(request.form.get('album_id'))
        caption = request.form.get('caption')
        tag = request.form.get('tag')
        photo_data = imgfile.read()
        if canAddPhoto(uid, album_id) == False:
            return render_template('hello.html', message="You cannot add photo to other's album!")
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption, album_id) VALUES (%s, %s, %s, %s )''',
                       (photo_data, uid, caption, album_id))
        cursor.execute("SELECT LAST_INSERT_ID()")
        picture_id = cursor.fetchall()[0][0]

        # if tag name already exists, fetch its id from database
        cursor.execute("SELECT tag_id FROM Tags WHERE name = '{0}'".format(tag))
        tag_id = cursor.fetchall()
        if len(tag_id) > 0:
            tag_id = tag_id[0][0]
        else:
            cursor.execute("INSERT INTO Tags (name) VALUES (%s)", tag)
            cursor.execute("SELECT LAST_INSERT_ID()")
            tag_id = cursor.fetchall()[0][0]
        cursor.execute("INSERT INTO Tagged(picture_id, tag_id) VALUES (%s, %s)", (picture_id, tag_id))
        conn.commit()
        return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!',
                               photos=getUsersPhotos(uid), base64=base64)
    # The method is GET so we return a  HTML form to upload the a photo.
    else:
        return render_template('upload.html')


def canAddPhoto(uid, album_id):
    # Check if the user is the owner of the album
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Albums WHERE album_id = '{}'".format(album_id))
    owner = cursor.fetchone()[0]
    return owner == uid


# end photo uploading code

@app.route('/delete/<photo_id>')
def delete_photo(photo_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Pictures WHERE picture_id = '{0}'".format(photo_id))
    conn.commit()
    return render_template('hello.html', message='Deleted successfully!')


# ------------------- tag ------------------- #
# Viewing your photos by tag name
@app.route('/my_tag')
@flask_login.login_required
def my_tag():
    cursor = conn.cursor()
    email = flask_login.current_user.id
    cursor.execute(
        "SELECT DISTINCT name FROM Tags, Users, Pictures, Tagged WHERE Users.email = '{}' AND Users.user_id = Pictures.user_id AND Pictures.picture_id = Tagged.picture_id AND Tags.tag_id = Tagged.tag_id".format(
            email))
    tag = cursor.fetchall()
    tag = [x[0] for x in tag]
    return render_template('my_tag.html', tag=tag)


# Viewing all photos by tag name
@app.route('/all_tag')
@flask_login.login_required
def all_tag():
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT name FROM Tags, Pictures, Tagged WHERE Pictures.picture_id = Tagged.picture_id AND Tags.tag_id = Tagged.tag_id")
    tag = cursor.fetchall()
    tag = [x[0] for x in tag]
    return render_template('all_tag.html', tag=tag)


@app.route('/add_tag', methods=['POST'])
@flask_login.login_required
def add_tag():
    tag = request.form.get('tag')
    picture_id = request.form.get('photo_id')
    cursor = conn.cursor()

    # if tag name already exists, fetch its id from database
    cursor.execute("SELECT tag_id FROM Tags WHERE name = '{0}'".format(tag))
    tag_id = cursor.fetchall()
    if len(tag_id) > 0:
        tag_id = tag_id[0][0]
    else:
        cursor.execute("INSERT INTO Tags (name) VALUES (%s)", tag)
        cursor.execute("SELECT LAST_INSERT_ID()")
        tag_id = cursor.fetchall()[0][0]

    # insert into tagged
    cursor.execute("INSERT INTO Tagged(picture_id, tag_id) VALUES (%s, %s)", (picture_id, tag_id))
    conn.commit()
    return render_template('hello.html', message='Tagged successfully!')


@app.route('/tag_all', methods=['POST'])
@flask_login.login_required
def tag_all():
    tag = request.form.get('tag_name')
    cursor = conn.cursor()
    cursor.execute("SELECT p.imgdata, p.picture_id, p.caption FROM Pictures p\
    JOIN tagged tgd ON p.picture_id = tgd.picture_id\
    JOIN tags t ON tgd.tag_id = t.tag_id\
    WHERE t.name = '{0}'".format(tag))
    photo = getAllPhotos(cursor.fetchall())
    return render_template('hello.html', photos=photo, base64=base64, message='Photo with tag {0} shown'.format(tag))


@app.route('/tag_popular', methods=['GET'])
@flask_login.login_required
def tag_popular():
    cursor = conn.cursor()

    # get 3 most popular tags
    cursor.execute("SELECT Tags.name, COUNT(*) AS tag_count\
                    FROM Tags\
                    JOIN Tagged ON Tags.tag_id = Tagged.tag_id\
                    GROUP BY Tags.name\
                    ORDER BY tag_count DESC\
                    LIMIT 3;")
    data = cursor.fetchall()
    # convert double nested tuples to list
    output=''
    if len(data) < 3:
        for i in range(len(data)):
            output += '#' + str(i + 1) + ': ' + data[i][0] + ' appears ' + str(data[i][1]) + ' times'
    else:
        for i in range(3):
            output+='#'+str(i+1)+': '+data[i][0]+ ' appears ' + str(data[i][1]) +' times'
    return output


# Photo search
@app.route('/tag_search', methods=['POST'])
def tag_search():
    raw_tag = request.form.get('tag')
    tag = raw_tag.strip().split()
    count = len(tag)
    tag = str(set(tag)).replace('{', '(').replace('}', ')')

    # Construct the SQL query imgdata, picture_id, caption
    query = f'''SELECT p.imgdata, p.picture_id, p.caption
                FROM Pictures p
                INNER JOIN tagged tgd ON p.picture_id = tgd.picture_id
                INNER JOIN tags t ON tgd.tag_id = t.tag_id
                WHERE t.name IN {tag}
                GROUP BY p.picture_id
                HAVING COUNT(DISTINCT t.tag_id) = {count};
                '''
    # Execute the query
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute(query)

    photo = getAllPhotos(cursor.fetchall())
    return render_template('hello.html', photos=photo, base64=base64, message='Search results for: ' + raw_tag)


# ------------------- comment ------------------- #
@app.route('/add_comment', methods=['POST'])
def comment():
    NOT_LOGGED_IN = -1
    comment = request.form.get('comment')
    photo_id = request.form.get('photo_id')
    try:
        uid = getUserIdFromEmail(flask_login.current_user.id)

    except:
        uid = NOT_LOGGED_IN  # visitor comment? conflict with sql schema

    # Users cannot leave comments on their own photos
    check = conn.cursor()

    check.execute("SELECT * FROM Pictures WHERE picture_id = '{0}' AND user_id = '{1}'".format(photo_id, uid))
    count = check.fetchall()
    # if returned tuple is not empty
    if count:
        return render_template('hello.html', message='You cannot comment on your own photo!')

    # normally insert comment
    cursor = conn.cursor()

    if uid != NOT_LOGGED_IN:  # if user is logged in
        cursor.execute('''INSERT INTO Comments (text, picture_id, user_id) VALUES (%s, %s, %s)''',
                       (comment, photo_id, uid))
    else:  # if user is not logged in
        cursor.execute('''INSERT INTO Comments (text, picture_id) VALUES (%s, %s)''', (comment, photo_id))

    conn.commit()
    return render_template('hello.html', message='Comment added!')


@app.route('/comment_search', methods=['POST'])
def comment_search():
    comment = request.form.get('comment')
    # Construct the SQL query
    query = f'''SELECT u.fname, COUNT(*) AS comment_count
                FROM Users u
                INNER JOIN Comments c ON c.user_id = u.user_id
                WHERE c.text = '{comment}'
                GROUP BY u.user_id
                ORDER BY comment_count DESC
                '''
    # Execute the query
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    # convert double nested tuples to list
    output = ''
    for i in range(len(data)):
        output += '#' + str(i + 1) + ': ' + data[i][0] + ' has ' + str(data[i][1]) + ' comments'
    return output


# ------------------- like ------------------- #
@app.route('/like/<photo_id>')
@flask_login.login_required
def like(photo_id):
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor.execute('''INSERT INTO Likes (picture_id, user_id) VALUES (%s, %s)''', (photo_id, uid))
    conn.commit()
    return render_template('hello.html', message='Liked!')


# 'You-may-also-like'
@app.route('/YMAL')
@flask_login.login_required
def YMAL():
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor.execute(f'''SELECT name FROM Pictures p, Tagged g, Tags t WHERE user_id = '{uid}' AND p.picture_id = g.picture_id
                   AND g.tag_id = t.tag_id GROUP BY t.tag_id ORDER BY COUNT(*) DESC LIMIT 3;''')
    tag_used = list(cursor.fetchall())
    tag_used = [x[0] for x in tag_used]
    count = len(tag_used)
    tag_used = str(set(tag_used)).replace('{', '(').replace('}', ')')

    # Perform a disjunctive search through all the photos for these three tags
    query = f'''SELECT p.imgdata, p.picture_id, p.caption
                    FROM Pictures p
                    INNER JOIN tagged tgd ON p.picture_id = tgd.picture_id
                    INNER JOIN tags t ON tgd.tag_id = t.tag_id
                    WHERE t.name IN {tag_used}
                    GROUP BY p.picture_id
                    HAVING COUNT(t.tag_id) <= {count}
                    ORDER BY COUNT(*) DESC
                    '''.format(tag_used, count)

    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    photo = getAllPhotos(cursor.fetchall())
    return render_template('hello.html', photos=photo, base64=base64, message='You may also like...')


# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
    app.run(port=5000, debug=True)
