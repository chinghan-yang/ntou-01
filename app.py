import multiprocessing
import subprocess
import json
import os
import sys
import glob
import cv2
import time
from gRPC import client

def run_command(command, queue, cuda_device):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(cuda_device)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
    for line in iter(process.stdout.readline, ''):
        try:
            line_encoded = line.encode('utf-8').decode('utf-8')
            json.loads(line_encoded)
            queue.put(line.strip())
        except json.JSONDecodeError:
            # 如果不是有效的 JSON，則不放入 queue
            #print(line)
            pass

    process.stdout.close()

def get_image_filename(directory, entry_count):
    # 建立檔名
    return os.path.join(directory, f"frame_{entry_count}")

def init_camera( filename, max_attempts=10, max_consecutive_failures=3 ):
    # 初始化 webcam
    cams = []
    cam_count = 0
    consecutive_failures = 0
    
    while consecutive_failures < max_consecutive_failures and cam_count < max_attempts:
        cap = cv2.VideoCapture(cam_count)
        if cap.isOpened():
            cams.append(cap)
            consecutive_failures = 0  # reset consecutive failures counter if a cam is found
        else:
            consecutive_failures += 1  # increment consecutive failures counter
        
        cam_count += 1  # try the next index

    if not cams:
        print("沒有找到攝影機")
        exit()
    
    # 建立資料夾如果不存在
    if not os.path.exists(directory):
        os.makedirs(directory)
    else:
        files = glob.glob(f"frameImage/*.jpg")
        for file in files:
            try:
                os.remove(file)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error deleting {file}. Reason: {e}")

    # 第一次抓取
    filename = get_image_filename(directory, 0)
    update_frame( cams, filename )

    return cams

def update_frame( cams, filename ):
    frames = []
    # 從 webcam 讀取一幀
    for cam in cams:
        ret, frame = cam.read()
        if ret:
            frames.append(frame)
        else:
            print("無法從某個攝影機讀取影像")
            return

    if len(cams) > 1:
        # 合併frames
        merged_frame = cv2.hconcat(frames)
        cv2.imwrite(filename + '_1.jpg', merged_frame)
        cv2.imwrite(filename + '_2.jpg', merged_frame)
        print("合併圖片已保存 " + filename)
    else:
        cv2.imwrite(filename + '_1.jpg', frames[0])
        cv2.imwrite(filename + '_2.jpg', frames[0])
        print("單圖片已保存")

def remove_previous_image(directory, current_count):
    # 指定要刪除的圖片編碼
    previous_count = current_count - 5

    # 若編碼小於0（例如第一或第二次時），直接返回
    if previous_count < 0:
        return

    # 建立要刪除的圖片檔名
    previous_filename = get_image_filename(directory, previous_count)
    if os.path.exists(previous_filename + '_1.jpg') and os.path.exists(previous_filename + '_2.jpg'):
        os.remove(previous_filename + '_1.jpg' )
        os.remove(previous_filename + '_2.jpg' )
        print(f"已刪除 '{previous_filename}'")

def terminate_and_restart_process(p, command, queue, cuda_device):
    if p.is_alive():
        p.terminate()
        p.join()
    new_p = multiprocessing.Process(target=run_command, args=(command, queue, cuda_device))
    new_p.start()
    return new_p

def terminate_process(p):
    if p.is_alive():
        p.terminate()
        p.join()

if __name__ == "__main__":
    directory = 'frameImage'
    cams = init_camera(directory)
    
    app1_command = "python3 ./detect.py --weights ./best.pt --source frameImage/frame_0_1.jpg  --output ./output"
    app2_command = "python3 ./pose-estimate.py --source frameImage/frame_0_2.jpg  --device 1"

    queue1 = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=run_command, args=(app1_command, queue1, 0))  # 使用 GPU 0
    p1.start()

    queue2 = multiprocessing.Queue()
    p2 = multiprocessing.Process(target=run_command, args=(app2_command, queue2, 1))  # 使用 GPU 1
    p2.start()

    firstTime = True
    delayBool = False
    count1 = False
    count2 = False
    condition_entry_count = 0  # 用於計算滿足條件的次數
    frameIndex = 0
    delay = 0
    start_time = time.time()

    while True:
        try:
            data_from_app1 = queue1.get_nowait()
            print("Data from app1:", data_from_app1, flush=True)
            count1 = True
        except multiprocessing.queues.Empty:
            #print( 'Q1 empty' )
            pass

        try:
            data_from_app2 = queue2.get_nowait()
            print("Data from app2:", flush=True)
            count2 = True
        except multiprocessing.queues.Empty:
            #print( 'Q2 empty' )
            pass

        if ( not firstTime and  ( ( time.time() - start_time ) * 1000 >= 15 ) ):
            delayBool = True
            delay = delay + 1
            if ( delay >= 10 ) :
                print("Restarting processes and resetting frameIndex...")
                try :
                    # 1. 終止兩個子進程
                    terminate_process(p1)
                    terminate_process(p2)
                    
                    for cam in cams:
                        cam.release()


                    # 2. 重啟整個程式
                    os.execv(sys.executable, ['python'] + sys.argv)
                except Exception as e:
                    print(f"Error Reason: {e}")

        if ( count1 and count2 ) or ( delayBool ) :
            elapsed_time = ( time.time() - start_time ) * 1000
            print(f"Time taken: {elapsed_time:.2f} milliseconds")

            if firstTime:
                firstTime = False
            app1_data_list = data_from_app1
            app2_data_list = data_from_app2
            
            camera_count = len(cams)

            # 依照攝影機數量拆分資料或保持原樣
            if camera_count > 1:
                app1_data_obj = json.loads(app1_data_list)
                app2_data_obj = json.loads(app2_data_list)
                #print( "FULL java : ", app1_data_obj )
                for idx in range(camera_count):
                    app1_data = app1_data_obj[idx] if app1_data_obj and idx < len(app1_data_obj) else []
                    app2_data = app2_data_obj[idx] if app2_data_obj and idx < len(app2_data_obj) else []

                    app1_data = json.dumps(app1_data)
                    app2_data = json.dumps(app2_data)
                    if app1_data[0] != '[' :
                       app1_data = '[' + app1_data + ']'
                    if app2_data[0] != '[' :
                        app2_data = '[' + app2_data + ']'
                    print("Calling run_client with index:", condition_entry_count, "and camera:", idx)
                    client.run_client(condition_entry_count, app1_data, app2_data, idx)
            else:
                # 只有一個攝影機但可能有多人
                # 直接傳送整個JSON
                print("Calling run_client with index:", condition_entry_count)
                client.run_client(condition_entry_count, app1_data_list, app2_data_list, 0)

            if ( count1 and count2 ) :
                count1 = False
                count2 = False

                # 清空兩個 queue
                while not queue1.empty():
                    queue1.get()

                while not queue2.empty():
                    queue2.get()

                # 更新frame
                frameIndex += 1
                filename = get_image_filename(directory, frameIndex)
                update_frame( cams, filename )
                remove_previous_image(directory, frameIndex)
                delay = 0

            start_time = time.time()
            condition_entry_count += 1
            delayBool = False
