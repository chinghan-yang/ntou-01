import grpc
from gRPC import virtualmirror_v2_pb2
from gRPC import virtualmirror_v2_pb2_grpc
import json

from datetime import datetime, timezone
import re
import os
import logging

# 設定 logging
#logging.basicConfig(filename='server.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)


def get_timestamp():
    # 取得當前的時間（UTC）
    current_time = datetime.now(timezone.utc)
    
    # 格式化成 ISO 8601 字串
    timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return timestamp

def run_client( index, pose_estimated_json, skeltons_json, camera_idx ):
    # 使用環境變量 'TARGET_IP'，如果不存在則使用預設的 '172.17.0.1:30001'
    TARGET_IP = os.environ.get('TARGET_IP', '192.168.60.118:50052')
    channel = grpc.insecure_channel(TARGET_IP)
    stub = virtualmirror_v2_pb2_grpc.MirrorStub(channel)

    camera = camera_idx
    frameIndex = index
    timestamp = get_timestamp()
    skeletons_temp = skeltons_json
    #logging.debug('Skeleton: %s', skeletons_temp)
    #pose_estimated = json.dumps(pose_estimated_json)
    pose_estimated = pose_estimated_json
    # = '[{"pose": ["left_dodge"], "action_name": ["smash"]}]' 
    #pose_estimated_json
    #print( "Running Data :" )
    #print( pose_estimated )
    print( skeletons_temp )
    # 構建要傳送的 Frame 資訊
    frame = virtualmirror_v2_pb2.Frame(
        camera=camera,
        frame_index=frameIndex,
        timestamp=timestamp,
        skeleton_type="MediaPipe",
        skeletons=skeletons_temp,
        pose_estimated=pose_estimated,
        frame_raw="",
        frame_mask=""
    )
    
    Pose = virtualmirror_v2_pb2.Pose(
        camera=camera,
        frame_index=frameIndex,
        timestamp=timestamp,
        pose = "['left_dodge', 'right_dodge']"
    )
    
    Action = virtualmirror_v2_pb2.Action(
        camera=camera,
        frame_index=frameIndex,
        timestamp=timestamp,
        action = "[forehand_swing]"
    )

    #logging.debug('Skeleton: %s', frame.skeletons)

    try :
        # 呼叫遠端
        response_frame = stub.SkeletonFrame(frame)
        #response_pose = stub.PoseDetected(Pose)
        #response_action = stub.ActionDetected(Action)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run_client()

