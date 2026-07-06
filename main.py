from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import plans, customers, subscriptions, invoices, webhooks, portal
from app.database import engine
from app import models

app = FastAPI(
    title="NombaFlow",
    description="Managed recurring billing engine on Nomba",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans.router, prefix="/v1/plans", tags=["Plans"])
app.include_router(customers.router, prefix="/v1/customers", tags=["Customers"])
app.include_router(subscriptions.router, prefix="/v1/subscriptions", tags=["Subscriptions"])
app.include_router(invoices.router, prefix="/v1/invoices", tags=["Invoices"])
app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["Webhooks"])
app.include_router(portal.router, prefix="/v1/portal", tags=["Portal"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "nombaflow"}
