from flask import Flask, send_file, jsonify, redirect, flash
from flask import render_template
from flask import request
from flask.globals import session
from flask.helpers import send_from_directory, url_for
import pymongo
import gridfs
from bson.objectid import ObjectId
import magic
import datetime
import os
import shutil # 用于递归删除非空文件夹  
import zipfile
import pickle
import numpy as np
import matplotlib.pyplot as plt
import re
from PIL import Image
from werkzeug.utils import secure_filename 
from CaChannel import ca, CaChannel, CaChannelException


app = Flask(__name__)
# db_client = pymongo.MongoClient("mongodb://222.29.111.164:27017/?readPreference=primary&appname=MongoDB%20Compass&ssl=false")
db_client = pymongo.MongoClient()
db = db_client.clapa_test
db_img = db_client.clapa9

home_app_dir = '/home/laser/mypython/py3_virtual_environment/py3_web_flask/site/app/'
# home_app_dir = "D:/2021/控制组/web前端相关/site2/服务器端文件/app/"

app.secret_key = 'laserplasma'
# app.config['PERMANENT_SESSION_LIFETIME'] = 3600

@app.route("/")
def main_page():
    session['logged_in'] = True
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        return render_template('index.html', events=db.event.find())
    else:
        return redirect(url_for('login'))


# 登陆界面
@app.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        form = request.form
        password = form.get('password')
    # if password == 'laser':
        # return password
        if password == 'laser':
            session['logged_in'] = True
            return 'success'
        else:
            flash('密码错误')
            return redirect(url_for('login'))
    else:
        return render_template('login.html')


# 显示MongoDB中对应id的event相关信息，及相关文件信息
@app.route("/event/<id>")
def get_event(id):
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        ev = db.event.find_one({"_id": ObjectId(id)})
        imgs_dict = {}
        files_dict = {}
        if len(ev['binary_data']) > 0:    
            for file_key in ev['binary_data']:
                file_type = ev['binary_data'][file_key]['file_type']
                # 按是否为图片文件分类
                if file_type[:5] == 'image':
                    imgs_dict[file_key] = ev['binary_data'][file_key]
                else:
                    files_dict[file_key] = ev['binary_data'][file_key]
        return render_template('event.html', event=ev, imgs = imgs_dict, files = files_dict)
    else:
        return redirect(url_for('login'))
    

# 返回储存在MongoDB的GridFS中的特定id的图片文件
@app.route("/getImage/<id>")
def get_image(id):
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        fs = gridfs.GridFS(db, 'img')
        img = fs.find_one({"_id": ObjectId(id)})
        img2 = fs.find_one({"_id": ObjectId(id)})
        # with open('test1.jpg','wb') as f:
        #     f.write(img2.read())
        # with open('test.jpg','wb') as f:
        #     f.write(img.read())
        # 判断文件的MIME类型
        MIME_type = magic.from_buffer(img2.read(), mime=True) 
        # print("what is", MIME_type)
        # img_binary = io.BytesIO(img.read())
        
        return send_file(img, mimetype = MIME_type)
    else:
        return redirect(url_for('login'))


# 文件接口，返回文件
@app.route("/getFile/<id>")
def get_file(id):
    # return id
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        fs = gridfs.GridFS(db, 'file')
        file = fs.find_one({"_id": ObjectId(id)})
        file2 = fs.find_one({"_id": ObjectId(id)})
        # with open('test3.pdf','wb') as f:
        #     f.write(file.read())
        if(file == None):
            return "No such file"
        MIME_type = magic.from_buffer(file2.read(), mime=True)
        # return MIME_type
        return send_file(file, mimetype = MIME_type)
    else:
        return redirect(url_for('login'))




@app.route("/getFilename", methods=['GET', 'POST'])
def get_filename():
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        params = request.values.to_dict() # GET传入参数
        ev_id = params['event_id'] # 对应事件id

        file_id_list = db.event.find_one(ObjectId(ev_id))['binary_data'].keys() # 事件id下的所有文件id
        files_information = {} # 将文件信息封装为json格式
        for file_id in file_id_list:
            file_document = db.file.files.find_one({"_id": ObjectId(file_id)})
            if file_document == None:  # 未找到id对应的文件
                continue
            else:
                if 'filename' in file_document.keys():
                    files_information[file_id] = {'file_id': str(file_document['_id']), 'filename': file_document['filename'], 'uploadDate': str(file_document['uploadDate'])}
        files_information = jsonify(files_information)
        return files_information
    else:
        return redirect(url_for('login'))

    


# 路由：进入配置表页面
@app.route("/configuration")
def configuration_page():
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        config_collection = db.configurations.find()
        return render_template('configuration.html', configs=config_collection)
    else:
        return redirect(url_for('login'))
    


# 更新配置表
@app.route("/configuration/update", methods=['POST'])
def configuration_update():
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        config_collection = db.configurations.find()
        try:
            form = request.form
            params = form.to_dict()
            if len(params['_id']) == 0: # 若为新插入的配置表
                write_Configuration_document(db, params['triger_sources'], params['pv_list'], params['ui_port'], params['archiver_port'])
            else:
                # print(params['_id'], params['triger_sources'], params['pv_list'], params['ui_port'], params['archiver_port'])
                # 若传回数据类型不正确，这一步会报错，然后返回fail
                update_Configuration_document(db, params['_id'], params['triger_sources'], params['pv_list'], params['ui_port'], params['archiver_port'])
        except:
            return "fail"
        return "success"
    else:
        return redirect(url_for('login'))



# 下载数据库中所有文件，按event分为不同文件夹，返回zip压缩文件
@app.route("/downloadFiles", methods=['GET'])
def downloadFiles():
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        file_dir = home_app_dir + "/static/experiment_data"
        if os.path.exists(file_dir) == False:
            os.mkdir(file_dir)
        for ev in db['event'].find():

            ev_dir = file_dir + '/' + ev['title']
            # 如果已经存在该文件夹，则在后添加标号
            if os.path.exists(ev_dir):
                i = 1
                while(True):
                    if os.path.exists(ev_dir + '(' + str(i) + ')'):
                        i += 1
                    else:
                        ev_dir += '(' + str(i) + ')'
                        break
            os.mkdir(ev_dir)

            for file_id in ev['binary_data'].keys():
                img_fs = gridfs.GridFS(db, 'img')
                file_fs = gridfs.GridFS(db, 'file')
                file = file_fs.find_one({"_id": ObjectId(file_id)})
                if file == None: # 在文件GridFs中未找到该文件，则在图片GridFS中查找
                    file = img_fs.find_one({"_id": ObjectId(file_id)})
                else:
                    file_info = db.file.files.find_one({'_id': ObjectId(file_id)})
                    if 'filename' in file_info.keys():
                        filename = file_info['filename']
                    else:
                        filename = file_id
                if file == None:
                    continue
                    
                with open(ev_dir + '/' + filename, 'wb') as f:
                    f.write(file.read())

        # 压缩从服务器端临时保存的文件
        with zipfile.ZipFile(home_app_dir + '/static/temporary_file.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for ev_name in os.listdir(file_dir):
                if len( os.listdir(os.path.join(file_dir, ev_name)) ) == 0:
                    zf.write(os.path.join(file_dir, ev_name), arcname = ev_name)
                for file_name in os.listdir(os.path.join(file_dir, ev_name)):
                    zf.write(os.path.join(file_dir, ev_name, file_name), arcname = os.path.join(ev_name, file_name))

        # os.remove(home_app_dir + '/static/experiment_data.zip')
        shutil.rmtree(home_app_dir + '/static/experiment_data') # 递归删除非空文件夹
        return send_file(open(home_app_dir+'/static/temporary_file.zip', 'rb'), mimetype = 'application/zip', as_attachment=True, attachment_filename='experiment_data.zip')

    else:
        return redirect(url_for('login'))


@app.route("/imageSources")
def get_allimagesSource():
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        source_list = db_img.list_collection_names()
        return render_template('Allimages.html', source_list = source_list)
    else:
        return redirect(url_for('login'))
    

@app.route("/getAllimages/<source>")
def get_allimages(source):
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        all_files = db_img[source].find({}, {'_id':1, 'filename':1})
        filenames = []
        for item in all_files:
            filenames.append({'filename': item['filename'], '_id': item['_id']})
        return render_template('Allimages_showimage.html', source = source, filenames = filenames)
    else:
        return redirect(url_for('login'))


# 打包下载所有实验图片
@app.route("/downloadAllImages", methods=['GET'])
def downloadAllImages():
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        file_dir = home_app_dir + "/static/experiment_data"
        if os.path.exists(file_dir) == False:
            os.mkdir(file_dir)
        if os.path.exists(file_dir + '/andor1') == False:
            os.mkdir(file_dir + '/andor1')
        
        for img_dict in db_img['andor1'].find():
            filename = img_dict['filename']
            pixelx = img_dict['pixelx']
            pixely = img_dict['pixely']
            img = pickle.loads(img_dict['data']).reshape(pixelx, pixely)
            outputImg = Image.fromarray( img, 'L')
            # 储存代价可能比较大
            with open(home_app_dir+'/log.txt','a+') as f:
                f.write(file_dir + '/andor1/'+ filename[:-4] + '.jpeg')
            outputImg.save(file_dir + '/andor1/'+ filename[:-4] + '.jpeg', 'JPEG', quality = 100, subsampling = 0)

        # 压缩从服务器端临时保存的文件
        with zipfile.ZipFile(home_app_dir + '/static/temporary_file.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for ev_name in os.listdir(file_dir):
                if len( os.listdir(os.path.join(file_dir, ev_name)) ) == 0:
                    zf.write(os.path.join(file_dir, ev_name), arcname = ev_name)
                for file_name in os.listdir(os.path.join(file_dir, ev_name)):
                    zf.write(os.path.join(file_dir, ev_name, file_name), arcname = os.path.join(ev_name, file_name))

        # os.remove(home_app_dir + '/static/experiment_data.zip')
        shutil.rmtree(home_app_dir + '/static/experiment_data') # 递归删除非空文件夹
        return send_file(open(home_app_dir+'/static/temporary_file.zip', 'rb'), mimetype = 'application/zip', as_attachment=True, attachment_filename='experiment_images.zip')

    else:
        return redirect(url_for('login'))
    

@app.route("/get_binary_images/<source>/<id>/<if_hd>")
def get_one_image(source, id, if_hd):
    if ('logged_in' in session) and session.get('logged_in') == True: # 判断是否登录
        collection = db_img[source]
        img_dict = collection.find_one(ObjectId(id))
        pixelx = img_dict['pixelx']
        pixely = img_dict['pixely']
        img = pickle.loads(img_dict['data']).reshape(pixelx, pixely)
        outputImg = Image.fromarray( img, 'L')
        if(if_hd != 'true'): # 是否是高清图
            outputImg = outputImg.resize( (int(200*pixelx/pixely), 200) )

        # 储存代价可能比较大
        outputImg.save(home_app_dir+'/static/temp_img.jpeg', 'JPEG', quality = 75, subsampling = 0)

        # 对于图片文件，可以不判断mime类型
        # with open(home_app_dir + '/static/temp_img.tiff', 'rb') as f:
        #     MIME_type = magic.from_buffer(f.read(), mime=True)
        return send_file(home_app_dir + '/static/temp_img.jpeg')

        # return send_from_directory(home_app_dir+'/static/temp_img.tiff', filename='pic')

        # MIME_type = magic.from_buffer(img2.read(), mime=True)
    else:
        return redirect(url_for('login'))
 

# 获取恢复PV的页面，并返回当前MongoDB下保存的所有发次
@app.route("/recover_pv")
def recover_pv():
    device_names = db_img.list_collection_names()

    # 集合保存发次，避免重复
    AllExperimentIndex = set([])
    for device_name in device_names:
        all_imgs = db_img[device_name].find({},{ "data": 0})
        for item in all_imgs:
            filename = item['filename']
            # 正则表达式匹配 发次 的int
            if not isinstance(filename, str):
                continue
            searchObj = re.search(r".*?(\d+).*", filename)
            if searchObj:
                AllExperimentIndex.add(searchObj.group(1))
    AllExperimentIndex = list(AllExperimentIndex)
    AllExperimentIndex.sort()
    # print(AllExperimentIndex)
    return render_template('recover_pv.html', AllExperimentIndex = AllExperimentIndex)


# 获取mongoDB中指定 设备 和 发次 的PV值
@app.route("/recover_page_get_pv/<device_name>/<ExperimentIndex>")
def recover_page_get_pv(device_name, ExperimentIndex):
    dict_device_pv = {'andor1':['13ANDOR1:cam1:SizeX', '13ANDOR1:cam1:SizeY']}
    andor1_sizex_now = 'N/A'; andor1_sizey_now = 'N/A'
    try:
        andor1_sizex_chan = CaChannel('13ANDOR1:cam1:SizeX'); andor1_sizey_chan = CaChannel('13ANDOR1:cam1:SizeY')
        andor1_sizex_chan.searchw(); andor1_sizey_chan.searchw()
        andor1_sizex_now = andor1_sizex_chan.getw(); andor1_sizey_now = andor1_sizey_chan.getw()
    except CaChannelException as e:
        print(e)

    device_collection = db_img[device_name]
    # 正则表达式查询
    selected_imgs = device_collection.find({"filename":{'$regex' : ".*"+ExperimentIndex+".*"}},{ "data": 0})
    # 多个结果只返回第一个
    for item in selected_imgs:
        pv_data = item
        break
    andor1_sizex_mongo = pv_data['pixelx']; andor1_sizey_mongo = pv_data['pixely']
    
    return_data = {'andor1': { 'andor1_sizex_mongo': andor1_sizex_mongo, 
                               'andor1_sizey_mongo': andor1_sizey_mongo,  
                               'andor1_sizex_now': andor1_sizex_now,
                               'andor1_sizey_now': andor1_sizey_now
                                }}

    return jsonify(return_data)


# 设置PV值
@app.route('/recover_page_set_pv', methods = ['POST'])
def recover_page_set_pv():
    if request.method == 'POST':
        form = request.values.to_dict()
        for pv_name in form.keys():
            pv_number = form[pv_name]
            if pv_number.isdigit(): # 判断返回值是否为数字
                pv_number = float(pv_number)
                try:
                    temp_chan = CaChannel(pv_name)
                    temp_chan.searchw()
                    temp_chan.putw(pv_number)
                except CaChannelException as e:
                    print(e)
                    return 'fail'
        return 'success'
    else:
        return 'fail'





############ 分割线 ###################################################################################################################

# 方法：向mongoDB插入一个新的配置表document，假设传入的参数全部为string类型
def write_Configuration_document(_db, _Triger_sources_list, _pv_list, _UI_port, _Archiver_port):
    configuration_document = {
        "modified_time": datetime.datetime.now(),
        "triger_sources": eval(_Triger_sources_list),
        "pv_list": eval(_pv_list), 
        "ui_port": int(_UI_port),
        "archiver_port": int(_Archiver_port)
    }
    configuration_collection = _db['configurations']
    configuration_collection.insert_one(configuration_document)

# 方法：向mongoDB更新一个现有的配置表，假设传入的参数全部为string类型
def update_Configuration_document(_db, _objectId, _Triger_sources_list, _pv_list, _UI_port, _Archiver_port):
    configuration_document = {
        "modified_time": datetime.datetime.now(),
        "triger_sources": eval(_Triger_sources_list),
        "pv_list": eval(_pv_list), 
        "ui_port": int(_UI_port),
        "archiver_port": int(_Archiver_port)
    }
    configuration_collection = _db['configurations']
    # 根据objectId找到文档并更新
    configuration_collection.update_one({"_id": ObjectId(_objectId)}, {"$set" :configuration_document})



# 直接用python运行flask服务
app.run(port='5055')
# app.run(debug=True, port='5055')
