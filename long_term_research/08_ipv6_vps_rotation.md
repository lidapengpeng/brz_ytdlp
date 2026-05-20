# IPv6 /64 VPS 轮换专项调研

> 日期: 2026-05-19
> 状态: Research v1
> 关联问题: 单 IPv4 节点 token bucket 限流（YouTube guest session ~1000 req/hr/IP），需要 IP 池数量级提升
> 作者: brz_ytdlp 长期顾问

---

## TL;DR

1. **本机 IPv6 路径已死**：macOS + Clash TUN 把所有 IPv6 收编到 `utun8` fake address，且 macOS 不允许 socket bind 到 /64 内任意未注册地址；中国大陆 ISP 走 IPv6 出口的 YouTube 路径未经验证、且 GFW 风险高。
2. **VPS + /64 IPv6 是唯一可行的"数量级"扩容方案**：单台 5 美元/月 VPS 可提供 **18 quintillion** 个出站源 IP，理论可让 token bucket 限流不再是单 IP 瓶颈。
3. **推荐栈**：**Hetzner CAX11 (Singapore, ARM, €3.79/mo, /64 IPv6 默认) + TREVORproxy（subnet 模式，用 Linux AnyIP 内核特性，每个 TCP connection 随机绑定 /64 内一个 IPv6 source）**，本机 Clash 把该 SOCKS5 当作一个节点接入。
4. **关键技术对比**：
   - smart-ipv6-rotator = cron 每 12h 换一个静态地址（粗糙，但好部署）
   - **TREVORproxy / freebind = 每 socket 随机选一个 /64 内地址（细粒度，本任务最佳）**
   - smart-ipv6-rotator 一定要看清：它只换 1 个地址/12h，不是"每请求一个 IP"
5. **真实风险**：YouTube 历来按 /64 段整体限流而非单 /128（Invidious 实战），所以 18 quintillion 不等于 18 quintillion 个独立 quota——但 /64 仍比单 IPv4 强一两个数量级，且可周期换 /64（多台 VPS）。

---

## 1. 背景：为什么本机 IPv6 不可行

### 1.1 macOS + Clash TUN 的 IPv6 接管行为
项目工程师之前实测：
- 中国 ISP 给了 `2001:da8:2d00:807::/64`（公网 /64，理论可用）
- Clash Verge 启用 TUN 模式后，整个 OS 的 IPv6 出站被 utun8（fake address）接管，所有 v6 流量被丢进代理隧道
- 即便关闭 TUN 让 v6 直连，macOS BSD socket 不接受 bind 到未 `ifconfig alias` 注册过的 /64 内地址，会报 `OSError 49: Can't assign requested address`
- macOS 无 Linux 的 `IP_FREEBIND` socket 选项、无 AnyIP 子网绑定特性

### 1.2 本次实测确认
```bash
$ curl -6 -s --max-time 5 https://api64.ipify.org
2607:a400:a:34b:333c:d3cb:946c:16a3
```
返回的是 **美国 ISP** 的 IPv6 → 证实 Clash TUN 已经把所有 v6 流量代理走了某个境外节点，**根本没用到本机 ISP 的 /64 子网**。本机 IPv6 路径在当前栈下不可恢复。

### 1.3 GFW + YouTube IPv6
- 大陆运营商 IPv6 直连 google IPv6 段的路径不稳定（北京电信/联通对 `2a00:1450::/32`、`2404:6800::/32` 的 PMTU/AS path 不一致）
- 即使能直连，PoP 仍可能落在欧洲，延迟高且易触发 YouTube 异常风控（同一 /64 出现"中国时区+欧洲路由"的反差）

**结论**：必须把出站点搬到海外 VPS 上。

---

## 2. VPS provider 对比表（2026-05 价格）

| 提供商 | 推荐型号 | vCPU/RAM/Disk | 月费 | 默认 IPv6 子网 | 流量额度 | 数据中心 | 中国用户开通难度 |
|---|---|---|---|---|---|---|---|
| **Hetzner Cloud** | CX22 (x86) | 2 / 4 GB / 40 GB | €3.79 (~$4.09) | **/64 免费** | 20 TB | 德 FSN/NBG、芬 HEL、美 ASH/HIL、**新加坡 SIN** | 中（要求护照 + 卡支付，封号风险中，UnionPay 可用） |
| **Hetzner Cloud** | **CAX11 (ARM)** | 2 / 4 GB / 40 GB | €3.79 (~$4.09) | **/64 免费** | 20 TB | FSN / NBG / HEL（**ARM 暂无 SIN**） | 同上 |
| **Hetzner Cloud** | CX32 | 4 / 8 GB / 80 GB | €6.80 | /64 免费 | 20 TB | 同 CX22 | 同上 |
| **Contabo** | VPS 10 SSD | 3 / 8 GB / 75 GB NVMe | $6.99 | **/64 免费** | 32 TB | 德/英/美/新加坡/印度/日本 | 中（信用卡 / PayPal） |
| **Vultr** | Regular 1GB | 1 / 1 GB / 25 GB | $6/mo + $0.50 IPv4 | **/64 免费** | 1 TB | 32 个城市（含东京/新加坡/HK） | **易**（支持 Alipay） |
| **Vultr** | IPv6-only 0.5GB | 1 / 0.5 GB / 10 GB | **$2.50/mo** | /64 | 0.5 TB | 全球 | 易 |
| **OVHcloud** | VPS Starter | 1 / 2 GB / 40 GB | ~$3.50 | /64 | 不限 | 法/加/美/新加坡/澳/印 | 中（卡，KYC 严） |
| **DigitalOcean** | Basic Droplet | 1 / 1 GB / 25 GB | $6 | **❌ 只有 /124（16 个）** | 1 TB | 全球 | 中（卡） |
| **RackNerd** | 促销年付 | 2 / 2 GB / 30 GB | ~$15/yr ($1.25/mo) | /64（部分套餐） | 2 TB | 美 LA 有 CN2 优化 | 易（支付宝/微信） |

### 选型决策
- **首选 Hetzner CAX11（FSN / NBG）**：ARM CPU 性价比最高、IPv6 /64 默认、稳定老牌、流量充足；唯一缺点是无 SIN ARM。若要 SIN 必须用 CX22 (x86)。
- **次选 Vultr Tokyo/Singapore**：对中国用户友好（Alipay）、有亚洲节点、IPv6 /64 默认；但 1TB 流量上限要注意（爬虫场景流量小，OK）。
- **避坑**：DigitalOcean 只给 /124（16 个 IPv6），**完全无法满足 /64 rotation 需求**，直接排除。

### 关键确认（已查证）
- Hetzner CAX11 / CX22 **IPv6 /64 是默认免费分配的**（实际是 `2a01:4f8::/29` 等大段分给客户子段）—— [docs.hetzner.com](https://docs.hetzner.com/cloud/general/locations/)
- Hetzner 2026 起 IPv4 每个 €0.50/mo，若 IPv6-only 可省（但 brz_ytdlp 本机连 VPS 还是需要 v4 入口，建议保留 IPv4）
- Contabo /64 也是默认（[contabo help](https://help.contabo.com/en/support/solutions/articles/103000270487-how-can-i-use-ipv6-on-my-server-)）

---

## 3. smart-ipv6-rotator 工作原理深度解析

### 3.1 设计目标（来自源码 + Invidious docs）
- 不是"每请求换 IP"——而是**定期换一个静态 IPv6 地址**
- Invidious 官方推荐：cron 每 12h（noon + midnight）跑一次
- 只针对**特定服务的 IPv6 段**改路由表，不影响其他流量

### 3.2 核心机制（源码 `smart_ipv6_rotator/__init__.py:130-272`）

#### 关键步骤
```python
# 1. 从 /64 网段中随机选一个 /128 地址
ipv6_network = IPv6Network(ipv6range)  # e.g. 2a01:4f8:c2c:1234::/64
random_ipv6_address = str(IPv6Address(
    ipv6_network.network_address
    + getrandbits(ipv6_network.max_prefixlen - ipv6_network.prefixlen)  # 64 random bits
))

# 2. 把这个 /128 加到接口上（等价于 ip -6 addr add）
IPROUTE.addr("add",
    index=default_interface_index,
    address=random_ipv6_address,
    mask=ipv6_network.prefixlen,
    preferred=preferred_value)

# 3. 对每个目标服务段（Google 的 15 个段），把 prefsrc 改成这个新地址
for ipv6_range in service_ranges:
    IPROUTE.route("add",
        dst=ipv6_range,                  # e.g. 2a00:1450::/32 (Google)
        prefsrc=random_ipv6_address,     # 我们这次选的 /128
        gateway=default_interface_gateway,
        oif=default_interface_index,
        priority=1)
```

#### 默认目标 ranges（`ranges.py`）
google 段 15 个：`2001:4860::/32`, `2404:6800::/32`, `2607:f8b0::/32`, `2a00:1450::/32`, `2c0f:fb50::/32` 等。

### 3.3 部署方式

#### 一次性手动
```bash
sudo apt install python3-requests python3-pyroute2
git clone https://github.com/iv-org/smart-ipv6-rotator.git
cd smart-ipv6-rotator
sudo python smart-ipv6-rotator.py run --ipv6range=YOUR_PREFIX/64
```

#### Cron 自动轮换（[Invidious 推荐](https://docs.invidious.io/ipv6-rotator/)）
```cron
@reboot          sleep 30 && /usr/bin/python /opt/smart-ipv6-rotator/smart-ipv6-rotator.py run --cron --ipv6range=2a01:4f8:abcd:1234::/64
0  */12  *  *  *  /usr/bin/python /opt/smart-ipv6-rotator/smart-ipv6-rotator.py run --cron --ipv6range=2a01:4f8:abcd:1234::/64
```

### 3.4 兼容性
- **必须 root**（修改路由表 + 接口地址）
- 需要 `pyroute2`（pip 或 apt）→ Python ≥ 3.9
- 任意 Linux（Debian / Ubuntu / Rocky / Arch 都行），用 systemd 或 cron 调度
- **关键限制**：要求 ISP/VPS 允许 bind 任意 /64 内地址（AWS/GCP/Azure 都不允许，Hetzner/Contabo/Vultr/OVH 允许）

### 3.5 致命局限
- **每次 run 只生成 1 个 IPv6**——所有出站流量都从这 1 个地址出
- 12 小时换一次 → 实际是"用 1 个 v6 跑 12 小时 → 再换 1 个跑 12 小时"
- **跟"每请求换一个 IP"完全是两回事**
- 适合 Invidious 这种单实例 +「降低单 IP 被识别累积量」的场景，**不适合 brz_ytdlp 这种"需要并发数千请求/秒"的场景**

---

## 4. **TREVORproxy + AnyIP**：本任务真正的杀手锏

smart-ipv6-rotator 12h 换一次太粗。我们要的是**每个 SOCKS connection 随机选一个 IPv6 源地址**。这正是 TREVORproxy 干的事。

### 4.1 工作原理（来自 [TREVORproxy README](https://github.com/blacklanternsecurity/TREVORproxy)）
```bash
sudo trevorproxy subnet -s 2a01:4f8:abcd:1234::/64 -i eth0
# [DEBUG] ip route add local 2a01:4f8:abcd:1234::/64 dev eth0
# [INFO] Listening on socks5://127.0.0.1:1080
```

它做了两件事：
1. `ip route add local <subnet> dev <iface>` —— 启用 Linux 内核的 **AnyIP** 特性，把整个 /64 看作"本机所有地址"
2. 跑一个 Python SOCKS5 server，listening on 1080；**每个进来的 connection，server 都随机生成一个 /64 内 /128，bind 它作为 outgoing source address**

#### 实测（README 示例）
```
$ curl --proxy socks5://127.0.0.1:1080 -6 api64.ipify.org
2a01:4f8:abcd:1234:74d0:b1be:3166:c934
$ curl --proxy socks5://127.0.0.1:1080 -6 api64.ipify.org
2a01:4f8:abcd:1234:4927:1b4:8e5f:d44d   # ← 每次不同！
$ curl --proxy socks5://127.0.0.1:1080 -6 api64.ipify.org
2a01:4f8:abcd:1234:2bb8:7b79:706e:cb7d
```

### 4.2 AnyIP 内核机制（[Wido den Hollander 详解](https://blog.widodh.nl/2016/04/anyip-bind-a-whole-subnet-to-your-linux-machine/)）
- `ip -6 route add local 2001:db8::/64 dev lo` 之后，kernel 把整段 /64 当作"本机 owned"
- Neighbor Discovery 自动应答 /64 内任意地址
- Userspace 可以 `bind()` 到这个段内**任意未注册**的 /128，kernel 不会返回 `EADDRNOTAVAIL`
- 相当于 Linux 上的 "免注册 bind" 能力——这就是 macOS 缺失的功能

### 4.3 备选方案对比

| 方案 | 粒度 | 部署 | 程序集成 | 适合 brz_ytdlp |
|---|---|---|---|---|
| smart-ipv6-rotator | 1 IP / 12h | cron + Python | 透明（路由级） | ❌ 太粗 |
| **TREVORproxy subnet** | 1 IP / connection | systemd | **SOCKS5 标准** | ✅✅✅ 最佳 |
| **freebind** (LD_PRELOAD) | 1 IP / socket | LD_PRELOAD shim | 改 yt-dlp 启动方式 | ✅ 备选 |
| **freebind.js** (Cobalt 同款) | 1 IP / dispatcher | Node 库 | 需要重写 brz_ytdlp 为 Node | ❌ 栈不匹配 |
| 多 SOCKS5 + 多 VPS | 多 IP / 多 VPS | 多机部署 | Clash provider 即可 | ✅ 后期叠加 |

### 4.4 TREVORproxy 安装
```bash
sudo apt install python3-pip
sudo pip install git+https://github.com/blacklanternsecurity/trevorproxy
sudo trevorproxy --help
```
依赖：Python 3.6+、`scapy`、`asyncio`。**必须 root**（要修改路由表）。

---

## 5. VPS → 本机链路架构选项

| 选项 | 链路 | 延迟开销 | 复杂度 | 可靠性 | brz_ytdlp 改动 |
|---|---|---|---|---|---|
| **A. SOCKS5 over public** | brz_ytdlp → VPS:1080 → YouTube IPv6 | +1 RTT (~150ms 到欧洲、~80ms 到新加坡、~200ms 到美东) | **低** | 高（成熟方案） | 把 SOCKS5 加进 Clash 节点池或直接 `--proxy` | 
| B. HTTPS proxy | 同上但 HTTPS | 同 A | 中（HTTPS proxy server 不如 SOCKS5 通用） | 中 | 一样 |
| C. WireGuard 隧道 | 整机 v6 走 WG | 隧道开销 + 网络层包覆 | 高（路由表麻烦） | 中 | 路由层透明 |
| D. brz_ytdlp 整搬上 VPS | 本机不参与 | 0 | 中（数据库同步问题） | 高 | 需要把 SQLite 迁过去或用 Postgres |

### 推荐：A（SOCKS5）+ 后期可叠加 D
- **现阶段（10 min - 1 day 内）**: 在 VPS 跑 TREVORproxy → 本机 Clash 加这个 SOCKS5 节点 → brz_ytdlp 完全不动代码
- **后期（数据库压力大、本机带宽紧张）**: 把 brz_ytdlp 整体搬上 VPS，避免数据来回穿越，进一步降低延迟

### 选项 A 的 SOCKS5 公网暴露
TREVORproxy 默认监听 `127.0.0.1:1080`，要让本机 Clash 能连，必须：
```bash
sudo trevorproxy -l 0.0.0.0 -p 1080 subnet -s YOUR_PREFIX/64 -i eth0
```
**但裸暴露 1080 = 公网开放 SOCKS5 = 立刻被滥用**。两种安全方案：
1. **iptables 白名单**只允许你的家庭 IP → 简单但你家 IP 可能漂动
2. **stunnel / 用 WireGuard 套层**：VPS 跑 WG server，本机连 WG，TREVORproxy 监听 WG 内网 IP；外部完全看不到 1080
3. **ssh -L 端口转发**最简单：本机 `ssh -L 1080:localhost:1080 root@vps`，brz_ytdlp 连 `socks5://127.0.0.1:1080`

**推荐 ssh -L**（零配置、加密、Clash 配置零改动）。

---

## 6. YouTube IPv6 兼容性

### 6.1 本机 dig 测试（注：Clash TUN 干扰）
本机 `dig AAAA youtube.com` 全部返回空 —— 不是 YouTube 没 AAAA，而是 **Clash 的 DNS 模块禁用了 AAAA 查询**（绝大多数代理工具默认行为，避免 IPv6 直连绕开代理）。

不要根据本机 dig 结果下结论。下面是已知事实：

### 6.2 已知 YouTube IPv6 AAAA 范围（来自 smart-ipv6-rotator `ranges.py`）
YouTube/Google 在以下 IPv6 段提供完整 AAAA：
```
2001:4860::/32  # 老 Google
2404:6800::/32  # APAC
2404:f340::/32
2607:f8b0::/32  # 美洲
2620:11a:a000::/40
2800:3f0::/32   # 南美
2a00:1450::/32  # 欧洲
```

### 6.3 在 VPS 上验证（部署后第一步）
```bash
# 上 VPS 后立即跑
dig AAAA youtube.com
dig AAAA www.youtube.com
dig AAAA youtubei.googleapis.com
dig AAAA i.ytimg.com
curl -6 -sI https://www.youtube.com | head -3
curl -6 -sI https://youtubei.googleapis.com/youtubei/v1/player | head -3
```

### 6.4 YouTube 对 /64 段的限流行为（实战经验汇总）
来自 Invidious 项目 #3915、#3822、Cobalt 项目讨论：
- **YouTube 不是按单 /128 限流**，而是按 /64 段累积（这是 IPv6 anti-abuse 通行做法）
- 但 /64 限流的阈值**远高于** /32 (IPv4) 单地址：经验值是单 /64 可以跑 1-10 e/s 持续数小时
- 周期性轮换 /64（多台 VPS）= 实战中 Invidious / Piped / SearXNG 用的标准做法
- 风险：Hetzner 的 `2a01:4f8::/29` 大段历史上有被 YouTube"软封"几小时的记录，但不是永久封；切到不同数据中心可缓解

### 6.5 IPv6 vs IPv4 quota
- YouTube 对 IPv4 和 IPv6 的 guest session quota **是独立计数**的（来自 Invidious 经验）
- 所以"本机 IPv4 (Clash 30 节点) + VPS IPv6" = 两个独立池子，**完全可以叠加**！

---

## 7. 完整部署 playbook

### 7.1 选定：Hetzner CAX11 in FSN1（Falkenstein, ARM, €3.79/mo）

**理由**：
- ARM 性能/价格最优（Ampere Altra）
- Falkenstein 是 Hetzner 最大数据中心，IPv6 路由稳
- 流量 20 TB/月（爬虫单台日均 < 100GB，绰绰有余）
- 默认 /64 IPv6 + 1 IPv4

### 7.2 注册 → 创建 server

1. 访问 https://accounts.hetzner.com/signUp
   - 邮箱 + 密码 → 邮箱验证
   - 公司信息可填个人；地址用真实地址（首次需 KYC 审核，1-3 工作日）
   - 支付方式：**信用卡（Visa/Master/UnionPay）**；PayPal 也行
2. 进 Hetzner Cloud Console：https://console.hetzner.cloud
3. New Project → "brz-ytdlp-proxy"
4. Add Server:
   - Location: `Falkenstein` (fsn1)
   - Image: `Ubuntu 24.04`
   - Type: `CAX11`（ARM, 2 vCPU, 4 GB, 40 GB SSD, €3.79/mo）
   - Networking: 勾选 IPv4 + **IPv6**（默认勾选；IPv6 免费）
   - SSH key: 上传你的 `~/.ssh/id_ed25519.pub`
   - Name: `brz-ipv6-proxy-1`
5. 创建后等 30 秒，记下 IPv4 和 IPv6 主地址

### 7.3 cloud-init bootstrap (可选，自动化)
保存为 `cloud-init.yaml`：
```yaml
#cloud-config
packages:
  - python3-pip
  - python3-venv
  - git
  - ufw
  - curl
  - dnsutils
runcmd:
  # 1. 系统更新
  - apt-get update && apt-get upgrade -y
  
  # 2. 安装 TREVORproxy
  - python3 -m pip install --break-system-packages git+https://github.com/blacklanternsecurity/trevorproxy
  
  # 3. 防火墙：只允许 ssh
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw allow 22/tcp
  - echo "y" | ufw enable
  
  # 4. 启用 IPv6 转发
  - sysctl -w net.ipv6.conf.all.forwarding=1
  - echo 'net.ipv6.conf.all.forwarding=1' >> /etc/sysctl.conf
```
（在 Hetzner 创建 server 时贴进 User Data 字段）

### 7.4 手动配置（如未用 cloud-init）

```bash
# === ssh 上 VPS ===
ssh root@<VPS_IPv4>

# === 1. 系统准备 ===
apt update && apt -y upgrade
apt -y install python3-pip python3-venv git ufw curl dnsutils tmux htop
ufw default deny incoming && ufw default allow outgoing
ufw allow 22/tcp && ufw --force enable

# === 2. 查看分配到的 /64 ===
ip -6 addr show eth0
# 找到类似 2a01:4f8:c2c:abcd::1/64 的，其中 2a01:4f8:c2c:abcd::/64 就是我们的 /64
IPV6_SUBNET=$(ip -6 addr show eth0 | awk '/inet6 2/ {print $2}' | head -1 | cut -d: -f1-4)::/64
echo "Detected /64: $IPV6_SUBNET"

# === 3. 验证 YouTube IPv6 可达 ===
dig +short AAAA youtube.com
dig +short AAAA www.youtube.com
dig +short AAAA youtubei.googleapis.com
curl -6 -sI https://www.youtube.com/feed/trending | head -3
# 应该返回 HTTP/2 200 等正常响应

# === 4. 装 TREVORproxy ===
pip install --break-system-packages git+https://github.com/blacklanternsecurity/trevorproxy
which trevorproxy   # 应是 /usr/local/bin/trevorproxy

# === 5. 启动 TREVORproxy (前台测试) ===
sudo trevorproxy subnet -s "$IPV6_SUBNET" -i eth0
# 应输出：
#   [DEBUG] ip route add local 2a01:4f8:c2c:abcd::/64 dev eth0
#   [INFO]  Listening on socks5://127.0.0.1:1080

# === 6. 验证（另开 ssh 会话） ===
for i in 1 2 3 4 5; do
  curl --proxy socks5://127.0.0.1:1080 -6 -s https://api64.ipify.org
  echo
done
# 期望：5 次都是不同的 IPv6，且都在你的 /64 段内
```

### 7.5 把 TREVORproxy 变成 systemd 服务

```bash
cat > /etc/systemd/system/trevorproxy.service <<EOF
[Unit]
Description=TREVORproxy IPv6 /64 SOCKS5 rotator
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/trevorproxy -l 127.0.0.1 -p 1080 subnet -s YOUR_PREFIX/64 -i eth0
Restart=on-failure
RestartSec=10s
User=root

[Install]
WantedBy=multi-user.target
EOF

# 把 YOUR_PREFIX/64 替换成实际值
sed -i "s|YOUR_PREFIX/64|$IPV6_SUBNET|" /etc/systemd/system/trevorproxy.service

systemctl daemon-reload
systemctl enable --now trevorproxy
systemctl status trevorproxy
journalctl -u trevorproxy -f --since "1 min ago"
```

### 7.6 本机 → VPS 的链路（ssh -L）

在你 Mac 上：
```bash
# 在 ~/.ssh/config 加：
cat >> ~/.ssh/config <<EOF

Host brz-ipv6
  HostName <VPS_IPv4>
  User root
  IdentityFile ~/.ssh/id_ed25519
  LocalForward 11080 127.0.0.1:1080
  ServerAliveInterval 30
  ServerAliveCountMax 3
  ExitOnForwardFailure yes
EOF

# 用 autossh 自动重连
brew install autossh
autossh -M 0 -fN brz-ipv6

# 验证本机能用
curl --proxy socks5://127.0.0.1:11080 -6 -s https://api64.ipify.org
curl --proxy socks5://127.0.0.1:11080 -6 -s https://api64.ipify.org   # 应跟上一次不同
```

### 7.7 接入 Clash

把 `127.0.0.1:11080` 当 SOCKS5 节点接进 Clash Verge 的 GLOBAL/Proxy Provider：

#### 方案 a：直接加进 config.yaml
```yaml
proxies:
  - name: "VPS-IPv6-Rotator"
    type: socks5
    server: 127.0.0.1
    port: 11080
    udp: false
    # 注意：这个 SOCKS5 出去后是 IPv6，确保 Clash 不要再次代理

proxy-groups:
  - name: "BRZ-YTDLP"
    type: select
    proxies:
      - VPS-IPv6-Rotator
      - DIRECT
      # ... 你原本的 30 个 IPv4 节点
```

#### 方案 b：作为 LoadBalance 池中的一员
```yaml
proxy-groups:
  - name: "BRZ-YTDLP-LB"
    type: load-balance
    strategy: round-robin   # 或 consistent-hashing
    proxies:
      - VPS-IPv6-Rotator    # 单独一项，但 TREVORproxy 内部已经每 connection 换 IP
      - 你的 30 个 IPv4 节点...
```

### 7.8 brz_ytdlp 怎么用

如果你的 brz_ytdlp 当前已经走 Clash（按你描述确认），**0 代码改动**——把上面的 Clash group 设成默认即可。

可选：单独给某些任务直接走 SOCKS5（不经过 Clash）：
```python
ydl_opts = {
    'proxy': 'socks5://127.0.0.1:11080',
    # ...
}
```

或在 yt-dlp 命令行：
```bash
yt-dlp --proxy socks5://127.0.0.1:11080 ...
```

---

## 8. 成本-收益分析

### 8.1 月费成本（USD）
| 配置 | 月费 | 备注 |
|---|---|---|
| 1× Hetzner CAX11 | $4 | 起步够用 |
| 3× Hetzner CAX11 (3 个 /64) | $12 | 中阶；规避 /64 整段封 |
| 5× Hetzner CAX11 + 2× Vultr Tokyo | $30 | 最稳；地理分散 |

### 8.2 时间成本
- 注册 + 部署单台：1-2 小时（首次走流程）
- 日常运维：每月 ~30 分钟（看监控、补丁）
- 失败排查：smart-ipv6-rotator 比较脆（cron 失败静默），TREVORproxy 用 systemd 容错好得多

### 8.3 预期 e/s 提升估算
当前：单 IP 4.86 e/s（你已实测）
- token bucket 1000 req/hr/IP ≈ 0.28 req/s（这是 YouTube 给单 guest session 的硬限）
- **但你 4.86 e/s 远超 0.28**，说明你已经用 IP 池/cookie 池/burst 摊薄了

加 1 台 VPS + TREVORproxy + /64:
- 假设 YouTube 按 /64 段总量限流而非单 /128 → 单 /64 约能跑 5-15 e/s
- 叠加现有 IPv4 池 → 总 e/s 可能 +5-15
- **乐观值**：3 台 VPS 拆分 3 个 /64 → +20-40 e/s 持续

### 8.4 现实风险（重要）
**不要相信"18 quintillion IP = 18 quintillion 个 quota"**：
- YouTube 按 /64 段累积，单台 VPS 一个 /64 = 一个 quota 单位（虽然比 IPv4 单地址宽很多）
- 真正的扩容杠杆是**多台 VPS × 多个不同 /64**（地理分散更好）
- 配合 cookie pool（拿到 user session 后 quota 大幅放宽）才是真正杀手锏

---

## 9. 风险与监控

### 9.1 风险清单
| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| VPS 被 Hetzner abuse 封号 | 中 | 高（数据丢失） | 不在 VPS 存数据，只做出站代理 |
| /64 整段被 YouTube 临时屏蔽 | 中-高 | 中 | 准备 2-3 台备用 VPS，systemd 检测 ratelimit 后切换 |
| TREVORproxy 进程崩溃 | 低 | 高 | systemd Restart=on-failure，alertmanager 推 PagerDuty/Telegram |
| ssh -L 隧道断开 | 中 | 中 | autossh 自动重连；本机 cron 每分钟 health check |
| ipv4 大段被 Hetzner CSP 共享导致连坐 | 低 | 中 | 选 Hetzner FSN1 而非新数据中心 |
| 本机 Clash 配置错误把 v6 流量绕过代理 | 中 | 高（直接暴露大陆 IPv4） | DNS 强制走 fake-ip 模式，禁用 AAAA fallback |

### 9.2 监控脚本（本机 cron 每分钟）
```bash
#!/bin/bash
# /usr/local/bin/check-brz-proxy.sh
LOG=/tmp/brz-proxy.log
PROXY="socks5://127.0.0.1:11080"

# 1. SOCKS5 健康检查
IP=$(curl --max-time 8 --proxy $PROXY -6 -s https://api64.ipify.org 2>/dev/null)
if [ -z "$IP" ]; then
    echo "$(date) FAIL: socks5 no response" >> $LOG
    # 触发告警（用你已经有的 Telegram bot 或者 macOS notify）
    osascript -e 'display notification "brz proxy down" with title "BRZ ALERT"'
    # 重启 autossh
    pkill -f "autossh -M 0 -fN brz-ipv6"
    sleep 2
    autossh -M 0 -fN brz-ipv6
    exit 1
fi

# 2. 期望 IP 在 /64 段内
PREFIX="2a01:4f8:c2c:abcd"  # 替换成你的 /64 前缀
if ! echo "$IP" | grep -q "^${PREFIX}:"; then
    echo "$(date) FAIL: ip $IP not in expected /64" >> $LOG
    exit 1
fi

# 3. 期望连续两次 IP 不同（验证 rotation 工作）
IP2=$(curl --max-time 8 --proxy $PROXY -6 -s https://api64.ipify.org 2>/dev/null)
if [ "$IP" = "$IP2" ]; then
    echo "$(date) WARN: same IP twice in a row ($IP), TREVORproxy maybe stuck" >> $LOG
fi

echo "$(date) OK: $IP" >> $LOG
```

加到 crontab：
```cron
* * * * * /usr/local/bin/check-brz-proxy.sh
```

### 9.3 VPS 侧监控
```bash
# 在 VPS 上
cat > /usr/local/bin/check-trevorproxy.sh <<'EOF'
#!/bin/bash
RESP=$(curl --max-time 5 --proxy socks5://127.0.0.1:1080 -6 -s https://api64.ipify.org)
if [ -z "$RESP" ]; then
    systemctl restart trevorproxy
fi
EOF
chmod +x /usr/local/bin/check-trevorproxy.sh

# 加 cron
echo '* * * * * root /usr/local/bin/check-trevorproxy.sh' >> /etc/crontab
```

### 9.4 YouTube 风控触发响应
- HTTP 429 / sign-in required / consent.youtube.com 重定向 → 立即把当前 VPS 节点踢出 Clash group 30 分钟
- brz_ytdlp 已有 token bucket logic，加一个"per-proxy quarantine"逻辑

---

## 10. 预期最终性能 + 与其他方案对比

| 方案 | 预期 e/s 提升 | 月成本 | 实施时间 | 风险 |
|---|---|---|---|---|
| 现状（30 IPv4 节点） | 4.86 baseline | $0 (已有) | -- | -- |
| **+1 VPS + TREVORproxy /64** | **+5-10 e/s** | **+$4** | **1-2 小时** | **低** |
| +3 VPS /64 分散地理 | +15-30 e/s | +$12 | 半天 | 低 |
| +cookie pool（user session）| +30-100 e/s | $0 | 2-3 天 | 中（账号管理） |
| BFS 重排请求顺序 | +0-5 e/s | $0 | 1 天 | 低 |
| 全套（VPS + cookie + BFS）| **+50-150 e/s** | $12-30 | 1 周 | 中 |

### 跟 cookie pool 的关系
- VPS IPv6 池 = **横向扩展 IP**（解决"匿名 quota 用尽"）
- cookie pool = **纵向放宽单 IP quota**（一个 logged-in session 比 anonymous 高 10-50 倍 quota）
- **两者正交、应叠加**：cookie + VPS IPv6 = 单个 VPS 跑 50-100 e/s 不是梦

---

## 11. 实施路线图（3 阶段）

### Phase 1 (Day 1, 1-2 小时)：单台 VPS POC
- [ ] Hetzner 注册（如果还没账号；KYC 可能 1-3 天，可同时申请）
- [ ] 创建 1× CAX11 in FSN1
- [ ] 跑 `dig AAAA youtube.com` 验证 IPv6 可达
- [ ] 装 TREVORproxy + systemd
- [ ] ssh -L 接到本机
- [ ] 用 `curl --proxy socks5://127.0.0.1:11080 -6` 跑 100 次，确认 IPv6 每次不同
- [ ] brz_ytdlp 只用这一个 SOCKS5（暂时绕过 Clash）跑 1 小时，观察 e/s

### Phase 2 (Week 1)：监控 + 集成
- [ ] 本机 cron 监控脚本（9.2）
- [ ] VPS 侧 systemd 监控（9.3）
- [ ] Clash provider 接入（7.7）
- [ ] yt-dlp 端 quarantine 逻辑（9.4）
- [ ] 跑一周，统计每天 e/s、429 率、被 ban 次数

### Phase 3 (Week 2-4)：扩容 + 优化
- [ ] 第二台 VPS（不同 /64，可以同 FSN 但不同 server，最好换 NBG 或 HEL）
- [ ] 第三台（Vultr Tokyo 备份地理分散）
- [ ] Terraform / Ansible 模板化部署
- [ ] 接入 cookie pool（如果还没做）
- [ ] 复盘：哪个 /64 段被 ban 最多？哪个 location 速度最好？

---

## 12. 关键命令速查（cheat sheet）

```bash
# VPS 侧 - 一行启动
sudo trevorproxy -l 127.0.0.1 -p 1080 subnet -s $(ip -6 addr show eth0 | awk '/inet6 2/ {print $2}' | head -1 | cut -d: -f1-4)::/64 -i eth0

# 本机 - 一行接入
autossh -M 0 -fN -L 11080:127.0.0.1:1080 root@<VPS_IP>

# 本机 - 验证
for i in {1..10}; do curl --proxy socks5://127.0.0.1:11080 -6 -s https://api64.ipify.org; echo; done | sort -u | wc -l
# 期望输出 10（10 次都不同 IP）

# brz_ytdlp 一行调用
yt-dlp --proxy socks5://127.0.0.1:11080 https://www.youtube.com/@somechannel

# VPS - 清理路由（如果出问题）
ip -6 route del local YOUR_PREFIX/64 dev eth0
systemctl restart trevorproxy
```

---

## 13. 参考资料

### 工具/项目
- [iv-org/smart-ipv6-rotator](https://github.com/iv-org/smart-ipv6-rotator) - Invidious 官方 cron rotator
- [blacklanternsecurity/TREVORproxy](https://github.com/blacklanternsecurity/TREVORproxy) - **本方案核心**：subnet 模式 SOCKS5
- [blechschmidt/freebind](https://github.com/blechschmidt/freebind) - LD_PRELOAD 风格 IPv6 bind shim
- [imputnet/freebind.js](https://github.com/imputnet/freebind.js/) - Cobalt 用的 Node.js 版

### 文档
- [Invidious IPv6 Rotator Docs](https://docs.invidious.io/ipv6-rotator/) - 官方教程
- [Hetzner Cloud Locations](https://docs.hetzner.com/cloud/general/locations/) - 数据中心列表
- [Hetzner Cloud Pricing](https://www.hetzner.com/cloud/pricing/) - 价格
- [Contabo IPv6 Setup](https://help.contabo.com/en/support/solutions/articles/103000270487-how-can-i-use-ipv6-on-my-server-)
- [Vultr IPv6 Config](https://docs.vultr.com/configuring-ipv6-on-your-vps)

### 技术深度
- [Wido den Hollander: AnyIP](https://blog.widodh.nl/2016/04/anyip-bind-a-whole-subnet-to-your-linux-machine/) - AnyIP 内核机制
- [eehs: Assigning subnets with AnyIP](https://eehs.xyz/assigning-whole-ip-subnets-to-network-interfaces-with-anyip)
- [Invidious issue #3915 - YouTube blocking circumvention](https://github.com/iv-org/invidious/issues/3915)
- [Techrights: YouTube blocking Invidious + IPv6 rotation](https://techrights.org/n/2023/12/19/Google_YouTube_Still_Trying_to_Block_All_Invidious_Instances_Bu.shtml)

### 相关 yt-dlp issues
- [yt-dlp issue #12438 - source-address with IPv6](https://github.com/yt-dlp/yt-dlp/issues/12438)
- [yt-dlp issue #8631 - ipv6 + ipv4 traffic balancing](https://github.com/yt-dlp/yt-dlp/issues/8631)

---

## 14. 迭代历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-05-19 | 初版调研。核心结论：Hetzner CAX11 + TREVORproxy + ssh -L 是最快路径；smart-ipv6-rotator 太粗、不适合本任务；预期 +5-10 e/s for $4/mo。 |

### 下一步建议（给读者）
1. **立即可执行**：花 2 小时跑 Phase 1（1 台 VPS POC），用数据验证 e/s 提升
2. **2 周后回顾**：如果 Phase 1 数据好（+5+ e/s 持续），上 Phase 2-3
3. **平行做的事**：cookie pool 调研（专项 09 - 如果还没立项）
4. **不要做的事**：不要先上 3 台 VPS；不要先做 Terraform；不要先做 cookie pool 集成——这些都是 premature optimization
