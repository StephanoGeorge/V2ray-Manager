# V2ray 管理脚本

因图形界面客户端难以为所有连接自定义配置, 所以编写此脚本

仅支持 Linux

# 使用方法

## 首次运行

将 v2ray 配置文件置于此脚本所在目录, 并重命名为 `V2ray-Config.json`.

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
ln -s $PWD/V2ray-Manager.py ~/.local/bin/v2man
```

## 运行

运行此脚本

# 示例

```
1      洛杉矶              example.com
2      日本                example.com
默认出站: freedom
要连接的配置: example.com
在前台运行 V2ray: True
使用 sudo 运行 V2ray: False

键入: vmess 连接配置, 或订阅地址, 或 u 以更新订阅, 或要连接的配置序号,
      或 "gfw google.com"/"cn 223.5.5.5" 向黑白名单列表添加域名或 IP,
      或 d 以切换默认出站, 或 f 以切换前台运行 V2ray, 或 s 以切换使用 sudo 运行 V2ray
      或回车以保存配置并运行, 或 q 以保存配置并退出
```

# 免责声明

下载, 使用脚本时均视为已经仔细阅读并完全同意以下条款:

- 脚本仅供个人学习与交流使用，严禁用于商业以及不良用途
- 使用本脚本所存在的风险将完全由其本人承担，脚本作者不承担任何责任
- 本声明未涉及的问题请参见国家有关法律法规，当本声明与国家有关法律法规冲突时，以国家法律法规为准

