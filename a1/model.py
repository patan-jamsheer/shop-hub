import pandas as pd
from sklearn.linear_model import LogisticRegression

# Dummy training data
data = {
    "email_length":[10,5,25,30],
    "phone_length":[10,4,10,3],
    "is_fake":[0,1,0,1]
}

df = pd.DataFrame(data)

X = df[["email_length","phone_length"]]
y = df["is_fake"]

model = LogisticRegression()
model.fit(X,y)

def predict_fake(email, phone):
    return model.predict([[len(email), len(phone)]])[0]
