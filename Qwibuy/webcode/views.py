from django.shortcuts import render,redirect

# Create your views here.

# views.py
import pandas as pd
import pickle,random,json
from surprise import Dataset, Reader, SVD
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
import mysql.connector as mydb

def server():
    global con,cur
    con = mydb.connect(host='localhost',user='root',password='Ankit1234',database='qwibuy')
    cur = con.cursor()

# Load trained model + combo rules once (global)
with open("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\svd_model.pkl", "rb") as f:
    svd_model = pickle.load(f)

with open("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\product_combos.pkl", "rb") as f:
    combo_rules = pickle.load(f)

# Load product list and names (for better output)
purchase_df = pd.read_csv("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\purchase_history.csv")
all_products = purchase_df['product_id'].unique().tolist()
product_map = dict(zip(purchase_df['product_id'], purchase_df['product_name']))
category_map = dict(zip(purchase_df['product_id'], purchase_df['category']))
file = open("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\product_sample.json")
data = json.load(file)
file.close()
# Precompute top-selling products (fallback)
top_products = purchase_df['product_id'].value_counts().index.tolist()

# Precomputed recommendations dictionary
precomputed_recommendations = {}

# -------------------------------
# Core Recommendation Function
# -------------------------------
def compute_recommendations_for_retailer(retailer_id):
    purchased = purchase_df[purchase_df['retailer_id'] == retailer_id]['product_id'].tolist()

    # --- Personalized Picks (SVD) ---
    predictions = [(pid, svd_model.predict(retailer_id, pid).est)
                   for pid in all_products if pid not in purchased]
    predictions.sort(key=lambda x: x[1], reverse=True)
    personalized = [p[0] for p in predictions[:10]]

    # --- Cross-Sell / Upsell (Combo Rules) ---
    cross_sell = []
    for p in purchased:
        if p in combo_rules:
            cross_sell.extend([x[0] for x in combo_rules[p]])
    cross_sell = list(dict.fromkeys([p for p in cross_sell if p not in purchased]))
    random.shuffle(cross_sell)
    cross_sell = cross_sell[:10]
    if not cross_sell:
        # Fallback to top-selling
        cross_sell = [p for p in top_products if p not in purchased][:10]

    # --- Content-Based Filtering (CBF) ---
    categories_bought = set([category_map[p] for p in purchased if p in category_map])
    content_based = [p for p in all_products
                     if category_map.get(p) in categories_bought
                     and p not in purchased
                     and p not in personalized
                     and p not in cross_sell]
    if content_based:
        content_based = random.sample(content_based, min(10, len(content_based)))
    else:
        # fallback: random new products
        content_based = [p for p in all_products if p not in purchased and p not in personalized and p not in cross_sell]
        content_based = random.sample(content_based, min(10, len(content_based)))

    # Return dict
    return {
        "new_products": [{"product_id": pid, "product_name": product_map.get(pid, pid), "product_price" : data[pid][-2],"product_cat" : data[pid][-3], "product_img" : data[pid][-1]} for pid in content_based],
        "cross_sell": [{"product_id": pid, "product_name": product_map.get(pid, pid), "product_price" : data[pid][-2],"product_icat" : data[pid][-3], "product_img" : data[pid][-1]} for pid in cross_sell],
        "personalized_picks": [{"product_id": pid, "product_name": product_map.get(pid, pid), "product_price" : data[pid][-2],"product_cat" : data[pid][-3], "product_img" : data[pid][-1]} for pid in personalized]
    }

# -------------------------------
# Precompute for all existing retailers
# -------------------------------
for retailer_id in purchase_df['retailer_id'].unique():
    precomputed_recommendations[retailer_id] = compute_recommendations_for_retailer(retailer_id)

print(" Precomputed recommendations ready for all retailers")

# -------------------------------
# Views
# -------------------------------

def get_recommendations(request):
    retailer_id = request.GET.get("retailer_id")
    if not retailer_id:
        return JsonResponse({"error": "Missing retailer_id"}, status=400)
    retailer_id = int(retailer_id)

    # Fetch precomputed recommendations
    if retailer_id in precomputed_recommendations:
        result = precomputed_recommendations[retailer_id]
    else:
        # Compute on-demand for new retailer
        result = compute_recommendations_for_retailer(retailer_id)
        precomputed_recommendations[retailer_id] = result

    return JsonResponse({"retailer_id": retailer_id, **result})

# -------------------------------
# Update after a new purchase
# -------------------------------
def update_after_purchase(retailer_id, new_product_id, category, product_name):
    # Add new purchase to in-memory dataframe
    purchase_df.loc[len(purchase_df)] = [retailer_id, new_product_id, category, product_name]

    # Update recommendations for this retailer
    precomputed_recommendations[retailer_id] = compute_recommendations_for_retailer(retailer_id)
# -------------------------------
# Simulate Purchase API
# -------------------------------
@csrf_exempt
def simulate_purchase(request):
    retailer_id = int(request.GET.get("retailer_id"))
    product_id = request.GET.get("product_id")
    product_name = request.GET.get("product_name")
    category = request.GET.get("category")

    update_after_purchase(retailer_id, product_id, category, product_name)
    return HttpResponse("Purchase added and recommendations updated")

def auth(request):
    request.session['email'] = None
    server()
    if request.method == 'POST':
        data = {}
        if request.POST.get('mode') == 'login':
            email = request.POST.get('email')
            password = request.POST.get('password')
            cur.execute("select * from users where email = %s and password = %s ;" ,(email,password))
            profile = cur.fetchall()
            if profile:
                request.session['email'] = profile[0][2]
                request.session['name'] = profile[0][1]
                request.session['uid'] = profile[0][0]
                data['verified'] = 'verified'
            else:
                data['a'] = 'a'
            return JsonResponse(data)
        else:
            name = request.POST.get('name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            repeatpass = request.POST.get('repass')
            cur.execute(f"select * from users where email = '{email}';")
            if cur.fetchall():
                data['error'] = 'accounterror'
            elif password != repeatpass:
                data['error'] = 'passworderror'
            else:
                data['success'] = 'success'
                cur.execute("insert into users (name,email,password) values (%s,%s,%s);",(name,email,password))
                con.commit()
            return JsonResponse(data)
    return render(request,'auth.html')

def index(request):
    server()
    email = request.session.get('email')
    if not email:
        return redirect('/auth')
    data = {
        "name":request.session.get('name'),
        "uid":request.session.get('uid')+100
    }
    return render(request,"Nexus.html",data)

def shop(request):
    server()
    email = request.session.get('email')
    if not email:
        return redirect('/auth')
    data = {
        "name":request.session.get('name'),
        "uid":request.session.get('uid')+100
    }
    return render(request,"shop.html",data)

def profile(request):
    server()
    email = request.session.get('email')
    if not email:
        return redirect('/auth')
    data = {
        "name":request.session.get('name'),
        "email":request.session.get('email'),
        "uid":int(request.session.get('uid'))+100
    }
    return render(request,"profile.html",data)

def portal(request):
    server()
    email = request.session.get('email')
    if not email:
        return redirect('/auth')
    data = {
        "uid":request.session.get('uid')+100
    }
    return render(request,"myportal.html",data)

