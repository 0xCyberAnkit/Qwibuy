import pandas as pd
from surprise import Dataset, Reader, SVD
import pickle

# Load purchase data
df = pd.read_csv("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\purchase_history.csv")
df['purchase_score'] = 1  # binary purchase

# --- SVD Collaborative Filtering ---
reader = Reader(rating_scale=(1, 1))
data = Dataset.load_from_df(df[['retailer_id','product_id','purchase_score']], reader)
trainset = data.build_full_trainset()
svd_model = SVD()
svd_model.fit(trainset)

with open("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\svd_model.pkl","wb") as f:
    pickle.dump(svd_model,f)

# --- Combo Rules (co-purchase) ---
basket = df.groupby(['retailer_id','product_id'])['purchase_score'].sum().unstack().fillna(0)
combo_rules = {}
for p1 in basket.columns:
    for p2 in basket.columns:
        if p1 != p2:
            both = (basket[p1]>0) & (basket[p2]>0)
            if (basket[p1]>0).sum() > 0:
                confidence = both.sum() / (basket[p1]>0).sum()
                if confidence > 0.4:
                    combo_rules.setdefault(p1,[]).append((p2,round(confidence,2)))

with open("C:\\Users\\ankit\\OneDrive\\Desktop\\Projects\\Projects\\Qwibuy\\webcode\\product_combos.pkl","wb") as f:
    pickle.dump(combo_rules,f)

print("Hybrid recommender trained: SVD + Combo Rules")
