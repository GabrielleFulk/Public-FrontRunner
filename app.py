
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, desc, asc
from sqlalchemy.orm.attributes import flag_modified
import routeMaker
import json

app = Flask(__name__, template_folder='templates')

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:<<Postgress password goes here>>@localhost:5432/frontrunner'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

current_user = 1

class Path(db.Model):
    __tablename__ = 'Path'
    pid = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    times_run = db.Column(db.Integer, nullable=False, default=0)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    favorite = db.Column(db.Boolean, default=False)
    length = db.Column(db.Float, nullable=False)
    is_public = db.Column(db.Boolean, default=True)
    route = db.Column(db.JSON, nullable=True)

    def __init__(self, times_run, lat, lon, favorite, length, is_public, route):
        self.times_run = times_run
        self.lat = lat 
        self.lon = lon 
        self.favorite = favorite
        self.length = length
        self.is_public = is_public
        self.route = route


class User(db.Model):
    __tablename__= 'User'
    uid = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    email = db.Column(db.String(30), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(10))
    is_public = db.Column(db.Boolean, default=True)

    def __init__(self, email, username, password, phone, is_public):
        self.email = email
        self.username = username
        self.password = password
        self.phone = phone
        self.is_public = is_public

class Group(db.Model):
    __tablename__='Group'
    gid = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    is_public = db.Column(db.Boolean, default=True)
    owner = db.Column(db.Integer, nullable=False)

    def __init__(self, name, is_public, owner):
        self.name = name
        self.is_public = is_public
        self.owner = owner

class Runs(db.Model):
    __tablename__='Runs'
    pid = db.Column(db.Integer, db.ForeignKey('Path.pid'), primary_key=True, nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('User.uid'), primary_key=True, nullable=False)

    def __init__(self, pid, uid):
        self.pid = pid
        self.uid = uid

class Belongs(db.Model):
    __tablename__='Belongs'
    uid = db.Column(db.Integer, db.ForeignKey('User.uid'), primary_key=True, nullable=False)
    gid = db.Column(db.Integer, db.ForeignKey('Group.gid'), primary_key=True, nullable=False)

    def __init__(self, uid, gid):
        self.uid = uid
        self.gid = gid

class Friends(db.Model):
    __tablename__='Friends'
    uid = db.Column(db.Integer, db.ForeignKey('User.uid'), primary_key=True, nullable=False)
    friends = db.Column(db.ARRAY(db.Integer()))

    def __init__(self, uid, friends):
        self.uid = uid
        self.friends = friends
        
db.create_all()

## functions ##
def get_users_paths():
    data = Path.query.join(Runs, Runs.pid == Path.pid).filter_by(uid=current_user).order_by(asc(Runs.pid)).all()
    # data = Path.query.filter_by(creator=current_user).order_by(asc(Path.pid)).all()
    return data

#get public paths of user's friends
def get_friends_paths(friendID):
    data = Path.query.join(Runs, Runs.pid == Path.pid).filter_by(uid=friendID).order_by(asc(Runs.pid)).all()
    # data = Path.query.filter_by(creator=friendID, is_public=True).order_by(asc(Path.pid)).all()
    return data

#get all groups set to public that current user is not apart of
def get_public_groups():
    pGroups = Group.query.filter_by(is_public=True).all()
    usersGroups = get_users_groups()
    data = [g for g in pGroups if g not in usersGroups]
    return data

#get groups of current user
def get_users_groups():
    groupsOfUser = Belongs.query.filter_by(uid=current_user).all()
    usersGroups = []
    groups_data = []
    if groupsOfUser is not None:
        for g in groupsOfUser:
            usersGroups.append(g.gid)
        for g in usersGroups:
                groupName = Group.query.filter_by(gid=g).first()
                groups_data.append(groupName)
    return groups_data 

#get groups owned by current user           
def get_OwnedGroups():
    owned = Group.query.filter_by(owner=current_user).all()
    return owned

#get friends of current user
def get_friends():
    friendsOfUser = Friends.query.filter_by(uid=current_user).first()
    friend_data = []
    if friendsOfUser is not None and friendsOfUser.friends is not None: 
        for f in friendsOfUser.friends:
            friend = User.query.filter_by(uid=f).first()
            friend_data.append(friend)
    return friend_data



## routes ##

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        distance = request.form['distance']
        lat = request.form['lat']
        lon = request.form['lon']
        if distance == '' or float(distance) <= 0:
            return render_template('home.html', message='Please enter required fields with a valid distance')
        tupleRoute = routeMaker.mapBox((float(lon), float(lat)), float(distance))
        coords = json.dumps(tupleRoute[0])    
        pdata = Path(0, lat, lon, False, tupleRoute[1], True, coords)
        db.session.add(pdata)
        db.session.commit()
        pid = Path.query.filter_by(lat=lat, lon=lon).order_by(desc(Path.pid)).first().pid
        rdata = Runs(pid ,current_user)
        db.session.add(rdata)
        db.session.commit()
        return render_template('path.html', result=str(coords), lon =lon, lat = lat, dist = tupleRoute[1] )


@app.route('/my_paths_page')
def my_paths_page():
    return render_template('my_paths.html', paths=get_users_paths())

@app.route('/my_paths_page_increase_time', methods=['POST'])
def increase_times():
    if request.method == 'POST':
        pathInc = request.form['Increase']
        if pathInc is not None:
            path = Path.query.filter_by(pid=pathInc).first()
            path.times_run = path.times_run + 1
            flag_modified(path, "times_run")
            db.session.commit()

    return render_template('my_paths.html', paths=get_users_paths())

@app.route('/my_paths_page_decrease_time', methods=['POST'])
def decrease_times():
    if request.method == 'POST':
        pathDec = request.form['Decrease']
        if pathDec is not None:
            path = Path.query.filter_by(pid=pathDec).first()
            if path.times_run > 0:
                path.times_run = path.times_run - 1
                flag_modified(path, "times_run")
                db.session.commit()
    return render_template('my_paths.html', paths=get_users_paths())

@app.route('/show_path', methods=['POST'])
def show_path():
    if request.method == 'POST':
        pathID = request.form['pathID']
        path = Path.query.filter_by(pid=pathID).first()
        lon = path.lon
        lat = path.lat
        distance = path.length
        coords = path.route
        return render_template('path.html', result=str(coords), lon =lon, lat = lat, dist = distance)

@app.route('/delete_path', methods=['POST'])
def delete_path():
    if request.method == 'POST':
        pathID = request.form['pathID']
        run = Runs.query.filter_by(pid=pathID).first()
        db.session.delete(run)
        db.session.commit()
        path = Path.query.filter_by(pid=pathID).first()
        db.session.delete(path)
        db.session.commit()
    return render_template('my_paths.html', paths=get_users_paths())

@app.route('/favorite_path', methods=['POST'])
def favorite_path():
    if request.method == 'POST':
        pathID = request.form['pathID']
        path = Path.query.filter_by(pid=pathID).first()
        path.favorite = not path.favorite
        flag_modified(path, "favorite")
        db.session.commit()
    return render_template('my_paths.html', paths=get_users_paths())   

@app.route('/edit_path_privacy', methods=['POST'])
def edit_path_privacy():
    if request.method == 'POST':
        pathID = request.form['pathID']
        path = Path.query.filter_by(pid=pathID).first()
        path.is_public = not path.is_public
        flag_modified(path, "is_public")
        db.session.commit()
    return render_template('my_paths.html', paths=get_users_paths())   
        


@app.route('/groups_page')
def groups_page():
    return render_template('groups.html', groups=get_users_groups())

@app.route('/groups_display', methods=['POST'])
def groups_display():
    if request.method == 'POST':
        groupID = request.form['groupID']
        data = Group.query.filter_by(gid=groupID).first()
        members = Belongs.query.join(Group, Belongs.gid == Group.gid).filter_by(gid=groupID).all()
        usernames = []
        for m in members:
            un = User.query.filter_by(uid=m.uid).first().username
            usernames.append(un)
        owner = User.query.filter_by(uid=data.owner).first().username
        return render_template('group_display.html', groupName=data.name, groupMembers=usernames, groupOwner=owner)

@app.route('/create_group', methods=['POST'])
def create_group():
    if request.method == 'POST':
        name = request.form['groupName']
        if name == '':
            return render_template('groups.html', message='Please enter required fields.')
        if request.form['is_public'] == "True":
            is_public = True
        elif request.form['is_public'] == "False":
            is_public = False
        else:
            return render_template('groups.html', message='Please enter required fields.')
        owner = current_user
        gdata = Group(name, is_public, owner)
        try:
            db.session.add(gdata)
            db.session.commit()
            gid = Group.query.filter_by(name=name).first().gid
            bdata = Belongs(current_user, gid)
            db.session.add(bdata)
            db.session.commit()
            return render_template('home.html', message = 'Your group, %s, has successfully been created!'%(name))
        except exc.IntegrityError:
            db.session.rollback()
            return render_template('create_group.html', message='A group with that name already exists. Please choose a different name.')

@app.route('/join_group_page')
def join_group_page():
    return render_template('join_group.html', groups=get_public_groups())

@app.route('/join_group', methods=['POST'])
def join_group(): 
    if request.method == 'POST':
        gid = request.form['Join']
        if gid == '':
            return render_template('join_group.html', groups=get_public_groups())
        data = Belongs(current_user, gid)
        try:
            db.session.add(data)
            db.session.commit()
            return render_template('join_group.html', message= 'You have successfully joined the group!')
        except exc.IntegrityError:
            db.session.rollback()
            return render_template('join_group.html', message= 'You are already in that group.', groups=get_public_groups())

@app.route('/leave_group_page')
def leave_group_page():
    return render_template('leave_group.html', groups=get_users_groups())

@app.route('/leave_group', methods=['POST'])
def leave_group():
    if request.method == 'POST':
        gid = request.form['Leave']
        if gid == '':
            return render_template('leave_group.html', groups=get_users_groups())
        Belongs.query.filter_by(uid=current_user, gid=gid).delete()
        db.session.commit()
        return render_template('leave_group.html', message='You have successfully left the group.', groups=get_users_groups())

@app.route('/delete_group_page')
def delete_group_page():
    return render_template('delete_group.html', groups=get_OwnedGroups())

@app.route('/delete_group', methods=['POST'])
def delete_group():
    if request.method == 'POST':
        gid = request.form['Delete']
        if gid == '':
            return render_template('delete_group.html', groups=get_OwnedGroups())
        members = Belongs.query.filter_by(gid=gid).all()
        for m in members:
            db.session.delete(m)
            db.session.commit()
        Group.query.filter_by(owner=current_user, gid=gid).delete()
        db.session.commit()
        return render_template('delete_group.html', message='You have successfully deleted the group.', groups=get_OwnedGroups())



@app.route('/friends_page')
def friends_page():
    return render_template('friends.html', friends=get_friends())

@app.route('/search_users', methods=['POST'])
def search_users():
    if request.method == 'POST':
        search = request.form['q']
        user = User.query.filter_by(username=search).all()
        if user == []:
            return render_template('friends.html', message = 'The username you searched does not exist', friends=get_friends())
        else:
            return render_template('friends.html', friends=get_friends(), result=user[0].username)

@app.route('/add_friend', methods=['POST'])
def add_friend():    
    if request.method == 'POST':
        new_friend = request.form['result']
        new_friend_uid = User.query.filter_by(username=new_friend).first().uid
        if new_friend_uid is not current_user:
            friendsQ = Friends.query.filter_by(uid=current_user).all()
            if friendsQ == []:
                friend_list = [new_friend_uid]
                data = Friends(current_user, friend_list)
                db.session.add(data)
                db.session.commit()
                return render_template('friends.html', message='You are now friends with %s!'%(new_friend), friends=get_friends())
            else: 
                current_friendships = Friends.query.filter_by(uid = current_user).first()
                if current_friendships.friends is None:
                    current_friendships.friends = [new_friend_uid]
                    db.session.commit()
                    return render_template('friends.html', message='You are now friends with %s!'%(new_friend), friends=get_friends())
                else:    
                    if new_friend_uid not in current_friendships.friends:
                        current_friendships.friends.append(new_friend_uid)
                        flag_modified(current_friendships, "friends")
                        db.session.commit()
                        return render_template('friends.html', message='You are now friends with %s!'%(new_friend), friends=get_friends())
                    else:
                        return render_template('friends.html', message = 'You are already friends with this user!', friends=get_friends())
        else:
            return render_template('friends.html', message = 'You cannot be friends with yourself!', friends=get_friends())                

@app.route('/remove_friend', methods=['POST'])
def remove_friend():    
    if request.method == 'POST':
        friend = request.form['Remove']
        friend_uid = User.query.filter_by(username=friend).first().uid
        current_friendships = Friends.query.filter_by(uid = current_user).first()
        list_of_friends = current_friendships.friends
        list_of_friends.remove(friend_uid)
        flag_modified(current_friendships, "friends")
        db.session.commit()
        return render_template('friends.html', message='You have removed %s from your friends'%(friend), friends=get_friends())

@app.route('/show_friends_path', methods=['POST'])
def show_friends_path():
    if request.method == 'POST':
        friendUID = request.form['friendID'] 
        friendUser = User.query.filter_by(uid=friendUID).first()
        return render_template('friends_paths.html', friend=friendUser, paths=get_friends_paths(friendUID))



if __name__=='__main__':
    app.debug = True
    app.run()





