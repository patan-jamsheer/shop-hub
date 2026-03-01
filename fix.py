with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'host="localhost",\n    user="root",\n    password="Jamsheer@2006",\n    database="olx_clone"',
    'host=os.environ.get("MYSQL_HOST"),\n    user=os.environ.get("MYSQL_USER"),\n    password=os.environ.get("MYSQL_PASSWORD"),\n    database=os.environ.get("MYSQL_DB")'
)

content = content.replace(
    'host="localhost",\n    user="root",\n    password="Jamsheer@2006",\n    database="olx_chatbot"',
    'host=os.environ.get("MYSQL_HOST"),\n    user=os.environ.get("MYSQL_USER"),\n    password=os.environ.get("MYSQL_PASSWORD"),\n    database=os.environ.get("MYSQL_DB")'
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')