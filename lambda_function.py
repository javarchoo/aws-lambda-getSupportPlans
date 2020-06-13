import boto3
import pymysql
import json
from datetime import datetime

# LOG start
print('Loading function')

# RDS Access INFO
# Access with Assigned Role, Block public access
bucket="<bucket-name>"
object_key="<object-key>"

def lambda_handler(event, context):
    
    rdsInfo = getRDSAccessInfo(bucket, object_key)
    rows = selectCredentials(rdsInfo)
    print(rows)
    
    str_list = []
    i = 1
    for row in rows:
        print("[" + str(i) + "]")
        print(row)
        result = insertSupportPlan(row[1], row[2], rdsInfo)
        str_list.append('Account ID: ' + result['AccountID'] + ', Support Plan: ' + result['SupportLevel'] + "\n")
        i+=1

    return ''.join(str_list)

def getRDSAccessInfo(bucket, object_key):
    s3 = boto3.resource('s3')
    content_object = s3.Object(bucket, object_key)
    file_content = content_object.get()['Body'].read().decode('utf-8')
    return json.loads(file_content)

def selectCredentials(rdsInfo):
    conn = getConn(rdsInfo)
    curs = conn.cursor()
    sql = """select account_id, access_key_id, secret_access_key from support_level_api_users where use_yn = true"""
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

    account_id = ''
    support_level = ''
    
    # caller_id확인 및 access_key_id, secret_access_key 유효 여부 확인    
    sts = boto3.client('sts',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key)
    identity = sts.get_caller_identity()    
    print(identity)
    account_id = identity['Account']

    try:
        # Support API supports only 'us-east-1' region.
        support = boto3.client('support', region_name='us-east-1',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
        response = support.describe_severity_levels()
        support_level = getSupportLevel(len(support.describe_severity_levels()['severityLevels']))

        print(response)

    except Exception as e:
        print(e)
        print('Error...')
#        raise e
        support_level = "Basic/Developer"

    insertRDS(account_id, support_level, rdsInfo)
    return {"AccountID": account_id, "SupportLevel": support_level}

def getSupportLevel(x):
    return {5: 'Enterprise', 4: 'Business'}[x]
