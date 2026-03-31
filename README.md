# 给NAS安装浏览器
```
version: '3.8'
services:
  selenium-chrome:
    image: seleniarm/standalone-chromium:latest
    container_name: selenium-arm
    environment:
      - TZ=Asia/Shanghai  # 北京时间（定时必加）
      - SE_NODE_MAX_SESSIONS=3
    # 数据挂载到你的硬盘
    volumes:
      - /mnt/mydisk/selenium:/config
    ports:
      - 4444:4444  # 爬虫唯一接口（无界面，无HTTPS报错）
    # 防崩溃必备
    shm_size: 1gb
    restart: unless-stopped
```