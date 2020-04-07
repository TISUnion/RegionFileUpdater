# -*- coding: utf-8 -*-
import copy
import os
import json
import re
import time
try:
	import Queue
except ImportError:
	import queue as Queue


SourceWorldPath = '/home/survival-25501/quick/world/'
DestinationWorldPath = 'server/world/'
Prefix = '!!region'
PluginName = 'RegionFileUpdater'
LogFileFolder = 'log/'
LogFilePath = LogFileFolder + PluginName + '.log'
Debug_output = 0
DimensionRegionFolder = {-1: 'DIM-1/region/', 0: 'region/', 1: 'DIM1/region/'}
HelpMessage = '''------MCD ''' + PluginName + ''' v1.0------
一个更新本服区域文件至生存服!!qb存档区域文件的插件
§a【指令说明】§r
§7''' + Prefix + ''' §r显示帮助信息
§7''' + Prefix + ''' add §r添加玩家所在位置的区域文件
§7''' + Prefix + ''' add §6[d] [x] [z] §r添加指定的区域文件
§7''' + Prefix + ''' del §r删除玩家所在位置的区域文件
§7''' + Prefix + ''' del §6[d] [x] [z] §r删除指定的区域文件
§7''' + Prefix + ''' delete-all §r删除所有区域文件
§7''' + Prefix + ''' list §r列出待更新的区域文件
§7''' + Prefix + ''' history §r输出上一次update的结果
§7''' + Prefix + ''' update §r更新列表中的区域文件，这将重启服务器
§a【参数说明】§r
§6[d]§r: 维度序号，主世界为0，下界为-1，末地为1
§6[x] [z]§r: 区域文件坐标，如r.-3.1.mca的区域文件坐标为x=-3 z=1
'''

regionList = []
historyList = []
queue = Queue.Queue()


def printMessage(server, info, msg, isBroadcast=False):
	for line in msg.splitlines():
		if info.isPlayer:
			if isBroadcast:
				server.say(line)
			else:
				server.tell(info.player, line)
		else:
			print(line)


def printLog(msg):
	if not os.path.exists(LogFileFolder):
		os.makedirs(LogFileFolder)
	if not os.path.exists(LogFilePath):
		with open(LogFilePath, 'w') as f:
			pass
	with open(LogFilePath, 'a') as logfile:
		logfile.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + ': ' + msg + '\n')


def minecraft_json_parser(text):
	text = re.sub(r'^.* has the following entity data: ', '', text)  # yeet prefix
	text = re.sub(r'(?<=\d)[a-zA-Z](?=\D)', '', text)  # remove letter after number
	text = re.sub(r'([a-zA-Z.]+)(?=:)', '"\g<1>"', text)  # add quotation marks to all
	list_a = re.split(r'""[a-zA-Z.]+":', text)  # add quotation marks to all
	list_b = re.findall(r'""[a-zA-Z.]+":', text)  # add quotation marks to all
	result = list_a[0]
	for i in range(len(list_b)):
		result += list_b[i].replace('""', '"').replace('":', ':') + list_a[i + 1]
	return json.loads(result)


def getPlayerInfo(server, name, path=''):
	if len(path) >= 1 and not path.startswith(' '):
		path = ' ' + path
	server.execute('data get entity {}{}'.format(name, path))
	global queue
	for i in range(1000):
		if not queue.empty():
			break
		time.sleep(0.01)
	return queue.get()


def getRegionFilePath(regionfile):
	path = ''
	path += DimensionRegionFolder[regionfile[0]]
	path += 'r.' + str(regionfile[1]) + '.' + str(regionfile[2]) + '.mca'
	return path


def addRegion(server, info, regionFile):
	global regionList
	if regionFile in regionList:
		printMessage(server, info, '列表中已存在该区域文件')
	else:
		regionList.append(regionFile)
		printMessage(server, info, '区域文件§6' + getRegionFilePath(regionFile) + '§r已添加')


def delRegion(server, info, regionFile):
	global regionList
	if regionFile not in regionList:
		printMessage(server, info, '列表中不存在该区域文件')
	else:
		regionList.remove(regionFile)
		printMessage(server, info, '区域文件§6' + getRegionFilePath(regionFile) + '§r已删除')


def deleteRegionList(server, info):
	global regionList
	regionList = []
	printMessage(server, info, '区域文件列表已清空')


def getRegionFileFromPlayer(server, player):
	playerInfo = getPlayerInfo(server, player)
	d = playerInfo['Dimension']
	x = int(playerInfo['Pos'][0]) // 512
	z = int(playerInfo['Pos'][2]) // 512
	return d, x, z


def getRegionFileFromParameter(p):
	d = int(p[0])
	x = int(p[1])
	z = int(p[2])
	flag = d in [-1, 0, 1]
	return (d, x, z), flag


def printRegionList(server, info):
	global regionList
	printMessage(server, info, '更新列表中共有' + str(len(regionList)) + '个待更新的区域文件')
	for region in regionList:
		printMessage(server, info, '§6' + getRegionFilePath(region) + '§r')


def printRegionHistory(server, info):
	global historyList
	printMessage(server, info, '上次尝试更新更新了' + str(len(historyList)) + '个区域文件')
	msg = {False: '失败', True: '成功'}
	for history in historyList:
		printMessage(server, info, '§6' + getRegionFilePath(history[0]) + '§r: ' + msg[history[1]])


def updateRegionFile(server, info):
	global regionList
	global historyList
	printRegionList(server, info)
	countdown = 5
	printMessage(server, info, '[' + PluginName + ']: ' + str(countdown) + '秒后重启服务器更新列表中的区域文件')
	for i in range(1, countdown):
		printMessage(server, info, '[' + PluginName + ']: 还有' + str(countdown - i) + '秒', isBroadcast=True)
		time.sleep(1)
	server.stop()
	time.sleep(10)
	if info.isPlayer:
		name = info.player
	else:
		name = '控制台'
	printLog(name + '更新了' + str(len(regionList)) + '个区域文件：')
	historyList = []
	for region in regionList:
		sourceFilePath = SourceWorldPath + getRegionFilePath(region)
		DestinationFilePath = DestinationWorldPath + DimensionRegionFolder[region[0]]
		flag = False
		if (os.path.isfile(sourceFilePath)):
			print('[' + PluginName + ']cp -f ' + sourceFilePath + ' ' + DestinationFilePath)
			os.system('cp -f ' + sourceFilePath + ' ' + DestinationFilePath)
			flag = True
		historyList.append((region, flag))
		msg = {False: '失败', True: '成功'}
		printLog(getRegionFilePath(region) + ': ' + msg[flag])
	regionList = []
	time.sleep(5)
	server.start()


def onServerInfo(server, info):
	if ' has the following entity data: ' in info.content:
		player_info = minecraft_json_parser(info.content)
		global queue
		queue.put(player_info)
	content = info.content
	if not info.isPlayer and content.endswith('<--[HERE]'):
		content = content.replace('<--[HERE]', '')

	command = content.split()
	if len(command) == 0 or command[0] != Prefix:
		return
	del command[0]

	if len(command) == 0:
		printMessage(server, info, HelpMessage)
		return

	cmdLen = len(command)
	# add
	if cmdLen == 1 and command[0] == 'add' and info.isPlayer:
		addRegion(server, info, getRegionFileFromPlayer(server, info.player))
	# add [d] [x] [y]
	elif cmdLen == 4 and command[0] == 'add':
		ret = getRegionFileFromParameter(command[1:])
		if (ret[1]):
			addRegion(server, info, ret[0])
		else:
			printMessage(server, info, '区域文件坐标错误！')
	# delete-all
	elif cmdLen == 1 and command[0] == 'delete-all':
		deleteRegionList(server, info)
	# del
	elif cmdLen == 1 and command[0] == 'del' and info.isPlayer:
		delRegion(server, info, getRegionFileFromPlayer(server, info.player))
	# del [d] [x] [y]
	elif cmdLen == 4 and command[0] == 'del':
		ret = getRegionFileFromParameter(command[1:])
		if (ret[1]):
			delRegion(server, info, ret[0])
		else:
			printMessage(server, info, '区域文件坐标错误！')
	# list
	elif cmdLen == 1 and command[0] == 'list':
		printRegionList(server, info)
	# history
	elif cmdLen == 1 and command[0] == 'history':
		printRegionHistory(server, info)
	# update
	elif cmdLen == 1 and command[0] == 'update':
		updateRegionFile(server, info)
	# else
	else:
		printMessage(server, info, '参数错误！请输入§7' + Prefix + '§r以获取插件帮助')


def on_info(server, info):
	info2 = copy.deepcopy(info)
	info2.isPlayer = info2.is_player
	onServerInfo(server, info2)


def on_load(server, old):
	server.add_help_message(Prefix, '从指定存档处更新region文件至本服')
