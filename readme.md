# clapa_web_mongoDB
## Howto run
1. Active python env: 
   
        Script/active

2. Start server: 
   
        flack run

## 2. 新增功能说明（2021.10.26）
2.1 修改MongoDB配置表：
'''
@app.route("/configuration/update", methods=['POST'])
def  configuration_update():
'''
2.2 返回当前event下的关联的文件信息：
'''
@app.route("/getFilename", methods=['GET', 'POST'])
'''
2.3 返回文件数据：
'''
@app.route("/getFile/<id>")
'''
2.4 林老师要求的功能，下载数据库中所有文件，按event分为不同文件夹，返回zip压缩文件
'''
@app.route("/downloadFiles", methods=['GET'])
'''
