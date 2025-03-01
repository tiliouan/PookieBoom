import subprocess
import re
import threading
import socket
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder="templates")

lock = threading.Lock()
response_times = []

# Use ApacheBench for stress testing
def run_ab(target_ip, packet_count=1000, concurrency=10):  # Configure ab parameters
    global response_times
    try:
        command = ["ab", "-n", str(packet_count), "-c", str(concurrency), f"http://{target_ip}/"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Parse response times from ApacheBench output
        matches = re.findall(r"Request\s+\d+\s+completed\s+in\s+([0-9.]+)\sms", result.stdout)
        times = [float(time) for time in matches]

        if times:
            with lock:
                response_times.extend(times)
    
    except subprocess.CalledProcessError as e:
        print(f"Error executing ab: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/test", methods=["GET"])
def test_performance():
    global response_times
    target_ip = request.args.get("ip")
    if not target_ip:
        return jsonify({"status": "error", "message": "Missing target IP."})
    
    # Reset the response times list before starting a new test
    response_times.clear()

    # Start the stress test using ApacheBench
    stress_thread = threading.Thread(target=run_ab, args=(target_ip, 10000, 100))  # 10,000 requests, 100 concurrent
    stress_thread.start()
    stress_thread.join()

    if response_times:
        avg_response = sum(response_times) / len(response_times)
        return jsonify({
            "status": "success", 
            "avg_response_ms": avg_response, 
            "requests_sent": len(response_times)
        })
    else:
        return jsonify({"status": "error", "message": "No response received."})

@app.route("/lookup_ip", methods=["GET"])
def lookup_ip():
    domain = request.args.get("domain")
    if not domain:
        return jsonify({"status": "error", "message": "Missing domain."})
    
    try:
        ip_address = socket.gethostbyname(domain)
        return jsonify({"status": "success", "ip_address": ip_address})
    except socket.gaierror:
        return jsonify({"status": "error", "message": "Could not resolve domain."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)