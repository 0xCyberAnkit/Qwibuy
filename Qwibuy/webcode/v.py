from django.shortcuts import render

# Create your views here.

# views.py
import pandas as pd
import pickle,random

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

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

# Precompute top-selling products for fallback
top_products = purchase_df['product_id'].value_counts().index.tolist()

# Precomputed recommendations dictionary
precomputed_recommendations = {}

# -------------------------------
# Recommendation Logic
# -------------------------------
def compute_recommendations_for_retailer(retailer_id):
    purchased = purchase_df[purchase_df['retailer_id'] == retailer_id]['product_id'].tolist()

    # Personalized Picks (SVD)
    predictions = [(pid, svd_model.predict(retailer_id, pid).est)
                   for pid in all_products if pid not in purchased]
    predictions.sort(key=lambda x: x[1], reverse=True)
    personalized = [p[0] for p in predictions[:10]]

    # Cross-Sell / Upsell (Combo Rules)
    cross_sell = []
    for p in purchased:
        if p in combo_rules:
            cross_sell.extend([x[0] for x in combo_rules[p]])
    cross_sell = list(dict.fromkeys([p for p in cross_sell if p not in purchased and p not in personalized]))
    random.shuffle(cross_sell)
    cross_sell = cross_sell[:10]
    if not cross_sell:
        cross_sell = [p for p in top_products if p not in purchased and p not in personalized][:10]

    # Content-Based / New Products
    categories_bought = set([category_map[p] for p in purchased if p in category_map])
    content_based = [p for p in all_products
                     if p not in purchased
                     and p not in personalized
                     and p not in cross_sell
                     and category_map.get(p) in categories_bought]

    if len(content_based) < 10:
        additional = [p for p in all_products if p not in purchased and p not in personalized and p not in cross_sell and p not in content_based]
        content_based.extend(random.sample(additional, min(10 - len(content_based), len(additional))))

    content_based = content_based[:10]

    return {
        "new_products": [{"product_id": pid, "product_name": product_map.get(pid, pid)} for pid in content_based],
        "cross_sell": [{"product_id": pid, "product_name": product_map.get(pid, pid)} for pid in cross_sell],
        "personalized_picks": [{"product_id": pid, "product_name": product_map.get(pid, pid)} for pid in personalized]
    }

# -------------------------------
# Precompute for existing retailers
# -------------------------------
for retailer_id in purchase_df['retailer_id'].unique():
    precomputed_recommendations[retailer_id] = compute_recommendations_for_retailer(retailer_id)

print(" Precomputed recommendations ready")

# -------------------------------
# Views
# -------------------------------
def home(request):
    return render(request, "recommendations.html")

def get_recommendations(request):
    retailer_id = request.GET.get("retailer_id")
    if not retailer_id:
        return JsonResponse({"error": "Missing retailer_id"}, status=400)
    retailer_id = int(retailer_id)

    if retailer_id in precomputed_recommendations:
        result = precomputed_recommendations[retailer_id]
    else:
        result = compute_recommendations_for_retailer(retailer_id)
        precomputed_recommendations[retailer_id] = result

    return JsonResponse({"retailer_id": retailer_id, **result})

# -------------------------------
# Update after new purchase
# -------------------------------
def update_after_purchase(retailer_id, new_product_id, category, product_name):
    # Append to in-memory dataframe
    purchase_df.loc[len(purchase_df)] = [retailer_id, new_product_id, category, product_name]

    # Update precomputed recommendations
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
    return HttpResponse("✅ Purchase added and recommendations updated")


def index(request):
    return render(request,"Nexus.html")

def shop(request):
    return render(request,"shop.html")

def profile(request):
    return render(request,"profile.html")

def portal(request):
    return render(request,"myportal.html")
