#!/bin/bash

# 檢查是否存在名為'testcontainer'的容器
if sudo docker ps -a --format '{{.Names}}' | grep -Eq '^testcontainer$'; then
    # 如果存在，則先停止並刪除該容器
    sudo docker stop testcontainer
    sudo docker rm testcontainer
fi

# 檢查 testimage 是否存在
IMAGE_EXISTS=$(sudo docker images -q testimage)

# 如果映像存在，則刪除它
if [ ! -z "$IMAGE_EXISTS" ]; then
    echo "Removing existing testimage..."
    sudo docker rmi testimage
fi

# 構建新的 testimage 映像
echo "Building testimage..."
sudo docker build -t testimage .

