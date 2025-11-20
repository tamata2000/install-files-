import subprocess
from flask import Flask, request, render_template_string, send_file
import os
import datetime

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Nmap Web Scanner</title>
<style>
    body {
        font-family: Tahoma, sans-serif;
        background: #101010;
        color: #fff;
        margin: 0;
        padding: 20px;
    }
    .container {
        max-width: 900px;
        margin: auto;
        background: #1b1b1b;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 0 12px #000;
    }
    input, textarea, button {
        width: 100%;
        padding: 12px;
        margin: 8px 0;
        border-radius: 8px;
        border: none;
    }
    input, textarea {
        background: #2b2b2b;
        color: #fff;
    }
    button {
        background: #007bff;
        color: white;
        cursor: pointer;
        font-size: 18px;
        font-weight: bold;
    }
    button:hover {
        background: #0056b3;
    }
    pre {
        background: #000;
        padding: 15px;
        border-radius: 10px;
        white-space: pre-wrap;
        font-size: 15px;
    }
    .download-btn {
        background: #28a745 !important;
    }
</style>
</head>
<body>

<div class="container">
    <h2>Nmap Web Scanner</h2>
    <p>أدخل أي أمر Nmap وسوف يتم تنفيذه ويظهر الناتج بالكامل هنا.</p>

    <form method="POST">
        <label>أمر Nmap كامل:</label>
        <input type="text" name="cmd" placeholder="مثال: nmap -sV -A 192.168.1.1" required>

        <button type="submit">تشغيل Nmap</button>
    </form>

    {% if output %}
    <h3>نتيجة الفحص:</h3>
    <pre>{{ output }}</pre>

    <form method="GET" action="/download?file={{ filename }}">
        <button class="download-btn">تحميل النتيجة كملف TXT</button>
    </form>
    {% endif %}
</div>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    output = None
    filename = None

    if request.method == "POST":
        cmd = request.form.get("cmd")

        # تشغيل الأمر
        try:
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as e:
            result = e.output

        output = result

        # حفظ النتيجة كملف
        filename = f"nmap_result_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result)

    return render_template_string(HTML, output=output, filename=filename)

@app.route("/download")
def download():
    file = request.args.get("file")
    if not file or not os.path.exists(file):
        return "File not found.", 404
    return send_file(file, as_attachment=True)

if __name__ == "__main__":
    print(">> Running Nmap Web Interface on port 8080 ...")
    app.run(host="0.0.0.0", port=8080)
