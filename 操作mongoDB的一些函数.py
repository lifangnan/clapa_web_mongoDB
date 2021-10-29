import pymongo
from dateutil import parser
import bson
import gridfs
import datetime
import magic

# 向mongoDB写入一个主表document
def write_Main_document(_db, _title, _datatime_str, _Triger, _pv_data, _binary_data):
    main_document = {
            'title': _title,
            'timestamp': parser.parse(_datatime_str),
            'triger': _Triger,
            'pv_data': _pv_data,
            'binary_data': _binary_data
    }
    event_collection = _db['event']
    event_collection.insert_one(main_document)


# 向mongoDB写入一个配置表document
def write_Configuration_document(_db, _Triger_sources_list, _pv_list, _UI_port, _Archiver_port):
    configuration_document = {
        "modified_time": datetime.datetime.now(),
        "triger_sources": _Triger_sources_list,
        "pv_list": _pv_list, 
        "ui_port": _UI_port,
        "archiver_port": _Archiver_port
    }
    configuration_collection = _db['configurations']
    configuration_collection.insert_one(configuration_document)


# 将文件存入GridFS，并将对应objectID存在相应event中
def save_files(_db, _files, _file_category, _event_title, _source, _file_type, _datetime, _comment, _filename = None, _url = None):

    query_condition = {'title': _event_title}
    _event = _db['event'].find_one(query_condition)
    if _event == None: # 没有查询到符合条件的主表
        print("Warning: 没有title为" + _event_title + "的document记录!")
        return

    data = _files
    fs = gridfs.GridFS(_db, _file_category)
    if (_filename != None) and (_url != None):
        _objectId = fs.put(data=data, **{"filename": _filename, "url": _url})
    elif (_filename != None):
        _objectId = fs.put(data=data, **{"filename": _filename})
    elif (_url != None):
        _objectId = fs.put(data=data, **{"url": _url})
    else:
        _objectId = fs.put(data=data)

    _event['binary_data'][str(_objectId)] = {'file_id': _objectId,
                                "source": _source,
                                "file_type": _file_type,
                                "Timestamp": _datetime,
                                "comment": _comment,
                                }
    _db['event'].update_one(query_condition, {"$set": _event})


# 关联删除，删除GridFS中文件和和event中Binary_data
def delete_files_with_FileId(_db, _file_category, _FileId):
    if type(_FileId) == bson.ObjectId: # 保证_FileId变量为string类型
        _FileId = str(_FileId) 
    
    fs = gridfs.GridFS(_db, _file_category)
    fs.delete(bson.ObjectId(_FileId))

    for _event_document in _db['event'].find():
        if 'binary_data' in _event_document.keys():
            if _FileId in _event_document['binary_data'].keys(): # 在event document中找到了该文件的引用
                _event_document['binary_data'].pop(_FileId)
                query = {"_id": _event_document["_id"]}
                _db['event'].update_one(query, {"$set": _event_document})



if __name__ == '__main__':
    host = 'localhost'
    port = 27017
    dbname = 'clapa1'
    collection_name = 'event'

    # 连接mongoDB
    client = pymongo.MongoClient(host=host, port=port)
    db = client[dbname]
    collection = db[collection_name]


    # 例1：插入主表
    title = 'event2'
    datatime_str = '2021-10-20 20:02'
    Triger = 'triger1'
    pv_data = {"PV_name1":{"VAL": 1.1, "DESC": 'comment1'}, "PV_name2":{"VAL": 2.2, "DESC": 'comment2'}}
    binary_data = {}
    write_Main_document(db, title, datatime_str, Triger, pv_data, binary_data)

    # 例2：插入配置表
    _Triger_sources_list = [{"source": "client1", "type": "passive"}, {"source": "client2", "type": "active"}]
    _pv_list = ['pv_name1', 'pv_name2']
    _UI_port = 8888
    _Archiver_port = 7777
    write_Configuration_document(db, _Triger_sources_list, _pv_list, _UI_port, _Archiver_port)


    # with open('D:/2021/控制组/web前端相关/test.jfif','rb') as f:
    #     data = f.read()
    #     fs = gridfs.GridFS(db, 'img')
    #     fs.put(data=data, **{"filename": "pic2.jfif", "url": "url_str"})

    # fs = gridfs.GridFS(db, 'img')
    # a = fs.get(bson.ObjectId("617112d45c94854fcfb4b90a"))
    # with open("pic_test.jpg", 'wb') as f2:
    #     f2.write(a.read())


    # 例3：存储图片数据，并在关联的event中记录
    with open('D:/2021/控制组/web前端相关/pic1.jpeg','rb') as f:
        event_title = 'event1'
        source = 'EPICS-1'
        img = f.read()
        img2 = img
        file_type = magic.from_buffer(img2, mime=True)
        Datetime = datetime.datetime.now()
        comment = "a test image"
        filename = "pic1.jpeg"
        file_category = "img"
        save_files(db, img, file_category, event_title, source, file_type, Datetime, comment, _filename = filename, _url = None)

    # 例4：存储文件数据，并在关联的event中记录
    with open('D:/2021/控制组/2021-8-7虚拟加速器调束软件/机器学习束流调节/机器学习束流调节/PhysRevLett.126.104801 贝叶斯优化电子加速.pdf','r', encoding='utf-8') as f:
        type(f.read())
        file = f.read()
        file2 = file
        event_title = 'event1'
        source = 'EPICS-1'
        file_type = magic.from_buffer(file2, mime=True)
        Datetime = datetime.datetime.now()
        comment = "a pdf file"
        filename = "PhysRevLett.126.104801.pdf"   
        file_category = "file"
        save_files(db, file, file_category, event_title, source, file_type, Datetime, comment, _filename = filename, _url = None)

    # 例5：利用ObjectId删除文件和event中对应文件记录。
    for docu in db.img.files.find():
        print(docu['_id'])
    for docu in db.file.files.find():
        print(docu['_id'])  #所有的文件id
    delete_files_with_FileId(db, "img", "6176236d356982754a634d98") # 第二个参数可选"file"或"img"

