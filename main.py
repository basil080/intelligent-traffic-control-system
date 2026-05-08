import time
import requests
import pandas as pd
import cv2
from ultralytics import YOLO  

url = 'http://127.0.0.1:5000/'

vehicle_model = YOLO('yolov8s.pt')  
ambulance_model = YOLO('emergency.pt')  

def find_and_count_vehicles(frame, lane_number):
    vehicle_results = vehicle_model(frame)
    ambulance_results = ambulance_model(frame)

    vehicle_boxes = vehicle_results[0].boxes
    ambulance_boxes = ambulance_results[0].boxes

    vehicle_classes = [2, 3, 5, 7, 8]  
    confidence_threshold_vehicle = 0.50
    confidence_threshold_ambulance = 0.80  

    df_vehicles = pd.DataFrame({
        "confidence": vehicle_boxes.conf.cpu().numpy(),
        "class": vehicle_boxes.cls.cpu().numpy(),
        "xmin": vehicle_boxes.xywh[:, 0].cpu().numpy(),
        "ymin": vehicle_boxes.xywh[:, 1].cpu().numpy(),
        "xmax": vehicle_boxes.xywh[:, 2].cpu().numpy(),
        "ymax": vehicle_boxes.xywh[:, 3].cpu().numpy()
    })

    df_ambulances = pd.DataFrame({
        "confidence": ambulance_boxes.conf.cpu().numpy(),
        "class": ambulance_boxes.cls.cpu().numpy(),
        "xmin": ambulance_boxes.xywh[:, 0].cpu().numpy(),
        "ymin": ambulance_boxes.xywh[:, 1].cpu().numpy(),
        "xmax": ambulance_boxes.xywh[:, 2].cpu().numpy(),
        "ymax": ambulance_boxes.xywh[:, 3].cpu().numpy()
    })

    filtered_vehicles = df_vehicles[(df_vehicles['confidence'] >= confidence_threshold_vehicle) & 
                                    (df_vehicles['class'].isin(vehicle_classes))]
    
    ambulance_detected = not df_ambulances[df_ambulances['confidence'] >= confidence_threshold_ambulance].empty  

    print(f"Lane {lane_number} detected vehicles: {filtered_vehicles.shape[0]}")  
    if ambulance_detected:
        print("Ambulance detected in Lane {lane_number}! ")

    return len(filtered_vehicles), ambulance_detected


def rotate_lights(lights_config):
    updated_config = []
    for lane in lights_config:
        if lane == [0, 0, 1]:
            updated_config.append([1, 0, 0])  
        elif lane == [0, 1, 0]:
            updated_config.append([0, 0, 1])  
        elif lane == [1, 0, 0]:
            updated_config.append([0, 1, 0])  
        else:
            updated_config.append(lane)
    return updated_config


def set_lights(light_config):
    try:
        lights_data = {"lights": light_config}
        response = requests.post(url+"set-lights", json=lights_data)

        if response.status_code == 200:
            print("\n🚦 Lights set successfully! Current status:")
            for i, lane in enumerate(light_config, start=1):
                status = "🟢 Green" if lane == [0, 0, 1] else "🟡 Yellow" if lane == [0, 1, 0] else "🔴 Red"
                print(f"Lane {i}: {status}")
        else:
            print("Failed to set lights:", response.status_code, response.json())
    except:
        print("Set light failed:")
        return 


def control_traffic():
    lane_videos = [cv2.VideoCapture(url+"/stream/lane1"),  
                   cv2.VideoCapture(url+"/stream/lane2"),
                   cv2.VideoCapture(url+"/stream/lane3")]
    
    while True:
        lane_counts = [0, 0, 0]
        ambulance_detected = [False, False, False]
        
        lane_frames = []
        for cap in lane_videos:
            ret, frame = cap.read()
            if not ret:
                print("End of video feed or error reading frames.")
                return
            lane_frames.append(frame)
        
        time.sleep(2)
        for i in range(3):
            lane_counts[i], ambulance_detected[i] = find_and_count_vehicles(lane_frames[i], i+1)
        
        if any(ambulance_detected):  
            ambulance_lane = ambulance_detected.index(True)
            sorted_lanes = sorted([i for i in range(3) if i != ambulance_lane], key=lambda i: lane_counts[i], reverse=True)
            next_lights_config = [[0, 0, 0] for _ in range(3)]
            next_lights_config[ambulance_lane] = [0, 0, 1]  
            next_lights_config[sorted_lanes[0]] = [0, 1, 0]  
            next_lights_config[sorted_lanes[1]] = [1, 0, 0]  
            
            print("Giving emergency priority for 15 seconds...")
            set_lights(next_lights_config)
            time.sleep(15)  

        else:
            sorted_lanes = sorted(range(3), key=lambda i: lane_counts[i], reverse=True)
            next_lights_config = [[0, 0, 0] for _ in range(3)]
            next_lights_config[sorted_lanes[0]] = [0, 0, 1]  
            next_lights_config[sorted_lanes[1]] = [0, 1, 0]  
            next_lights_config[sorted_lanes[2]] = [1, 0, 0]  

        print("Starting rotation cycle...")
        set_lights(next_lights_config)
        time.sleep(3)

        for _ in range(3):
            lane_frames = [cap.read()[1] for cap in lane_videos if cap.isOpened()]

            ambulance_detected_during_rotation = [find_and_count_vehicles(lane_frames[i], i+1)[1] for i in range(3)]
            
            if any(ambulance_detected_during_rotation):
                print("New ambulance detected during rotation! Immediately switching lights.")
                ambulance_lane = ambulance_detected_during_rotation.index(True)
                next_lights_config = [[0, 0, 0] for _ in range(3)]
                next_lights_config[ambulance_lane] = [0, 0, 1]  
                set_lights(next_lights_config)
                time.sleep(15)  
                break  

            next_lights_config = rotate_lights(next_lights_config)
            print("Rotating lights...")
            set_lights(next_lights_config)
            time.sleep(10)  

    
    for cap in lane_videos:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    control_traffic()
