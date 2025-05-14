import random
import logging
import gevent
from locust import FastHttpUser, TaskSet, between, events, LoadTestShape
from faker import Faker
from tabulate import tabulate
import datetime
import os

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

active_users = set()

def print_active_users():
    if active_users:
        table = [(i + 1, uid) for i, uid in enumerate(active_users)]
        logger.info("\n" + tabulate(table, headers=["#", "User ID"], tablefmt="pretty"))


def index(l):
    l.client.get(f"{BASE_URL}/", params={"user": l.user_id})
    logger.info(f"[Locust] GET / | user={l.user_id}")


def setCurrency(l):
    payload = {'currency_code': random.choice(['EUR', 'USD', 'JPY', 'CAD', 'GBP', 'TRY'])}
    l.client.post(f"{BASE_URL}/setCurrency", data=payload, params={"user": l.user_id})
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
    }
    l.client.post(f"{BASE_URL}/cart", data=payload, params={"user": l.user_id})
    logger.info(f"[Locust] POST /cart | user={l.user_id} | data={payload}")


def empty_cart(l):
    l.client.post(f"{BASE_URL}/cart/empty", data={}, params={"user": l.user_id})
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
    }
    l.client.post(f"{BASE_URL}/cart/checkout", data=payload, params={"user": l.user_id})
    logger.info(f"[Locust] POST /cart/checkout | user={l.user_id} | data={payload}")


def logout(l):
    l.client.get(f"{BASE_URL}/logout", params={"user": l.user_id})
    logger.info(f"[Locust] GET /logout | user={l.user_id}")


class UserBehavior(TaskSet):
    def on_start(self):
        self.user_id = fake.uuid4()
        active_users.add(self.user_id)
        print_active_users()
        index(self)

    def on_stop(self):
        active_users.discard(self.user_id)
        print_active_users()

    tasks = {
        index: 1,
        setCurrency: 2,
        browseProduct: 10,
        addToCart: 2,
        viewCart: 3,
        checkout: 1,
        empty_cart: 1
    }


class WebsiteUser(FastHttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 1)


class CyclicLoadShape(LoadTestShape):
    last_user_count = 0  # ⬅️ Track last known user count

    def tick(self):
        run_time = self.get_run_time()
        cycle = run_time // 30

        if cycle % 2 == 0:
            user_count = 10
        else:
            user_count = 2

        # ✅ Print active user IDs only if we're increasing
        if user_count > self.last_user_count:
            logger.info(f"[Locust] Scaling up to {user_count} users.")
            print_active_users()

        self.last_user_count = user_count
        return (user_count, 1)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("[Locust] Test is starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("[Locust] Test is stopping...")

