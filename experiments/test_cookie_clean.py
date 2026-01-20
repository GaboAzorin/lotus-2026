from http.cookies import SimpleCookie

raw_cookie = "JSESSIONID=A8B9C7; Path=/; Secure; HttpOnly; SameSite=Lax"
cookie = SimpleCookie()
cookie.load(raw_cookie)
print("Original:", raw_cookie)
print("Parsed Items:", [(k, v.value) for k, v in cookie.items()])
cleaned = "; ".join([f"{k}={v.value}" for k, v in cookie.items()])
print("Cleaned:", cleaned)

raw_cookie_2 = "JSESSIONID=123; Path=/; Secure, OTHER=456; Path=/"
cookie2 = SimpleCookie()
cookie2.load(raw_cookie_2)
print("Original 2:", raw_cookie_2)
print("Parsed Items 2:", [(k, v.value) for k, v in cookie2.items()])
cleaned2 = "; ".join([f"{k}={v.value}" for k, v in cookie2.items()])
print("Cleaned 2:", cleaned2)
