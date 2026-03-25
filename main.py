from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import uuid
from fastapi import Form, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="super_secret_admin_key_123"
)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "demon123"

# ---------------- DATABASE ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["complaint_db"]
collection = db["complaints"]

# ---------------- MODEL ----------------
class Complaint(BaseModel):
    text: str

# ---------------- AI LOGIC ----------------

def categorize(text):
    text = text.lower()
    if "water" in text or "leak" in text:
        return "Infrastructure"
    elif "wifi" in text or "internet" in text:
        return "IT"
    elif "electric" in text or "light" in text:
        return "Electrical"
    return "General"

def detect_priority(text):
    text = text.lower()
    if "urgent" in text or "fire" in text:
        return "High"
    return "Normal"

def sentiment_boost(text, current_priority):
    negative_words = ["angry", "worst", "frustrated", "not solved"]
    for word in negative_words:
        if word in text.lower():
            return "High"
    return current_priority

def assign_department(category):
    if category == "Infrastructure":
        return "Water Department"
    elif category == "Electrical":
        return "Electrical Department"
    elif category == "IT":
        return "IT Department"
    return "General Administration"

def check_duplicate(new_text):
    complaints = list(collection.find({}, {"text": 1}))
    if not complaints:
        return False

    texts = [c["text"] for c in complaints]
    texts.append(new_text)

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(texts)
    similarity_matrix = cosine_similarity(tfidf[-1], tfidf[:-1])
    similarity_score = float(similarity_matrix.max())

    return similarity_score > 0.8

# ---------------- SUBMIT ROUTE ----------------

@app.post("/submit/")
def submit_complaint(complaint: Complaint):

    category = categorize(complaint.text)
    priority = detect_priority(complaint.text)
    priority = sentiment_boost(complaint.text, priority)
    duplicate = check_duplicate(complaint.text)
    department = assign_department(category)

    complaint_id = str(uuid.uuid4())

    collection.insert_one({
        "complaint_id": complaint_id,
        "text": complaint.text,
        "category": category,
        "priority": priority,
        "duplicate": duplicate,
        "department": department,
        "status": "Pending",
        "created_at": datetime.utcnow(),
        "resolved_at": None
    })

    return {
        "complaint_id": complaint_id,
        "category": category,
        "priority": priority,
        "duplicate": duplicate,
        "department": department
    }

# ---------------- GET ALL ----------------

@app.get("/complaints/")
def get_complaints():
    return list(collection.find({}, {"_id": 0}))

# ---------------- UPDATE STATUS ----------------

@app.put("/update-status/{complaint_id}")
def update_status(complaint_id: str, status: str):

    update_data = {"status": status}

    if status == "Resolved":
        update_data["resolved_at"] = datetime.utcnow()

    collection.update_one(
        {"complaint_id": complaint_id},
        {"$set": update_data}
    )

    return {"message": "Updated"}

# ======================================================
# ================= USER UI =============================
# ======================================================

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>Smart AI Complaint System</title>
        <style>
            body {
                margin: 0;
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                color: white;
                overflow: hidden;
            }

            /* ---------------- INTRO OVERLAY ---------------- */
            #intro {
                position: fixed;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, #000814, #001d3d);
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                z-index: 9999;
                animation: fadeOut 1.5s ease forwards;
                animation-delay: 2.5s;
            }

            #intro h1 {
                font-size: 40px;
                color: #00bfff;
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0% { transform: scale(1); opacity: 0.8; }
                50% { transform: scale(1.1); opacity: 1; }
                100% { transform: scale(1); opacity: 0.8; }
            }

            @keyframes fadeOut {
                to { opacity: 0; visibility: hidden; }
            }

            /* ---------------- MAIN CARD ---------------- */
            .card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                padding: 40px;
                width: 500px;
                border-radius: 20px;
                box-shadow: 0 0 30px rgba(0,150,255,0.6);
                text-align: center;
                transition: 0.3s ease;
            }

            h1 {
                margin-bottom: 20px;
                font-weight: 600;
            }

            textarea {
                width: 100%;
                height: 100px;
                padding: 12px;
                border-radius: 12px;
                border: none;
                resize: none;
                font-size: 14px;
                outline: none;
                margin-bottom: 15px;
            }

            button {
                width: 100%;
                padding: 12px;
                border-radius: 12px;
                border: none;
                font-size: 16px;
                font-weight: bold;
                background: linear-gradient(to right, #00c6ff, #0072ff);
                color: white;
                cursor: pointer;
                margin-top: 10px;
                transition: 0.3s ease;
            }

            button:hover {
                transform: scale(1.05);
                box-shadow: 0 0 20px #00c6ff;
            }

            .secondary-btn {
                background: linear-gradient(to right, #1f4037, #99f2c8);
            }

            .admin-btn {
                background: linear-gradient(to right, #001f33, #00bfff);
            }

            .result {
                margin-top: 20px;
                padding: 20px;
                background: rgba(255,255,255,0.15);
                border-radius: 12px;
                text-align: left;
                display: none;
            }

            .badge {
                padding: 5px 10px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }

            .high { background-color: #ff4d4d; }
            .normal { background-color: #28a745; }
            .duplicate { background-color: #ffc107; color: black; }

        </style>
    </head>

    <body>

        <!-- INTRO SCREEN -->
        <div id="intro">
            <h1>💙 Initializing AI Complaint System...</h1>
        </div>

        <!-- MAIN UI -->
        <div class="card">
            <h1>💙 Smart AI Complaint System</h1>

            <textarea id="complaintText" placeholder="Describe your issue..."></textarea>
            <button onclick="submitComplaint()">Submit Complaint</button>

            <div class="result" id="result"></div>

            <button id="nextBtn" class="secondary-btn" 
                    style="display:none;" 
                    onclick="nextComplaint()">
                ➕ Submit Another Complaint
            </button>

            <button class="admin-btn" onclick="confirmAdmin()">
                🔐 Admin Dashboard
            </button>
        </div>

        <script>

            async function submitComplaint() {
                const text = document.getElementById("complaintText").value;

                if (!text) {
                    alert("Please enter a complaint!");
                    return;
                }

                const response = await fetch("/submit/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text: text })
                });

                const data = await response.json();

                let priorityClass = data.priority === "High" ? "high" : "normal";
                let duplicateBadge = data.duplicate 
                    ? '<span class="badge duplicate">Duplicate</span><br><br>' 
                    : '';

                document.getElementById("result").innerHTML =
                    "<b>Complaint ID:</b> " + data.complaint_id + "<br><br>" +
                    "<b>Category:</b> " + data.category + "<br><br>" +
                    "<b>Department:</b> " + data.department + "<br><br>" +
                    "<b>Priority:</b> <span class='badge " + priorityClass + "'>" 
                    + data.priority + "</span><br><br>" +
                    duplicateBadge;

                document.getElementById("result").style.display = "block";
                document.getElementById("nextBtn").style.display = "block";
                document.getElementById("complaintText").disabled = true;
            }

            function nextComplaint() {
                document.getElementById("complaintText").value = "";
                document.getElementById("complaintText").disabled = false;
                document.getElementById("result").style.display = "none";
                document.getElementById("nextBtn").style.display = "none";
            }

            function confirmAdmin() {
                let confirmAccess = confirm("Are you sure you want to enter Admin Dashboard?");
                if(confirmAccess){
                    window.location.href = "/admin";
                }
            }

        </script>

    </body>
    </html>
    """

# login:

@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page():
    return """
    <html>
    <head>
        <title>Admin Login</title>
        <style>
            body {
                background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
                font-family:sans-serif;
                color:white;
            }
            .box {
                background:rgba(255,255,255,0.1);
                padding:40px;
                border-radius:20px;
                backdrop-filter:blur(15px);
                box-shadow:0 0 25px #00c6ff;
            }
            input {
                display:block;
                width:100%;
                margin-bottom:15px;
                padding:10px;
                border-radius:10px;
                border:none;
            }
            button {
                width:100%;
                padding:10px;
                border:none;
                border-radius:10px;
                background:linear-gradient(to right,#00c6ff,#0072ff);
                color:white;
                font-weight:bold;
                cursor:pointer;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>💙 Admin Login</h2>
            <form method="post" action="/admin-login">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/admin-login")
def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse("/admin", status_code=302)
    return HTMLResponse("<h3>Invalid Credentials</h3>")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin-login", status_code=302)



# ======================================================
# ================= ADMIN UI ===========================
# ======================================================

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):

    # ✅ Proper session check
    if request.session.get("admin") != True:
        return RedirectResponse(url="/admin-login", status_code=302)

    return """
    <html>
    <head>
    <title>Blue AI Admin Panel</title>
    <style>
        body {
            background:#000814;
            color:white;
            font-family:sans-serif;
            padding:20px;
        }

        .topbar {
            display:flex;
            justify-content:space-between;
            align-items:center;
        }

        h1 { color:#00bfff; }

        .logout-btn {
            padding:8px 15px;
            border:none;
            border-radius:8px;
            background:#ff4d4d;
            color:white;
            cursor:pointer;
        }

        .logout-btn:hover {
            background:#cc0000;
        }

        select {
            padding:5px;
            margin:5px;
            background:#001f33;
            color:white;
            border:1px solid #00bfff;
        }

        table {
            width:100%;
            margin-top:20px;
            border-collapse:collapse;
        }

        th,td {
            padding:10px;
            border-bottom:1px solid #00bfff;
            text-align:center;
        }

        th { background:#001f33; }
    </style>
    </head>

    <body>

    <div class="topbar">
        <h1>💙 Complaint Management System Admin Dashboard</h1>
        <button class="logout-btn" onclick="logout()">🔒 Logout</button>
    </div>

    <br>

    <label>Department:</label>
    <select id="dept" onchange="applyFilter()">
        <option value="All">All</option>
        <option value="Water Department">Water</option>
        <option value="Electrical Department">Electrical</option>
        <option value="IT Department">IT</option>
        <option value="General Administration">General</option>
    </select>

    <label>Priority:</label>
    <select id="priority" onchange="applyFilter()">
        <option value="All">All</option>
        <option value="High">High</option>
        <option value="Normal">Normal</option>
    </select>

    <label>Status:</label>
    <select id="status" onchange="applyFilter()">
        <option value="All">All</option>
        <option value="Pending">Pending</option>
        <option value="In Progress">In Progress</option>
        <option value="Resolved">Resolved</option>
    </select>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Department</th>
                <th>Status</th>
                <th>Resolution(sec)</th>
            </tr>
        </thead>
        <tbody id="tableBody"></tbody>
    </table>

    <script>
    let allData = [];

    async function loadData(){
        const res = await fetch("/complaints/");
        allData = await res.json();
        applyFilter();
    }

    function applyFilter(){
        const dept = document.getElementById("dept").value;
        const priority = document.getElementById("priority").value;
        const status = document.getElementById("status").value;

        const filtered = allData.filter(item=>{
            if(dept !== "All" && item.department !== dept) return false;
            if(priority !== "All" && item.priority !== priority) return false;
            if(status !== "All" && item.status !== status) return false;
            return true;
        });

        renderTable(filtered);
    }

    function renderTable(data){
        const body = document.getElementById("tableBody");
        body.innerHTML = "";

        data.forEach(item=>{
            let resolution = "-";

            if(item.resolution_time_sec){
                resolution = item.resolution_time_sec;
            }

            body.innerHTML += `
                <tr>
                    <td>${item.complaint_id}</td>
                    <td>${item.category}</td>
                    <td>${item.priority}</td>
                    <td>${item.department}</td>
                    <td>
                        <select onchange="updateStatus('${item.complaint_id}', this.value)">
                            <option ${item.status=="Pending"?"selected":""}>Pending</option>
                            <option ${item.status=="In Progress"?"selected":""}>In Progress</option>
                            <option ${item.status=="Resolved"?"selected":""}>Resolved</option>
                        </select>
                    </td>
                    <td>${resolution}</td>
                </tr>
            `;
        });
    }

    async function updateStatus(id,status){
        await fetch(`/update-status/${id}?status=${status}`,{
            method:"PUT"
        });
        loadData();
    }

    function logout(){
        window.location.href = "/logout";
    }

    loadData();
    </script>

    </body>
    </html>
    """