# V2Ray 管理脚本

因图形界面客户端难以为所有连接自定义配置, 所以编写此脚本

仅支持 Linux

# 使用方法

## 首次运行

将 V2Ray 配置文件重命名为 `V2Ray-Config.json`, 并置于 `~/.config/V2Ray-Manager/` 中.

确保配置中的 `vmess` 出站包含以下形式的 `streamSettings`:

```json
"streamSettings": {
    "network": "",
    "kcpSettings": {
        "header": {
            "type": ""
        }
    },
    "quicSettings": {
        "header": {
            "type": ""
        }
    },
    "tcpSettings": {
        "header": {
            "type": ""
        }
    },
    "wsSettings": {
        "headers": {
            "Host": ""
        },
        "path": ""
    },
```

可选地, 向 PATH 中添加此脚本的符号链接:

```sh
ln -s $PWD/V2Ray-Manager.py ~/.local/bin/v2man
```

## 运行

运行此脚本

# 示例

```
$ v2man
功能: 需要键入的内容
从剪贴板添加 vmess 连接配置: c
添加订阅地址: <订阅地址>
更新订阅: u
查看配置列表: p
选择要连接的配置: <序号>
保存配置并运行: (回车)
保存配置并退出: q
向黑白名单列表(rules与dns)添加域名或 IP: (形如 "gfw google.com" 或 "cn 223.5.5.5")
切换默认出站(freedom/vmess): d
切换前台运行 V2Ray: f
切换使用 sudo 运行 V2Ray: s
移除所有规则并备份, 或从备份中恢复: r
移除拦截广告的规则并备份, 或从备份中恢复: a

默认出站: freedom
要连接的配置: 日本1: www.my-server.com
在前台运行 V2Ray: False
使用 sudo 运行 V2Ray: True
https://www.my-server.com/123456

默认出站: freedom
要连接的配置: 日本1: www.my-server.com
在前台运行 V2Ray: False
使用 sudo 运行 V2Ray: True
p

默认出站: freedom
要连接的配置: 日本1: www.my-server.com
在前台运行 V2Ray: False
使用 sudo 运行 V2Ray: True
18

默认出站: freedom
要连接的配置: 美国3: www.my-server.com
在前台运行 V2Ray: False
使用 sudo 运行 V2Ray: True
gfw github.com

默认出站: freedom
要连接的配置: 美国3: www.my-server.com
在前台运行 V2Ray: False
使用 sudo 运行 V2Ray: True

root

```

# 免责声明

下载, 使用脚本时均视为已经仔细阅读并完全同意以下条款:

- 脚本仅供个人学习与交流使用，严禁用于商业以及不良用途
- 使用本脚本所存在的风险将完全由其本人承担，脚本作者不承担任何责任
- 本声明未涉及的问题请参见国家有关法律法规，当本声明与国家有关法律法规冲突时，以国家法律法规为准

