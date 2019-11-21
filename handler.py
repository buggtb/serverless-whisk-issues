import json
import base64
import boto3
from botocore.vendored import requests
import os
import time


def sessionDebug(params):
    isAuthorized(params)
    body = {
        "event": params
    }

    response = makeResponse(200, body)
    return response


def makeResponse(statusCode, body):
    response = {
        "statusCode": statusCode,
        "headers": makeCORSResponseHeaders(),
        "body": json.dumps(body)
    }
    return response

def makeCORSResponseHeaders():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': True,
    }

def expectValue(body, valueName):
    if valueName not in body:
        raise ValueError('Expected value name not found: {}'.format(valueName))
    return body[valueName]

def isAuthorized(params):
    if 'authorization' not in params["__ow_headers"]:
        print('Missing Authorization header')
        return False

    auth64 = params["__ow_headers"]['authorization']
    if not auth64.startswith('Bearer '):
        print('Missing auth bearer: '+auth64)
        return False

    auth64 = auth64[len('Bearer '):]
    auth = base64.b64decode(auth64).decode("utf-8")

    if auth != '123:123':
        print('Incorrect auth bearer: '+auth)
        return False

    return True

def sessionList(params):
    if not isAuthorized(params):
        return makeResponse(401, 'Auth rejected')

    sol = expectValue(params, 'sol')
    experiment = expectValue(params, 'experiment')

    s3 = getS3()
    contents = getBucketContents(s3, getBucketName())
    paths = getPathListFromS3Contents(contents)
    expPaths = filterPathsFor(paths, getSessionsRoot(), sol, experiment, False)

    # Run through each, split the file name up and get the relevant parameters out
    result = []
    for path in expPaths:
        fileName = os.path.basename(path)

        s3Item = getS3ObjectForKey(path, contents)
        unixtime = getS3ObjectLastModifiedUnixTime(s3Item)

        # Name: strip off the .json
        # Date: is the file date from S3
        item = { 'name': fileName.split('.')[0], 'date': unixtime, 'sessionFileName': fileName }

        result.append(item)

    # Order them by date
    def takeDate(elem):
        return elem['date'];
    result.sort(key=takeDate, reverse=True)

    response = makeResponse(200, result)
    return response


def getS3():
    s3 = boto3.resource('s3')
    return s3

def getBucketContents(s3, bucketName):
    bucket = s3.Bucket(bucketName)
    return bucket.objects.all()

def getPathListFromS3Contents(contents):
    result = []
    for item in contents:
        result.append(item.key)
    return result

def getBucketName():
    return os.environ['DATA_BUCKET']

def filterPathsFor(paths, category, sol, experiment, returnStripped):
    mustStartWith = makePathFor(category, sol, experiment)
    return filterPaths(paths, mustStartWith, returnStripped)

def makePathFor(category, sol, experiment):
    return '{}/{}/{}/'.format(category, sol, experiment)

def filterPaths(paths, mustStartWith, returnStripped):
    result = []
    for path in paths:
        if path.startswith(mustStartWith):
            if returnStripped == True:
                result.append(path[len(mustStartWith):])
            else:
                result.append(path)

    return result

def getSessionsRoot():
    return 'Sessions'

def getS3ObjectForKey(key, bucketContents):
    for item in bucketContents:
        if item.key == key:
            return item
    return None

def getS3ObjectLastModifiedUnixTime(obj):
    return int(time.mktime(obj.last_modified.timetuple()))
