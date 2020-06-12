import boto3
import pymysql
import json
from datetime import datetime

# LOG start
print('Loading function')

# RDS Access INFO
# Block public access
bucket="<BucketName>"
object_key="<ObjectKey>"

def lambda_handler(event, context):
    
    rdsInfo = getRDSAccessInfo(bucket, object_key)
    rows = selectCredentials(rdsInfo)
    print(rows)
    
    str_list = []
    for row in rows:
        print(row)
        result = insertSupportPlan(row[1], row[2], rdsInfo)
        str_list.append('Account ID: ' + result['AccountID'] + ', Support Plan: ' + result['SupportLevel'])

    return ''.join(str_list)

def getRDSAccessInfo(bucket, object_key):
    s3 = boto3.resource('s3')
    content_object = s3.Object(bucket, object_key)
    file_content = content_object.get()['Body'].read().decode('utf-8')
    return json.loads(file_content)

def selectCredentials(rdsInfo):
    conn = getConn(rdsInfo)
    curs = conn.cursor()
    sql = """select account_id, access_key_id, secret_access_key from support_level_api_users"""
    curs.execute(sql)
    rows = curs.fetchall()
    conn.close()
    return rows

def getConn(rdsInfo):
    host = rdsInfo['host']
    user = rdsInfo['user']
    password = rdsInfo['password']
    port = rdsInfo['port']
    db = rdsInfo['db']
    return pymysql.connect(host=host, user=user, password=password, port=port, db=db, charset='utf8')

def insertRDS(accountID, supportLevel, rdsInfo):
    conn = getConn(rdsInfo)
    curs = conn.cursor()
    print(accountID)
    sql = """insert into support_level_history(account_id,date_time,support_level)
             values (%s, %s, %s)"""
    print(supportLevel)
    curs.execute(sql, (accountID, datetime.today().strftime('%Y-%m-%d %H:%M:%S'), supportLevel))
    conn.commit()
    conn.close()
    
def insertSupportPlan(access_key_id, secret_access_key, rdsInfo):
    sts = boto3.client('sts',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key)
    # Support API supports only 'us-east-1' region.
    support = boto3.client('support', region_name='us-east-1',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key)

    try:
        response = support.describe_severity_levels()
        identity = sts.get_caller_identity()
        accountID = identity['Account']
        supportLevel = getSupportLevel(len(support.describe_severity_levels()['severityLevels']))
        print(identity)
        print(response)

        insertRDS(accountID, supportLevel, rdsInfo)
        return {"AccountID": identity['Account'], "SupportLevel": supportLevel}
    except Exception as e:
        print(e)
        print('Error...')
#        raise e
        return {"AccountID": identity['Account'], "SupportLeve": "unknown"}

def getSupportLevel(x):
    return {5: 'Enterprise', 4: 'Business'}[x]
