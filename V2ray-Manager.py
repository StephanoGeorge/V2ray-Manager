#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import argparse
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

proxy_protocols = ('vmess', 'shadowsocks')
proxy_protocols_abbr = ('vmess', 'ss')

parser = argparse.ArgumentParser()
user = os.getenv('SUDO_USER')
default_path = Path('/' if user == 'root' else '/home') / user / '.config' / 'V2Ray-Manager'
parser.add_argument('--config', default=default_path, help='V2ray manager config path')
args = parser.parse_args()
path = args.config
config_path = path / 'Config.yaml'

# path.mkdir(parents=True, exist_ok=True)
config_path.touch()
config = yaml.safe_load(config_path.read_text())
if not config:
    config = {
        'run-in-front': False,
        'v2ray-config': '/etc/v2ray/config.json',
        'v2ray-command': 'systemctl restart v2ray.service',
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
v2ray_path = Path(config['v2ray-config'])
v2ray = json.loads(v2ray_path.read_text())

subscriptions = config['subscriptions']
imported = config['imported']
out_bounds = v2ray['outbounds']

connections = []

# v2ray的子对象的引用
proxy = {}
freedom = {}
proxy_index = 0
freedom_index = 0

# v2ray的子对象的引用
domain_gfw = []
ip_gfw = []
domain_cn = []
ip_cn = []
dns_gfw = []
dns_cn = []

# v2ray的子对象的引用
stream_settings = {}

input_str = ''
has_set_connections = False
do_update_subscriptions = False


def init():
    global proxy, proxy_index, freedom, freedom_index, \
        domain_gfw, ip_gfw, domain_cn, ip_cn, dns_gfw, dns_cn, stream_settings
    for index1, out1 in enumerate(out_bounds):
        out_protocol = out1['protocol']
        if out_protocol in proxy_protocols:
            proxy = out1
            proxy_index = index1
        elif out_protocol == 'freedom':
            freedom = out1
            freedom_index = index1
    for rule1 in v2ray['routing']['rules']:
        outbound_tag = rule1['outboundTag']
        if outbound_tag == proxy['tag']:
            if 'domain' in rule1:
                domain_gfw = rule1['domain']
            elif 'ip' in rule1:
                ip_gfw = rule1['ip']
        elif outbound_tag == freedom['tag']:
            if 'domain' in rule1:
                domain_cn = rule1['domain']
            elif 'ip' in rule1:
                ip_cn = rule1['ip']
    if 'dns' in v2ray and 'servers' in v2ray['dns']:
        for server1 in v2ray['dns']['servers']:
            if isinstance(server1, dict):
                dns_domains = server1['domains']
                if 'geosite:google' in dns_domains:
                    dns_gfw = dns_domains
                elif 'geosite:cn' in dns_domains:
                    dns_cn = dns_domains
    stream_settings = proxy['streamSettings']


def update_connections(do_print=False):
    global connections
    connections = []
    echo = []
    count = itertools.count(1)
    if do_print:
        echo.append(f"{highlight('imported', 32)}\n")
    for connection1 in imported:
        connections.append(connection1)
        if do_print:
            echo.append(f"{highlight(next(count), 34)}\t{connection1['remarks']}\t\t{connection1['address']}\n")
    for url1, connections1 in subscriptions.items():
        if do_print:
            echo.append(f'{highlight(url1, 32)}\n')
        for connection2 in connections1:
            connections.append(connection2)
            if do_print:
                echo.append(f"{highlight(next(count), 34)}\t{connection2['remarks']}\t\t{connection2['address']}\n")
    if do_print:
        # TODO: 通过两个 subprocess.PIPE 传递输入
        os.system(f'''echo "{''.join(echo)}" | less -r''')


def get_connection(string):
    protocol = re.search(rf"^({'|'.join(proxy_protocols_abbr)})://", string)
    if not protocol:
        return None
    try:
        string = string.removeprefix(protocol.group(0))
        protocol = protocol.group(1)
        if protocol == 'vmess':
            connection_vmess = json.loads(b64decode(string))
            if 'v' in connection_vmess and connection_vmess['v'] != '2':
                print(f"仅支持 version 2 连接, 当前连接 version {connection_vmess['v']}")
                return None
            return {
                '_protocol': protocol,
                'remarks': connection_vmess['ps'],
                'address': connection_vmess['add'],
                'port': int(connection_vmess['port']),
                'id': connection_vmess['id'],
                'aid': int(connection_vmess['aid']) if 'aid' in connection_vmess else 0,
                'net': connection_vmess['net'],
                'type': connection_vmess['type'],
                'host': connection_vmess['host'] if 'host' in connection_vmess else '',
                'path': connection_vmess['path'] if 'path' in connection_vmess else '',
                'tls': connection_vmess['tls'] if 'tls' in connection_vmess else '',
            }
        elif protocol == 'ss':
            connection_ss, ps = string.split('#')
            connection_ss = b64decode(connection_ss).decode()
            search = re.search('^(?P<method>.+?):(?P<password>.+)@(?P<address>.+?):(?P<port>[0-9]+)$', connection_ss)
            return {
                '_protocol': protocol,
                'remarks': ps,
                'address': search.group('address'),
                'port': int(search.group('port')),
                'method': search.group('method'),
                'password': search.group('password'),
            }
    except Exception as e:
        print(f'{type(e).__name__}: {e}')
        return None


def add_import(connection):
    connection = get_connection(connection)
    if connection:
        imported.append(connection)


def update_subscriptions_wrapper(urls=None):
    global do_update_subscriptions
    print('Ctrl+C 以终止')
    do_update_subscriptions = True
    threads = []
    if not urls:
        urls = subscriptions.keys()
    for url in urls:
        thread1 = Thread(target=update_subscriptions, args=(url,))
        threads.append(thread1)
        thread1.start()
    try:
        for thread2 in threads:
            thread2.join()
    except KeyboardInterrupt:
        do_update_subscriptions = False
        print()


def update_subscriptions(url):
    for _ in range(3):
        if not do_update_subscriptions:
            return
        try:
            response = requests.get(url, timeout=10)
            new_connections = b64decode(response.text).decode()
            break
        except Exception as e:
            if not do_update_subscriptions:
                return
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


def add_address(address, target, rules, warning=True):
    if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', address):
        if not rules:
            return
        if target == 'gfw':
            if address in ip_gfw and warning:
                print(f'已经存在于 GFW IPs: {address}')
            else:
                ip_gfw.append(address)
        else:
            if address in ip_cn and warning:
                print(f'已经存在于 CN IPs: {address}')
            else:
                ip_cn.append(address)
    else:
        if address.startswith('http'):
            address = re.sub(r'https?://', '', address)
        domain_item = f'domain:{address}'

        def set_target(domain_list, dns_list):
            if rules:
                if domain_list:
                    if domain_item in domain_list and warning:
                        print(f"已经存在于 {target.upper()} domains: {domain_item}")
                    else:
                        domain_list.append(domain_item)
            if dns_list:
                if domain_item in dns_list and warning:
                    print(f'已经存在于 {target.upper()} DNS domains: {domain_item}')
                else:
                    dns_list.append(domain_item)

        if target == 'gfw':
            set_target(domain_gfw, dns_gfw)
        else:
            set_target(domain_cn, dns_cn)


def add_address_from_input_str():
    if input_str.startswith('gfw'):
        target = 'gfw'
    else:
        target = 'cn'
    address = input_str.removeprefix(f'{target} ')
    add_address(address, target, True)


def set_connection(from_input=True):
    global has_set_connections
    if not from_input and has_set_connections:
        return
    if not connections:
        update_connections()
    connection = connections[int(input_str) - 1] if from_input else config['current-connection']
    if connection['_protocol'] == 'vmess':
        proxy['protocol'] = 'vmess'
        proxy['settings'].setdefault('vnext', [{'users': [{}]}])
        proxy['settings']['vnext'][0]['address'] = connection['address']
        proxy['settings']['vnext'][0]['port'] = connection['port']
        proxy['settings']['vnext'][0]['users'][0]['id'] = connection['id']
        proxy['settings']['vnext'][0]['users'][0]['alterId'] = connection['aid']
        stream_settings['network'] = connection['net']
        stream_settings['security'] = connection['tls']

        def set_header(prefix):
            settings = f'{prefix}Settings'
            stream_settings.setdefault(settings, {'header': {}})
            stream_settings[settings].setdefault('header', {})
            stream_settings[settings]['header']['type'] = connection['type']

        if stream_settings['network'] == 'ws':
            stream_settings.setdefault('wsSettings', {'headers': {}})
            stream_settings['wsSettings'].setdefault('headers', {})
            stream_settings['wsSettings']['headers']['Host'] = connection['host']
            stream_settings['wsSettings']['path'] = connection['path']
        else:
            # tcp, kcp, quic
            set_header(stream_settings['network'])
    elif connection['_protocol'] == 'ss':
        proxy['protocol'] = 'shadowsocks'
        proxy['settings'].setdefault('servers', [{}])
        proxy['settings']['servers'][0]['address'] = connection['address']
        proxy['settings']['servers'][0]['port'] = connection['port']
        proxy['settings']['servers'][0]['method'] = connection['method']
        proxy['settings']['servers'][0]['password'] = connection['password']
        stream_settings['network'] = 'tcp'

    if config['current-connection']:
        if 'dns' in v2ray and 'servers' in v2ray['dns']:
            for server in v2ray['dns']['servers']:
                if isinstance(server, dict) and 'domains' in server:
                    domain_item = f"domain:{config['current-connection']['address']}"
                    if domain_item in server['domains']:
                        server['domains'].remove(domain_item)
    add_address(connection['address'], 'cn', False, warning=from_input)
    config['current-connection'] = connection
    has_set_connections = True


def save_config():
    config_path.write_text(yaml.safe_dump(config, indent=4, allow_unicode=True, sort_keys=False))
    v2ray_path.write_text(json.dumps(v2ray, indent=4))


def save_and_run_and_exit():
    set_connection(from_input=False)
    save_config()
    if config['run-in-front']:
        os.system(f"{config['v2ray-command']}")
    else:
        os.system(f"nohup {config['v2ray-command']} > /dev/null 2>&1 &")
    exit()


def highlight(string, code=33):
    return f'\33[{code}m{string}\33[0m'


def main():
    global input_str, proxy_index, freedom_index, do_update_subscriptions
    init()
    first = True
    while True:
        try:
            if first:
                first = False
                print(
                    '功能列表: "功能描述: 输入"\n'
                    f'从剪贴板添加 {proxy_protocols_abbr} 连接配置: c\n'
                    '添加订阅地址: <订阅地址>\n'
                    '更新订阅: u\n'
                    '查看配置列表: p\n'
                    '选择要连接的配置: <序号>\n'
                    '保存配置并运行: (回车)\n'
                    '保存配置并退出: q\n'
                    '向黑白名单列表(rules与dns)添加域名或IP: (形如 "gfw google.com" 或 "cn 223.5.5.5")\n'
                    '切换默认出站(freedom/proxy): d\n'
                    '切换前台运行 V2Ray: f\n'
                    '移除所有规则并备份, 或从备份中恢复: r\n'
                    '移除拦截广告的规则并备份, 或从备份中恢复: a'
                )
            print(
                f"\n默认出站: {highlight(out_bounds[0]['protocol'])}\n"
                f'''要连接的配置: {highlight(
                    f"{config['current-connection']['remarks']}: {config['current-connection']['address']}"
                    if config['current-connection'] else ''
                )}\n'''
                f"在前台运行 V2Ray: {highlight(config['run-in-front'])}"
            )
            input_str = input().strip()
            if input_str == '':
                save_and_run_and_exit()
            elif input_str == 'c':
                for connection in re.split('\n|\\n', pyperclip.paste()):
                    add_import(connection)
            elif input_str == 'u':
                update_subscriptions_wrapper()
            elif input_str == 'p':
                update_connections(do_print=True)
            elif input_str == 'q':
                save_config()
                exit()
            elif input_str == 'd':
                if out_bounds[0]['protocol'] in proxy_protocols:
                    out_bounds[0], out_bounds[freedom_index] = out_bounds[freedom_index], out_bounds[0]
                    proxy_index, freedom_index = freedom_index, 0
                else:
                    out_bounds[0], out_bounds[proxy_index] = out_bounds[proxy_index], out_bounds[0]
                    proxy_index, freedom_index = 0, proxy_index
            elif input_str == 'f':
                config['run-in-front'] = not config['run-in-front']
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
                for rule_index1, rule1 in enumerate(v2ray['routing']['rules']):
                    if 'domain' in rule1 and 'geosite:category-ads-all' in rule1['domain']:
                        ok1 = True
                        rule_index = rule_index1
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
                print('更新订阅')
                update_subscriptions_wrapper([input_str])
        except Exception as e:
            print(f'{type(e).__name__}: {e}')


main()
