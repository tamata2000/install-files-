#!/usr/bin/env python3
import os
import subprocess
import threading
import time
from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit

# ---------------- Configuration ----------------
HOST = "0.0.0.0"
PORT = 8080
COMMAND_TIMEOUT = 120
# ------------------------------------------------

app = Flask(__name__) # تصحيح هنا
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "change_me_later")
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- HTML / Web Terminal UI ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Web Terminal — Remote Shell</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
<style>
    :root { --bg:#0b0f12; --panel:#071018; --accent:#00d4ff; --muted:#8b98a5; --danger:#ff6b6b; }
    body{background:linear-gradient(120deg,#02111a 0%, #06131a 100%); color:#cfe8f2; font-family: "Segoe UI", Tahoma, sans-serif; margin:0; padding:20px; display:flex; justify-content:center;}
    .wrap{width:70%; min-width:700px;}
    .panel{background:var(--panel);border-radius:12px;padding:16px;box-shadow: 0 8px 30px rgba(3,10,15,0.7);}
    #terminal{ background: rgba(0,0,0,0.25); border-radius:8px; padding:14px; min-height:500px; overflow:auto; font-family: "Courier New", monospace; font-size:14px; }
    .line{padding:4px 0; white-space:pre-wrap;}
    .stdout{color:#e6f7ff;}
    .stderr{color:var(--danger);}
    .prompt{color:var(--accent); font-weight:600;}
    input[type="text"]{flex:1; padding:10px; border-radius:8px; border:none; background:#0003; color:#fff;}
    button{background:var(--accent); color:#021018; padding:10px 14px; border-radius:8px; border:none; cursor:pointer; font-weight:700;}
    button.secondary{background:transparent;color:var(--muted);border:1px solid #ffffff14;}
    .topbar{display:flex; justify-content:space-between; margin-bottom:12px;}
</style>
</head>
<body>
<div class="wrap">
    <div class="panel">
        <div class="topbar">
            <strong>Web Terminal</strong>
            <div>
                <button id="clearBtn" class="secondary">Clear</button>
                <button id="stopBtn" class="secondary" style="color:var(--danger);border-color:var(--danger);">Stop</button>
            </div>
        </div>
        <div id="terminal"></div>
        <form id="cmdForm" onsubmit="return false;" style="display:flex; gap:8px; margin-top:12px;">
            <input id="cmdInput" type="text" placeholder="Enter command..." autocomplete="off" />
            <button id="runBtn">Run</button>
        </form>
    </div>
</div>
<script>
    const socket = io({transports:['websocket']});
    const term = document.getElementById("terminal");
    const cmdInput = document.getElementById("cmdInput");
    let lastCmdId = null;

    function addLine(cls, text){
        const d = document.createElement("div");
        d.className = "line " + cls;
        d.innerText = text; // Using innerText for safety or escapeHtml logic
        term.appendChild(d);
        term.scrollTop = term.scrollHeight;
    }

    socket.on("cmd_start", data => {
        lastCmdId = data.id; // تصحيح: تحديث المعرف هنا
        addLine("prompt", `$ ${data.cmd}`);
    });
    
    socket.on("stream", data => {
        addLine(data.stream === "stderr" ? "stderr" : "stdout", data.chunk);
    });
    
    socket.on("cmd_end", data => {
        addLine("stdout", `\\n[exit code: ${data.returncode}]\\n`);
    });

    document.getElementById("cmdForm").addEventListener("submit", () => {
        const cmd = cmdInput.value.trim();
        if(!cmd) return;
        socket.emit("run_cmd", {cmd});
        cmdInput.value = "";
    });

    document.getElementById("clearBtn").onclick = () => term.innerHTML = "";
    document.getElementById("stopBtn").onclick = () => {
        if(lastCmdId) socket.emit("stop_cmd", {id:lastCmdId});
    };
</script>
</body>
</html>
"""

# ---------------- Command Runner ----------------
running = {}
running_lock = threading.Lock()
cmd_counter = 0

def gen_cmd_id():
    global cmd_counter
    with running_lock:
        cmd_counter += 1
    return f"cmd-{int(time.time())}-{cmd_counter}"

def run_and_stream(cmd, sid):
    cmd_id = gen_cmd_id()
    
    try:
        # shell=True خطير جداً أمنياً
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except Exception as e:
        socketio.emit("stream", {"id":cmd_id, "chunk":str(e), "stream":"stderr"}, to=sid)
        return

    stop_event = threading.Event()
    with running_lock:
        running[cmd_id] = {"proc":proc, "stop":stop_event}

    socketio.emit("cmd_start", {"id":cmd_id, "cmd":cmd}, to=sid)

    def reader(stream, stream_name):
        # قراءة السطور حتى ينتهي الـ stream
        for line in iter(stream.readline, ""):
            if stop_event.is_set():
                break
            socketio.emit("stream", {"id":cmd_id, "chunk":line, "stream":stream_name}, to=sid)
        stream.close()

    t1 = threading.Thread(target=reader, args=(proc.stdout, "stdout"), daemon=True)
    t2 = threading.Thread(target=reader, args=(proc.stderr, "stderr"), daemon=True)
    t1.start()
    t2.start()

    try:
        proc.wait(timeout=COMMAND_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        socketio.emit("stream", {"id":cmd_id, "chunk":f"Process timed out after {COMMAND_TIMEOUT}s\\n", "stream":"stderr"}, to=sid)
    
    socketio.emit("cmd_end", {"id":cmd_id, "returncode":proc.returncode}, to=sid)
    
    with running_lock:
        running.pop(cmd_id, None)

# ---------------- WebSocket ----------------
@socketio.on("run_cmd")
def handle_run_cmd(data):
    cmd = data.get("cmd", "").strip()
    if not cmd:
        emit("stream", {"id":"-","chunk":"No command given","stream":"stderr"})
        return
    threading.Thread(target=run_and_stream, args=(cmd, request.sid), daemon=True).start()

@socketio.on("stop_cmd")
def handle_stop_cmd(data):
    cmd_id = data.get("id")
    with running_lock:
        obj = running.get(cmd_id)
        if not obj:
            emit("stream", {"id":cmd_id, "chunk":"Not running","stream":"stderr"})
            return
        obj["stop"].set()
        obj["proc"].kill()
        emit("stream", {"id":cmd_id, "chunk":"Process killed by user","stream":"stderr"})

# ---------------- HTTP API ----------------
@app.route("/")
def index():
    return render_template_string(HTML)

# ---------------- Run ----------------
if __name__ == "__main__": # تصحيح هنا
    print(f"Server running on http://{HOST}:{PORT}")
    socketio.run(app, host=HOST, port=PORT)
