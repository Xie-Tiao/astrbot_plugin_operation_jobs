# 给NAS安装浏览器
```
version: '3'
services:
  selenium-chrome:
    image: seleniarm/standalone-chromium:latest
    container_name: selenium-arm
    environment:
      - TZ=Asia/Shanghai
      # 限制并发为 1
      - SE_NODE_MAX_SESSIONS=1
      # 显式限制 Java 堆内存，防止 Java 进程直接吃掉所有内存导致被系统杀掉
      # 限制 Java 只用 300MB 内存，给 Chromium 留出空间
      - SE_JAVA_OPTS=-Xmx300m -Xms200m 
      # 暂时去掉这个，有时它会导致配置解析错误
      # - SE_LOG_LEVEL=ERROR 
    volumes:
      - /mnt/mydisk/selenium:/config
    ports:
      - 4444:4444
    # 将 shm 稍微调大到 512mb，256mb 对某些复杂的渲染可能不够
    shm_size: 512mb
    deploy:
      resources:
        limits:
          memory: 1G  # 稍微放宽到 1G，Java + Chromium 启动瞬间压力很大
    restart: unless-stopped
```