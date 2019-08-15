import os
import json
import requests
import tarfile
from copy import deepcopy
from ast import literal_eval
from chalice import Chalice
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
import boto3

# init chalice
app = Chalice(app_name='game-of-life')

''' HELPERS '''

def s3_public_image(body, bucket, key):
    boto3.client('s3').put_object(Body=body, Bucket=bucket, Key=key)
    boto3.resource('s3').ObjectAcl(bucket, key).put(ACL='public-read')

def load_params(ssm):
    params = ssm.get_parameters(Names=['COUNT', 'BOARD', 'ACCESS_TOKEN'])

    BOARD = None
    COUNT = None
    ACCESS_TOKEN = None

    for i in params['Parameters']:
        if i['Name'] == 'COUNT':
            COUNT = i['Value']
        elif i['Name'] == 'BOARD':
            BOARD = i['Value']
        elif i['Name'] == 'ACCESS_TOKEN':
            ACCESS_TOKEN = i['Value']

    # set to default values
    if not COUNT:
        COUNT = '1'
    if not BOARD:
        BOARD = [[-1, -1, -1, -1, -1, -1, -1, -1, -1],
                   [-1, 0, 0, 0, 0, 0, 0, 0, -1],
                   [-1, 0, 0, 1, 1, 1, 0, 0, -1],
                   [-1, 0, 0, 0, 1, 1, 1, 0, -1],
                   [-1, 0, 0, 0, 0, 0, 0, 0, -1],
                   [-1, -1, -1, -1, -1, -1, -1, -1, -1]]
    else:
        BOARD = literal_eval(BOARD)

    return BOARD, COUNT, ACCESS_TOKEN

''' GITHUB API '''

def make_issue(title, headers):
    ''' make issue with title on base_url '''
    url = os.environ['BASE_URL'] + '/issues'

    data = {
        'title': title
    }

    resp = requests.request('POST', url, data=json.dumps(data), headers=headers)

    if resp.status_code == 201:
        print('success')
    else:
        print(resp.content)
        print('failed to create issue')

def close_issues(headers):
    ''' Use github api to close all issues '''
    # info for get/patch
    get_all_url = os.environ['BASE_URL'] + '/issues'
    data = {
        'state': 'closed'
    }

    # get all issues
    resp   = requests.request('GET', get_all_url, headers=headers)
    if 400 < resp.status_code < 500:
        print("Couldn't get issues for repo")
        return
    issues = json.loads(resp.content)

    # close all issues
    for issue in issues:
        test = requests.request('PATCH', issue['url'],data=json.dumps(data), headers=headers)
        if 400 < test.status_code < 500:
            print("Couldn't close right: {}".format(issue['url']))

def make_contributions(x, y, headers):
    for i in range(10):
        make_issue('{}, {}'.format(x,y), headers)

    close_issues(headers)

''' GAME OF LIFE '''

def check_neighbors(copy, x, y):
    ''' sum points of neighboring blocks '''
    total = 0
    for i in range(-1,2):
        for j in range(-1,2):
            if i == 0 and j == 0:
                continue
            total += copy[x+i][y+j] if copy[x+i][y+j] != -1 else 0
    return total

def update_game(board):
    ''' update game based on rules of game of life '''
    copy = deepcopy(board)
    for i in range(1, int(os.environ['WIDTH'])-1):
        for j in range(1, int(os.environ['HEIGHT'])-1):
            total = check_neighbors(copy,i,j)
            if board[i][j]:
                if not 2 <= total < 4:
                    board[i][j] = 0
            else:
                if total == 3:
                    board[i][j] = 1

def count_to_index(count):
    ''' convert daily count 1-28 to coordinate '''
    i = (count // (int(os.environ['HEIGHT']) - 2)) + 1
    j = (count % (int(os.environ['HEIGHT']) - 2))
    if not j:
        i -= 1
        j  = 7
    return i,j

''' MAIN LAMBDA '''

@app.schedule('cron(38 15 * * ? *)')
def game_handler(event):
    ''' run game of life and create/close issues '''
    ssm = boto3.client('ssm', region_name='us-east-1')
    BOARD, COUNT, ACCESS_TOKEN = load_params(ssm)
    print("Count: " + COUNT)
    x, y = count_to_index(int(COUNT)) 
    print(x, y)
    print(BOARD[x][y])

    # Request head for github
    HEADERS = {
        'Authorization': 'token {}'.format(ACCESS_TOKEN)
    }

    # Make contributions if 1 for day
    if BOARD[x][y]:
        make_contributions(x, y, HEADERS)

    # update count / board if needed
    COUNT = str(int(COUNT) + 1)
    if int(COUNT) > 28:
        COUNT = '1'
        update_game(BOARD)
        BOARD = str(BOARD)
        ssm.put_parameter(Name='BOARD', Value=BOARD, Type='String', Overwrite=True)
    ssm.put_parameter(Name='COUNT', Value=COUNT, Type='String', Overwrite=True)

    return 0



''' Screenshot Tool '''

@app.schedule('cron(53 2 * * ? *)')
def screenshot_update(event):
    fox = webdriver.PhantomJS(executable_path='chalicelib/phantomjs', service_log_path='/tmp/log.log')
    fox.get('https://github.com/users/sambattalio-gol/contributions?to=' +
            datetime.today().strftime('%Y-%m-%d'))
    ss = fox.find_element(By.CLASS_NAME, 'js-yearly-contributions').screenshot_as_png
    fox.quit()

    s3_public_image(ss, os.environ['BUCKET'], os.environ['PIC_KEY'])
