from lilya.apps import Lilya
from lilya.decorators import observable

app = Lilya()


@app.post("/pay")
@observable(send=["payment_success"])
async def process_payment():
    return {"message": "Payment processed!"}


@observable(listen=["payment_success"])
async def notify_user():
    print("Notifying user about payment confirmation...")


@observable(listen=["payment_success"])
async def update_database():
    print("Updating payment database records...")


@observable(listen=["payment_success"])
async def generate_invoice():
    print("Generating invoice for the payment...")
