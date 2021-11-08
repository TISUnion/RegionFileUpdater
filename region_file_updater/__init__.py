# -*- coding: utf-8 -*-
import os
import shutil
import time
import json
from typing import Dict, Iterable, List, Tuple, Optional, Union

from mcdreforged.api.all import *

PLUGIN_METADATA = ServerInterface.get_instance().as_plugin_server_interface().get_self_metadata()
PROTECTED_REGION_FILE_NAME = 'protected-regions.json'


class Config(Serializable):
	enabled: bool = True,
	source_world_directory: str = './qb_multi/slot1/world'
	destination_world_directory: str = './server/world'
	dimension_region_folder: Dict[str, Union[str, List[str]]] = {
		'-1': 'DIM-1/region',
		'0': 'region',
		'1': 'DIM1/region'
	}


config: Optional[Config] = None
Prefix = '!!region'
PluginName = PLUGIN_METADATA.name
LogFilePath = os.path.join('logs', '{}.log'.format(PluginName))
HelpMessage = '''
------MCDR {1} v{2}------
一个从指定位置拉取region文件至本服存档的插件，如生存服qb槽位->本服 
§a【指令说明】§r
§7{0} §r显示帮助信息
§7{0} add §r添加玩家所在位置的区域文件
§7{0} add §6[x] [z] [d] §r添加指定的区域文件
§7{0} del §r删除玩家所在位置的区域文件
§7{0} del §6[d] [x] [z] [d] §r删除指定的区域文件
§7{0} del-all §r删除所有区域文件
§7{0} protect §r将玩家所在位置的区域文件设为保护状态
§7{0} protect §6[x] [z] [d] §r保护指定的区域文件
§7{0} deprotect §r取消保护玩家所在位置的区域文件
§7{0} deprotect §6[x] [z] [d] §r取消保护指定的区域文件
§7{0} deprotect-all §r取消保护所有的区域文件
§7{0} list §r列出待更新的区域文件
§7{0} list-protect §r列出受保护的区域文件
§7{0} history §r输出上一次update的结果
§7{0} update §r更新列表中的区域文件，这将重启服务器
§7{0} reload §r重新载入配置文件
§a【参数说明】§r
§6[x] [z]§r: 区域文件坐标，如r.-3.1.mca的区域文件坐标为x=-3 z=1
§6[d]§r: 维度序号，主世界为0，下界为-1，末地为1
'''.strip().format(Prefix, PLUGIN_METADATA.name, PLUGIN_METADATA.version)

regionList = []  # type: List[Region]
protectedRegionList = []  # type: List[Region]
historyList = []  # type: List[Tuple[Region, bool]]
server_inst: PluginServerInterface


class Region(Serializable):
	def __init__(self, x: int, z: int, dim: int):
		self.x = x
		self.z = z
		self.dim = dim

	def to_file_name(self):
		return 'r.{}.{}.mca'.format(self.x, self.z)

	def to_file_list(self):
		file_list = []
		folders = config.dimension_region_folder[str(self.dim)]
		if isinstance(folders, str):
			file_list.append(os.path.join(folders, self.to_file_name()))
		elif isinstance(folders, Iterable):
			for folder in folders:
				file_list.append(os.path.join(folder, self.to_file_name()))
		else:
			pass
		return file_list

	def __eq__(self, other):
		if not isinstance(other, type(self)):
			return False
		return self.x == other.x and self.z == other.z and self.dim == other.dim

	def __repr__(self):
		return 'Region[x={}, z={}, dim={}]'.format(self.x, self.z, self.dim)


def print_log(server: ServerInterface, msg: str):
	server.logger.info(msg)
	with open(LogFilePath, 'a') as logfile:
		logfile.write(time.strftime('%Y-%m-%d %H:%M:%S',
									time.localtime(time.time())) + ': ' + msg + '\n')


def add_region(source: CommandSource, region: Region):
	if region in regionList:
		source.reply('列表中已存在该区域文件')
	elif region not in protectedRegionList:
		regionList.append(region)
		source.reply('区域文件§6{}§r已添加'.format(region))
	else:
		source.reply('该区域已设保护')


def delete_region(source: CommandSource, region: Region):
	if region not in regionList:
		source.reply('列表中不存在该区域文件')
	else:
		regionList.remove(region)
		source.reply('区域文件§6{}§r已删除'.format(region))


def clean_region_list(source):
	regionList.clear()
	source.reply('区域文件列表已清空')


def protect_region(source: CommandSource, region: Region):
	if region in protectedRegionList:
		source.reply('该区域文件已设保护')
	elif region in regionList:
		regionList.remove(region)
		protectedRegionList.append(region)
		source.reply('区域文件§6{}§r已从列表移除并设保护'.format(region))
		save_protected_region_file()
	else:
		protectedRegionList.append(region)
		source.reply('区域文件§6{}§r已设保护'.format(region))
		save_protected_region_file()


def deprotect_region(source: CommandSource, region: Region):
	if region in protectedRegionList:
		protectedRegionList.remove(region)
		source.reply('区域文件§6{}§r已取消保护'.format(region))
		save_protected_region_file()
	else:
		source.reply('该区域文件未被保护')


def deprotect_all_regions(source):
	protectedRegionList.clear()
	source.reply('所有受保护区域文件已去保护')
	save_protected_region_file()


def save_protected_region_file():
	file_path = os.path.join(
		config.destination_world_directory, PROTECTED_REGION_FILE_NAME)
	with open(file_path, 'w', encoding='utf8') as file:
		json.dump(serialize(protectedRegionList), file)


def load_protected_region_file():
	global protectedRegionList
	file_path = os.path.join(
		config.destination_world_directory, PROTECTED_REGION_FILE_NAME)
	if os.path.isfile(file_path):
		with open(file_path, 'r', encoding='utf8') as file:
			try:
				data = json.load(file)
				protectedRegionList = deserialize(data, List[Region])
			except Exception as e:
				server_inst.logger.error(
					'Fail to load protected regions from {}: {}'.format(file_path, e))
				protectedRegionList = []


def get_region_from_source(source: PlayerCommandSource) -> Region:
	api = source.get_server().get_plugin_instance('minecraft_data_api')
	coord = api.get_player_coordinate(source.player)
	dim = api.get_player_dimension(source.player)
	return Region(int(coord.x) // 512, int(coord.z) // 512, dim)


@new_thread(PLUGIN_METADATA.name)
def add_region_from_player(source: CommandSource):
	if isinstance(source, PlayerCommandSource):
		add_region(source, get_region_from_source(source))
	else:
		source.reply('该指令仅支持玩家执行')


@new_thread(PLUGIN_METADATA.name)
def delete_region_from_player(source: CommandSource):
	if isinstance(source, PlayerCommandSource):
		delete_region(source, get_region_from_source(source))
	else:
		source.reply('该指令仅支持玩家执行')


@new_thread(PLUGIN_METADATA.name)
def protect_region_from_player(source: CommandSource):
	if isinstance(source, PlayerCommandSource):
		protect_region(source, get_region_from_source(source))
	else:
		source.reply('该指令仅支持玩家执行')


@new_thread(PLUGIN_METADATA.name)
def deprotect_region_from_player(source: CommandSource):
	if isinstance(source, PlayerCommandSource):
		deprotect_region(source, get_region_from_source(source))
	else:
		source.reply('该指令仅支持玩家执行')


def show_region_list(source: CommandSource):
	source.reply('更新列表中共有{}个待更新的区域文件'.format(len(regionList)))
	for region in regionList:
		source.reply('- §6{}§r'.format(region))


def show_history(source: CommandSource):
	source.reply('上次尝试更新更新了{}个区域文件'.format(len(historyList)))
	msg = {False: '失败', True: '成功'}
	for region, flag in historyList:
		source.reply('§6{}§r: {}'.format(region, msg[flag]))


def show_protected_regions(source: CommandSource):
	source.reply('已保护区域列表中共有{}个受保护的区域文件'.format(len(protectedRegionList)))
	for region in protectedRegionList:
		source.reply('- §6{}§r'.format(region))


@new_thread(PLUGIN_METADATA.name)
def region_update(source: CommandSource):
	show_region_list(source)
	countdown = 5
	source.reply('[{}]: {}秒后重启服务器更新列表中的区域文件'.format(
		PluginName, countdown), isBroadcast=True)
	for i in range(1, countdown):
		source.reply('[{}]: 还有{}秒'.format(
			PluginName, countdown - i), isBroadcast=True)
		time.sleep(1)

	source.get_server().stop()
	source.get_server().wait_for_start()

	print_log(source.get_server(), '{} 更新了 {} 个区域文件：'.format(
		source, len(regionList)))
	historyList.clear()
	for region in regionList:
		for region_file in region.to_file_list():
			source_dir = os.path.join(
				config.source_world_directory, region_file)
			destination = os.path.join(
				config.destination_world_directory, region_file)
			try:
				source.get_server().logger.info('- "{}" -> "{}"'.format(source_dir, destination))
				shutil.copyfile(source_dir, destination)
			except Exception as e:
				msg = '失败，错误信息：{}'.format(str(e))
				flag = False
			else:
				msg = '成功'
				flag = True
			historyList.append((region, flag))
			print_log(source.get_server(), '  {}: {}'.format(region, msg))

	regionList.clear()
	time.sleep(1)
	source.get_server().start()


def on_load(server: PluginServerInterface, old):
	try:
		global historyList, regionList, protectedRegionList
		historyList = old.historyList
		regionList = old.regionList
		protectedRegionList = old.protectedRegionList
	except AttributeError:
		pass

	global server_inst
	server_inst = server
	load_config(None)
	register_commands(server)
	server.register_help_message(Prefix, '从指定存档处更新region文件至本服')


def load_config(source: Optional[CommandSource]):
	global config, server_inst
	config_file_path = os.path.join(
		'config', '{}.json'.format(PLUGIN_METADATA.id))
	config = server_inst.load_config_simple(
		config_file_path, in_data_folder=False, source_to_reply=source, echo_in_console=False, target_class=Config)


def reload_config(source: CommandSource):
	source.reply('重载配置文件中')
	load_config(source)


def register_commands(server: PluginServerInterface):
	def get_region_parm_node(callback):
		return Integer('x').then(Integer('z').then(Integer('dim').in_range(-1, 1).runs(callback)))

	server.register_command(
		Literal(Prefix).
		runs(lambda src: src.reply(HelpMessage)).
		on_error(UnknownArgument, lambda src: src.reply('参数错误！请输入§7{}§r以获取插件帮助'.format(Prefix)), handled=True).
		then(
			Literal('add').runs(add_region_from_player).
			then(get_region_parm_node(lambda src, ctx: add_region(
				src, Region(ctx['x'], ctx['z'], ctx['dim']))))
		).
		then(
			Literal('del').runs(delete_region_from_player).
			then(get_region_parm_node(lambda src, ctx: delete_region(
				src, Region(ctx['x'], ctx['z'], ctx['dim']))))
		).
		then(Literal('del-all').runs(clean_region_list)).
		then(
			Literal('protect').runs(protect_region_from_player).
			then(get_region_parm_node(lambda src, ctx: protect_region(src, Region(ctx['x'], ctx['z'], ctx['dim']))))).
		then(
			Literal('deprotect').runs(deprotect_region_from_player).
			then(get_region_parm_node(lambda src, ctx: deprotect_region(src, Region(ctx['x'], ctx['z'], ctx['dim']))))).
		then(Literal('deprotect-all').runs(deprotect_all_regions)).
		then(Literal('list').runs(show_region_list)).
		then(Literal('list-protect').runs(show_protected_regions)).
		then(Literal('history').runs(show_history)).
		then(
			Literal('update').
			requires(lambda: config.enabled).
			on_error(RequirementNotMet, lambda src: src.reply('{}未启用！请在配置文件中开启'.format(PLUGIN_METADATA.name)), handled=True).
			runs(region_update)
		).
		then(Literal('reload').runs(reload_config))
	)
