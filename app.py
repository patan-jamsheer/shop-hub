from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
import hashlib
import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

app = Flask(__name__)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
print("SID:", TWILIO_ACCOUNT_SID)
print("TOKEN:", TWILIO_AUTH_TOKEN)


TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
TWILIO_API_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"

app.secret_key = "supersecretkey123"

# ---------- OLX MAIN DATABASE ----------
db = mysql.connector.connect(
    host=os.environ.get("MYSQL_HOST"),
    user=os.environ.get("MYSQL_USER"),
    password=os.environ.get("MYSQL_PASSWORD"),
    database=os.environ.get("MYSQL_DB")
)

# ---------- CHATBOT DATABASE ----------
db_chat = mysql.connector.connect(
    host=os.environ.get("MYSQL_HOST"),
    user=os.environ.get("MYSQL_USER"),
    password=os.environ.get("MYSQL_PASSWORD"),
    database=os.environ.get("MYSQL_DB")
)

# ---------- Auth Page ----------
@app.route("/")
def auth_page():
    return render_template("auth.html")


# ---------- Main Page ----------
@app.route("/main")
def main_page():
    if "user_id" not in session:
        return redirect(url_for("auth_page"))
    user_name = session.get("user_name")
    user_id = session.get("user_id")
    return render_template("main.html", user_name=user_name, user_id=user_id)

# ---------- Signup API ----------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password_raw = data.get("password")
    city = data.get("city")
    state = data.get("state")
    country = data.get("country")
    address = data.get("address")

    if not all([name, email, phone, password_raw]):
        return jsonify({"message": "All fields required"}), 400

    password = hashlib.sha256(password_raw.encode()).hexdigest()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO users (name,email,phone,password,city,state,country,address)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (name,email,phone,password,city,state,country,address))
        db.commit()
        return jsonify({"message": "Account created successfully!"}), 200
    except mysql.connector.errors.IntegrityError:
        return jsonify({"message": "Email already exists"}), 409

# ---------- Login API ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email")
    password_raw = data.get("password")

    if not all([email, password_raw]):
        return jsonify({"message": "All fields required"}), 400

    password = hashlib.sha256(password_raw.encode()).hexdigest()
    cur = db.cursor()
    cur.execute("SELECT id,name FROM users WHERE email=%s AND password=%s", (email,password))
    user = cur.fetchone()

    if user:
        session["user_id"] = user[0]
        session["user_name"] = user[1]
        return jsonify({"message": "Login successful", "redirect": "/main"}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401

# ---------- Logout ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth_page"))
import ollama

# ---------- Chatbot API ----------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(force=True)
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"response": "🤖 Please type something!"})

    try:
        response = ollama.chat(
            model="phi3:mini",   # fast model
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ShopHub AI assistant. "
                        "patan jamsheer is the owner of shophub"
                        "Help users with buying, selling, products, cart, and general questions. "
                        "Be friendly and concise."
                    )
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ]
        )

        reply = response["message"]["content"].strip()
        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({"response": f"🤖 AI Error: {str(e)}"})

import os
from werkzeug.utils import secure_filename

# ---------- Config ----------
UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- Post Product API ----------
# ---------- Post Product API ----------
@app.route("/post_product", methods=["POST"])
def post_product():
    if "user_id" not in session:
        return jsonify({"message":"Login required"}), 401

    name = request.form.get("name")
    category = request.form.get("category")
    price = request.form.get("price")
    description = request.form.get("description")
    image_file = request.files.get("image")

    if not all([name, category, price]):
        return jsonify({"message":"Name, category, and price are required"}), 400

    image_filename = None
    if image_file and image_file.filename != "":
        result = cloudinary.uploader.upload(image_file)
        image_filename = result["secure_url"]

    cur = db.cursor()
    cur.execute(
        "INSERT INTO products (name, category, price, description, image, seller_id) VALUES (%s,%s,%s,%s,%s,%s)",
        (name, category, price, description, image_filename, session["user_id"])
    )
    db.commit()

    return jsonify({"message":"Product posted successfully!"}), 200
@app.route("/post_product_page")
def post_product_page():
    if "user_id" not in session:
        return redirect(url_for("auth_page"))
    return render_template("post_product.html")
# ---------- Get Products API ----------
@app.route("/get_products")
def get_products():
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT 
    p.id, p.name, p.category, p.price, p.image,
    p.status,

            u.id AS seller_id,
            u.name AS seller_name,
            u.phone AS seller_phone,
            u.city, u.state
        FROM products p
JOIN users u ON p.seller_id = u.id
WHERE p.is_visible = 1
ORDER BY p.id DESC

    """)
    products = cur.fetchall()

    for p in products:
        p["price"] = float(p["price"])
        p["is_owner"] = (p["seller_id"] == session.get("user_id"))

    return jsonify(products)



@app.route("/seller/<int:seller_id>")
def seller_profile(seller_id):
    cur = db.cursor(dictionary=True)

    # Seller details
    cur.execute("""
        SELECT name, phone, city, state, country
        FROM users WHERE id=%s
    """, (seller_id,))
    seller = cur.fetchone()

    # Seller products
    cur.execute("""
        SELECT id, name, price, image
        FROM products
        WHERE seller_id=%s
        ORDER BY id DESC
    """, (seller_id,))
    products = cur.fetchall()

    return render_template(
        "seller_profile.html",
        seller=seller,
        products=products
    )

@app.route("/product/<int:product_id>")
def product_details(product_id):
    cur = db.cursor(dictionary=True)
    
    # Get product + seller info
    cur.execute("""
        SELECT p.id, p.name, p.category, p.price, p.description, p.image,
               u.id AS seller_id, u.name AS seller_name, u.phone AS seller_phone,
               u.city, u.state, u.country
        FROM products p
        JOIN users u ON p.seller_id = u.id
        WHERE p.id = %s
    """, (product_id,))
    
    product = cur.fetchone()
    if not product:
        return "Product not found", 404
    
    # Optional: fetch similar products (same category, excluding this one)
    cur.execute("""
        SELECT id, name, price, image 
        FROM products 
        WHERE category=%s AND id!=%s 
        ORDER BY id DESC LIMIT 4
    """, (product["category"], product_id))
    similar = cur.fetchall()
    
    return render_template("product_details.html", product=product, similar=similar)
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    if "user_id" not in session:
        return jsonify({"message": "Login required"}), 401

    data = request.get_json()
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE quantity=quantity+%s",
            (session["user_id"], product_id, quantity, quantity)
        )
        db.commit()
        return jsonify({"message": "Added to cart successfully"}), 200
    except Exception as e:
        print(e)
        return jsonify({"message": "Error adding to cart"}), 500
@app.route("/get_cart")
def get_cart():
    if "user_id" not in session:
        return jsonify([])

    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT c.id AS cart_id, c.quantity, p.id AS product_id, p.name, p.price, p.image
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id=%s
    """, (session["user_id"],))
    items = cur.fetchall()
    for i in items:
        i["price"] = float(i["price"])
    return jsonify(items)
@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    if "user_id" not in session:
        return jsonify({"message":"Login required"}), 401

    data = request.get_json()
    cart_id = data.get("cart_id")
    cur = db.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, session["user_id"]))
    db.commit()
    return jsonify({"message":"Removed from cart"})
# ---------- Cart Page ----------
@app.route("/cart_page")
def cart_page():
    if "user_id" not in session:
        return redirect(url_for("auth_page"))
    return render_template("cart.html")  # We'll create cart.html next
import os
import requests
from requests.auth import HTTPBasicAuth
@app.route("/send_interested_message", methods=["POST"])
def send_interested_message():
    if "user_id" not in session:
        return jsonify({"message": "Login required"}), 401

    data = request.get_json(force=True)
    product_name = data.get("product")
    seller_id = data.get("seller_id")

    if not product_name or not seller_id:
        return jsonify({"message": "Product and seller required"}), 400

    cur = db.cursor()
    cur.execute("SELECT phone FROM users WHERE id=%s", (seller_id,))
    seller = cur.fetchone()

    if not seller:
        return jsonify({"message": "Seller not found"}), 404

    seller_phone = seller[0]

    # --- TEST WITH YOUR OWN NUMBER FIRST ---
    # Replace with your WhatsApp number joined in sandbox
    seller_phone = "+919652403534"  

    if not seller_phone.startswith("+"):
        seller_phone = "+" + seller_phone

    to_whatsapp = f"whatsapp:{seller_phone}"
    message_text = f"Hi 👋 I am interested in your product '{product_name}'. Sent via ShopHub 🛒"

    try:
        response = requests.post(
            TWILIO_API_URL,
            data={
                "From": TWILIO_WHATSAPP_FROM,
                "To": to_whatsapp,
                "Body": message_text
            },
            auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        )

        # --- LOG EVERYTHING ---
        print("Twilio API URL:", TWILIO_API_URL)
        print("From:", TWILIO_WHATSAPP_FROM)
        print("To:", to_whatsapp)
        print("Message:", message_text)
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code in [200, 201]:
            return jsonify({"message": "WhatsApp message sent successfully!"}), 200
        else:
            return jsonify({
                "message": "Failed to send WhatsApp message",
                "twilio_status": response.status_code,
                "twilio_response": response.text
            }), 500

    except Exception as e:
        print(e)
        return jsonify({"message": "WhatsApp error", "error": str(e)}), 500
# ---------- Mark Product as SOLD ----------
@app.route("/mark_sold/<int:pid>", methods=["POST"])
def mark_product_sold(pid):
    if "user_id" not in session:
        return jsonify({"message": "Login required"}), 401

    cur = db.cursor()
    cur.execute(
        "UPDATE products SET status='sold' WHERE id=%s AND seller_id=%s",
        (pid, session["user_id"])
    )
    db.commit()

    return jsonify({"message": "Product marked as sold"})


# ---------- Delete from Browser (Hide) ----------
@app.route("/product/hide/<int:pid>")
def hide_product(pid):
    if "user_id" not in session:
        return redirect(url_for("auth_page"))

    cur = db.cursor()
    cur.execute(
        "UPDATE products SET is_visible=0 WHERE id=%s AND seller_id=%s",
        (pid, session["user_id"])
    )
    db.commit()
    return redirect(url_for("main_page"))

@app.route("/delete_product/<int:id>", methods=["POST"])
def delete_product(id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Login required"}), 401

    try:
        cur = db.cursor()
        # Delete the product only if it belongs to the logged-in seller
        cur.execute("DELETE FROM products WHERE id=%s AND seller_id=%s", (id, session["user_id"]))
        db.commit()

        if cur.rowcount == 0:
            # Nothing deleted
            return jsonify({"success": False, "message": "Product not found or you are not the owner"}), 404

        return jsonify({"success": True, "message": "Product deleted successfully"})
    except Exception as e:
        print("Delete Error:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
@app.route("/rate_website", methods=["POST"])
def rate_website():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Login required"}), 401

    user_id = session["user_id"]
    data = request.get_json(force=True)
    rating = data.get("rating")

    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"success": False, "message": "Invalid rating"}), 400

    cur = db.cursor()
    try:
        # Insert or update rating
        cur.execute("""
            INSERT INTO website_ratings (user_id, rating)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE rating=%s, created_at=CURRENT_TIMESTAMP
        """, (user_id, rating, rating))
        db.commit()

        return jsonify({"success": True, "message": f"Thanks {session['user_name']}! Your {rating}⭐ rating has been recorded. 🎉"})
    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": "Error saving rating"}), 500
@app.route("/get_website_rating")
def get_website_rating():
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS count, AVG(rating) AS average FROM website_ratings")
    result = cur.fetchone()
    count = result[0] or 0
    average = round(result[1] or 0, 1)
    return jsonify({"count": count, "average": average})

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
