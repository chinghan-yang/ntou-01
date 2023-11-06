# 使用 Python 官方提供的 Python 映像檔作為基礎
FROM python:3.8

# 安裝必要的函式庫
# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# 複製專案目錄到容器內的 /app 資料夾
COPY . /app

# 設定工作目錄
WORKDIR /app

# 安裝所需的套件
RUN pip install --upgrade pip
RUN pip install --default-timeout=600 --retries=1 -r requirements.txt

# 開啟應用程式
CMD ["python", "main.py"]
