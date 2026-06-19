def add(a,b):
    return a+b


def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return execute(query)


def process_order(order):
    if order:
        if order.status == "paid":
            if order.items:
                for item in order.items:
                    if item.stock > 0:
                        item.stock -= 1
                    else:
                        print("out of stock")
    return True


def save_api_key():
    api_key = "demo-secret-value"
    return api_key
