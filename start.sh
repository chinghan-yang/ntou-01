#!/bin/bash

# 檢查是否存在名為'testcontainer'的容器
if sudo docker ps -a --format '{{.Names}}' | grep -Eq '^testcontainer$'; then
    # 如果存在，則先停止並刪除該容器
    sudo docker stop testcontainer
    sudo docker rm testcontainer
fi

# 運行新的容器
sudo docker run -e TARGET_IP='192.168.60.118:50052' \
           --name testcontainer \
           --gpus all \
           --device /dev/video0:/dev/video0 \
           --device /dev/video2:/dev/video1 \
           -it testimage

