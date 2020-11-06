#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import itertools
import json
import os
import re
from base64 import b64decode
from pathlib import Path
from threading import Thread

import pyperclip
import requests
import yaml

path = Path.home() / '.config/V2Ray-Manager'
configPath = path / 'Config.yaml'
v2rayPath = path / 'V2Ray-Config.json'

path.mkdir(parents=True, exist_ok=True)
configPath.touch()
with configPath.open() as configStream:
    config = yaml.safe_load(configStream)
if not config:
    config = {
        'run-in-front': False,
        'use-sudo': False,
        'v2ray-command': 'v2ray',
        'current-connection': None,
        'imported': [],
        'subscriptions': {},
        'config': {
            'routing': {
                'rules': [],
                '_category-ads-all': {}
            }
        },
    }
with v2rayPath.open() as v2rayStream:
    v2ray = json.load(v2rayStream)

subscriptions = config['subscriptions']
imported = config['imported']
outBounds = v2ray['outbounds']

connections = []

vmess = {}
freedom = {}
vmessIndex = 0
freedomIndex = 0
for index1, out1 in enumerate(outBounds):
    outProtocol = out1['protocol']
    if outProtocol == 'vmess':
        vmess = out1
        vmessIndex = index1
    elif outProtocol == 'freedom':
        freedom = out1
        freedomIndex = index1

gfwDomain = []
gfwIp = []
cnDomain = []
cnIp = []
for rule2 in v2ray['routing']['rules']:
    outboundTag = rule2['outboundTag']
    if outboundTag == vmess['tag']:
        if 'domain' in rule2:
            gfwDomain = rule2['domain']
        elif 'ip' in rule2:
            gfwIp = rule2['ip']
    elif outboundTag == freedom['tag']:
        if 'domain' in rule2:
            cnDomain = rule2['domain']
        elif 'ip' in rule2:
            cnIp = rule2['ip']

dnsGfw = []
dnsCn = []
if 'dns' in v2ray and 'servers' in v2ray['dns']:
    for server1 in v2ray['dns']['servers']:
        if type(server1) == dict:
            dnsDomains = server1['domains']
            if 'geosite:google' in dnsDomains:
                dnsGfw = dnsDomains
            elif 'geosite:cn' in dnsDomains:
                dnsCn = dnsDomains

mainVnext = vmess['settings']['vnext'][0]
mainUser = mainVnext['users'][0]
streamSettings = vmess['streamSettings']


def updateConnections(doPrint=False):
    global connections
    connections = []
    echo = []
    count = itertools.count(1)
    if doPrint:
        echo.append('\033[32m{}\033[0m\n'.format('imported'))
    for connection1 in imported:
        connections.append(connection1)
        if doPrint:
            echo.append('\033[34m{}\033[0m\t{}\t\t{}\n'.format(next(count), connection1['ps'], connection1['add']))
    for url1, connections1 in subscriptions.items():
        if doPrint:
            echo.append('\033[32m{}\033[0m\n'.format(url1))
        for connection3 in connections1:
            connections.append(connection3)
            if doPrint:
                echo.append('\033[34m{}\033[0m\t{}\t\t{}\n'.format(next(count), connection3['ps'], connection3['add']))
    if doPrint:
        os.system('echo "{}" | less -r'.format(''.join(echo)))  # 我不知道怎么正确地通过两个 subprocess.PIPE 传递输入


def getConnection(string):
    if not string.startswith('vmess://'):
        return None
    try:
        connection = json.loads(b64decode(string.replace('vmess://', '')))
        if 'v' in connection and connection['v'] != '2':
            print('不支持 version {}'.format(connection['v']))
            return None
        return {
            'sorted': False,
            **connection,
        }
    except Exception as e:
        print(f'{type(e).__name__}: {e}')
        return None


def addImport(connection):
    connection = getConnection(connection)
    if connection:
        imported.append(connection)


def updateSubscriptions(url):
    for _ in range(3):
        try:
            response = requests.get(url, timeout=10)
            connections3 = b64decode(response.text).decode()
            break
        except Exception as e:
            print(f'{type(e).__name__}: {e}')
            continue
    else:
        print(f'更新失败: {url}')
        return
    subscriptions1 = []
    for connection6 in connections3.splitlines():
        connection6 = getConnection(connection6)
        if connection6:
            subscriptions1.append(connection6)
    if subscriptions1:
        subscriptions[url] = subscriptions1
        print(f'已更新: {url}')
    else:
        print(f'返回空配置列表, 未更改: {url}')


def addAddress(address, target, rules):
    if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', address):
        if not rules:
            return
        if target == 'gfw':
            if address in gfwIp:
                print('{} 已经存在于 GFW IPs'.format(address))
            else:
                gfwIp.append(address)
        else:
            if address in cnIp:
                print('{} 已经存在于 CN IPs'.format(address))
            else:
                cnIp.append(address)
    else:
        if address.startswith('http'):
            address = re.sub(r'https?://', '', address)
        domainItem = 'domain:{}'.format(address)
        if target == 'gfw':
            if rules:
                if gfwDomain:
                    if domainItem in gfwDomain:
                        print('{} 已经存在于 GFW domains'.format(domainItem))
                    else:
                        gfwDomain.append(domainItem)
            if dnsGfw:
                if domainItem in dnsGfw:
                    print('{} 已经存在于 GFW DNS domains'.format(domainItem))
                else:
                    dnsGfw.append(domainItem)
        else:
            if rules:
                if cnDomain:
                    if domainItem in cnDomain:
                        print('{} 已经存在于 CN domains'.format(domainItem))
                    else:
                        cnDomain.append(domainItem)
            if dnsCn:
                if domainItem in dnsCn:
                    print('{} 已经存在于 CN DNS domains'.format(domainItem))
                else:
                    dnsCn.append(domainItem)


def addAddressFromInputStr():
    if inputStr.startswith('gfw'):
        target = 'gfw'
    else:
        target = 'cn'
    address = inputStr.replace('{} '.format(target), '')
    addAddress(address, target, True)


def setConnection():
    if not connections:
        updateConnections()
    connection2 = connections[int(inputStr) - 1]
    mainVnext['address'] = connection2['add']
    mainVnext['port'] = int(connection2['port'])
    mainUser['id'] = connection2['id']
    mainUser['alterId'] = int(connection2['aid'])
    streamSettings['network'] = connection2['net']

    def setHeader(prefix):
        settings1 = f'{prefix}Settings'
        if settings1 not in streamSettings:
            streamSettings[settings1] = {'header': {}}
        elif 'header' not in streamSettings[settings1]:
            streamSettings[settings1]['header'] = {}
        streamSettings[settings1]['header']['type'] = connection2['type']

    if streamSettings['network'] == 'ws':
        if 'wsSettings' not in streamSettings:
            streamSettings['wsSettings'] = {'headers': {}}
        elif 'headers' not in streamSettings['wsSettings']:
            streamSettings['wsSettings']['headers'] = {}
        streamSettings['wsSettings']['headers']['Host'] = connection2['host'] if 'host' in connection2 else ''
        streamSettings['wsSettings']['path'] = connection2['path'] if 'path' in connection2 else ''
    else:
        # tcp, kcp, quic
        setHeader(streamSettings['network'])
    streamSettings['security'] = connection2['tls'] if 'tls' in connection2 else ''
    if config['current-connection']:
        if 'dns' in v2ray and 'servers' in v2ray['dns']:
            for server2 in v2ray['dns']['servers']:
                if type(server2) == dict and 'domains' in server2:
                    domainItem1 = f"domain:{config['current-connection']['add']}"
                    if domainItem1 in server2['domains']:
                        server2['domains'].remove(domainItem1)
    addAddress(mainVnext['address'], 'cn', False)
    config['current-connection'] = connection2


def sortConnectionKeys(connection):
    if 'sorted' in connection:
        connection6 = {
            'ps': connection['ps'],
            'add': connection['add'],
            'port': connection['port'],
            'id': connection['id'],
            'aid': connection['aid'] if 'aid' in connection else '0',
            'net': connection['net'],
            'type': connection['type'],
        }
        if 'host' in connection:
            connection6['host'] = connection['host']
        if 'path' in connection:
            connection6['path'] = connection['path']
        if 'tls' in connection:
            connection6['tls'] = connection['tls']
        return connection6
    return connection


def saveConfig():
    for i1, connection6 in enumerate(imported):
        imported[i1] = sortConnectionKeys(connection6)
    for url2 in subscriptions.keys():
        for i2, connection7 in enumerate(subscriptions[url2]):
            subscriptions[url2][i2] = sortConnectionKeys(connection7)
    with configPath.open('w') as configStream1:
        yaml.safe_dump(config, configStream1, indent=4, allow_unicode=True, sort_keys=False)
    with v2rayPath.open('w') as v2rayStream1:
        json.dump(v2ray, v2rayStream1, indent=4)


def generateAndRestartAndExit():
    saveConfig()
    if config['use-sudo']:
        os.system('sudo whoami')
        os.system('sudo killall v2ray > /dev/null 2>&1')
        if config['run-in-front']:
            os.system(f"sudo {config['v2ray-command']} -config {v2rayPath.resolve()}")
        else:
            os.system(f"nohup sudo {config['v2ray-command']} -config {v2rayPath.resolve()} > /dev/null 2>&1 &")
    else:
        os.system('killall v2ray > /dev/null 2>&1')
        if config['run-in-front']:
            os.system(f"{config['v2ray-command']} -config {v2rayPath.resolve()}")
        else:
            os.system(f"nohup {config['v2ray-command']} -config {v2rayPath.resolve()} > /dev/null 2>&1 &")
    exit()


first = True
while True:
    if first:
        first = False
        print('功能: 需要键入的内容\n'
              '从剪贴板添加 vmess 连接配置: c\n'
              '添加订阅地址: <订阅地址>\n'
              '更新订阅: u\n'
              '查看配置列表: p\n'
              '选择要连接的配置: <序号>\n'
              '保存配置并运行: (回车)\n'
              '保存配置并退出: q\n'
              '向黑白名单列表(rules与dns)添加域名或 IP: (形如 "gfw google.com" 或 "cn 223.5.5.5")\n'
              '切换默认出站(freedom/vmess): d\n'
              '切换前台运行 V2Ray: f\n'
              '切换使用 sudo 运行 V2Ray: s\n'
              '移除所有规则并备份, 或从备份中恢复: r\n'
              '移除拦截广告的规则并备份, 或从备份中恢复: a')
    print(f"\n默认出站: \33[33m{outBounds[0]['protocol']}\33[0m\n" +
          "要连接的配置: \33[33m{}\33[0m\n".format(
              f"{config['current-connection']['ps']}: {config['current-connection']['add']}"
              if config['current-connection'] else ''
          ) +
          f"在前台运行 V2Ray: \33[33m{config['run-in-front']}\33[0m\n"
          f"使用 sudo 运行 V2Ray: \33[33m{config['use-sudo']}\33[0m")
    inputStr = input().strip()
    if inputStr == '':
        generateAndRestartAndExit()
    elif inputStr == 'c':
        connections2 = re.split(r'\n|\\n', pyperclip.paste())
        for connection5 in connections2:
            addImport(connection5)
    elif inputStr == 'u':
        threads1 = []
        for url4, connection4 in subscriptions.items():
            thread1 = Thread(target=updateSubscriptions, args=(url4,))
            threads1.append(thread1)
            thread1.start()
        for thread2 in threads1:
            thread2.join()
    elif inputStr == 'p':
        updateConnections(True)
    elif inputStr == 'q':
        saveConfig()
        exit()
    elif inputStr == 'd':
        if outBounds[0]['protocol'] == 'vmess':
            outBounds[0], outBounds[freedomIndex] = outBounds[freedomIndex], outBounds[0]
            vmessIndex, freedomIndex = freedomIndex, 0
        else:
            outBounds[0], outBounds[vmessIndex] = outBounds[vmessIndex], outBounds[0]
            vmessIndex, freedomIndex = 0, vmessIndex
    elif inputStr == 'f':
        config['run-in-front'] = not config['run-in-front']
    elif inputStr == 's':
        config['use-sudo'] = not config['use-sudo']
    elif inputStr == 'r':
        if v2ray['routing']['rules']:
            config['config']['routing']['rules'] = v2ray['routing']['rules']
            v2ray['routing']['rules'] = []
        else:
            v2ray['routing']['rules'] = config['config']['routing']['rules']
    elif inputStr == 'a':
        if not v2ray['routing']['rules']:
            continue
        ok1 = False
        ruleIndex2 = -1
        for ruleIndex1, rule1 in enumerate(v2ray['routing']['rules']):
            if 'domain' in rule1 and 'geosite:category-ads-all' in rule1['domain']:
                ok1 = True
                ruleIndex2 = ruleIndex1
                break
        if ok1:
            config['config']['routing']['_category-ads-all'] = v2ray['routing']['rules'][ruleIndex2]
            v2ray['routing']['rules'].pop(ruleIndex2)
        else:
            v2ray['routing']['rules'].append(config['config']['routing']['_category-ads-all'])
    elif inputStr.isdigit():
        # 选择要连接的配置
        setConnection()
    elif ' ' in inputStr:
        # 向列表添加域名或 IP
        addAddressFromInputStr()
    else:
        # 订阅地址
        if not inputStr.startswith('http'):
            inputStr = 'http://' + inputStr
        updateSubscriptions(inputStr)
