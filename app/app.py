import datetime
import hashlib
import random
import string
import threading
import time
import urllib
from decimal import Decimal

import redis
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, json, jsonify, request, make_response
from flask_cors import CORS
# r'/*' 是通配符，让本服务器所有的URL 都允许跨域请求
import requests
from sqlalchemy.ext.declarative import declarative_base
import json

from uuid import UUID

Base = declarative_base()

app = Flask(__name__)
CORS(app, resources=r'/*')
re_1 = redis.Redis(host='redis', port=6379)
app.config.from_object('config')
db = SQLAlchemy(app, use_native_unicode='utf8')

# 公共页数
allPageSize = 10

# 当前登录回调的用户
line_dict = set()
black_list = []
zombie_list = []
friend_list = []
qrSource = ''
stepNum = 0
loginStatus = 0
remote_url = 'http://159.138.135.12:8080'
memberList = []

from sqlalchemy.ext.declarative import DeclarativeMeta


class OutputMixin(object):
    RELATIONSHIPS_TO_DICT = False

    def __iter__(self):
        return self.to_dict().iteritems()

    def to_dict(self, rel=None, backref=None):
        if rel is None:
            rel = self.RELATIONSHIPS_TO_DICT
        res = {column.key: getattr(self, attr)
               for attr, column in self.__mapper__.c.items()}
        if rel:
            for attr, relation in self.__mapper__.relationships.items():
                # Avoid recursive loop between to tables.
                if backref == relation.table:
                    continue
                value = getattr(self, attr)
                if value is None:
                    res[relation.key] = None
                elif isinstance(value.__class__, DeclarativeMeta):
                    res[relation.key] = value.to_dict(backref=self.__table__)
                else:
                    res[relation.key] = [i.to_dict(backref=self.__table__)
                                         for i in value]
        return res

    def to_json(self, rel=None):
        def extended_encoder(x):
            if isinstance(x, datetime):
                return x.isoformat()
            if isinstance(x, UUID):
                return str(x)

        if rel is None:
            rel = self.RELATIONSHIPS_TO_DICT
        return json.dumps(self.to_dict(rel), default=extended_encoder)


class User(OutputMixin, db.Model):
    """用户"""
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    id = db.Column(db.Integer, doc='用户id', primary_key=True, autoincrement=True, unique=True, nullable=False,
                   default=False)
    nickname = db.Column(db.String(20), doc='昵称', default='Wanted User', nullable=False, unique=True)
    password_hash = db.Column(db.String(128), doc='密码', nullable=False)
    mobile = db.Column(db.String(120), doc='手机号码', nullable=False)
    payPassword = db.Column(db.String(32), doc='支付密码', nullable=False)
    money = db.Column(db.DECIMAL(10, 2), doc='账户余额', default=0, nullable=False)
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

    # 多个对象
    def dobule_to_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            if getattr(self, key) is not None:
                result[key] = str(getattr(self, key))
            else:
                result[key] = getattr(self, key)
        return result


class Ciphers(OutputMixin, db.Model):
    __tablename__ = 'ciphers'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    cipher = db.Column(db.String(32), doc='密钥', primary_key=True)
    status = db.Column(db.Integer, doc='状态', default=False)
    type = db.Column(db.Integer, doc='类型id ', default=False)
    isActive = db.Column(db.Boolean, doc='是否激活', default=False)
    isSale = db.Column(db.Boolean, doc='是否销售', default=False)
    activeTime = db.Column(db.DateTime, doc='激活时间', default=None)
    saleTime = db.Column(db.DateTime, doc='销售时间', default=None)
    proxyId = db.Column(db.Integer, doc='代理id ', default=False)
    bindId = db.Column(db.Integer, doc='绑定id ', default=False)
    activeDays = db.Column(db.Integer, doc='有效天数 ', default=False)

    # 多个对象
    def dobule_to_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            if getattr(self, key) is not None:
                result[key] = str(getattr(self, key))
            else:
                result[key] = getattr(self, key)
        return result


class ActiveCodeOption(OutputMixin, db.Model):
    __tablename__ = 'active_code_option'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    id = db.Column(db.Integer, doc='类型id', primary_key=True, autoincrement=True, unique=True, nullable=False,
                   default=False)
    name = db.Column(db.String(150), doc='名称', default=False)
    price = db.Column(db.DECIMAL(10, 2), doc='价格', default=False)
    activeDays = db.Column(db.Integer, doc='有效天数 ', default=False)
    royalty = db.Column(db.Integer, doc='优惠比例', default=False)

    # 多个对象
    def dobule_to_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            if getattr(self, key) is not None:
                result[key] = str(getattr(self, key))
            else:
                result[key] = getattr(self, key)
        return result


class ActiveCodeBuy(OutputMixin, db.Model):
    __tablename__ = 'active_code_buy'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    id = db.Column(db.Integer, doc='id', primary_key=True, autoincrement=True, unique=True, nullable=False,
                   default=False)
    orderNo = db.Column(db.String(150), doc='订单号', unique=True, nullable=False, default=False)
    amount = db.Column(db.DECIMAL(10, 2), doc='价格', default=False)
    proxyId = db.Column(db.Integer, doc='代理id', default=False)
    buyTime = db.Column(db.DateTime, doc='购买时间', default=False)
    cipher = db.Column(db.TEXT(), doc='密钥', nullable=False, default=False)
    count = db.Column(db.Integer, doc='数量 ', default=False)
    royaltyAmount = db.Column(db.Float, doc='优惠金额', default=False)

    # 多个对象
    def dobule_to_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            if getattr(self, key) is not None:
                result[key] = str(getattr(self, key))
            else:
                result[key] = getattr(self, key)
        return result


class UserAmountRecord(OutputMixin, db.Model):
    __tablename__ = 'user_amount_record'
    __table_args__ = {'mysql_engine': 'InnoDB'}  # 支持事务操作和外键
    id = db.Column(db.Integer, doc='id', primary_key=True, autoincrement=True, unique=True, nullable=False,
                   default=False)
    orderNo = db.Column(db.String(150), doc='订单号', unique=True, nullable=False, default=False)
    amount = db.Column(db.DECIMAL(10, 2), doc='金额', default=False)
    status = db.Column(db.Integer, doc='状态 1发起 2完成', default=False)
    type = db.Column(db.Integer, doc='类型 1转帐 2 购买激活码 3 充值', default=False)
    addTime = db.Column(db.DateTime, doc='发生时间', default=False)
    remark = db.Column(db.String(255), doc='说明', nullable=False, default=False)
    fromId = db.Column(db.Integer, doc='来源 ', default=False)
    toId = db.Column(db.Integer, doc='去向 ', default=False)

    # 多个对象
    def dobule_to_dict(self):
        result = {}
        for key in self.__mapper__.c.keys():
            if getattr(self, key) is not None:
                result[key] = str(getattr(self, key))
            else:
                result[key] = getattr(self, key)
        return result


# 生成订单号
def get_order_code():
    order_no = str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) + str(time.time()).replace('.', '')[-7:]
    return order_no


def en_pass(str_pass):
    m = hashlib.md5()
    password = ('wx-clean' + str_pass).encode(encoding='utf-8')
    m.update(password)
    return m.hexdigest()


def convert_list_dict(items):
    dict_list = []
    for item in items:
        dict_list.append(
            json.loads(item.to_json())
        )
    return dict_list


def build_page_data(pageData):
    jsonData = {
        'code': 200,
        'records': convert_list_dict(pageData.items),
        'total': pageData.total,
        'pages': pageData.pages,
        'current': pageData.page,
        'hasPrev': pageData.has_prev,
        'hasNext': pageData.has_next
    }
    return jsonData


def to_json(all_vendors):
    v = [ven.dobule_to_dict() for ven in all_vendors]
    return v


# 返回分页模板
def returnPage(listObj):
    json = {
        'code': 200,
        'records': to_json(listObj.items),
        'total': listObj.pages * allPageSize
    }
    return jsonify(json)


# 返回列表模板
def returnList(list):
    data = {
        'code': 200,
        'records': to_json(list),
    }
    return jsonify(data)


def is_null(val):
    if val is None:
        return True
    if not val:
        return True
    if val == '':
        return True
    if val == 'null':
        return True
    if val == 'false':
        return True
    if val == 0:
        return True
    if val == '0':
        return True
    if val == False:
        return True
    return False


# 用户端
@app.route('/user')
def user_index():
    return 'userPage'


# =========================总后台接口地址=========================================================================================================
# 总后台登录
@app.route('/admin/login', methods=['POST'])
def admin_login():
    form = request.form
    username = form.get('username')
    password = form.get('password')
    proxy = int(form.get('proxy', 0))
    if username and password:
        password = en_pass(password)
        # admin = User.query.filter(User.mobile == username,User.isProxy == 1).first() if proxy == 1 else User.query.filter(User.mobile == username, User.isAdmin == 1).first()
        admin = User.query.filter(User.mobile == username, User.isAdmin == 1).first()
        if admin is None:
            res = {'msg': '用户名密码错误!!', 'code': 1001}
            return jsonify(res)
        else:
            adminUser = admin.__dict__
            if adminUser['password_hash'] == password:
                res = {'msg': '成功!', 'code': 200, 'data': json.loads(admin.to_json())}
                return jsonify(res)
            else:
                res = {'msg': '用户名密码错误!', 'pa': password, 'code': 1001}
                return jsonify(res)
    else:
        res = {'msg': '用户名密码不能为空!', 'code': 1001}
        return jsonify(res)


# 代理登录
@app.route('/proxy/login', methods=['POST'])
def proxy_login():
    form = request.form
    username = form.get('username')
    password = form.get('password')
    proxy = int(form.get('proxy', 0))
    if username and password:
        password = en_pass(password)
        # admin = User.query.filter(User.mobile == username,User.isProxy == 1).first() if proxy == 1 else User.query.filter(User.mobile == username, User.isAdmin == 1).first()
        admin = User.query.filter(User.mobile == username, User.isProxy == 1).first()
        if admin is None:
            res = {'msg': '用户名密码错误!!', 'code': 1001}
            return jsonify(res)
        else:
            adminUser = admin.__dict__
            if adminUser['password_hash'] == password:
                res = {'msg': '成功!', 'code': 200, 'data': json.loads(admin.to_json())}
                return jsonify(res)
            else:
                res = {'msg': '用户名密码错误!', 'pa': password, 'code': 1001}
                return jsonify(res)
    else:
        res = {'msg': '用户名密码不能为空!', 'code': 1001}
        return jsonify(res)


@app.route('/admin/register', methods=['POST'])
def admin_register():
    form = request.form
    password = en_pass(form.get('password'))
    proxy = int(form.get('proxy', 0))

    userJudge = User.query.filter(User.mobile == form.get('username')).first()
    if userJudge:
        return jsonify({'code': 1002, 'message': '用户已经存在请更换用户名'})
    else:
        user = User(mobile=form.get('username'), password_hash=password, payPassword=password, money=0,
                    nickname=form.get('username'))
        if proxy == 1:
            user.isProxy = 1
        else:
            user.isAdmin = 1
        db.session.add(user)
        db.session.commit()
        return jsonify({'code': 200, 'message': '注册成功'})


# 充值接口
@app.route('/admin/recharge', methods=('POST', 'GET'))
def recharge():
    form = request.form
    mobile = form.get('mobile')
    amount = int(form.get('amount', 0))
    adminId = int(form.get('adminId', 0))
    # 查询该用户
    userInfo = User.query.filter(User.mobile == mobile, User.isProxy == 1).first()
    if userInfo is None:
        return jsonify({'code': 1002, 'message': '用户不存在'})
    userAmount = userInfo.money
    userInfo.money = userAmount + amount
    db.session.add(userInfo)
    db.session.commit()
    # 写入记录
    addAmountRecord(amount, 2, 3, "充值", adminId, userInfo.id)
    return jsonify({'code': 200, 'message': '充值成功'})


# 充值记录
@app.route('/admin/recharge/list', methods=('POST', 'GET'))
def rechargeList():
    orderNo = request.args.get('orderNo')
    status = request.args.get('status')

    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)

    M = UserAmountRecord.query.filter_by(type=3)
    if not is_null(orderNo):
        M = M.filter_by(orderNo=orderNo)
    if not is_null(status):
        M = M.filter_by(status=status)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 获取所有用户列表
@app.route('/admin/user/all', methods=('POST', 'GET'))
def allUserList():
    list = User.query.filter().all()
    return returnList(list)


# 获取用户列表
@app.route('/admin/user/List', methods=('POST', 'GET'))
def userList():
    mobile = request.args.get('mobile')
    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)

    M = User.query.filter_by(isProxy=1)
    if not is_null(mobile):
        M = M.filter_by(mobile=mobile)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 删除用户
@app.route('/admin/user/delete', methods=('POST', 'GET'))
def deleteUser():
    userId = int(request.args.get('id'))
    u = User.query.filter_by(id=userId).first()
    db.session.delete(u)
    db.session.commit()
    return jsonify({'code': 200, 'data': {}, 'message': '删除成功'})


# 获取激活码类型列表
@app.route('/admin/activeType/list', methods=('POST', 'GET'))
def activeTypeList():
    list = ActiveCodeOption.query.filter().first()
    if is_null(list):
        a = ActiveCodeOption(name="日卡", price=0, activeDays=1, royalty=0)
        b = ActiveCodeOption(name="周卡", price=0, activeDays=7, royalty=0)
        c = ActiveCodeOption(name="月卡", price=0, activeDays=30, royalty=0)
        d = ActiveCodeOption(name="季卡", price=0, activeDays=90, royalty=0)
        e = ActiveCodeOption(name="半年卡", price=0, activeDays=180, royalty=0)
        f = ActiveCodeOption(name="年卡", price=0, activeDays=365, royalty=0)
        db.session.add(a)
        db.session.add(b)
        db.session.add(c)
        db.session.add(d)
        db.session.add(e)
        db.session.add(f)
        db.session.commit()
        return jsonify({'code': 200})
    list2 = ActiveCodeOption.query.filter().all()
    return returnList(list2)


# 保存激活码类型
@app.route('/admin/activeType/save', methods=('POST', 'GET'))
def saveActiveType():
    form = request.form
    dayAmount = form.get('dayAmount')
    dayBiLi = form.get('dayBiLi')
    zhouAmount = form.get('zhouAmount')
    zhouBiLi = form.get('zhouBiLi')
    monthAmount = form.get('monthAmount')
    monthBiLi = form.get('monthBiLi')
    jiduAmount = form.get('jiduAmount')
    jiduBiLi = form.get('jiduBiLi')
    bannianAmount = form.get('bannianAmount')
    bannianBiLi = form.get('bannianBiLi')
    yearAmount = form.get('yearAmount')
    yearBiLi = form.get('yearBiLi')
    a = ActiveCodeOption.query.filter_by(name='日卡').first()
    a.price = int(dayAmount)
    a.royalty = int(dayBiLi)
    b = ActiveCodeOption.query.filter_by(name='周卡').first()
    b.price = int(zhouAmount)
    b.royalty = int(zhouBiLi)
    c = ActiveCodeOption.query.filter_by(name='月卡').first()
    c.price = int(monthAmount)
    c.royalty = int(monthBiLi)
    d = ActiveCodeOption.query.filter_by(name='季卡').first()
    d.price = int(jiduAmount)
    d.royalty = int(jiduBiLi)
    e = ActiveCodeOption.query.filter_by(name='半年卡').first()
    e.price = int(bannianAmount)
    e.royalty = int(bannianBiLi)
    f = ActiveCodeOption.query.filter_by(name='年卡').first()
    f.price = int(yearAmount)
    f.royalty = int(yearBiLi)
    db.session.commit()
    return jsonify({'code': 200})


# 后台生成激活码
@app.route('/admin/activeCode/add', methods=('POST', 'GET'))
def addActiveCode():
    form = request.form
    adminId = int(form.get('adminId'))
    typeId = int(form.get('typeId'))
    admin = User.query.filter_by(id=adminId, isAdmin=1).first()
    if is_null(admin):
        return jsonify({'code': 1001, 'message': '权限错误'})
    create = createActiveCode(typeId)
    if create:
        return jsonify({'code': 200, 'message': '生成成功'})
    return jsonify({'code': 1002, 'message': '生成错误'})


@app.route('/admin/activeCode/list', methods=('GET', 'POST', 'OPTIONS'))
def activeCodeList():
    cipher = request.args.get('cipher')
    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)

    M = Ciphers.query.filter_by()
    if not is_null(cipher):
        M = M.filter_by(cipher=cipher)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 激活记录查询
@app.route('/admin/active/list', methods=('GET', 'POST', 'OPTIONS'))
def activeList():
    cipher = request.args.get('cipher')
    isProxy = request.args.get('isProxy')
    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)
    isProxy = 0 if is_null(isProxy) else int(isProxy)

    M = Ciphers.query.filter(Ciphers.isActive == 1, Ciphers.bindId > 0)
    if isProxy > 0:
        M = M.filter(Ciphers.proxyId > 0)
    if not is_null(cipher):
        M = M.filter_by(cipher=cipher)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 切换绑定
@app.route('/admin/active/changeBind', methods=('GET', 'POST', 'OPTIONS'))
def changeBind():
    form = request.form
    cipher = form.get('code')
    mobile = form.get('mobile')
    adminId = form.get('adminId')
    admin = User.query.filter_by(id=adminId, isAdmin=1).first()
    if is_null(admin):
        return jsonify({'code': 1001, 'message': '权限错误'})
    # 查询出新的账号
    newUser = User.query.filter_by(mobile=mobile).first()
    if is_null(newUser):
        return jsonify({'code': 1002, 'message': '没有该账号'})
    # 查询出激活码
    code = Ciphers.query.filter_by(cipher=cipher).first()
    if is_null(code):
        return jsonify({'code': 1003, 'message': '没有该激活码'})
    if code.isActive != 1:
        return jsonify({'code': 1004, 'message': '激活码未激活'})
    # 切换绑定
    code.bindId = newUser.id
    db.session.commit()
    return jsonify({'code': 200})


# 首页统计
@app.route('/admin/active/count', methods=('GET', 'POST', 'OPTIONS'))
def activeCount():
    dayCount = getDayCount()
    dayAllCount = getDayAllCount()
    ddayCount = getDDayCount()
    ddayAllCount = getDAllCount()
    return jsonify({
        'code': 200,
        'dayCount': dayCount,
        'dayAllCount': dayAllCount,
        'ddayCount': ddayCount,
        'ddayAllCount': ddayAllCount,
    })


# =========================总后台接口地址=========================================================================================================


# =========================代理接口地址=========================================================================================================

@app.route('/proxy/activeCode/list', methods=('GET', 'POST', 'OPTIONS'))
def proxyActiveCodeList():
    cipher = request.args.get('cipher')
    proxyId = request.args.get('proxyId')
    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)

    M = Ciphers.query.filter_by(proxyId=proxyId)
    if not is_null(cipher):
        M = M.filter_by(cipher=cipher)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


@app.route('/proxy/active/list', methods=('GET', 'POST', 'OPTIONS'))
def proxyActiveList():
    cipher = request.args.get('cipher')
    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    proxyId = request.args.get('proxyId')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)

    M = Ciphers.query.filter_by(proxyId=proxyId, isActive=1)
    if not is_null(cipher):
        M = M.filter_by(cipher=cipher)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 转账记录
@app.route('/proxy/recharge/list', methods=('POST', 'GET'))
def ProxyRechargeList():
    proxyId = request.args.get('proxyId')
    orderNo = request.args.get('orderNo')
    status = request.args.get('status')

    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)

    M = UserAmountRecord.query.filter_by(type=1, fromId=proxyId)
    if not is_null(orderNo):
        M = M.filter_by(orderNo=orderNo)
    if not is_null(status):
        M = M.filter_by(status=status)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 转账记录
@app.route('/proxy/buy/list', methods=('POST', 'GET'))
def ProxyBuyList():
    proxyId = request.args.get('proxyId')
    cipher = request.args.get('cipher')
    orderNo = request.args.get('orderNo')
    pageNum = request.args.get('pageNum')
    pageSize = request.args.get('pageSize')
    pageNum = 1 if is_null(pageNum) else int(pageNum)
    pageSize = allPageSize if is_null(pageSize) else int(pageSize)
    M = ActiveCodeBuy.query.filter_by(proxyId=proxyId)
    if not is_null(orderNo):
        M = M.filter_by(orderNo=orderNo)
    if not is_null(cipher):
        M = M.filter_by(cipher=cipher)
    ciphersPage = M.paginate(pageNum, pageSize)
    return returnPage(ciphersPage)


# 首页统计
@app.route('/proxy/active/count', methods=('GET', 'POST', 'OPTIONS'))
def proxyActiveCount():
    proxyId = request.args.get('proxyId')
    ddayCount = getDDayCount(int(proxyId))
    ddayAllCount = getDAllCount(int(proxyId))
    return jsonify({
        'code': 200,
        'ddayCount': ddayCount,
        'ddayAllCount': ddayAllCount,
    })


# 充值转账接口
@app.route('/proxy/to_recharge', methods=['POST'])
def to_proxy_recharge():
    form = request.form
    mobile = form.get('mobile')
    amount = int(form.get('amount', 0))
    proxyId = int(form.get('proxyId', 0))
    # 查询代理用户余额度
    proxyUserInfo = User.query.filter(User.id == proxyId, User.isProxy == 1).first()
    if proxyUserInfo is None:
        return jsonify({'code': 1002, 'message': '参数错误'})

    # 查询该用户
    userInfo = User.query.filter(User.mobile == mobile, User.isProxy == 1).first()
    if userInfo is None:
        return jsonify({'code': 1002, 'message': '代理用户不存在'})
    else:
        if proxyUserInfo.id == userInfo.id:
            return jsonify({'code': 1002, 'message': '非法操作'})
    # 减掉代理帐号余额
    if proxyUserInfo.money < amount:
        return jsonify({'code': 1002, 'message': '余额不足'})
    else:
        proxyUserInfo.money = proxyUserInfo.money - amount
        db.session.add(proxyUserInfo)
        db.session.commit()
    userAmount = userInfo.money
    userInfo.money = userAmount + amount
    db.session.add(userInfo)
    db.session.commit()

    # 写入记录
    addAmountRecord(amount, 2, 2, "转账", proxyId, userInfo.id)
    return jsonify({'code': 200, 'message': '转账成功'})


# 激活卡密
@app.route('/proxy/active/code', methods=['POST'])
def proxy_active_code():
    form = request.form
    mobile = form.get('mobile')
    code = form.get('code', '')
    proxyId = int(form.get('proxyId', 0))
    # 查询该用户
    userInfo = User.query.filter(User.mobile == mobile, User.isProxy == 0, User.isAdmin == 0).first()
    if userInfo is None:
        return jsonify({'code': 1002, 'message': '用户不存在'})
    ciphers = Ciphers.query.filter(Ciphers.cipher == code, Ciphers.proxyId == proxyId).first()
    if ciphers is None:
        return jsonify({'code': 1002, 'message': '没有该激活码'})
    else:
        if ciphers.__dict__['isActive'] != 0:
            return jsonify({'code': 1002, 'message': '该卡密已经被激活'})
    ciphers.bindId = userInfo.id
    ciphers.isActive = 1
    activeTime = str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))
    ciphers.activeTime = activeTime
    db.session.add(ciphers)
    db.session.commit()
    # 写入记录
    return jsonify({'code': 200, 'message': '激活成功'})


# 购买卡密接口
@app.route('/proxy/buy/ciphers', methods=['POST'])
def proxy_buy_ciphers():
    form = request.form
    type = int(form.get('type', 0))
    count = int(form.get('count', 0))
    proxyId = int(form.get('proxyId', 0))
    cipher_list = []
    # 查询代理用户余额度
    proxyUserInfo = User.query.filter(User.id == proxyId, User.isProxy == 1).first()
    if proxyUserInfo is None:
        return jsonify({'code': 1002, 'message': '参数错误'})
    opt = ActiveCodeOption.query.filter(ActiveCodeOption.id == type).first()
    if opt is None:
        return jsonify({'code': 1002, 'message': '参数错误'})
    # 判断余额
    allTotal = opt.price * count * Decimal.from_float((1 - opt.royalty))
    if allTotal > proxyUserInfo.money:
        return jsonify({'code': 1002, 'message': '余额不足'})
    ciphersList = Ciphers.query.filter(Ciphers.isActive == 0, Ciphers.isSale == 0, Ciphers.type == type).all()
    if ciphersList is None:
        return jsonify({'code': 1002, 'message': '没有该类型的库存了，请联系管理员'})
    elif len(ciphersList) < count:
        return jsonify({'code': 1002, 'message': '该类型的库存不足，请联系管理员'})
    else:
        for item in Ciphers.query.filter(Ciphers.isActive == 0, Ciphers.isSale == 0, Ciphers.type == type).limit(
                count).all():
            cipher_list.append(item.cipher)
            item.isSale = 1
            item.saleTime = str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))
            item.proxyId = proxyId
            db.session.add(item)
            db.session.commit()

    # 减掉代理帐号余额
    proxyUserInfo.money = proxyUserInfo.money - allTotal
    db.session.add(proxyUserInfo)
    db.session.commit()

    # 写入记录
    buyTime = str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))
    acb = ActiveCodeBuy(orderNo=get_order_code(), buyTime=buyTime, amount=allTotal, count=count, proxyId=proxyId,
                        cipher=",".join(cipher_list))
    db.session.add(acb)
    db.session.commit()
    addAmountRecord(allTotal, 2, 2, "购买激活码", proxyId, 0)
    return jsonify({'code': 200, 'message': '购买激活码成功'})


# =========================代理接口地址=========================================================================================================


# ===================公共方法================================================================================================================

# 公共写入流水记录
def addAmountRecord(amount, status, type, remark, fromId, toId):
    orderNo = get_order_code()
    addTime = str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())))
    record = UserAmountRecord(orderNo=orderNo, amount=amount, status=status, type=type, addTime=addTime, remark=remark,
                              fromId=fromId, toId=toId)
    db.session.add(record)
    db.session.commit()


# 后台创建激活码
def createActiveCode(typeId):
    cipher = getCode()
    c = Ciphers()
    c.cipher = cipher
    c.activeDays = 0
    c.status = 0
    c.type = typeId
    c.isActive = False
    c.isSale = False
    c.proxyId = 0
    c.bindId = 0
    # 查询出该类型的天数
    a = ActiveCodeOption.query.filter_by(id=typeId).first()
    c.activeDays = a.activeDays
    db.session.add(c)
    db.session.commit()
    return True


# 获取不重复的激活码
def getCode():
    code = ''.join(random.sample(string.ascii_letters + string.digits, 20))
    md5Code = en_pass(str(code))
    cipher = md5Code
    # 查询是否存在
    check = Ciphers.query.filter_by(cipher=cipher).first()
    if not is_null(check):
        # 如果为空，
        return getCode()
    else:
        return cipher


# 生成当天激活的统计
def getDayCount():
    all = db.session.execute(
        "select COUNT(c.`cipher`) dayCount FROM ciphers c WHERE c.isActive = 1 AND DATE_FORMAT(activeTime,'%y%m%d') = DATE_FORMAT(NOW(),'%y%m%d')")
    count = 0
    for x in all:
        count = count + x.dayCount
    return count


# 生成所有激活的统计
def getDayAllCount():
    all = db.session.execute("select COUNT(c.`cipher`) dayCount FROM ciphers c WHERE c.isActive = 1 ")
    count = 0
    for x in all:
        count = count + x.dayCount
    return count


# 生成代理当天激活的统计
def getDDayCount(proxyId=0):
    string = ""
    if proxyId > 0:
        string = " AND c.proxyId = " + str(proxyId)
    else:
        string = " AND c.proxyId > 0 "
    all = db.session.execute(
        "select COUNT(c.`cipher`) dayCount FROM ciphers c WHERE c.isActive = 1 " + string + " AND DATE_FORMAT(activeTime,'%y%m%d') = DATE_FORMAT(NOW(),'%y%m%d')")
    count = 0
    for x in all:
        count = count + x.dayCount
    return count


# 生成代理所有激活的统计
def getDAllCount(proxyId=0):
    string = ""
    if proxyId > 0:
        string = " AND c.proxyId = " + str(proxyId)
    else:
        string = " AND c.proxyId > 0 "
    all = db.session.execute("select COUNT(c.`cipher`) dayCount FROM ciphers c WHERE c.isActive = 1 " + string)
    count = 0
    for x in all:
        count = count + x.dayCount
    return count


# ===================公共方法================================================
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
        m = hashlib.md5()
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


def Caltime(date1, date2):
    # %Y-%m-%d为日期格式，其中的-可以用其他代替或者不写，但是要统一，同理后面的时分秒也一样；可以只计算日期，不计算时间。
    # date1=time.strptime(date1,"%Y-%m-%d %H:%M:%S")
    # date2=time.strptime(date2,"%Y-%m-%d %H:%M:%S")
    date1 = time.strptime(date1, "%Y-%m-%d")
    date2 = time.strptime(date2, "%Y-%m-%d")
    # 根据上面需要计算日期还是日期时间，来确定需要几个数组段。下标0表示年，小标1表示月，依次类推...
    # date1=datetime.datetime(date1[0],date1[1],date1[2],date1[3],date1[4],date1[5])
    # date2=datetime.datetime(date2[0],date2[1],date2[2],date2[3],date2[4],date2[5])
    date1 = datetime.datetime(date1[0], date1[1], date1[2])
    date2 = datetime.datetime(date2[0], date2[1], date2[2])
    # 返回两个变量相差的值，就是相差天数
    return date2 - date1


# 用户接口
@app.route('/user/login', methods=('GET', 'POST'))
def user_login():
    if request.method == 'GET':

        return render_template('user/login.html')
    else:
        activity_code = request.form.get('activity_code')
        ciphers = Ciphers.query.filter(Ciphers.cipher == activity_code, Ciphers.isActive == 1,
                                       Ciphers.bindId > 0).first()

        # user = User.query.filter(User.loginCipher == activity_code).first()
        if ciphers:
            opt = ActiveCodeOption.query.filter_by(id=ciphers.type).first()
            if opt is None:
                return jsonify({'code': 1003, 'url': '', 'message': '无效卡密'})
            else:
                if Caltime(time, ciphers.activeTime) <= opt.activeDays:
                    return jsonify({'code': 200, 'url': '/api/login'})
                else:
                    return jsonify({'code': 1003, 'url': '', 'message': '无效卡密'})


        else:
            return jsonify({'code': 1003, 'url': '', 'message': '无效卡密'})


@app.route('/user/login_page', methods=('GET', 'POST'))
def user_login_page():
    if request.method == 'GET':
        return render_template('user/account_login.html')
    if request.method == 'POST':
        form = request.form
        username = form.get('username')
        password = form.get('password')
        if username and password:
            password = en_pass(password)
            user = User.query.filter(User.mobile == username,
                                     User.isProxy == 0, User.isAdmin == 0).first()
            if user is None:
                res = {'msg': '用户名密码错误!', 'code': 1001}
                return jsonify(res)
            else:
                if user.__dict__['password_hash'] == password:
                    res = {'msg': '成功!', 'code': 200, 'url': '/api/login'}
                    return jsonify(res)
                else:
                    res = {'msg': '用户名密码错误!', 'code': 1001}
                    return jsonify(res)
        else:
            res = {'msg': '用户名密码不能为空!', 'code': 1001}
            return jsonify(res)


@app.route('/user/register', methods=('GET', 'POST'))
def user_register():
    if request.method == 'GET':
        return render_template('user/regist.html')
    if request.method == 'POST':
        form = request.form
        password = en_pass(form.get('password'))
        userJudge = User.query.filter(User.mobile == form.get('username'), User.isAdmin == 0, User.isProxy == 0).first()
        if userJudge:
            return jsonify({'code': 1002, 'message': '用户名已经存在'})
        else:
            user = User(mobile=form.get('username'), password_hash=password, payPassword=password, money=0,
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
    global stepNum
    if data.get('to_account') == 'filehelper':

        if data.get('content') == '100':
            sync_friend_list(data.get('my_account'))
        if data.get('content') == '1':
            if stepNum == 4:
                do_action_clean_auto(data.get('my_account'))
        elif data.get('content') == '2':
            if stepNum == 4:
                do_action_clean_maul(data.get('my_account'))
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
    global loginStatus
    global stepNum
    if data.get('type') == 1:
        if loginStatus == 0:
            loginStatus = 1
            stepNum = 1
            send_msg(data.get('account'), 'filehelper', content='欢迎使用云尚清粉 \n 首次初始化 \n 请耐心等待 1～5分钟', content_type=1)
            time.sleep(30)
            sync_friend_list(data.get('account'))
    else:
        loginStatus = 0

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
        global black_list
        global zombie_list
        global friend_list
        global memberList
        global stepNum
        if data.get('result') == '1':
            zombie_list.append(data)
            # send_card_msg(data.get('my_account'), 'filehelper', data.get('account'))
        if data.get('result') == '2':
            black_list.append(data)
        # send_msg(data.get('my_account'), 'filehelper', '----------------被拉黑------------', 1)
        # send_card_msg(data.get('my_account'), 'filehelper', data.get('account'))
        # send_msg(data.get('my_account'), 'filehelper', '------------------------------', 1)
        if data.get('result') == '0':
            friend_list.append(data)
        print(str(len(black_list)) + '_' + str(len(zombie_list)) + '_' + str(len(friend_list)) + '=' + str(
            len(memberList)))
        if (len(black_list) + len(zombie_list) + len(friend_list)) == len(memberList):
            send_msg(data.get('my_account'), 'filehelper',
                     '僵尸粉检测完毕！\n 总计人数' + str(len(memberList)) + '\n 被拉黑人数' + str(len(black_list)) + '\n 被删除人数' + str(
                         len(zombie_list)),
                     1)
            stepNum = 3
            time.sleep(5)
            send_msg(data.get('my_account'), 'filehelper',
                     '开始清理僵尸粉！\n回复 数字 1 发送名片并自动删除 \n回复 数字 2 发送只发送名片不删除\n请根据自己的需要选择对应的数字', 1)
            stepNum = 4

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
    global black_list
    global zombie_list
    global friend_list
    global stepNum
    black_list = []
    zombie_list = []
    friend_list = []
    stepNum = 2
    if len(memberList) > 0:
        for item in memberList:
            check_zombie(my_account=my_account, account=item['account'])
    pass


def do_action_clean_maul(my_account):
    if len(black_list) > 0:
        send_msg(my_account, 'filehelper', content='---------被拉黑列表-----------', content_type=1)
        for item in black_list:
            send_card_msg(my_account, 'filehelper', item['account'])

    if len(zombie_list) > 0:
        send_msg(my_account, 'filehelper', content='---------被删除列表-----------', content_type=1)
        for item in zombie_list:
            send_card_msg(my_account, 'filehelper', item['account'])
    pass


def do_action_clean_auto(my_account):
    if len(black_list) > 0:
        send_msg(my_account, 'filehelper', content='---------被拉黑列表-----------', content_type=1)
        for item in black_list:
            send_card_msg(my_account, 'filehelper', item['account'])
            del_friend(my_account, item['account'])

    if len(zombie_list) > 0:
        send_msg(my_account, 'filehelper', content='---------被删除列表-----------', content_type=1)
        for item in zombie_list:
            send_card_msg(my_account, 'filehelper', item['account'])
            del_friend(my_account, item['account'])
    pass


@app.route('/create_db', methods=('GET', 'POST'))
def create_db():
    db.create_all()
    return '创建表'


# 后台接口


if __name__ == '__main__':
    app.run()
