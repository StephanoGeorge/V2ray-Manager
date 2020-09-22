#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import itertools
import json
import os
import re
from base64 import b64decode
from pathlib import Path

import requests
import yaml

path = Path.home() / '.config/V2ray-Manager-Denis'
configPath = path / 'Config.yaml'
v2rayPath = path / 'V2ray-Config.json'

path.mkdir(parents=True, exist_ok=True)
configPath.touch()
with configPath.open() as configStream:
    config = yaml.safe_load(configStream)
if not config:
    config = {'run-in-front': False, 'use-sudo': False, 'imported': [], 'subscriptions': {},
              'config': {
                  'routing': {
                      'rules': [],
                      '_category-ads-all': {}
                  }
              }}
with v2rayPath.open() as v2rayStream:
    v2ray = json.load(v2rayStream)

subscriptions = config['subscriptions']
imported = config['imported']
outBounds = v2ray['outbounds']


def sortConnectionKeys(connection):
    if 'sorted' in connection:
        connection6 = {
            'ps': connection['ps'],
            'add': connection['add'],
            'port': connection['port'],
            'id': connection['id'],
            'aid': connection['aid'],
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
    v2rayPathResolved = v2rayPath.resolve()
    if config['use-sudo']:
        os.system('sudo whoami')
        os.system('sudo killall v2ray > /dev/null 2>&1')
        if config['run-in-front']:
            os.system('sudo v2ray -config {}'.format(v2rayPathResolved))
        else:
            os.system('nohup sudo v2ray -config {} > /dev/null 2>&1 &'.format(v2rayPathResolved))
    else:
        os.system('killall v2ray > /dev/null 2>&1')
        if config['run-in-front']:
            os.system('v2ray -config {}'.format(v2rayPathResolved))
        else:
            os.system('nohup v2ray -config {} > /dev/null 2>&1 &'.format(v2rayPathResolved))
    exit()


def updateSubscriptions(url):
    print(f'正在获取 {url}')
    try:
        response = requests.get(url, timeout=20)
        connections3 = b64decode(response.text).decode()
    except Exception as e:
        print(e)
        return
    if 'vmess://' not in connections3:
        print('返回空配置列表, 未更改')
        return
    subscriptions[url] = []
    for connection6 in connections3.splitlines():
        if not connection6:
            continue
        connection6 = getConnection(connection6)
        if not connection6:
            continue
        subscriptions[url].append(connection6)


def getConnection(string):
    try:
        connection = json.loads(b64decode(string.replace('vmess://', '')))
        if connection['v'] != '2':
            print('不支持 version {}'.format(connection['v']))
            return
        return {
            'sorted': False,
            **connection,
        }
    except Exception as e:
        print(e)
        return


def isUrl(string):
    return string.startswith('http')


def removeSchema(string):
    return re.sub(r'https?://', '', string)


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
wsSettings = streamSettings['wsSettings']


def addAddressFromInputStr():
    if inputStr.startswith('gfw'):
        target = 'gfw'
    else:
        target = 'cn'
    address = inputStr.replace('{} '.format(target), '')
    addAddress(address, target)


def addAddress(address, target):
    if not re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', address):
        if isUrl(address):
            address = removeSchema(address)
        domainItem = 'domain:{}'.format(address)
        if target == 'gfw':
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
    else:
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


connections = []
first = True


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


while True:
    if first:
        first = False
        print('键入: vmess 连接配置, 或订阅地址, 或 u 以更新订阅, 或要连接的配置序号,\n'
              '      或 "gfw google.com"/"cn 223.5.5.5" 向黑白名单列表添加域名或 IP,\n'
              '      或 d 以切换默认出站, 或 f 以切换前台运行 V2ray, 或 s 以切换使用 sudo 运行 V2ray\n'
              '      或 r 以移除所有规则并备份或从备份中恢复, 或 a 以移除拦截广告的规则并备份或或从备份中恢复\n'
              '      或 p 以查看配置列表, 或回车以保存配置并运行, 或 q 以保存配置并退出')
    print()
    print('默认出站: \33[33m{}\33[0m\n'
          '要连接的配置: \33[33m{}\33[0m\n'
          '在前台运行 V2ray: \33[33m{}\33[0m\n'
          '使用 sudo 运行 V2ray: \33[33m{}\33[0m'
          .format(outBounds[0]['protocol'], mainVnext['address'], config['run-in-front'], config['use-sudo']))
    inputStr = input().strip()
    if inputStr == '':
        generateAndRestartAndExit()
    elif inputStr == 'f':
        config['run-in-front'] = not config['run-in-front']
    elif inputStr == 's':
        config['use-sudo'] = not config['use-sudo']
    elif inputStr == 'd':
        if outBounds[0]['protocol'] == 'vmess':
            outBounds[0], outBounds[freedomIndex] = outBounds[freedomIndex], outBounds[0]
        else:
            outBounds[0], outBounds[vmessIndex] = outBounds[vmessIndex], outBounds[0]
    elif inputStr == 'p':
        updateConnections(True)
    elif inputStr == 'u':
        for url4, connection4 in subscriptions.items():
            updateSubscriptions(url4)
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
    elif inputStr == 'q':
        saveConfig()
        exit()
    elif inputStr.isdigit():
        if not connections:
            updateConnections()
        # 要连接的配置序号
        connection2 = connections[int(inputStr) - 1]
        mainVnext['address'] = connection2['add']
        mainVnext['port'] = int(connection2['port'])
        mainUser['id'] = connection2['id']
        mainUser['alterId'] = int(connection2['aid'])
        streamSettings['network'] = connection2['net']
        streamSettings['tcpSettings']['header']['type'] = connection2['type']
        streamSettings['kcpSettings']['header']['type'] = connection2['type']
        streamSettings['quicSettings']['header']['type'] = connection2['type']
        wsSettings['headers']['Host'] = connection2['host'] if 'host' in connection2 else ''
        wsSettings['path'] = connection2['path'] if 'path' in connection2 else ''
        streamSettings['security'] = connection2['tls'] if 'tls' in connection2 else ''
        addAddress(mainVnext['address'], 'cn')
    elif inputStr.startswith('vmess://'):
        # 连接配置
        connections2 = re.split(r'\n|\\n', inputStr)
        for connection5 in connections2:
            if 'vmess://' not in connection5:
                continue
            connection5 = getConnection(connection5)
            if not connection5:
                continue
            imported.append(connection5)
    elif ' ' in inputStr:
        # 向列表添加域名或 IP
        addAddressFromInputStr()
    else:
        # 订阅地址
        if not isUrl(inputStr):
            inputStr = 'http://' + inputStr
        updateSubscriptions(inputStr)
