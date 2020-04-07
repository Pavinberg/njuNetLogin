'''
登陆或登出南京大学校园网
使用：
    登陆：python njunet.py login
    登出：python njunet.py logout
    帮助：python njunet.py --help
账号密码可在输入上述命令后提示输入。也可写在此文件的usernmae和password变量中，
避免每次都要输入。

Author: Pavinberg
Email: pavin0702@gmail.com
Repository: https://github.com/Pavinberg/njuNetLogin

'''

import sys
import re
import requests
import json
import time
import argparse
import getpass
import subprocess

###############################################################################
# 设置账号密码
###############################################################################
# default username = "xxxx"
# 你可以将自己的学号写在这里，避免每次都要输入

username = "xxxx"

# defualt password = "****"
# 你也可以将密码写在这里。但其他能够访问此文件的人都能看到你的密码，请谨慎填写。
# password 为默认值("****") 或为空字符串时，需要从命令行运行时输入密码。

password = "****"

###############################################################################


def getUserInfo() -> [dict, None]:
    ''' get user information '''
    url = "http://p.nju.edu.cn/portal_io/selfservice/userinfo/getlist"
    try:
        r = requests.get(url)
        cont = r.content
        if r.status_code != 200:
            return None
    except:
        return None
    js = json.loads(cont.decode("utf8"))
    return js.get("rows", [None])[0]


def getTimeInfo() -> [dict, None]:
    ''' get time information '''
    url = "http://p.nju.edu.cn/portal_io/selfservice/volume/getlist"
    try:
        cont = requests.get(url).content
    except:
        return None
    js = json.loads(cont.decode("utf8"))
    return js.get("rows", [None])[0]


def printInfo():
    ''' Get information of the account's balance and time used. '''
    def formatTime(secs):
        '''
        Input: total seconds
        Output: hour, minute, second
        Transfer secs to format of "hour, minute, second"
        '''
        hour = secs // 3600
        minute = (secs - hour * 3600) // 60
        second = secs - hour * 3600 - minute * 60
        return hour, minute, second

    userinfo = getUserInfo()
    if not userinfo:
        print(f"Warning: 已接入外网，但不能获得用户信息，"
              f"可能是校园网状况不稳定，或可能由于不在校园网环境下")
        sys.exit()
    print(f"账户：{userinfo['fullname']} {userinfo['username']}")
    balance = userinfo["account_balance"] / 10  # cents

    timeinfo = getTimeInfo()
    if not timeinfo:
        print(f"Warning: 读取时长信息失败，可能是校园网状况不稳定。"
              f"一般来说此时已经登陆了校园网，请稍后输入登陆命令查看余额信息"
              f"或用浏览器查看情况")
        sys.exit()
    totTime = timeinfo["total_time"]  # seconds

    PRICE = 180  # seconds per cent
    FREETIME = 30 * 3600  # seconds
    TOPTIME = 130 * 3600  # seconds
    paidTime = min(max(totTime - FREETIME, 0), TOPTIME - FREETIME)
    hour, minute, _ = formatTime(totTime)
    consumed = paidTime / PRICE
    print(f"余额：{balance/100:.2f} 元，已使用：{hour} 小时 {minute} 分钟, "
          f"本月已消费 {consumed/100:.2f} 元。")

    if totTime > TOPTIME:
        print("本月费用已封顶 20 元.")
    else:
        timeLeft = TOPTIME - max(FREETIME, totTime)
        moneyToPay = timeLeft / PRICE  # 1 cent for 6 mintes.
        if balance <= moneyToPay:  # balance not enough
            remainTime = balance * PRICE + max(0, FREETIME - totTime)
            h, m, _ = formatTime(remainTime)
            print(f"余额不足本月封顶，还可使用 {h:.0f} 小时 {m:.0f} 分钟。")
        else:
            h, m, _ = formatTime(TOPTIME - totTime)
            print(f"余额充足，距离封顶还有 {h} 小时 {m} 分钟。")


def checkInternet():
    try:
        r = requests.get("http://www.baidu.com")
        if r.status_code == 200:
            return True
        else:
            return False
    except:
        return False


def login(userCheck: str = None):
    ''' Login to campus network if network is unavailable.'''
    if checkInternet():
        printInfo()  # already logged in
        return
    print("正在登陆南京大学校园网...")
    global username, password
    if username == "xxxx" or username == "":
        username = str(input("输入账户名："))
        if userCheck and userCheck != username:  # check username's correction
            print(f"Error: 账户名为 {username} 而在命令中指定登陆用户为 {userCheck}")
            sys.exit()
    else:
        if userCheck and userCheck != username:
            print(f"文件中配置的账户为 {username}，与命令中指定账户不符。")
            cmd = input(f"是否使用命令中的账户 {userCheck} 作为登陆账户？(y/[n])")
            if cmd == 'y':
                username = userCheck
                password = "****"  # reset password
            else:
                sys.exit()
        print(f"账户名: {username}")
    if password == "****" or password == "":
        password = getpass.getpass("密码：")

    param = {
        "username": username,
        "password": password
    }
    url = "http://p.nju.edu.cn/portal_io/login"
    try:
        cont = requests.post(url, params=param).status_code
    except:
        print("登陆失败")

    if cont == 200:
        time.sleep(1)  # wait until login finishes, or may fail to get info.
        if checkInternet():
            print("登陆校园网成功")
            printInfo()
        else:
            print("登陆校园网失败")
    else:
        print("登陆校园网失败")


def checkProcess():
    ''' check if has background processes of yours '''
    ignoringCmd = set(["ssh", "sshd:", "vim", "emacs", "ps", "grep"])
    ignoringSess = re.compile(r"zsh|/sftp|/bin/bash")
    ignoringObj = re.compile(r"njunet.py")
    loginName = getpass.getuser()  # the login name of the user of the shell
    ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE)\
                   .communicate()[0]
    processes = ps.decode("utf8").strip().split('\n')
    nfields = len(processes[0].split()) - 1  # column numbers - 1
    from collections import Counter
    recDict = Counter()
    for row in processes[1:]:
        record = row.split(None, nfields)
        if record[0] == loginName:
            line = record[-1].split()
            if len(line) >= 2:
                command, obj = line[0:2]
            else:
                command, obj = line[0], ""
            if command not in ignoringCmd:
                if not ignoringSess.search(command) \
                   and not ignoringObj.search(obj):
                    recDict[record[-1]] += 1
    if len(recDict) == 0:
        return False
    print(f"Num   Command")
    for command, num in recDict.items():
        print(f"{num:>3}x  {command}")
    return True


def logout(userCheck: str = None):
    def doLogout():
        print("正在退出登陆南京大学校园网...")
        if checkProcess():
            cmd = input("\n有以上进程在运行，是否继续退出登陆校园网？(y/[n])")
            if cmd != "y":
                return None  # don't logout
        # logout
        url = "http://p.nju.edu.cn/portal_io/logout"
        for _ in range(3):
            requests.post(url)  # send logout
            if not checkInternet():
                print(f"已退出登陆校园网 "
                      f"账户：{name} {userid}")
                return
            time.sleep(0.5)
        else:
            print("退出登陆失败校园网，请重试，或用浏览器退出登陆。")

    userinfo = getUserInfo()
    if not userinfo:
        # print("没有连接到校园网")
        sys.exit()
    userid = userinfo["username"]
    name = userinfo["fullname"]
    if userCheck:
        if userCheck == userid:
            # log out if userCheck is set and the login id is right
            return doLogout()
        else:
            # ask nothing
            return

    global username
    if username == "xxxx" or username == "":
        print(f"Notice: 已登陆账户为 {name} {userid}")
        cmd = input("是否退出这个账户？(y/[n])")
        if cmd == 'y':
            return doLogout()  # else do nothing
    else:
        if username != userid:
            print(f"Notice: 已登陆账户为 {name} {userid} ，与您设置的账户"
                  f" {username} 不一致")
            cmd = input("是否退出这个账户？(y/[n])")
            if cmd == 'y':
                return doLogout()  # else do nothing
        else:
            return doLogout()


def main():
    if len(sys.argv) == 1:
        print(f"usage:\n    登陆: 'python njunet.py login'"
              f"\n    登出: 'python njunet.py logout'")
        sys.exit()
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["login", "logout"],
                        help=f"choose from login/logout to "
                        f"login or logout the NJU network")
    parser.add_argument("--user", "-u",
                        help="specify id to check when login/logout")
    args = parser.parse_args()
    if args.action == "login":
        login(args.user)
    else:
        logout(args.user)


if __name__ == '__main__' :
    main()
