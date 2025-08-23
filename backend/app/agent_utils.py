from app.models import UserBillingCredential
from agent_service import agent_service

from sqlalchemy.orm import Session

async def simulate_agent_run(credential_id: str, db: Session):
    """Run agent for a specific credential"""
    credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
    if credential:
        # Use agent service to run the agent
        result = await agent_service.run_agent(credential, db)
        print(f"Agent result for {credential.email}: {result}")
