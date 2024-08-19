import random
import logging
import gevent
from locust import FastHttpUser, TaskSet, between, events, HttpUser, LoadTestShape
from faker import Faker
import datetime
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()

SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PORT = os.getenv("SERVER_PORT")
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

products = [
    '0PUK6V6EV0',
    '1YMWWN1N4O',
    '2ZYFJ3GM2N',
    '66VCHSJNUP',
    '6E92ZMYYFZ',
    '9SIQT8TOJO',
    'L9ECAV7KIM',
    'LS4PSXUNUM',
    'OLJCESPC7Z']

def index(l):
    l.client.get(f"{BASE_URL}/")

def setCurrency(l):
    currencies = ['EUR', 'USD', 'JPY', 'CAD', 'GBP', 'TRY']
    l.client.post(f"{BASE_URL}/setCurrency", {'currency_code': random.choice(currencies)})

def browseProduct(l):
    l.client.get(f"{BASE_URL}/product/" + random.choice(products))

def viewCart(l):
    l.client.get(f"{BASE_URL}/cart")

def addToCart(l):
    product = random.choice(products)
    l.client.get(f"{BASE_URL}/product/" + product)
    l.client.post(f"{BASE_URL}/cart", {
        'product_id': product,
        'quantity': random.randint(1,10)})
    
def empty_cart(l):
    l.client.post(f'{BASE_URL}/cart/empty')

def checkout(l):
    addToCart(l)
    current_year = datetime.datetime.now().year+1
    l.client.post(f"{BASE_URL}/cart/checkout", {
        'email': fake.email(),
        'street_address': fake.street_address(),
        'zip_code': fake.zipcode(),
        'city': fake.city(),
        'state': fake.state_abbr(),
        'country': fake.country(),
        'credit_card_number': fake.credit_card_number(card_type="visa"),
        'credit_card_expiration_month': random.randint(1, 12),
        'credit_card_expiration_year': random.randint(current_year, current_year + 70),
        'credit_card_cvv': f"{random.randint(100, 999)}",
    })
    
def logout(l):
    l.client.get(f'{BASE_URL}/logout')  


class UserBehavior(TaskSet):

    def on_start(self):
        index(self)

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
    wait_time = between(1, 1)  # Constant request frequency: 1 request per second

class CyclicLoadShape(LoadTestShape):
    step_time = 10  # Time between each step in seconds
    step_load = 10  # Number of users added at each step
    spawn_rate = 10  # Number of users to start/stop per second

    def __init__(self):
        super().__init__()
        self.scaling_up = True
        self.current_users = 0
        self.last_change_time = 0

    def tick(self):
        run_time = self.get_run_time()
        elapsed_time = run_time - self.last_change_time

        if elapsed_time >= self.step_time:
            if self.scaling_up:
                self.current_users += self.step_load
                if self.current_users >= 100:  # Max user limit for scaling up
                    self.current_users = 100
                    self.scaling_up = False
                logger.info(f"Scaling up to {self.current_users} users at {run_time} seconds")
            else:
                self.current_users = 10
                self.scaling_up = True
                logger.info(f"Scaling down to {self.current_users} users at {run_time} seconds")

            self.last_change_time = run_time
            return (self.current_users, self.spawn_rate)
        else:
            return (self.current_users, self.spawn_rate)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("Test is starting...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("Test is stopping...")

if __name__ == "__main__":
    # Locust will use the WebsiteUser class as the default user
    WebsiteUser().run()

