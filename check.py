from flask import Flask, request, jsonify, render_template, session, Response, redirect, url_for
import cv2
import time

app = Flask(__name__)
app.secret_key = "1234"
started = False
lights = [[0, 1, 0], [1, 0, 0], [0, 0, 1]]
data = [[0, 0, 0]]  

VALID_USERNAME = "admin"
VALID_PASSWORD = "admin"

@app.route('/manual', methods=['POST'])
def manual_control():
    global lights
    data = request.get_json()
    lane1_color = data.get('lane1')
    lane2_color = data.get('lane2')
    lane3_color = data.get('lane3')
    
    lane_colors = {
        "red": [1, 0, 0],
        "yellow": [0, 1, 0],
        "green": [0, 0, 1]
    }
    
    lights = [
        lane_colors.get(lane1_color, [0, 0, 0]),
        lane_colors.get(lane2_color, [0, 0, 0]),
        lane_colors.get(lane3_color, [0, 0, 0])
    ]
    print("Updated lights:", lights)
    return jsonify({'lights': lights})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/start")
def start():
    global started
    started = not started
    return {"status": "started" if started else "stopped"}, 200

@app.route("/fetch")
def fetch():
    vehicle_data = {"lane1": data[0][0], "lane2": data[0][1], "lane3": data[0][2]}
    print("Vehicle data:", vehicle_data)
    return jsonify(vehicle_data)

@app.route("/fetch_lights")
def light_fetch():
    return jsonify({"lights": lights})

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
    return jsonify({"status": "Failure"}), 401

@app.route("/dash")
def control_panel():
    if "user" in session:
        return render_template("dash.html")
    return redirect(url_for("login_page"))

cap_lane1 = cv2.VideoCapture("lane1.mp4")  
cap_lane2 = cv2.VideoCapture("lane2.mp4")
cap_lane3 = cv2.VideoCapture("lane3.mp4")

def generate_video_stream(capture_device, lane):
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
    global data
    try:
        data = request.json['data']
        print("Received data:", data)
        return jsonify({"status": "Success, lights updated"}), 200
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"error": f"Error processing data: {str(e)}"}), 400

@app.route("/stream/lane1")
def stream_lane1():
    return Response(generate_video_stream(cap_lane1, "1"), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/stream/lane2")
def stream_lane2():
    return Response(generate_video_stream(cap_lane2, "2"), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/stream/lane3")
def stream_lane3():
    return Response(generate_video_stream(cap_lane3, "3"), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route('/set-lights', methods=['POST'])
def set_lights():
    global lights
    if started:
        try:
            lights_matrix = request.json['lights']
            if len(lights_matrix) != 3 or any(len(lane) != 3 for lane in lights_matrix):
                return jsonify({"error": "Invalid array format. Must be 3x3."}), 400
            lights = lights_matrix
            print("Updated light states:", lights)
            return jsonify({"status": "Success, lights updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Traffic system not started"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
