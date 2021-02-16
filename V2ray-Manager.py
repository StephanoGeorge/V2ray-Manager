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

path = Path.home() / '.config' / 'V2Ray-Manager'
config_path = path / 'Config.yaml'
v2ray_path = path / 'V2Ray-Config.json'

# path.mkdir(parents=True, exist_ok=True)
config_path.touch()
with config_path.open() as config_stream:
    config = yaml.safe_load(config_stream)
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
with v2ray_path.open() as v2ray_stream:
    v2ray = json.load(v2ray_stream)

subscriptions = config['subscriptions']
imported = config['imported']
out_bounds = v2ray['outbounds']

connections = []

vmess = {}
freedom = {}
vmess_index = 0
freedom_index = 0
for index1, out1 in enumerate(out_bounds):
    out_protocol = out1['protocol']
    if out_protocol == 'vmess':
        vmess = out1
        vmess_index = index1
    elif out_protocol == 'freedom':
        freedom = out1
        freedom_index = index1

gfw_domain = []
gfw_ip = []
cn_domain = []
cn_ip = []
for rule1 in v2ray['routing']['rules']:
    outbound_tag = rule1['outboundTag']
    if outbound_tag == vmess['tag']:
        if 'domain' in rule1:
            gfw_domain = rule1['domain']
        elif 'ip' in rule1:
            gfw_ip = rule1['ip']
    elif outbound_tag == freedom['tag']:
        if 'domain' in rule1:
            cn_domain = rule1['domain']
        elif 'ip' in rule1:
            cn_ip = rule1['ip']

dns_gfw = []
dns_cn = []
if 'dns' in v2ray and 'servers' in v2ray['dns']:
    for server1 in v2ray['dns']['servers']:
        if type(server1) == dict:
            dns_domains = server1['domains']
            if 'geosite:google' in dns_domains:
                dns_gfw = dns_domains
            elif 'geosite:cn' in dns_domains:
                dns_cn = dns_domains

main_vnext = vmess['settings']['vnext'][0]
main_user = main_vnext['users'][0]
stream_settings = vmess['streamSettings']

input_str = ''

do_update_subscriptions = False


def update_connections(do_print=False):
    global connections
    connections = []
    echo = []
    count = itertools.count(1)
    if do_print:
        echo.append('\033[32m{}\033[0m\n'.format('imported'))
    for connection1 in imported:
        connections.append(connection1)
        if do_print:
            echo.append('\033[34m{}\033[0m\t{}\t\t{}\n'.format(next(count), connection1['ps'], connection1['add']))
    for url1, connections1 in subscriptions.items():
        if do_print:
            echo.append('\033[32m{}\033[0m\n'.format(url1))
        for connection2 in connections1:
            connections.append(connection2)
            if do_print:
                echo.append('\033[34m{}\033[0m\t{}\t\t{}\n'.format(next(count), connection2['ps'], connection2['add']))
    if do_print:
        os.system('echo "{}" | less -r'.format(''.join(echo)))  # 我不知道怎么正确地通过两个 subprocess.PIPE 传递输入


def get_connection(string):
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


def add_import(connection):
    connection = get_connection(connection)
    if connection:
        imported.append(connection)


def update_subscriptions(url):
    for _ in range(3):
        if not do_update_subscriptions:
            return
        try:
            response = requests.get(url, timeout=10)
            new_connections = b64decode(response.text).decode()
            break
        except Exception as e:
            print(f'{type(e).__name__}: {e}')
            continue
    else:
        print(f'更新失败: {url}')
        return
    new_subscriptions = []
    for connection in new_connections.splitlines():
        connection = get_connection(connection)
        if connection:
            new_subscriptions.append(connection)
    if new_subscriptions:
        if not do_update_subscriptions:
            return
        subscriptions[url] = new_subscriptions
        print(f'已更新: {url}')
    else:
        print(f'返回空配置列表, 未更改: {url}')


def add_address(address, target, rules):
    if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', address):
        if not rules:
            return
        if target == 'gfw':
            if address in gfw_ip:
                print('{} 已经存在于 GFW IPs'.format(address))
            else:
                gfw_ip.append(address)
        else:
            if address in cn_ip:
                print('{} 已经存在于 CN IPs'.format(address))
            else:
                cn_ip.append(address)
    else:
        if address.startswith('http'):
            address = re.sub(r'https?://', '', address)
        domain_item = 'domain:{}'.format(address)
        if target == 'gfw':
            if rules:
                if gfw_domain:
                    if domain_item in gfw_domain:
                        print('{} 已经存在于 GFW domains'.format(domain_item))
                    else:
                        gfw_domain.append(domain_item)
            if dns_gfw:
                if domain_item in dns_gfw:
                    print('{} 已经存在于 GFW DNS domains'.format(domain_item))
                else:
                    dns_gfw.append(domain_item)
        else:
            if rules:
                if cn_domain:
                    if domain_item in cn_domain:
                        print('{} 已经存在于 CN domains'.format(domain_item))
                    else:
                        cn_domain.append(domain_item)
            if dns_cn:
                if domain_item in dns_cn:
                    print('{} 已经存在于 CN DNS domains'.format(domain_item))
                else:
                    dns_cn.append(domain_item)


def add_address_from_input_str():
    if input_str.startswith('gfw'):
        target = 'gfw'
    else:
        target = 'cn'
    address = input_str.replace('{} '.format(target), '')
    add_address(address, target, True)


def set_connection():
    if not connections:
        update_connections()
    connection = connections[int(input_str) - 1]
    main_vnext['address'] = connection['add']
    main_vnext['port'] = int(connection['port'])
    main_user['id'] = connection['id']
    main_user['alterId'] = int(connection['aid'])
    stream_settings['network'] = connection['net']

    def set_header(prefix):
        settings = f'{prefix}Settings'
        if settings not in stream_settings:
            stream_settings[settings] = {'header': {}}
        elif 'header' not in stream_settings[settings]:
            stream_settings[settings]['header'] = {}
        stream_settings[settings]['header']['type'] = connection['type']

    if stream_settings['network'] == 'ws':
        if 'wsSettings' not in stream_settings:
            stream_settings['wsSettings'] = {'headers': {}}
        elif 'headers' not in stream_settings['wsSettings']:
            stream_settings['wsSettings']['headers'] = {}
        stream_settings['wsSettings']['headers']['Host'] = connection['host']
        stream_settings['wsSettings']['path'] = connection['path']
    else:
        # tcp, kcp, quic
        set_header(stream_settings['network'])
    stream_settings['security'] = connection['tls']
    if config['current-connection']:
        if 'dns' in v2ray and 'servers' in v2ray['dns']:
            for server in v2ray['dns']['servers']:
                if type(server) == dict and 'domains' in server:
                    domainItem = f"domain:{config['current-connection']['add']}"
                    if domainItem in server['domains']:
                        server['domains'].remove(domainItem)
    add_address(main_vnext['address'], 'cn', False)
    config['current-connection'] = connection


def sort_connection_keys(connection):
    if 'sorted' in connection:
        connection = {
            'ps': connection['ps'],
            'add': connection['add'],
            'port': connection['port'],
            'id': connection['id'],
            'aid': connection['aid'] if 'aid' in connection else '0',
            'net': connection['net'],
            'type': connection['type'],
            'host': connection['host'] if 'host' in connection else '',
            'path': connection['path'] if 'path' in connection else '',
            'tls': connection['tls'] if 'tls' in connection else '',
        }
        return connection
    return connection


def save_config():
    for i1, connection1 in enumerate(imported):
        imported[i1] = sort_connection_keys(connection1)
    for url2 in subscriptions.keys():
        for i2, connection2 in enumerate(subscriptions[url2]):
            subscriptions[url2][i2] = sort_connection_keys(connection2)
    with config_path.open('w') as configStream1:
        yaml.safe_dump(config, configStream1, indent=4, allow_unicode=True, sort_keys=False)
    with v2ray_path.open('w') as v2rayStream1:
        json.dump(v2ray, v2rayStream1, indent=4)


def generate_and_restart_and_exit():
    save_config()
    if config['use-sudo']:
        os.system('sudo whoami')
        os.system('sudo killall v2ray > /dev/null 2>&1')
        if config['run-in-front']:
            os.system(f"sudo {config['v2ray-command']} -config {v2ray_path.resolve()}")
        else:
            os.system(f"nohup sudo {config['v2ray-command']} -config {v2ray_path.resolve()} > /dev/null 2>&1 &")
    else:
        os.system('killall v2ray > /dev/null 2>&1')
        if config['run-in-front']:
            os.system(f"{config['v2ray-command']} -config {v2ray_path.resolve()}")
        else:
            os.system(f"nohup {config['v2ray-command']} -config {v2ray_path.resolve()} > /dev/null 2>&1 &")
    exit()


def highlight(string):
    return f'\33[33m{string}\33[0m'


def main():
    global input_str, vmess_index, freedom_index, do_update_subscriptions
    first = True
    while True:
        if first:
            first = False
            print(
                '以下为: "功能: 键入的内容"\n'
                '从剪贴板添加 vmess 连接配置: c\n'
                '添加订阅地址: <订阅地址>\n'
                '更新订阅: u\n'
                '查看配置列表: p\n'
                '选择要连接的配置: <序号>\n'
                '保存配置并运行: (回车)\n'
                '保存配置并退出: q\n'
                '向黑白名单列表(rules与dns)添加域名或IP: (形如 "gfw google.com" 或 "cn 223.5.5.5")\n'
                '切换默认出站(freedom/vmess): d\n'
                '切换前台运行 V2Ray: f\n'
                '切换使用 sudo 运行 V2Ray: s\n'
                '移除所有规则并备份, 或从备份中恢复: r\n'
                '移除拦截广告的规则并备份, 或从备份中恢复: a'
            )
        print(
            f"\n默认出站: {highlight(out_bounds[0]['protocol'])}\n"
            f'''要连接的配置: {highlight(
                f"{config['current-connection']['ps']}: {config['current-connection']['add']}"
                if config['current-connection'] else ''
            )}\n'''
            f"在前台运行 V2Ray: {highlight(config['run-in-front'])}\n"
            f"使用 sudo 运行 V2Ray: {highlight(config['use-sudo'])}"
        )
        input_str = input().strip()
        if input_str == '':
            generate_and_restart_and_exit()
        elif input_str == 'c':
            for connection in re.split(r'\n|\\n', pyperclip.paste()):
                add_import(connection)
        elif input_str == 'u':
            print('Ctrl+C 以终止')
            do_update_subscriptions = True
            threads = []
            for url1, connection1 in subscriptions.items():
                thread1 = Thread(target=update_subscriptions, args=(url1,))
                threads.append(thread1)
                thread1.start()
            try:
                for thread2 in threads:
                    thread2.join()
            except KeyboardInterrupt:
                print()
                do_update_subscriptions = False
        elif input_str == 'p':
            update_connections(do_print=True)
        elif input_str == 'q':
            save_config()
            exit()
        elif input_str == 'd':
            if out_bounds[0]['protocol'] == 'vmess':
                out_bounds[0], out_bounds[freedom_index] = out_bounds[freedom_index], out_bounds[0]
                vmess_index, freedom_index = freedom_index, 0
            else:
                out_bounds[0], out_bounds[vmess_index] = out_bounds[vmess_index], out_bounds[0]
                vmess_index, freedom_index = 0, vmess_index
        elif input_str == 'f':
            config['run-in-front'] = not config['run-in-front']
        elif input_str == 's':
            config['use-sudo'] = not config['use-sudo']
        elif input_str == 'r':
            if v2ray['routing']['rules']:
                config['config']['routing']['rules'] = v2ray['routing']['rules']
                v2ray['routing']['rules'] = []
            else:
                v2ray['routing']['rules'] = config['config']['routing']['rules']
        elif input_str == 'a':
            if not v2ray['routing']['rules']:
                continue
            ok1 = False
            rule_index = -1
            for rule_index2, rule2 in enumerate(v2ray['routing']['rules']):
                if 'domain' in rule2 and 'geosite:category-ads-all' in rule2['domain']:
                    ok1 = True
                    rule_index = rule_index2
                    break
            if ok1:
                config['config']['routing']['_category-ads-all'] = v2ray['routing']['rules'][rule_index]
                v2ray['routing']['rules'].pop(rule_index)
            else:
                v2ray['routing']['rules'].append(config['config']['routing']['_category-ads-all'])
        elif input_str.isdecimal():
            # 选择要连接的配置
            set_connection()
        elif re.search('^(gfw)|(cn) .', input_str):
            # 向列表添加域名或 IP
            add_address_from_input_str()
        else:
            # 订阅地址
            if not input_str.startswith('http'):
                input_str = f'http://{input_str}'
            update_subscriptions(input_str)


main()
