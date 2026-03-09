from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "placement-secret-key"

jwt = JWTManager(app)

DB = "placement.db"
MODEL = "model.pkl"

# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------------- ML MODEL ---------------- #

def train_model():

    data = {
        "cgpa":[9,8,7,6,5,8.5,7.5,6.5],
        "skills":[5,4,3,2,1,4,3,2],
        "internships":[2,1,1,0,0,1,1,0],
        "projects":[3,2,2,1,1,2,1,1],
        "certifications":[3,2,1,0,0,2,1,0],
        "placed":[1,1,1,0,0,1,1,0]
    }

    df = pd.DataFrame(data)

    X = df.drop("placed", axis=1)
    y = df["placed"]

    model = LogisticRegression()
    model.fit(X, y)

    joblib.dump(model, MODEL)

if not os.path.exists(MODEL):
    train_model()

# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["POST"])
def register():

    data = request.json

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users(email,password) VALUES(?,?)",
        (data["email"], data["password"])
    )

    conn.commit()
    conn.close()

    return {"msg":"Registered Successfully"}

# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["POST"])
def login():

    data = request.json

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE email=? AND password=?",
        (data["email"], data["password"])
    )

    user = cur.fetchone()
    conn.close()

    if user:
        token = create_access_token(identity=str(user[0]))
        return {"token": token}

    return {"msg":"Invalid Login"}

# ---------------- PREDICTION ---------------- #

@app.route("/predict", methods=["POST"])
@jwt_required()
def predict():

    data = request.json

    model = joblib.load(MODEL)

    X = [[
        float(data["cgpa"]),
        int(data["skills"]),
        int(data["internships"]),
        int(data["projects"]),
        int(data["certifications"])
    ]]

    prob = model.predict_proba(X)[0][1]

    result = "Eligible" if prob > 0.5 else "Not Eligible"

    return {
        "result": result,
        "probability": round(prob*100,2)
    }

# ---------------- FRONTEND ---------------- #

html = """

<h2>Campus Placement Prediction System</h2>

<h3>Register</h3>

<input id="email" placeholder="Email"><br><br>
<input id="pass" placeholder="Password"><br><br>

<button onclick="register()">Register</button>

<h3>Login</h3>

<button onclick="login()">Login</button>

<h3>Prediction</h3>

<input id="cgpa" placeholder="CGPA"><br><br>
<input id="skills" placeholder="Skills"><br><br>
<input id="internships" placeholder="Internships"><br><br>
<input id="projects" placeholder="Projects"><br><br>
<input id="certifications" placeholder="Certifications"><br><br>

<button onclick="predict()">Predict</button>

<pre id="result"></pre>

<script>

let token=""

function register(){

fetch("/register",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
email:email.value,
password:pass.value
})
})

alert("Registered")
}

function login(){

fetch("/login",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
email:email.value,
password:pass.value
})
})
.then(r=>r.json())
.then(d=>{
token=d.token
alert("Login Successful")
})

}

function predict(){

fetch("/predict",{
method:"POST",
headers:{
"Content-Type":"application/json",
"Authorization":"Bearer "+token
},
body:JSON.stringify({
cgpa:cgpa.value,
skills:skills.value,
internships:internships.value,
projects:projects.value,
certifications:certifications.value
})
})
.then(r=>r.json())
.then(d=>{
result.innerText=JSON.stringify(d,null,2)
})

}

</script>

"""

@app.route("/")
def home():
    return render_template_string(html)

# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    init_db()
    app.run(debug=True)