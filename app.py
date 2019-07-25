import os
from copy import deepcopy
from ast import literal_eval
from chalice import Chalice

# init chalice
app = Chalice(app_name='game-of-life')

''' GITHUB API '''

# Request head for github
HEADERS = {
    'Authorization': 'token {}'.format(os.environ['ACCESS_TOKEN'])
}

def make_issue(title):
    ''' make issue with title on base_url '''
    url = os.environ['BASE_URL'] + '/issues'

    data = {
        'title': title
    }

    resp = requests.request('POST', url, data=json.dumps(data), headers=HEADERS)

    if resp.status_code == 201:
        print('success')
    else:
        print(resp.content)
        print('failed to create issue')

def close_issues():
    ''' Use github api to close all issues '''
    # info for get/patch
    get_all_url = BASE_URL + '/issues'
    data = {
        'state': 'closed'
    }

    # get all issues
    resp   = requests.request('GET', get_all_url, headers=HEADERS)
    if 400 < resp.status_code < 500:
        print("Couldn't get issues for repo")
        return
    issues = json.loads(resp.content)

    # close all issues
    for issue in issues:
        test = requests.request('PATCH', issue['url'],data=json.dumps(data), headers=HEADERS)
        if 400 < test.status_code < 500:
            print("Couldn't close right: {}".format(issue['url']))

def make_contributions(x,y):
    for i in range(10):
        make_issue('{}, {}'.format(x,y))

    close_issues()

''' GAME OF LIFE '''

# default board for first month's run
START_BOARD = [[-1, -1, -1, -1, -1, -1, -1, -1, -1],
               [-1, 0, 0, 0, 0, 0, 0, 0, -1],
               [-1, 0, 1, 1, 1, 0, 0, 0, -1],
               [-1, 0, 0, 1, 1, 1, 0, 0, -1],
               [-1, 0, 0, 0, 0, 0, 0, 0, -1],
               [-1, -1, -1, -1, -1, -1, -1, -1, -1]]

# load init value for count if not there
if not os.environ.get('COUNT'):
    os.environ['COUNT'] = '1'

def check_neighbors(copy, x, y):
    ''' sum points of neighboring blocks '''
    total = 0
    for i in range(-1,2):
        for j in range(-1,2):
            total += copy[x+i][y+j] if copy[x+i][y+j] != -1 else 0
    return total

def update_game(board):
    ''' update game based on rules of game of life '''
    copy = deepcopy(board)
    for i in range(1, int(os.environ['WIDTH'])-1):
        for j in range(1, int(os.environ['HEIGHT'])-1):
            total = check_neighbors(copy,i,j)
            if total != 3:
                board[i][j] = 0
            else:
                board[i][j] = 1

def load_board():
    ''' load board from env variables '''
    if not os.environ.get('BOARD'):
        os.environ['BOARD'] = str(START_BOARD)
        return START_BOARD
    return literal_eval(os.environ['BOARD'])

def count_to_index(count):
    ''' convert daily count 1-28 to coordinate '''
    i = (count // (int(os.environ['HEIGHT']) - 2)) + 1
    j = (count % (int(os.environ['HEIGHT']) - 2))
    if not j:
        i -= 1
        j  = 7
    return i,j


''' MAIN LAMBDA '''

@app.schedule('cron(0 10 * * ? *)')
def game_handler(event):
    ''' run game of life and create/close issues '''
    print("Count: " + os.environ['COUNT'])
    x, y = count_to_index(int(os.environ['COUNT'])) 
    print(x, y)
    board = load_board()
    print(board[x][y])

    # Make contributions if 1 for day
    if board[x][y]:
        make_contributions(x, y)

    # update count / board if needed
    os.environ['COUNT'] = str(int(os.environ['COUNT']) + 1)
    if int(os.environ['COUNT']) > 28:
        os.environ['COUNT'] = '1'
        update_game(board)
        os.environ['BOARD'] = str(board)

