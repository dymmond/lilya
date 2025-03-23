from lilya.apps import Lilya
from lilya.decorators import observable

app = Lilya()

# User registration endpoint
@app.post("/register")
@observable(send=["user_registered"])
async def register_user(data: dict):
    return {"message": "User registered successfully!"}


# Listeners for the event
@observable(listen=["user_registered"])
async def send_welcome_email():
    print("Sending welcome email...")


@observable(listen=["user_registered"])
async def assign_default_roles():
    print("Assigning default roles to the user...")
