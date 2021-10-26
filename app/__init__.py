from flask import Flask, send_file, jsonify
from flask import render_template
from flask import request
from flask.helpers import send_from_directory
import pymongo
import gridfs
from bson.objectid import ObjectId
import magic
import datetime
import os
import shutil # 用于递归删除非空文件夹  
import zipfile
from io import BytesIO


app = Flask(__name__)
db_client = pymongo.MongoClient()
db = db_client.clapa1


@app.route("/")
def main_page():
    return render_template('index.html', events=db.event.find())


@app.route("/event/<id>")
def get_event(id):
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


@app.route("/getImage/<id>")
def get_image(id):
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


    fs = gridfs.GridFS(db, 'img')
    img = fs.find_one({"_id": ObjectId(id)})

# 文件接口，返回文件
@app.route("/getFile/<id>")
def get_file(id):
    # return id
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


@app.route("/getFilename", methods=['GET', 'POST'])
def get_filename():
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


# 路由：进入配置表页面
@app.route("/configuration")
def configuration_page():
    config_collection = db.configurations.find()
    return render_template('configuration.html', configs=config_collection)


# 更新配置表
@app.route("/configuration/update", methods=['POST'])
def configuration_update():
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


# 下载数据库中所有文件，按event分为不同文件夹，返回zip压缩文件
@app.route("/downloadFiles", methods=['GET'])
def downloadFiles():
    file_dir = "./app/static/experiment_data"
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
    with zipfile.ZipFile('./app/static/temporary_file.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for ev_name in os.listdir(file_dir):
            if len( os.listdir(os.path.join(file_dir, ev_name)) ) == 0:
                zf.write(os.path.join(file_dir, ev_name), arcname = ev_name)
            for file_name in os.listdir(os.path.join(file_dir, ev_name)):
                zf.write(os.path.join(file_dir, ev_name, file_name), arcname = os.path.join(ev_name, file_name))

    # os.remove('./app/static/experiment_data.zip')
    shutil.rmtree('./app/static/experiment_data') # 递归删除非空文件夹
    return send_file(open('./app/static/temporary_file.zip', 'rb'), mimetype = 'application/zip', as_attachment=True, attachment_filename='experiment_data.zip')


        

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
# app.run(debug=True ,port='5050')

