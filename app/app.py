import hashlib
import random
import threading
import time
import urllib

import redis
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, json, jsonify, request, make_response
from flask_cors import CORS
# r'/*' 是通配符，让本服务器所有的URL 都允许跨域请求

import requests

app = Flask(__name__)
CORS(app, resources=r'/*')
re_1 = redis.Redis(host='redis', port=6379)
app.config.from_object('config')
db = SQLAlchemy(app, use_native_unicode='utf8')
# 创建md5对象
m = hashlib.md5()
# 当前登录回调的用户
line_dict = set()

qrSource = ''
remote_url = 'http://159.138.135.12:8080'
memberList = []


class User(db.Model):
    """用户"""
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    id = db.Column(db.Integer, doc='用户id', primary_key=True, autoincrement=True, unique=True, nullable=False,
                   default=False)
    nickname = db.Column(db.String(20), doc='昵称', default='Wanted User', nullable=False, unique=True)
    password_hash = db.Column(db.String(128), doc='密码', nullable=False)
    mobile = db.Column(db.String(120), doc='手机号码', nullable=False)
    payPassword = db.Column(db.String(32), doc='支付密码', nullable=False)
    money = db.Column(db.Float, doc='账户余额', default=50, nullable=False)
    description = db.Column(db.String(50), doc='个性签名', default='这个人很懒，什么也没留下', nullable=False)
    isAdmin = db.Column(db.Boolean, doc='是否管理员', default=False)
    isProxy = db.Column(db.Boolean, doc='是否是代理', default=False)
    loginCipher = db.Column(db.String(150), doc='登录卡密', default=False)
    account = db.Column(db.String(150), doc='微信号', default=False)
    accountAlias = db.Column(db.String(150), doc='微信号别名', default=False)
    name = db.Column(db.String(150), doc='微信号名', default=False)
    headimg = db.Column(db.String(150), doc='微信头像', default=False)
    status = db.Column(db.Integer, doc='微信状态', default=False)
    type = db.Column(db.Boolean, doc='微信登录状态', default=False)
    taskId = db.Column(db.Integer, doc='任务Id', default=False)


class Ciphers(db.Model):
    __tablename__ = 'ciphers'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    cipher = db.Column(db.String(32), doc='密钥', primary_key=True)
    status = db.Column(db.Integer, doc='状态', default=False)
    type = db.Column(db.Integer, doc='类型 1周卡 2 月卡 3年卡 ', default=False)
    activeTime = db.Column(db.DateTime, doc='激活时间', default=False)
    amount = db.Column(db.DECIMAL(10, 2), doc='价格', default=False)
    royalty = db.Column(db.Float, doc='提成比例', default=False)


# 后台管理端
@app.route('/')
def index():
    return 'Hello World!'


# 用户端
@app.route('/user')
def user_index():
    return 'userPage'


# ========================zhaoxin===============================================
# 总后台登录
@app.route('/admin/login', methods=('GET', 'POST', 'OPTIONS'))
def admin_login():
    if request.method == 'OPTIONS':
        result_text = {"statusCode": 200, "message": "文件上传成功"}
        response = make_response(jsonify(result_text))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'OPTIONS,HEAD,GET,POST'
        response.headers['Access-Control-Allow-Headers'] = 'x-requested-with'
        return response
    mobile = request.args.get('mobile')
    password = request.args.get('password')
    if not password:
        password = "1"

    m.update(password.encode(encoding='utf-8'))
    password_hash = m.hexdigest()
    s = User.query.get(1)
    User.query.filter_by(id=mobile, password_hash=password_hash).all()
    if s is None:
        return "空数据"
    else:
        return "有数据"


# =========================zhaoxin==============================================

def run_wxpy():
    print("------------------")


@app.route('/api/login')
def login_remote_service():
    # 查找apikey是否存在
    apikey = re_1.get('apikey')
    if not apikey:
        url = 'http://api.aiheisha.com/foreign/auth/login.html'
        r = requests.post(url=url, data={'phone': '18008083201', 'password': '123456'},
                          headers={'Content-Type': 'application/x-www-form-urlencoded'})
        result = json.loads(r.text)
        apikey = result.get('data').get('apikey')
        re_1.set('apikey', apikey)
        print(apikey)

    scan_url = 'http://api.aiheisha.com/foreign/message/scanNew.html'
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    if not token:
        ticks = time.time()
        hswebtime = str(ticks) + '_' + str(random.randint(1, 50))
        b = (hswebtime + '399d3098a3627eb2df1329ccd77b03e87d556fcace085558250eeb126bc95e14').encode(encoding='utf-8')
        m.update(b)
        token = m.hexdigest()
        re_1.set('token', token)
        re_1.set('hswebtime', hswebtime)
    # 设置消息通知接口url
    set_url = 'http://api.aiheisha.com/foreign/user/setUrl.html'

    set_response = requests.post(url=set_url, data={'callbackSend': remote_url + '/callback_send',
                                                    'wacatout': remote_url + '/wacat_out',
                                                    'messagelog': remote_url + '/message_log',
                                                    'crowdlog': remote_url + '/crowd_log',
                                                    'addfriendlog': remote_url + '/add_friend_log',
                                                    'addgrouplog': remote_url + '/add_group_log',
                                                    'delfriendlog': remote_url + '/del_friend_log',
                                                    'newfriendlog': remote_url + '/new_friend_log',
                                                    },
                                 headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                          'apikey': apikey,
                                          'Hswebtime': hswebtime
                                          })
    # set_res = json.loads(set_response.text)
    print(set_response.text)
    global qrSource
    qrSource = ''
    response = requests.post(url=scan_url, data={'callback_url': remote_url + '/callback_login'},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)
    print(response.text)

    if result.get('code') == 1:
        task_id = result.get('data').get('task_id')
        # threading.Thread(target=run_wxpy).start()
        while not qrSource:
            time.sleep(1)
        file = urllib.request.urlopen(qrSource)
        f_data = file.read()
        file.close()
        response = make_response(f_data)
        response.headers['Content-Type'] = 'image/jpeg'
        return response

    else:
        re_1.delete('apikey')
        re_1.delete('token')
        re_1.delete('hswebtime')
        return 'error'


# 用户接口
@app.route('/user/login', methods=('GET', 'POST'))
def user_login():
    # db.create_all()
    return render_template('user/login.html')


@app.route('/user/login_page')
def user_login_page():
    return render_template('user/account_login.html')


@app.route('/user/register', methods=('GET', 'POST'))
def user_register():
    if request.method == 'GET':
        return render_template('user/regist.html')
    if request.method == 'POST':
        form = request.form
        password = ('wx-clean' + form.get('password')).encode(encoding='utf-8')
        m.update(password)
        user = User(mobile=form.get('username'), password_hash=m.hexdigest(), payPassword=m.hexdigest(), money=0,
                    nickname=form.get('username'))

        db.session.add(user)
        db.session.commit()
        return jsonify({'code': 200, 'url': '/user/login'})


# 微信接口
@app.route('/callback_login', methods=('GET', 'POST'))
def callback_login():
    # global qrSource
    data = request.form.get('data')
    if data:
        result = json.loads(data)
        global qrSource
        # global line_dict
        # line_dict.add({result['task_id']: result['url']})
        qrSource = result['url']
    print('请求方式为------->', request.method)
    args = request.args.get('data') or "args没有参数"
    print('args参数是------->', args)
    form = request.form.get('data') or 'form 没有参数'
    print('form参数是------->', form)
    return jsonify(args=request.args, form=request.form)


# 通用接口
@app.route('/callback_send', methods=('GET', 'POST'))
def callback_send():
    data = request.form.get('data')

    print(data)
    return data


# 接收群聊消息
@app.route('/crowd_log', methods=('GET', 'POST'))
def crowd_log():
    print('---------crowd_log--------------')
    data = request.form.get('data')

    print(data)
    return data


#  接收单聊消息
@app.route('/message_log', methods=('GET', 'POST'))
def message_log():
    print('---------message_log--------------')
    data = request.form.get('data')
    data = json.loads(data)
    if data.get('to_account') == 'filehelper':
        if data.get('content') == '1':
            sync_friend_list(my_account=data.get('my_account'))

    print(data)
    return data


#  接收新增好友通知
@app.route('/add_friend_log', methods=('GET', 'POST'))
def add_friend_log():
    print('---------add_friend_log--------------')
    data = request.form.get('data')

    print(data)
    return data


#  接收微信状态接口
@app.route('/wacat_out', methods=('GET', 'POST'))
def wacat_out():
    print('---------wacat_out--------------')
    data = request.form.get('data')
    data = json.loads(data)
    if data.get('type') == 1:
        send_msg(data.get('account'), 'filehelper', content='欢迎使用云尚清粉 \n 首次初始化 \n 请耐心等待 1～5分钟', content_type=1)
        time.sleep(20)
        sync_friend_list(data.get('account'))

    print(data)
    return data


#  有加入群时，接收入群微信信息
@app.route('/add_group_log', methods=('GET', 'POST'))
def add_group_log():
    print('---------add_group_log--------------')
    data = request.form.get('data')

    print(data)
    return data


#  删除好友时，接收删除好友通知
@app.route('/del_friend_log', methods=('GET', 'POST'))
def del_friend_log():
    print('---------del_friend_log--------------')
    data = request.form.get('data')

    print(data)
    return data


#  有新的好友添加时，接收新加好友信息
@app.route('/new_friend_log', methods=('GET', 'POST'))
def new_friend_log():
    print('---------new_friend_log--------------')
    data = request.form.get('data')

    print(data)
    return data


# 检测僵尸粉
def check_zombie(my_account, account):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    check_zombie_url = 'http://api.aiheisha.com/foreign/Friends/checkZombie.html'
    response = requests.post(url=check_zombie_url,
                             data={'callback_url': remote_url + '/check_zombie_callback', 'account': account,
                                   'my_account': my_account},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)

    return jsonify(result)


# 删除好友
def del_friend(my_account, account):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    del_friend_url = 'http://api.aiheisha.com/foreign/Friends/delFriend.html'
    response = requests.post(url=del_friend_url,
                             data={'callback_url': remote_url + '/del_friend_log', 'my_account': my_account,
                                   'account': account},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)

    return result


# 退出微信
def wchat_out(my_account):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    out_url = 'http://api.aiheisha.com/foreign/wacat/out.html'
    response = requests.post(url=out_url, data={'callback_url': remote_url + '/wacat_out', 'my_account': my_account},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)

    return result


@app.route('/check_zombie_callback', methods=('GET', 'POST'))
def check_zombie_callback():
    print('---------check_zombie_callback--------------')
    # 不为None 则为有问题数据
    data = request.form
    print(data)
    if data:
        context = data.get('content')
        # has_del = True if context.find("对方开启了朋友验证，你还不是他（她）朋友。请先发送朋友验证请求，对方验证通过后，才能聊天。") else False
        # has_pull_black_list = True if context.find("消息已发出，但被对方拒收了。") else False
        # if has_del or has_pull_black_list:
        #     send_card_msg(data.get('my_account'), 'filehelper', data.get('to_account'))
        #     send_card_msg2(data.get('my_account'), 'filehelper', data.get('to_account'))
        if data.get('result') == '1':
            send_card_msg(data.get('my_account'), 'filehelper', data.get('account'))
        if data.get('result') == '2':
            send_msg(data.get('my_account'), 'filehelper', '----------------被拉黑------------', 1)
            send_card_msg(data.get('my_account'), 'filehelper', data.get('account'))
            send_msg(data.get('my_account'), 'filehelper', '------------------------------', 1)

    else:
        print('-----------------')
    return 'success'


# 发送消息  内容类型：1文字、2图片、5视频、6文件、15动图
def send_msg(my_account, to_account, content, content_type):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    send_url = 'http://api.aiheisha.com/foreign/message/send.html'
    response = requests.post(url=send_url, data={'my_account': my_account, 'to_account': to_account, 'content': content,
                                                 'content_type': content_type},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)

    return result


# 发送名片
def send_card_msg(my_account, to_account, card_name):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    send_url = 'http://api.aiheisha.com/foreign/message/wacatCard.html'
    response = requests.post(url=send_url,
                             data={'my_account': my_account, 'to_account': to_account, 'card_name': card_name,
                                   'type': 1},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)
    print('发送名片-----------------' + response.text)

    return result


# 发送公众号名片
def send_card_msg2(my_account, to_account, card_name):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    send_url = 'http://api.aiheisha.com/foreign/message/sendCard.html'
    response = requests.post(url=send_url,
                             data={'my_account': my_account, 'to_account': to_account, 'card_name': card_name},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)
    print('发送公众号名片-----------------')

    return result


# 获取微信好友列表
def sync_friend_list(my_account):
    hswebtime = re_1.get('hswebtime')
    token = re_1.get('token')
    apikey = re_1.get('apikey')
    send_url = 'http://api.aiheisha.com/foreign/Friends/syncFriendList.html'
    response = requests.post(url=send_url,
                             data={'my_account': my_account, 'callback_url': remote_url + '/sync_friend_list_callback'},
                             headers={'Content-Type': 'application/x-www-form-urlencoded', 'token': token,
                                      'apikey': apikey,
                                      'Hswebtime': hswebtime
                                      })
    result = json.loads(response.text)

    return result


@app.route('/sync_friend_list_callback', methods=('GET', 'POST'))
def sync_friend_list_callback():
    print('---------sync_friend_list_callback--------------')
    print(request.form)
    data = request.form.get('info')
    data = json.loads(data)
    global memberList
    memberList.extend(data)
    print(data)
    print(memberList)
    # 判断是否接收完成
    live = (int(request.form.get('total')) % 100)
    print((int(int(request.form.get('total')) / 100) + (1 if live > 0 else 0)) == int(request.form.get(
        'currentPage')))
    isAll = (int(int(request.form.get('total')) / 100) + (1 if live > 0 else 0)) == int(request.form.get(
        'currentPage'))
    if isAll:
        print('-----数据接收完成-----')
        send_msg(request.form.get('my_account'), 'filehelper', content='初始化完成，开始工作', content_type=1)
        context = '本次您的待检查人数 ' + str(request.form.get('total')) + '\n 您的联系人共计 ' + str(
            request.form.get('total')) + '\n 开始检测僵尸粉'
        send_msg(request.form.get('my_account'), 'filehelper', content=context, content_type=1)
        do_action(request.form.get('my_account'))
    else:
        print('----等待数据完成----')

    return jsonify(request.form)


def do_action(my_account):
    if len(memberList) > 0:
        for item in memberList:
            check_zombie(my_account=my_account, account=item['account'])
    pass


@app.route('/create_db', methods=('GET', 'POST'))
def create_db():
    db.create_all()
    return '创建表'


# 后台接口


if __name__ == '__main__':
    app.run()
