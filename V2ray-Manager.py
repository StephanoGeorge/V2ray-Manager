#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import itertools
import os
import re
from pathlib import Path
import requests
from base64 import b64decode
import json
import yaml

path = Path(__file__).resolve().parent
configPath = path / 'Config.yaml'
v2rayPath = path / 'V2ray-Config.json'

configPath.touch()
with configPath.open() as configStream:
    config = yaml.safe_load(configStream)
if config is None:
    config = {'runInFront': False, 'useSudo': False, 'imported': []}
with v2rayPath.open() as v2rayStream:
    v2ray = json.load(v2rayStream)

outBounds = v2ray['outbounds']


def saveConfig():
    with configPath.open('w') as configStreamI:
        yaml.safe_dump(config, configStreamI, indent=4, allow_unicode=True, sort_keys=False)
    with v2rayPath.open('w') as v2rayStreamI:
        json.dump(v2ray, v2rayStreamI, indent=4)


def generateAndRestartAndExit():
    saveConfig()
    if config['useSudo']:
        os.system('sudo whoami')
        os.system('sudo killall v2ray > /dev/null 2>&1')
        if config['runInFront']:
            os.system('sudo v2ray -config {}'.format(v2rayPath.resolve()))
        else:
            os.system('nohup sudo v2ray -config {} > /dev/null 2>&1 &'.format(v2rayPath.resolve()))
    else:
        os.system('killall v2ray > /dev/null 2>&1')
        if config['runInFront']:
            os.system('v2ray -config {}'.format(v2rayPath.resolve()))
        else:
            os.system('nohup v2ray -config {} > /dev/null 2>&1 &'.format(v2rayPath.resolve()))
    exit()


def updateSubscriptions(url):
    try:
        response = requests.get(url, timeout=20)
        connectsM = b64decode(response.text).decode()
    except requests.exceptions.BaseHTTPError and UnicodeEncodeError as e:
        print(e)
        return
    if 'vmess://' not in connectsM:
        print('{} 返回空配置列表, 未更改'.format(url))
        return
    config[url] = []
    for connectM in connectsM.splitlines():
        connectM = getConnect(connectM)
        config[url].append(connectM)


def getConnect(string):
    return json.loads(b64decode(string.replace('vmess://', '')))


def isUrl(string):
    return string.startswith('http')


def removeSchema(string):
    return re.sub(r'https?://', '', string)


vmess = {}
freedom = {}
vmessIndex = 0
freedomIndex = 0
for indexI, outI in enumerate(outBounds):
    outProtocol = outI['protocol']
    if outProtocol == 'vmess':
        vmess = outI
        vmessIndex = indexI
    elif outProtocol == 'freedom':
        freedom = outI
        freedomIndex = indexI
gfwDomain = []
gfwIp = []
cnDomain = []
cnIp = []
for rule in v2ray['routing']['rules']:
    outboundTag = rule['outboundTag']
    if outboundTag == vmess['tag']:
        if 'domain' in rule:
            gfwDomain = rule['domain']
        elif 'ip' in rule:
            gfwIp = rule['ip']
    elif outboundTag == freedom['tag']:
        if 'domain' in rule:
            cnDomain = rule['domain']
        elif 'ip' in rule:
            cnIp = rule['ip']
dnsGfw = []
dnsCn = []
if 'dns' in v2ray and 'servers' in v2ray['dns']:
    for serverNI in v2ray['dns']['servers']:
        if type(serverNI) == dict:
            dnsDomains = serverNI['domains']
            if 'geosite:google' in dnsDomains:
                dnsGfw = dnsDomains
            elif 'geosite:cn' in dnsDomains:
                dnsCn = dnsDomains
mainVnext = vmess['settings']['vnext'][0]
mainUser = mainVnext['users'][0]
streamSettings = vmess['streamSettings']
wsSettings = streamSettings['wsSettings']


def addAddr():
    if inputStr.startswith('gfw'):
        target = 'gfw'
    else:
        target = 'cn'
    addr = inputStr.replace('{} '.format(target), '')
    if re.search(r' [0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', inputStr) is None:
        if isUrl(addr):
            addr = removeSchema(addr)
        domainItem = 'domain:{}'.format(addr)
        if target == 'gfw':
            if len(gfwDomain) != 0:
                if domainItem in gfwDomain:
                    print('{} 已经存在于 GFW domains'.format(domainItem))
                else:
                    gfwDomain.append(domainItem)
            if len(dnsGfw) != 0:
                if domainItem in dnsGfw:
                    print('{} 已经存在于 GFW DNS domains'.format(domainItem))
                else:
                    dnsGfw.append(domainItem)
        else:
            if len(cnDomain) != 0:
                if domainItem in cnDomain:
                    print('{} 已经存在于 CN domains'.format(domainItem))
                else:
                    cnDomain.append(domainItem)
            if len(dnsCn) != 0:
                if domainItem in dnsCn:
                    print('{} 已经存在于 CN DNS domains'.format(domainItem))
                else:
                    dnsCn.append(domainItem)
    else:
        if target == 'gfw':
            if addr in gfwIp:
                print('{} 已经存在于 GFW IPs'.format(addr))
            else:
                gfwIp.append(addr)
        else:
            if addr in cnIp:
                print('{} 已经存在于 CN IPs'.format(addr))
            else:
                cnIp.append(addr)


while True:
    connects = []
    if config is not None:
        count = itertools.count(1)
        for key, value in config.items():
            if key == 'imported' or isUrl(key):
                print('\033[32m{}\033[0m'.format(key))
                for connect in value:
                    connects.append(connect)
                    print('\033[34m{}\033[0m\t{}\t\t{}'.format(next(count), connect['ps'], connect['add']))
    print('默认出站: \033[33m{}\033[0m\n要连接的配置: \033[33m{}\033[0m\n在前台运行 V2ray: \033[33m{}\033[0m\n'
          '使用 sudo 运行 V2ray: \033[33m{}\033[0m\n'
          .format(outBounds[0]['protocol'], mainVnext['address'], config['runInFront'], config['useSudo']))
    inputStr = input('键入: vmess 连接配置, 或订阅地址, 或 u 以更新订阅, 或要连接的配置序号,\n'
                     '      或 "gfw google.com"/"cn 223.5.5.5" 向黑白名单列表添加域名或 IP,\n'
                     '      或 d 以切换默认出站, 或 f 以切换前台运行 V2ray, 或 s 以切换使用 sudo 运行 V2ray\n'
                     '      或回车以保存配置并运行, 或 q 以保存配置并退出\n').strip()
    if inputStr == '':
        generateAndRestartAndExit()
    elif inputStr == 'f':
        config['runInFront'] = True if not config['runInFront'] else False
    elif inputStr == 's':
        config['useSudo'] = True if not config['useSudo'] else False
    elif inputStr == 'u':
        for key, value in config.items():
            if isUrl(key):
                updateSubscriptions(key)
    elif inputStr == 'd':
        if outBounds[0]['protocol'] == 'vmess':
            outBounds[0], outBounds[freedomIndex] = outBounds[freedomIndex], outBounds[0]
        else:
            outBounds[0], outBounds[vmessIndex] = outBounds[vmessIndex], outBounds[0]
    elif inputStr == 'q':
        saveConfig()
        exit()
    elif inputStr.isdigit():
        # 要连接的配置序号
        connectII = connects[int(inputStr) - 1]
        mainVnext['address'] = connectII['add']
        mainVnext['port'] = int(connectII['port'])
        mainUser['id'] = connectII['id']
        mainUser['alterId'] = connectII['aid']
        streamSettings['network'] = connectII['net']
        streamSettings['tcpSettings']['header']['type'] = connectII['type']
        streamSettings['kcpSettings']['header']['type'] = connectII['type']
        streamSettings['quicSettings']['header']['type'] = connectII['type']
        wsSettings['headers'] = connectII['host']
        wsSettings['path'] = connectII['path']
    elif inputStr.startswith('vmess://'):
        # 连接配置
        connectsI = re.split(r'\n|\\n', inputStr)
        for connectI in connectsI:
            if 'vmess://' not in connectI:
                continue
            connectI = getConnect(connectI)
            config['imported'].append(connectI)
    elif ' ' in inputStr:
        # 向列表添加域名或 IP
        addAddr()
    else:
        # 订阅地址
        if not isUrl(inputStr):
            inputStr = 'http://' + inputStr
        updateSubscriptions(inputStr)
