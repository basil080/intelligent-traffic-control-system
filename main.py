from flask import Flask, request, jsonify, render_template, session, Response,redirect,url_for
import cv2
import time

app = Flask(__name__)
app.secret_key = "1234"
started=False
lights=[[0,1,0],[1,0,0],[0,0,1]]
data = [
    [0, 0, 0] 
]
lanes = {
    'lane1': {'red': 14, 'yellow': 15, 'green': 26},
    'lane2': {'red': 23, 'yellow': 24, 'green': 25},
    'lane3': {'red': 5, 'yellow': 6, 'green': 13},
}

VALID_USERNAME = "admin"
VALID_PASSWORD = "admin"

COLOR_RGB = {
    "red": [255, 0, 0],      
    "yellow": [255, 255, 0], 
    "green": [0, 255, 0],    
}

@app.route('/manual', methods=['POST'])
def manual_control():
    data = request.get_json()
    global lights
    global started
    lane1_color = data.get('lane1')
    lane2_color = data.get('lane2')
    lane3_color = data.get('lane3')
    l=[]
    if lane1_color=="red":
        lane1=[1,0,0]
    if lane1_color=="yellow":
        lane1=[0,1,0]
    if lane1_color=="green":
        lane1=[0,0,1]
    if lane2_color=="red":
        lane2=[1,0,0]
    if lane2_color=="yellow":
        lane2=[0,1,0]
    if lane2_color=="green":
        lane2=[0,0,1]
    if lane3_color=="red":
        lane3=[1,0,0]
    if lane3_color=="yellow":
        lane1=[0,1,0]
    if lane3_color=="green":
        lane3=[0,0,1]
    l.append(lane1)
    l.append(lane2)
    l.append(lane3)
    lights=l
    print(lights)
    set_lights()
    return jsonify({'lights': lights})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))
@app.route("/start")
def start():
    global started
    if not started:
        started=True
        return {"status":"started"},200
    else:
        started=False
        return {"status":"stopped"},200

@app.route("/fetch")
def fetch():
    global data
    
    vehicle_data = {
        "lane1": data[0][0],  
        "lane2": data[0][1],  
        "lane3":data[0][2] 
    }
    print(vehicle_data)
    return jsonify(vehicle_data)
@app.route("/fetch_lights")
def light_fetch():
    global lights
    
    light_data = {
        "lane1": lights
    }
    return jsonify(light_data)
@app.route("/")
def login_page():
    return render_template("index.html")

@app.route("/validate-login", methods=["POST"])
def validate_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        session["user"] = "admin"
        return jsonify({"status": "Success"}), 200
    else:
        return jsonify({"status": "Failure"}), 401

@app.route("/dash")
def control_panel():
    if "user" in session:
        return render_template("dash.html")

cap_lane1 = cv2.VideoCapture("lane1.mp4")  
cap_lane2 = cv2.VideoCapture("lane2.mp4")
cap_lane3 = cv2.VideoCapture("lane3.mp4")

def generate_video_stream(capture_device, lane):
    """Function to generate video stream from a video capture device (OpenCV)"""
    while True:
        ret, frame = capture_device.read()
        
        if not ret:
            capture_device.set(cv2.CAP_PROP_POS_FRAMES, 0)  
            ret, frame = capture_device.read()  

        if not ret:
            print(f"Error reading video for Lane {lane}")
            break
        time.sleep(0.5)
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            print(f"Error encoding frame for Lane {lane}")
            break

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')


@app.route('/data', methods=['POST'])
def handle_data():
    try:
        global data
        data = request.json['data']
        print("Received data:", data)
        

        return jsonify({"status": "Success, lights updated"}), 200
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"error": f"Error processing data: {str(e)}"}), 400

@app.route("/stream/lane1")
def stream_lane1():
    """Video stream for lane 1"""
    return Response(generate_video_stream(cap_lane1,"1"),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/stream/lane2")
def stream_lane2():
    """Video stream for lane 2"""
    return Response(generate_video_stream(cap_lane2,"2"),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/stream/lane3")
def stream_lane3():
    """Video stream for lane 3"""
    return Response(generate_video_stream(cap_lane3,"3"),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

import RPi.GPIO as GPIO
import time


GPIO.setmode(GPIO.BCM)

@app.route("/")
def login():
    return render_template("index.html")


for lane in lanes.values():
    for color, pin in lane.items():
        GPIO.setup(pin, GPIO.OUT)

def control_lights(lights_matrix):
    for lane_idx, lane_state in enumerate(lights_matrix):
        lane_name = f'lane{lane_idx + 1}'
        lane_pins = lanes[lane_name]

        GPIO.output(lane_pins['red'], lane_state[0])
        GPIO.output(lane_pins['yellow'], lane_state[1])
        GPIO.output(lane_pins['green'], lane_state[2])

@app.route('/set-lights', methods=['POST'])
def set_lights():
    if started==True:
        try:
            lights_matrix = request.json['lights']
            global lights
            lights=lights_matrix
            
            if len(lights_matrix) != 3 or any(len(lane) != 3 for lane in lights_matrix):
                return jsonify({"error": "Invalid array format. Must be 3x3."}), 400
            
            control_lights(lights_matrix)
            
            return jsonify({"status": "Success, lights updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return "pode",500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)
