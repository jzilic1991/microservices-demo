import random
import logging
import gevent
from locust import FastHttpUser, TaskSet, between, events, LoadTestShape
from faker import Faker
import datetime
import os

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()

SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = os.getenv("SERVER_PORT", "5001")
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

products = [
    '0PUK6V6EV0', '1YMWWN1N4O', '2ZYFJ3GM2N', '66VCHSJNUP',
    '6E92ZMYYFZ', '9SIQT8TOJO', 'L9ECAV7KIM', 'LS4PSXUNUM', 'OLJCESPC7Z'
]

def index(l):
    l.client.get(f"{BASE_URL}/", params={"user": l.user_id})
    logger.info(f"[Locust] GET / | user={l.user_id}")

def setCurrency(l):
    payload = {'currency_code': random.choice(['EUR', 'USD', 'JPY', 'CAD', 'GBP', 'TRY']), 'user': l.user_id}
    l.client.post(f"{BASE_URL}/setCurrency", data=payload)
    logger.info(f"[Locust] POST /setCurrency | user={l.user_id} | data={payload}")

def browseProduct(l):
    product = random.choice(products)
    l.client.get(f"{BASE_URL}/product/{product}", params={"user": l.user_id})
    logger.info(f"[Locust] GET /product/{product} | user={l.user_id}")

def viewCart(l):
    l.client.get(f"{BASE_URL}/cart", params={"user": l.user_id})
    logger.info(f"[Locust] GET /cart | user={l.user_id}")

def addToCart(l):
    product = random.choice(products)
    l.client.get(f"{BASE_URL}/product/{product}", params={"user": l.user_id})
    payload = {
        'product_id': product,
        'quantity': random.randint(1, 10),
        'user': l.user_id
    }
    l.client.post(f"{BASE_URL}/cart", data=payload)
    logger.info(f"[Locust] POST /cart | user={l.user_id} | data={payload}")

def empty_cart(l):
    payload = {'user': l.user_id}
    l.client.post(f"{BASE_URL}/cart/empty", data=payload)
    logger.info(f"[Locust] POST /cart/empty | user={l.user_id}")

def checkout(l):
    addToCart(l)
    payload = {
        'email': fake.email(),
        'street_address': fake.street_address(),
        'zip_code': fake.zipcode(),
        'city': fake.city(),
        'state': fake.state_abbr(),
        'country': fake.country(),
        'credit_card_number': fake.credit_card_number(card_type="visa"),
        'credit_card_expiration_month': random.randint(1, 12),
        'credit_card_expiration_year': datetime.datetime.now().year + random.randint(1, 5),
        'credit_card_cvv': f"{random.randint(100, 999)}",
        'user': l.user_id
    }
    l.client.post(f"{BASE_URL}/cart/checkout", data=payload)
    logger.info(f"[Locust] POST /cart/checkout | user={l.user_id} | data={payload}")

def logout(l):
    l.client.get(f"{BASE_URL}/logout", params={"user": l.user_id})
    logger.info(f"[Locust] GET /logout | user={l.user_id}")

class UserBehavior(TaskSet):
    def on_start(self):
        self.user_id = fake.uuid4()
        self._print_loop = gevent.spawn(self._print_user_id)
        index(self)

    def _print_user_id(self):
        while True:
            logger.info(f"[Locust] Periodic User ID = {self.user_id}")
            gevent.sleep(10)

    tasks = {
        index: 1,
        setCurrency: 2,
        browseProduct: 10,
        addToCart: 2,
        viewCart: 3,
        checkout: 1
    }

class WebsiteUser(FastHttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 1)

class CyclicLoadShape(LoadTestShape):
    def tick(self):
        return (1, 1)  # Fixed: 1 user, no scaling

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("[Locust] Test is starting...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("[Locust] Test is stopping...")

